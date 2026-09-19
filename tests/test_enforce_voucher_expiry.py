"""T-Enforce — tools/enforce_voucher_expiry.py (แก้บั๊ก H3/M1/M2 พร้อมกัน)"""
import contextlib
from datetime import datetime, timedelta

import pytest

from tools import enforce_voucher_expiry as ev


def test_expire_stale_vouchers_calls_correct_sql():
    calls = []

    def fake_exec(sql, args=()):
        calls.append(" ".join(sql.split()))
        return 3

    n = ev.expire_stale_vouchers(fake_exec)
    assert n == 3
    assert "UPDATE voucher SET status='expired'" in calls[0]
    assert "status='active'" in calls[0]
    assert "valid_until < NOW()" in calls[0]


def test_mark_used_up_vouchers_only_touches_vouchers_with_quota():
    calls = []

    def fake_exec(sql, args=()):
        calls.append(" ".join(sql.split()))
        return 1

    ev.mark_used_up_vouchers(fake_exec)
    assert "quota_mb IS NOT NULL" in calls[0]
    assert "used_mb >= quota_mb" in calls[0]


def test_sum_session_traffic_bytes_sums_conn_log():
    def fake_query_one(sql, args=()):
        assert args[0] == "AA:BB:CC:DD:EE:01"
        return {"bo": 12345, "bi": 67890}

    bo, bi = ev.sum_session_traffic_bytes(fake_query_one, "AA:BB:CC:DD:EE:01", datetime.now())
    assert (bo, bi) == (12345, 67890)


def test_sum_session_traffic_bytes_handles_no_rows():
    bo, bi = ev.sum_session_traffic_bytes(lambda *a: None, "AA:BB:CC:DD:EE:01", datetime.now())
    assert (bo, bi) == (0, 0)


def test_close_session_writes_bytes_and_bumps_used_mb():
    calls = []

    def fake_exec(sql, args=()):
        calls.append((" ".join(sql.split()), args))
        return 1

    ev.close_session(fake_exec, session_id=42, voucher_id=7,
                     bytes_out=3_000_000, bytes_in=2_000_000)
    assert len(calls) == 2
    assert calls[0][0].startswith("UPDATE portal_session SET ended_at=NOW()")
    assert calls[0][1] == ("voucher_expired", 3_000_000, 2_000_000, 42)  # default voucher_status="expired"
    assert calls[1][0].startswith("UPDATE voucher SET used_mb = used_mb +")
    assert calls[1][1] == (5, 7)  # (3MB+2MB) รวม 5MB


def test_close_session_maps_terminate_cause_from_voucher_status():
    """
    บั๊กเดิม (พบตอนตรวจทานรอบ 2): terminate_cause เคยตั้งเป็น 'voucher_expired' ตายตัว
    แม้ voucher จะถูกพนักงานยกเลิก (revoked) หรือใช้ครบโควต้า (used_up) -- ระบุสาเหตุผิด
    ในหลักฐานตาม ม.26 ต้องแมปจาก voucher.status จริง
    """
    calls = []

    def fake_exec(sql, args=()):
        calls.append((" ".join(sql.split()), args))
        return 1

    ev.close_session(fake_exec, session_id=1, voucher_id=1,
                     bytes_out=0, bytes_in=0, voucher_status="revoked")
    assert calls[0][1][0] == "voucher_revoked"

    calls.clear()
    ev.close_session(fake_exec, session_id=1, voucher_id=1,
                     bytes_out=0, bytes_in=0, voucher_status="used_up")
    assert calls[0][1][0] == "quota_exceeded"


def test_close_session_skips_voucher_update_when_zero_bytes():
    calls = []

    def fake_exec(sql, args=()):
        calls.append(sql)
        return 1

    ev.close_session(fake_exec, session_id=1, voucher_id=1, bytes_out=0, bytes_in=0)
    assert len(calls) == 1, "ไม่ต้องยิง UPDATE voucher ถ้าไม่มีทราฟฟิกเพิ่ม (delta=0)"


def test_deauth_mac_returns_false_when_ndsctl_missing(monkeypatch):
    monkeypatch.setattr(ev.shutil, "which", lambda _: None)
    assert ev.deauth_mac("AA:BB:CC:DD:EE:01") is False


def test_deauth_mac_returns_true_on_success(monkeypatch):
    monkeypatch.setattr(ev.shutil, "which", lambda _: "/usr/bin/ndsctl")

    class FakeResult:
        returncode = 0
        stderr = b""

    monkeypatch.setattr(ev.subprocess, "run", lambda *a, **kw: FakeResult())
    assert ev.deauth_mac("AA:BB:CC:DD:EE:01") is True


def test_deauth_mac_returns_false_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(ev.shutil, "which", lambda _: "/usr/bin/ndsctl")

    class FakeResult:
        returncode = 1
        stderr = b"no such client"

    monkeypatch.setattr(ev.subprocess, "run", lambda *a, **kw: FakeResult())
    assert ev.deauth_mac("AA:BB:CC:DD:EE:01") is False


# ---------------------------------------------------------------- run() end-to-end
class _FakeCursor:
    def __init__(self, state):
        self.state = state
        self.rowcount = 0
        self._result = None

    def execute(self, sql, args=()):
        s = " ".join(sql.split())
        if s.startswith("UPDATE voucher SET status='expired'"):
            self.rowcount = self.state["expire_count"]
        elif s.startswith("SELECT ps.id, ps.mac"):
            self._result = self.state["to_close"]
        elif s.startswith("SELECT COALESCE(SUM(bytes_out)"):
            self._result = {"bo": 1_000_000, "bi": 1_000_000}
        elif s.startswith("UPDATE portal_session SET ended_at"):
            self.state["closed"].append(args)
            self.rowcount = 1
        elif s.startswith("UPDATE voucher SET used_mb"):
            self.state["used_mb_bumped"].append(args)
            self.rowcount = 1
        elif s.startswith("UPDATE voucher SET status='used_up'"):
            self.rowcount = self.state["used_up_count"]
        else:
            raise AssertionError(f"ไม่รู้จัก SQL: {s[:80]}")

    def fetchone(self):
        return self._result

    def fetchall(self):
        return self._result

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_run_end_to_end_closes_expired_sessions_and_skips_deauth_when_disabled(monkeypatch):
    state = dict(
        expire_count=2,
        to_close=[{"id": 1, "mac": "AA:BB:CC:DD:EE:01", "voucher_id": 10,
                  "started_at": datetime.now() - timedelta(hours=1),
                  "voucher_status": "expired"}],
        closed=[], used_mb_bumped=[], used_up_count=0,
    )

    class FakeConn:
        def cursor(self):
            return _FakeCursor(state)

    import common.db as db
    monkeypatch.setattr(db, "get_conn", lambda: contextlib.nullcontext(FakeConn()))

    summary = ev.run(deauth=False)
    assert summary.expired_vouchers == 2
    assert summary.sessions_closed == 1
    assert summary.deauth_ok == 0 and summary.deauth_failed == 0, \
        "deauth=False ต้องไม่เรียก ndsctl เลย"
    assert len(state["closed"]) == 1
    assert len(state["used_mb_bumped"]) == 1


# ============== N22: ndsctl ต้องรันด้วยสิทธิ์ root ไม่งั้นเพิกถอน voucher แล้วตัดคนไม่ออกจริง
def _fake_run(captured, returncode=0):
    class FakeResult:
        pass
    FakeResult.returncode = returncode
    FakeResult.stderr = b""

    def run(cmd, **kw):
        captured.append(cmd)
        return FakeResult()
    return run


def test_deauth_mac_runs_ndsctl_directly_when_already_root(monkeypatch):
    monkeypatch.setattr(ev.shutil, "which", lambda _: "/usr/bin/ndsctl")
    monkeypatch.setattr(ev, "_running_as_root", lambda: True)
    captured = []
    monkeypatch.setattr(ev.subprocess, "run", _fake_run(captured))

    assert ev.deauth_mac("AA:BB:CC:DD:EE:01") is True
    assert captured == [["ndsctl", "deauth", "aa:bb:cc:dd:ee:01"]],         "openNDS เทียบ MAC แบบ case-sensitive และใช้ตัวพิมพ์เล็กเสมอ"


def test_deauth_mac_adds_sudo_when_not_root(monkeypatch):
    """รันเป็น cafewifi ตรง ๆ จะอ่าน /etc/config/opennds ไม่ได้และต่อ /tmp/ndsctl.sock ไม่ได้
    (ยืนยันบน Pi จริง 2026-09-16: exit 3 ทุกครั้ง) จึงต้องยกสิทธิ์ก่อนเสมอ"""
    monkeypatch.setattr(ev.shutil, "which", lambda _: "/usr/bin/ndsctl")
    monkeypatch.setattr(ev, "_running_as_root", lambda: False)
    captured = []
    monkeypatch.setattr(ev.subprocess, "run", _fake_run(captured))

    assert ev.deauth_mac("AA:BB:CC:DD:EE:01") is True
    assert captured == [["sudo", "-n", "ndsctl", "deauth", "aa:bb:cc:dd:ee:01"]]


def test_deauth_failure_is_logged_as_error_not_warning(monkeypatch, caplog):
    """deauth ล้มเหลว = ลูกค้าที่ถูกตัดสิทธิ์ยังใช้เน็ตได้จริง ไม่ใช่แค่ตัวเลขใน DB เพี้ยน
    ระดับ log จึงต้องเป็น ERROR ให้เห็นชัด (ของเดิมเป็น warning เลยถูกมองข้าม)"""
    import logging
    monkeypatch.setattr(ev.shutil, "which", lambda _: "/usr/bin/ndsctl")
    monkeypatch.setattr(ev, "_running_as_root", lambda: True)
    monkeypatch.setattr(ev.subprocess, "run", _fake_run([], returncode=3))

    with caplog.at_level(logging.DEBUG):
        assert ev.deauth_mac("AA:BB:CC:DD:EE:01") is False

    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors, "ต้อง log ระดับ ERROR อย่างน้อยหนึ่งรายการ"
    assert "ยังออกเน็ตได้อยู่" in errors[0].getMessage()


def _run_with_fake_db(monkeypatch, deauth_succeeds: bool):
    state = dict(
        expire_count=0,
        to_close=[{"id": 1, "mac": "AA:BB:CC:DD:EE:01", "voucher_id": 10,
                  "started_at": datetime.now() - timedelta(hours=1),
                  "voucher_status": "revoked"}],
        closed=[], used_mb_bumped=[], used_up_count=0,
    )

    class FakeConn:
        def cursor(self):
            return _FakeCursor(state)

    import common.db as db
    monkeypatch.setattr(db, "get_conn", lambda: contextlib.nullcontext(FakeConn()))
    monkeypatch.setattr(ev, "deauth_mac", lambda mac: deauth_succeeds)
    return ev.run(deauth=True), state


def test_run_keeps_session_open_when_deauth_fails_so_next_run_retries(monkeypatch):
    """ถ้าตัดที่ openNDS ไม่สำเร็จ ลูกค้ายังต่อเน็ตอยู่จริง ห้ามปิดแถวในฐานข้อมูล ไม่งั้น
    คิวรีรอบถัดไป (หาเฉพาะ ended_at IS NULL) จะมองไม่เห็นแถวนี้อีกเลย = ใช้เน็ตต่อได้ตลอดไป
    โดยไม่มีการลองตัดซ้ำ -- พบจากการทดสอบบน Pi จริง 2026-09-16"""
    summary, state = _run_with_fake_db(monkeypatch, deauth_succeeds=False)

    assert summary.deauth_failed == 1
    assert summary.sessions_closed == 0, "นับเฉพาะที่ปิดจริง ไม่ใช่จำนวนที่ตั้งใจจะปิด"
    assert state["closed"] == [], "ห้ามปิด session ที่ยังตัดไม่ออกจริง"


def test_run_closes_session_when_deauth_succeeds(monkeypatch):
    summary, state = _run_with_fake_db(monkeypatch, deauth_succeeds=True)

    assert summary.deauth_ok == 1
    assert summary.sessions_closed == 1
    assert len(state["closed"]) == 1


# ============== N28: ลูกค้าไม่อยู่ใน openNDS แล้ว (เดินออกไป / idle timeout) ต้องนับว่าตัดสำเร็จ
def test_deauth_counts_client_already_gone_as_success(monkeypatch):
    """ยืนยันบน Pi จริง: `ndsctl deauth <mac>` ของเครื่องที่ไม่อยู่แล้วได้ stdout
    "Client ... not found." exit 1 -- ถ้านับเป็นล้มเหลว N22 จะเว้น session ไว้ตลอดกาล"""
    monkeypatch.setattr(ev.shutil, "which", lambda _: "/usr/bin/ndsctl")
    monkeypatch.setattr(ev, "_running_as_root", lambda: True)

    class FakeResult:
        returncode = 1
        stdout = b"Client aa:bb:cc:dd:ee:01 not found."
        stderr = b""

    monkeypatch.setattr(ev.subprocess, "run", lambda *a, **kw: FakeResult())
    assert ev.deauth_mac("AA:BB:CC:DD:EE:01") is True


def test_deauth_other_failures_still_count_as_failure(monkeypatch):
    """ต้องไม่กลืนความล้มเหลวจริง เช่น permission denied แบบที่เจอใน N22"""
    monkeypatch.setattr(ev.shutil, "which", lambda _: "/usr/bin/ndsctl")
    monkeypatch.setattr(ev, "_running_as_root", lambda: True)

    class FakeResult:
        returncode = 3
        stdout = b""
        stderr = b"cat: /etc/config/opennds: Permission denied"

    monkeypatch.setattr(ev.subprocess, "run", lambda *a, **kw: FakeResult())
    assert ev.deauth_mac("AA:BB:CC:DD:EE:01") is False
