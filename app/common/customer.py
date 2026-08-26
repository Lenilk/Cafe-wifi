"""
common/customer.py — ตรรกะเกี่ยวกับข้อมูลลูกค้าที่ทั้งฝั่งเว็บ (app/) และงานบำรุงรักษา (tools/)
ต้องใช้ร่วมกัน (ตามแบบที่ common/traffic.py ทำไว้แล้วกับ sum_session_traffic_bytes() -- กัน
การ import ข้ามชั้นผิดทิศทางจาก app/ ไป tools/ ที่เคยเป็นปัญหาจริงมาก่อน ดู Work Log ตรวจทานรอบ 4
ใน PROJECT_PLAN.md)
"""
from __future__ import annotations

PURGED_MARK = "PURGED"  # ค่า natid_masked ที่แปลว่า "ถูกล้างข้อมูลระบุตัวตนไปแล้ว"


def anonymize_customer(execute_fn, customer_id: int) -> int:
    """
    ล้างข้อมูลระบุตัวตนของลูกค้า 1 คน (natid_hash/natid_enc/natid_masked) แต่**คงแถวไว้**
    -- ห้าม DELETE เพราะ fk_voucher_customer เป็น RESTRICT ปริยาย และลูกค้าทุกรายมี voucher
    อย่างน้อย 1 ใบเสมอ (ดู D20 ใน PROJECT_PLAN.md, บั๊กจริง C2 ที่เคย DELETE ตรง ๆ แล้วชน FK
    จนทำให้ cafe-maintenance.service ทั้งหน่วยหยุดกลางคัน) แถวที่เหลือยังใช้เป็นหลักฐานจำนวน
    ครั้ง/อุปกรณ์ตาม พ.ร.บ.คอมพิวเตอร์ ม.26 ได้ต่อ แม้ตัวตนจะถูกลบไปแล้ว

    ใช้ร่วมกันทั้ง 2 เส้นทางที่ต้องล้าง PII ของลูกค้า -- ตรรกะต้องเป็นชุดเดียวกันเป๊ะเสมอ
    ไม่แยกเขียนซ้ำที่ไหนอีก:
      (1) purge อัตโนมัติตามอายุ (tools/purge_old_data.py::purge_stale_customers, T11)
      (2) ลบตามคำขอเจ้าของข้อมูล -- DSR (N6, CODING_BRIEF.md, admin/app.py POST
          /customers/<id>/erase, §6.2 ข้อ 6 ของนโยบายความเป็นส่วนตัว)

    execute_fn(sql, args) -> จำนวนแถวที่ถูกกระทบ (rowcount) -- คืนค่านี้ตรง ๆ ให้ผู้เรียกเช็คว่า
    id ที่ส่งมามีแถวอยู่จริงไหม (0 = ไม่พบแถว)
    """
    return execute_fn(
        "UPDATE customer SET natid_hash = CONCAT('PURGED-', id), "
        "natid_enc = '', natid_masked = 'PURGED' WHERE id = %s",
        (customer_id,),
    )
