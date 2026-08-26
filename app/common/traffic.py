"""
common/traffic.py — รวมยอด traffic (bytes) ต่อ MAC จาก conn_log

แยกออกมาจาก tools/enforce_voucher_expiry.py (แก้บั๊ก พบตอนตรวจทานรอบ 4): เดิม
app/fas/app.py (service ที่ลูกค้าเข้าถึงได้โดยตรง) import ฟังก์ชันนี้จาก tools.* ซึ่งเป็นชั้น
CLI/batch-job สำหรับงานบำรุงรักษาเท่านั้น -- ผิดทิศทางการพึ่งพา (dependency direction) ทำให้
service หน้าบ้านผูกติดกับโมดูล CLI งานเบื้องหลังโดยไม่จำเป็น common/ คือชั้นที่ทั้ง app/ และ
tools/ พึ่งพาได้ทั้งคู่อยู่แล้ว (เหมือน crypto.py, db.py) จึงย้ายมาไว้ตรงนี้แทน
"""
from __future__ import annotations

BYTES_PER_MB = 1_000_000


def sum_session_traffic_bytes(query_one_fn, mac: str, started_at) -> tuple[int, int]:
    """รวม bytes_out/bytes_in จาก conn_log ของ mac นี้นับตั้งแต่ session เริ่ม"""
    row = query_one_fn(
        "SELECT COALESCE(SUM(bytes_out),0) AS bo, COALESCE(SUM(bytes_in),0) AS bi "
        "FROM conn_log WHERE mac=%s AND ts >= %s", (mac, started_at))
    if not row:
        return 0, 0
    return int(row["bo"]), int(row["bi"])
