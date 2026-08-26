"""T-Logger — conn_collector / dns_collector / integrity (เฉพาะส่วนที่ทดสอบได้โดยไม่ต้องมีฮาร์ดแวร์จริง)"""
import gzip
from datetime import datetime

import pytest

from logger.conn_collector import ConnRecord, parse_conntrack_line
from logger.dns_collector import DnsCorrelator, parse_dnsmasq_line, parse_syslog_timestamp
from logger.integrity import (MemoryManifestStore, sha256_file, seal_directory,
                              verify_chain)
from logger.netutil import MacCache, resolve_mac

# ---------------------------------------------------------------- conntrack
NEW_LINE = ("[1692702000.1] [NEW] tcp 6 120 SYN_SENT src=10.10.0.105 dst=93.184.216.34 "
           "sport=51322 dport=443 [UNREPLIED] src=93.184.216.34 dst=10.10.0.105 "
           "sport=443 dport=51322")
DESTROY_TCP = ("[1692702005.9] [DESTROY] tcp 6 src=10.10.0.105 dst=93.184.216.34 "
              "sport=51322 dport=443 packets=12 bytes=1400 src=93.184.216.34 "
              "dst=10.10.0.105 sport=443 dport=51322 packets=9 bytes=8200 [ASSURED]")
DESTROY_UDP = ("[1692702010.0] [DESTROY] udp 17 src=10.10.0.108 dst=8.8.8.8 "
              "sport=54000 dport=53 packets=1 bytes=60 src=8.8.8.8 dst=10.10.0.108 "
              "sport=53 dport=54000 packets=1 bytes=120")


def test_new_event_is_ignored():
    assert parse_conntrack_line(NEW_LINE) is None, "เก็บเฉพาะ DESTROY (connection จบแล้ว) เท่านั้น"


def test_destroy_tcp_parsed_correctly():
    r = parse_conntrack_line(DESTROY_TCP)
    assert r == ConnRecord(ts=1692702005.9, proto="tcp", src_ip="10.10.0.105",
                           src_port=51322, dst_ip="93.184.216.34", dst_port=443,
                           bytes_out=1400, bytes_in=8200)


def test_uses_original_direction_not_reply_direction():
    r = parse_conntrack_line(DESTROY_TCP)
    # ต้องเป็น IP/port ของ "ต้นทาง" (บล็อกแรก) ไม่ใช่ของทิศทางย้อนกลับ (บล็อกที่สอง)
    assert r.src_ip == "10.10.0.105" and r.dst_ip == "93.184.216.34"


def test_udp_and_no_ports_for_icmp():
    r = parse_conntrack_line(DESTROY_UDP)
    assert r.proto == "udp" and r.src_port == 54000


def test_garbage_and_empty_lines_ignored():
    assert parse_conntrack_line("") is None
    assert parse_conntrack_line("not conntrack output at all") is None


def test_bytes_default_to_zero_without_extended_accounting():
    line = "[1.0] [DESTROY] tcp 6 src=1.2.3.4 dst=5.6.7.8 sport=1 dport=2"
    r = parse_conntrack_line(line)
    assert r.bytes_out == 0 and r.bytes_in == 0


# ---------------------------------------------------------------- dnsmasq
NOW = datetime(2026, 8, 22, 12, 0, 0)


def test_parse_query_line():
    ev = parse_dnsmasq_line("Aug 22 10:15:32 dnsmasq[1234]: query[A] example.com from 10.10.0.105", NOW)
    assert ev.__class__.__name__ == "DnsQueryEvent"
    assert ev.qname == "example.com" and ev.client_ip == "10.10.0.105" and ev.qtype == "A"


def test_parse_reply_and_cached_lines():
    r1 = parse_dnsmasq_line("Aug 22 10:15:33 dnsmasq[1234]: reply example.com is 93.184.216.34", NOW)
    r2 = parse_dnsmasq_line("Aug 22 10:15:33 dnsmasq[1234]: cached example.com is 93.184.216.34", NOW)
    assert r1.answer == "93.184.216.34" and r2.answer == "93.184.216.34"


def test_forwarded_line_is_ignored():
    assert parse_dnsmasq_line("Aug 22 10:15:32 dnsmasq[1234]: forwarded example.com to 1.1.1.1", NOW) is None


def test_year_rollback_for_old_timestamps():
    # สถานการณ์จริง: อ่าน log เก่าตอนต้นปีใหม่ (now = 2 ม.ค. 2026) ที่มีบรรทัดของ
    # "31 ธ.ค." (ปี 2025) ค้างอยู่ — ถ้าเดาว่าเป็นปีปัจจุบัน (2026) จะกลายเป็นอนาคต ต้องถอยปีให้
    early_jan = datetime(2026, 1, 2, 8, 0, 0)
    ts = parse_syslog_timestamp("Dec 31 23:59:00", early_jan)
    assert ts.year == 2025, "31 ธ.ค. ที่ดูเหมือนอยู่ในอนาคตเมื่อเทียบกับ now ต้องถูกตีความเป็นปีก่อน"


def test_correlator_matches_query_with_reply():
    c = DnsCorrelator()
    assert c.feed_line("Aug 22 10:15:32 dnsmasq[1234]: query[A] example.com from 10.10.0.105", NOW) is None
    row = c.feed_line("Aug 22 10:15:33 dnsmasq[1234]: reply example.com is 93.184.216.34", NOW)
    assert row == dict(ts=NOW.replace(hour=10, minute=15, second=32), client_ip="10.10.0.105",
                       qname="example.com", qtype="A", answer="93.184.216.34")


def test_correlator_ignores_orphan_reply():
    c = DnsCorrelator()
    assert c.feed_line("Aug 22 10:15:50 dnsmasq[1234]: reply orphan.com is 1.2.3.4", NOW) is None


def test_correlator_memory_is_bounded():
    c = DnsCorrelator(max_pending=3)
    for i in range(10):
        c.feed_line(f"Aug 22 10:15:{i:02d} dnsmasq[1]: query[A] q{i}.com from 10.0.0.1", NOW)
    assert len(c._pending) <= 3


# ---------------------------------------------------------------- integrity / hash chain
def test_sha256_file_plain_and_gz_match_same_content(tmp_path):
    content = b"log content for testing\n" * 100
    plain = tmp_path / "a.log"
    plain.write_bytes(content)
    gz = tmp_path / "a.log.gz"
    with gzip.open(gz, "wb") as f:
        f.write(content)
    assert sha256_file(plain) == sha256_file(gz), "hash เนื้อหาต้องเหมือนกันไม่ว่าจะบีบอัดหรือไม่"


def test_seal_directory_builds_chain(tmp_path):
    (tmp_path / "day1.log").write_bytes(b"day 1 content")
    (tmp_path / "day2.log").write_bytes(b"day 2 content")
    store = MemoryManifestStore()

    sealed = seal_directory(tmp_path, store, patterns=("*.log",))
    assert len(sealed) == 2
    assert sealed[0].prev_sha256 is None, "ไฟล์แรกสุดไม่มี prev"
    assert sealed[1].prev_sha256 == sealed[0].sha256, "ไฟล์ถัดไปต้องอ้าง hash ไฟล์ก่อนหน้า"


def test_seal_directory_matches_real_logrotate_dateext_filenames(tmp_path):
    """
    บั๊กเดิม (C1): pattern default ("*.log.gz", "*.log") ไม่ตรงกับไฟล์ที่ install.sh
    logrotate สร้างจริงเลยสักไฟล์ เพราะตั้ง `dateext` + `dateformat -%Y-%m-%d` ไว้
    ชื่อไฟล์จริงจึงเป็น "dnsmasq.log-2026-08-25.gz" (delaycompress ทำให้รอบแรกยังไม่ .gz)
    ไม่ใช่ "dnsmasq.log.gz" แบบที่เทสต์เดิมสมมติ -- เทสต์นี้ใช้ชื่อไฟล์แบบจริงและไม่ระบุ
    patterns เอง (ใช้ default) เพื่อจับบั๊กนี้ไว้ไม่ให้กลับมาอีก
    """
    with gzip.open(tmp_path / "dnsmasq.log-2026-08-24.gz", "wb") as f:
        f.write(b"day 1 already compressed")
    (tmp_path / "dnsmasq.log-2026-08-25").write_bytes(b"day 2 not compressed yet (delaycompress)")
    store = MemoryManifestStore()

    sealed = seal_directory(tmp_path, store)  # ไม่ระบุ patterns -- ต้องใช้ default ได้ตรง
    assert len(sealed) == 2, "ต้องผนึกไฟล์แบบ dateext ของจริงได้ทั้งคู่ด้วย pattern default"


def test_seal_directory_is_idempotent(tmp_path):
    (tmp_path / "day1.log").write_bytes(b"content")
    store = MemoryManifestStore()
    seal_directory(tmp_path, store, patterns=("*.log",))
    sealed_again = seal_directory(tmp_path, store, patterns=("*.log",))
    assert sealed_again == [], "ไฟล์ที่ผนึกแล้วต้องไม่ถูกผนึกซ้ำ"
    assert len(store.all_entries()) == 1


def test_verify_chain_passes_on_untouched_files(tmp_path):
    (tmp_path / "day1.log").write_bytes(b"content 1")
    (tmp_path / "day2.log").write_bytes(b"content 2")
    store = MemoryManifestStore()
    seal_directory(tmp_path, store, patterns=("*.log",))
    assert verify_chain(store, tmp_path) == []


def test_verify_chain_detects_tampered_file(tmp_path):
    (tmp_path / "day1.log").write_bytes(b"original content")
    store = MemoryManifestStore()
    seal_directory(tmp_path, store, patterns=("*.log",))

    (tmp_path / "day1.log").write_bytes(b"TAMPERED content")  # แก้ไขย้อนหลัง
    issues = verify_chain(store, tmp_path)
    assert len(issues) == 1 and issues[0].kind == "hash_mismatch"


def test_verify_chain_detects_deleted_file(tmp_path):
    (tmp_path / "day1.log").write_bytes(b"content")
    store = MemoryManifestStore()
    seal_directory(tmp_path, store, patterns=("*.log",))
    (tmp_path / "day1.log").unlink()

    issues = verify_chain(store, tmp_path)
    assert len(issues) == 1 and issues[0].kind == "missing_file"


def test_verify_chain_detects_broken_link():
    """จำลอง manifest ที่ถูกแก้ prev_sha256 ตรง ๆ (เช่นมีคนไปแก้ DB โดยตรง)"""
    from logger.integrity import ManifestEntry
    store = MemoryManifestStore()
    store.add(ManifestEntry(filename="a.log", sha256="a" * 64, prev_sha256=None, size_bytes=1))
    store.add(ManifestEntry(filename="b.log", sha256="b" * 64, prev_sha256="WRONG", size_bytes=1))
    issues = verify_chain(store, store and __import__("pathlib").Path("/nonexistent"))
    kinds = {i.kind for i in issues}
    assert "chain_broken" in kinds


# ---------------------------------------------------------------- netutil
PROC_NET_ARP_SAMPLE = """IP address       HW type     Flags       HW address            Mask     Device
10.10.0.105      0x1         0x2         aa:bb:cc:dd:ee:ff     *        eth1
10.10.0.108      0x1         0x2         11:22:33:44:55:66     *        eth1
10.10.0.199      0x1         0x0         00:00:00:00:00:00     *        eth1
"""


def test_resolve_mac_from_arp_table(tmp_path):
    arp_file = tmp_path / "arp"
    arp_file.write_text(PROC_NET_ARP_SAMPLE)
    assert resolve_mac("10.10.0.105", arp_file) == "AA:BB:CC:DD:EE:FF"
    assert resolve_mac("10.10.0.999", arp_file) is None
    assert resolve_mac("10.10.0.199", arp_file) is None, "MAC ทั้งหมดเป็น 0 แปลว่ายังไม่ resolve จริง"


def test_mac_cache_reuses_within_ttl(tmp_path, monkeypatch):
    arp_file = tmp_path / "arp"
    arp_file.write_text(PROC_NET_ARP_SAMPLE)
    calls = {"n": 0}
    import logger.netutil as netutil
    real_resolve = netutil.resolve_mac

    def counting_resolve(ip, path):
        calls["n"] += 1
        return real_resolve(ip, path)

    monkeypatch.setattr(netutil, "resolve_mac", counting_resolve)
    cache = MacCache(ttl_seconds=10, arp_path=arp_file)
    cache.get("10.10.0.105", now=100.0)
    cache.get("10.10.0.105", now=105.0)  # ยังอยู่ใน TTL -> ไม่ควรอ่านไฟล์ซ้ำ
    cache.get("10.10.0.105", now=115.0)  # เกิน TTL -> อ่านใหม่
    assert calls["n"] == 2
