"""
tools/enforce_voucher_expiry.py — บังคับอายุ voucher จริงที่ชั้นเครือข่าย + ปิด session ค้าง

รันถี่ (ทุก 5 นาที ผ่าน cafe-enforce.timer ตั้งโดย install.sh -- ถี่กว่า cafe-maintenance
รายคืนมาก เพราะนี่คือการบังคับสิทธิ์การเข้าถึงจริง ไม่ใช่งาน housekeeping)

แก้ 3 บั๊กพร้อมกันเพราะเป็นเรื่องเดียวกันจริง ๆ (ทั้งหมดคือ "ไม่มีอะไรมาปิด session/voucher
เมื่อหมดอายุ"):

  H3 — SessionTimeout ใน opennds.conf ตั้งตายตัวที่ 240 นาที (4 ชม.) ทำให้ voucher ที่ซื้อ
       1 ชม. ใช้ได้จริง 4 ชม. (ยาวกว่าที่จ่าย) ส่วน voucher 24 ชม. ถูกตัดที่ 4 ชม. (สั้นกว่า
       ที่จ่าย) -- install.sh แก้ SessionTimeout เป็น 1440 (ค่าสูงสุดที่ /issue อนุญาต) เพื่อไม่
       ให้ใครถูกตัดเร็วเกินที่จ่ายไว้ แล้วให้สคริปต์นี้เป็นตัวบังคับเวลาที่แท้จริงแทนด้วย
       `ndsctl deauth` -- 🔶 คำสั่งนี้ยังไม่เคยทดสอบกับ openNDS binary จริงบนฮาร์ดแวร์ (เหมือน
       ส่วนอื่นของโปรโตคอลนี้ที่บันทึกไว้ใน opennds_proto.py) ถ้า ndsctl ใช้ไม่ได้จริง อย่างน้อย
       ระบบยังปิด session ในฐานข้อมูลให้ถูกต้อง (online_now จะไม่ค้างเป็นเท็จ)

  M1 — portal_session ไม่เคยถูกปิดเมื่อลูกค้าเดินออกจากร้านไปเฉย ๆ (ปิดเฉพาะตอน MAC เดิม
       login ซ้ำ) ทำให้ "กำลังใช้งานอยู่ตอนนี้" ในหน้า dashboard มีแต่เพิ่มไม่มีวันลด --
       สคริปต์นี้ปิด session ที่ voucher หมดอายุ/ถูกยกเลิกไปแล้วให้ตามจริง (ยังไม่ครอบคลุม
       เคส "หมดอายุ session แต่ voucher ยัง active" เพราะไม่มีข้อมูล heartbeat ให้ตรวจ ต้องรอ
       Phase 5 ถ้าจะทำให้สมบูรณ์กว่านี้ -- บันทึกไว้ตรง ๆ ไม่ overclaim)

  M2 — voucher.status ไม่เคยถูก UPDATE จากที่ไหนเลย ค่า 'expired'/'used_up' จึงไม่มีทาง
       เกิดขึ้นจริงในฐานข้อมูล และ portal_session.bytes_in/out, voucher.used_mb ก็ไม่เคยถูก
       เขียนเลยทั้งที่ conn_log มีข้อมูล bytes ต่อ MAC อยู่แล้ว -- สคริปต์นี้: (1)ตั้ง
       status='expired' ให้ voucher ที่หมดอายุแล้ว (2) รวมยอด bytes จาก conn_log ต่อ mac
       ในช่วงเวลาของ session ลงใน portal_session.bytes_in/out + voucher.used_mb (3) ตั้ง
       status='used_up' ถ้ามีการกำหนด quota_mb ไว้และใช้เกิน -- ปิดครบสายแล้ว (N8,
       CODING_BRIEF.md, 2026-08-26): หน้า /issue มีช่องกรอก quota_mb แล้ว (dropdown
       ไม่จำกัด/500MB/1GB/2GB/5GB) ส่งเข้า INSERT INTO voucher จริง ฟังก์ชันนี้จึงถูกกระตุ้น
       ใช้งานได้จริงแล้ว ไม่ใช่แค่ต่อสายรอเฉย ๆ เหมือนก่อนหน้านี้
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass

# แก้บั๊ก (พบตอนตรวจทานรอบ 4): ฟังก์ชันนี้เคยนิยามซ้ำอยู่ในไฟล์นี้ด้วย แล้ว app/fas/app.py
# (service หน้าบ้าน) import ข้ามชั้นมาจาก tools/ (ชั้น CLI งานบำรุงรักษา) ตรง ๆ -- ผิดทิศทาง
# การพึ่งพา ย้ายไปไว้ที่ common/traffic.py (ชั้นที่ทั้ง app/ และ tools/ พึ่งพาได้ทั้งคู่อยู่แล้ว
# เหมือน crypto.py, db.py) แล้ว import กลับมาใช้ตรงนี้แทนเพื่อไม่ให้โค้ดซ้ำ
from common.traffic import BYTES_PER_MB, sum_session_traffic_bytes  # noqa: F401 (re-export)

log = logging.getLogger("cafe-wifi.enforce")


@dataclass(frozen=True)
class EnforceSummary:
    expired_vouchers: int = 0
    used_up_vouchers: int = 0
    sessions_closed: int = 0
    deauth_ok: int = 0
    deauth_failed: int = 0


def expire_stale_vouchers(execute_fn) -> int:
    """ตั้ง status='expired' ให้ voucher ที่ valid_until ผ่านไปแล้วแต่ยังเป็น 'active'"""
    return execute_fn(
        "UPDATE voucher SET status='expired' WHERE status='active' AND valid_until < NOW()")


def mark_used_up_vouchers(execute_fn) -> int:
    """ตั้ง status='used_up' ถ้ามี quota_mb กำหนดไว้และใช้ถึง/เกินแล้ว"""
    return execute_fn(
        "UPDATE voucher SET status='used_up' "
        "WHERE status='active' AND quota_mb IS NOT NULL AND used_mb >= quota_mb")


# แก้บั๊ก (พบตอนตรวจทานรอบ 2): เดิม close_session() ตั้ง terminate_cause='voucher_expired'
# ตายตัวเสมอ ไม่ว่า voucher จะหมดอายุจริง (expired) หรือถูกพนักงานยกเลิกเอง (revoked) หรือ
# ใช้ครบโควต้า (used_up) -- ระบุสาเหตุผิดในหลักฐานตาม ม.26 ต้อง SELECT v.status มาด้วยเพื่อ
# แมปสาเหตุให้ตรงจริง
TERMINATE_CAUSE_BY_STATUS = {
    "expired": "voucher_expired",
    "revoked": "voucher_revoked",
    "used_up": "quota_exceeded",
}


def find_sessions_to_close(query_all_fn) -> list[dict]:
    """session ที่ยังเปิดอยู่ (ended_at IS NULL) แต่ voucher ของมันไม่ active แล้ว"""
    return query_all_fn("""
        SELECT ps.id, ps.mac, ps.voucher_id, ps.started_at, v.status AS voucher_status
        FROM portal_session ps
        JOIN voucher v ON v.id = ps.voucher_id
        WHERE ps.ended_at IS NULL AND v.status != 'active'
    """)


def deauth_mac(mac: str, ndsctl_bin: str = "ndsctl") -> bool:
    """
    เรียก `ndsctl deauth <mac>` สั่ง openNDS ตัดการเชื่อมต่อทันที
    🔶 ยังไม่เคยทดสอบกับ openNDS binary จริงบนฮาร์ดแวร์ -- ถ้าเรียกไม่สำเร็จไม่ throw
    (แค่ log แล้วให้ผู้เรียกปิด session ในฐานข้อมูลต่อไป อย่างน้อยเลิกนับว่า "online" ผิด)
    """
    if shutil.which(ndsctl_bin) is None:
        log.warning("ไม่พบ %s บนเครื่องนี้ -- ข้ามการตัดที่ openNDS (ปิดแค่ session ใน DB)", ndsctl_bin)
        return False
    try:
        r = subprocess.run([ndsctl_bin, "deauth", mac], capture_output=True, timeout=10)
        if r.returncode != 0:
            log.warning("ndsctl deauth %s exit code %d: %s", mac, r.returncode,
                       r.stderr.decode(errors="replace")[:200])
        return r.returncode == 0
    except Exception as exc:  # noqa: BLE001
        log.warning("ndsctl deauth %s ล้มเหลว: %s", mac, exc)
        return False


def close_session(execute_fn, session_id: int, voucher_id: int,
                  bytes_out: int, bytes_in: int, voucher_status: str = "expired") -> None:
    cause = TERMINATE_CAUSE_BY_STATUS.get(voucher_status, "voucher_expired")
    execute_fn(
        "UPDATE portal_session SET ended_at=NOW(), terminate_cause=%s, "
        "bytes_out=%s, bytes_in=%s WHERE id=%s",
        (cause, bytes_out, bytes_in, session_id))
    used_mb_delta = (bytes_out + bytes_in) // BYTES_PER_MB
    if used_mb_delta:
        execute_fn("UPDATE voucher SET used_mb = used_mb + %s WHERE id=%s",
                  (used_mb_delta, voucher_id))


def run(deauth: bool = True) -> EnforceSummary:
    from common.db import execute as db_execute
    from common.db import get_conn, query_all, query_one

    with get_conn() as conn, conn.cursor() as cur:
        def _exec(sql, args=()):
            cur.execute(sql, args)
            return cur.rowcount

        def _query_all(sql, args=()):
            cur.execute(sql, args)
            return cur.fetchall()

        def _query_one(sql, args=()):
            cur.execute(sql, args)
            return cur.fetchone()

        n_expired = expire_stale_vouchers(_exec)
        to_close = find_sessions_to_close(_query_all)

        deauth_ok = deauth_failed = 0
        for row in to_close:
            if deauth:
                ok = deauth_mac(row["mac"])
                deauth_ok += int(ok)
                deauth_failed += int(not ok)
            bo, bi = sum_session_traffic_bytes(_query_one, row["mac"], row["started_at"])
            close_session(_exec, row["id"], row["voucher_id"], bo, bi, row["voucher_status"])

        n_used_up = mark_used_up_vouchers(_exec)

    summary = EnforceSummary(expired_vouchers=n_expired, used_up_vouchers=n_used_up,
                             sessions_closed=len(to_close),
                             deauth_ok=deauth_ok, deauth_failed=deauth_failed)
    log.info("enforce เสร็จ: voucher expired %d, used_up %d, session ปิด %d "
            "(deauth สำเร็จ %d, ล้มเหลว/ข้าม %d)",
            summary.expired_vouchers, summary.used_up_vouchers, summary.sessions_closed,
            summary.deauth_ok, summary.deauth_failed)
    return summary


def main() -> int:  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
