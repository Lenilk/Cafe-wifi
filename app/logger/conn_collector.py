"""
logger/conn_collector.py — เก็บข้อมูลจราจร (metadata เท่านั้น, D5) จาก `conntrack -E`

รันจริงต้องใช้สิทธิ์ CAP_NET_ADMIN/CAP_NET_RAW (systemd unit cafe-logger.service ให้ไว้แล้ว)
และต้องเปิด accounting ของเคอร์เนลก่อนจึงจะได้ตัวเลข bytes:
    sysctl -w net.netfilter.nf_conntrack_acct=1

ไฟล์นี้แยกส่วน "แปลงข้อความ 1 บรรทัดเป็นข้อมูล" (parse_conntrack_line, ทดสอบได้ล้วน ๆ
ไม่ต้องมี conntrack จริง) ออกจากส่วน "รันจริงแบบ stream ต่อเนื่อง" (run_forever)
เพื่อให้ตรรกะหลักตรวจสอบได้โดยไม่ต้องพึ่งฮาร์ดแวร์/สิทธิ์ root
"""
from __future__ import annotations

import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass

from .netutil import MacCache

log = logging.getLogger("cafe-wifi.conn_collector")

_BRACKET_RE = re.compile(r"\[([^\]]*)\]")
_KV_RE = re.compile(r"(\w+)=(\S+)")
_TS_RE = re.compile(r"^\[(\d+\.\d+)\]")

# เฉพาะ event ที่บอกว่า connection "จบแล้ว" เท่านั้นที่มีตัวเลข bytes สุดท้ายให้บันทึก
# NEW/UPDATE ยังไม่นิ่ง ถ้าบันทึกทุก event จะซ้ำซ้อนและ bytes ยังไม่ครบ
INTERESTING_EVENTS = {"DESTROY"}


@dataclass(frozen=True)
class ConnRecord:
    ts: float
    proto: str
    src_ip: str
    src_port: int | None
    dst_ip: str
    dst_port: int | None
    bytes_out: int
    bytes_in: int


def _proto_norm(p: str) -> str:
    p = p.lower()
    return p if p in {"tcp", "udp", "icmp"} else "other"


def parse_conntrack_line(line: str, now: float | None = None) -> ConnRecord | None:
    """
    แปลงบรรทัดหนึ่งจาก `conntrack -E -o timestamp -e DESTROY [-o extended]`
    คืน None ถ้าไม่ใช่ event ที่สนใจ หรือ parse ไม่ได้ (บันทึก warning แล้วข้าม ไม่ throw
    เพื่อไม่ให้ 1 บรรทัดเสียทำให้ collector ทั้งตัวตายทั้งกระบวนการ)
    """
    line = line.strip()
    if not line:
        return None

    ts = now if now is not None else time.time()
    m = _TS_RE.match(line)
    if m:
        try:
            ts = float(m.group(1))
        except ValueError:
            pass
        line = _TS_RE.sub("", line, count=1).strip()

    brackets = _BRACKET_RE.findall(line)
    event = brackets[0].upper() if brackets else ""
    if INTERESTING_EVENTS and event not in INTERESTING_EVENTS:
        return None

    body = _BRACKET_RE.sub(" ", line)
    tokens = body.split()
    proto = "other"
    for tok in tokens:
        if "=" not in tok and not tok.isdigit():
            proto = _proto_norm(tok)
            break

    kv_first: dict[str, str] = {}
    byte_values: list[int] = []
    for k, v in _KV_RE.findall(body):
        if k == "bytes":
            try:
                byte_values.append(int(v))
            except ValueError:
                pass
            continue
        kv_first.setdefault(k, v)  # การเกิดครั้งแรก = ทิศทาง original (client -> server)

    src_ip = kv_first.get("src")
    dst_ip = kv_first.get("dst")
    if not src_ip or not dst_ip:
        log.warning("conntrack line ไม่มี src/dst ครบ ข้ามบรรทัดนี้: %r", line[:200])
        return None

    def _to_port(v: str | None) -> int | None:
        try:
            return int(v) if v is not None else None
        except ValueError:
            return None

    bytes_out = byte_values[0] if len(byte_values) >= 1 else 0
    bytes_in = byte_values[1] if len(byte_values) >= 2 else 0

    return ConnRecord(
        ts=ts, proto=proto, src_ip=src_ip, src_port=_to_port(kv_first.get("sport")),
        dst_ip=dst_ip, dst_port=_to_port(kv_first.get("dport")),
        bytes_out=bytes_out, bytes_in=bytes_in,
    )


def insert_conn_records(records: list[ConnRecord], mac_cache: MacCache) -> int:
    """เขียนกลุ่ม record ลง conn_log เป็น batch — คืนจำนวนแถวที่เขียนสำเร็จ"""
    from datetime import datetime

    from common.db import get_conn

    rows = []
    for r in records:
        mac = mac_cache.get(r.src_ip)
        if not mac:
            continue  # หา MAC ไม่เจอ (หลุดจาก ARP cache แล้ว) -- ข้ามแทนที่จะเก็บ MAC ว่าง
        rows.append((datetime.fromtimestamp(r.ts), mac, r.src_ip, r.src_port,
                     r.dst_ip, r.dst_port, r.proto, r.bytes_out, r.bytes_in))
    if not rows:
        return 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO conn_log (ts, mac, src_ip, src_port, dst_ip, dst_port, "
            "proto, bytes_out, bytes_in) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    return len(rows)


def run_forever(batch_size: int = 100, flush_interval: float = 5.0) -> None:  # pragma: no cover
    """
    รันจริงบน gateway: เปิด `conntrack -E` เป็น subprocess แบบ stream แล้วอ่านทีละบรรทัด
    ฟังก์ชันนี้ไม่มี unit test ตรง ๆ (ต้องมี conntrack-tools + สิทธิ์ root) แต่ตรรกะการ
    parse/insert ด้านบนถูกทดสอบแยกแล้วอย่างละเอียด
    """
    mac_cache = MacCache()
    buffer: list[ConnRecord] = []
    last_flush = time.time()

    cmd = ["conntrack", "-E", "-o", "timestamp,extended", "-e", "DESTROY"]
    log.info("เริ่ม conn_collector: %s", " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            rec = parse_conntrack_line(line)
            if rec:
                buffer.append(rec)
            now = time.time()
            if len(buffer) >= batch_size or (buffer and now - last_flush >= flush_interval):
                try:
                    n = insert_conn_records(buffer, mac_cache)
                    log.debug("บันทึก conn_log %d แถว", n)
                except Exception:
                    log.exception("เขียน conn_log ไม่สำเร็จ — จะลองใหม่รอบถัดไป")
                buffer.clear()
                last_flush = now
    finally:
        proc.terminate()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    run_forever()
