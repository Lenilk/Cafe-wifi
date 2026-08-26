"""
logger/run_all.py — entrypoint ของ cafe-logger.service (ตั้งค่าโดย install.sh)
รัน conn_collector และ dns_collector พร้อมกันเป็น thread, จับ SIGTERM ให้ปิดตัวนุ่มนวล

หมายเหตุ: ฟังก์ชันในไฟล์นี้เป็น "ตัวประกอบร่าง" ของสิ่งที่ทดสอบแยกไว้แล้วใน
conn_collector.py / dns_collector.py — ตัวไฟล์นี้เองไม่มี unit test เพราะต้องพึ่ง
conntrack binary + สิทธิ์ root + ไฟล์ log จริงบนเครื่อง (ทดสอบได้เฉพาะ Phase 4 บนฮาร์ดแวร์จริง)
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import threading

from . import conn_collector, dns_collector

log = logging.getLogger("cafe-wifi.logger")
_stop = threading.Event()


def _handle_signal(signum, frame):  # noqa: ARG001
    log.info("ได้รับสัญญาณ %s — กำลังปิด log collector", signum)
    _stop.set()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    log_dir = os.environ.get("LOG_DIR", "/var/log/cafe-wifi")
    dnsmasq_log = os.path.join(log_dir, "dnsmasq.log")

    threads = [
        threading.Thread(target=conn_collector.run_forever, name="conn_collector", daemon=True),
        threading.Thread(target=dns_collector.run_forever, args=(dnsmasq_log,),
                         name="dns_collector", daemon=True),
    ]
    for t in threads:
        t.start()
        log.info("เริ่ม thread %s", t.name)

    _stop.wait()
    log.info("ปิด cafe-logger เรียบร้อย")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
