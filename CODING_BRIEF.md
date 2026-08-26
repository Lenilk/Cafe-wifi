# CODING BRIEF — งานที่ต้องเขียนโค้ดรอบถัดไป (Cafe Wi-Fi Gateway)

> **สำหรับ Claude session ใหม่:** อ่านไฟล์นี้ให้จบก่อนแตะอะไรทั้งสิ้น แล้วค่อยเปิด `PROJECT_PLAN.md`
> (ไฟล์นี้คือ "ใบสั่งงาน" · `PROJECT_PLAN.md` คือ "สมองกลาง" ที่เก็บบริบททั้งหมด)
>
> เขียนเมื่อ 2026-08-26 · ที่มา: การรีวิวแผนงาน + อ่านโค้ดจริงทุกไฟล์ในทาร์บอล

---

## ⛔ 0. อ่านก่อน — กับดักเรื่องไฟล์ (พลาดตรงนี้ = งานหายทั้งรอบ)

โฟลเดอร์โปรเจกต์ **ไม่มีซอร์สโค้ดอยู่จริง** มีแค่นี้:

```
cafe-wifi/
├── PROJECT_PLAN.md              ← ใหม่ที่สุด (1,111 บรรทัด) ใช้ตัวนี้
├── install.sh                   ← ใหม่ที่สุด (1,503 บรรทัด) ใช้ตัวนี้
├── CODING_BRIEF.md              ← ไฟล์นี้
├── cafe-wifi-project-fixed.tar.gz   ← ซอร์สโค้ดจริงอยู่ในนี้ (2026-08-26)
├── cafe-wifi-project.tar.gz         ← ⛔ ของเก่า 2026-08-23 อย่าใช้เด็ดขาด
├── cafe-wifi-presentation.pptx
└── รายงานเล่ม/
```

**กับดัก:** ในทาร์บอล `-fixed` มี `install.sh` (1,363 บรรทัด) และ `PROJECT_PLAN.md` (1,098 บรรทัด)
ติดมาด้วย แต่ **ทั้งคู่เก่ากว่าที่รากโฟลเดอร์** ถ้าแตกทาร์บอลทับตรง ๆ จะย้อนงานหายไป
140 บรรทัดใน install.sh และ 13 บรรทัดในแผน

### ขั้นตอนตั้งต้นที่ถูกต้อง (ทำตามนี้เป๊ะ)

```bash
cd "C:/Users/lenul/OneDrive/เดสก์ท็อป/cafe-wifi"

# 1) สำรองของที่ใหม่กว่าไว้ก่อน (เก็บไว้ในโฟลเดอร์เดียวกัน ใช้ได้ทั้ง bash และ PowerShell)
cp PROJECT_PLAN.md PROJECT_PLAN.md.keep && cp install.sh install.sh.keep

# 2) แตกทาร์บอล (จะได้ app/ tools/ tests/ sql/ docs/ infra/)
#    หมายเหตุ: ทาร์บอลมีโฟลเดอร์ cafe-wifi/ ครอบอยู่ จึงต้องใช้ --strip-components=1
tar -xzf cafe-wifi-project-fixed.tar.gz --strip-components=1

# 3) เอาของใหม่กว่าคืนที่ (ทับตัวเก่าที่เพิ่งแตกออกมา) แล้วลบไฟล์สำรอง
mv PROJECT_PLAN.md.keep PROJECT_PLAN.md && mv install.sh.keep install.sh

# 3.5) ยืนยันว่าได้ของถูกตัว — ต้องได้ 1111 และ 1503
wc -l PROJECT_PLAN.md install.sh

# 4) ⭐ ทำ git ทันที — ตอนนี้โปรเจกต์ยังไม่มี .git เลยสักที่
git init && git add -A && git commit -m "baseline: import from cafe-wifi-project-fixed.tar.gz"
```

> **`git init` คืองานแรกที่สำคัญที่สุด** ตอนนี้บั๊ก 15 ตัวที่แก้ไปเมื่อ 2026-08-26 อยู่ในทาร์บอล
> ก้อนเดียว ไม่มี history ไม่มี backup · แถม `PROJECT_PLAN.md` D17/R11 อ้างว่า "โค้ด 2-อินเทอร์เฟซ
> เดิมยังอยู่ใน git history" ซึ่ง**ไม่จริง** เพราะไม่มี history
>
> ตรวจว่า `.gitignore` กัน `.env`, `secrets.env`, `*.tar.gz`, `.pytest_cache/` ก่อน commit

---

## 1. บริบทย่อของโปรเจกต์

โครงงาน ป.ตรี วิศวกรรมคอมพิวเตอร์ — ระบบ Captive Portal + บันทึก log ตาม พ.ร.บ.คอมพิวเตอร์ ม.26
บน Raspberry Pi 4B · รายละเอียดเต็มอยู่ใน `PROJECT_PLAN.md` (วัตถุประสงค์ O1-O4 ที่ §1,
Decision Log D1-D21 ที่ §2, schema ที่ §5, Task Board ที่ §9)

**สถานะปัจจุบัน:** โค้ด Phase 0-4 เขียนเกือบครบ เทสต์ 114 เคสผ่าน — **แต่ยังไม่เคยแตะฮาร์ดแวร์จริง
เลยสักครั้ง** (ไม่เคยรันกับ Raspberry Pi, openNDS binary, MariaDB, conntrack, dnsmasq ตัวจริง)

**สภาพแวดล้อมที่คุณจะทำงาน:** Windows + ไม่มี MariaDB + ไม่มี Linux
→ **เทสต์ทุกตัวที่เขียนใหม่ต้องรันผ่านบน Windows ด้วย mock/fake** ตามแบบที่ `tests/` ทำอยู่แล้ว
อย่าเขียนเทสต์ที่ต้องมี DB จริง

---

## 2. กติกาการทำงาน (ห้ามข้าม)

1. **ทำทีละงาน** ตามลำดับใน §4 · ห้ามทำรวบหลายงานในรอบเดียว
2. **ทุกงานต้องมีเทสต์** วางไว้ที่ `tests/test_<ชื่องาน>.py` และต้องรันผ่านจริง ไม่ใช่แค่เขียนไว้
3. **รันชุดเทสต์ทั้งหมดก่อนปิดงาน** — ต้องไม่มีเคสเดิมพัง
4. **อัปเดต `PROJECT_PLAN.md` ทุกครั้งที่ปิดงาน** — ติ๊ก §9 Task Board + เพิ่มแถวใน §10 Work Log
   (นี่คือกฎของโปรเจกต์นี้ ระบุไว้ที่หัวไฟล์แผน)
5. **`git commit` ทีละงาน** ข้อความสั้น ๆ ภาษาไทยหรืออังกฤษก็ได้ แต่ต้องบอกว่าแก้อะไร
6. **ห้าม `git push` หรือสร้าง PR** เว้นแต่เจ้าของโปรเจกต์สั่ง
7. **รายงานตามจริง** ถ้าเทสต์ไม่ผ่านให้บอกตรง ๆ พร้อม output · ถ้าข้ามงานไหนต้องบอกว่าข้ามและเพราะอะไร

### แบบแผนโค้ดที่มีอยู่แล้ว — ใช้ซ้ำ อย่าเขียนใหม่

| ต้องการ | ใช้ตัวนี้ |
|---|---|
| ต่อ DB | `from common.db import query_one, query_all, execute, get_conn` · `execute()` คืน **rowcount** |
| บันทึก audit | `from common import audit` → `audit.log(action, staff_id=, target=, client_ip=, detail=)` · ค่าคงที่ action มีให้แล้ว (`audit.REVEAL_NATID`, `audit.EXPORT_LOG`, …) |
| เข้ารหัส/แฮช | `from common import crypto` → `natid_hash`, `natid_encrypt/decrypt`, `mask_natid`, `hash_password`, `verify_password`, `gen_voucher_code`, `valid_thai_id` |
| ตรวจ integrity ของ log | `from logger.integrity import verify_chain, seal_directory, SqlManifestStore` |
| กันสิทธิ์หน้า Admin | decorator `@login_required` / `@admin_required` (นิยามใน `app/admin/app.py`) |
| IP ผู้เรียกจริง | `client_ip()` ใน `app/admin/app.py` — **ห้าม**อ่าน `X-Forwarded-For` ตรง ๆ (เคยเป็นบั๊ก C3) |
| route แบบใหม่ | `@app.get(...)` / `@app.post(...)` (โค้ดเดิมใช้แบบนี้ปนกับ `@app.route`) |
| template | `{% extends "base.html" %}` · Bootstrap 5 แบบ local ไม่ใช้ CDN |
| สคริปต์ใน `tools/` | รันด้วย `python -m tools.<ชื่อ>` · อ่านค่าจาก `os.environ` · มี `def main() -> int` |
| ภาษาใน comment/UI | **ภาษาไทย** ตามที่โค้ดเดิมทำทั้งโปรเจกต์ |

**ทุกอย่างที่แตะข้อมูลอ่อนไหว (เลขบัตร ปชช. / log ผู้ใช้) ต้องลง `audit_log` เสมอ** — นี่คือ
ข้อกำหนด PDPA ที่โปรเจกต์นี้ยึดถือ (§6.2 ในแผน)

---

## 3. บริบทระบบที่ต้องรู้

- **โครงสร้างเครือข่าย:** one-armed router (D17) — Pi ต่อเราเตอร์ด้วยสาย RJ45 เส้นเดียว
  eth0 มี 2 IP: `192.168.1.2/24` (uplink/ผู้ดูแล) + `10.10.0.1/24` (ลูกค้า)
- **พอร์ต:** Admin Panel = **8443** (https ผ่าน nginx) · Captive Portal = **8080** (http)
  gunicorn อยู่หลังที่ 18443/18080 ฟังแค่ 127.0.0.1
  > ⚠️ `PROJECT_PLAN.md` §3.2, §3.3, §4, §6.4 และ T8 เขียน `8081` ไว้ซึ่ง**ผิด** (`install.sh:49`
  > ตั้ง `ADMIN_PORT="8443"`) — ถ้ามีโอกาสช่วยแก้ให้ตรงกันด้วย
- **ไดเรกทอรีบนเครื่องจริง:** `ETC_DIR=/etc/cafe-wifi` · `OPT_DIR=/opt/cafe-wifi` ·
  `LOG_DIR=/var/log/cafe-wifi` · venv ที่ `/opt/cafe-wifi/venv`
- **งานตามเวลา:** `cafe-maintenance.timer` (ทุกวัน 03:30 — purge/backup/integrity/check_time)
  และ `cafe-enforce.timer` (ทุก 5 นาที — บังคับอายุ voucher)
- **ตารางใน DB:** `staff`, `customer`, `voucher`, `device`, `portal_session`, `conn_log`,
  `dns_log`, `audit_log` (ดู `sql/001_schema.sql` หรือ §5 ในแผน)

---

## 4. รายการงาน — ทำตามลำดับนี้

> ทุกงานคือการ**ปิดช่องว่างที่แผนสัญญาไว้แล้วแต่ยังไม่มีจริงในโค้ด** ไม่ใช่ฟีเจอร์ที่คิดขึ้นใหม่

### 🔴 ชุด A — ทำก่อน (ครึ่งวัน ปิดความเสี่ยงด้านกฎหมาย)

#### N1 · แจ้งเตือนดิสก์ใกล้เต็ม — `tools/check_disk.py`

**ปัญหา:** `grep -c "disk\|df -h\|80%" install.sh` = **0** ทั้งโปรเจกต์ไม่มีสักบรรทัด
ทั้งที่ Risk Register R5 เขียนแผนรับมือไว้ว่า "alert เมื่อ disk > 80%"
**ดิสก์เต็ม = log หยุดเขียน = ผิด ม.26 ทันที โดยไม่มีใครรู้ตัว**

**ต้องทำ:**
- สคริปต์ใหม่ `tools/check_disk.py` ใช้ `shutil.disk_usage()` ตรวจ `LOG_DIR` และ `/`
- เกณฑ์จาก env `DISK_WARN_PCT` (default 80) และ `DISK_CRIT_PCT` (default 90)
- เกินเกณฑ์ → เขียน WARNING/CRITICAL ลง `${LOG_DIR}/alert.log` **และ** ลงแถวใน `audit_log`
  (`action='disk_alert'`, `detail` = เปอร์เซ็นต์ + พื้นที่เหลือ)
- เพิ่ม `ExecStart=-${VENV_DIR}/bin/python -m tools.check_disk` เข้า `cafe-maintenance.service`
  ใน `install.sh` (ต่อจาก `tools.backup_db`)

**ผ่านเมื่อ:** เทสต์ mock `shutil.disk_usage` ครอบ 3 กรณี (ปกติ / เกิน warn / เกิน crit)
ยืนยันว่ามีแถว `audit_log` เฉพาะตอนเกินเกณฑ์ · `bash -n install.sh` ยังผ่าน

---

#### N2 · ปุ่ม "ตรวจสอบความถูกต้องของ log" ในหน้า Admin

**ทำไมคุ้ม:** `logger/integrity.py` มี `verify_chain()` พร้อมใช้และเทสต์ผ่านแล้ว
แค่ต่อปุ่ม → ได้ **T12 ที่สาธิตสดต่อหน้ากรรมการได้ใน 20 วินาที**
(แก้ไฟล์ log 1 ตัวอักษร → กดปุ่ม → ระบบจับได้)

**ต้องทำ:**
- route ใหม่ `@app.post("/logs/verify")` + `@admin_required` ใน `app/admin/app.py`
- เรียก `verify_chain(SqlManifestStore(...), Path(LOG_DIR))` แล้วแสดงผลเป็นตาราง
  `IntegrityIssue` (ไฟล์ไหน ผิดยังไง)
- ลง `audit_log` ทุกครั้งที่กด (`action='verify_integrity'`)
- ปุ่มอยู่ในหน้า dashboard + template ใหม่ `logs_verify.html`

**ผ่านเมื่อ:** เทสต์ครอบ 2 กรณี — chain สมบูรณ์ (ไม่มี issue) กับ chain ถูกแก้ (มี issue)
+ ยืนยันว่า staff ธรรมดากดไม่ได้ (403)

---

#### N3 · `chattr +a` บน log ที่หมุนแล้ว

§6.1 ระบุเป็นข้อกำหนด integrity ตาม ม.26 แต่ยังไม่ได้ทำ
เพิ่ม `postrotate` ใน logrotate config ที่ `install.sh` เขียน ให้สั่ง `chattr +a` กับไฟล์ที่หมุนแล้ว
· ต้องกันกรณี filesystem ไม่รองรับ (`chattr` ล้มเหลว → warning ไม่ใช่ error)

**ผ่านเมื่อ:** `bash -n install.sh` ผ่าน + `--dry-run` แสดงคำสั่งถูกต้อง

---

#### N4 · Backup ออกนอกเครื่อง

§11.1 ข้อ 4 เขียนเงื่อนไขไว้เองว่า "ถ้าใช้ SD card **ต้อง** backup ออกนอกการ์ด" แต่ยังไม่ได้ทำ
· เพิ่มขั้นตอน copy ไฟล์ backup ไปยัง path จาก env `OFFSITE_BACKUP_DIR`
(ถ้าไม่ตั้ง = ข้าม พร้อม log ว่าข้ามเพราะอะไร) ใน `tools/backup_db.py`

**ผ่านเมื่อ:** เทสต์ครอบ 3 กรณี — ไม่ตั้ง env / ตั้งแล้วปลายทางมีอยู่ / ปลายทางเขียนไม่ได้

---

### 🟠 ชุด B — สัปดาห์ถัดไป

#### N5 · หน้า System Health (`/health` ปัจจุบันคืนแค่ `{"status":"ok"}`)

ยกระดับเป็นหน้าเว็บจริงที่แสดง: **disk %** (คำนวณสดด้วย `shutil.disk_usage`) ·
**chrony offset** (อ่านจากไฟล์ที่ `check_time.sh` เขียน — ปิด T13) · service ขึ้น/ลง ·
session ที่ active · จำนวน log rows วันนี้ · วันที่ seal hash chain ล่าสุด · alert ล่าสุดจาก N1

> เก็บ `/health` เดิมที่คืน JSON ไว้ด้วย (มีเทสต์อ้างอิงอยู่) — เพิ่มหน้า HTML เป็น `/status` แทน
> **นี่คือหน้าจอที่ทำให้ระบบดูเป็นระบบจริงตอนสาธิต**

#### N6 · DSR — ลบข้อมูลรายบุคคลตามคำขอ (PDPA)

§6.2 ข้อ 6 ประกาศสิทธิ์นี้ไว้ในนโยบายความเป็นส่วนตัวแล้ว แต่โค้ดมีแค่ `/reveal` กับ `/block`
· `purge_old_data.py` ลบตามอายุเท่านั้น ลบรายคนไม่ได้

- route `@app.post("/customers/<int:cid>/erase")` + `@admin_required` + **บังคับกรอกเหตุผล**
- ใช้ตรรกะ anonymize ที่มีอยู่แล้วใน `tools/purge_old_data.py` (ล้าง `natid_hash/natid_enc/natid_masked`
  แต่**คงแถวไว้** — ห้าม `DELETE` เพราะชน `fk_voucher_customer` ดู **D20** ในแผน)
- ลง `audit_log` (`action='erase_customer'`) พร้อมเหตุผล

#### N7 · QR code + สลิปพิมพ์ได้ ในหน้า `/issue/result`

KPI §14 ตั้งไว้ว่า "ออก voucher 1 ใบ ≤ 30 วินาที" — ถ้าพนักงานต้องอ่านรหัส base32 8 ตัว
ให้ลูกค้าฟังทีละตัวแล้วลูกค้าพิมพ์ผิด จะเกิน 30 วินาทีแน่นอน
· เพิ่ม QR (ฝัง `qrcode` เป็น SVG/base64 inline — **ห้ามใช้ CDN**) + CSS `@media print`
· เพิ่ม `qrcode` ลง `app/requirements.txt`

#### N8 · ตัดสินใจเรื่องฟีเจอร์ครึ่งใบ 2 ตัว

- **`quota_mb`** — `tools/enforce_voucher_expiry.py` มี `mark_used_up_vouchers()` พร้อมใช้
  แต่หน้า `/issue` ไม่มีช่องกรอก → ไม่มี voucher ใบไหนตั้งค่านี้ได้จริง
- **2FA** — `pyotp==2.9.0` อยู่ใน `requirements.txt` แต่**ไม่มีไฟล์ไหน import เลย**
  และ `staff.totp_secret` ใน schema ไม่ถูกใช้

**เลือกทางเดียวต่อฟีเจอร์: ทำให้จบ หรือ ถอดออก** (ถ้าถอด ต้องลบ dependency/คอลัมน์ที่ไม่ใช้ด้วย)
· **ถามเจ้าของโปรเจกต์ก่อนตัดสินใจ** เพราะกระทบสิ่งที่จะเขียนในเล่มรายงาน

---

### 🟡 ชุด C — งานหลักที่เหลือ

#### N9 · หน้าเว็บค้น log ใน Admin ⭐ (~1-2 วัน)

**นี่คือช่องว่างที่ใหญ่ที่สุด** — DoD ของ Phase 4 เขียนว่า "ค้นย้อนกลับใน Admin เจอครบ"
และ **T10 ทดสอบไม่ได้เลยถ้าไม่มีหน้านี้** ปัจจุบันมีแค่ export ผ่าน command line

**ต้องทำ:**
- `@app.get("/logs")` + `@login_required` — ค้น `conn_log` และ `dns_log`
- กรองด้วย: ช่วงเวลา (**บังคับกรอก ห้ามค้นแบบไม่จำกัดช่วง**), MAC, โดเมน, IP
- **แบ่งหน้า (pagination) + จำกัดผลลัพธ์สูงสุดต่อหน้า** — Pi 4B RAM จำกัด อย่า query แบบไม่มี LIMIT
- แสดง mapping ย้อนกลับ: `conn_log.mac → device → voucher → customer` โดย
  **แสดงเลขบัตรแบบ masked เท่านั้น** (role `staff` ห้ามเห็นเลขเต็ม — §6.2 ข้อ 5)
- **ลง `audit_log` ทุกครั้งที่ค้น** (`action='search_log'`, `detail` = เงื่อนไขที่ใช้ค้น)
  — ทั้งเพื่อ PDPA และเป็นจุดขายตอนนำเสนอ

**ผ่านเมื่อ:** เทสต์ครอบ — ค้นด้วย MAC เจอ, ค้นด้วยโดเมนเจอ, ไม่กรอกช่วงเวลาถูกปฏิเสธ,
pagination ทำงาน, มีแถว `audit_log` ทุกครั้ง, staff เห็น masked ไม่ใช่เลขเต็ม

#### N10 · Bypass Detector (T17) ⭐ (~1 วัน)

`PROJECT_PLAN.md` §3.1.4 ชั้นที่ 4 เขียนเองว่า *"ไม่ได้ป้องกัน แต่มีคุณค่าเชิงวิชาการสูง"*
**แต่ไม่มีไฟล์นี้ในโปรเจกต์ ไม่มีใน §7 layout และ Task Board มีแต่ "ทดสอบ T17"
โดยไม่มีงานให้ "เขียน" มัน** — คือมีแผนจะทดสอบสิ่งที่ยังไม่มีใครสร้าง

**ต้องทำ:** `app/logger/bypass_detector.py` — อ่าน ARP table (มี `logger/netutil.py` ช่วยอยู่แล้ว)
เฝ้าวง uplink `192.168.1.0/24` → เจอ IP/MAC ที่ไม่ใช่ Pi หรือเราเตอร์ → บันทึกลงตาราง alert + audit
· ต้องเพิ่มตารางใหม่ใน `sql/` (ไฟล์ migration ใหม่ เช่น `005_bypass_alert.sql` — **อย่าแก้
`001_schema.sql` ที่ apply ไปแล้ว**)

**ทำไมคุ้มที่สุด:** นี่คือ**ฟีเจอร์เดียวที่แปลงข้อจำกัด D19 จาก "จุดอ่อนที่ต้องขอโทษ"
ให้กลายเป็น "ผลการวิจัยที่วัดเป็น % ได้"** — บทที่ 4 จะมีตาราง "ทดลอง bypass 20 ครั้ง
ตรวจจับได้ 18 ครั้ง (90%)" ซึ่งเป็นตัวเลขจริงที่ทีมสร้างเอง

---

## 5. ⛔ สิ่งที่ห้ามทำในรอบนี้

| ห้าม | เหตุผล |
|---|---|
| แตะสถาปัตยกรรมเครือข่าย (D17 / โหมด wlan0 / macvlan / ซื้อ USB Ethernet) | **ยังไม่ตัดสินใจ** เจ้าของโปรเจกต์ต้องคุยกับอาจารย์ก่อน · ถ้าแชทนี้ไปแก้ `install.sh` ส่วน network จะชนกับการตัดสินใจทีหลัง |
| ติดตั้ง Grafana / Prometheus / Netdata | N5 (หน้า Health ~3 ชม.) ให้ผลเท่ากันในบริบทนี้ · Grafana กินเวลาเป็นสัปดาห์ |
| ทำ WPA2-Enterprise / 802.1X | D16 = stretch goal · อาจารย์บอก "เอาที่พอไหว" |
| **ตัด FreeRADIUS ออกเงียบ ๆ** | §1 ขอบเขต เขียนว่า "Pi ทำหน้าที่ Gateway + **RADIUS Server** + Log Server" — ถ้าจะตัดต้องคุยกับอาจารย์และแก้ขอบเขตเป็นลายลักษณ์อักษรก่อน ไม่ใช่แค่ไม่ทำ |
| เพิ่ม LINE Notify / mobile app / ระบบชำระเงิน | ไม่มีในวัตถุประสงค์ O1-O4 |
| แก้ `sql/001_schema.sql` | ถ้าต้องเพิ่มตาราง ให้สร้างไฟล์ migration ใหม่ |
| ใช้ CDN ใน template | ทั้งโปรเจกต์ใช้ asset แบบ local (ระบบนี้อยู่หลัง captive portal ที่ยังไม่มีเน็ต) |
| `git push` / เปิด PR | ต้องรอเจ้าของโปรเจกต์สั่ง |

---

## 6. รูปแบบการรายงานเมื่อปิดแต่ละงาน

รายงานสั้น ๆ ให้ครบ 5 ข้อ:

1. **ทำอะไรไป** — ไฟล์ไหนบ้าง เพิ่ม/แก้อะไร
2. **เทสต์** — เพิ่มกี่เคส รันแล้วผลเป็นยังไง (แปะ output จริง) ชุดเดิมยังผ่านครบไหม
3. **สิ่งที่ยังทดสอบไม่ได้** — ระบุตรง ๆ ว่าอะไรต้องรอฮาร์ดแวร์/MariaDB จริง
   (ใช้เครื่องหมาย 🔶 ตามแบบที่แผนใช้อยู่)
4. **อัปเดตแผนแล้ว** — ติ๊ก §9 ข้อไหน เพิ่ม §10 Work Log แถวไหน
5. **บั๊กที่เจอระหว่างทาง** — โปรเจกต์นี้มีธรรมเนียมบันทึกบั๊กจริงทุกตัวลง §10 พร้อมเหตุผล
   ว่าทำไมมันเกิด (ดูตัวอย่างท้าย §17 ในแผน — เขียนได้ดีมาก ให้รักษามาตรฐานนั้นไว้)

---

## 7. ลำดับที่แนะนำ

```
วันแรก        git init → N1 → N2 → N3 → N4        (ปิดความเสี่ยงด้านกฎหมายทั้งหมด)
สัปดาห์ถัดไป   N5 → N6 → N7 → N8
งานหลัก       N9  (หน้าค้น log — ปิด DoD Phase 4 + T10)
ก่อน Phase 5   N10 (Bypass Detector — แปลงข้อจำกัดเป็นผลวิจัย)
```

รวมประมาณ **6-7 วันทำงาน** แล้วจะไม่เหลือช่องว่างระหว่าง "สิ่งที่แผนบอกว่ามี"
กับ "สิ่งที่สาธิตได้จริง"

---

## 8. คำสั่งเปิดงานสำหรับเจ้าของโปรเจกต์

พิมพ์แบบนี้ในแชทใหม่:

```
อ่าน CODING_BRIEF.md ให้จบก่อน แล้วทำงาน N1 ตามนั้น
```
