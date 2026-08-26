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
from logger.netutil import read_arp_table

PROC_NET_ARP_SAMPLE = """IP address       HW type     Flags       HW address            Mask     Device
192.168.1.2      0x1         0x2         aa:bb:cc:dd:ee:01     *        eth0
192.168.1.1      0x1         0x2         aa:bb:cc:dd:ee:02     *        eth0
192.168.1.50     0x1         0x2         11:22:33:44:55:66     *        eth0
192.168.1.199    0x1         0x0         00:00:00:00:00:00     *        eth0
10.10.0.105      0x1         0x2         cc:dd:ee:ff:00:11     *        eth0
"""


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

    events = bypass_detector.run(uplink_network="192.168.1.0/24", arp_path=str(arp_file))
    assert events == [BypassEvent(ip="192.168.1.50", mac="11:22:33:44:55:66")]
