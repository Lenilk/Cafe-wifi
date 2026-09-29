"""
tools/export_evidence.py — ส่งออกข้อมูลจราจร (conn_log/dns_log) เป็นหลักฐานตามคำสั่งเจ้าหน้าที่

ใช้งาน:
    python -m tools.export_evidence --mac AA:BB:CC:DD:EE:FF --from 2026-08-01 --to 2026-08-22
    python -m tools.export_evidence --natid 1234567890123 --from 2026-08-01 --to 2026-08-22

ทุกครั้งที่ export จะ:
  1. เขียนไฟล์ CSV (conn_log และ dns_log แยกไฟล์)
  2. คำนวณ SHA-256 ของแต่ละไฟล์ แล้วเขียน manifest .json คู่กัน (พิสูจน์ทีหลังว่าไฟล์ไม่ถูกแก้)
  3. บันทึก audit_log ว่าใคร export อะไร เมื่อไหร่ (สำคัญมากตาม PDPA — นี่คือการเข้าถึง
     ข้อมูลผู้ใช้จำนวนมากในครั้งเดียว ต้องมีร่องรอยเสมอ)
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

log = logging.getLogger("cafe-wifi.export")

CONN_FIELDS = ["ts", "mac", "src_ip", "src_port", "dst_ip", "dst_port", "proto", "bytes_out", "bytes_in"]
DNS_FIELDS = ["ts", "event_kind", "client_ip", "mac", "qname", "qtype", "answer"]


@dataclass(frozen=True)
class ExportedFile:
    path: Path
    sha256: str
    row_count: int


def rows_to_csv_text(rows: list[dict], fieldnames: list[str]) -> str:
    """แปลง list ของ dict เป็นข้อความ CSV — แยกจาก I/O เพื่อทดสอบง่าย"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_export_file(rows: list[dict], fieldnames: list[str], out_path: Path) -> ExportedFile:
    text = rows_to_csv_text(rows, fieldnames)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="")
    return ExportedFile(path=out_path, sha256=sha256_text(text), row_count=len(rows))


def build_manifest(files: list[ExportedFile], criteria: dict) -> dict:
    return {
        "generated_at": datetime.now().isoformat(),
        "criteria": criteria,
        "files": [{"filename": f.path.name, "sha256": f.sha256, "row_count": f.row_count}
                 for f in files],
        "note": "ตรวจสอบไฟล์ไม่ถูกแก้ไข: sha256sum <ชื่อไฟล์> แล้วเทียบกับค่าในนี้",
    }


def parse_range_end(value: str) -> datetime:
    """
    N32 (พบตอนทดสอบส่งออกหลักฐานบน Pi จริง 2026-09-20): ถ้าผู้ใช้ระบุวันสิ้นสุดเป็นวันที่เปล่า ๆ
    (YYYY-MM-DD) ให้หมายถึง **สิ้นวันนั้น** ไม่ใช่เที่ยงคืนต้นวัน

    ของเดิม `--to 2026-09-20` = 2026-09-20 00:00:00 ทำให้ข้อมูลของวันที่ 20 ทั้งวันไม่ติดมาใน
    ไฟล์หลักฐานเลย (เงียบ ๆ ไม่มี error) และขอข้อมูลวันเดียว (--from กับ --to วันเดียวกัน) ก็ถูก
    ปฏิเสธด้วย "วันที่สิ้นสุดต้องอยู่หลังวันที่เริ่มต้น" ทั้งที่เป็นคำขอที่พบบ่อยที่สุดจากเจ้าหน้าที่
    ถ้าระบุเวลามาด้วยจะใช้ตามที่ระบุ ไม่ไปยุ่ง
    """
    dt = datetime.fromisoformat(value)
    if len(value.strip()) == 10:  # "YYYY-MM-DD" ไม่มีส่วนเวลา
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return dt


def export(mac: str | None, start: datetime, end: datetime, out_dir: Path,
          query_conn_fn, query_dns_fn, staff_id: int | None = None) -> dict:
    if end <= start:
        raise ValueError("วันที่สิ้นสุดต้องอยู่หลังวันที่เริ่มต้น")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = (mac or "all").replace(":", "")
    conn_rows = query_conn_fn(mac, start, end)
    dns_rows = query_dns_fn(mac, start, end)

    conn_file = write_export_file(conn_rows, CONN_FIELDS, out_dir / f"conn_log_{tag}_{stamp}.csv")
    dns_file = write_export_file(dns_rows, DNS_FIELDS, out_dir / f"dns_log_{tag}_{stamp}.csv")

    criteria = dict(mac=mac, start=start.isoformat(), end=end.isoformat())
    manifest = build_manifest([conn_file, dns_file], criteria)
    manifest_path = out_dir / f"manifest_{tag}_{stamp}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    from common import audit
    audit.log(audit.EXPORT_LOG, staff_id=staff_id, target=mac or "ALL",
             detail=f"rows conn={len(conn_rows)} dns={len(dns_rows)} range={start}..{end}")

    return {"manifest_path": manifest_path, "conn_file": conn_file, "dns_file": dns_file}


def _cli() -> int:  # pragma: no cover
    import argparse

    from common.db import query_all

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mac", help="กรองเฉพาะ MAC นี้ (ไม่ใส่ = ทุกเครื่อง)")
    p.add_argument("--from", dest="start", required=True, help="YYYY-MM-DD")
    p.add_argument("--to", dest="end", required=True,
                  help="YYYY-MM-DD (นับถึงสิ้นวันนั้น) หรือระบุเวลาเองเป็น YYYY-MM-DDTHH:MM:SS")
    p.add_argument("--out", default="/var/log/cafe-wifi/exports")
    args = p.parse_args()

    start = datetime.fromisoformat(args.start)
    end = parse_range_end(args.end)

    def q_conn(mac, s, e):
        sql = "SELECT ts, mac, src_ip, src_port, dst_ip, dst_port, proto, bytes_out, bytes_in FROM conn_log WHERE ts BETWEEN %s AND %s"
        params = [s, e]
        if mac:
            sql += " AND mac = %s"; params.append(mac)
        return query_all(sql + " ORDER BY ts", tuple(params))

    def q_dns(mac, s, e):
        sql = "SELECT ts, event_kind, client_ip, mac, qname, qtype, answer FROM dns_log WHERE ts BETWEEN %s AND %s"
        params = [s, e]
        if mac:
            sql += " AND mac = %s"; params.append(mac)
        return query_all(sql + " ORDER BY ts", tuple(params))

    logging.basicConfig(level=logging.INFO)
    result = export(args.mac, start, end, Path(args.out), q_conn, q_dns)
    print(f"ส่งออกสำเร็จ: {result['manifest_path']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())
