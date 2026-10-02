"""
T-BypassDetector — logger/bypass_detector.py (N10, CODING_BRIEF.md, T17)

PROJECT_PLAN.md §3.1.4 ชั้นที่ 4 วิเคราะห์ไว้เองว่า "ตรวจจับ + แจ้งเตือน ... ไม่ได้ป้องกัน
แต่มีคุณค่าเชิงวิชาการสูง" แต่ก่อนหน้านี้ไม่มีไฟล์นี้อยู่จริงเลย -- มีแผนจะทดสอบ T17 โดยไม่มีอะไร
ให้ทดสอบ ไฟล์นี้แบ่ง 3 ส่วน: (1) logger/netutil.py::read_arp_table() ตรง ๆ (2) ตรรกะล้วน ๆ ของ
find_bypass_devices() (3) run() ที่ต่อสาย DB/audit จริง (mock execute/audit)
"""
from __future__ import annotations

import pytest

from logger import bypass_detector
from logger.bypass_detector import BypassEvent, find_bypass_devices
from logger.netutil import active_arp_refresh, read_arp_table

PROC_NET_ARP_SAMPLE = """IP address       HW type     Flags       HW address            Mask     Device
192.168.1.2      0x1         0x2         aa:bb:cc:dd:ee:01     *        eth0
192.168.1.1      0x1         0x2         aa:bb:cc:dd:ee:02     *        eth0
192.168.1.50     0x1         0x2         11:22:33:44:55:66     *        eth0
192.168.1.199    0x1         0x0         00:00:00:00:00:00     *        eth0
10.10.0.105      0x1         0x2         cc:dd:ee:ff:00:11     *        eth0
"""


@pytest.fixture(autouse=True)
def no_real_ping_sweep(monkeypatch):
    """การทดสอบ run() ใช้ ARP fixture จึงไม่ควรยิง ping ไปเครือข่ายจริง"""
    monkeypatch.setattr("logger.netutil.active_arp_refresh", lambda network: None)


def test_active_arp_refresh_rejects_network_larger_than_23(monkeypatch):
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("ห้ามยิง ping"))
    with pytest.raises(ValueError, match="/23"):
        active_arp_refresh("192.168.0.0/22")


def test_active_arp_refresh_accepts_23_boundary(monkeypatch):
    import subprocess

    class FakeProcess:
        def wait(self, timeout):
            return 0

    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda args, **kwargs: calls.append(args) or FakeProcess())
    active_arp_refresh("192.168.0.0/23", batch_gap=0)
    assert len(calls) == 510


def test_run_disables_bypass_scan_for_large_uplink(monkeypatch, caplog):
    import logger.netutil as netutil

    monkeypatch.setattr(netutil, "active_arp_refresh", lambda network: pytest.fail("ห้ามสแกน"))
    assert bypass_detector.run(uplink_network="192.168.0.0/22") == []
    assert "ไม่มีผลตรวจจับ bypass" in caplog.text


# ================================================================== ส่วนที่ 1: netutil.read_arp_table()
def test_read_arp_table_returns_all_resolved_entries(tmp_path):
    arp_file = tmp_path / "arp"
    arp_file.write_text(PROC_NET_ARP_SAMPLE)
    table = read_arp_table(arp_file)
    assert table["192.168.1.2"] == "AA:BB:CC:DD:EE:01"
    assert table["192.168.1.1"] == "AA:BB:CC:DD:EE:02"
    assert table["192.168.1.50"] == "11:22:33:44:55:66"
    assert table["10.10.0.105"] == "CC:DD:EE:FF:00:11"


def test_read_arp_table_excludes_incomplete_entries(tmp_path):
    arp_file = tmp_path / "arp"
    arp_file.write_text(PROC_NET_ARP_SAMPLE)
    table = read_arp_table(arp_file)
    assert "192.168.1.199" not in table, "MAC เป็น 00:00:00:00:00:00 แปลว่ายังไม่ resolve จริง"


def test_read_arp_table_missing_file_returns_empty_dict(tmp_path):
    assert read_arp_table(tmp_path / "no-such-file") == {}


# ================================================================== ส่วนที่ 2: find_bypass_devices() ตรรกะล้วน ๆ
def test_finds_device_in_uplink_network_that_is_not_known():
    arp = {"192.168.1.2": "AA:BB:CC:DD:EE:01", "192.168.1.1": "AA:BB:CC:DD:EE:02",
          "192.168.1.50": "11:22:33:44:55:66"}
    known = {"192.168.1.2", "192.168.1.1"}  # Pi + เราเตอร์
    events = find_bypass_devices(arp, "192.168.1.0/24", known)
    assert events == [BypassEvent(ip="192.168.1.50", mac="11:22:33:44:55:66")]


def test_ignores_devices_outside_uplink_network():
    arp = {"192.168.1.2": "AA:BB:CC:DD:EE:01", "10.10.0.105": "CC:DD:EE:FF:00:11"}
    known = {"192.168.1.2"}
    events = find_bypass_devices(arp, "192.168.1.0/24", known)
    assert events == [], "10.10.0.0/24 คือวงลูกค้าปกติ ไม่ใช่วง uplink ไม่ควรถูกนับเป็น bypass"


def test_known_ips_never_flagged_even_if_mac_looks_odd():
    arp = {"192.168.1.2": "AA:BB:CC:DD:EE:01", "192.168.1.1": "AA:BB:CC:DD:EE:02"}
    known = {"192.168.1.2", "192.168.1.1"}
    assert find_bypass_devices(arp, "192.168.1.0/24", known) == []


def test_no_bypass_returns_empty_list():
    arp = {"192.168.1.2": "AA:BB:CC:DD:EE:01"}
    known = {"192.168.1.2", "192.168.1.1"}
    assert find_bypass_devices(arp, "192.168.1.0/24", known) == []


def test_multiple_bypass_devices_sorted_by_ip():
    arp = {"192.168.1.2": "AA:BB:CC:DD:EE:01", "192.168.1.99": "99:99:99:99:99:99",
          "192.168.1.50": "11:22:33:44:55:66"}
    known = {"192.168.1.2", "192.168.1.1"}
    events = find_bypass_devices(arp, "192.168.1.0/24", known)
    assert [e.ip for e in events] == ["192.168.1.50", "192.168.1.99"]


def test_malformed_ip_in_arp_table_is_skipped_not_crashed():
    arp = {"192.168.1.2": "AA:BB:CC:DD:EE:01", "not-an-ip": "11:22:33:44:55:66"}
    known = {"192.168.1.2"}
    events = find_bypass_devices(arp, "192.168.1.0/24", known)
    assert events == []


# ================================================================== ส่วนที่ 3: run() ต่อสาย DB/audit จริง
@pytest.fixture
def arp_file(tmp_path):
    p = tmp_path / "arp"
    p.write_text(PROC_NET_ARP_SAMPLE)
    return p


def test_run_requires_uplink_network(monkeypatch, arp_file):
    monkeypatch.delenv("UPLINK_NETWORK", raising=False)
    with pytest.raises(RuntimeError, match="UPLINK_NETWORK"):
        bypass_detector.run(arp_path=str(arp_file))


def test_run_writes_bypass_alert_row_and_audit_log_per_event(monkeypatch, arp_file):
    calls = []
    import common.db as db
    monkeypatch.setattr(db, "execute", lambda sql, args=(): calls.append((sql, args)) or 1)
    monkeypatch.setattr(db, "query_one", lambda sql, args=(): None)  # ยังไม่เคยแจ้งเตือนมาก่อน

    events = bypass_detector.run(
        uplink_network="192.168.1.0/24",
        known_ips={"192.168.1.2", "192.168.1.1"},
        arp_path=str(arp_file),
    )

    assert events == [BypassEvent(ip="192.168.1.50", mac="11:22:33:44:55:66")]

    bypass_inserts = [c for c in calls if "insert into bypass_alert" in " ".join(c[0].split()).lower()]
    audit_inserts = [c for c in calls if "insert into audit_log" in " ".join(c[0].split()).lower()]

    assert len(bypass_inserts) == 1
    assert bypass_inserts[0][1] == ("192.168.1.50", "11:22:33:44:55:66")

    assert len(audit_inserts) == 1
    audit_args = audit_inserts[0][1]
    assert audit_args[1] == "bypass_detected"  # action
    assert audit_args[2] == "192.168.1.50"     # target
    assert "mac=11:22:33:44:55:66" in audit_args[4]  # detail


def test_run_writes_nothing_when_no_bypass_found(monkeypatch, tmp_path):
    clean_arp = tmp_path / "arp"
    clean_arp.write_text(
        "IP address       HW type     Flags       HW address            Mask     Device\n"
        "192.168.1.2      0x1         0x2         aa:bb:cc:dd:ee:01     *        eth0\n"
        "192.168.1.1      0x1         0x2         aa:bb:cc:dd:ee:02     *        eth0\n"
    )
    calls = []
    import common.db as db
    monkeypatch.setattr(db, "execute", lambda sql, args=(): calls.append((sql, args)) or 1)
    monkeypatch.setattr(db, "query_one", lambda sql, args=(): None)  # ยังไม่เคยแจ้งเตือนมาก่อน

    events = bypass_detector.run(uplink_network="192.168.1.0/24",
                                 known_ips={"192.168.1.2", "192.168.1.1"},
                                 arp_path=str(clean_arp))
    assert events == []
    assert calls == []


def test_run_reads_known_ips_from_env_when_not_passed(monkeypatch, arp_file):
    monkeypatch.setenv("UPLINK_IP", "192.168.1.2")
    monkeypatch.setenv("UPLINK_GW", "192.168.1.1")
    calls = []
    import common.db as db
    monkeypatch.setattr(db, "execute", lambda sql, args=(): calls.append((sql, args)) or 1)
    monkeypatch.setattr(db, "query_one", lambda sql, args=(): None)  # ยังไม่เคยแจ้งเตือนมาก่อน

    events = bypass_detector.run(uplink_network="192.168.1.0/24", arp_path=str(arp_file))
    assert events == [BypassEvent(ip="192.168.1.50", mac="11:22:33:44:55:66")]


# ============================================== ส่วนที่ 4: cooldown กันแถวซ้ำ (บั๊กที่เจอบน Pi จริง)
def test_run_skips_insert_when_same_device_alerted_within_cooldown(monkeypatch, arp_file):
    """อุปกรณ์เดิมที่ยังเสียบอยู่ต้องไม่ถูกบันทึกซ้ำทุกนาที -- ไม่งั้น audit_log (หลักฐานตาม
    กฎหมาย) ถูกถมด้วยแถวซ้ำจนหาเหตุการณ์จริงไม่เจอ"""
    calls = []
    import common.db as db
    monkeypatch.setattr(db, "execute", lambda sql, args=(): calls.append((sql, args)) or 1)
    monkeypatch.setattr(db, "query_one", lambda sql, args=(): {"id": 1})  # เพิ่งแจ้งเตือนไป

    events = bypass_detector.run(uplink_network="192.168.1.0/24",
                                 known_ips={"192.168.1.2", "192.168.1.1"},
                                 arp_path=str(arp_file))

    assert events == [BypassEvent(ip="192.168.1.50", mac="11:22:33:44:55:66")],         "ยังต้องคืนค่าว่าตรวจเจอ -- cooldown กันแค่การเขียนซ้ำ ไม่ใช่กันการตรวจจับ"
    assert calls == [], "ห้ามเขียน bypass_alert หรือ audit_log ซ้ำระหว่าง cooldown"


def test_cooldown_query_uses_both_ip_and_mac(monkeypatch, arp_file):
    """ต้องกันซ้ำต่อคู่ (ip, mac) ไม่ใช่ต่อ ip อย่างเดียว -- ถ้าเครื่องใหม่มาใช้ IP เดิม
    (อุปกรณ์คนละตัว) ต้องถือเป็นเหตุการณ์ใหม่ที่ต้องบันทึก"""
    seen = []
    import common.db as db
    monkeypatch.setattr(db, "execute", lambda sql, args=(): 1)
    monkeypatch.setattr(db, "query_one", lambda sql, args=(): seen.append((sql, args)) or None)

    bypass_detector.run(uplink_network="192.168.1.0/24",
                       known_ips={"192.168.1.2", "192.168.1.1"},
                       arp_path=str(arp_file), cooldown_minutes=30)

    assert len(seen) == 1
    sql, args = seen[0]
    assert "bypass_alert" in sql.lower()
    assert args == ("192.168.1.50", "11:22:33:44:55:66", 30)


def test_cooldown_zero_disables_dedupe(monkeypatch, arp_file):
    """ตั้ง 0 = ปิด cooldown บันทึกทุกรอบเหมือนเดิม (เผื่ออยากเก็บ raw ตอนทำการทดลองในเล่ม)"""
    calls = []
    queries = []
    import common.db as db
    monkeypatch.setattr(db, "execute", lambda sql, args=(): calls.append((sql, args)) or 1)
    monkeypatch.setattr(db, "query_one", lambda sql, args=(): queries.append(sql) or {"id": 1})

    bypass_detector.run(uplink_network="192.168.1.0/24",
                       known_ips={"192.168.1.2", "192.168.1.1"},
                       arp_path=str(arp_file), cooldown_minutes=0)

    assert queries == [], "cooldown=0 ต้องไม่ query หา alert เดิมเลย"
    assert len(calls) == 2, "ต้องเขียนทั้ง bypass_alert และ audit_log ตามปกติ"


def test_cooldown_minutes_defaults_from_env(monkeypatch, arp_file):
    seen = []
    import common.db as db
    monkeypatch.setenv("BYPASS_ALERT_COOLDOWN_MIN", "15")
    monkeypatch.setattr(db, "execute", lambda sql, args=(): 1)
    monkeypatch.setattr(db, "query_one", lambda sql, args=(): seen.append(args) or None)

    bypass_detector.run(uplink_network="192.168.1.0/24",
                       known_ips={"192.168.1.2", "192.168.1.1"},
                       arp_path=str(arp_file))

    assert seen[0][2] == 15
