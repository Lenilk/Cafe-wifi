"""
T-Traffic — common/traffic.py

ย้ายมาจาก tools/enforce_voucher_expiry.py (แก้บั๊ก พบตอนตรวจทานรอบ 4: app/fas/app.py
เคย import ข้ามชั้นจาก tools/ ตรง ๆ) เทสต์เดิมที่คุมผ่าน tools.enforce_voucher_expiry
(re-export) ยังใช้ได้อยู่ -- ไฟล์นี้เทสต์โมดูลต้นทางโดยตรงเพิ่มเติม
"""
from datetime import datetime

from common.traffic import BYTES_PER_MB, sum_session_traffic_bytes


def test_bytes_per_mb_is_one_million():
    assert BYTES_PER_MB == 1_000_000


def test_sum_session_traffic_bytes_queries_conn_log_with_mac_and_started_at():
    calls = []

    def fake_query_one(sql, args=()):
        calls.append((" ".join(sql.split()), args))
        return {"bo": 42, "bi": 7}

    started = datetime(2026, 8, 1, 12, 0, 0)
    bo, bi = sum_session_traffic_bytes(fake_query_one, "AA:BB:CC:DD:EE:01", started)

    assert (bo, bi) == (42, 7)
    assert len(calls) == 1
    assert "FROM conn_log WHERE mac=%s AND ts >= %s" in calls[0][0]
    assert calls[0][1] == ("AA:BB:CC:DD:EE:01", started)


def test_sum_session_traffic_bytes_handles_no_matching_rows():
    bo, bi = sum_session_traffic_bytes(lambda *a: None, "AA:BB:CC:DD:EE:01", datetime.now())
    assert (bo, bi) == (0, 0)
