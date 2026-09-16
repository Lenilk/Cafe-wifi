"""
logger/integrity.py — hash chain รายวันของไฟล์ log เพื่อพิสูจน์ว่าไม่ถูกแก้ไขย้อนหลัง
(ตอบโจทย์ "log ต้องแก้ไขไม่ได้" ใน §6.1 ของ PROJECT_PLAN.md)

หลักการ: ทุกครั้งที่มีไฟล์ log ใหม่ถูกหมุน (logrotate) ให้คำนวณ SHA-256 ของไฟล์นั้น
ผูกกับ SHA-256 ของไฟล์ก่อนหน้า (prev_sha256) แล้วบันทึกเป็นแถวใน manifest
ถ้าใครย้อนไปแก้ไฟล์เก่า SHA-256 ที่คำนวณใหม่จะไม่ตรงกับที่บันทึกไว้ -> ตรวจพบทันที

ออกแบบให้ตรรกะหลัก (คำนวณ hash, ตรวจสาย hash) แยกจากที่เก็บข้อมูล (DB) ผ่าน interface
ManifestStore เพื่อให้ทดสอบได้โดยไม่ต้องมี MariaDB จริง — SqlManifestStore คือ
ตัวที่ใช้งานจริงบน gateway, MemoryManifestStore ใช้ในเทสต์ (และเป็น fallback ฉุกเฉินได้)
"""
from __future__ import annotations

import gzip
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

log = logging.getLogger("cafe-wifi.integrity")

CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    """SHA-256 ของเนื้อไฟล์ — ถ้าเป็น .gz จะ hash เนื้อหาที่ decompress แล้ว (เสถียรกว่า
    hash ตัวบีบอัดเอง เพราะ gzip header มี timestamp ที่เปลี่ยนได้แม้เนื้อหาเหมือนเดิม)"""
    h = hashlib.sha256()
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rb") as f:  # type: ignore[arg-type]
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class ManifestEntry:
    filename: str
    sha256: str
    prev_sha256: str | None
    size_bytes: int


class ManifestStore(Protocol):
    def last_entry(self) -> ManifestEntry | None: ...
    def has(self, filename: str) -> bool: ...
    def add(self, entry: ManifestEntry) -> None: ...
    def all_entries(self) -> list[ManifestEntry]: ...


class MemoryManifestStore:
    """ใช้ในเทสต์ (และเป็น fallback ได้ถ้า DB ล่มชั่วคราว แต่ข้อมูลจะหายเมื่อ process ตาย)"""

    def __init__(self) -> None:
        self._entries: list[ManifestEntry] = []

    def last_entry(self) -> ManifestEntry | None:
        return self._entries[-1] if self._entries else None

    def has(self, filename: str) -> bool:
        return any(e.filename == filename for e in self._entries)

    def add(self, entry: ManifestEntry) -> None:
        self._entries.append(entry)

    def all_entries(self) -> list[ManifestEntry]:
        return list(self._entries)


class SqlManifestStore:
    """ตัวจริงที่ใช้งานบน gateway — เขียน/อ่านตาราง log_manifest ผ่าน common.db"""

    def last_entry(self) -> ManifestEntry | None:
        from common.db import query_one
        row = query_one("SELECT filename, sha256, prev_sha256, size_bytes "
                        "FROM log_manifest ORDER BY id DESC LIMIT 1")
        return ManifestEntry(**row) if row else None

    def has(self, filename: str) -> bool:
        from common.db import query_one
        return query_one("SELECT id FROM log_manifest WHERE filename=%s", (filename,)) is not None

    def add(self, entry: ManifestEntry) -> None:
        from datetime import date

        from common.db import execute
        execute("INSERT INTO log_manifest (log_date, filename, sha256, prev_sha256, size_bytes) "
                "VALUES (%s,%s,%s,%s,%s)",
                (date.today(), entry.filename, entry.sha256, entry.prev_sha256, entry.size_bytes))

    def all_entries(self) -> list[ManifestEntry]:
        from common.db import query_all
        rows = query_all("SELECT filename, sha256, prev_sha256, size_bytes "
                         "FROM log_manifest ORDER BY id ASC")
        return [ManifestEntry(**r) for r in rows]


def seal_directory(
    directory: Path,
    store: ManifestStore,
    # แก้บั๊ก C1: ของเดิม ("*.log.gz", "*.log") ไม่ตรงกับไฟล์ที่ logrotate สร้างจริงเลยสักไฟล์
    # เพราะ install.sh ตั้ง `dateext` + `dateformat -%Y-%m-%d` ไว้ ชื่อไฟล์จึงเป็น
    # "dnsmasq.log-2026-08-25.gz" (มี -YYYY-MM-DD คั่นก่อน .gz เสมอ) หรือช่วง delaycompress
    # รอบแรกจะเป็น "dnsmasq.log-2026-08-25" (ยังไม่ compress) -- ผลคือ seal_directory()
    # ไม่เคยผนึกไฟล์อะไรเลยบนเครื่องจริง ทั้งที่เทสต์ผ่านหมดเพราะเทสต์ใช้ชื่อไฟล์สมมติ
    # "day1.log" ที่ไม่ตรงกับรูปแบบจริงของ logrotate
    patterns: tuple[str, ...] = ("*.log-*.gz", "*.log-*", "*.log.gz", "*.log"),
) -> list[ManifestEntry]:
    """
    เดินดูไฟล์ที่ยังไม่เคยผนึกในไดเรกทอรี (เรียงตาม mtime เก่า->ใหม่ เพื่อให้สาย hash
    เรียงตามเวลาจริง) แล้วผนึกทีละไฟล์ต่อจาก prev hash ล่าสุด คืนรายการที่เพิ่งผนึกใหม่
    """
    candidates: list[Path] = []
    for pat in patterns:
        candidates.extend(directory.glob(pat))
    candidates.sort(key=lambda p: p.stat().st_mtime)

    sealed: list[ManifestEntry] = []
    prev = store.last_entry()
    prev_hash = prev.sha256 if prev else None

    for path in candidates:
        if store.has(path.name):
            continue
        digest = sha256_file(path)
        entry = ManifestEntry(filename=path.name, sha256=digest,
                              prev_sha256=prev_hash, size_bytes=path.stat().st_size)
        store.add(entry)
        sealed.append(entry)
        prev_hash = digest
        log.info("ผนึก log %s -> %s", path.name, digest[:16])
    return sealed


@dataclass(frozen=True)
class IntegrityIssue:
    filename: str
    kind: str    # 'hash_mismatch' | 'missing_file' | 'chain_broken'
    detail: str


def verify_chain(store: ManifestStore, directory: Path) -> list[IntegrityIssue]:
    """
    ตรวจทั้งสาย: ไฟล์ยังอยู่ไหม, hash ยังตรงกับที่บันทึกไว้ไหม, prev_sha256 ต่อกันถูกไหม
    คืน list ว่างแปลว่าผ่านหมด — ใช้เป็นหลักฐานตอนนำเสนอ/ใส่ในเล่มรายงานได้ตรง ๆ
    """
    issues: list[IntegrityIssue] = []
    entries = store.all_entries()
    prev_hash: str | None = None

    for entry in entries:
        if entry.prev_sha256 != prev_hash:
            issues.append(IntegrityIssue(
                entry.filename, "chain_broken",
                f"คาดว่า prev_sha256={prev_hash!r} แต่บันทึกไว้เป็น {entry.prev_sha256!r}"))

        path = directory / entry.filename
        if not path.exists():
            issues.append(IntegrityIssue(entry.filename, "missing_file",
                                         f"ไม่พบไฟล์ {path} — อาจถูกลบทิ้งนอกกระบวนการปกติ"))
        else:
            actual = sha256_file(path)
            if actual != entry.sha256:
                issues.append(IntegrityIssue(
                    entry.filename, "hash_mismatch",
                    f"sha256 ปัจจุบัน {actual[:16]}… ไม่ตรงกับที่บันทึกไว้ {entry.sha256[:16]}… "
                    "— ไฟล์นี้อาจถูกแก้ไขหลังผนึก"))

        prev_hash = entry.sha256

    return issues


def main() -> int:  # pragma: no cover
    import os

    logging.basicConfig(level=logging.INFO)
    log_dir = Path(os.environ.get("LOG_DIR", "/var/log/cafe-wifi"))
    archive_dir = log_dir / "archive"
    store = SqlManifestStore()

    sealed = seal_directory(archive_dir, store)
    log.info("ผนึกไฟล์ใหม่ %d ไฟล์", len(sealed))

    issues = verify_chain(store, archive_dir)
    if issues:
        # N21: ต้องบันทึกลง audit_log ในฐานข้อมูลด้วย ไม่ใช่แค่ log ไฟล์ -- ถ้าคนร้ายแก้ไฟล์
        # log ได้ ก็ย่อมลบบรรทัด ERROR ในไฟล์ log ทิ้งได้เหมือนกัน หลักฐานว่า "ตรวจพบการแก้ไข"
        # จึงต้องอยู่คนละที่กับสิ่งที่ถูกแก้ และ ExecStart= ของ cafe-maintenance ใช้ `-` นำหน้า
        # (ยอมให้ fail ได้) exit code 1 จึงถูกกลืน ไม่มีใครรู้เรื่องเลยถ้าไม่บันทึกตรงนี้
        for i in issues:
            log.error("[%s] %s: %s", i.kind, i.filename, i.detail)
            try:
                from common import audit
                audit.log(audit.INTEGRITY_FAILED, target=i.filename,
                         detail=f"kind={i.kind} {i.detail}")
            except Exception:  # DB ล่มก็ยังต้องรายงานผ่าน log ไฟล์ให้ได้ ห้าม crash ทิ้ง
                log.exception("บันทึก audit_log ไม่สำเร็จ — ยังเหลือร่องรอยแค่ใน log ไฟล์เท่านั้น")
        return 1
    log.info("ตรวจสาย hash chain ผ่านทั้งหมด (%d ไฟล์)", len(store.all_entries()))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
