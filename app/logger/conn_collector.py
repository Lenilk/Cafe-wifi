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
import queue
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

from .netutil import MacCache
from .telemetry import CollectorTelemetry

log = logging.getLogger("cafe-wifi.conn_collector")

# N31 (พบบน Pi จริง 2026-09-20 ขณะทดสอบโควตาด้วยการโหลดไฟล์ 100 MB หลายรอบ):
# `conntrack -E` พ่น "WARNING: We have hit ENOBUFS! We are losing events." ออก stderr
# แปลว่าเคอร์เนลทิ้งเหตุการณ์เพราะบัฟเฟอร์ netlink เต็ม -> conn_log ขาดหายจริง (วัดได้: โหลด
# 5 ไฟล์ บันทึกได้ 2) ซึ่งร้ายแรงมากสำหรับหลักฐานตาม ม.26 เพราะช่วงที่ร้านคนเยอะคือช่วงที่
# log ต้องครบที่สุด · ของเดิมยังไม่เคยอ่าน stderr เลย คำเตือนจึงไม่มีใครเห็น และถ้าท่อ stderr
# เต็ม (64 KB) conntrack จะค้าง = หยุดเก็บ log ทั้งระบบแบบเงียบ ๆ
# 2026-09-20 รอบสอง: 8 MB ยังไม่พอ -- ยังเจอ ENOBUFS ตอนโหลดไฟล์ต่อเนื่อง (เห็นช้าเพราะ
# stderr ของ conntrack ถูกพักในบัฟเฟอร์ก่อนไหลออกมา ทำให้ตอนเช็คทันทีหลังทดสอบยังไม่เห็น)
# เคอร์เนลจะคูณสองให้อีกที และ conntrack ใช้ SO_RCVBUFFORCE จึงข้ามเพดาน net.core.rmem_max ได้
NETLINK_BUFFER_BYTES = 32 * 1024 * 1024
# คิวกันการอ่านช้าเพราะรอเขียน DB -- ตัวอ่านต้องว่างตลอดเพื่อไม่ให้ท่อจากเคอร์เนลตัน
EVENT_QUEUE_MAX = 20000
# เพดานเรคคอร์ดที่ค้างรอเขียนตอน DB ล่ม (กันหน่วยความจำบวมไม่มีที่สิ้นสุด)
MAX_PENDING_RECORDS = 20000
PIPE_BUFFER_BYTES = 1024 * 1024  # N39 -- ท่อปริยาย 64 KB เต็มได้ในชุดเดียวตอน conntrack เก็บกวาด
F_SETPIPE_SZ = 1031              # ค่าคงที่ของ Linux (ไม่มีใน fcntl ของ Python)

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
    # *** แก้บั๊ก (พบจาก conntrack ตัวจริงบน VM lab, 2026-08-28) *** — เดิมเข้าใจว่า token
    # ที่ไม่ใช่ตัวเลข/key=value ตัวแรกคือชื่อโปรโตคอล แต่ผลจริงจาก `conntrack -E -o
    # timestamp,extended` ขึ้นต้นด้วย address family ("ipv4"/"ipv6") ก่อนเสมอ เช่น
    # "ipv4     2 tcp      6 72 TIME_WAIT src=... dst=..." -- โค้ดเดิมเจอ "ipv4" เป็น
    # token แรกที่เข้าเงื่อนไข แล้ว _proto_norm("ipv4") คืน "other" ทันทีแบบไม่ทันได้
    # เห็น "tcp" ที่ตามมาเลย -- ผลคือ proto เป็น "other" 100% ของทุกแถวเสมอ (ยืนยันจาก
    # conn_log จริงบน VM lab: 16/16 แถวเป็น "other" หมด ทั้งที่มี TCP/UDP จริงปนอยู่)
    # ต้องข้าม "ipv4"/"ipv6" ไปก่อนถึงจะเจอ token ที่เป็นชื่อโปรโตคอลจริง
    for tok in tokens:
        if tok.lower() in ("ipv4", "ipv6"):
            continue
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


def insert_conn_records(records: list[ConnRecord], mac_cache: MacCache,
                        on_unmapped=None) -> int:
    """เขียนกลุ่ม record ลง conn_log เป็น batch — คืนจำนวนแถวที่เขียนสำเร็จ"""
    from datetime import datetime

    from common.db import get_conn

    rows = []
    unmapped = 0
    for r in records:
        mac = mac_cache.get(r.src_ip)
        if not mac:
            log.warning("ไม่พบ MAC ของ %s — เก็บ conn_log โดยไม่ระบุตัวอุปกรณ์", r.src_ip)
            unmapped += 1
        rows.append((datetime.fromtimestamp(r.ts), mac, r.src_ip, r.src_port,
                     r.dst_ip, r.dst_port, r.proto, r.bytes_out, r.bytes_in))
    if not rows:
        return 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO conn_log (ts, mac, src_ip, src_port, dst_ip, dst_port, "
            "proto, bytes_out, bytes_in) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    if on_unmapped and unmapped:
        on_unmapped(unmapped)
    return len(rows)


def flush_buffer(buffer: list[ConnRecord], mac_cache: MacCache,
                 max_pending: int = MAX_PENDING_RECORDS,
                 telemetry: CollectorTelemetry | None = None) -> int:
    """
    พยายามเขียน buffer ลง DB -- คืนจำนวนแถวที่เขียนสำเร็จ (0 ถ้าล้มเหลว)

    N31: ของเดิมเรียก insert แล้ว `buffer.clear()` นอก try ทั้งที่คอมเมนต์เขียนว่า "จะลองใหม่
    รอบถัดไป" -> DB สะดุดแค่ครู่เดียว (เช่น MariaDB ถูกรีสตาร์ทตอนติดตั้ง ซึ่งเกิดขึ้นจริงเมื่อ
    2026-09-19) ข้อมูลจราจรช่วงนั้นหายถาวรโดยไม่มีใครรู้ ตอนนี้เก็บไว้ลองใหม่จริง ๆ และถ้า DB
    ล่มยาวจนเกินเพดาน จะทิ้งของเก่าสุดพร้อม **บันทึกไว้ว่าทิ้งไปกี่รายการ** ไม่ใช่หายเงียบ
    """
    if not buffer:
        return 0
    try:
        if telemetry:
            n = insert_conn_records(buffer, mac_cache, on_unmapped=telemetry.missing_mac)
        else:
            n = insert_conn_records(buffer, mac_cache)
    except Exception:
        log.exception("เขียน conn_log ไม่สำเร็จ — เก็บ %d รายการไว้ลองใหม่รอบถัดไป", len(buffer))
        if telemetry:
            telemetry.error("เขียน conn_log ไม่สำเร็จ")
        if len(buffer) > max_pending:
            dropped = len(buffer) - max_pending
            del buffer[:dropped]
            log.error("DB ล่มนานจนคิวเกิน %d รายการ — ทิ้งรายการเก่าสุด %d รายการ "
                     "(หลักฐานช่วงนั้นจะไม่ครบ)", max_pending, dropped)
            if telemetry:
                telemetry.drop(dropped)
        return 0
    buffer.clear()
    if telemetry:
        telemetry.write(n)
    return n


def _drain_stderr(stream, on_event_loss=None) -> None:  # pragma: no cover (thread I/O)
    """
    N31: อ่าน stderr ของ conntrack ตลอดเวลา 2 เหตุผล: (1) ถ้าไม่อ่าน ท่อจะเต็มแล้ว conntrack
    ค้าง = หยุดเก็บ log ทั้งระบบ (2) ข้อความ ENOBUFS คือสัญญาณว่าหลักฐานขาดหาย ต้องดังให้ได้ยิน
    """
    for line in stream:
        line = line.strip()
        if not line:
            continue
        if "ENOBUFS" in line:
            log.error("conntrack: %s -- เหตุการณ์บางส่วนถูกทิ้ง conn_log ช่วงนี้ไม่ครบ", line)
            if on_event_loss:
                on_event_loss(line)
        else:
            log.warning("conntrack: %s", line)


def _record_event_loss(detail: str, cooldown_seconds: int = 300,
                       _last: list[float] = []) -> None:  # pragma: no cover (ต้องมี DB)
    """บันทึกลง audit_log ว่ามีช่วงที่เก็บ log ได้ไม่ครบ -- หลักฐานความซื่อสัตย์ของระบบเอง
    ตาม ม.26 ดีกว่าปล่อยให้ข้อมูลขาดไปเงียบ ๆ · จำกัดความถี่กันถม audit_log"""
    now = time.time()
    if _last and now - _last[-1] < cooldown_seconds:
        return
    _last.append(now)
    try:
        from common import audit
        audit.log(audit.LOG_GAP, target="conn_log", detail=detail[:200])
    except Exception:
        log.exception("บันทึก audit_log เรื่องเหตุการณ์ที่หายไม่สำเร็จ")


def _enlarge_pipe(stream, target: int = PIPE_BUFFER_BYTES) -> int:  # pragma: no cover (ขึ้นกับ OS)
    """
    N39: ขยายท่อระหว่าง conntrack กับตัวเรา (ปริยาย 64 KB ซึ่งเต็มได้ในชุดเดียว)
    ถ้าเคอร์เนลไม่ยอม (เกิน `/proc/sys/fs/pipe-max-size`) ให้ทำงานต่อด้วยขนาดเดิม
    ไม่ใช่ล้มทั้งบริการ -- เป็นการปรับให้ทนทานขึ้น ไม่ใช่เงื่อนไขที่ขาดไม่ได้
    """
    try:
        import fcntl
        return fcntl.fcntl(stream.fileno(), F_SETPIPE_SZ, target)
    except Exception as exc:
        log.warning("ขยายบัฟเฟอร์ท่อเป็น %d ไบต์ไม่สำเร็จ (%s) — ใช้ขนาดปริยายต่อไป", target, exc)
        return 0


def run_forever(batch_size: int = 100, flush_interval: float = 5.0) -> None:  # pragma: no cover
    """
    รันจริงบน gateway: เปิด `conntrack -E` เป็น subprocess แล้วแยกเป็น 3 ส่วนที่ไม่บล็อกกัน
    (N31) -- เดิมอ่านและเขียน DB อยู่ในลูปเดียวกัน ระหว่างที่รอ DB ท่อจากเคอร์เนลจะตันจนเกิด
    ENOBUFS และเหตุการณ์ถูกทิ้ง:
      1. เธรดอ่าน stdout  -> โยนเข้าคิว (ต้องว่างตลอด)
      2. เธรดอ่าน stderr  -> log คำเตือน ENOBUFS + บันทึกลง audit_log
      3. ลูปหลัก          -> ดึงจากคิวมาเขียน DB เป็น batch
    """
    mac_cache = MacCache()
    telemetry = CollectorTelemetry("conn")
    buffer: list[ConnRecord] = []
    events: queue.Queue = queue.Queue(maxsize=EVENT_QUEUE_MAX)
    overflow = [0]
    last_flush = time.time()

    cmd = ["conntrack", "-E", "-o", "timestamp,extended", "-e", "DESTROY",
           "--buffer-size", str(NETLINK_BUFFER_BYTES)]
    log.info("เริ่ม conn_collector: %s", " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _enlarge_pipe(proc.stdout)

    def _read_stdout() -> None:
        # N39: เธรดนี้ต้อง "โง่และเร็วที่สุด" -- หน้าที่เดียวคือดูดข้อมูลออกจากท่อ
        # ของเคอร์เนลให้ทัน ของเดิมแปลงบรรทัดเป็น record ตรงนี้ด้วย ซึ่งช้าพอที่จะทำให้
        # ท่อตันตอนที่ conntrack ปล่อยเหตุการณ์มาเป็นชุดใหญ่พร้อมกัน (เกิดจากการเก็บกวาด
        # รายการหมดอายุ ซึ่งปล่อยทีละหลายร้อยรายการในมิลลิวินาทีเดียว) -> ENOBUFS -> หลักฐานหาย
        # วัดจริงแล้วหาย 17 จาก 300 การเชื่อมต่อ (5.7%) เทียบกับตัวอ้างอิงที่รันคู่ขนาน
        for line in proc.stdout:  # type: ignore[union-attr]
            try:
                events.put_nowait(line)
            except queue.Full:
                overflow[0] += 1

    stdout_thread = threading.Thread(target=_read_stdout, daemon=True, name="conntrack-stdout")
    stderr_thread = threading.Thread(target=_drain_stderr, args=(proc.stderr, _record_event_loss),
                                     daemon=True, name="conntrack-stderr")
    stdout_thread.start()
    stderr_thread.start()

    try:
        reported_overflow = 0
        while proc.poll() is None:
            telemetry.heartbeat()
            if not stdout_thread.is_alive() or not stderr_thread.is_alive():
                raise RuntimeError("conntrack reader thread หยุดทำงาน")
            try:
                # N39: แปลงบรรทัดเป็น record ตรงนี้ (ลูปหลัก) แทนที่จะทำในเธรดอ่าน
                rec = parse_conntrack_line(events.get(timeout=flush_interval))
                if rec:
                    buffer.append(rec)
                    telemetry.event()
            except queue.Empty:
                pass
            if overflow[0] != reported_overflow:
                lost = overflow[0] - reported_overflow
                reported_overflow = overflow[0]
                log.error("log_gap conn_log: stdout queue เต็ม ทิ้ง %d เหตุการณ์", lost)
                telemetry.drop(lost)
                _record_event_loss(f"conntrack stdout queue full, dropped={lost}")
            now = time.time()
            if len(buffer) >= batch_size or (buffer and now - last_flush >= flush_interval):
                n = flush_buffer(buffer, mac_cache, telemetry=telemetry)
                log.debug("บันทึก conn_log %d แถว", n)
                last_flush = now
        log.error("conntrack หยุดทำงาน (exit %s) — cafe-logger จะถูก systemd รีสตาร์ทให้",
                 proc.returncode)
        raise RuntimeError(f"conntrack หยุดทำงาน (exit {proc.returncode})")
    finally:
        flush_buffer(buffer, mac_cache, telemetry=telemetry)
        proc.terminate()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    run_forever()
