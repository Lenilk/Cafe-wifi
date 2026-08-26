"""logger/netutil.py — เครื่องมือช่วยเล็ก ๆ ที่ใช้ร่วมกันในตัวเก็บ log"""
from __future__ import annotations

import re
from pathlib import Path

_ARP_LINE = re.compile(
    r"^(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+\S+\s+\S+\s+(?P<mac>[0-9a-fA-F:]{17})\s"
)


def _iter_arp_entries(arp_path: str | Path):
    """แกะทุกแถวใน /proc/net/arp เป็น (ip, mac) -- ข้ามแถวที่ mac เป็น 00:00:00:00:00:00
    (incomplete entry ที่เคอร์เนลยังไม่ resolve จริง) ใช้ร่วมกันทั้ง resolve_mac() (หา MAC
    ของ IP เดียว) และ read_arp_table() (N10, CODING_BRIEF.md -- เฝ้าทั้งวงให้ bypass_detector.py)"""
    try:
        text = Path(arp_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines()[1:]:  # บรรทัดแรกคือหัวตาราง
        m = _ARP_LINE.match(line)
        if not m:
            continue
        mac = m.group("mac").upper()
        if mac != "00:00:00:00:00:00":
            yield m.group("ip"), mac


def resolve_mac(ip: str, arp_path: str | Path = "/proc/net/arp") -> str | None:
    """
    หา MAC address จาก IP โดยอ่านตาราง ARP ของเคอร์เนล (/proc/net/arp)
    คืน None ถ้าหาไม่เจอ (เช่นอุปกรณ์เพิ่งหลุดออกจาก ARP cache) — เรียกใหญ่ในโค้ดต้องรับมือ None ได้
    """
    for entry_ip, mac in _iter_arp_entries(arp_path):
        if entry_ip == ip:
            return mac
    return None


def read_arp_table(arp_path: str | Path = "/proc/net/arp") -> dict[str, str]:
    """คืน {ip: mac} ของทุกแถวใน ARP table ปัจจุบัน -- ต่างจาก resolve_mac() ที่หาแค่ IP เดียว
    ตัวนี้อ่านทั้งวงในครั้งเดียว (N10, CODING_BRIEF.md -- bypass_detector.py ใช้เฝ้าวง uplink ทั้งวง
    หา IP/MAC แปลกปลอมที่ไม่ใช่ Pi/เราเตอร์) ถ้า IP เดียวกันมีหลายแถว (ไม่ควรเกิดจริงในทางปฏิบัติ)
    จะเหลือแค่แถวสุดท้ายที่อ่านเจอ"""
    return dict(_iter_arp_entries(arp_path))


class MacCache:
    """แคช IP->MAC แบบง่าย กันอ่านไฟล์ /proc/net/arp ถี่เกินไปตอนมี event เยอะ ๆ"""

    def __init__(self, ttl_seconds: float = 5.0, arp_path: str | Path = "/proc/net/arp"):
        self.ttl = ttl_seconds
        self.arp_path = arp_path
        self._cache: dict[str, tuple[float, str | None]] = {}

    def get(self, ip: str, now: float | None = None) -> str | None:
        import time
        now = now if now is not None else time.time()
        hit = self._cache.get(ip)
        if hit and now - hit[0] < self.ttl:
            return hit[1]
        mac = resolve_mac(ip, self.arp_path)
        self._cache[ip] = (now, mac)
        return mac
