"""
T-Traffic — common/traffic.py

ย้ายมาจาก tools/enforce_voucher_expiry.py (แก้บั๊ก พบตอนตรวจทานรอบ 4: app/fas/app.py
เคย import ข้ามชั้นจาก tools/ ตรง ๆ) เทสต์เดิมที่คุมผ่าน tools.enforce_voucher_expiry
(re-export) ยังใช้ได้อยู่ -- ไฟล์นี้เทสต์โมดูลต้นทางโดยตรงเพิ่มเติม
"""
from datetime import datetime, timedelta
import sqlite3

from common.traffic import BYTES_PER_MB, sum_session_traffic_bytes


def test_bytes_per_mb_is_one_million():
    assert BYTES_PER_MB == 1_000_000


def test_sum_session_traffic_bytes_queries_conn_log_with_authentication_boundary():
    calls = []

    def fake_query_one(sql, args=()):
        calls.append((" ".join(sql.split()), args))
        return {"bo": 42, "bi": 7}

    started = datetime(2026, 8, 1, 12, 0, 0)
    bo, bi = sum_session_traffic_bytes(fake_query_one, "AA:BB:CC:DD:EE:01", started)

    assert (bo, bi) == (42, 7)
    assert len(calls) == 1
    assert "FROM conn_log WHERE mac=%s AND ts > %s" in calls[0][0]
    assert calls[0][1] == ("AA:BB:CC:DD:EE:01", started)


def test_sum_session_traffic_bytes_ends_at_reauth_boundary():
    calls = []
    started = datetime(2026, 8, 1, 12, 0, 0)
    ended = datetime(2026, 8, 1, 13, 0, 0)

    def fake_query_one(sql, args=()):
        calls.append((" ".join(sql.split()), args))
        return {"bo": 10, "bi": 20}

    assert sum_session_traffic_bytes(fake_query_one, "AA:BB:CC:DD:EE:01", started, ended) == (10, 20)
    assert "ts > %s AND ts <= %s" in calls[0][0]
    assert calls[0][1] == ("AA:BB:CC:DD:EE:01", started, ended)


def test_adjacent_sessions_do_not_count_the_same_conn_log_row():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE conn_log (mac TEXT, ts TIMESTAMP, bytes_out INTEGER, bytes_in INTEGER)")
    first_auth = datetime(2026, 9, 30, 12, 0)
    reauth = first_auth + timedelta(minutes=5)
    mac = "AA:BB:CC:DD:EE:01"
    db.executemany("INSERT INTO conn_log VALUES (?,?,?,0)", [
        (mac, first_auth.isoformat(" "), 1_000_000),  # ตรงเวลาเปิดสิทธิ์: ไม่คิด
        (mac, (first_auth + timedelta(seconds=1)).isoformat(" "), 2_000_000),
        (mac, reauth.isoformat(" "), 3_000_000),      # รอยต่อ: ของ session เก่า
        (mac, (reauth + timedelta(seconds=1)).isoformat(" "), 7_000_000),
    ])

    def query_one(sql, args=()):
        values = tuple(value.isoformat(" ") if isinstance(value, datetime) else value
                       for value in args)
        row = db.execute(sql.replace("%s", "?"), values).fetchone()
        return dict(row) if row else None

    assert sum_session_traffic_bytes(query_one, mac, first_auth, reauth) == (5_000_000, 0)
    assert sum_session_traffic_bytes(query_one, mac, reauth) == (7_000_000, 0)
    db.close()


def test_sum_session_traffic_bytes_handles_no_matching_rows():
    bo, bi = sum_session_traffic_bytes(lambda *a: None, "AA:BB:CC:DD:EE:01", datetime.now())
    assert (bo, bi) == (0, 0)
