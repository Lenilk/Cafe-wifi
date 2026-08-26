"""
fas/app.py — Captive Portal (Forwarding Authentication Service, FAS level 2)

ลำดับการทำงาน (ดู §3.3 ใน PROJECT_PLAN.md):
  1. ลูกค้าต่อ Wi-Fi -> openNDS redirect มาที่ GET /login?fas=..&iv=..
  2. ถอดรหัส payload ได้ ClientContext (mac, hid, gatewayaddress, originurl, ...)
  3. แสดงฟอร์มให้กรอก username/password ของ voucher (ฝัง context ไว้ใน hidden field
     เพราะ cookie อาจใช้งานไม่ได้เสถียรระหว่างขั้นตอน captive portal)
  4. POST /login -> ตรวจ voucher, ผูก MAC, จำกัดจำนวนอุปกรณ์, เปิด portal_session
  5. redirect (302) ไปยัง authaction URL ของ openNDS จริง ๆ (browser ของลูกค้าเป็นคนยิง ไม่ใช่ server)
     -> openNDS อนุญาต MAC ผ่าน nftables

ความซื่อสัตย์ทางวิศวกรรม: ยังไม่เคยทดสอบกับ openNDS binary จริง (ดูหมายเหตุใน opennds_proto.py)
"""
from __future__ import annotations

import ipaddress
import os
import re
import time
from datetime import datetime, timedelta

from flask import Flask, abort, redirect, render_template, request

from common import audit, crypto
from common.db import execute, get_conn, query_one
from common.traffic import sum_session_traffic_bytes
from logger.netutil import resolve_mac
from .opennds_proto import (ClientContext, FasProtocolError,
                            build_auth_action_url, decrypt_fas_payload)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", os.urandom(32).hex()),
    MAX_CONTENT_LENGTH=256 * 1024,
)
if not os.environ.get("SECRET_KEY"):
    # แก้บั๊ก (พบตอนตรวจทานรอบ 2): ดูรายละเอียดเดียวกันใน admin/app.py -- ไฟล์นี้ไม่ได้ใช้
    # Flask session/flash เอง (ใช้ hidden form field แทน) ผลกระทบจึงต่ำกว่า admin/app.py
    # มาก แต่ log ไว้เผื่ออนาคตมีคนเพิ่มโค้ดที่พึ่ง session เข้ามาโดยไม่รู้ตัวว่า SECRET_KEY หาย
    app.logger.error(
        "ไม่พบ SECRET_KEY ใน environment — ใช้ค่าสุ่มชั่วคราวแทน ตรวจสอบว่า EnvironmentFile "
        "โหลด /etc/cafe-wifi/secrets.env สำเร็จหรือไม่"
    )

FAS_KEY = os.environ.get("FAS_KEY", "")
GATEWAY_NAME = os.environ.get("GATEWAY_NAME", "Cafe-Guest")
MAC_RE = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")

_attempts: dict[str, list[float]] = {}
MAX_ATTEMPTS = 5
WINDOW_SEC = 600


def rate_limited(bucket: str) -> bool:
    now = time.time()
    hits = [t for t in _attempts.get(bucket, []) if now - t < WINDOW_SEC]
    _attempts[bucket] = hits
    return len(hits) >= MAX_ATTEMPTS


def record_attempt(bucket: str) -> None:
    _attempts.setdefault(bucket, []).append(time.time())


def client_ip() -> str:
    # แก้บั๊ก C3: ใช้ X-Real-IP ก่อนเสมอ (nginx เขียนทับด้วย $remote_addr ทุกครั้ง ปลอมไม่ได้)
    # ดูรายละเอียดเดียวกันใน admin/app.py::client_ip()
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if not real_ip:
        fwd = request.headers.get("X-Forwarded-For", "")
        real_ip = fwd.split(",")[0].strip() if fwd else (request.remote_addr or "")
    try:
        ipaddress.ip_address(real_ip)
    except ValueError:
        return ""
    return real_ip


def normalize_mac(mac: str) -> str:
    return (mac or "").strip().upper()


def ctx_from_form() -> ClientContext:
    """หลัง POST ต้องอ่าน context กลับจาก hidden fields ที่ฟอร์ม GET เคยฝังไว้"""
    return ClientContext(
        clientip=request.form.get("ctx_clientip", ""),
        clientmac=normalize_mac(request.form.get("ctx_clientmac", "")),
        gatewayname=request.form.get("ctx_gatewayname", GATEWAY_NAME),
        hid=request.form.get("ctx_hid", ""),
        gatewayaddress=request.form.get("ctx_gatewayaddress", ""),
        authdir=request.form.get("ctx_authdir", ""),
        originurl=request.form.get("ctx_originurl", ""),
        clientif=request.form.get("ctx_clientif", ""),
    )


@app.context_processor
def inject_globals():
    return {"gateway_name": GATEWAY_NAME}


@app.get("/health")
def health():
    return {"status": "ok", "service": "cafe-wifi-fas"}


# ---------------------------------------------------------------- หน้าล็อกอิน
@app.route("/login", methods=["GET", "POST"])
def login():
    if not FAS_KEY:
        app.logger.error("ไม่พบ FAS_KEY ใน environment — service โหลด secrets.env หรือยัง?")
        return render_template("error.html", title="ระบบยังตั้งค่าไม่ครบ",
                               message="ผู้ดูแลระบบต้องตรวจสอบการตั้งค่าเซิร์ฟเวอร์"), 503

    if request.method == "GET":
        fas_b64 = request.args.get("fas", "")
        iv = request.args.get("iv", "")

        # เข้าเว็บตรง ๆ ผ่าน http://cafe.wifi (ไม่มี fas/iv) เช่น ลูกค้าพิมพ์เองเพราะ
        # captive detection ไม่เด้ง -> อธิบายวิธีต่อใหม่แทนที่จะ error
        if not fas_b64 or not iv:
            return render_template("manual.html")

        try:
            ctx = decrypt_fas_payload(fas_b64, iv, FAS_KEY)
        except FasProtocolError as exc:
            app.logger.warning("ถอดรหัส FAS payload ไม่สำเร็จ: %s", exc)
            return render_template("error.html", title="เชื่อมต่อไม่สำเร็จ",
                                   message="ลิงก์เข้าสู่ระบบไม่ถูกต้องหรือหมดอายุ "
                                           "กรุณาต่อ Wi-Fi ใหม่อีกครั้ง"), 400
        if not ctx.is_complete():
            return render_template("error.html", title="ข้อมูลไม่ครบ",
                                   message="กรุณาต่อ Wi-Fi ใหม่อีกครั้ง"), 400
        if not MAC_RE.match(ctx.clientmac):
            return render_template("error.html", title="ข้อมูลอุปกรณ์ไม่ถูกต้อง",
                                   message="ไม่รู้จักที่อยู่อุปกรณ์ กรุณาต่อ Wi-Fi ใหม่"), 400

        return render_template("login.html", ctx=ctx)

    # ---- POST ----
    ctx = ctx_from_form()
    if not ctx.is_complete() or not MAC_RE.match(ctx.clientmac):
        return render_template("error.html", title="เซสชันหมดอายุ",
                               message="กรุณาต่อ Wi-Fi ใหม่แล้วลองอีกครั้ง"), 400

    # บั๊กเดิม: ใช้ ctx.clientip (มาจาก hidden field ที่ POST เข้ามา -- ผู้ใช้ปลอมค่าได้ตรง ๆ
    # ผ่าน devtools/curl) ไปเขียนลง audit_log/device/portal_session ซึ่งเป็นหลักฐานตาม PDPA
    # ต้องใช้ IP จริงของ request (client_ip() ที่นิยามไว้แล้วแต่ไม่เคยถูกเรียก) แทน
    real_ip = client_ip() or ctx.clientip

    # แก้บั๊ก H2: ctx.clientmac ก็มาจาก hidden field เหมือนกัน (ปลอมได้เช่นเดียวกับ clientip
    # เดิม) แต่ MAC คือกุญแจเดียวที่เชื่อม "ตัวตนลูกค้า" เข้ากับ conn_log/dns_log (ซึ่งได้ MAC
    # จริงจากตาราง ARP ของเคอร์เนล ไม่ใช่จากฟอร์ม) -- เทียบกับ ARP entry ของ real_ip ปัจจุบัน
    # ก่อนผูก MAC ลง device/portal_session ถ้าไม่ตรงกันปฏิเสธทันที (ไม่พบใน ARP เลย เช่น
    # entry เพิ่งหลุด cache ไม่ถือเป็นการปลอม -- ปล่อยผ่านแทนที่จะบล็อกลูกค้าจริงโดยไม่มีเหตุ)
    arp_mac = resolve_mac(real_ip)
    if arp_mac and arp_mac != ctx.clientmac:
        app.logger.warning("MAC ไม่ตรงกับ ARP: form=%s arp=%s ip=%s", ctx.clientmac, arp_mac, real_ip)
        return render_template("error.html", title="ข้อมูลอุปกรณ์ไม่ตรงกัน",
                               message="กรุณาต่อ Wi-Fi ใหม่อีกครั้ง"), 400

    bucket = f"login:{ctx.clientmac}"
    if rate_limited(bucket):
        return render_template("login.html", ctx=ctx,
                               error="พยายามเข้าสู่ระบบมากเกินไป กรุณารอ 10 นาทีแล้วลองใหม่"), 429

    code = (request.form.get("username") or "").strip().upper()
    password = request.form.get("password") or ""

    voucher = query_one("""
        SELECT v.id, v.password_hash, v.valid_from, v.valid_until, v.status,
               v.max_devices, v.customer_id, c.is_blocked
        FROM voucher v JOIN customer c ON c.id = v.customer_id
        WHERE v.username = %s
    """, (code,))

    now = datetime.now()
    reason = None
    if not voucher:
        reason = "ไม่พบรหัสนี้ในระบบ"
    elif voucher["is_blocked"]:
        reason = "ลูกค้ารายนี้ถูกระงับการใช้งาน กรุณาติดต่อพนักงาน"
    elif voucher["status"] != "active":
        reason = "รหัสนี้ถูกยกเลิกหรือใช้งานไปแล้ว"
    elif now > voucher["valid_until"]:
        reason = "รหัสนี้หมดอายุแล้ว กรุณาขอรหัสใหม่จากพนักงาน"
    elif now < voucher["valid_from"]:
        reason = "รหัสนี้ยังไม่ถึงเวลาที่ใช้งานได้"
    elif not crypto.verify_password(voucher["password_hash"], password):
        reason = "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"

    if reason:
        record_attempt(bucket)
        audit.log(audit.LOGIN_FAIL, target=code, client_ip=real_ip,
                  detail=f"mac={ctx.clientmac} reason={reason}")
        return render_template("login.html", ctx=ctx, error=reason), 401

    # ---- ตรวจ/ผูกอุปกรณ์ ----
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM device WHERE voucher_id=%s AND mac=%s",
                    (voucher["id"], ctx.clientmac))
        existing_device = cur.fetchone()
        if not existing_device:
            cur.execute("SELECT COUNT(*) AS n FROM device WHERE voucher_id=%s", (voucher["id"],))
            if int(cur.fetchone()["n"]) >= voucher["max_devices"]:
                audit.log(audit.LOGIN_FAIL, target=code, client_ip=real_ip,
                          detail=f"mac={ctx.clientmac} reason=device_limit_exceeded")
                return render_template(
                    "login.html", ctx=ctx,
                    error=f"รหัสนี้ใช้ครบ {voucher['max_devices']} อุปกรณ์แล้ว "
                          "กรุณาขอรหัสใหม่จากพนักงานหากต้องการเพิ่มอุปกรณ์"), 403
            cur.execute("INSERT INTO device (voucher_id, mac, last_ip) VALUES (%s, %s, %s)",
                        (voucher["id"], ctx.clientmac, real_ip))
        else:
            cur.execute("UPDATE device SET last_ip=%s WHERE id=%s",
                        (real_ip, existing_device["id"]))

        # ปิด session เก่าที่ยังค้างของ mac นี้ (กันนับซ้ำใน "กำลังใช้งานอยู่ตอนนี้")
        # บั๊กเดิม (พบตอนตรวจทานรอบ 2): ปิด session ตรงนี้โดยไม่บันทึก bytes_out/bytes_in
        # เลย ต่างจาก enforce_voucher_expiry.py ที่รวมยอดจาก conn_log ให้ -- ผลคือ session ที่
        # ปิดด้วย reauth มี bytes เป็น 0 ตลอดกาล ขณะที่ session ที่ปิดด้วย voucher หมดอายุมี
        # ตัวเลขจริง ทำให้ข้อมูลไม่สม่ำเสมอ ใช้ฟังก์ชันรวมยอดตัวเดียวกับ enforce_voucher_expiry
        # เพื่อไม่ให้ตรรกะซ้ำกันสองที่
        def _query_one(sql, args=()):
            cur.execute(sql, args)
            return cur.fetchone()

        # บั๊กเดิม (พบตอนตรวจทานรอบ 4): เดิม fetchone() ดึง started_at มาแค่แถวเดียว (ไม่ระบุ
        # ORDER BY จึงได้แถวไหนก็ได้) แต่ UPDATE ด้านล่างที่ตามมาแก้ "ทุกแถว" ที่ mac=%s AND
        # ended_at IS NULL ตรงกัน -- ถ้าบังเอิญมี session ค้างเปิดพร้อมกันมากกว่า 1 อันของ mac
        # เดียวกัน (เช่น race condition กับ enforce_voucher_expiry.py ที่รันคู่ขนานอยู่) ทุกแถว
        # จะถูกเขียนทับด้วยยอด bytes ของแถวเดียวกันหมด ทั้งที่แต่ละ session เริ่มคนละเวลา ยอด
        # ที่ควรจะได้ไม่เท่ากัน -- ดึงมาทีละแถวแล้วปิด+คำนวณ bytes แยกต่อแถวแทน (ปกติจะมีแค่
        # 0-1 แถวเสมออยู่แล้ว จึงไม่กระทบประสิทธิภาพ)
        cur.execute("SELECT id, started_at FROM portal_session WHERE mac=%s AND ended_at IS NULL",
                    (ctx.clientmac,))
        for stale in cur.fetchall():
            bo, bi = sum_session_traffic_bytes(_query_one, ctx.clientmac, stale["started_at"])
            cur.execute("""UPDATE portal_session SET ended_at=NOW(), terminate_cause='reauth',
                           bytes_out=%s, bytes_in=%s WHERE id=%s""",
                        (bo, bi, stale["id"]))
        cur.execute("""INSERT INTO portal_session (voucher_id, mac, ip, started_at)
                       VALUES (%s, %s, %s, NOW())""", (voucher["id"], ctx.clientmac, real_ip))

    audit.log(audit.LOGIN_OK, target=code, client_ip=real_ip, detail=f"mac={ctx.clientmac}")

    try:
        redirect_url = build_auth_action_url(ctx, FAS_KEY)
    except FasProtocolError as exc:
        app.logger.error("สร้าง auth URL ไม่สำเร็จ: %s", exc)
        return render_template("error.html", title="เกิดข้อผิดพลาด",
                               message="กรุณาลองใหม่อีกครั้ง หรือแจ้งพนักงาน"), 500

    return redirect(redirect_url, code=302)


@app.get("/policy")
def policy():
    return render_template("policy.html")


@app.errorhandler(404)
def e404(e):
    return render_template("error.html", title="ไม่พบหน้านี้",
                           message="กรุณาต่อ Wi-Fi ใหม่อีกครั้ง"), 404


@app.errorhandler(500)
def e500(e):
    app.logger.exception("unhandled error")
    return render_template("error.html", title="เกิดข้อผิดพลาด",
                           message="กรุณาลองใหม่อีกครั้ง หรือแจ้งพนักงาน"), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("FAS_PORT", 18080)), debug=False)
