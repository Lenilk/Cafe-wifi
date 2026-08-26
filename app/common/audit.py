"""common/audit.py — บันทึกร่องรอยการใช้งานที่มีผลทางกฎหมาย/PDPA"""
from __future__ import annotations

from . import db

# หมายเหตุ: import โมดูล `db` ทั้งก้อนแล้วเรียก db.execute(...) แบบ dynamic ตอนใช้งานจริง
# (ไม่ใช่ `from .db import execute` ที่ import ครั้งเดียวแล้วผูกชื่อตายตัว) เพราะถ้ามีการ
# สลับ implementation ของ db.execute ในภายหลัง (เช่น ห่อ retry logic, หรือใน unit test ที่
# monkeypatch แทนที่ด้วย fake) โค้ดจุดนี้ต้องเห็นเวอร์ชันล่าสุดเสมอ ไม่งั้น audit trail จะ
# เงียบ ๆ เขียนไปที่ implementation เก่าโดยไม่มีใครรู้ตัว — สำคัญมากเพราะนี่คือกลไกพิสูจน์
# การเข้าถึงข้อมูลอ่อนไหวตาม PDPA

# การกระทำที่ "ต้อง" บันทึกเสมอ
REVEAL_NATID = "reveal_natid"
ISSUE_VOUCHER = "issue_voucher"
REVOKE_VOUCHER = "revoke_voucher"
EXPORT_LOG = "export_log"
LOGIN_OK = "login_ok"
LOGIN_FAIL = "login_fail"
SETUP_ADMIN = "setup_admin"
DISK_ALERT = "disk_alert"  # N1 (CODING_BRIEF.md) -- ดิสก์เต็ม = log หยุดเขียน = ผิด ม.26
ERASE_CUSTOMER = "erase_customer"  # N6 (CODING_BRIEF.md) -- DSR: ลบข้อมูลรายบุคคลตามคำขอ (PDPA §6.2 ข้อ 6)


def log(action: str, staff_id: int | None = None, target: str = "",
        client_ip: str = "", detail: str = "") -> None:
    """ล้มเหลวเงียบ ๆ ไม่ได้ — แต่ก็ต้องไม่ทำให้ request หลักพัง"""
    try:
        db.execute(
            "INSERT INTO audit_log (staff_id, action, target, client_ip, detail) "
            "VALUES (%s, %s, %s, %s, %s)",
            (staff_id, action[:64], target[:128], client_ip[:45], detail),
        )
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).error("เขียน audit_log ไม่สำเร็จ: %s", exc)
