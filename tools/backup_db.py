"""
tools/backup_db.py — สำรองฐานข้อมูลรายวัน (แก้บั๊ก H4)

บั๊กเดิม: งาน maintenance รายคืน (cafe-maintenance.service) มีแค่ purge + integrity +
check_time -- ไม่มี backup DB เลยสักจุดในระบบ ทั้งที่ระบบตั้งใจให้รันบน SD card ตาม D14
(ซึ่งเสียเป็นเรื่องปกติ ไม่ใช่เรื่องบังเอิญ) SD พังโดยไม่มี backup = log ตาม ม.26 หายทั้งหมด
กู้คืนไม่ได้เลย = ผิดหน้าที่ตามกฎหมายทันที

รันทุกวันผ่าน cafe-maintenance.timer (ตั้งโดย install.sh) ต่อจาก purge_old_data

ขอบเขตที่ทำจริง (ต้องซื่อสัตย์): dump เก็บไว้ที่ BACKUP_DIR ในเครื่องก่อน (mode 0600 root-only
เพราะเนื้อหาในนั้นมี natid_enc ที่เข้ารหัสอยู่ -- backup เองไม่ได้ทำให้ปลอดภัยกว่า secrets.env
เดิม เพราะยังต้องมี DEK ใน secrets.env คู่กันถึงจะถอดรหัสได้) แล้ว **คัดลอกออกนอกเครื่องด้วย
ถ้าตั้ง OFFSITE_BACKUP_DIR ไว้** (N4, CODING_BRIEF.md -- §11.1 ข้อ 4 เขียนเงื่อนไขไว้เองว่า
"ถ้าใช้ SD card ต้อง backup ออกนอกการ์ด" เพราะถ้า SD card ทั้งใบพัง แล้ว backup อยู่ใน SD
ใบเดียวกัน ก็ไม่ต่างจากไม่มี backup เลย) OFFSITE_BACKUP_DIR ควรชี้ไปที่ mount point อื่น
(เช่น USB drive/NAS ที่ mount ไว้) -- ถ้าไม่ตั้งค่านี้ จะข้ามขั้นตอนนี้พร้อม log ว่าข้ามเพราะอะไร
ไม่ throw error (ยังไม่รองรับการส่งไป remote จริง ๆ เช่น rclone/scp ข้ามเครื่อง เป็นแค่ copy
ไปยัง path ในเครื่องเดียวกัน/mount point ที่เข้าถึงได้ผ่าน filesystem ตรง ๆ เท่านั้น)

บั๊กที่เกือบเกิดจริง (พบตอนตรวจทานรอบ 4): เดิม dump_cmd มี --routines --triggers ซึ่งต้องใช้
สิทธิ์อ่าน mysql.proc/TRIGGER ที่ DB_USER ไม่มีแล้วหลังแก้ GRANT ให้แคบลงเหลือแค่
SELECT/INSERT/UPDATE/DELETE (แก้บั๊ก GRANT ALL รอบ 3) -- ถ้ารันจริงอาจ error หรือ warning
กลางทาง เอาสองแฟลกนี้ออกแล้วตั้งใจแยก "schema เป็นโค้ด" ออกจาก "data เป็น backup" แทน:
โครงสร้าง (ตาราง/procedure/event ใน sql/001_schema.sql และ sql/003_partitions.sql ถ้าเปิด
--enable-partitions ไว้) มี DROP...IF EXISTS/CREATE...IF NOT EXISTS คุมไว้แล้ว รันซ้ำได้เสมอ
ไม่ต้องพึ่ง mysqldump มาช่วยจับ -- ตอน restore ให้รัน `mysql db < sql/001_schema.sql` (และ
`< sql/003_partitions.sql` ถ้าเคยเปิด partition ไว้) ก่อน แล้วค่อย restore ไฟล์ backup นี้ทับ
ข้อมูล วิธีนี้ตรงไปตรงมากว่า และไม่ต้องเพิ่มสิทธิ์ DB_USER กลับไปเสี่ยงเหมือนเดิม
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("cafe-wifi.backup")


class BackupError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackupResult:
    path: Path
    size_bytes: int
    pruned: int
    offsite_path: Path | None = None  # N4 -- None แปลว่าไม่ได้ตั้ง OFFSITE_BACKUP_DIR หรือคัดลอกไม่สำเร็จ


def dump_database(db_name: str, host: str, port: int, user: str, password: str,
                  out_path: Path, mysqldump_bin: str = "mysqldump",
                  gzip_bin: str = "gzip") -> Path:
    """
    รัน mysqldump --single-transaction (ไม่ lock ตาราง InnoDB ระหว่าง dump) ต่อสายผ่าน
    pipe จริงเข้า `gzip` (คนละโปรเซส) เขียนผ่านไฟล์ .tmp ก่อนแล้วค่อย rename ให้เป็นชื่อจริง
    ตอนจบ (atomic -- กัน backup ค้างไฟล์เขียนไม่ครบถ้า process ถูกฆ่ากลางคัน)

    หมายเหตุ (กันบั๊กที่เกือบเกิด): ห้ามใช้ `subprocess.run(cmd, stdout=gzip.GzipFile(...))`
    เพราะ subprocess เรียก .fileno() ของ stdout เพื่อส่งให้ child process เขียนตรง ๆ ที่
    เคอร์เนล -- GzipFile.fileno() คืน fd ของไฟล์ดิบข้างใน "ไม่ผ่าน" การบีบอัดของ Python เลย
    ผลคือ mysqldump จะเขียนข้อความดิบทับไฟล์ตรง ๆ (gzip header/trailer มาปะหัวท้ายเฉย ๆ)
    ได้ไฟล์ .gz ที่เปิดไม่ได้จริง -- ต้องรัน gzip เป็นอีกโปรเซสหนึ่งต่อ pipe กันจริง ๆ แทน
    """
    if shutil.which(mysqldump_bin) is None:
        raise BackupError(f"ไม่พบคำสั่ง '{mysqldump_bin}' — ตรวจว่าติดตั้ง mariadb-client แล้ว")
    if shutil.which(gzip_bin) is None:
        raise BackupError(f"ไม่พบคำสั่ง '{gzip_bin}'")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    # ไม่ใส่ --routines/--triggers/--events ตั้งใจ -- ต้องการสิทธิ์ที่ DB_USER ไม่มีแล้ว
    # (ดู docstring ด้านบน) โครงสร้าง schema/procedure/event อยู่ใน sql/*.sql (คุมด้วย
    # DROP...IF EXISTS/CREATE...IF NOT EXISTS อยู่แล้ว) ให้รันไฟล์เหล่านั้นตอน restore แทน
    dump_cmd = [mysqldump_bin, "--single-transaction", "--no-tablespaces",
               "-h", host, "-P", str(port), "-u", user, db_name]
    env = dict(os.environ, MYSQL_PWD=password)  # ไม่ใส่รหัสผ่านใน argv (โผล่ใน `ps` ได้)

    dump_proc = gzip_proc = None
    try:
        with open(tmp_path, "wb") as out_file:
            dump_proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, env=env)
            gzip_proc = subprocess.Popen([gzip_bin], stdin=dump_proc.stdout,
                                         stdout=out_file, stderr=subprocess.PIPE)
            dump_proc.stdout.close()  # ให้ SIGPIPE ทำงานถูกถ้า gzip ตายก่อน (idiom มาตรฐาน)
            _, dump_err = dump_proc.communicate()
            _, gzip_err = gzip_proc.communicate()
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    if dump_proc.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        raise BackupError(f"mysqldump exit code {dump_proc.returncode}: "
                          f"{dump_err.decode(errors='replace')[:500]}")
    if gzip_proc.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        raise BackupError(f"gzip exit code {gzip_proc.returncode}: "
                          f"{gzip_err.decode(errors='replace')[:500]}")

    tmp_path.rename(out_path)
    out_path.chmod(0o600)  # เนื้อหามี natid_enc -- จำกัดสิทธิ์เหมือน secrets.env
    return out_path


def prune_old_backups(backup_dir: Path, keep_days: int, pattern: str = "*.sql.gz") -> int:
    """ลบ backup ที่เก่ากว่า keep_days วัน (นับจาก mtime) คืนจำนวนไฟล์ที่ลบ"""
    cutoff = datetime.now() - timedelta(days=keep_days)
    pruned = 0
    for path in backup_dir.glob(pattern):
        if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
            path.unlink()
            pruned += 1
    return pruned


def copy_offsite(src: Path, offsite_dir: str | None) -> Path | None:
    """
    คัดลอก backup ออกนอกเครื่อง (N4) ถ้าตั้ง OFFSITE_BACKUP_DIR ไว้ -- คืน path ปลายทางถ้า
    สำเร็จ, None ถ้าข้าม (ไม่ได้ตั้งค่า) หรือคัดลอกไม่สำเร็จ

    ตั้งใจไม่ throw เมื่อคัดลอกไม่สำเร็จ (เช่น mount point ไม่อยู่/เขียนไม่ได้เต็มดิสก์)
    เพราะ backup ในเครื่องสำเร็จไปแล้วก่อนหน้านี้ -- ความล้มเหลวของ offsite ไม่ควรทำให้
    ทั้ง backup_db.py ถือว่าล้มเหลว (log ไว้ให้เห็นชัดเจนแทน แล้วปล่อยให้ backup ในเครื่อง
    ที่ทำสำเร็จแล้วยังมีประโยชน์ต่อไป)
    """
    if not offsite_dir:
        log.info("ไม่ได้ตั้ง OFFSITE_BACKUP_DIR — ข้าม backup ออกนอกเครื่อง "
                 "(backup ยังอยู่ในเครื่องเดียวกันที่ %s เท่านั้น เสี่ยงถ้า SD card พังทั้งใบ)", src)
        return None

    dest_dir = Path(offsite_dir)
    dest_path = dest_dir / src.name
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)
        dest_path.chmod(0o600)  # เนื้อหาเดียวกับต้นฉบับ มี natid_enc เข้ารหัสอยู่
    except OSError as exc:
        log.error("คัดลอก backup ออกนอกเครื่องไปที่ %s ไม่สำเร็จ: %s — backup ในเครื่องยังอยู่ที่ %s",
                  dest_path, exc, src)
        return None

    log.info("คัดลอก backup ออกนอกเครื่องสำเร็จ: %s", dest_path)
    return dest_path


def run(backup_dir: Path | None = None, keep_days: int | None = None,
       offsite_dir: str | None = None) -> BackupResult:
    backup_dir = backup_dir or Path(os.environ.get("BACKUP_DIR", "/var/backups/cafe-wifi"))
    keep_days = keep_days or int(os.environ.get("BACKUP_RETENTION_DAYS", "14"))
    offsite_dir = offsite_dir or os.environ.get("OFFSITE_BACKUP_DIR", "")

    db_name = os.environ.get("DB_NAME", "cafewifi")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = backup_dir / f"{db_name}-{stamp}.sql.gz"

    dump_database(
        db_name=db_name,
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "cafewifi"),
        password=os.environ.get("DB_PASS", ""),
        out_path=out_path,
    )
    size = out_path.stat().st_size
    offsite_path = copy_offsite(out_path, offsite_dir)  # N4
    pruned = prune_old_backups(backup_dir, keep_days)
    log.info("สำรอง DB สำเร็จ: %s (%d bytes) — ลบ backup เก่า %d ไฟล์ — offsite: %s",
            out_path, size, pruned, offsite_path or "ข้าม")
    return BackupResult(path=out_path, size_bytes=size, pruned=pruned, offsite_path=offsite_path)


def main() -> int:  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    try:
        run()
    except BackupError as exc:
        log.error(str(exc))
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
