"""
T-Setup — First-run Setup Wizard (สร้างบัญชีผู้ดูแลระบบหลักผ่านหน้าเว็บ)

ใช้ฐานข้อมูลจำลองในหน่วยความจำ จึงรันได้โดยไม่ต้องมี MariaDB
"""
import contextlib
import os
import pathlib

import pytest

TOKEN = "b8f2c1d9e4a7361f0c5b2d8e93a41f6072ce5b1d4a8f3927"
GOOD_PW = "CafeWifi2026Secure"

STAFF: list[dict] = []
AUDIT: list[tuple] = []


class FakeCursor:
    def __init__(self):
        self.lastrowid = None
        self._rows: list[dict] = []

    def execute(self, sql, args=()):
        s = " ".join(sql.split()).lower()
        if s.startswith("select count(*) as n from staff"):
            self._rows = [{"n": len(STAFF)}]
        elif s.startswith("insert into staff"):
            STAFF.append({"id": len(STAFF) + 1, "username": args[0],
                          "password_hash": args[1], "display_name": args[2],
                          "role": "admin", "is_active": 1})
            self.lastrowid = STAFF[-1]["id"]
        elif s.startswith("insert into audit_log"):
            AUDIT.append(args)
            self.lastrowid = len(AUDIT)
        elif s.startswith("select id, username, password_hash"):
            self._rows = [r for r in STAFF if r["username"] == args[0]]
        else:
            self._rows = []

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def cursor(self):
        return FakeCursor()


@pytest.fixture
def client(tmp_path, monkeypatch):
    STAFF.clear()
    AUDIT.clear()
    monkeypatch.setenv("ETC_DIR", str(tmp_path))
    (tmp_path / "setup.token").write_text(TOKEN + "\n", encoding="utf-8")

    import common.db as db
    monkeypatch.setattr(db, "get_conn", lambda: contextlib.nullcontext(FakeConn()))

    def _run(sql, args=()):
        cur = FakeCursor()
        cur.execute(sql, args)
        return cur

    monkeypatch.setattr(db, "query_one", lambda s, a=(): _run(s, a).fetchone())
    monkeypatch.setattr(db, "query_all", lambda s, a=(): _run(s, a).fetchall())
    monkeypatch.setattr(db, "execute", lambda s, a=(): _run(s, a).lastrowid)

    import importlib
    admin_app = importlib.import_module("admin.app")
    importlib.reload(admin_app)
    admin_app.SETUP_TOKEN_FILE = tmp_path / "setup.token"
    admin_app.app.config.update(SESSION_COOKIE_SECURE=False, TESTING=True)
    c = admin_app.app.test_client()
    c.token_file = tmp_path / "setup.token"
    return c


def _post(c, **over):
    data = dict(token=TOKEN, username="admin", display_name="ผู้ดูแลระบบ",
                password=GOOD_PW, password_confirm=GOOD_PW)
    data.update(over)
    return c.post("/setup", data=data)


def test_all_pages_redirect_to_setup_before_first_account(client):
    for path in ("/", "/customers", "/issue"):
        r = client.get(path)
        assert r.status_code == 302 and "/setup" in r.headers["Location"], path


def test_setup_page_renders_form(client):
    html = client.get("/setup").get_data(as_text=True)
    assert 'name="token"' in html
    assert "ปิดตัวเองถาวร" in html


def test_wrong_token_creates_nothing(client):
    r = _post(client, token="wrong-token")
    assert r.status_code == 400
    assert "Setup Token ไม่ถูกต้อง" in r.get_data(as_text=True)
    assert STAFF == []


def test_weak_password_rejected(client):
    r = _post(client, password="admin123", password_confirm="admin123")
    assert r.status_code == 400
    assert STAFF == []


def test_mismatched_password_rejected(client):
    r = _post(client, password_confirm=GOOD_PW + "x")
    assert r.status_code == 400
    assert STAFF == []


def test_invalid_username_rejected(client):
    assert _post(client, username="ad min!").status_code == 400
    assert STAFF == []


def test_successful_setup(client):
    r = _post(client)
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert len(STAFF) == 1
    assert STAFF[0]["role"] == "admin"
    assert GOOD_PW not in STAFF[0]["password_hash"], "ต้องเก็บเป็น hash เท่านั้น"
    assert not client.token_file.exists(), "ต้องลบ setup.token ทิ้งอัตโนมัติ"
    assert any("setup_admin" in str(a) for a in AUDIT)


def test_setup_closes_permanently(client):
    _post(client)
    assert client.get("/setup").status_code == 410
    r = _post(client, username="attacker")
    assert r.status_code == 410
    assert len(STAFF) == 1, "ห้ามสร้างบัญชีที่สองผ่านหน้า setup"


def test_login_with_new_account(client):
    _post(client)
    assert client.post("/login", data=dict(username="admin", password=GOOD_PW)).status_code == 302
    assert client.post("/login", data=dict(username="admin", password="wrong-pass-123")).status_code == 401
