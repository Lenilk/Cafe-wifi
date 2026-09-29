"""ยืนยัน pending FAS sessions กับ openNDS ก่อนนับว่าออนไลน์จริง."""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime

from common import audit
from common.db import get_conn

log = logging.getLogger("cafe-wifi.reconcile_pending")


def gateway_clients() -> dict | None:
    try:
        result = subprocess.run(["ndsctl", "json"], capture_output=True, text=True,
                                timeout=10, check=True)
        return (json.loads(result.stdout) or {}).get("clients", {})
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        log.error("อ่านสถานะ openNDS ไม่ได้: %s", exc)
        return None


def confirmed_since(client: dict | None, ip: str, started_at: datetime) -> bool:
    """MAC อย่างเดียวไม่พอ: ต้องเป็น IP เดิมและ gateway session ที่เริ่มหลัง pending."""
    if not client or not str(client.get("state", "")).lower().startswith("auth"):
        return False
    if str(client.get("ip") or client.get("clientip") or "") != ip:
        return False
    try:
        gateway_start = datetime.fromtimestamp(int(client["session_start"]))
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return False
    return gateway_start >= started_at


def purge_orphan_claims() -> int:
    """R2-01: ลบ claim ที่ portal_session_id=NULL ซึ่งหลุด commit มาจาก /login รุ่นก่อนแก้

    แถวแบบนี้ไม่มี session ให้ผูก ลูปหลักจึงไม่เคยลบ และทำให้ MAC นั้นได้ 409 ตลอดไป
    แยก transaction จากลูปหลักและแตะแค่ตารางนี้ เพื่อไม่ให้ลำดับ lock ชนกับ /login
    (claim ของ /login ที่ยังไม่ commit จะผูก portal_session_id ก่อน commit เสมอ จึงไม่ถูกลบ)
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM pending_mac_claim WHERE portal_session_id IS NULL")
        purged = cur.rowcount
    if purged:
        log.warning("ลบ pending_mac_claim ที่ค้างอยู่ %d รายการ", purged)
    return purged


def run() -> tuple[int, int]:
    clients = gateway_clients()
    promoted = expired = 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM fas_context WHERE expires_at < "
                    "DATE_SUB(NOW(), INTERVAL 1 DAY)")
        cur.execute("SELECT ps.id, ps.voucher_id, ps.mac, ps.ip, ps.started_at, "
                    "ps.pending_until, v.status, v.valid_until "
                    "FROM portal_session ps JOIN voucher v ON v.id=ps.voucher_id "
                    "WHERE ps.state='pending' ORDER BY ps.id FOR UPDATE")
        pending = cur.fetchall()
        for row in pending:
            if row["pending_until"] <= datetime.now():
                from tools.enforce_voucher_expiry import deauth_mac
                if not deauth_mac(row["mac"]):
                    log.error("pending %s หมดเวลาแต่ตัดสิทธิ์ที่ gateway ไม่สำเร็จ", row["id"])
                    continue
                cur.execute("UPDATE portal_session SET state='closed', ended_at=NOW(), "
                            "terminate_cause='auth_timeout' WHERE id=%s AND state='pending'",
                            (row["id"],))
                cur.execute("DELETE FROM pending_mac_claim WHERE mac=%s AND portal_session_id=%s",
                            (row["mac"], row["id"]))
                expired += 1
                continue
            if clients is None:
                continue
            client = clients.get(row["mac"].lower()) or clients.get(row["mac"].upper())
            if not confirmed_since(client, row["ip"], row["started_at"]):
                continue
            if row["status"] != "active" or row["valid_until"] <= datetime.now():
                from tools.enforce_voucher_expiry import deauth_mac
                if not deauth_mac(row["mac"]):
                    log.error("voucher ไม่ active แต่ตัด MAC %s ไม่สำเร็จ", row["mac"])
                    continue
                cur.execute("UPDATE portal_session SET state='closed', ended_at=NOW(), "
                            "terminate_cause='voucher_invalid' WHERE id=%s", (row["id"],))
                cur.execute("DELETE FROM pending_mac_claim WHERE mac=%s AND portal_session_id=%s",
                            (row["mac"], row["id"]))
                continue
            cur.execute("SELECT id, started_at FROM portal_session WHERE mac=%s "
                        "AND state='authenticated' AND ended_at IS NULL FOR UPDATE",
                        (row["mac"],))
            for old in cur.fetchall():
                from common.traffic import sum_session_traffic_bytes
                def lookup(sql, args=()):
                    cur.execute(sql, args)
                    return cur.fetchone()
                bo, bi = sum_session_traffic_bytes(lookup, row["mac"], old["started_at"])
                cur.execute("UPDATE portal_session SET state='closed', ended_at=NOW(), "
                            "terminate_cause='reauth', bytes_out=%s, bytes_in=%s WHERE id=%s",
                            (bo, bi, old["id"]))
            cur.execute("INSERT INTO device (voucher_id, mac, last_ip) VALUES (%s,%s,%s) "
                        "ON DUPLICATE KEY UPDATE last_ip=VALUES(last_ip)",
                        (row["voucher_id"], row["mac"], row["ip"]))
            cur.execute("UPDATE portal_session SET state='authenticated', authenticated_at=NOW() "
                        "WHERE id=%s AND state='pending'", (row["id"],))
            cur.execute("DELETE FROM pending_mac_claim WHERE mac=%s AND portal_session_id=%s",
                        (row["mac"], row["id"]))
            promoted += 1
    purge_orphan_claims()
    if promoted:
        audit.log(audit.LOGIN_OK, detail=f"confirmed={promoted}")
    if expired:
        log.warning("pending session หมดเวลา %d รายการ", expired)
    return promoted, expired


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
