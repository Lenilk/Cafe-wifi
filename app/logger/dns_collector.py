"""
logger/dns_collector.py — เก็บ DNS query log จาก dnsmasq (`log-queries` ใน dnsmasq.conf)

ข้อจำกัดที่ต้องเขียนในเล่ม (ดู §6.5): ถ้าลูกค้าใช้ DNS-over-HTTPS ในเบราว์เซอร์
โดยตรง log นี้จะไม่เห็น query นั้นเลย เพราะไม่ผ่าน dnsmasq
"""
from __future__ import annotations

import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime

from .netutil import MacCache
from .telemetry import CollectorTelemetry

log = logging.getLogger("cafe-wifi.dns_collector")

# ตัวอย่างบรรทัดจริงจาก dnsmasq (log-facility ไปไฟล์, ไม่ผ่าน syslog prefix มาตรฐาน
# แต่ dnsmasq ยังคงใส่ timestamp+pid นำหน้าเองเป็นค่าเริ่มต้น):
#   Aug 22 10:15:32 dnsmasq[1234]: query[A] example.com from 10.10.0.105
#   Aug 22 10:15:32 dnsmasq[1234]: forwarded example.com to 1.1.1.1
#   Aug 22 10:15:33 dnsmasq[1234]: reply example.com is 93.184.216.34
#   Aug 22 10:15:33 dnsmasq[1234]: cached example.com is 93.184.216.34
#   Aug 22 10:15:33 dnsmasq[1234]: reply example.com is <CNAME>
_TS_PREFIX = re.compile(r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+dnsmasq(?:\[\d+\])?:\s*(.*)$")
_QUERY_RE = re.compile(r"^query\[(?P<qtype>\w+)\]\s+(?P<qname>\S+)\s+from\s+(?P<ip>\S+)$")
_REPLY_RE = re.compile(r"^(?:reply|cached)\s+(?P<qname>\S+)\s+is\s+(?P<answer>\S+)$")

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def parse_syslog_timestamp(text: str, now: datetime | None = None) -> datetime:
    """'Aug 22 10:15:32' -> datetime (เดา ปี จาก now, กันช่วงข้ามปีใหม่ตอน tail log เก่า)"""
    now = now or datetime.now()
    mon_s, day_s, time_s = text.split()
    month = _MONTHS[mon_s]
    day = int(day_s)
    hh, mm, ss = (int(x) for x in time_s.split(":"))
    year = now.year
    candidate = datetime(year, month, day, hh, mm, ss)
    if candidate - now > _MAX_FUTURE_SKEW:
        candidate = datetime(year - 1, month, day, hh, mm, ss)
    return candidate


from datetime import timedelta  # noqa: E402

_MAX_FUTURE_SKEW = timedelta(days=1)


@dataclass(frozen=True)
class DnsQueryEvent:
    ts: datetime
    client_ip: str
    qname: str
    qtype: str


@dataclass(frozen=True)
class DnsAnswerEvent:
    ts: datetime
    qname: str
    answer: str


def parse_dnsmasq_line(line: str, now: datetime | None = None):
    """คืน DnsQueryEvent | DnsAnswerEvent | None"""
    line = line.rstrip("\n")
    m = _TS_PREFIX.match(line)
    if not m:
        return None
    ts_text, rest = m.group(1), m.group(2)

    qm = _QUERY_RE.match(rest)
    if qm:
        return DnsQueryEvent(ts=parse_syslog_timestamp(ts_text, now), client_ip=qm.group("ip"),
                             qname=qm.group("qname").rstrip("."), qtype=qm.group("qtype"))

    rm = _REPLY_RE.match(rest)
    if rm:
        return DnsAnswerEvent(ts=parse_syslog_timestamp(ts_text, now),
                              qname=rm.group("qname").rstrip("."), answer=rm.group("answer"))

    return None  # เช่นบรรทัด "forwarded ... to ..." ที่เราไม่สนใจ


class DnsCorrelator:
    """เก็บ query และ answer แยกกัน เพราะ text log ไม่มี request id สำหรับจับคู่ที่แน่นอน"""

    def feed_line(self, line: str, now: datetime | None = None) -> dict | None:
        ev = parse_dnsmasq_line(line, now)
        if isinstance(ev, DnsQueryEvent):
            return dict(ts=ev.ts, client_ip=ev.client_ip, qname=ev.qname,
                        qtype=ev.qtype, answer=None, event_kind="query")
        if isinstance(ev, DnsAnswerEvent):
            return dict(ts=ev.ts, client_ip=None, qname=ev.qname,
                        qtype=None, answer=ev.answer, event_kind="answer")
        return None


def insert_dns_rows(rows: list[dict], mac_cache: MacCache, on_unmapped=None) -> int:
    from common.db import get_conn

    values = []
    unmapped = 0
    for r in rows:
        mac = mac_cache.get(r["client_ip"]) if r["client_ip"] else None
        if r["client_ip"] and not mac:
            unmapped += 1
        values.append((r["ts"], r["client_ip"], mac, r["qname"][:255],
                       (r["qtype"] or "")[:10] or None,
                       (r["answer"] or "")[:255] or None, r["event_kind"]))
    if not values:
        return 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO dns_log (ts, client_ip, mac, qname, qtype, answer, event_kind) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)", values)
    if on_unmapped and unmapped:
        on_unmapped(unmapped)
    return len(values)


MAX_PENDING_RECORDS = 20000


def flush_buffer(buffer: list[dict], mac_cache: MacCache,
                 max_pending: int = MAX_PENDING_RECORDS,
                 telemetry: CollectorTelemetry | None = None) -> int:
    if not buffer:
        return 0
    try:
        if telemetry:
            n = insert_dns_rows(buffer, mac_cache, on_unmapped=telemetry.missing_mac)
        else:
            n = insert_dns_rows(buffer, mac_cache)
    except Exception:
        log.exception("เขียน dns_log ไม่สำเร็จ — เก็บ %d รายการไว้ลองใหม่", len(buffer))
        if telemetry:
            telemetry.error("เขียน dns_log ไม่สำเร็จ")
        if len(buffer) > max_pending:
            dropped = buffer[:len(buffer) - max_pending]
            del buffer[:len(dropped)]
            log.error("log_gap dns_log: ทิ้ง %d รายการ ช่วง %s ถึง %s",
                      len(dropped), dropped[0]["ts"], dropped[-1]["ts"])
            if telemetry:
                telemetry.drop(len(dropped))
        return 0
    buffer.clear()
    if telemetry:
        telemetry.write(n)
    return n


def run_forever(log_path: str = "/var/log/cafe-wifi/dnsmasq.log",
                batch_size: int = 200, flush_interval: float = 5.0) -> None:  # pragma: no cover
    """tail -F แบบง่าย ๆ ด้วยมือ (ไม่พึ่ง binary ภายนอก) แล้วป้อนเข้า DnsCorrelator"""
    correlator = DnsCorrelator()
    mac_cache = MacCache()
    telemetry = CollectorTelemetry("dns", os.path.dirname(log_path))
    buffer: list[dict] = []
    last_flush = time.time()

    log.info("เริ่ม dns_collector: tail -F %s", log_path)
    f = open(log_path, "r", encoding="utf-8", errors="replace")
    try:
        f.seek(0, 2)  # ไปท้ายไฟล์ก่อน แล้วค่อยตามอ่านของใหม่
        while True:
            telemetry.heartbeat()
            line = f.readline()
            if not line:
                now = time.time()
                if buffer and now - last_flush >= flush_interval:
                    flush_buffer(buffer, mac_cache, telemetry=telemetry)
                    last_flush = now
                try:
                    replaced = os.fstat(f.fileno()).st_ino != os.stat(log_path).st_ino
                except FileNotFoundError:
                    replaced = False
                if replaced:
                    log.info("dnsmasq.log ถูกหมุน — เปิดไฟล์ใหม่")
                    f.close()
                    f = open(log_path, "r", encoding="utf-8", errors="replace")
                    # ตำแหน่งเริ่มต้นเป็น 0 เพื่ออ่านบรรทัดที่เข้ามาระหว่างหมุนไฟล์
                time.sleep(0.5)
                continue
            row = correlator.feed_line(line)
            if row:
                buffer.append(row)
                telemetry.event()
            if len(buffer) >= batch_size:
                flush_buffer(buffer, mac_cache, telemetry=telemetry)
                last_flush = time.time()
    finally:
        f.close()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    run_forever()
