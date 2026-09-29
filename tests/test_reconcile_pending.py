"""Gateway confirmation must match state, IP, and a new gateway session."""
from datetime import datetime, timedelta

import tools.reconcile_pending as rp
from tools.reconcile_pending import confirmed_at


def test_confirmed_at_requires_fresh_gateway_session():
    now = datetime.now().replace(microsecond=0)
    client = dict(state="Authenticated", ip="10.10.0.105",
                  session_start=str(int(now.timestamp())))
    assert confirmed_at(client, "10.10.0.105", now) == now
    assert confirmed_at(client, "10.10.0.106", now) is None
    assert confirmed_at({**client, "state": "Preauthenticated"}, "10.10.0.105", now) is None
    assert confirmed_at({**client, "session_start": str(int((now - timedelta(minutes=5)).timestamp()))},
                        "10.10.0.105", now) is None
    assert confirmed_at({**client, "session_start": None}, "10.10.0.105", now) is None


class _FakeCursor:
    def __init__(self, pending):
        self.pending = pending
        self.executed = []
        self._last = ""

    def execute(self, sql, args=()):
        self.executed.append((sql, args))
        self._last = sql

    def fetchall(self):
        return self.pending if "ps.state='pending'" in self._last else []

    def fetchone(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self, cur):
        self.cur = cur

    def cursor(self):
        return self.cur

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _run(monkeypatch, row, clients):
    import tools.enforce_voucher_expiry as enforce
    cur = _FakeCursor([row])
    deauthed = []
    monkeypatch.setattr(rp, "gateway_clients", lambda: clients)
    monkeypatch.setattr(rp, "get_conn", lambda: _FakeConn(cur))
    monkeypatch.setattr(rp, "purge_orphan_claims", lambda: 0)
    monkeypatch.setattr(rp.audit, "log", lambda *a, **k: None)
    monkeypatch.setattr(enforce, "deauth_mac", lambda mac: deauthed.append(mac) or True)
    return rp.run(), cur.executed, deauthed


def _pending_row(now, pending_until):
    return dict(id=7, voucher_id=3, mac="aa:bb:cc:dd:ee:ff", ip="10.10.0.105",
                started_at=now - timedelta(seconds=180), pending_until=pending_until,
                status="active", valid_until=now + timedelta(hours=1))


def test_confirmed_near_deadline_is_promoted_not_timed_out(monkeypatch):
    """R2-08: openNDS เปิดสิทธิ์แล้วก่อน reconcile รอบถัดไป -> ต้อง promote ไม่ใช่ auth_timeout"""
    now = datetime.now().replace(microsecond=0)
    opened = now - timedelta(seconds=2)
    row = _pending_row(now, pending_until=now - timedelta(seconds=1))
    clients = {row["mac"]: dict(state="Authenticated", ip=row["ip"],
                                session_start=str(int(opened.timestamp())))}
    (promoted, expired), executed, deauthed = _run(monkeypatch, row, clients)
    assert (promoted, expired) == (1, 0)
    assert deauthed == []
    assert not any("auth_timeout" in sql for sql, _ in executed)
    # authenticated_at ต้องเป็นเวลาที่ openNDS เปิดสิทธิ์จริง ไม่ใช่ NOW() ตอน timer มาเจอ
    (sql, args), = [(s, a) for s, a in executed if "state='authenticated', authenticated_at" in s]
    assert "NOW()" not in sql
    assert args == (opened, row["id"])


def test_unconfirmed_past_deadline_still_times_out(monkeypatch):
    now = datetime.now().replace(microsecond=0)
    row = _pending_row(now, pending_until=now - timedelta(seconds=1))
    (promoted, expired), executed, deauthed = _run(monkeypatch, row, {})
    assert (promoted, expired) == (0, 1)
    assert deauthed == [row["mac"]]
    assert any("auth_timeout" in sql for sql, _ in executed)
