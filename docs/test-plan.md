# แผนการทดสอบ (Test Plan)

อ้างอิงตัวชี้วัดจาก `PROJECT_PLAN.md` §12 และ §14 — เอกสารนี้ขยายรายละเอียดวิธีทดสอบ
แต่ละข้อ พร้อมระบุสถานะปัจจุบันตรงไปตรงมาว่าอะไรทดสอบอัตโนมัติได้แล้ว อะไรต้องรอฮาร์ดแวร์จริง

สัญลักษณ์สถานะ: ✅ ทดสอบอัตโนมัติผ่านแล้วในสภาพแวดล้อมพัฒนา · ⬜ ยังไม่ได้ทดสอบ (ต้องใช้ฮาร์ดแวร์/เครือข่ายจริง)

## กลุ่มที่ 1 — ตรรกะล้วน ๆ (ทดสอบอัตโนมัติได้เต็มรูปแบบ ไม่ต้องมีฮาร์ดแวร์)

| ID | รายการ | ไฟล์เทสต์ | สถานะ |
|---|---|---|---|
| T1 | Thai ID checksum | `tests/test_thai_id.py` | ✅ 8 เคส |
| T2 | Crypto round-trip (AES-256-GCM, HMAC, argon2id) | `tests/test_crypto.py` | ✅ 12 เคส |
| T-Proto | FAS protocol (AES-256-CBC ตาม openNDS FAS level 2) | `tests/test_opennds_proto.py` | ✅ 15 เคส |
| T-Setup | First-run Setup Wizard | `tests/test_setup_flow.py` | ✅ 9 เคส |
| T-FAS | Captive Portal login flow (mock gateway) | `tests/test_fas_flow.py` | ✅ 17 เคส |
| T-Logger | Parser ของ conntrack/dnsmasq + hash chain | `tests/test_logger.py` | ✅ 22 เคส |
| T-Purge | นโยบายการลบข้อมูล + export หลักฐาน | `tests/test_purge_and_export.py` | ✅ 14 เคส |

**วิธีรัน (บนเครื่องที่มีอินเทอร์เน็ต):**
```bash
pip install pytest PyMySQL cryptography argon2-cffi Flask
PYTHONPATH=app pytest tests/ -v
```

## กลุ่มที่ 2 — ต้องใช้ MariaDB จริง (schema ยังไม่เคย apply จริง)

| ID | รายการ | วิธีทดสอบ | สถานะ |
|---|---|---|---|
| — | `sql/001_schema.sql` สร้างตารางได้ไม่มี error | `mysql cafewifi < sql/001_schema.sql` | ⬜ |
| — | `sql/003_partitions.sql` ทำงานถูกต้อง | รันแล้วตรวจ `SHOW CREATE TABLE conn_log` | ⬜ |
| — | Foreign key / constraint ทำงานถูกต้องภายใต้ concurrent write | load test จริง | ⬜ |

## กลุ่มที่ 3 — ต้องใช้ Raspberry Pi + เครือข่ายจริง (ตัวชี้วัดจาก §14)

| ID | รายการ | เกณฑ์ผ่าน | สถานะ |
|---|---|---|---|
| T3 | Captive portal detection บน iOS/Android/Windows/macOS | เด้งหน้า login ≤ 10 วินาที, สำเร็จ ≥ 95% จาก 10 ครั้ง/OS | ⬜ |
| T4 | Auth flow จริงผ่าน openNDS binary | เข้าเน็ตได้ภายใน 3 วินาทีหลัง login | ⬜ |
| T5 | Device limit (จำกัดจำนวนอุปกรณ์ต่อ voucher) | ตรรกะทดสอบผ่านแล้วใน T-FAS (mock) — ต้องยืนยันซ้ำกับอุปกรณ์จริง | ⬜ ยืนยันซ้ำ |
| T6 | Client isolation (กัน sniffing ระหว่างลูกค้า) | เครื่อง A ping/nmap เครื่อง B ไม่สำเร็จ | ⬜ |
| T7 | จำลอง ARP spoof | ไม่สามารถดักข้อมูลเครื่องอื่นได้ | ⬜ |
| T8 | Admin Panel เข้าจากฝั่งลูกค้าไม่ได้ | connection refused/timeout | ⬜ |
| T13 | ความแม่นยำนาฬิกา (chrony) | offset < 10 ms | ⬜ |
| T14 | Load test 20 client พร้อมกัน | ไม่มี log drop, response < 2 วิ | ⬜ |
| T15 | Recovery หลังไฟดับ | ทุก service กลับมาเองภายใน 90 วิ | ⬜ |

## กลุ่มที่ 4 — ทดสอบด้วยตนเอง (manual, ก่อนสาธิต)

- [ ] เดินผ่านขั้นตอน `install.sh` เต็มรูปแบบบน Raspberry Pi จริง 1 รอบ ไม่ใช้ `--skip-*` ใด ๆ
- [ ] เปิด `/setup` จากเครื่องอื่นในวง LAN ยืนยันว่าใช้งานได้จริงผ่าน HTTPS self-signed
- [ ] ออก voucher จริง 1 ใบ แล้วลองต่อ Wi-Fi ด้วยมือถือจริง
- [ ] ปิด-เปิดเครื่อง Pi ระหว่างมีการเชื่อมต่อค้างอยู่ ดูว่า session/log สอดคล้องกันหรือไม่
- [ ] รัน `python -m logger.integrity` แล้วลองแก้ไฟล์ log เก่าด้วยมือ ตรวจว่า `verify_chain` จับได้จริง

## หมายเหตุด้านความซื่อสัตย์ทางวิศวกรรม

การทดสอบในกลุ่มที่ 1 ใช้ "mock gateway" ที่เราคุมทั้งสองฝั่ง (เข้ารหัสด้วยฟังก์ชันเดียวกับที่
เราจะถอดรหัส) เพราะไม่มี openNDS binary จริงให้ทดสอบในสภาพแวดล้อมพัฒนา นี่ยืนยันได้ว่า
"โค้ดของเราสอดคล้องกันเอง" (internal consistency) แต่ **ยังไม่ยืนยันว่าคุยกับ openNDS ตัวจริงได้
100%** — ต้องทำกลุ่มที่ 3 บน Raspberry Pi จริงก่อนจึงจะเชื่อมั่นได้เต็มที่ ระบุไว้ชัดเจนใน
`app/fas/opennds_proto.py` เช่นกัน
