"""
common/qr.py — สร้าง QR code เป็น SVG ฝังในหน้าเว็บตรง ๆ (N7, CODING_BRIEF.md)

ทำไมต้องมี: KPI §14 ตั้งไว้ว่า "ออก voucher 1 ใบ ≤ 30 วินาที" -- ถ้าพนักงานต้องอ่านรหัส
8 ตัว (base32-ish, ไม่มีตัวกำกวมแต่ก็ยังต้องสะกดทีละตัว) ให้ลูกค้าฟังแล้วลูกค้าพิมพ์เองบนคีย์บอร์ด
มือถือ มีโอกาสพิมพ์ผิดสูงและกินเวลาเกิน 30 วินาทีแน่นอน -- ให้สแกนแทนพิมพ์แทน

**ข้อจำกัดที่ตั้งใจไว้**: openNDS FAS level 2 ต้องการ payload `fas`/`iv` ที่เข้ารหัสเฉพาะรอบ
การเชื่อมต่อนั้น ๆ (ผูกกับ MAC/gateway context ของลูกค้าตอนนั้นจริง ๆ) เราสร้าง URL "auto-login"
ล่วงหน้าจากฝั่ง Admin Panel ไม่ได้เลย (ดู fas/app.py::login()) -- QR นี้จึง**ไม่ใช่ลิงก์เข้าระบบ
อัตโนมัติ** แค่เข้ารหัสข้อความ user/pass ไว้ให้สแกนแล้วเห็น/คัดลอกได้ ไม่ต้องพิมพ์เองทั้งหมด
(ลูกค้ายังต้องกดเข้า Wi-Fi และวางรหัสในฟอร์มเองอยู่ดี แต่ไม่ต้องพิมพ์ทีละตัวอักษร)

ห้ามใช้ CDN (ทั้งโปรเจกต์ asset แบบ local เพราะ Admin Panel/Portal อยู่หลัง captive portal ที่
ลูกค้ายังไม่มีเน็ตตอนนั้น) -- ใช้ไลบรารี qrcode สร้าง SVG ฝั่งเซิร์ฟเวอร์ตรง ๆ ไม่มี JS ฝั่ง
ไคลเอนต์เลยแม้แต่บรรทัดเดียว
"""
from __future__ import annotations

import io

import qrcode
import qrcode.image.svg


def voucher_qr_svg(text: str) -> str:
    """คืน markup ตั้งแต่ `<svg ...>` เป็นต้นไป (ตัด `<?xml ...?>` prolog ทิ้ง เพราะฝังใน
    เอกสาร HTML5 โดยตรง ไม่ใช่ไฟล์ .svg แยก) ให้ใส่ใน template ผ่าน `{{ ... | safe }}` ได้เลย
    -- ไม่ใช่ data: URI ของรูปภาพ เพื่อให้ปรับขนาด/สีตาม CSS ของหน้าได้ตามปกติ"""
    img = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    start = svg.index("<svg")
    return svg[start:]
