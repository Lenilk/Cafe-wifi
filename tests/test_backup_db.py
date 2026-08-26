"""
T-Backup — tools/backup_db.py (แก้บั๊ก H4: เดิมไม่มี backup DB เลยในระบบ)

รันจริงด้วย `sh` + `gzip` ตัวจริง (ไม่ mock subprocess) โดยแกล้งเป็น mysqldump ด้วยสคริปต์
ปลอมที่พิมพ์ข้อความคงที่ออก stdout -- ทดสอบ pipe จริง ไม่ใช่แค่ตรรกะล้วน ๆ เพราะบั๊กประเภทนี้
(subprocess.run(stdout=gzip.GzipFile(...)) เขียนข้อมูลดิบทับไฟล์ ไม่ผ่านการบีบอัดจริง)
ตรวจจับไม่ได้ด้วย mock -- ต้องรันจริงถึงจะเห็น
"""
import gzip
import os
import shutil
import stat

import pytest

from tools.backup_db import BackupError, dump_database, prune_old_backups, run

pytestmark = pytest.mark.skipif(
    shutil.which("sh") is None or shutil.which("gzip") is None,
    reason="ทดสอบนี้ต้องมี sh และ gzip จริงในระบบ (มีอยู่แล้วบนทุก distro เป้าหมาย)",
)

FAKE_DUMP_SCRIPT = """#!/bin/sh
echo "-- fake mysqldump output"
echo "INSERT INTO customer VALUES (1);"
"""

FAKE_DUMP_FAIL_SCRIPT = """#!/bin/sh
echo "ERROR 1045: Access denied" >&2
exit 1
"""


def _make_fake_mysqldump(tmp_path, script_text=FAKE_DUMP_SCRIPT, name="fake_mysqldump.sh"):
    p = tmp_path / name
    p.write_text(script_text)
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return str(p)


def test_dump_database_produces_valid_gzip_via_real_pipe(tmp_path):
    """
    จุดสำคัญที่สุดของเทสต์นี้: เปิดไฟล์ผลลัพธ์ด้วย gzip.open() จริง ๆ แล้วอ่านเนื้อหาออกมา
    เทียบ -- ถ้า pipe ผิด (เช่นข้อมูลดิบไม่ผ่านการบีบอัด) ไฟล์จะเปิดไม่ได้เลยหรือได้ขยะ
    ไม่ใช่แค่เช็คว่าไฟล์มีขนาด > 0
    """
    fake = _make_fake_mysqldump(tmp_path)
    out_path = tmp_path / "out" / "testdb.sql.gz"

    result = dump_database("testdb", "127.0.0.1", 3306, "root", "x",
                           out_path, mysqldump_bin=fake, gzip_bin="gzip")

    assert result == out_path
    assert out_path.exists()
    content = gzip.open(out_path, "rt").read()
    assert "fake mysqldump output" in content
    assert "INSERT INTO customer VALUES (1);" in content
    # เนื้อหามี natid_enc -- ต้องจำกัดสิทธิ์เหมือน secrets.env เสมอ
    assert oct(out_path.stat().st_mode)[-3:] == "600"
    # ไฟล์ .tmp ต้องไม่ค้าง (rename สำเร็จแล้ว)
    assert not out_path.with_suffix(".gz.tmp").exists()


def test_dump_database_raises_and_cleans_up_tmp_on_mysqldump_failure(tmp_path):
    fake = _make_fake_mysqldump(tmp_path, FAKE_DUMP_FAIL_SCRIPT, "fake_dump_fail.sh")
    out_path = tmp_path / "testdb.sql.gz"

    with pytest.raises(BackupError, match="Access denied"):
        dump_database("testdb", "127.0.0.1", 3306, "root", "x",
                      out_path, mysqldump_bin=fake, gzip_bin="gzip")

    assert not out_path.exists()
    assert not out_path.with_suffix(".gz.tmp").exists(), "ไฟล์ .tmp ค้างต้องถูกลบทิ้งเมื่อ mysqldump พัง"


def test_dump_database_raises_if_mysqldump_binary_missing(tmp_path):
    with pytest.raises(BackupError, match="mysqldump-that-does-not-exist"):
        dump_database("testdb", "127.0.0.1", 3306, "root", "x",
                      tmp_path / "out.sql.gz", mysqldump_bin="mysqldump-that-does-not-exist")


def test_prune_old_backups_deletes_only_files_past_retention(tmp_path):
    import time

    old = tmp_path / "cafewifi-old.sql.gz"
    new = tmp_path / "cafewifi-new.sql.gz"
    old.write_bytes(b"x")
    new.write_bytes(b"x")
    old_time = time.time() - 20 * 86400  # 20 วันก่อน
    os.utime(old, (old_time, old_time))

    pruned = prune_old_backups(tmp_path, keep_days=14)
    assert pruned == 1
    assert not old.exists()
    assert new.exists()


def test_run_end_to_end_writes_and_prunes(tmp_path, monkeypatch):
    """
    run() เรียก dump_database(mysqldump_bin="mysqldump") แบบไม่ให้ override ชื่อคำสั่งได้
    (ตั้งใจ -- ผู้ใช้จริงต้องมี mysqldump ตัวจริงบน PATH) เทสต์นี้จึงวางสคริปต์ปลอมชื่อ
    "mysqldump" ไว้ในโฟลเดอร์ที่เพิ่มเข้า PATH ก่อน แทนการ monkeypatch โค้ดภายใน
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_mysqldump(bin_dir, name="mysqldump")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    backup_dir = tmp_path / "backups"
    monkeypatch.setenv("DB_NAME", "cafewifi")
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DB_USER", "root")
    monkeypatch.setenv("DB_PASS", "x")

    result = run(backup_dir=backup_dir, keep_days=14)
    assert result.path.exists()
    assert result.size_bytes > 0
    assert result.pruned == 0
    content = gzip.open(result.path, "rt").read()
    assert "fake mysqldump output" in content
