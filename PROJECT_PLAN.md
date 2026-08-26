# แผนงานโปรเจกต์: Cafe Wi-Fi Gateway & Management System บน Raspberry Pi

> **ไฟล์นี้คือ "สมองกลาง" ของโปรเจกต์** — ออกแบบมาให้ Claude session ใหม่ (หรือคนในทีม) อ่านไฟล์นี้ไฟล์เดียว
> แล้วทำงานต่อได้ทันทีโดยไม่ต้องถามซ้ำ ทุกครั้งที่ตัดสินใจอะไรใหม่ / ทำงานเสร็จ ให้อัปเดตไฟล์นี้ด้วย

---

## 0. วิธีใช้ไฟล์นี้กับ Claude

พิมพ์ประมาณนี้ตอนเปิด session ใหม่:

```
อ่าน PROJECT_PLAN.md แล้วทำงานต่อจาก [ชื่องานใน §9 Task Board]
```

**ไฟล์ที่มีอยู่แล้วในโปรเจกต์** (ดูรายละเอียดใน §7 — เกือบครบทุก component ของ Phase 0-4 แล้ว
ยกเว้นสิ่งที่ต้องมีฮาร์ดแวร์จริงถึงจะทดสอบต่อได้):
`install.sh` (ตัวติดตั้งสากล, §17) · `app/common/{crypto,db,audit}.py` ·
`app/admin/app.py` + templates (Admin Panel + Setup Wizard) ·
`app/fas/{app.py,opennds_proto.py}` + templates (Captive Portal) ·
`app/logger/{conn_collector,dns_collector,integrity,netutil,run_all}.py` ·
`sql/001_schema.sql`, `sql/003_partitions.sql` ·
`tools/{reset_admin,purge_old_data,export_evidence,backup_db,enforce_voucher_expiry}.py` ·
`tests/` (151 เคสที่ pytest เก็บได้ — 147 ยืนยันผ่านจริงบนเครื่องนี้, อีก 4 ต้องรันบน Linux จริง) ·
`docs/{privacy-policy-th,test-plan}.md` · `README.md`

**สิ่งที่ยังไม่มี/ยังไม่ทำ:** หน้าเว็บ Admin สำหรับค้นหา log (มีแค่ export ผ่าน command line),
`sql/004_freeradius.sql` (Phase 5), การส่ง backup ไป remote จริง ๆ (rclone/scp ข้ามเครื่อง —
มี copy ไป path ในเครื่อง/mount point ที่เข้าถึงได้ผ่าน `OFFSITE_BACKUP_DIR` แล้วตั้งแต่ N4),
การทดสอบบนฮาร์ดแวร์จริงทั้งหมด (Raspberry Pi, openNDS
binary, `ndsctl deauth`, MariaDB จริง, conntrack/dnsmasq จริง), เล่มรายงานและสไลด์

> 🟢 **อัปเดต 2026-08-26 — ไล่หาบัคทั้งโปรเจกต์ 4 รอบ พบ+แก้รวม 37 บั๊กจริง (13 รอบแรก
> + 13 รอบ self-review + 8 รอบตรวจรอยต่อ + 2-3 ที่พบเพิ่มระหว่างแก้จริง) — รายละเอียดเต็มใน §10 Work Log**
> จุดสำคัญที่สุดที่แก้: **hash chain integrity เคยไม่เคยผนึกไฟล์เลยสักไฟล์บนเครื่องจริง** (C1),
> **งาน maintenance รายคืนเคย crash ทั้งชุดเพราะ FK constraint** (C2), **audit_log/rate-limit
> ปลอมค่าได้ผ่าน X-Forwarded-For** (C3), **ไม่มี backup DB เลยในระบบ** (H4), **อายุ voucher
> ไม่ถูกบังคับจริงที่ชั้นเครือข่าย** (H3), **`GRANT ALL PRIVILEGES`+`chrony.conf` เขียนทับ
> ทั้งไฟล์**, และ **rate-limit ในหน่วยความจำชนกับ `--workers 2`** — ทั้งหมดแก้แล้วพร้อมเทสต์
> ยืนยัน ยกเว้นส่วนที่ต้องมีฮาร์ดแวร์จริง (`ndsctl deauth`, R11) ซึ่งทำโค้ดพร้อมไว้แล้วแต่ยัง
> ยืนยันไม่ได้จนกว่าจะมี Pi จริง · **บทเรียนสำคัญจาก 4 รอบนี้**: การแก้บั๊กรอบหนึ่งสร้างบั๊ก
> ใหม่รอบถัดไปได้เสมอถ้าไม่ทดสอบจริง หรือชนกับการแก้อีกจุดที่ทำไปก่อนหน้า (เจอเอง 4 ครั้ง:
> gzip pipe ผิด, execute() คืนค่าผิดความหมาย, chrony.conf truncate race, GRANT รอบ 3 ชน
> กับ mysqldump flags ที่เขียนไว้ตั้งแต่รอบ 2) — ทุกครั้งจับได้เพราะรันจริงเทียบผลหรือไล่อ่าน
> รอยต่อระหว่างการแก้คนละรอบก่อน ship ไม่ใช่อ่านโค้ดจุดเดียวแล้วเชื่อว่าถูก
>
> 🟢 **อัปเดต 2026-08-23 (ค่ำ) — `install.sh` แก้เป็นโหมดสาย LAN เส้นเดียวเสร็จแล้ว**
> โครงสร้างเครือข่ายเปลี่ยนจาก "2 อินเทอร์เฟซ (WAN/LAN แยกกัน)" เป็น
> **"สาย LAN เส้นเดียว (one-armed router)"** ตาม **D17/D18/D19** — ใช้แค่ RPi 4B + เราเตอร์บ้าน
> · **โค้ด `install.sh` แก้ครบทั้ง 10 จุดตาม §3.1.6 แล้ว** — `bash -n` ผ่าน, `--dry-run` ทั้งแบบ
> ค่า default และแบบระบุ flag ครบผ่านหมด, nftables ruleset ที่ generate ออกมาตรวจสอบด้วย
> `nft -c` ตัวจริงแล้วว่า syntax ถูกต้อง (ดู §17 สถานะการทดสอบ) · ชุดเทสต์ Python 100/100 ยังผ่าน
> (ไม่ถูกกระทบเพราะแก้แค่ install.sh) · **ห้ามรองรับโหมด 2 อินเทอร์เฟซอีก** — เจ้าของโครงงานสั่งตัดออก
> · **ยังไม่เคยรันบนฮาร์ดแวร์จริง** — สิ่งที่ยังไม่ยืนยันคือ R11 (openNDS ทำงานบนอินเทอร์เฟซเดียวได้จริงไหม)
> ซึ่งเป็นความเสี่ยงอันดับ 1 ที่เหลืออยู่ อ่าน §3.1 ทั้งหัวข้อก่อนไปติดตั้งจริง โดยเฉพาะ §3.1.4
> (ช่องโหว่ bypass), §3.1.6 (รายละเอียดการแก้โค้ดที่ทำไปแล้ว), และ §3.1.7 (กัน SSH หลุด)

**กติกาสำหรับ Claude ที่มาทำงานต่อ:**

1. อ่าน §1 (สรุปโปรเจกต์) + §2 (Decision Log) + §9 (Task Board) ก่อนเสมอ
2. อย่าเปลี่ยนการตัดสินใจใน §2 โดยไม่บอก — ถ้าจะเปลี่ยน ให้เพิ่มบรรทัดใหม่ใน Decision Log พร้อมเหตุผล
3. งานเสร็จแล้ว → เปลี่ยน `[ ]` เป็น `[x]` ใน §9 และเขียนสิ่งที่ได้ลง §10 (Work Log)
4. โค้ด/ไฟล์คอนฟิกที่เขียนจริง ให้วางไว้ตามโครงสร้างใน §7 (Repository Layout)
5. ถ้าเจอเรื่องกฎหมาย/PDPA ให้ยึด §6 เป็นหลัก — เป็นส่วนที่ห้ามลัด
6. แก้ `install.sh` แล้วต้องรัน `bash -n install.sh` และ `./install.sh --dry-run` ทุกครั้ง
7. ห้ามใส่ค่า secret จริงลงไฟล์ใด ๆ ในรีโป — ค่าจริงอยู่ที่ `/etc/cafe-wifi/secrets.env` เท่านั้น

---

## 1. สรุปโปรเจกต์ (Context)

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อไทย | ระบบจัดการเครือข่ายอินเทอร์เน็ตไร้สายสำหรับคาเฟ่ พร้อมการยืนยันตัวตนด้วยเลขประจำตัวประชาชนและการบันทึกประวัติการใช้งานเครือข่ายด้วย Raspberry Pi |
| ชื่ออังกฤษ | Cafe Wi-Fi Management System with National ID Authentication and Network Usage Logging using Raspberry Pi |
| ประเภท | โครงงานวิจัยระดับปริญญาตรี สาขาวิศวกรรมคอมพิวเตอร์และการสื่อสาร |
| ทีม | นายลีนิกซ์ จันทรังษี (666415850027), นายลีนุกซ์ จันทรังษี (666415850029) |
| รหัสเอกสาร | Project-01 |

### วัตถุประสงค์ (จากข้อเสนอโครงการ)

| # | วัตถุประสงค์ | แมปกับ Phase |
|---|---|---|
| O1 | สร้างระบบควบคุมการเข้าใช้งาน Wi-Fi (Captive Portal) ด้วย Raspberry Pi | P1, P2 |
| O2 | พัฒนา Admin Panel ให้พนักงานลงทะเบียนผู้ใช้ด้วยเลขบัตรประชาชนเพื่อสร้างรหัสผ่าน | P3 |
| O3 | พัฒนาระบบดักจับแพ็กเก็ตและบันทึก Log การเชื่อมต่อ | P4 |
| O4 | เพิ่มความปลอดภัยในเครือข่ายและป้องกันการโจมตีภายในวง LAN | P2, P5 |

### ขอบเขต (Scope)

- Raspberry Pi ทำหน้าที่ Network Gateway + RADIUS Server + Log Server
- UI 2 ส่วน: หน้าเว็บพนักงาน (Admin Panel) และหน้า Login ลูกค้า (Captive Portal)
- เลขบัตรประชาชน 13 หลัก = ตัวระบุผู้ใช้, ระบบสุ่ม Password ให้
- เก็บ Connection Log / DNS Log ได้อย่างน้อย 90 วัน

---

## 2. Decision Log (การตัดสินใจเชิงสถาปัตยกรรม)

> บรรทัดที่มี ⚠️ = เป็นการ**แก้ไข/ปรับ**จากข้อเสนอโครงการเดิม พร้อมเหตุผล ควรอธิบายให้อาจารย์ที่ปรึกษาทราบ

| ID | การตัดสินใจ | เหตุผล | สถานะ |
|---|---|---|---|
| D1 | ใช้ **openNDS v10.x** เป็น Captive Portal engine แทนการเขียน redirect เอง | Production-grade, จัดการ nftables/firewall เอง, มี FAS ให้เขียน logic เองได้เต็มที่, รองรับ OS captive-portal detection ของ iOS/Android/Windows ครบ | ✅ ตัดสินใจแล้ว |
| D2 | Backend เขียนด้วย **Python 3 + Flask** (Jinja2 template → HTML/CSS ตามข้อเสนอ) | ทีมคุ้นเคย, ecosystem crypto/DB ดี, deploy ด้วย Gunicorn + Nginx ได้ | ✅ |
| D3 | DB = **MariaDB** | FreeRADIUS มี schema มาตรฐานรองรับตรง ๆ (radcheck/radacct), รองรับ concurrent write จาก log pipeline ดีกว่า SQLite | ✅ |
| D4 | **FreeRADIUS อยู่ใน Phase 5 (optional/เสริม)** ไม่ใช่ core auth path | Captive Portal ยืนยันตัวตนผ่าน FAS ได้เลยโดยไม่ต้องมี RADIUS — RADIUS เพิ่มเข้ามาเพื่อ (ก) ให้ตรงขอบเขตข้อ 3.1 (ข) ทำ Accounting/session quota (ค) เผื่อขยายเป็น WPA2-Enterprise | ✅ |
| D5 | ⚠️ **ไม่เก็บ payload ของแพ็กเก็ต** — เก็บเฉพาะ metadata (5-tuple, ขนาด, เวลา) + DNS query | เก็บ payload = ละเมิด PDPA ร้ายแรง + กินพื้นที่มหาศาล + กฎหมายไม่ได้บังคับ (มาตรา 26 ต้องการ "ข้อมูลจราจร" ไม่ใช่เนื้อหา) | ✅ |
| D6 | ⚠️ **ไม่เก็บเลขบัตรประชาชนแบบ plaintext** — เก็บ HMAC-SHA256 (สำหรับค้นหา) + AES-256-GCM ciphertext (สำหรับถอดตามหมายศาล) + masked (สำหรับแสดงผล) | PDPA: ต้องมีมาตรการรักษาความมั่นคงปลอดภัยที่เหมาะสม; เลขบัตร ปชช. รั่วไหลคือความเสียหายถาวร | ✅ |
| D7 | ~~ต้องมี USB3 Ethernet adapter~~ → **ยกเลิก แทนที่ด้วย D17** | เดิมออกแบบให้แยก WAN/LAN เป็น 2 อินเทอร์เฟซ · เปลี่ยนเป็นโหมดสาย LAN เส้นเดียวตาม D17 (2026-08-23) | ❌ ยกเลิกแล้ว |
| D8 | ⚠️ **ใช้เราเตอร์บ้านเป็นตัวปล่อย Wi-Fi** ไม่ใช้ Wi-Fi ในตัว RPi เป็น AP หลัก | wlan0 ในตัว RPi รับ client พร้อมกันได้จำกัด (~10-15) และ throughput ต่ำ; เราเตอร์บ้านที่มีอยู่แล้วทำหน้าที่นี้ได้ดีกว่าและไม่ต้องซื้อเพิ่ม (แต่ยังทำ hostapd เป็น demo/fallback ได้) | ✅ ปรับตาม D17 |
| D9 | ⚠️ **Client Isolation ต้องเปิดที่เราเตอร์** (AP isolation / "แยกผู้ใช้ไร้สาย") | นี่คือมาตรการหลักที่ตอบวัตถุประสงค์ O4 "ป้องกันการดักจับข้อมูลในวง LAN" — Pi อย่างเดียวป้องกันไม่ได้ถ้า client คุยกันเองผ่าน Wi-Fi โดยไม่ผ่าน Pi · ⚠️ เราเตอร์บ้านราคาถูกบางรุ่น**ไม่มี**ฟีเจอร์นี้ ต้องตรวจสอบก่อน (ดู §3.1.3) | 🔶 ต้องยืนยันว่าเราเตอร์รองรับ |
| D10 | OS = **Raspberry Pi OS Lite 64-bit (Debian 13 "Trixie")** | เวอร์ชันปัจจุบัน, nftables เป็น default firewall, systemd-timesyncd/chrony พร้อม | ✅ |
| D11 | Log rotation: เก็บ **90 วันขั้นต่ำ, purge อัตโนมัติที่ 180 วัน** | กฎหมายบังคับ ≥90 วัน; PDPA บอกห้ามเก็บนานเกินจำเป็น → ตั้งเพดานไว้ | ✅ |
| D12 | **ติดตั้งทั้งระบบด้วย `install.sh` ไฟล์เดียว** รองรับ apt/dnf/yum/pacman/zypper/apk | ย้ายเครื่องได้ ติดตั้งซ้ำได้ ไม่ผูกกับ Raspberry Pi OS — ตอนสาธิตถ้า Pi พังยังย้ายไป VM/แล็ปท็อปทันได้ (แผนสำรอง R9) | ✅ ทำแล้ว |
| D13 | **สร้างบัญชีผู้ดูแลระบบหลักผ่านหน้าเว็บ `/setup`** ด้วย one-time token ไม่ใช่ seed รหัสผ่านตายตัวใน SQL | รหัสผ่าน default ที่ hardcode ไว้คือช่องโหว่คลาสสิก; token สุ่มตอนติดตั้ง + ปิดหน้าตัวเองถาวรหลังใช้ = ปลอดภัยกว่าและอธิบายในเล่มได้ดี | ✅ ทำแล้ว |
| D14 | ⚠️ **เฟสแล็บใช้ SD card ได้** แต่ต้องย้าย log + DB ไป SSD ก่อนติดตั้งใช้งานจริง | ดูเหตุผลเชิงตัวเลขใน §11.1 — ปริมาณเขียนไม่ใช่ปัญหา แต่ไฟดับกลางคันคือปัญหา | ✅ |
| D15 | **ไม่ต่อ syslog server ภายนอก** — log ทั้งหมดอยู่บน gateway | อาจารย์ยืนยันแล้ว ลดความซับซ้อนลงมาก; ทดแทนด้วย hash chain + backup รายวันเพื่อพิสูจน์ integrity | ✅ |
| D16 | **WPA2-Enterprise (802.1X) = optional stretch goal ท้ายสุด** | ทำ Captive Portal ให้ครบก่อน; 802.1X ทำเฉพาะถ้าเหลือเวลา และทำเป็น SSID ที่สองแยกจาก SSID หลัก จะได้ไม่กระทบของที่ใช้ได้แล้ว | ✅ |
| D17 | ⚠️⚠️ **เปลี่ยนเป็นโหมดสาย LAN เส้นเดียว (one-armed router / router-on-a-stick)** — ใช้แค่ 2 อุปกรณ์: RPi 4B + เราเตอร์บ้าน 1 ตัว เชื่อมกันด้วยสาย RJ45 เส้นเดียว | ตัดสินใจโดยเจ้าของโครงงาน (2026-08-23): ลดอุปกรณ์ ลดงบ ใช้ของที่มีอยู่แล้ว · RPi 4B มีพอร์ต Ethernet เดียว จึงต้องรับ-ส่งทั้งฝั่งลูกค้าและฝั่งอินเทอร์เน็ตบนสายเดียวกัน · **แลกมาด้วยช่องโหว่ bypass ที่ปิดไม่สนิท (ดู D19 และ §3.1.4)** และ throughput เหลือประมาณครึ่งเดียว (ดู §3.1.5) | ✅ ตัดสินใจแล้ว · 🔶 โค้ดยังไม่รองรับ |
| D18 | **แยก subnet ลูกค้าออกจาก subnet เราเตอร์** — ลูกค้าอยู่ `10.10.0.0/24` (gw = Pi), เราเตอร์+Pi อยู่คนละวงเช่น `192.168.1.0/24` บนสายกายภาพเดียวกัน | ถ้าใช้ subnet เดียวกันทั้งหมด ลูกค้าแค่เปลี่ยนค่า gateway ในเครื่องเป็น IP เราเตอร์ก็ทะลุออกเน็ตได้ทันที · การแยก subnet ทำให้การ bypass ต้องตั้งค่า IP ใหม่ทั้งชุดเอง ไม่ใช่แค่แก้ gateway ช่องเดียว และทำให้เขียน nftables แยกทิศทางได้ชัดเจน | ✅ |
| D19 | **ยอมรับว่าช่องโหว่ bypass ปิดไม่ได้ 100% ในโหมดนี้** — ใช้มาตรการซ้อนกัน 4 ชั้น (ดู §3.1.4) และ**เขียนเป็นข้อจำกัดในเล่มรายงานอย่างตรงไปตรงมา** | เป็นข้อจำกัดเชิงสถาปัตยกรรมของ one-armed router บนสวิตช์ที่ไม่รองรับ VLAN — ไม่ใช่บั๊กที่แก้ได้ด้วยโค้ด · ทดสอบในแล็บเท่านั้น (§15 ข้อ 2) จึงยอมรับได้ · **ถ้านำไปใช้ในร้านจริงต้องกลับไปใช้ 2 อินเทอร์เฟซหรือ managed switch + VLAN** เพราะผู้ใช้ที่หลุดออกไปจะไม่ถูกบันทึก log = เสี่ยงผิด ม.26 | ✅ |
| D20 | ⚠️ **`purge_stale_customers()` "ล้างข้อมูลระบุตัวตน" (anonymize) แทนการ `DELETE` แถว customer ทิ้ง** | บั๊กจริงที่เจอ (C2, 2026-08-26): `DELETE` ชน `fk_voucher_customer` (RESTRICT ปริยาย) แตกจริงเพราะลูกค้าทุกรายมี voucher เสมอ ทำให้ cafe-maintenance.service ทั้งหน่วยหยุดกลางคัน — เปลี่ยนเป็นเคลียร์ `natid_hash/natid_enc/natid_masked` แต่คงแถวไว้ รักษาสาย FK ของ voucher/device/portal_session ที่ยังใช้เป็นหลักฐานจำนวนครั้ง/อุปกรณ์ตาม ม.26 ได้ต่อ แม้ตัวตนจะถูกลบไปแล้ว | ✅ ทำแล้ว |
| D21 | **เพิ่ม `cafe-enforce.timer` (ทุก 5 นาที) แยกจาก `cafe-maintenance.timer` (รายคืน)** เพื่อบังคับอายุ voucher จริงผ่าน `ndsctl deauth` + ปิด session ค้าง + ตั้ง `SessionTimeout` ใน opennds.conf เป็น 1440 (ค่าสูงสุด) แทน 240 ตายตัว | บั๊กจริงที่เจอ (H3, 2026-08-26): SessionTimeout ตายตัวทำให้ voucher สั้นกว่า 4 ชม. ใช้ได้นานเกินจ่าย และ voucher ยาวกว่า 4 ชม. ถูกตัดสั้นกว่าที่จ่าย — งาน maintenance รายคืนช้าเกินไปสำหรับบังคับสิทธิ์การเข้าถึงเครือข่าย (ต้องถี่กว่านั้นมาก) จึงแยกเป็น timer ใหม่ · 🔶 `ndsctl deauth` ยังไม่เคยทดสอบกับ openNDS binary จริงบนฮาร์ดแวร์ (เหมือนส่วนอื่นของโปรโตคอลนี้) ถ้าใช้ไม่ได้จริง อย่างน้อยระบบยังปิด session ในฐานข้อมูลให้ถูกต้อง | ✅ ทำแล้ว · 🔶 ndsctl ยังไม่ยืนยันบนฮาร์ดแวร์ |

---

## 3. สถาปัตยกรรมระบบ

### 3.1 Network Topology (โหมดสาย LAN เส้นเดียว — D17)

> **หมายเหตุสำคัญสำหรับ Claude ที่มาทำงานต่อ:** หัวข้อนี้ถูกเขียนใหม่ทั้งหมดเมื่อ 2026-08-23
> ตาม D17 · โครงสร้างเดิม (2 อินเทอร์เฟซ WAN/LAN แยกกัน) **ถูกยกเลิกแล้ว ไม่ต้องรองรับอีก**
> · `install.sh` ปัจจุบันยังเขียนตามแบบเดิมอยู่ ต้องแก้ตาม §3.1.6

#### 3.1.1 ภาพรวม

```
                         Internet
                             │
                             │ (WAN port)
        ┌────────────────────▼─────────────────────┐
        │        เราเตอร์ Wi-Fi บ้าน (unmanaged)    │
        │  LAN IP : 192.168.1.1/24                 │
        │  DHCP   : ❌ ปิด  (ให้ Pi เป็นคนแจก)      │
        │  Wi-Fi  : ✅ เปิด SSID "Cafe-Guest"       │
        │  AP Isolation : ✅ เปิด (ถ้ามีให้ตั้ง)     │
        │  Access Control : อนุญาต WAN เฉพาะ Pi     │
        └───────┬──────────────────────┬───────────┘
                │ LAN port             │
                │ (RJ45 เส้นเดียว)      ≈≈≈ Wi-Fi ≈≈≈
                │                      │
    ┌───────────▼──────────────┐   [ลูกค้า A] [ลูกค้า B] ...
    │   Raspberry Pi 4B        │    10.10.0.100-250
    │   eth0 — สายเดียว 2 IP:  │    gw  = 10.10.0.1  (Pi)
    │   ├ 192.168.1.2/24 ◄─────┼─── dns = 10.10.0.1  (Pi)
    │   │  (คุยกับเราเตอร์,     │           │
    │   │   ออกเน็ต, SSH เข้ามา) │           │
    │   └ 10.10.0.1/24  ◄──────┼───────────┘
    │      (gateway + DHCP +   │   ลูกค้าทุกเครื่องวิ่งผ่าน Pi
    │       DNS ของลูกค้า)      │   ทั้งขาไปและขากลับ
    │                          │
    │  openNDS │ nftables      │
    │  dnsmasq │ Flask FAS     │
    │  MariaDB │ Flask Admin   │
    │  logger  │ chrony        │
    └──────────────────────────┘
```

**เส้นทางของแพ็กเก็ตจริง** (ลูกค้าเปิดเว็บ 1 ครั้ง):

```
ลูกค้า(10.10.0.105) ──Wi-Fi──> เราเตอร์(bridge) ──LAN port──> Pi eth0
      │
      Pi: ตรวจ openNDS ว่า MAC นี้ auth แล้วหรือยัง → NAT เป็น 192.168.1.2
      │
      └──> ออกทาง eth0 เส้นเดิม ──> เราเตอร์ 192.168.1.1 ──NAT──> Internet
```

สังเกตว่าแพ็กเก็ตวิ่งผ่านสาย RJ45 เส้นเดียวกัน **2 รอบ** (ขาเข้าจากลูกค้า + ขาออกไปเราเตอร์)
นี่คือลักษณะของ *router-on-a-stick* และเป็นที่มาของข้อจำกัดเรื่อง throughput ใน §3.1.5

#### 3.1.2 การตั้งค่าฝั่ง Raspberry Pi

| รายการ | ค่า | หมายเหตุ |
|---|---|---|
| อินเทอร์เฟซ | `eth0` เพียงตัวเดียว | ไม่มี eth1 อีกแล้ว |
| IP ที่ 1 (ฝั่งเราเตอร์/ผู้ดูแล) | `192.168.1.2/24` **static** | ใช้ SSH เข้ามาจัดการ + เป็นทางออกเน็ต |
| IP ที่ 2 (ฝั่งลูกค้า) | `10.10.0.1/24` secondary | เป็น default gateway + DNS + DHCP server ของลูกค้า |
| default route | `via 192.168.1.1 dev eth0` | ชี้ไปเราเตอร์ |
| DHCP pool | `10.10.0.100 – 10.10.0.250` | dnsmasq บน Pi |
| NAT | masquerade `10.10.0.0/24` → `192.168.1.2` | double NAT กับเราเตอร์อีกชั้น — ยอมรับได้ |
| `net.ipv4.ip_forward` | `1` | |
| `net.ipv4.conf.all.send_redirects` | **`0`** | สำคัญ — กัน Pi บอกลูกค้าให้ไปคุยกับเราเตอร์ตรง ๆ |
| `net.ipv4.conf.all.accept_redirects` | `0` | |

#### 3.1.3 การตั้งค่าฝั่งเราเตอร์บ้าน (เจ้าของโครงงานทำเอง)

ทำตามลำดับนี้เท่านั้น — **สลับลำดับแล้วจะ SSH เข้า Pi ไม่ได้** (ดู §3.1.7):

| # | ตั้งค่า | ค่าที่ต้องการ | ถ้าเราเตอร์ไม่มีให้ตั้ง |
|---|---|---|---|
| 1 | LAN IP ของเราเตอร์ | `192.168.1.1/24` (หรือค่าเดิมก็ได้ แต่ต้องจดไว้) | — |
| 2 | **DHCP Server** | ❌ **ปิด** | ถ้าปิดไม่ได้ ให้จำกัด pool เหลือ 1-2 IP แล้วกันไว้ให้ Pi (ไม่ดีเท่าปิด) |
| 3 | Wi-Fi | เปิด SSID `Cafe-Guest` + WPA2 | — |
| 4 | **AP / Client Isolation** | ✅ เปิด | 🔶 ถ้าไม่มี = ลูกค้าคุยกันเองได้ ต้องเขียนเป็นข้อจำกัดในเล่ม (O4 จะอ่อนลง) |
| 5 | **Access Control / IP Filter** | อนุญาตให้ออก WAN ได้**เฉพาะ** `192.168.1.2` (Pi) | 🔶 ถ้าไม่มี = ช่องโหว่ bypass เปิดกว้าง (ดู §3.1.4 ชั้นที่ 1) |
| 6 | UPnP | ❌ ปิด | ลดช่องทางที่ลูกค้าเปิดพอร์ตเองได้ |

> **ฟีเจอร์ข้อ 5 คือหัวใจของความปลอดภัยในโหมดนี้** ในเมนูเราเตอร์อาจใช้ชื่อว่า
> *Access Control*, *IP Filtering*, *Parental Control*, *Firewall Rules* หรือ *MAC Filter*
> — ให้ไปหาก่อนเป็นอันดับแรกและจดไว้ว่ารุ่นนี้มีหรือไม่มี เพราะมีผลต่อการเขียน §6.5 ในเล่ม

#### 3.1.4 ⚠️ ช่องโหว่ Bypass — วิเคราะห์ตรงไปตรงมา

**ปัญหา:** ลูกค้าและเราเตอร์อยู่บน L2 segment เดียวกัน ถ้าลูกค้าตั้งค่า IP เองเป็น
`192.168.1.50/24 gw 192.168.1.1` จะคุยกับเราเตอร์ได้ตรง ๆ **โดยไม่ผ่าน Pi เลย**
→ ใช้เน็ตได้โดยไม่ต้อง login และ **ไม่ถูกบันทึก log**

**สิ่งที่ป้องกันได้จริง (เรียงตามประสิทธิผล):**

| ชั้น | มาตรการ | ปิดช่องโหว่ได้แค่ไหน |
|---|---|---|
| 1 | **Access Control ที่เราเตอร์** — อนุญาต WAN เฉพาะ IP/MAC ของ Pi | ✅ **ปิดได้เกือบสนิท** ถ้าเราเตอร์มีฟีเจอร์นี้ · เหลือแค่การปลอม MAC เป็น Pi ซึ่งจะเกิด IP/MAC ขัดกันบนวง ตรวจจับได้ |
| 2 | **ใช้ subnet เล็กมากฝั่งเราเตอร์** เช่น `/30` (`172.31.99.0/30` = ใช้ได้แค่ .1 กับ .2) | ✅ ดีมากถ้าเราเตอร์ตั้ง mask เองได้ — ไม่มี IP ว่างให้ผู้บุกรุกหยิบไปใช้เลย ต้องชน IP กับเราเตอร์หรือ Pi เท่านั้น |
| 3 | **แยก subnet ลูกค้า** (D18) | 🔶 ยกระดับความยาก — ต้องตั้ง IP ใหม่ทั้งชุดเอง ไม่ใช่แค่แก้ gateway · กัน "คนทั่วไป" ได้ แต่ไม่กันคนที่ตั้งใจ |
| 4 | **ตรวจจับ + แจ้งเตือน** — Pi เฝ้าดู ARP/traffic ที่มาจาก IP แปลกปลอมในวงเราเตอร์ แล้วบันทึก + alert | ❌ ไม่ได้ป้องกัน แต่**มีคุณค่าเชิงวิชาการสูง** — ใช้เป็นการทดลองใน Phase 5 ได้ ("วัดผลว่าตรวจจับการ bypass ได้กี่ %") |

**สรุปเชิงวิศวกรรมอย่างซื่อสัตย์:** ในโหมดสายเส้นเดียวบนสวิตช์ที่ไม่รองรับ VLAN
**ไม่มีทางปิดช่องโหว่นี้ได้ 100% ด้วยซอฟต์แวร์บน Pi ฝ่ายเดียว** เพราะ Pi ไม่ได้อยู่บนเส้นทาง
บังคับ (ไม่ใช่ inline) การป้องกันจึงต้องพึ่งเราเตอร์เป็นหลัก (ชั้นที่ 1-2)
วิธีที่ปิดได้จริง 100% มี 2 ทางคือ (ก) กลับไปใช้ 2 อินเทอร์เฟซ (USB Ethernet ~200-400 บาท)
หรือ (ข) ใช้ managed switch + VLAN — **ทั้งสองทางถูกตัดออกจากขอบเขตโครงงานนี้ตาม D17 แล้ว**
จึงต้องเขียนเรื่องนี้ลง §6.5 และบทที่ 5 (ข้อจำกัด + ข้อเสนอแนะงานในอนาคต) อย่างชัดเจน
— **การอธิบายข้อจำกัดได้อย่างเข้าใจลึกถือเป็นจุดแข็งของรายงาน ไม่ใช่จุดอ่อน**

#### 3.1.5 ผลต่อประสิทธิภาพ

ทุกแพ็กเก็ตวิ่งผ่านสาย RJ45 เส้นเดียว 2 รอบ → **แบนด์วิดท์ที่ใช้ได้จริงเหลือประมาณครึ่งเดียว**

| รายการ | ค่าประมาณ |
|---|---|
| Ethernet ของ RPi 4B | 1 Gbps (แต่แชร์บัส USB กับอุปกรณ์อื่น) |
| หักครึ่งจาก one-armed | ~500 Mbps ตามทฤษฎี |
| หักค่า NAT + conntrack logging + openNDS บน CPU ของ Pi 4B | **~250-400 Mbps ตามจริง (ต้องวัดเอง)** |

→ ต้องปรับตัวชี้วัดใน §14 จาก "≥ 300 Mbps" เป็น **"≥ 200 Mbps"** ให้สมจริงกับสถาปัตยกรรมนี้
(เน็ตร้านคาเฟ่ทั่วไปมักไม่เกิน 100-500 Mbps อยู่แล้ว จึงยังเพียงพอในทางปฏิบัติ)

#### 3.1.6 สิ่งที่แก้ใน `install.sh` แล้ว (2026-08-23) ✅

`install.sh` แก้เสร็จครบทั้ง 10 จุดแล้ว ตรวจสอบด้วย `bash -n`, `--dry-run` (ทั้งค่า default
และระบุ `--nic/--uplink-gw/--client-cidr` ตรง ๆ) และ `nft -c` กับไฟล์ nftables.conf ที่ generate
ออกมาจริง — ผ่านทั้งหมด (ดู §10 Work Log และ §17) ตารางนี้เก็บไว้เป็นบันทึกว่าแก้อะไรไปบ้าง:

| # | จุดที่แก้ | รายละเอียด |
|---|---|---|
| 1 | ✅ `preflight()` | ปัจจุบัน **ปฏิเสธ**ถ้า `WAN_IF == LAN_IF` → ต้องเอาออก และเปลี่ยนเป็นโหมดสายเดียวเป็นค่าเริ่มต้น |
| 2 | ✅ ตัวแปร `WAN_IF` / `LAN_IF` | ยุบเหลือ `NIC` ตัวเดียว + เพิ่ม `UPLINK_IP` (192.168.1.2/24), `UPLINK_GW` (192.168.1.1), `CLIENT_CIDR` (10.10.0.1/24) |
| 3 | ✅ `configure_network()` — การตั้ง IP | ต้อง `ip addr add 10.10.0.1/24 dev eth0` เป็น **secondary** โดย**ห้ามลบ IP เดิม** (จะหลุด SSH) |
| 4 | ✅ **nftables ทั้งชุด** | เปลี่ยนจากการอ้างอิง `iifname $LAN_IF` / `oifname $WAN_IF` มาเป็นการอ้างอิง **subnet** (`ip saddr 10.10.0.0/24` / `ip daddr`) เพราะอินเทอร์เฟซเดียวกันทั้งเข้าและออก |
| 5 | ✅ **กฎ SSH** | ปัจจุบัน `iifname $LAN_IF tcp dport 22 drop` → ในโหมดสายเดียวจะ**ตัด SSH ของตัวเองทันที** ต้องเปลี่ยนเป็น drop เฉพาะ `ip saddr 10.10.0.0/24` และ accept จาก `192.168.1.0/24` |
| 6 | ✅ กฎ Admin Panel | เช่นเดียวกัน — drop เฉพาะจาก subnet ลูกค้า |
| 7 | ✅ `iifname $LAN_IF oifname $LAN_IF drop` (เดิม) | เดิมกันลูกค้าคุยกันเอง · ในโหมดสายเดียวกฎนี้จะบล็อกทุกอย่างรวมถึง traffic ที่ต้องวิ่งกลับออกไป → ต้องเขียนใหม่เป็น `ip saddr 10.10.0.0/24 ip daddr 10.10.0.0/24 drop` |
| 8 | ✅ `sysctl` | เพิ่ม `send_redirects=0`, `accept_redirects=0` |
| 9 | ✅ `opennds.conf` | ตั้ง `gatewayinterface eth0` + **ระบุ `gatewayaddress 10.10.0.1` ให้ชัดเจน** (ไม่งั้น openNDS อาจหยิบ IP ผิดตัวเพราะมี 2 IP บน NIC เดียว) |
| 10 | ✅ **dead-man switch กัน SSH หลุด** | ก่อน apply nftables ให้ตั้ง `systemd-run --on-active=300 nft flush ruleset` ไว้ ถ้าผู้ติดตั้งยังเข้าได้ค่อยสั่งยกเลิก — ดู §3.1.7 |

**หมายเหตุการ implement จริง (ต่างจากตารางแผนเล็กน้อย แต่ตรงเจตนา):**

- ตัวแปรสุดท้ายใช้ชื่อ `UPLINK_CIDR` (ไม่ใช่ `UPLINK_IP`) เพื่อให้สื่อว่าเก็บทั้ง IP+prefix — flag คือ `--nic`, `--uplink-cidr`, `--uplink-gw`, `--client-cidr` (ตัวเก่า `--wan-if`/`--lan-if`/`--lan-cidr` ยังอยู่ในโค้ดแต่แค่เพื่อ**ดักแล้ว `die()` ด้วยข้อความบอกให้ใช้ flag ใหม่** กันคนที่จำคำสั่งเก่าได้)
- เพิ่มฟังก์ชันช่วย `cidr_to_network()` (คำนวณ network address จาก IP/prefix ด้วยเลขฐาน 2 ล้วน ไม่พึ่ง `ipcalc` เพราะไม่ได้มากับทุก distro) ใช้สร้างค่า `CLIENT_NET`/`UPLINK_NET` ให้ nftables
- **แก้เพิ่มอีก 1 จุดที่ไม่ได้อยู่ใน 10 ข้อเดิม:** `net.ipv4.conf.all.rp_filter` เปลี่ยนจาก `1` (strict) เป็น `0` — เหตุผลคือโหมดสายเดียวมี 2 IP บนอินเทอร์เฟซเดียว ทำให้เกิด asymmetric routing ได้ตามธรรมชาติ ถ้าเปิด strict mode ไว้ Linux จะ drop แพ็กเก็ตที่ถูกต้องทิ้งอย่างงงงวย (debug ยาก) ความปลอดภัยที่ `rp_filter` เคยช่วยตรงนี้ถูกแทนที่ด้วยกฎ nftables ที่อิง `ip saddr`/`ip daddr` ตาม subnet อยู่แล้วในข้อ 4
- ข้อ 3 ใช้ `ip addr add` (ไม่ใช่ `replace`) กับ**ทั้งสอง**ที่อยู่ (uplink และ client) แบบ idempotent เพื่อไม่ลบ IP เดิมทิ้งไม่ว่ากรณีใด — ตรงตามเจตนาเดิมที่เน้นว่า "ห้ามลบ IP เดิม"
- ตรวจสอบแล้วด้วย `nft -c` ตัวจริง (ไม่ใช่แค่ dry-run ของ install.sh) ว่า ruleset ที่ generate ออกมา compile ผ่าน — ดู §17

⚠️ **ยังไม่ได้แก้ (นอกขอบเขตของรอบนี้ตามที่ตกลง):** หน้า Admin Panel URL ที่พิมพ์ใน `final_summary()`
ยังชี้ไปที่ IP ฝั่งลูกค้า (`10.10.0.1:8443/setup`) แต่กฎ nftables ก็ block ไม่ให้ฝั่งลูกค้าเข้าถึง
Admin Panel — เป็นความย้อนแย้งที่**มีอยู่แล้วในแผนเดิมก่อนเปลี่ยนสถาปัตยกรรม** (ไม่ใช่บั๊กใหม่ที่เกิดจาก
การแก้ครั้งนี้) เพราะแผนเดิมก็ไม่เคยระบุชัดว่าอุปกรณ์พนักงานเชื่อมต่อจากวงไหน ต้องตัดสินใจก่อนถึง
Phase 1: พนักงานจะเข้า Admin Panel ผ่านสาย LAN ที่ต่อตรงจาก Pi (วง `192.168.1.0/24`) หรือจะเปิด
exception เฉพาะ MAC ของอุปกรณ์พนักงานในวงลูกค้า — บันทึกไว้เป็นคำถามเปิดใน §15

**แผนสำรอง (Plan B) ถ้า openNDS ทำงานบนอินเทอร์เฟซเดียวไม่ได้:**
สร้าง **macvlan** ซ้อนบน eth0 แล้วให้ openNDS ผูกกับ macvlan แทน —
`ip link add cli0 link eth0 type macvlan mode bridge` แล้วย้าย `10.10.0.1/24` ไปไว้ที่ `cli0`
วิธีนี้ทำให้ openNDS เห็น "อินเทอร์เฟซฝั่งลูกค้า" แยกจากอินเทอร์เฟซ uplink อย่างสะอาด
ทั้งที่ใช้สายกายภาพเส้นเดียว (ลูกค้า ARP หา 10.10.0.1 → ได้ MAC ของ cli0 → เฟรมวิ่งเข้า cli0)
🔶 **ยังไม่ได้ทดสอบ** — ข้อควรระวังคือ macvlan สื่อสารกับ IP ของ parent interface ตรง ๆ ไม่ได้
แต่เส้นทางของเราเป็นการ route ออกไปหาเราเตอร์ซึ่งเป็นคนละเครื่อง จึงไม่น่าติดข้อจำกัดนี้

#### 3.1.7 ⚠️ ลำดับการติดตั้งผ่าน SSH (ห้ามสลับ — เสี่ยงล็อกตัวเองออก)

ติดตั้งผ่าน SSH บนสายเส้นเดียวกับที่กำลังจะเปลี่ยนค่าเครือข่าย = เสี่ยงหลุดกลางคัน
ให้ทำตามลำดับนี้:

1. **ก่อนอื่น** — ต่อจอ+คีย์บอร์ดเข้า Pi ไว้เป็นทางหนีทีไล่ (หรือเตรียมสาย USB-TTL serial)
2. ตั้ง IP static `192.168.1.2/24` ให้ Pi **ขณะที่ DHCP เราเตอร์ยังเปิดอยู่**
3. ตัดการเชื่อมต่อ แล้ว SSH เข้าใหม่ที่ `192.168.1.2` — **ยืนยันว่าเข้าได้จริงก่อนไปต่อ**
4. ค่อยไปปิด DHCP ที่เราเตอร์
5. รัน `sudo ./install.sh` (จะเพิ่ม IP ที่สอง `10.10.0.1/24` และตั้ง nftables)
6. ระหว่าง apply nftables ให้มี dead-man switch ตาม §3.1.6 ข้อ 10 เสมอ

> ถ้าหลุดจริง ๆ: เสียบจอเข้า Pi แล้วสั่ง `sudo nft flush ruleset` เพื่อล้างกฎทั้งหมด

#### 3.1.8 🧪 วิธีทดสอบในแล็บโดยไม่มีเราเตอร์จริง (ตัดสินใจ 2026-08-23)

เจ้าของโครงงานยังไม่มีเราเตอร์ Wi-Fi สำรอง แต่มี: มือถือปล่อยฮอตสปอตให้ทั้งคอมและ Pi อยู่แล้ว,
คอม Windows ที่มีทั้งพอร์ต Ethernet (RJ45) และ Wi-Fi adapter (Wi-Fi กำลังต่อฮอตสปอตอยู่), และ VM
Debian บน **VMware Workstation/Player** — ใช้ทรัพยากรที่มีอยู่จำลอง "เราเตอร์บ้าน" แทนของจริงได้
โดยให้ **VM Debian เล่นบทบาทเราเตอร์** (มี 2 การ์ดเครือข่ายเหมือนเราเตอร์จริงมี WAN+LAN):

```
มือถือ (ฮอตสปอต, มีเน็ตจริง)
      │ Wi-Fi
      ▼
คอม Windows ──[VMware NAT]──> VM Debian (eth0 = NAT, ได้เน็ตจากคอมอัตโนมัติ)
      │                              │
      │ (พอร์ต Ethernet ว่างอยู่)      │ eth1 = Bridged ไปที่การ์ด Ethernet จริงของคอม
      │◄─────────────────────────────┘  (192.168.1.1/24 -- เล่นเป็น "เราเตอร์")
      │
      │ สาย RJ45 เส้นเดียว (คอม ──> Pi)
      ▼
Raspberry Pi eth0 (192.168.1.2/24 + 10.10.0.1/24 ตามปกติ)
```

**ทำตามนี้:**

1. ใน VMware ตั้งค่า VM Debian ให้มี **2 การ์ดเครือข่าย**: Adapter 1 = **NAT** (ได้เน็ตจากคอมอัตโนมัติ
   ไม่ต้องยุ่งอะไร) · Adapter 2 = **Bridged** — **ต้องเลือกการ์ด Ethernet (RJ45) ของคอมตรง ๆ ไม่ใช่
   "Automatic"** (เพราะคอมมี 2 การ์ด ถ้าเลือกอัตโนมัติอาจไป bridge Wi-Fi ที่กำลังต่อฮอตสปอตอยู่แทน)
2. ต่อสาย RJ45 จากพอร์ต Ethernet ของคอม ไปเข้า `eth0` ของ Pi โดยตรง (ไม่ผ่านอะไรอีก)
3. ใน VM Debian (เช็คชื่อการ์ดจริงด้วย `ip link` ก่อน อาจไม่ใช่ `ens33`/`ens37` เป๊ะ ๆ):
   ```bash
   sudo sysctl -w net.ipv4.ip_forward=1
   echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
   sudo ip addr add 192.168.1.1/24 dev ens37   # การ์ดที่เป็น Bridged (ฝั่ง Pi)
   sudo ip link set ens37 up
   sudo apt update && sudo apt install -y nftables
   sudo nft add table inet nat
   sudo nft add chain inet nat postrouting { type nat hook postrouting priority 100 \; }
   sudo nft add rule inet nat postrouting oifname "ens33" masquerade   # การ์ดที่เป็น NAT (ฝั่งเน็ต)
   ```
   **ห้ามลง DHCP server ใด ๆ บน VM นี้** — ต้องให้ Pi (`dnsmasq`) เป็น DHCP เจ้าเดียวเท่านั้น
   ตรงตามเงื่อนไขที่ D17/§3.1.3 ต้องการจากเราเตอร์จริง
4. ที่ Pi: `sudo ./install.sh --nic eth0 --uplink-gw 192.168.1.1 --uplink-cidr 192.168.1.2/24 --client-cidr 10.10.0.1/24`
5. **ใช้ Windows (host) เองเป็นเครื่อง "ลูกค้าทดสอบ"** — ตั้งการ์ด Ethernet ของ Windows ให้ "Obtain IP
   automatically" (DHCP) แทนที่จะปล่อยว่าง เพราะพอร์ต Ethernet เดียวกันนี้ที่ VMware bridge ไปใช้
   ยังใช้งานคู่ขนานได้จาก Windows เองด้วย (VMware bridge แค่แตะสาย ไม่ได้ยึดพอร์ตไปทั้งหมด) —
   Windows จะได้ IP จากช่วง `10.10.0.100-250` (Pi แจกให้) แล้วลองเปิดเบราว์เซอร์ดูว่าเด้งหน้า login
   ไหม (ทดสอบ R11 เป็นครั้งแรก)

**สิ่งที่ทดสอบวิธีนี้ได้จริง:** DHCP จาก Pi, nftables (NAT/isolation/DNS-redirect), การ forward ผ่าน
VM ออกเน็ตจริงผ่านมือถือ, **openNDS ทำงานบนอินเทอร์เฟซเดียวได้จริงไหม (R11)**, FAS login flow ครบวงจร

**สิ่งที่วิธีนี้ทดสอบไม่ได้ (ต้องรอเราเตอร์จริง/ฮาร์ดแวร์จริง):** พฤติกรรม captive-portal
auto-detect ของ iOS/Android จริง (Windows browser ไม่มี captive network assistant แบบมือถือ),
AP Isolation/Access Control ของเราเตอร์จริง (R12), T16/T17 (ทดสอบ bypass), throughput จริงผ่าน Wi-Fi

### 3.2 Component Diagram

```
┌──────────────── Raspberry Pi ────────────────────────────────┐
│                                                              │
│  ลูกค้า ──HTTP──> [openNDS :2050] ──redirect──> [FAS :8080]  │
│                        │                          │          │
│                        │  auth token              │ verify   │
│                        ▼                          ▼          │
│                   [nftables]              [MariaDB: creds]   │
│                   allow MAC                       ▲          │
│                        │                          │          │
│                        │                   [Admin :8081]     │
│                        │                    (พนักงาน)        │
│                        ▼                                     │
│                   [NAT → eth0 → Internet]                    │
│                        │                                     │
│         ┌──────────────┼──────────────┐                      │
│         ▼              ▼              ▼                      │
│   [conntrack -E]  [dnsmasq log]  [openNDS session]           │
│         └──────────────┼──────────────┘                      │
│                        ▼                                     │
│              [log-collector.py] ──> [MariaDB: logs]          │
│                        └──────────> [SSD: *.log.gz]          │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Authentication Flow (ลำดับเหตุการณ์จริง)

```
1. ลูกค้าเดินเข้าร้าน → ยื่นบัตรประชาชนให้พนักงาน
2. พนักงานเปิด Admin Panel (http://10.10.0.1:8081) → Login ด้วยบัญชีพนักงาน
3. กรอกเลขบัตร 13 หลัก → ระบบ validate checksum (mod-11) ทันทีในหน้าเว็บ
4. ระบบ:
   a. คำนวณ HMAC-SHA256(natid, PEPPER) → natid_hash  (ใช้ค้นหา/กันซ้ำ)
   b. เข้ารหัส AES-256-GCM(natid, DEK) → natid_enc
   c. เก็บ masked "1-2345-XXXXX-XX-X" ไว้แสดงผล
   d. สุ่ม password 8 ตัว (base32 ตัดตัวกำกวม 0/O/1/I/l) → เก็บ argon2id hash
   e. สร้าง voucher: valid_until = now + 4 ชม., max_devices = 2
5. หน้าจอแสดง Username (= running voucher code) + Password **ครั้งเดียว** → พนักงานบอก/พิมพ์สลิปให้ลูกค้า
6. ลูกค้าต่อ Wi-Fi "Cafe-Guest" → DHCP ได้ IP → OS ตรวจเจอ captive portal
7. เด้งหน้า Login (FAS) → กรอก username/password
8. FAS ตรวจกับ DB → ถ้าผ่าน เรียก openNDS auth endpoint พร้อม token
9. openNDS สั่ง nftables อนุญาต MAC นั้น → ลูกค้าใช้เน็ตได้
10. ทุก connection/DNS query ถูกบันทึก mapping กลับไปยัง voucher → natid_hash
11. หมดเวลา/หมดโควตา → openNDS deauth → กลับสู่ข้อ 6
```

---

## 4. Tech Stack

| ชั้น | เทคโนโลยี | หมายเหตุ |
|---|---|---|
| OS | Raspberry Pi OS Lite 64-bit (Debian 13 Trixie) | ไม่ต้องมี desktop |
| Firewall/NAT | nftables | openNDS จัดการ chain ของตัวเองอัตโนมัติ |
| DHCP + DNS | dnsmasq | `log-queries` = แหล่ง DNS log |
| Captive Portal | openNDS v10.3.x | `fas_secure_enabled = 2` (AES-256-CBC + faskey) |
| Portal UI (FAS) | Python 3.11 + Flask + Jinja2 + HTML/CSS | port 8080 |
| Admin Panel | Python 3.11 + Flask + Bootstrap 5 (local, ไม่ใช้ CDN) | port 8081, เข้าได้จาก LAN ของพนักงานเท่านั้น |
| WSGI/Reverse proxy | Gunicorn + Nginx | Nginx ทำ TLS ให้ Admin Panel (self-signed) |
| Database | MariaDB 11.x | |
| RADIUS (Phase 5) | FreeRADIUS 3.2 + rlm_sql | radcheck / radacct |
| Connection log | `conntrack -E` (conntrack-tools) หรือ nflog + ulogd2 | metadata เท่านั้น |
| Packet demo | tcpdump `-s 96` (header only) | ใช้สาธิตตอนนำเสนอเท่านั้น ไม่รันถาวร |
| Log storage | External SSD → `/var/log/cafe`, logrotate + gzip | |
| Time sync | chrony → `time1.nimt.or.th`, `th.pool.ntp.org` | กฎหมายต้องการความคลาดเคลื่อน ≤ 10 ms |
| AP | TP-Link/Ubiquiti โหมด AP + Client Isolation | |
| Monitoring (nice-to-have) | Netdata หรือ Prometheus + Grafana | |

---

## 5. Database Schema (MariaDB)

```sql
-- ===== ผู้ดูแล/พนักงาน =====
CREATE TABLE staff (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,          -- argon2id
  display_name  VARCHAR(128),
  role          ENUM('admin','staff') NOT NULL DEFAULT 'staff',
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  totp_secret   VARCHAR(64) NULL,               -- 2FA (Phase 5)
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===== ลูกค้า (ผูกกับเลขบัตร ปชช.) =====
CREATE TABLE customer (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  natid_hash   CHAR(64)  NOT NULL UNIQUE,   -- HMAC-SHA256(natid, PEPPER) hex
  natid_enc    VARBINARY(255) NOT NULL,     -- AES-256-GCM: nonce||ct||tag
  natid_masked CHAR(20)  NOT NULL,          -- '1-2345-XXXXX-XX-X'
  first_seen   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen    DATETIME NULL,
  visit_count  INT NOT NULL DEFAULT 0,
  is_blocked   BOOLEAN NOT NULL DEFAULT FALSE,
  INDEX idx_last_seen (last_seen)
);

-- ===== Voucher / บัญชีใช้งานชั่วคราว =====
CREATE TABLE voucher (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  customer_id   BIGINT NOT NULL,
  username      VARCHAR(32) NOT NULL UNIQUE,   -- เช่น 'CAFE-8F3K2'
  password_hash VARCHAR(255) NOT NULL,         -- argon2id
  issued_by     INT NOT NULL,                  -- staff.id
  issued_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  valid_from    DATETIME NOT NULL,
  valid_until   DATETIME NOT NULL,
  quota_mb      INT NULL,                      -- NULL = ไม่จำกัด
  used_mb       INT NOT NULL DEFAULT 0,
  max_devices   TINYINT NOT NULL DEFAULT 2,
  status        ENUM('active','expired','revoked','used_up') NOT NULL DEFAULT 'active',
  FOREIGN KEY (customer_id) REFERENCES customer(id),
  FOREIGN KEY (issued_by)   REFERENCES staff(id),
  INDEX idx_status_valid (status, valid_until)
);

-- ===== อุปกรณ์ที่ผูกกับ voucher =====
CREATE TABLE device (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  voucher_id  BIGINT NOT NULL,
  mac         CHAR(17) NOT NULL,
  first_seen  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_ip     VARCHAR(45),
  UNIQUE KEY uq_voucher_mac (voucher_id, mac),
  INDEX idx_mac (mac),
  FOREIGN KEY (voucher_id) REFERENCES voucher(id)
);

-- ===== Session (จาก openNDS/RADIUS accounting) =====
CREATE TABLE portal_session (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  voucher_id  BIGINT NOT NULL,
  mac         CHAR(17) NOT NULL,
  ip          VARCHAR(45) NOT NULL,
  started_at  DATETIME NOT NULL,
  ended_at    DATETIME NULL,
  bytes_in    BIGINT NOT NULL DEFAULT 0,
  bytes_out   BIGINT NOT NULL DEFAULT 0,
  terminate_cause VARCHAR(32) NULL,
  INDEX idx_time (started_at, ended_at),
  INDEX idx_mac_time (mac, started_at),
  FOREIGN KEY (voucher_id) REFERENCES voucher(id)
);

-- ===== Connection Log (ข้อมูลจราจร ตาม ม.26) =====
CREATE TABLE conn_log (
  id        BIGINT AUTO_INCREMENT PRIMARY KEY,
  ts        DATETIME(3) NOT NULL,
  mac       CHAR(17) NOT NULL,
  src_ip    VARCHAR(45) NOT NULL,
  src_port  SMALLINT UNSIGNED,
  dst_ip    VARCHAR(45) NOT NULL,
  dst_port  SMALLINT UNSIGNED,
  proto     ENUM('tcp','udp','icmp','other') NOT NULL,
  bytes_out BIGINT DEFAULT 0,
  bytes_in  BIGINT DEFAULT 0,
  INDEX idx_ts (ts),
  INDEX idx_mac_ts (mac, ts),
  INDEX idx_dst (dst_ip)
) PARTITION BY RANGE (TO_DAYS(ts)) (
  -- สร้าง partition รายวัน/รายสัปดาห์ด้วย event scheduler เพื่อ DROP ทิ้งเร็ว
  PARTITION p_init VALUES LESS THAN MAXVALUE
);

-- ===== DNS Log =====
CREATE TABLE dns_log (
  id        BIGINT AUTO_INCREMENT PRIMARY KEY,
  ts        DATETIME(3) NOT NULL,
  client_ip VARCHAR(45) NOT NULL,
  mac       CHAR(17),
  qname     VARCHAR(255) NOT NULL,
  qtype     VARCHAR(10),
  answer    VARCHAR(255),
  INDEX idx_ts (ts),
  INDEX idx_qname (qname),
  INDEX idx_mac_ts (mac, ts)
);

-- ===== Audit Log (ใครดู/ถอดรหัสเลขบัตร ปชช. เมื่อไหร่) =====
CREATE TABLE audit_log (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  ts         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  staff_id   INT NULL,
  action     VARCHAR(64) NOT NULL,   -- 'login','issue_voucher','reveal_natid','export_log','revoke'
  target     VARCHAR(128),
  client_ip  VARCHAR(45),
  detail     TEXT,
  INDEX idx_ts (ts),
  INDEX idx_action (action)
);
```

**หมายเหตุสำคัญ:** `audit_log` แถว `reveal_natid` คือหลักฐานว่าระบบมีการควบคุมการเข้าถึงข้อมูลอ่อนไหว — เป็นจุดขายเวลานำเสนอ

---

## 6. ความปลอดภัยและกฎหมาย (ห้ามลัด)

### 6.1 พ.ร.บ.คอมพิวเตอร์ พ.ศ. 2560 มาตรา 26

| ข้อกำหนด | สิ่งที่ระบบต้องทำ | เช็ค |
|---|---|---|
| เก็บข้อมูลจราจรฯ ไม่น้อยกว่า **90 วัน** (ขยายได้ถึง 2 ปีตามคำสั่งเจ้าหน้าที่) | logrotate เก็บ 180 วัน + partition ใน DB | [ ] |
| ต้องระบุตัวผู้ใช้ได้ | mapping: conn_log.mac → device → voucher → customer → natid | [ ] |
| นาฬิกาต้องตรงเวลาอ้างอิงสากล **คลาดเคลื่อน ≤ 10 ms** | chrony + `chronyc tracking` ต้องแสดง offset < 10 ms; log ค่านี้ทุกชั่วโมง | [ ] |
| Log ต้องแก้ไขไม่ได้ (integrity) | เขียนไฟล์ append-only (`chattr +a`) + hash chain SHA-256 รายวัน เก็บ manifest แยก | [ ] |
| บทลงโทษ | ไม่เก็บ: ปรับสูงสุด 500,000 บาท / ไม่ส่งตามคำสั่ง: 200,000 บาท + วันละ 5,000 บาท | — |

### 6.2 PDPA — การจัดการเลขบัตรประชาชน

**ห้ามทำเด็ดขาด:**
- เก็บเลข 13 หลักแบบ plaintext ใน DB, log file, หรือ URL/query string
- แสดงเลขเต็มในหน้าเว็บ/รายงานโดยไม่มีการ log การเข้าถึง
- push ไฟล์ `.env` / key ขึ้น Git

**ต้องทำ:**
1. **Key management** — DEK (Data Encryption Key) และ PEPPER เก็บใน `/etc/cafe-wifi/secrets.env` (chmod 600, owner root) ไม่อยู่ใน repo
2. **Consent notice** — หน้า Admin ต้องมีข้อความให้พนักงานอ่านให้ลูกค้าฟัง + หน้า Portal มีลิงก์ "นโยบายความเป็นส่วนตัว"
3. **Data minimization** — ไม่เก็บชื่อ-นามสกุล, ที่อยู่, รูปบัตร เก็บแค่เลขบัตร (เข้ารหัส) + วันเวลาใช้งาน
4. **Retention** — cron job ลบ `customer` ที่ไม่มี voucher ใน 180 วันย้อนหลัง
5. **Access control** — role `staff` เห็นได้แค่ masked; role `admin` เท่านั้นที่กด "เปิดเผยเลขเต็ม" ได้ และทุกครั้งต้องลง `audit_log`
6. **DSR** — มีปุ่ม/สคริปต์ค้นหาและลบข้อมูลของบุคคลตามคำขอ (ยกเว้นส่วนที่กฎหมายบังคับให้เก็บ)

### 6.3 Thai National ID Checksum (ต้อง validate ก่อนบันทึกเสมอ)

```python
def valid_thai_id(nid: str) -> bool:
    """เลข 13 หลัก: ผลรวม d[i] * (13-i) สำหรับ i=0..11, check = (11 - sum%11) % 10"""
    if not (nid.isdigit() and len(nid) == 13):
        return False
    s = sum(int(nid[i]) * (13 - i) for i in range(12))
    return (11 - s % 11) % 10 == int(nid[12])
```

### 6.4 มาตรการป้องกันการโจมตีใน LAN (ตอบวัตถุประสงค์ O4)

| ภัยคุกคาม | มาตรการ | ที่ตั้งค่า |
|---|---|---|
| Packet sniffing ระหว่างลูกค้า | **AP Client Isolation** + nftables drop LAN↔LAN | AP + Pi |
| ARP spoofing | `arp_ignore=1`, static ARP สำหรับ gateway, ตรวจจับ MAC-IP ไม่ตรงแล้ว alert | Pi |
| DHCP rogue server | dnsmasq เป็น authoritative; nftables drop DHCP server จากฝั่ง LAN (udp sport 67) | Pi |
| DNS hijacking / bypass | บังคับ redirect UDP/TCP 53 มาที่ dnsmasq; block DoH endpoints ที่รู้จัก (optional) | nftables |
| เข้าถึง Admin Panel จากฝั่งลูกค้า | nftables drop dst 10.10.0.1:8081 จาก LAN; เปิดให้เฉพาะ MAC/IP ของเครื่องพนักงาน | nftables |
| Brute-force รหัส voucher | rate-limit 5 ครั้ง/MAC/10 นาที + exponential backoff | FAS |
| MAC spoofing เพื่อขโมย session | ผูก MAC+IP, ตรวจ session ทุก 60 วิ, บังคับ re-auth เมื่อ IP เปลี่ยน | openNDS + FAS |
| SSH/พอร์ตบริหารเปิดสู่ WAN | key-only auth, ปิด password login, fail2ban | Pi |
| **Bypass captive portal** (ตั้ง IP/gateway เอง) | Access Control ที่เราเตอร์ + แยก subnet + ตรวจจับ ARP แปลกปลอม — **ปิดไม่สนิท ดู §3.1.4** | เราเตอร์ (หลัก) + Pi |

### 6.5 ข้อจำกัดที่ต้องรู้ (อธิบายในเล่มรายงาน)

- **HTTPS/HSTS ทำให้ redirect หน้า portal ไม่ขึ้นเสมอ** — สมัยนี้ต้องพึ่ง OS captive-portal detection (`captive.apple.com`, `connectivitycheck.gstatic.com/generate_204`, `msftconnecttest.com`) openNDS จัดการให้แล้ว แต่ต้องทดสอบทุก OS
- **DNS log จับได้ไม่หมด** — ถ้าลูกค้าใช้ DoH/DoT ในเบราว์เซอร์ จะไม่เห็น query ต้อง block DoH หรือยอมรับเป็นข้อจำกัดในรายงาน
- **Random MAC address** — iOS/Android สุ่ม MAC ต่อ SSID ทำให้ MAC ไม่ใช่ตัวระบุถาวร แต่ยังใช้ได้ภายใน session เดียว (mapping ผ่าน voucher จึงสำคัญกว่า MAC)
- ⚠️ **ช่องโหว่ bypass ของโหมดสายเส้นเดียว (D17/D19)** — ผู้ใช้ที่ตั้งค่า IP เองให้อยู่วงเดียวกับเราเตอร์ สามารถออกเน็ตโดยไม่ผ่าน Pi และ**ไม่ถูกบันทึก log** · ป้องกันได้ด้วย Access Control ที่เราเตอร์เป็นหลัก แต่**ปิดไม่ได้ 100% ด้วยซอฟต์แวร์บน Pi ฝ่ายเดียว** เพราะ Pi ไม่ได้อยู่บนเส้นทางบังคับ (ไม่ใช่ inline) — **นี่เป็นข้อจำกัดสำคัญที่สุดของสถาปัตยกรรมนี้ ต้องเขียนในบทที่ 5 พร้อมข้อเสนอแนะว่าการใช้งานจริงต้องใช้ 2 อินเทอร์เฟซหรือ managed switch + VLAN** · วิเคราะห์เต็มใน §3.1.4

---

## 7. Repository Layout

> ✅ = มีไฟล์จริงแล้วและมีเทสต์ผ่าน · ⬜ = ยังไม่ได้เขียน · 🔶 = มีไฟล์แล้วแต่ยังไม่เคยรันกับของจริง (ต้องมี MariaDB/ฮาร์ดแวร์)

```
cafe-wifi/
├── PROJECT_PLAN.md              ✅ ไฟล์นี้ -- เอกสารหลัก
├── README.md                    ✅
├── install.sh                   ✅ ตัวติดตั้งสากล (ดู §17) -- ยังไม่เคยรันบนเครื่องจริง
├── .env.example / .gitignore    ✅
├── docs/
│   ├── privacy-policy-th.md     ✅ ร่างนโยบายความเป็นส่วนตัว (ต้องให้นักกฎหมายตรวจก่อนใช้จริง)
│   └── test-plan.md             ✅ แผนทดสอบละเอียด แยกตามสิ่งที่ต้องมีฮาร์ดแวร์/ไม่ต้องมี
├── app/
│   ├── requirements.txt         ✅
│   ├── common/
│   │   ├── crypto.py            ✅ argon2id, HMAC, AES-256-GCM, mask, thai-id checksum (18 เทสต์)
│   │   ├── db.py                ✅ PyMySQL helper -- execute() คืน rowcount (แก้บั๊ก 2026-08-26 เดิมคืน lastrowid ผิด)
│   │   ├── audit.py             ✅ audit_log (dynamic dispatch ไป db.execute)
│   │   ├── traffic.py           ✅ ใหม่ (แก้บั๊ก พบตอนตรวจทานรอบ 4) -- sum_session_traffic_bytes()
│   │   │                          ย้ายมาจาก tools/enforce_voucher_expiry.py เพราะ app/fas/app.py
│   │   │                          เคย import ข้ามชั้นจาก tools/ ตรง ๆ (3 เทสต์)
│   │   └── models.py            ⬜ ไม่จำเป็น -- ตอนนี้แต่ละ view เขียน SQL ตรงเอง
│   ├── admin/                   Admin Panel (gunicorn :18443 หลัง nginx :8443)
│   │   ├── app.py               ✅ /setup, /login, /issue (POST-Redirect-GET), /customers,
│   │   │                          /reveal, /vouchers/<id>/revoke, /customers/<id>/block,
│   │   │                          /logs/verify (N2 -- T12 ผ่านเว็บ) (22 เทสต์)
│   │   └── templates/           ✅ 11 ไฟล์ (dashboard มีปุ่มยกเลิก voucher + ตรวจ log,
│   │                              customers มีปุ่มระงับ, logs_verify.html ใหม่)
│   ├── fas/                     Captive Portal (gunicorn :18080 หลัง nginx :8080)
│   │   ├── app.py               ✅ /login (GET ถอดรหัส + POST ตรวจ voucher), /policy (17 เทสต์)
│   │   ├── opennds_proto.py     ✅ AES-256-CBC ตาม openNDS FAS level 2 (15 เทสต์) 🔶 ยังไม่ทดสอบกับ openNDS จริง
│   │   └── templates/           ✅ 5 ไฟล์
│   └── logger/
│       ├── run_all.py           ✅ entrypoint (ไม่มี unit test -- ต้องมี conntrack+root)
│       ├── conn_collector.py    ✅ parser 6 เทสต์ + insert (batch)
│       ├── dns_collector.py     ✅ parser+correlator 8 เทสต์
│       ├── integrity.py         ✅ hash chain -- pattern default แก้ให้ตรงชื่อไฟล์ dateext
│       │                          ของ logrotate จริงแล้ว (เดิมไม่เคยผนึกไฟล์เลยสักไฟล์บนเครื่องจริง)
│       └── netutil.py           ✅ resolve MAC จาก ARP -- ตอนนี้ fas/app.py เรียกใช้จริงด้วย (H2)
├── sql/
│   ├── 001_schema.sql           🔶 เขียนครบตาม §5 แต่ยังไม่เคย apply กับ MariaDB จริง
│   ├── 003_partitions.sql       🔶 partition รายสัปดาห์ + event scheduler (optional, ยังไม่ทดสอบ)
│   └── 004_freeradius.sql       ⬜ Phase 5
├── tests/  (รวม 151 เคสที่ pytest เก็บได้ — 147 รันผ่านจริงยืนยันแล้วบนเครื่องนี้, 4 ต้องรันบน Linux จริง
│           เพราะพึ่ง POSIX shebang/exec-bit ที่จำลองบน Windows ไม่ได้ — ดูวิธีรันใน §17)
│   ├── conftest.py, test_thai_id.py, test_crypto.py, test_opennds_proto.py
│   ├── test_setup_flow.py, test_fas_flow.py, test_logger.py, test_purge_and_export.py
│   ├── test_backup_db.py        ✅ ใหม่ (H4) -- ทดสอบ pipe จริงด้วย gzip ตัวจริง ไม่ mock + copy_offsite() (N4) 11 เทสต์
│   ├── test_enforce_voucher_expiry.py  ✅ ใหม่ (H3/M1/M2)
│   ├── test_admin_issue_and_moderation.py  ✅ ใหม่ (M6, revoke/block, validation)
│   ├── test_traffic.py          ✅ ใหม่ (แก้บั๊ก รอบ 4 -- import ข้ามชั้น)
│   ├── test_check_disk.py       ✅ ใหม่ (N1, CODING_BRIEF.md) -- 12 เทสต์
│   ├── test_logs_verify.py      ✅ ใหม่ (N2, CODING_BRIEF.md) -- 6 เทสต์
│   └── load/locustfile.py       ⬜ T14 (ต้องมีเครื่อง gateway จริงให้ยิงโหลด)
├── tools/
│   ├── reset_admin.py           ✅
│   ├── purge_old_data.py        ✅ anonymize (ไม่ใช่ DELETE) ลูกค้าเก่า + ปฏิเสธถ้า retention < 90 วัน (8 เทสต์)
│   ├── export_evidence.py       ✅ export CSV + SHA256 manifest + audit (6 เทสต์)
│   ├── backup_db.py             ✅ ใหม่ (H4) -- mysqldump ต่อ pipe จริงเข้า gzip, atomic rename, prune ตาม retention
│   │                              + copy_offsite() (N4, CODING_BRIEF.md) ไป OFFSITE_BACKUP_DIR ถ้าตั้งไว้
│   ├── enforce_voucher_expiry.py  ✅ ใหม่ (H3/M1/M2) -- ndsctl deauth 🔶 + ปิด session ค้าง + รวมยอด bytes จาก conn_log
│   └── check_disk.py            ✅ ใหม่ (N1, CODING_BRIEF.md) -- แจ้งเตือนดิสก์ใกล้เต็ม (R5) ต่อเข้า cafe-maintenance.service — 12 เทสต์
```

**หมายเหตุเรื่องพอร์ต:** gunicorn ฟังที่ `127.0.0.1` เท่านั้น (18080/18443)
แล้วให้ nginx เป็นตัวรับจากภายนอกที่ 8080 (http, หน้าลูกค้า) และ 8443 (https, หน้าพนักงาน)
เพื่อให้ TLS และ security header อยู่ที่จุดเดียว

## 8. แผนงานแบ่งเป็น Phase

> ประมาณการเป็น "สัปดาห์" (2 คนทำงานคู่ขนาน) ไม่ผูกกับปฏิทิน ปรับได้ตามจริง

### Phase 0 — เตรียมความพร้อม (1 สัปดาห์)
- จัดซื้อ/ยืมอุปกรณ์ครบตาม §11
- ตั้ง Git repo + branch strategy (`main` / `dev` / `feat/*`)
- ติดตั้ง Raspberry Pi OS Lite 64-bit, เปิด SSH key-only, ตั้ง hostname `cafe-gw`
- **DoD:** SSH เข้า Pi ได้จากเครื่องทั้งสองคน, `git push` ได้

### Phase 1 — Gateway พื้นฐาน (1–2 สัปดาห์) → O1  *(เขียนใหม่ตาม D17)*
- ตั้งค่าเราเตอร์บ้านตาม §3.1.3 (ปิด DHCP, เปิด AP Isolation, ตั้ง Access Control) — **ทำก่อนเป็นอันดับแรก**
- ตั้ง `eth0` static `192.168.1.2/24` → ยืนยัน SSH เข้าได้ (§3.1.7 ข้อ 2-3)
- เพิ่ม secondary IP `10.10.0.1/24` บน `eth0` เส้นเดิม
- เปิด `net.ipv4.ip_forward=1`, ปิด `send_redirects` / `accept_redirects`
- nftables: NAT masquerade `10.10.0.0/24` → uplink, กฎอิงตาม **subnet** ไม่ใช่ชื่ออินเทอร์เฟซ (§3.1.6 ข้อ 4-7)
- dnsmasq: DHCP pool 10.10.0.100-250, DNS forwarder, `log-queries`
- chrony ชี้ NTP ไทย + ตรวจ offset
- **DoD:** เครื่องต่อ Wi-Fi ได้ IP `10.10.0.x` อัตโนมัติ (จาก Pi ไม่ใช่เราเตอร์) และออกเน็ตได้; SSH ยังเข้าได้ตลอด; `chronyc tracking` offset < 10 ms

### Phase 2 — Captive Portal (2–3 สัปดาห์) → O1, O4
- ติดตั้ง openNDS, ตั้ง `gatewayinterface = eth0` + `gatewayaddress = 10.10.0.1` (§3.1.6 ข้อ 9) · **ทดสอบ R11 ก่อนเป็นอันดับแรก**
- ตั้ง FAS level 2: `fasport 8080`, `faspath /login`, `faskey <random>`
- เขียน FAS ขั้นต่ำ (hardcode รหัสผ่านไว้ก่อน) → กด login แล้วออกเน็ตได้
- ทำ walled garden: อนุญาต DNS, NTP, และโดเมนตรวจจับ captive portal
- ตั้งเราเตอร์บ้านเป็นตัวปล่อย Wi-Fi (ปิด DHCP) + เปิด Client Isolation (§3.1.3)
- **DoD:** เครื่อง iOS / Android / Windows / macOS ทั้ง 4 แพลตฟอร์ม เด้งหน้า login อัตโนมัติและใช้เน็ตได้หลัง login; เครื่องลูกค้า ping กันเองไม่ได้

### Phase 3 — Admin Panel + Voucher System (3 สัปดาห์) → O2
- MariaDB + schema §5
- `common/crypto.py`: argon2id, HMAC, AES-GCM, mask, thai id checksum + unit test
- Admin: login พนักงาน, ออก voucher, ค้นหาลูกค้า (masked), ระงับ voucher, ประวัติการออก
- FAS ต่อ DB จริง: ตรวจ voucher, ผูก MAC, จำกัดจำนวนอุปกรณ์, หมดอายุ
- Nginx + TLS self-signed สำหรับ Admin Panel + จำกัดการเข้าถึงด้วย nftables
- **DoD:** พนักงานออก voucher → ลูกค้า login ได้จริง → หมดอายุแล้วเน็ตตัดอัตโนมัติ; unit test ผ่านหมด

### Phase 4 — Logging & Compliance (2–3 สัปดาห์) → O3
- `conn_collector.py`: `conntrack -E -o timestamp` → parse → batch insert
- `dns_collector.py`: tail `/var/log/dnsmasq.log` → parse → insert
- เขียนคู่ขนานลง SSD เป็นไฟล์ append-only + gzip + hash chain รายวัน
- logrotate 180 วัน, MariaDB partition ราย 7 วัน + event drop
- หน้ารายงานใน Admin: ค้นหา log ตามช่วงเวลา/MAC/โดเมน, export CSV+SHA256
- `export_evidence.py` สำหรับส่งเจ้าหน้าที่
- **DoD:** ให้เครื่องทดสอบเข้าเว็บ 10 เว็บ → ค้นย้อนกลับใน Admin เจอครบว่าเลขบัตรใด (masked) เข้าเว็บไหน เวลาใด; ทดสอบ throughput log ที่ 20 clients พร้อมกันแล้วไม่ drop

### Phase 5 — Hardening + RADIUS + สาธิตการโจมตี (2–3 สัปดาห์) → O4
- FreeRADIUS + rlm_sql, ให้ openNDS/FAS ตรวจผ่าน RADIUS, เก็บ radacct
- fail2ban, rate limiting, 2FA พนักงาน (TOTP)
- **การทดลองเชิงวิจัย** (ส่วนสำคัญของเล่ม): จำลอง ARP spoof / MITM ด้วย `arpspoof`+`ettercap` และ sniff ด้วย `tcpdump` ในสภาพแวดล้อมทดสอบปิด → วัดผล "ก่อน/หลัง" เปิดมาตรการ พร้อมตาราง
- ทดสอบโหลดด้วย Locust / iperf3
- **DoD:** มีตารางผลการทดลองว่ามาตรการใดกันการโจมตีใดได้ พร้อมหลักฐาน screenshot/pcap

### Phase 6 — รายงาน + นำเสนอ (2–3 สัปดาห์)
- เขียนเล่ม 5 บท, ทำ diagram ให้สวย (draw.io / Mermaid)
- คู่มือติดตั้ง + คู่มือพนักงาน
- ซ้อมสาธิต + เตรียมแผนสำรอง (บันทึกวิดีโอ demo เผื่อเน็ตงานล่ม)
- **DoD:** ส่งเล่ม + สาธิตได้ภายใน 15 นาทีโดยไม่ติดขัด

---

## 9. Task Board

> อัปเดตช่องนี้ทุกครั้งที่ทำงานเสร็จ · **A** = นายลีนิกซ์ (027, สาย Network/Infra) · **B** = นายลีนุกซ์ (029, สาย App/Data)

### Phase 0
- [ ] A · จัดหาอุปกรณ์ครบตาม §11
- [x] B · สร้าง Git repo + โครงสร้างโฟลเดอร์ตาม §7  *(install.sh, README, .gitignore, .env.example พร้อมแล้ว)*
- [ ] A · ติดตั้ง RPi OS Lite 64-bit + SSH key-only + hostname `cafe-gw`
- [x] A+B · เขียน `install.sh` ติดตั้งอัตโนมัติข้าม distro (D12)
- [x] B · First-run Setup Wizard `/setup` สร้างบัญชีผู้ดูแลหลัก (D13)
- [ ] **A · ตรวจเมนูเราเตอร์ว่ามี Access Control + AP Isolation หรือไม่ แล้วจดผลลง §10** *(ทำก่อนอย่างอื่น — มีผลต่อ §6.5 และ R12)*
- [x] **B · แก้ `install.sh` ให้รองรับโหมดสายเส้นเดียวตาม §3.1.6 (10 จุด)** *(เสร็จ 2026-08-23 — ตรวจด้วย bash -n, --dry-run 3 แบบ, และ nft -c ตัวจริง ยังไม่เคยรันบนฮาร์ดแวร์จริง)*
- [ ] A · รัน `sudo ./install.sh` บน Pi จริง แล้วบันทึกปัญหาที่เจอลง §10
- [x] B · เขียน `.env.example` + `requirements.txt`

### Phase 1 — Gateway  *(ปรับตาม D17)*
- [ ] A · ตั้งค่าเราเตอร์ตาม §3.1.3 (ปิด DHCP / AP Isolation / Access Control / ปิด UPnP)
- [ ] A · ตั้ง `192.168.1.2/24` บน Pi ตามลำดับ §3.1.7 + ยืนยัน SSH ก่อนไปต่อ *(ทำมือครั้งแรกก่อนรัน install.sh — ดู §3.1.7)*
- [x] B · `configure_network()` เพิ่ม secondary IP `10.10.0.1/24` + `send_redirects=0`/`accept_redirects=0` อัตโนมัติ *(install.sh ทำให้แล้ว 2026-08-23 — ยังไม่เคยรันจริง)*
- [x] B · dnsmasq — DHCP pool + DNS + log-queries (bind เฉพาะวงลูกค้าผ่าน `listen-address`) *(install.sh ทำให้แล้ว — ยังไม่เคยรันจริง)*
- [x] B · **เขียน nftables ใหม่ทั้งชุดให้อิง subnet แทนชื่ออินเทอร์เฟซ** (§3.1.6 ข้อ 4-7) *(เสร็จแล้ว ตรวจ syntax ด้วย `nft -c` จริง — ยังไม่เคยรันจริงบนฮาร์ดแวร์ ยังไม่ได้ยืนยันพฤติกรรมจริง)*
- [ ] A · ทดสอบ T16 (bypass) + T17 (ตรวจจับ bypass) แล้วบันทึกผลจริงลง §6.5 *(ต้องรอฮาร์ดแวร์จริง)*
- [x] A · chrony (ต่อท้าย chrony.conf แบบ idempotent ไม่ลบ default ของ distro) + `check_time.sh` บันทึก offset ลง time-accuracy.log **และแจ้งเตือนแยกถ้าเกิน 10ms หรืออ่านค่าไม่ได้** ลง time-accuracy-alerts.log
- [x] B · ติดตั้ง MariaDB + `sql/001_schema.sql`  *(install.sh ทำให้อัตโนมัติแล้ว)*

### Phase 2 — Captive Portal
- [ ] **A · ทดสอบว่า openNDS ทำงานบนอินเทอร์เฟซเดียวได้หรือไม่ (R11 — ความเสี่ยงอันดับ 1)** · ถ้าไม่ได้ ลอง Plan B macvlan ตาม §3.1.6
- [ ] A · ติดตั้ง openNDS + `conf/opennds.conf` (FAS level 2) + ระบุ `gatewayaddress 10.10.0.1` ให้ชัด
- [ ] A · walled garden + ทดสอบ captive detection 4 OS  *(walled garden ใส่ใน opennds.conf โดย install.sh แล้ว — เหลือแค่ทดสอบจริง)*
- [ ] A · เปิด Client Isolation ที่เราเตอร์ + ทดสอบ ping ข้ามเครื่องต้องไม่ผ่าน *(ถ้าเราเตอร์ไม่มีฟีเจอร์นี้ ให้บันทึกเป็นข้อจำกัดตาม R12)*
- [x] B · `app/fas/opennds_proto.py` — decode/encode FAS payload (AES-256-CBC + faskey) — 15 เทสต์ผ่าน 🔶 ยังไม่ทดสอบกับ openNDS binary จริง
- [x] B · `app/fas/app.py` เต็มรูปแบบ (ไม่ใช่แค่ stub) ต่อ DB จริง: ตรวจ voucher, ผูก MAC (เทียบกับ ARP จริงด้วย — H2), จำกัดอุปกรณ์, rate limit — 17 เทสต์ผ่าน
- [x] B · templates: login/manual/error/policy
- [x] B · `tools/enforce_voucher_expiry.py` + `cafe-enforce.timer` (ทุก 5 นาที) — บังคับอายุ voucher จริงผ่าน `ndsctl deauth` แทน `SessionTimeout` ตายตัวเดิม, ปิด session ค้าง, รวมยอด traffic — 10 เทสต์ผ่าน 🔶 `ndsctl deauth` ยังไม่ทดสอบกับ openNDS จริง (ดู D21)

### Phase 3 — Admin + Voucher
- [x] B · `common/crypto.py` (argon2id, HMAC-SHA256, AES-256-GCM, mask, thai id checksum)
- [x] B · `tests/test_crypto.py` + `tests/test_thai_id.py` *(ผ่านทั้งหมดแล้ว)*
- [x] B · หน้า login พนักงาน + session + audit + rate limit
- [x] B · หน้า `/issue` — ฟอร์มกรอกเลขบัตร → ออก voucher → แสดงรหัสครั้งเดียว + consent notice
- [x] B · หน้า `/customers` + `/reveal` (เฉพาะ admin, บังคับกรอกเหตุผล, ลง audit_log)
- [x] B · `/vouchers/<id>/revoke` + `/customers/<id>/block` — เดินสาย `voucher.status='revoked'` และ `customer.is_blocked` ที่ schema ออกแบบไว้ตั้งแต่แรกแต่ไม่มี endpoint ใดเรียกใช้จริง (M2) — ปุ่มอยู่ในหน้า dashboard/customers แล้ว — 7 เทสต์ผ่าน (รวม smoke-test render template)
- [x] B · `tools/purge_old_data.py` (T11) — anonymize (ไม่ใช่ DELETE) ลูกค้าเก่า, ปฏิเสธถ้า retention < 90 วัน — 8 เทสต์ผ่าน
- [x] B · `tools/backup_db.py` — mysqldump ต่อ pipe เข้า gzip จริง + atomic rename + prune ตาม `BACKUP_RETENTION_DAYS` (default 14) รันทุกคืนผ่าน `cafe-maintenance.timer` **+ copy ออกนอกเครื่องผ่าน `copy_offsite()` (N4, CODING_BRIEF.md) ถ้าตั้ง `OFFSITE_BACKUP_DIR` ไว้** (ไม่ตั้ง = ข้าม พร้อม log ว่าข้ามเพราะอะไร ไม่ throw) — 8/11 เทสต์รันยืนยันบนเครื่องนี้แล้ว (อีก 3 ต้องรันบน Linux จริงเพราะพึ่ง POSIX exec-bit — เพิ่มจากเดิม 4 เป็น 4 เท่ากัน เพราะเทสต์ offsite ใหม่ 1 ใน 5 เคสก็ต้องพึ่ง fake mysqldump ตัวเดียวกัน) 🔶 ยังไม่รองรับส่งไป remote จริง ๆ (rclone/scp ข้ามเครื่อง) เป็นแค่ copy ไปยัง path/mount point ในเครื่องเดียวกันเท่านั้น
- [x] A · nginx + TLS self-signed + systemd services  *(install.sh สร้างให้)*
- [x] A · nftables rule ปิด Admin Panel จากฝั่งลูกค้า  *(install.sh เขียน /etc/nftables.conf ให้)*

### Phase 4 — Logging
- [x] A · `logger/conn_collector.py` (parse DESTROY event, batch insert) — 6 เทสต์ผ่าน 🔶 ยังไม่รันกับ conntrack จริง
- [x] A · `logger/dns_collector.py` (parse+correlate query/reply, tail-follow) — 8 เทสต์ผ่าน 🔶 ยังไม่รันกับ dnsmasq log จริง
- [x] A · `logger/integrity.py` hash chain (seal/verify, ตรวจจับไฟล์ถูกแก้ไข/หายได้จริง) — pattern default แก้ให้ตรงชื่อไฟล์ `dateext` ของ logrotate จริงแล้ว (C1 — เดิมไม่เคยผนึกไฟล์เลยสักไฟล์บนเครื่องจริงเพราะ pattern เดิมไม่ตรงชื่อไฟล์จริงสักไฟล์)
- [x] A · `chattr +a` บน log ที่หมุนแล้ว (N3, CODING_BRIEF.md) — เพิ่มใน `configure_logrotate()` แล้ว `prerotate` ล้าง `+a` ก่อน (กัน logrotate เองลบไฟล์เกิน retention ไม่ได้เพราะ append-only บล็อก unlink) แล้ว `postrotate` ใส่ `+a` กลับให้ไฟล์ที่หมุนใหม่ · `chattr` ล้มเหลว → warning ไม่ใช่ error 🔶 ยืนยันแค่ syntax + รันสคริปต์จริงบน temp dir (ไม่มี logrotate binary ให้ทดสอบทั้งไฟล์บนเครื่องนี้) — ยังไม่ได้ยืนยัน `chattr +a` บังคับใช้จริงบน ext4 ของ Pi
- [x] B · `tools/check_disk.py` (N1, CODING_BRIEF.md) — แจ้งเตือนดิสก์ใกล้เต็ม เขียน `${LOG_DIR}/alert.log` + แถว `audit_log` (`action='disk_alert'`) เมื่อ `LOG_DIR`/`/` เกิน `DISK_WARN_PCT`/`DISK_CRIT_PCT` (default 80/90) — ต่อเข้า `cafe-maintenance.service` แล้ว (ต่อจาก `tools.backup_db`) — 12 เทสต์ผ่าน
- [x] B · `sql/003_partitions.sql` + event scheduler จัดการ partition — ต่อสายเข้า install.sh แล้วเป็น opt-in ผ่าน `--enable-partitions` (ผูก retention กับ `LOG_RETENTION_DAYS` จริง ไม่ใช่ 180 ตายตัว) 🔶 เขียนแล้วยังไม่ apply กับ MariaDB จริง
- [ ] B · หน้าเว็บ Admin สำหรับค้นหา/กรอง log *(ตอนนี้มีแค่ export ผ่าน command line — ยังไม่มีหน้าเว็บ)*
- [x] B · `POST /logs/verify` (N2, CODING_BRIEF.md) — ปุ่มในหน้า dashboard (เฉพาะ admin) เรียก `verify_chain(SqlManifestStore(), LOG_DIR/archive)` ที่มีอยู่แล้วให้ใช้งานได้จริงจากเว็บ (เดิมเรียกได้แค่ผ่าน CLI) แสดงผลเป็นตาราง `IntegrityIssue` ที่ `logs_verify.html` ใหม่ + ลง `audit_log` ทุกครั้ง (`action='verify_integrity'`) — ปิด T12 ให้สาธิตสดได้ใน 20 วินาที — 6 เทสต์ผ่าน (chain สมบูรณ์/hash_mismatch/missing_file/staff โดน 403/ไม่ login redirect/ปุ่มโชว์เฉพาะ admin)
- [x] B · `tools/export_evidence.py` — export CSV + SHA256 manifest + audit log — 6 เทสต์ผ่าน
- [ ] A+B · ทดสอบย้อนรอย end-to-end: เข้าเว็บ 10 เว็บ → ค้นเจอครบ

### Phase 5 — Hardening + RADIUS
- [ ] A · `setup-07-freeradius.sh` + `sql/004_freeradius.sql`
- [ ] B · ให้ FAS ตรวจสอบผ่าน RADIUS + บันทึก radacct
- [ ] A · fail2ban + rate limit + ปิดพอร์ตที่ไม่จำเป็น
- [ ] B · 2FA (TOTP) สำหรับบัญชี admin
- [ ] A+B · การทดลองโจมตี ARP spoof / sniffing วัดผลก่อน-หลัง
- [ ] A · load test iperf3 + Locust

### Phase 6 — เอกสาร
- [ ] B · `docs/privacy-policy-th.md`
- [ ] A · คู่มือติดตั้ง (install guide)
- [ ] B · คู่มือพนักงาน (1 หน้า, มีภาพประกอบ)
- [ ] A+B · เล่มรายงาน 5 บท + สไลด์นำเสนอ
- [ ] A+B · ซ้อมสาธิต + อัดวิดีโอสำรอง

---

## 10. Work Log

| วันที่ | ผู้ทำ | สิ่งที่ทำ | ผลลัพธ์ / ปัญหาที่เจอ |
|---|---|---|---|
| 2026-08-22 | Claude | จัดทำแผนงานฉบับนี้จากข้อเสนอโครงการ | ตัดสินใจ D1–D11, ระบุประเด็น PDPA เรื่องเลขบัตร ปชช. และประเด็น payload capture |
| 2026-08-22 | Claude | เขียน `install.sh` (1,175 บรรทัด) ติดตั้งข้าม distro | ตรวจ `bash -n` ผ่าน, รัน `--dry-run` ผ่านครบทุกขั้นตอน · ยัง**ไม่ได้ทดสอบบนเครื่องจริง** |
| 2026-08-22 | Claude | เขียน `common/crypto.py` + `admin/app.py` + templates + schema | ทดสอบ crypto 18 ข้อผ่านหมด, ทดสอบ `/setup` flow 20 ข้อผ่านหมด (ใช้ DB จำลอง) |
| 2026-08-22 | อาจารย์ | ตอบคำถาม §15 ครบ 5 ข้อ | เพิ่ม D14–D16, ตัดงาน syslog ภายนอกออก |
| 2026-08-22 | Claude | เขียน Captive Portal เต็มรูปแบบ (`fas/app.py`, `opennds_proto.py`) | ทดสอบด้วย mock openNDS gateway 32 เคสผ่าน (proto 15 + flow 17) · พบและบันทึกข้อจำกัดจริงของ openNDS FAS level 2: AES-CBC ไม่มี integrity check · **ยังไม่ทดสอบกับ openNDS binary จริง** |
| 2026-08-22 | Claude | เขียน Log Collector ครบ (`conn_collector`, `dns_collector`, `integrity`, `netutil`) | 22 เคสผ่าน รวม hash-chain tamper-detection ที่ทดสอบจริงว่าจับการแก้ไขไฟล์ย้อนหลังได้ · **ยังไม่รันกับ conntrack/dnsmasq จริง** |
| 2026-08-22 | Claude | เขียน `tools/purge_old_data.py`, `tools/export_evidence.py`, `sql/003_partitions.sql`, docs 2 ไฟล์ | 21 เคสผ่าน (purge 7 + export 6 + อื่น ๆ) · purge ปฏิเสธ retention < 90 วันจริง (ทดสอบแล้ว) · partition SQL **ยังไม่เคย apply กับ MariaDB จริง** |
| 2026-08-22 | Claude | รันชุดเทสต์ทั้งหมด (100 เคส) พร้อมกัน พบบั๊กจริง 1 จุด | `common/audit.py` ผูกชื่อฟังก์ชัน `execute` ตายตัวตอน import ทำให้เปลี่ยน implementation ภายหลังไม่มีผล — แก้เป็น dynamic dispatch แล้ว, เทสต์ทั้งหมดผ่าน 100/100 คงที่ (รันซ้ำ 2 รอบยืนยัน) |
| 2026-08-23 | เจ้าของโครงงาน + Claude | **เปลี่ยนสถาปัตยกรรมเครือข่ายเป็นโหมดสาย LAN เส้นเดียว (D17-D19)** — ใช้ RPi 4B + เราเตอร์บ้าน 1 ตัว | เขียน §3.1 ใหม่ทั้งหัวข้อ (7 หัวข้อย่อย) · ยกเลิก D7 (USB Ethernet) · ปรับ D8/D9 · เพิ่มความเสี่ยง R11-R14 · เพิ่มการทดสอบ T16/T17 · ปรับตัวชี้วัด throughput 300→200 Mbps · **วิเคราะห์ช่องโหว่ bypass อย่างละเอียดใน §3.1.4 และสรุปตรง ๆ ว่าปิดไม่ได้ 100% ในโหมดนี้** · ระบุ 10 จุดที่ต้องแก้ใน install.sh (§3.1.6) พร้อม Plan B (macvlan) · **ยังไม่ได้แก้โค้ด** ตามที่เจ้าของโครงงานสั่งให้แก้แผนก่อน |
| 2026-08-23 | Claude | **แก้ `install.sh` ให้รองรับโหมดสายเส้นเดียวครบทั้ง 10 จุดตาม §3.1.6** — เปลี่ยนตัวแปร `WAN_IF`/`LAN_IF` เป็น `NIC`/`UPLINK_CIDR`/`UPLINK_GW`/`CLIENT_CIDR`, เขียน nftables ใหม่ทั้งชุดจาก interface-based เป็น subnet-based, เพิ่ม dead-man switch, เพิ่มฟังก์ชัน `cidr_to_network()`, เพิ่ม `GatewayAddress` ให้ openNDS, ตั้ง `rp_filter=0` (จุดที่ 11 นอกเหนือจากแผนเดิม เพราะจำเป็นสำหรับ asymmetric routing ของโหมดนี้) | `bash -n` ผ่าน · `--dry-run` ผ่านทั้งโหมดค่า default และระบุ `--nic/--uplink-gw/--client-cidr` ตรง ๆ · **ตรวจ nftables ruleset ที่ generate ออกมาจริงด้วย `nft -c` ตัวจริง (ไม่ใช่แค่ dry-run) — compile ผ่าน** · ชุดเทสต์ Python 100/100 ยังผ่าน (ไม่ถูกกระทบ) · flag เก่า `--wan-if`/`--lan-if`/`--lan-cidr` ยืนยันว่า `die()` ทันทีพร้อมบอกทางแก้ · **พบความย้อนแย้งเดิม**: Admin Panel URL ที่พิมพ์ตอนจบยังชี้ไป IP ฝั่งลูกค้าที่ nftables เอง block ไว้ — บันทึกเป็นคำถามเปิดใหม่ใน §15 (ไม่ใช่บั๊กจากการแก้ครั้งนี้ มีมาตั้งแต่แผนเดิม) · **ยังไม่เคยรันบนฮาร์ดแวร์จริงเลย** — R11 (openNDS บนอินเทอร์เฟซเดียว) ยังเป็นความเสี่ยงอันดับ 1 ที่ไม่ยืนยัน |
| 2026-08-23 | เจ้าของโครงงาน + Claude | **ออกแบบวิธีทดสอบในแล็บโดยไม่มีเราเตอร์จริง** — ใช้ VM Debian บน VMware เป็น "เราเตอร์จำลอง" (2 การ์ด: NAT ออกเน็ตผ่านมือถือฮอตสปอต + Bridged ไปพอร์ต Ethernet จริงของคอมที่ต่อสายตรงเข้า Pi) เขียนเป็น §3.1.8 | ยังไม่ได้ลงมือทดสอบจริง — เป็นแผนที่ตกลงกันไว้ก่อน รอเจ้าของโครงงานลงมือทำตามขั้นตอน แล้วจะเป็นการทดสอบ R11 (openNDS บนอินเทอร์เฟซเดียว) ครั้งแรกจริง ๆ |
| 2026-08-22 | Claude | ตรวจสอบรอบสุดท้าย: รัน `install.sh --dry-run` แบบเต็ม (ไม่ใส่ `--skip-network`) เพื่อจำลองเครื่องที่ไม่มี `iproute2` ติดตั้งมาก่อน | พบบั๊กจริง 2 จุดใน `install.sh` (ดูรายละเอียดใน §17) — แก้ทั้งคู่แล้ว, `bash -n` ผ่าน, `--dry-run` รันจบครบทุกขั้นตอนทั้งแบบมี/ไม่มี `--skip-network`, รันชุดเทสต์ Python ซ้ำอีกครั้งหลังแก้ยืนยัน 100/100 (การแก้ install.sh ไม่กระทบโค้ด Python) |
| 2026-08-26 | Claude | ไล่หาบัคทั้งโปรเจกต์ (แตก `cafe-wifi-project.tar.gz` มาอ่านโค้ดจริงทุกไฟล์ในเครื่อง, ไม่ใช่แค่ install.sh) หลังพบว่า install.sh ยังไม่มี fix ของปัญหาที่เจอจริงบน Pi | พบและแก้ 5 บั๊กจริง: **(1)** `install.sh pkg_refresh()` ฝั่ง apt ยังไม่มีการแก้ IPv6-unreachable (`Acquire::ForceIPv4`) และ `--allow-releaseinfo-change` เลย — คือสาเหตุเดียวกับที่ไปติดซ้ำๆ ตอนรันจริงบน Pi (ดู session แชท "Cafe Wi-Fi Gateway project plan") ใส่ fix ถาวรเข้าไปแล้วแทนที่จะต้องแก้มือทุกรอบที่ re-run · **(2)** `final_summary()` พิมพ์ URL หน้า `/setup` ไปที่ `CLIENT_CIDR` (วงลูกค้า) ซึ่ง nftables (T8) บล็อกไม่ให้เข้า ADMIN_PORT ได้เอง — ตอบคำถามเปิดใน §15 แล้ว แก้เป็นพิมพ์ `UPLINK_CIDR` แทน · **(3)** `app/fas/app.py` — ฟังก์ชัน `client_ip()` (validate IP จริงของ request) ถูกนิยามไว้แต่ไม่เคยถูกเรียกเลย จุด POST `/login` ใช้ `ctx.clientip` ที่มาจาก hidden form field ซึ่งไคลเอนต์ปลอมค่าได้ตรง ๆ ไปเขียนลง `audit_log`/`device.last_ip`/`portal_session.ip` (หลักฐานตาม PDPA) — แก้เป็นใช้ `client_ip()` จริงแทน · **(4)** `app/admin/app.py` หน้า `/issue` — `int(request.form.get("hours"/"devices"))` ไม่ดัก `ValueError` เลย กรอกค่าที่ไม่ใช่ตัวเลขจะได้ 500 ดิบ (ไฟล์นี้ไม่มี `@app.errorhandler(500)` ด้วย) — ห่อ `try/except` คืน error message ที่อ่านออกแทน · **(5)** `tools/purge_old_data.py` — docstring บอกว่าตั้ง `CUSTOMER_RETENTION_DAYS` ผ่าน env ได้ แต่โค้ดไม่เคยอ่านตัวแปรนี้จริง (fallback ไป `LOG_RETENTION_DAYS` เสมอ) — ต่อสายให้อ่าน env ตามที่ doc บอกจริง · โค้ดที่แก้ (Python) compile ผ่านด้วย `py_compile` ทุกไฟล์ · **ยังไม่ได้รัน pytest ในเครื่องนี้** (ไม่มี dependency ติดตั้งในเครื่อง Windows นี้) ต้องรันชุดเทสต์ยืนยัน 100/100 อีกครั้งในสภาพแวดล้อมที่มี pytest/flask/argon2/pymysql · แพ็กไฟล์ที่แก้แล้วเป็น `cafe-wifi-project-fixed.tar.gz` แยกจากไฟล์เดิม (ยังไม่ได้ทับของเดิม) |
| 2026-08-26 | Claude | ตรวจโค้ดทั้งโปรเจกต์แบบละเอียดรอบสอง (อ่านไฟล์ที่ยังไม่เคยดู: templates, sql schema เต็ม, ส่วนที่เหลือของ install.sh) ทำเป็นรายงานแยก (artifact) จัดลำดับความรุนแรง | พบข้อบกพร่องใหม่ 13 จุด ไม่ทับกับ 5 จุดของรอบก่อน แบ่งเป็น **วิกฤต 3** — C1: `logger/integrity.py` `seal_directory()` pattern default (`*.log.gz`/`*.log`) ไม่ตรงชื่อไฟล์ที่ logrotate สร้างจริงเลยสักไฟล์ (มี `dateext`) พิสูจน์ด้วยการรัน glob จริงได้ `[]`; C2: `purge_stale_customers()` เคย `DELETE FROM customer` ตรง ๆ ซึ่งชน `fk_voucher_customer` (RESTRICT ปริยาย) แตกจริงเพราะลูกค้าทุกรายมี voucher เสมอ ทำให้ cafe-maintenance.service ทั้งหน่วยหยุดกลางคัน; C3: nginx ใช้ `$proxy_add_x_forwarded_for` (ต่อท้าย ไม่เขียนทับ) แต่แอปหยิบตัวแรกจาก header — ปลอม IP ได้ ทำให้ rate-limit หน้า login เลี่ยงได้ไม่จำกัดและ `audit_log.client_ip` เชื่อถือไม่ได้ **สูง 4** — H1: `opennds.conf` (มี `FaskeyOverride`) เขียนด้วย mode 0644; H2: `device.mac`/`portal_session.mac` รับ MAC จาก hidden form field ตรง ๆ ไม่เทียบกับ ARP จริง; H3: `SessionTimeout` ใน opennds.conf ตายตัวที่ 240 นาที ไม่สนอายุ voucher จริงที่พนักงานเลือก (1-24 ชม.); H4: ไม่มี backup DB เลยในระบบทั้งที่ตั้งใจรันบน SD card **กลาง 6** — M1: portal_session ไม่เคยถูกปิดถ้าลูกค้าเดินออกไปเฉย ๆ; M2: `voucher.status`/`customer.is_blocked`/`quota_mb`/`used_mb`/`audit.REVOKE_VOUCHER` ประกาศไว้ในสคีมาแต่ไม่มี endpoint ใดเขียนถึงเลย; M3: `cafe-logger.service` รัน `User=root` ไม่มี hardening ทั้งที่ service สิทธิ์น้อยกว่ากลับมี; M4: build openNDS จาก default branch ล่าสุดทุกครั้ง ไม่ pin เวอร์ชัน; M5: logrotate postrotate เรียก `logger.integrity` โดยไม่มี env ให้เลย ถูก `\|\| true` กลบ error เงียบ ๆ; M6: `/issue` POST render ผลลัพธ์ตรง ๆ ไม่ redirect — refresh = ออก voucher ซ้ำ · เผยแพร่รายงานเป็น Artifact ให้ผู้ใช้ดูก่อนตัดสินใจแก้ |
| 2026-08-26 | Claude | ผู้ใช้สั่ง "แก้ให้หมดเลยครับ เเล้วค่อยตรวจทานอีกรอบ" — ไล่แก้ทั้ง 13 จุด (C1-C3, H1-H4, M1-M6) พร้อมเขียนเทสต์ยืนยันทุกจุดที่ทำได้ | **แก้ครบทั้ง 13 จุด** สรุปย่อ: C1 เพิ่ม pattern `*.log-*.gz`/`*.log-*` ให้ `seal_directory()` + เทสต์ regression ด้วยชื่อไฟล์ dateext จริง · C2 เปลี่ยนเป็น anonymize (ล้าง `natid_hash/natid_enc/natid_masked`) แทน DELETE เพื่อรักษาสาย FK (ดู **D20**) · C3 แก้ nginx ให้ `X-Forwarded-For \$remote_addr` (เขียนทับ) + แก้ `client_ip()` ทั้ง 2 ไฟล์ให้อ่าน `X-Real-IP` ก่อนเสมอ · H1 เปลี่ยน mode opennds.conf เป็น 0640 · H2 เพิ่มการเทียบ `ctx.clientmac` กับ `resolve_mac(real_ip)` จริงก่อนผูก MAC (ปฏิเสธถ้าไม่ตรงแต่ ARP มีข้อมูล) · H3+M1+M2 ไม่ใช่ปัญหาแยกกันจริง ๆ — เขียนรวมเป็น **`tools/enforce_voucher_expiry.py`** ตัวใหม่ + **`cafe-enforce.timer`** (ทุก 5 นาที, ดู **D21**): ตั้ง `status='expired'` ให้ voucher หมดอายุ, ปิด session ค้างพร้อมเรียก `ndsctl deauth` (🔶 ยังไม่ยืนยันบนฮาร์ดแวร์จริง), รวมยอด bytes จาก conn_log ลง `used_mb`, และเพิ่ม endpoint `/vouchers/<id>/revoke` + `/customers/<id>/block` ให้ `status='revoked'`/`is_blocked` ใช้งานได้จริงพร้อมปุ่มในหน้า dashboard/customers · SessionTimeout เปลี่ยนเป็น 1440 (ค่าสูงสุด) กัน "ตัดเร็วเกินจ่าย" ไว้ก่อนให้ enforce.timer จัดการเวลาจริงแทน · H4 เขียน **`tools/backup_db.py`** ใหม่ (mysqldump ต่อ pipe จริงเข้า gzip คนละโปรเซส ไม่ใช้ `subprocess.run(stdout=gzip.GzipFile(...))` เพราะ `GzipFile.fileno()` จะคืน fd ของไฟล์ดิบ ทำให้ข้อมูลไม่ผ่านการบีบอัดจริง — **จับได้เองก่อน ship ด้วยการรันจริงเทียบกับ gzip ตัวจริง ไม่ใช่แค่ mock**) atomic rename + prune ตาม retention, wire เข้า cafe-maintenance.service · M3 เปลี่ยน cafe-logger.service เป็น non-root + hardening ครบชุด (ต้องเปิด `AF_NETLINK` เพิ่มใน RestrictAddressFamilies เพราะ conntrack ใช้ netlink socket) · M4 เพิ่ม `--opennds-ref` pin tag พร้อม fallback ถ้า tag ไม่มีจริง · M5 ตัดการเรียก `logger.integrity` ที่พังเงียบออกจาก postrotate · M6 เปลี่ยน `/issue` เป็น POST-Redirect-GET เก็บรหัสผ่านชั่วคราวใน session (pop ทิ้งทันทีที่อ่าน) **ระหว่างเขียนเทสต์พบบั๊กแฝงเพิ่มอีก 2 จุด (ไม่ได้นับใน 13 ข้างต้น แต่แก้พร้อมกัน)**: `common/db.py execute()` เคยคืน `cur.lastrowid` ซึ่งเป็น 0 เสมอสำหรับ UPDATE/DELETE — โค้ด `/vouchers/<id>/revoke` ที่เพิ่งเขียนจะเช็ค "แก้สำเร็จไหม" ผิดเสมอถ้าไม่แก้ (ไม่มีผู้เรียกเดิมพึ่งค่าที่คืนมาอยู่แล้ว จึงเปลี่ยนเป็น `rowcount` ได้อย่างปลอดภัย); `tests/test_purge_and_export.py` เรียก `read_text()` โดยไม่ระบุ `encoding="utf-8"` ทำให้อ่านไฟล์ manifest ที่มีข้อความไทยพังบน Windows/locale ที่ไม่ใช่ UTF-8 · **ยืนยันด้วยการรัน pytest จริง** (ติดตั้ง venv ชั่วคราวแล้วลบทิ้ง ไม่ทิ้งร่องรอยในโปรเจกต์): รวม 114 เทสต์ (98 เดิม + 16 ใหม่) ผ่าน 111/111 ที่รันได้บนเครื่องนี้ — เหลือ 3 เทสต์ใน `test_backup_db.py` ที่ต้องรันบน Linux จริงเพราะพึ่ง POSIX shebang/exec-bit ที่ Windows จำลองไม่ได้ (ยืนยันกลไก pipe หลักด้วยมือแยกต่างหากแล้วว่าถูกต้อง) · เพิ่มปุ่ม "ยกเลิก"/"ระงับ"/"ยกเลิกระงับ" ในหน้า dashboard/customers พร้อม `onsubmit="confirm(...)"` · repack เป็น `cafe-wifi-project-fixed.tar.gz` (ลบ `__pycache__` ที่เคยติดไปในรอบก่อนออกด้วย) · **ยังไม่ได้รันบนฮาร์ดแวร์จริงเลย** — จุดที่ยังไม่ยืนยัน: `ndsctl deauth` ทำงานจริงไหม (ต่อเนื่องจาก R11), tag `v10.1.3` ของ openNDS ยังมีอยู่จริงไหม (ต้องเช็คก่อนใช้) |
| 2026-08-26 | Claude | ตรวจทานรอบ 3 (self-review) — อ่านโค้ดที่เพิ่งเขียนเองในรอบก่อนด้วยสายตาใหม่ + จุดที่ยังไม่เคยดูเลย (event scheduler, GRANT ของ DB user, chrony.conf, check_time.sh, gunicorn worker count) | พบ 13 จุด **4 จุดเป็นบั๊กที่ตัวเองเพิ่งสร้างขึ้นตอนแก้รอบก่อน**: (1) `cafe-enforce.service` ที่เพิ่งเขียนใหม่รัน root ไม่มี hardening — ปัญหาเดียวกับที่เพิ่งแก้ให้ `cafe-logger` ไปเอง (M3) (2) `portal_session.bytes_in/out` เขียนแค่ตอน `enforce_voucher_expiry.py` ปิด session แต่ `fas/app.py` ปิดตอน reauth ไม่เขียน — ข้อมูลไม่สม่ำเสมอ (3) `terminate_cause='voucher_expired'` ฮาร์ดโค้ดใน `close_session()` แม้ voucher จะถูกพนักงาน revoke เอง (4) `--workers 2` ที่มีอยู่เดิมทำให้การแก้ M6 (session-based one-time password) เสี่ยงเจอปัญหา SECRET_KEY ไม่ตรงกันข้าม worker **9 จุดเดิมที่เพิ่งเจอ**: sql/003_partitions.sql ไม่เคยถูกเรียกใน install.sh เลย (Task Board ติ๊กผิด), เลข retention 180 ฮาร์ดโค้ดในนิยาม event ไม่ผูกกับ `LOG_RETENTION_DAYS`, `GRANT ALL PRIVILEGES` ให้ DB user (เกินความจำเป็น มี DROP/ALTER ได้), `chrony.conf` ถูกเขียนทับทั้งไฟล์ลบ default ของ distro, `check_time.sh` วัดค่าอย่างเดียวไม่เคยเตือนเมื่อเกิน 10ms, `set -euo pipefail` ทำให้ fallback `${off:-unknown}` เป็นโค้ดตาย, rate-limit ในหน่วยความจำชนกับ `--workers 2` (limit จริงเป็น 2 เท่า), `SECRET_KEY` fallback สุ่มเงียบ ๆ ไม่มี log ต่างจาก `FAS_KEY` ที่ fail ดัง, `.env.example` ตกยุคไม่มีตัวแปรที่ backup_db.py ใช้จริง |
| 2026-08-26 | Claude | ผู้ใช้สั่งแก้ทั้ง 13 จุดจากรอบ 3 ทีละจุดจนครบแล้วตรวจทานอีกรอบ | **แก้ครบทั้ง 13 จุด** พร้อมพบและแก้ **บั๊กที่เกือบเขียนขึ้นเองอีก 1 จุดระหว่างแก้** (จับได้ก่อน ship เพราะทดสอบจริงเป็นนิสัย): ตอนแก้ chrony.conf รอบแรกใช้ `cat "$conf" | write_file "$conf"` (อ่านและเขียนไฟล์เดียวกันใน pipeline เดียว) — pipeline ทุก stage รันพร้อมกัน ฝั่งเขียน (`cat > path` ข้างใน write_file) truncate ไฟล์ได้ก่อนฝั่งอ่านอ่านจบ ทดสอบจริงด้วยลูป 20 รอบพบว่าเนื้อหาเดิมหายเกือบทุกรอบ เหลือแต่ส่วนที่ต่อท้าย — เปลี่ยนเป็นอ่านทั้งไฟล์เข้าตัวแปรผ่าน command substitution (บล็อกจนอ่านเสร็จจริง) ก่อนค่อยเขียนทับ แล้วทดสอบซ้ำ 20 รอบยืนยันว่าเนื้อหาเดิมรอดครบทุกรอบ · **สรุปการแก้แต่ละจุด**: cafe-enforce.service เปลี่ยนเป็น non-root + hardening (ไม่ต้อง CAP_NET_ADMIN เพราะแค่ shell ออกไปเรียก ndsctl ไม่แตะ raw socket เอง) · bytes_in/out: ให้ fas/app.py เรียก `sum_session_traffic_bytes()` ตัวเดียวกับ enforce_voucher_expiry.py ตอนปิด session จาก reauth ด้วย (ไม่ให้ตรรกะซ้ำสองที่) · terminate_cause: เพิ่ม `TERMINATE_CAUSE_BY_STATUS` map (expired→voucher_expired, revoked→voucher_revoked, used_up→quota_exceeded) และ SELECT `v.status` มาด้วยใน `find_sessions_to_close()` · gunicorn `--workers 2` → `--workers 1 --threads 4` (thread แชร์หน่วยความจำในโปรเซสเดียวกันได้ปกติ แก้ทั้ง rate-limit 2 เท่าและ SECRET_KEY ไม่ตรงกันพร้อมกัน) · SECRET_KEY: เพิ่ม `app.logger.error(...)` ตอน import ถ้าไม่พบใน env ทั้ง admin/app.py และ fas/app.py · sql/003_partitions.sql: ทำเป็น opt-in ผ่าน flag ใหม่ `--enable-partitions` (ไม่บังคับ ALTER TABLE บนทุกเครื่องเงียบ ๆ เพราะอาจช้า/ล็อกตารางถ้ามีข้อมูลอยู่แล้ว) ผูก retention ด้วย `ALTER EVENT ... DO CALL cafewifi_partition_maintenance(${LOG_RETENTION_DAYS})` แทนเลข 180 ตายตัว และเพิ่ม `event_scheduler=ON` ในไฟล์ my.cnf ถาวร (ไม่ใช่แค่ `SET GLOBAL` ที่หายตอน restart) · GRANT ผู้ใช้แอปเหลือแค่ `SELECT, INSERT, UPDATE, DELETE` (ไม่มีจุดไหนใน codebase รัน DDL ผ่าน user นี้อยู่แล้ว) · chrony.conf: เปลี่ยนจากเขียนทับเป็นต่อท้ายแบบ idempotent (เช็ค marker กันต่อท้ายซ้ำ) ไม่ลบ default ของ distro · check_time.sh: เอา `-e` ออก (เหลือ `-uo pipefail`) ให้ fallback "unknown" รันถึงจริงเมื่อ chronyc ล้ม + เพิ่ม `time-accuracy-alerts.log` แยกเตือนเมื่อ offset > 10ms หรืออ่านค่าไม่ได้เลย — ทดสอบทั้ง 3 เคส (เกินเกณฑ์/ในเกณฑ์/chronyc ล้ม) ด้วย fake chronyc จริงบน bash · .env.example: เพิ่ม `BACKUP_DIR`, `BACKUP_RETENTION_DAYS`, `CUSTOMER_RETENTION_DAYS` **ยืนยันด้วยการรัน pytest จริงอีกครั้ง**: 121/121 ที่รันได้บนเครื่องนี้ผ่าน (เพิ่ม 1 เทสต์ใหม่สำหรับ terminate_cause mapping, อัปเดต fixture ของ test_fas_flow.py ให้รองรับ query ใหม่) รันซ้ำกับไฟล์ที่ extract จาก tarball จริงอีกรอบยืนยันตรงกัน ก่อน repack เป็น `cafe-wifi-project-fixed.tar.gz` |
| 2026-08-26 | Claude | ตรวจทานรอบ 4 (ไม่แก้ ตามที่สั่ง "ตรวจอีกรอบโดยไม่ต้องแก้ไข") — ตรวจรอยต่อระหว่างการแก้ 2 รอบก่อนหน้า (GRANT vs backup_db.py flags), เส้นทางที่ `-y` ข้าม, ทิศทางการ import ข้ามชั้น | พบ 8 จุด **จุดร้ายแรงสุดคือรอยต่อระหว่างการแก้ของตัวเอง 2 รอบชนกัน**: รอบ 2 เขียน `backup_db.py` ใช้ `mysqldump --routines --triggers` (ต้องการสิทธิ์อ่าน `mysql.proc`/`TRIGGER`) แต่รอบ 3 จำกัด `DB_USER` เหลือแค่ `SELECT/INSERT/UPDATE/DELETE` (ถูกต้องในตัวเอง) — ผลคือ backup รายคืนที่เพิ่งเพิ่มเข้ามาแก้ H4 อาจไม่เคยสำเร็จเลยบนเครื่องจริง (ยังไม่เคยรันกับ MariaDB จริงเพื่อยืนยัน) **จุดอื่น**: (2) เช็ค "retention ≥ 90 วัน" อยู่ใน `wizard()` เท่านั้น `-y --retention-days 30` ข้าม wizard จึงข้ามการเตือน/เช็คไปเงียบ ๆ ด้วย — purge/partition maintenance จะปฏิเสธทำงานทุกคืนแบบไม่มีใครรู้ (3) `app/fas/app.py` (service หน้าบ้าน) import `sum_session_traffic_bytes` จาก `tools.enforce_voucher_expiry` (ชั้น CLI งานบำรุงรักษา) ตรง ๆ — ผิดทิศทางการพึ่งพา (4) ปิด session ตอน reauth: `fetchone()` ดึง `started_at` มาแค่แถวเดียวแต่ `UPDATE` แก้ทุกแถวที่ mac ตรงกัน — ถ้ามี session ค้างเปิดพร้อมกัน > 1 อัน จะเขียนทับ bytes ผิดแถว (5) `.env.example` มี `CUSTOMER_RETENTION_DAYS` แต่ install.sh ไม่เคยเขียนค่านี้ลง secrets.env จริง ไม่มีคำอธิบายว่าตั้งใจ (6) `ENABLE_PARTITIONS` ไม่ถูกบันทึกใน `install.state` (7) `--workers 1` ที่เปลี่ยนไปรอบ 3 เป็น tradeoff จริงที่ควรบันทึกไว้ชัดเจน (ไม่มี worker สำรองถ้า worker เดียวค้าง) (8) `time-accuracy-alerts.log` ถูกสร้างโดย root (cafe-maintenance ไม่มี User=) แต่ logrotate ตั้ง owner คืนเป็น cafewifi — ไม่สอดคล้องกันตั้งแต่ไฟล์แรกก่อนหมุนรอบแรก · **สิ่งที่ตรวจแล้วสะอาด**: cafe-enforce.service hardening, chrony.conf append logic, check_time.sh 3 เส้นทาง, ลำดับ --enable-partitions, เทสต์ 121/121 |
| 2026-08-26 | Claude | ผู้ใช้สั่งแก้ทั้ง 8 จุดจากรอบ 4 | **แก้ครบทั้ง 8 จุด**: (1) เอา `--routines --triggers` ออกจาก `mysqldump` ใน `backup_db.py` แทนที่จะเพิ่มสิทธิ์ `DB_USER` กลับไป (ไม่แน่ใจ 100% ว่าสิทธิ์ที่ต้องเพิ่มจริง ๆ คืออะไรกันแน่ในทุกเวอร์ชัน MariaDB — เลือกทางที่ปลอดภัยกว่าคือแยก "schema เป็นโค้ด" ออกจาก "data เป็น backup": โครงสร้าง/procedure/event มี `DROP...IF EXISTS`/`CREATE...IF NOT EXISTS` คุมอยู่แล้วใน sql/*.sql รันซ้ำได้เสมอตอน restore ไม่ต้องพึ่ง mysqldump) เพิ่ม `--no-tablespaces` กันปัญหา `PROCESS` privilege ที่คล้ายกันไปด้วย และเพิ่ม warn ใน install.sh เตือนว่า partition/event ไม่ได้อยู่ใน backup ต้องรัน sql/003_partitions.sql ซ้ำเองตอน restore (2) ย้ายเช็ค 90 วันออกจาก `wizard()` ไปไว้ใน `main()` ตรง ๆ (หลัง parse_args เสมอ) ให้ทำงานไม่ว่าจะผ่าน wizard หรือไม่ — `confirm()` คืน true ทันทีถ้า `-y` แต่บรรทัด `warn` ก่อนหน้ายังพิมพ์เสมอ ไม่เงียบเหมือนเดิม (3) สร้าง `common/traffic.py` ย้าย `sum_session_traffic_bytes()`/`BYTES_PER_MB` มาไว้ที่นี่ (ชั้นที่ทั้ง app/ และ tools/ พึ่งพาได้) แล้วให้ `tools/enforce_voucher_expiry.py` re-export กลับ (เทสต์เดิมที่เรียกผ่าน `ev.sum_session_traffic_bytes` ยังผ่านหมดโดยไม่ต้องแก้) เพิ่มเทสต์ตรงของโมดูลใหม่ 3 เคส (4) เปลี่ยนจาก `fetchone()`+`UPDATE...WHERE mac=` เป็น `fetchall()` วนปิดทีละแถวด้วย `WHERE id=` แทน พร้อมเทสต์ regression จำลอง session ค้าง 2 อันพร้อมกันของ mac เดียวกัน ยืนยันว่าปิดครบทั้งคู่ถูกต้อง (5) เพิ่มหมายเหตุใน `.env.example` ว่า `CUSTOMER_RETENTION_DAYS` ไม่ถูกเขียนโดย install.sh ต้องเพิ่มเองด้วยมือถ้าต้องการ (6) เพิ่ม `ENABLE_PARTITIONS=${ENABLE_PARTITIONS}` ลง `install.state` (7) เพิ่ม comment อธิบาย tradeoff ของ `--workers 1` แบบละเอียด (gunicorn arbiter จะฆ่า+เกิดใหม่ worker เองถ้าเกิน `--timeout 60` ไม่ต้องพึ่ง systemd) (8) `configure_time()` touch+chown+chmod ไฟล์ `time-accuracy.log`/`time-accuracy-alerts.log` ให้เป็น `${APP_USER}:${APP_USER}` mode 0640 ตั้งแต่สร้างไฟล์แรก ก่อน check_time.sh (รันเป็น root) จะเขียนถึง **ยืนยันด้วย pytest จริง**: เพิ่ม 4 เทสต์ใหม่ (3 ใน test_traffic.py + 1 regression ใน test_fas_flow.py) รวมที่ pytest เก็บได้ทั้งหมด 128 เคส (นับรวม parametrize 2 จุดที่ขยายเป็นหลายเคสต่อฟังก์ชัน) ผ่าน 125/125 ที่รันได้บนเครื่องนี้ (3 เคสเดิมใน test_backup_db.py ยังต้องรันบน Linux จริงเหมือนเดิมเพราะพึ่ง POSIX shebang/exec-bit) รันซ้ำกับไฟล์ที่ extract จาก tarball จริงยืนยันตรงกัน ก่อน repack |
| 2026-08-26 | Claude | เริ่มทำงานตาม `CODING_BRIEF.md` — ทำ `git init` ครั้งแรกของโปรเจกต์ (ยังไม่เคยมี git มาก่อนเลย) แล้วปิดงาน **N1** (แจ้งเตือนดิสก์ใกล้เต็ม) | **git**: แตกทาร์บอล `cafe-wifi-project-fixed.tar.gz` ทับ `PROJECT_PLAN.md`/`install.sh` ที่รากโฟลเดอร์ (คนละไฟล์กันตามที่ CODING_BRIEF.md เตือนไว้ แต่บังเอิญเนื้อหาตรงกันเป๊ะ เพราะ sync เข้าไปในทาร์บอลแล้วตอน repack รอบ 4) เพิ่ม `*.tar.gz`, `.pytest_cache/`, `*.pptx`, `รายงานเล่ม/` ลง `.gitignore` (ไม่ใช่ซอร์สโค้ด/ไฟล์ไบนารีใหญ่ที่ไม่ควรอยู่ใน git history — คนละเรื่องกับที่ CODING_BRIEF.md สั่งไว้ แต่เป็นการตัดสินใจที่สมเหตุสมผลก่อน commit แรกซึ่งย้อนกลับยากกว่าถ้า commit ไปแล้ว) commit baseline 61 ไฟล์ · **N1**: เขียน `tools/check_disk.py` ใหม่ (`check_path()`/`check_all()` แยกตรรกะล้วน ๆ ออกจาก I/O ตามแบบแผนเดิมของ `purge_old_data.py`) ตรวจ `LOG_DIR` และ `/` ด้วย `shutil.disk_usage()` เทียบ `DISK_WARN_PCT`/`DISK_CRIT_PCT` (default 80/90 จาก env) เกินเกณฑ์ → เขียน `${LOG_DIR}/alert.log` + แถว `audit_log` (`action='disk_alert'`, เพิ่มค่าคงที่ `audit.DISK_ALERT` ใหม่) ต่อ `ExecStart=-...tools.check_disk` เข้า `cafe-maintenance.service` ใน install.sh ต่อจาก `tools.backup_db` ตามที่สั่ง | เทสต์ใหม่ 12 เคสใน `tests/test_check_disk.py` ครอบ 3 กรณีตามที่สั่ง (ปกติ/เกิน warn/เกิน crit) บวก edge case (total=0, threshold ที่ขอบเขตพอดี, อ่านค่าจาก env, ยืนยัน audit_log เกิดเฉพาะตอนเกินเกณฑ์) — รันชุดเทสต์เต็มยืนยัน 140 เคสที่ pytest เก็บได้ ผ่าน 137/137 ที่รันได้บนเครื่องนี้ (เพิ่มจาก 125 เดิม, ไม่มีเคสเก่าพัง) · `bash -n install.sh` ผ่าน · 🔶ยังไม่ได้รันบน Linux จริง/ดิสก์เต็มจริง — ยืนยันแค่ตรรกะผ่าน fake `disk_usage_fn` **บั๊กที่เจอระหว่างทาง (เขียนเองแล้วจับได้เอง ไม่ได้ ship)**: ร่างแรกของเทสต์ `main()` มอนกี้แพตช์ `check_disk.shutil.disk_usage` แล้วคาดหวังให้ `run()`/`check_all()` เห็นค่าใหม่ — แต่พารามิเตอร์ default `disk_usage_fn=shutil.disk_usage` ถูก bind เป็นค่าคงที่ตอน import ครั้งเดียว (ข้อจำกัดของ Python เอง) การมอนกี้แพตช์ทีหลังไม่มีผล เทสต์หนึ่งตัว "ผ่านโดยบังเอิญ" เพราะดิสก์จริง (C:\\) ของเครื่องที่ทดสอบตอนนั้นเต็มเกิน 90% พอดี ไม่ได้ผ่านเพราะ mock ทำงานจริง — ลบเทสต์ `main()` ทั้งสองทิ้ง หันไปตรงกับธรรมเนียมเดิมของโปรเจกต์แทน (`purge_old_data.py`/`backup_db.py`/`enforce_voucher_expiry.py` ล้วนมาร์ก `main()` เป็น `# pragma: no cover` ไม่มีเทสต์ตรง ๆ เพราะเหตุผลเดียวกันนี้) **แผน**: ติ๊ก §9 (บรรทัดใหม่ใต้ Phase 4 + R5 ใน Risk Register) และเพิ่มแถวนี้ใน §10 แล้ว |
| 2026-08-26 | Claude | ปิดงาน **N2** (`CODING_BRIEF.md`) — ต่อปุ่ม "ตรวจสอบความถูกต้องของ log" เข้าหน้า Admin | เพิ่ม `POST /logs/verify` + `@login_required` + `@admin_required` ใน `app/admin/app.py` เรียก `verify_chain(SqlManifestStore(), LOG_DIR/"archive")` ที่มีอยู่แล้วและมีเทสต์ผ่านมาตั้งแต่รอบก่อน (ไม่ต้องเขียนตรรกะ hash chain ใหม่เลย แค่ต่อสาย) แสดงผลเป็นตารางที่ template ใหม่ `logs_verify.html` (แยก 3 คำอธิบายภาษาไทยตาม `IntegrityIssue.kind`: hash_mismatch/missing_file/chain_broken) ลง `audit_log` ทุกครั้งที่กด (`action='verify_integrity'`) ไม่ว่าผลจะเป็นอย่างไร · เพิ่มปุ่มในหน้า dashboard (การ์ดใหม่ "ความถูกต้องของ log") โชว์เฉพาะ `current_role == 'admin'` ตามแบบเดียวกับปุ่มเปิดเผยเลขบัตรใน `customers.html` — staff ธรรมดาเห็นแค่ข้อความ "เฉพาะ admin" ไม่เห็นปุ่มเลย (ไม่ใช่แค่ซ่อนด้วย CSS) | เทสต์ใหม่ 6 เคสใน `tests/test_logs_verify.py`: chain สมบูรณ์ (ไม่มี issue), ไฟล์ถูกแก้ 1 ตัวอักษรหลังผนึก (hash_mismatch — สาธิตตรงตามที่ `CODING_BRIEF.md` อธิบาย T12), ไฟล์หายไป (missing_file), staff ธรรมดาโดน 403, ไม่ login ถูก redirect ไป `/login`, ปุ่มโชว์/ไม่โชว์ถูก role — รันชุดเทสต์เต็มยืนยัน 146 เคสที่ pytest เก็บได้ ผ่าน 143/143 ที่รันได้บนเครื่องนี้ (เพิ่มจาก 137 เดิม ไม่มีเคสเก่าพัง) — ไม่แตะ install.sh เลยรอบนี้ (`bash -n` ผ่านเพราะไม่มีอะไรเปลี่ยน) 🔶 ยังไม่ได้ทดสอบกับไฟล์ log จริงบน Raspberry Pi/MariaDB จริง — ยืนยันด้วย fake `ManifestStore`/ไฟล์ temp ในเทสต์เท่านั้น ไม่มีบั๊กที่เจอระหว่างทางรอบนี้ (งานเชื่อมสายเรียบง่าย ไม่มีจุดเสี่ยง race/pipe เหมือนงานก่อน ๆ) **แผน**: ติ๊ก §9 Phase 4 (บรรทัดใหม่) และหมายเหตุ T12 ใน §12 ว่าใช้ผ่านเว็บได้แล้ว เพิ่มแถวนี้ใน §10 แล้ว |
| 2026-08-26 | Claude | ปิดงาน **N3** (`CODING_BRIEF.md`) — `chattr +a` บน log ที่หมุนแล้ว | เพิ่ม `prerotate`/`postrotate` ใน `configure_logrotate()` (install.sh): `postrotate` ใส่ `chattr +a` ให้ไฟล์ `*.log-*` ทั้งหมดใน `olddir` (append-only จริง — เขียนทับ/ลบไม่ได้แม้เป็น root จนกว่าจะ `chattr -a` ก่อน) **คิดล่วงหน้าถึงผลข้างเคียงที่จะเกิดจริงถ้าไม่ทำ**: append-only บล็อก `unlink()` ด้วย ทำให้ logrotate เองจะ "ลบไฟล์เก่าที่เกิน `rotate ${LOG_RETENTION_DAYS}` ไม่ได้อีกเลย" ถ้าไม่มีใครมาเคลียร์ flag ก่อน — แก้ด้วยการเพิ่ม `prerotate` ที่ `chattr -a` ไฟล์ทั้งหมดในไดเรกทอรีก่อน (ก่อน logrotate ลบไฟล์เก่าในรอบเดียวกัน) แล้วให้ `postrotate` ใส่ `+a` กลับทุกไฟล์อีกครั้งหลังหมุนเสร็จ — มีช่วงเสี้ยววินาทีระหว่าง prerotate ถึง postrotate ที่ไฟล์ไม่มี `+a` ชั่วคราว ยอมรับได้เพราะเป็นแค่ตอนรัน logrotate เอง (คนละเรื่องกับใครพยายามแก้ไขไฟล์ตอนไม่มีใครดู) · กัน filesystem ไม่รองรับด้วย `2>/dev/null \|\| echo "warning..." >&2` (ไม่ทำให้ทั้ง postrotate ล้มเหลว) | **ไม่มีเทสต์ Python** สำหรับงานนี้ (เป็น shell/logrotate config ล้วน ๆ ตรงกับที่ `CODING_BRIEF.md` ระบุเกณฑ์ผ่านไว้ว่า `bash -n` + `--dry-run` เท่านั้น ไม่ใช่ pytest) — ยืนยันด้วย 3 วิธีแทน: (1) `bash -n install.sh` ผ่าน (2) ดึงเฉพาะ `configure_logrotate()` มารันแยกในเครื่องนี้ (เครื่องนี้ไม่มี `/etc/os-release` ทำให้รัน `install.sh --dry-run` เต็มไฟล์ไม่ได้ตั้งแต่ `detect_distro` เหมือนที่เจอมาตลอดหลายรอบ) ยืนยันว่าตัวแปรทุกตัวถูกแทนค่าถูกต้องและ syntax ของ logrotate stanza (`prerotate`/`postrotate`/`endscript`) ถูกต้อง (3) รัน `chattr -a`/`chattr +a` ตัวจริงกับไฟล์จริงใน temp dir เพื่อยืนยันว่า script บอดี้ไม่มี syntax error และ fallback `\|\| echo ... >&2` ทำงานจริงเมื่อ chattr fail (บังคับ fail ด้วย path ที่ไม่มีอยู่จริงเพื่อพิสูจน์) — พบว่า `chattr` บน Windows/msys คืน exit 0 และ `lsattr` แสดง flag `a` ด้วยซ้ำ แต่เป็นแค่ผิวเผิน (`rm` ไฟล์ที่ตั้ง `+a` แล้วยังลบผ่านได้ปกติ เพราะ NTFS ไม่บังคับใช้ attribute นี้จริง) — 🔶 ยังไม่ได้ยืนยันการบังคับใช้จริงบน ext4 ของ Raspberry Pi ต้องรอฮาร์ดแวร์จริง รันชุดเทสต์ Python เต็มอีกครั้งยืนยัน 143/143 เดิมผ่านหมด (ไม่กระทบเพราะแก้แค่ install.sh) ไม่มีบั๊กที่เจอระหว่างทางรอบนี้ **แผน**: ติ๊ก §9 Phase 4 แล้ว (ปล่อย §6.1 ไว้ตามเดิมเพราะเป็น checklist ยืนยันบนฮาร์ดแวร์จริง ไม่ใช่ checklist ว่าเขียนโค้ดแล้วหรือยัง) เพิ่มแถวนี้ใน §10 แล้ว |
| 2026-08-26 | Claude | ปิดงาน **N4** (`CODING_BRIEF.md`) — backup ออกนอกเครื่อง ปิดชุด A ทั้ง 4 งานครบแล้ว | เพิ่ม `copy_offsite(src, offsite_dir)` ใน `tools/backup_db.py` -- อ่าน `OFFSITE_BACKUP_DIR` จาก env (ไม่ตั้ง = ข้ามพร้อม log อธิบายเหตุผล ไม่ throw) คัดลอกไฟล์ backup ที่ dump เสร็จแล้วไปยัง path นั้นด้วย `shutil.copy2` + `chmod 0600` (เนื้อหาเดียวกับต้นฉบับ มี natid_enc) ความล้มเหลวของขั้นตอนนี้ (mount point ไม่อยู่/เขียนไม่ได้) ไม่ทำให้ `backup_db.py` ทั้งตัวถือว่าล้มเหลว เพราะ backup ในเครื่องสำเร็จไปแล้วก่อนหน้า -- แค่ log error แล้วคืน `None` ต่อสายเข้า `run()` เป็นพารามิเตอร์ใหม่ `offsite_dir` (fallback ไป env เหมือนพารามิเตอร์อื่น) เพิ่มฟิลด์ `offsite_path` ใน `BackupResult` เพิ่ม `OFFSITE_BACKUP_DIR` ใน `.env.example` (ตามแบบ `CUSTOMER_RETENTION_DAYS` — install.sh ไม่เขียนอัตโนมัติ ต้องรู้ mount point จริงก่อน) ปิด §11.1 ข้อ 4 ที่ค้างมาตั้งแต่ต้นโปรเจกต์ | เทสต์ใหม่ 5 เคสใน `tests/test_backup_db.py`: ไม่ตั้ง env (None + empty string 2 เคสย่อย), ปลายทางเขียนได้ (คัดลอกสำเร็จ เนื้อหาตรง), ปลายทางเขียนไม่ได้ (จำลองด้วยไฟล์ธรรมดาขวางตำแหน่งที่ควรเป็นโฟลเดอร์ — พกพาข้ามแพลตฟอร์มได้แน่นอน ต่างจาก chmod 000 ที่ไม่น่าเชื่อถือบน Windows), และเทสต์ end-to-end ยืนยันว่า `run()` ต่อสาย `copy_offsite()` เข้าจริง (เคสนี้ต้องพึ่ง fake mysqldump แบบเดียวกับเทสต์เดิม 3 เคส จึงต้องรันบน Linux จริงเหมือนกัน — รวมเป็น 4 เคสที่รันบนเครื่องนี้ไม่ได้) รันชุดเทสต์เต็มยืนยัน 151 เคสที่ pytest เก็บได้ ผ่าน 147/147 ที่รันได้บนเครื่องนี้ (เพิ่มจาก 143 เดิม ไม่มีเคสเก่าพัง) ไม่แตะ install.sh เลยรอบนี้ (`bash -n` ผ่านเพราะไม่มีอะไรเปลี่ยน) 🔶 ยังไม่รองรับส่งไป remote จริง ๆ (rclone/scp ข้ามเครื่อง) เป็นแค่ copy ไปยัง path ในเครื่องเดียวกัน/mount point ที่เข้าถึงได้ผ่าน filesystem ตรง ๆ **บั๊กที่เจอระหว่างทาง (ในเทสต์ตัวเอง ไม่ได้ ship)**: (1) `blocked_path.write_text(...)` ไม่ระบุ `encoding="utf-8"` พังบน Windows locale เหมือนบั๊กเดิมที่เคยเจอในรอบ 3 กับไฟล์เทสต์อื่น — เป็นรูปแบบบั๊กที่เกิดซ้ำเพราะเขียนโดยไม่คิดถึง default encoding ของแพลตฟอร์ม (2) assertion `oct(result.stat().st_mode)[-3:] == "600"` ใช้ไม่ได้บน Windows เพราะ `chmod()` บน Windows แค่สลับ read-only attribute ไม่ใช่ POSIX permission bits จริง -- บั๊กเดิมที่มีอยู่แล้วใน `test_dump_database_produces_valid_gzip_via_real_pipe` (assertion เดียวกันเป๊ะ) แต่ไม่เคยเจอเพราะเทสต์นั้นถูก deselect ด้วยเหตุผลอื่น (shebang) อยู่แล้วเสมอ -- เทสต์ใหม่ของ `copy_offsite()` ไม่ต้องพึ่ง shebang เลยจึงรันจริงบน Windows แล้วเผยบั๊กที่ซ่อนอยู่แต่แรกออกมา แก้ด้วยการ guard เงื่อนไขนี้ด้วย `if os.name == "posix":` **แผน**: ติ๊ก §9 Phase 3 (backup_db.py) และ §11.1 ข้อ 4 แล้ว อัปเดต "สิ่งที่ยังไม่มี/ยังไม่ทำ" ที่หัวไฟล์ เพิ่มแถวนี้ใน §10 — **ชุด A (N1-N4) ปิดครบทั้งหมดแล้ว** เหลือชุด B (N5-N8) ตามลำดับที่ `CODING_BRIEF.md` §7 แนะนำ |
| | | | |

---

## 11. รายการอุปกรณ์ (BOM)

| # | รายการ | สเปกแนะนำ | จำเป็น? | หมายเหตุ |
|---|---|---|---|---|
| 1 | **Raspberry Pi 4B** | 4GB RAM ขึ้นไป | ✅ | **ยืนยันแล้วว่าใช้รุ่นนี้** (2026-08-23) · RPi 5 เร็วกว่าแต่ไม่จำเป็น · 2GB พอไหวแต่จะตึงเมื่อรัน MariaDB + logging พร้อมกัน |
| 2 | Power supply | 15W USB-C (RPi 4B: 5V/3A) | ✅ | ใช้ของแท้ ไฟไม่พอ = ระบบไม่เสถียร |
| 3 | Active cooler / heatsink | official active cooler | ✅ | รัน 24/7 ต้องระบายความร้อน |
| 4 | microSD | 32GB A2 (ระบบปฏิบัติการ) | ✅ | |
| 5 | ~~USB3 Ethernet adapter~~ | — | ❌ | **ตัดออกแล้วตาม D17** (โหมดสายเส้นเดียว) · ถ้าภายหลังอยากปิดช่องโหว่ bypass ให้สนิท ซื้อตัวนี้ ~200-400 บาทแล้วกลับไปใช้ 2 อินเทอร์เฟซได้ (ดู §3.1.4) |
| 6 | External SSD | USB3 SATA/NVMe 128–256GB | ✅ | เก็บ log 90+ วัน (ประมาณการ ~50MB/วัน ที่ 50 ผู้ใช้/วัน) |
| 7 | **เราเตอร์ Wi-Fi บ้าน** | ตัวที่มีอยู่แล้ว · ต้องปิด DHCP ได้ · **ควร**มี AP Isolation + Access Control | ✅ | **D8, D9, D17** — ตรวจ 2 ฟีเจอร์นี้ก่อนตาม §3.1.3 เพราะมีผลต่อความปลอดภัยโดยตรง |
| 8 | สาย RJ45 | Cat5e/Cat6 1 เส้น | ✅ | เชื่อม Pi ↔ พอร์ต LAN ของเราเตอร์ (เส้นเดียวพอ) |
| 9 | UPS เล็ก | 600VA | ⬜ | กัน log หายตอนไฟดับ / SD card เสีย |
| 10 | เครื่องทดสอบ | iPhone, Android, Windows laptop, macOS | ✅ | ต้องทดสอบ captive portal ครบทุก OS · **และใช้ทดสอบ bypass ตาม T16 ด้วย** |
| 11 | เครื่องพนักงาน | tablet หรือ notebook เปิด Admin Panel | ✅ | |

---


### 11.1 เรื่อง SD card แทน External SSD — คำตอบตรง ๆ

**ใช้ SD card ได้สำหรับเฟสทดสอบในแล็บ แต่ต้องเปลี่ยนเป็น SSD ก่อนติดตั้งใช้งานจริงในร้าน**

เหตุผลเชิงตัวเลข — ปริมาณการเขียนไม่ใช่ปัญหาอย่างที่คนมักกลัวกัน:

| รายการ | ประมาณการ |
|---|---|
| conn_log + dns_log ที่ 50 ผู้ใช้/วัน | ~50-100 MB/วัน |
| รวม write amplification ของ InnoDB (~5 เท่า) | ~0.5 GB/วัน |
| ต่อปี | ~180 GB |
| ความทนทานของ SD card ระดับ A2 ทั่วไป | ~10-20 TBW |

→ เขียนปีละ 0.18 TB บนการ์ดที่ทนได้ 10 TB **ไม่มีทางเขียนจนพังในช่วงเวลาของโครงงาน**

**ความเสี่ยงจริงคือไฟดับกลางคัน ไม่ใช่การเขียนจนหมดอายุ** SD card ไม่มี power-loss
protection แบบ SSD ไฟดับตอนกำลังเขียน = filesystem หรือ InnoDB พัง = log หายทั้งก้อน
ซึ่งแปลว่าผิดกฎหมายทันที

**ถ้าจะใช้ SD card ต้องทำ 4 อย่างนี้:**

1. ใช้การ์ด **High Endurance** (SanDisk Max Endurance / Samsung PRO Endurance) ไม่ใช่การ์ดถ่ายรูปทั่วไป
2. `install.sh` ตั้ง `innodb_flush_log_at_trx_commit = 1` ให้แล้ว — **ห้ามเปลี่ยนเป็น 0 หรือ 2** เพื่อเร่งความเร็ว
3. เพิ่ม `noatime` ใน `/etc/fstab` ของ root filesystem
4. **backup ฐานข้อมูลรายวันออกไปนอกการ์ด** (USB flash drive ก็ยังดีกว่าไม่มี) — เพิ่มเข้า `cafe-maintenance.service` ✅ ทำแล้ว (N4, 2026-08-26) — ตั้ง `OFFSITE_BACKUP_DIR` ชี้ไป mount point ของ USB drive/NAS ใน secrets.env เอง (ดู `tools/backup_db.py::copy_offsite()`)

**ทางเลือกที่ดีกว่าถ้าจะซื้อเพิ่มทีหลัง:** Raspberry Pi 5 ต่อ NVMe ผ่าน PCIe HAT ได้
เร็วและเสถียรกว่า USB-SATA SSD และไม่กินพอร์ต USB

**สรุปสำหรับแผนงาน:** เริ่ม Phase 0-4 บน SD card ได้เลย ไม่ต้องรอ ใส่ SSD เป็น
checklist ของ Phase 5 (ก่อนทดสอบ T11 retention 90 วัน และก่อนสาธิต)

## 12. แผนการทดสอบ (Test Plan สรุป)

| ID | รายการทดสอบ | วิธี | เกณฑ์ผ่าน |
|---|---|---|---|
| T1 | Thai ID checksum | unit test เลขถูก 20 ชุด / เลขผิด 20 ชุด | 100% |
| T2 | Crypto round-trip | encrypt→decrypt เลขบัตร 1,000 ชุด | ตรงทุกชุด, hash ซ้ำได้ค่าเดิม |
| T3 | Captive portal detection | ต่อ Wi-Fi ด้วย iOS/Android/Win/macOS | เด้งหน้า login ทั้ง 4 ภายใน 10 วิ |
| T4 | Auth flow | login ถูก/ผิด/หมดอายุ/ถูกระงับ | พฤติกรรมตรงตามที่ออกแบบทุกกรณี |
| T5 | Device limit | login ด้วย voucher เดียวจาก 3 เครื่อง (max=2) | เครื่องที่ 3 ถูกปฏิเสธ |
| T6 | Client isolation | เครื่อง A ping/nmap เครื่อง B | ไม่มี response |
| T7 | ARP spoof | `arpspoof` จากเครื่องทดสอบ | ไม่สามารถดักข้อมูลของเครื่องอื่นได้ |
| T8 | Admin access control | เครื่องลูกค้าเปิด `https://10.10.0.1:8081` | connection refused/timeout |
| T9 | Reveal audit | admin กดเปิดเผยเลขบัตร | มีแถวใน `audit_log` ทุกครั้ง |
| T10 | Log completeness | เข้า 10 เว็บ แล้วค้นย้อนหลัง | เจอครบ 10 domain พร้อม timestamp |
| T11 | Log retention | ใส่ข้อมูลจำลอง 100 วัน แล้วรัน purge | ข้อมูล <180 วัน ยังอยู่, >180 วัน หายไป |
| T12 | Log integrity | แก้ไฟล์ log แล้วรันตรวจ hash chain | ตรวจพบความผิดปกติ — ✅ ตอนนี้กดปุ่ม "ตรวจสอบความถูกต้องของ log" ในหน้า dashboard ได้เลย (N2, 2026-08-26) ไม่ต้องเข้า CLI แล้ว สาธิตสดได้ใน 20 วินาที |
| T13 | Time accuracy | `chronyc tracking` | offset < 10 ms |
| T14 | Load test | 20 client พร้อมกัน, iperf3 + Locust 50 req/s ที่ FAS | ไม่ drop log, response < 2 วิ |
| T15 | Recovery | ถอดปลั๊กระหว่างใช้งาน แล้วเสียบใหม่ | ระบบขึ้นเองครบทุก service ภายใน 90 วิ |
| **T16** | **Bypass captive portal** (ใหม่ ตาม D19) | ตั้ง IP เครื่องทดสอบเองเป็น `192.168.1.50/24 gw 192.168.1.1` แล้วลองออกเน็ต | **ต้องออกเน็ตไม่ได้** ถ้าเราเตอร์มี Access Control (§3.1.3 ข้อ 5) · ถ้าออกได้ = บันทึกเป็นข้อจำกัดในเล่มพร้อมอธิบายเหตุผลเชิงสถาปัตยกรรม |
| **T17** | **ตรวจจับการ bypass** (ใหม่) | รัน T16 ขณะที่ Pi เฝ้า ARP/traffic อยู่ | Pi ตรวจพบและบันทึก IP/MAC แปลกปลอมในวง `192.168.1.0/24` ได้ |

---

## 13. Risk Register

| # | ความเสี่ยง | โอกาส | ผลกระทบ | แผนรับมือ |
|---|---|---|---|---|
| R1 | Wi-Fi ในตัว RPi รับ client ไม่ไหว | สูง | สูง | ใช้เราเตอร์บ้านเป็นตัวปล่อย Wi-Fi (D8/D17) — ตัดสินใจไปแล้ว ไม่ใช้ wlan0 ของ Pi |
| R2 | Captive portal ไม่เด้งบนบาง OS (HSTS/DoH) | สูง | กลาง | ใช้ openNDS ที่จัดการ detection URL ครบ + ทำหน้า "ถ้าไม่เด้ง ให้เปิด http://cafe.wifi" + ระบุเป็นข้อจำกัดในเล่ม |
| R3 | ข้อมูลเลขบัตร ปชช. รั่ว | ต่ำ | **วิกฤต** | D6 + §6.2 ครบทุกข้อ; ห้าม demo ด้วยเลขบัตรจริงของคนอื่น ใช้เลขทดสอบที่ผ่าน checksum |
| R4 | microSD พังจากการเขียน log หนัก | กลาง | สูง | ย้าย log + DB ไปอยู่บน SSD ทั้งหมด, ตั้ง `commit=600` / ใช้ `noatime` |
| R5 | Log ล้นดิสก์ | กลาง | กลาง | logrotate + partition drop + alert เมื่อ disk > 80% ✅ ทำแล้ว (N1, 2026-08-26) — `tools/check_disk.py` เขียน alert.log + audit_log เมื่อ LOG_DIR หรือ / เกิน `DISK_WARN_PCT`/`DISK_CRIT_PCT` (default 80/90) รันทุกคืนผ่าน cafe-maintenance.timer |
| R6 | ไฟดับทำให้ DB corrupt | กลาง | สูง | UPS + `innodb_flush_log_at_trx_commit=1` + backup รายวันไป external |
| R7 | อาจารย์ติงว่า "ดักจับแพ็กเก็ต" ไม่ได้ทำจริง | กลาง | กลาง | ทำโหมดสาธิต tcpdump header-only + อธิบายเหตุผล D5 ไว้ในเล่มชัดเจน (เป็นจุดแข็งด้านจริยธรรมวิจัย ไม่ใช่จุดอ่อน) |
| R8 | ทำไม่ทันเวลา | กลาง | สูง | ตัด Phase 5 (RADIUS/2FA) เป็น "งานในอนาคต" ได้ — Phase 1–4 ครบวัตถุประสงค์ O1–O3 แล้ว |
| R9 | อุปกรณ์มาไม่ทัน | กลาง | สูง | เริ่ม Phase 1-3 บน VM (Ubuntu/Debian + 2 virtual NIC) ก่อนได้เลย ย้ายลง Pi ทีหลัง |
| R10 | คนใดคนหนึ่งติดภารกิจ | กลาง | กลาง | commit ทุกวัน, code review ข้ามสาย, ไม่ให้ความรู้กระจุกที่คนเดียว |
| **R11** | **openNDS ทำงานบนอินเทอร์เฟซเดียวไม่ได้** (D17) | **กลาง** | **สูง** | นี่คือความเสี่ยงอันดับ 1 ของโหมดใหม่ · ทดสอบเป็นงานแรกสุดหลังติดตั้ง · มี Plan B = macvlan (§3.1.6) · ถ้าทั้งสองทางล้ม → ซื้อ USB Ethernet 200-400 บาท กลับไปใช้ 2 อินเทอร์เฟซ (โค้ดเดิมยังอยู่ใน git history) |
| **R12** | **เราเตอร์บ้านไม่มี Access Control / AP Isolation** | **สูง** | กลาง | ตรวจเมนูเราเตอร์ก่อนเริ่ม (§3.1.3) · ถ้าไม่มี → ใช้ subnet `/30` ฝั่งเราเตอร์แทน (§3.1.4 ชั้น 2) + เขียนเป็นข้อจำกัดในเล่ม · ไม่ทำให้โครงงานล้ม แต่ทำให้ O4 อ่อนลง |
| **R13** | **SSH หลุดระหว่างติดตั้ง** (เปลี่ยนค่าเครือข่ายบนสายที่ใช้ SSH อยู่) | **สูง** | กลาง | ทำตามลำดับใน §3.1.7 เคร่งครัด · ต่อจอ+คีย์บอร์ดไว้เป็นทางหนีทีไล่ · ใช้ dead-man switch `systemd-run --on-active=300 nft flush ruleset` |
| **R14** | Throughput ไม่ถึงเป้าเพราะ one-armed หักครึ่ง | กลาง | ต่ำ | ปรับตัวชี้วัด §14 เป็น ≥200 Mbps แล้ว · เน็ตร้านคาเฟ่จริงมักไม่เกินนี้อยู่แล้ว |

---

## 14. เกณฑ์วัดผลสำเร็จของโครงงาน (สำหรับบทที่ 4-5)

| ตัวชี้วัด | เป้าหมาย |
|---|---|
| เวลาตั้งแต่ต่อ Wi-Fi จนหน้า login แสดง | ≤ 10 วินาที |
| เวลาตั้งแต่กด login จนใช้เน็ตได้ | ≤ 3 วินาที |
| อัตราความสำเร็จของ captive detection (4 OS × 10 ครั้ง) | ≥ 95% |
| ความครบถ้วนของ log (ทดสอบ 500 connection) | ≥ 99% |
| เวลาที่พนักงานใช้ออก voucher 1 ใบ | ≤ 30 วินาที |
| Throughput ที่ Pi ทำได้ (iperf3 ผ่าน NAT) | **≥ 200 Mbps** *(ปรับลงจาก 300 ตาม §3.1.5 — one-armed หักครึ่ง)* |
| จำนวน client พร้อมกันที่รองรับ | ≥ 20 เครื่อง |
| การโจมตีที่ป้องกันได้ (จาก 5 รูปแบบที่ทดสอบ) | ≥ 4 รูปแบบ |

---

## 15. คำตอบจากอาจารย์ที่ปรึกษา (เคลียร์แล้ว 2026-08-22)

| # | คำถาม | คำตอบ | ผลต่อแผนงาน |
|---|---|---|---|
| 1 | ต้องส่ง log ออกไป syslog server ภายนอกไหม | **ไม่ต้อง** | D15 — ตัดงานนี้ออก เก็บบน gateway อย่างเดียว แต่เพิ่มน้ำหนักให้ hash chain + backup รายวันแทน |
| 2 | มีร้านคาเฟ่จริงให้ทดสอบไหม | **ทดสอบในแล็บก่อน** | Phase 1-5 ทำในแล็บทั้งหมด; ตัวชี้วัด §14 วัดในแล็บได้ครบ ยกเว้น "จำนวน client พร้อมกัน" ที่ต้องยืมเครื่องเพื่อนมาช่วย |
| 3 | งบประมาณ / ใช้ SD card แทน SSD ได้ไหม | **งบไม่มีปัญหา · ใช้ SD card ก่อนได้** | D14 — ดูรายละเอียดและเงื่อนไขใน §11.1 |
| 4 | อาจารย์รับได้กับ D5 (ไม่เก็บ payload) ไหม | **ไม่ได้ติงอะไร ขอแค่ไม่ผิดกฎหมาย** | D5 ยืนตามเดิม — และ D5 คือทางที่ *ถูกกฎหมายมากกว่า* เพราะ ม.26 ต้องการข้อมูลจราจร ไม่ใช่เนื้อหา ส่วน PDPA ห้ามเก็บเกินจำเป็น เขียนเหตุผลนี้ลงบทที่ 3 ให้ชัด |
| 5 | ต้องทำ WPA2-Enterprise (802.1X) ไหม | **"เอาที่พอไหว"** | D16 — Captive Portal คืองานหลัก, 802.1X เป็น stretch goal ท้าย Phase 5 ทำเป็น SSID ที่สองแยกต่างหาก ถ้าไม่ทันให้เขียนเป็น "ข้อเสนอแนะสำหรับงานในอนาคต" ในบทที่ 5 ไม่ถือว่าโครงงานไม่สมบูรณ์ |

### คำถามใหม่ที่เกิดขึ้นหลังจากนี้

- [ ] แล็บมีอินเทอร์เน็ตให้เครื่องทดสอบต่อออกได้ไหม หรือต้องจำลอง WAN เอง
- [ ] ยืมเครื่องทดสอบได้กี่เครื่องพร้อมกัน (ตัวชี้วัด "รองรับ ≥ 20 client" ต้องการของจริงหรือใช้ script จำลองได้)
- [ ] การทดลอง ARP spoof ใน Phase 5 ต้องขออนุญาตใช้แล็บเป็นกรณีพิเศษไหม
- [x] **(2026-08-23, แก้แล้ว 2026-08-26)** พนักงานจะเข้า Admin Panel จากวงไหน? nftables ปัจจุบัน block ไม่ให้วงลูกค้า (`10.10.0.0/24`) เข้า Admin Panel ได้เลย — **คำตอบชั่วคราว**: `final_summary()` ใน install.sh แก้ให้พิมพ์ URL ไปที่ IP ฝั่งอัพลิงก์ (`UPLINK_CIDR`) แทนวงลูกค้าแล้ว (nftables อนุญาตฝั่งนี้เข้า ADMIN_PORT อยู่แล้วโดยไม่ต้องเปิด exception เพิ่ม) — **แต่ยังไม่มีทางออกถ้าพนักงานต้องใช้ Wi-Fi เดียวกับลูกค้าจริงๆ** (ต้องเปิด exception เฉพาะ MAC/IP อุปกรณ์พนักงานถ้าเจอเคสนี้ ยังไม่ได้ทำ) ดู §3.1.6 หมายเหตุ implement

## 17. คู่มือ `install.sh`

ตัวติดตั้งไฟล์เดียว ตรวจ distro เองแล้วเลือก package manager ให้ (apt / dnf / yum / pacman / zypper / apk)
รองรับทั้ง systemd และ OpenRC

> 🟢 **อัปเดตแล้ว (2026-08-23)** — หัวข้อนี้อธิบายตามโหมดสาย LAN เส้นเดียว (D17) ที่แก้โค้ดเสร็จแล้ว
> flag เก่า `--wan-if`/`--lan-if`/`--lan-cidr` ถูกยกเลิก เรียกแล้วจะ `die()` ทันทีพร้อมบอกทางแก้

### คำสั่งที่ใช้บ่อย

```bash
sudo ./install.sh                                                # โหมดถาม-ตอบ (แนะนำครั้งแรก)
./install.sh --dry-run                                           # ดูว่าจะทำอะไร ไม่ต้อง root ไม่แตะระบบ
sudo ./install.sh -y --nic eth0 --uplink-gw 192.168.1.1 \
                     --uplink-cidr 192.168.1.2/24 --client-cidr 10.10.0.1/24  # ระบุครบทุกค่า
sudo ./install.sh -y --skip-network --skip-opennds                # โหมดพัฒนาบน VM/แล็ปท็อป
sudo ./install.sh --uninstall                                     # ถอนการติดตั้ง (ไม่ลบ DB/log/secrets)
```

### สิ่งที่ install.sh ทำให้ (ตามลำดับ)

| # | ขั้นตอน | ผลลัพธ์ |
|---|---|---|
| 1 | ตรวจ distro / init system | เลือก package manager และวิธีจัดการ service |
| 2 | **preflight** | RAM, พื้นที่ว่าง, อินเทอร์เน็ต, อินเทอร์เฟซมีจริงไหม, พอร์ตชนไหม, เตือนถ้ารันบน SD card, เตือนถ้า firewalld/ufw เปิดอยู่ |
| 3 | สร้าง user `cafewifi` + ไดเรกทอรี | `/opt/cafe-wifi`, `/etc/cafe-wifi`, `/var/log/cafe-wifi` |
| 4 | ติดตั้งแพ็กเกจ | python, build tools, mariadb, nginx, chrony, dnsmasq, nftables, conntrack |
| 5 | **สร้าง secrets** | สุ่ม `NATID_PEPPER`, `NATID_DEK`, `SECRET_KEY`, `FAS_KEY`, `DB_PASS`, setup token → `/etc/cafe-wifi/secrets.env` (0640) |
| 6 | Python venv + pip install | `/opt/cafe-wifi/venv` |
| 7 | ตั้งค่า MariaDB | สร้าง DB/user, โหลด `sql/001_schema.sql`, ปรับ config ให้ทนไฟดับ |
| 8 | chrony | ชี้ NTP ไทย + `check_time.sh` บันทึก offset (หลักฐานตาม ม.26) |
| 9 | เครือข่าย | ip_forward, static IP ฝั่ง LAN, dnsmasq (DHCP+DNS+query log), nftables (NAT + client isolation + DNS redirect) |
| 10 | openNDS | build จาก source แล้วเขียน `/etc/opennds/opennds.conf` (FAS level 2) |
| 11 | systemd units | `cafe-fas`, `cafe-admin`, `cafe-logger`, `cafe-maintenance.timer` (พร้อม hardening) |
| 12 | nginx + TLS | self-signed cert, http :8080 (ลูกค้า), https :8443 (พนักงาน) |
| 13 | logrotate | เก็บตาม `--retention-days` (default 180) |
| 14 | สรุป | พิมพ์ URL `/setup` + Setup Token ออกหน้าจอ |

### ข้อควรระวัง

- **`gen_secrets` จะไม่เขียนทับ `secrets.env` เดิม** — จงใจ เพราะถ้าสร้าง `NATID_DEK` ใหม่ ข้อมูลเลขบัตรที่เข้ารหัสไว้เดิมจะถอดไม่ได้ตลอดกาล
- **สำรอง `/etc/cafe-wifi/secrets.env` ไว้นอกเครื่อง** ตั้งแต่วันแรก
- `--dry-run` รันโดยไม่ต้อง root ได้ ใช้ตรวจก่อนลงเครื่องจริงเสมอ
- ยังไม่ได้ทดสอบบนเครื่องจริง — งานแรกของ Phase 0 คือรันบน Pi แล้วจดปัญหาลง §10

### First-run Setup Wizard (`/setup`)

```
install.sh สุ่ม token -> /etc/cafe-wifi/setup.token (0640)
                              |
        พนักงานเปิด https://<gw>:8443/setup
                              |
   ตาราง staff ว่าง ? --ใช่--> แสดงฟอร์ม  --token ถูก + รหัสผ่านผ่านเกณฑ์-->
                              |                     สร้าง staff role=admin
                            ไม่ใช่                    ลบ setup.token
                              |                     เขียน audit_log
                              v                            |
                        410 Gone (ปิดถาวร)  <---------------+
```

กติกาที่บังคับไว้ในโค้ด:

- ตราบใดที่ยังไม่มีบัญชี ทุก URL จะถูก redirect มา `/setup`
- เทียบ token ด้วย `hmac.compare_digest` (กัน timing attack)
- กรอก token ผิดเกิน 5 ครั้งใน 10 นาที → 429
- รหัสผ่านต้อง ≥ 12 ตัว มีพิมพ์เล็ก/พิมพ์ใหญ่/ตัวเลข
- `SELECT ... FOR UPDATE` กันสร้างบัญชีซ้อนจาก 2 request พร้อมกัน
- สร้างสำเร็จ → ลบ token ทันที → `/setup` คืน 410 ตลอดไป
- ลืมรหัสผ่าน: `sudo -E /opt/cafe-wifi/venv/bin/python -m tools.reset_admin admin`

### สถานะการทดสอบ (อัปเดตล่าสุด — หลังเขียน FAS + Logger + Tools ครบ)

| ทดสอบ | ผล |
|---|---|
| `bash -n install.sh` | ✅ ผ่าน (รวมหลังแก้เป็นโหมดสายเดียว D17) |
| `./install.sh --dry-run -y --skip-network --skip-opennds` (โหมดพัฒนา) | ✅ รันครบทุกขั้นตอน |
| `./install.sh --dry-run -y` (โหมดเต็ม ไม่ข้ามอะไรเลย จำลองเครื่องที่ไม่มี `iproute2`) | ✅ รันครบทุกขั้นตอน — พบและแก้บั๊ก 2 จุดระหว่างทาง (รายละเอียดด้านล่าง) |
| `./install.sh --dry-run -y --nic eth0 --uplink-gw 192.168.1.1 --uplink-cidr 192.168.1.2/24 --client-cidr 10.10.0.1/24` **(ใหม่ 2026-08-23 — โหมดสายเดียว)** | ✅ รันครบทุกขั้นตอน — ยืนยัน `ip addr add` 2 ที่อยู่, `ip route replace default`, เขียนไฟล์ dnsmasq/nftables/opennds.conf ถูกต้องตามที่ออกแบบใน §3.1.6 |
| `--wan-if` / `--lan-if` / `--lan-cidr` (flag เก่าที่ยกเลิกแล้ว) | ✅ ยืนยันว่า `die()` ทันทีพร้อมข้อความบอกให้ใช้ flag ใหม่ (ไม่ใช่แค่เงียบ ๆ ใช้ค่า default ผิด ๆ) |
| **nftables ruleset ที่ generate จาก `configure_network()` (โหมดสายเดียว) ตรวจด้วย `nft -c` ตัวจริง** | ✅ **compile ผ่าน** — ทดสอบโดย extract heredoc ออกมาแทนค่าตัวแปรจริงแล้วรัน `nft -c -f` กับ `nft` binary ในแซนด์บ็อกซ์นี้ (ไม่ใช่แค่ dry-run ของ install.sh เอง) ยืนยันว่า syntax `ip saddr $CLIENT_NET ...` ที่แทนที่ `iifname $LAN_IF ...` ถูกต้อง |
| `cidr_to_network()` (ฟังก์ชันคำนวณ network address ใหม่) | ✅ ทดสอบแยกว่า `10.10.0.1/24` → `10.10.0.0/24` และ `192.168.1.2/24` → `192.168.1.0/24` ถูกต้อง |
| ชุดเทสต์ทั้งหมด (`tests/*.py`, 100 เคส) | ✅ ผ่านทั้งหมด รันซ้ำ 2 รอบยืนยัน isolation ไม่มี cross-test contamination |
| — `test_thai_id.py` | ✅ 8 เคส |
| — `test_crypto.py` | ✅ 12 เคส |
| — `test_opennds_proto.py` | ✅ 15 เคส (รวมเคสบันทึกข้อจำกัดของ CBC ไม่มี integrity check) |
| — `test_setup_flow.py` | ✅ 9 เคส |
| — `test_fas_flow.py` | ✅ 17 เคส (mock openNDS gateway) |
| — `test_logger.py` | ✅ 22 เคส (conntrack/dnsmasq parser + hash chain) |
| — `test_purge_and_export.py` | ✅ 14 เคส |
| ติดตั้งบน Raspberry Pi จริง | ⬜ **ยังไม่ได้ทดสอบ** — งานแรกสุดของ Phase 0 |
| ติดตั้งบน Fedora / Arch / Alpine จริง | ⬜ ยังไม่ได้ทดสอบ (เขียน mapping ไว้แล้วแต่ยังไม่ยืนยัน) |
| `sql/001_schema.sql` / `sql/003_partitions.sql` กับ MariaDB จริง | ⬜ **ยังไม่เคย apply** — แซนด์บ็อกซ์นี้ติดตั้ง MariaDB ไม่ได้ (เครือข่ายถูกปิดกั้น) |
| คุยกับ openNDS binary จริง (fas_secure_enabled=2) | ⬜ **ยังไม่เคยทดสอบ** — เทสต์ทั้งหมดใช้ mock gateway ที่เราคุมทั้งสองฝั่ง ดู §17.4 |
| conn_collector / dns_collector กับ conntrack/dnsmasq log จริง | ⬜ ยังไม่เคยทดสอบ — parser ผ่านเทสต์ด้วยตัวอย่างข้อความที่จำลองขึ้นจากรูปแบบจริง แต่ไม่เคยรันกับ process จริง |

**หมายเหตุการแก้บั๊กระหว่างทาง (คุ้มค่าบันทึกไว้):** ตอนรันเทสต์ทั้งหมดพร้อมกันครั้งแรก
เจอว่า `test_setup_flow.py` fail แบบไม่คงเส้นคงวา (ผ่านเดี่ยว ๆ แต่ fail เมื่อรันรวมกับไฟล์อื่น)
สาเหตุคือ `common/audit.py` เดิมเขียน `from .db import execute` ซึ่งผูกชื่อฟังก์ชันตายตัว
ตอน import ครั้งแรก — ถ้า test ไฟล์อื่นที่ import ก่อนไป monkeypatch `db.execute` ไว้
audit.py จะยังเรียกฟังก์ชันเก่าที่ถูกผูกไว้ตั้งแต่แรกอยู่ดี (import ซ้ำไม่ทำงานเพราะ Python
cache module ไว้ใน `sys.modules`) แก้โดยเปลี่ยนเป็น `from . import db` แล้วเรียก
`db.execute(...)` แบบ dynamic ทุกครั้งที่ใช้งานจริง เก็บ finding นี้ไว้เพราะมันคือบั๊ก
จริงที่จะเกิดในโปรดักชันได้เหมือนกัน (ไม่ใช่แค่ปัญหาของชุดเทสต์เฉย ๆ) — ถ้า `db.execute`
เคยถูกแทนที่ด้วย wrapper อื่น (เช่น เพิ่ม retry logic) ในอนาคต audit log จะเงียบ ๆ
เขียนไปที่ของเก่าโดยไม่มีใครรู้ตัว ซึ่งกระทบความน่าเชื่อถือของ audit trail ตาม PDPA โดยตรง

**บั๊กที่พบเพิ่มเติมในรอบตรวจสอบสุดท้าย (`install.sh`, พบทั้งคู่จากการรัน `--dry-run` แบบเต็ม
โดยไม่ใส่ `--skip-network`):**

1. **preflight พังถ้าเครื่องยังไม่มี `iproute2`** — โค้ดเดิมเรียก `ip -o link show` และ `ss`
   ตรง ๆ ใน `preflight()` เพื่อตรวจอินเทอร์เฟซเครือข่าย แต่คำสั่งเหล่านี้มาจากแพ็กเกจ
   `iproute2` ซึ่ง `install_packages()` เพิ่งจะติดตั้งให้ *หลังจาก* `preflight()` ทำงานไปแล้ว
   บนเครื่องขั้นต่ำที่ยังไม่มี `iproute2` ติดมาแต่แรก (เช่น container/VM ที่เพิ่ง bootstrap)
   สคริปต์จะ exit 127 ทันทีเพราะ `set -Eeuo pipefail` ทำให้ทั้งสคริปต์ล้มก่อนจะได้ติดตั้ง
   อะไรเลย ถือเป็นบั๊กเรื่อง cross-distro portability จริง เพราะบาง minimal image ไม่มี
   `iproute2` ติดตั้งมาให้ตั้งแต่ต้น — **แก้แล้ว** โดยห่อการเรียก `ip`/`ss` ทุกจุดใน
   `preflight()` ด้วย `command -v ip`/`command -v ss` ถ้าไม่พบจะแสดงคำเตือนภาษาไทยแล้ว
   ข้ามการตรวจไปก่อน (จะตรวจใหม่ได้ตอนตั้งค่าเครือข่ายจริงหลัง `install_packages()` ติดตั้ง
   `iproute2` ให้แล้ว) แทนที่จะ crash ทั้งสคริปต์
2. **Bash multi-line string continuation bug ที่เกิดจากการแก้บั๊กข้อ 1 เอง** — ตอนเขียน
   ข้อความเตือนภาษาไทยที่ยาว เผลอขึ้นบรรทัดใหม่กลางสตริงโดยไม่ใส่ `\` ต่อท้ายบรรทัดแรก
   (เข้าใจผิดคิดว่า bash รวมสตริงสองบรรทัดที่อยู่ติดกันให้อัตโนมัติแบบ Python — ซึ่งไม่จริง)
   ผลคือ bash ตีความบรรทัดที่สองเป็นคำสั่งแยกต่างหาก (พยายามรันสตริงข้อความเป็นคำสั่ง)
   ทำให้ error "command not found" (exit 127) แล้วสคริปต์ล้มอีกรอบภายใต้ `set -e` —
   **แก้แล้ว** โดยรวมเป็นบรรทัดเดียว จากนั้นสแกนทั้งไฟล์ด้วย regex หา pattern เดียวกัน
   (บรรทัดที่ลงท้ายด้วย `"` ไม่มี `\` ต่อท้าย แล้วตามด้วยบรรทัดที่ขึ้นต้นด้วย `"`) ไม่พบจุดอื่น
   ยืนยันว่าเป็นจุดเดียว

ทั้งสองบั๊กนี้พบได้เพราะจงใจรัน `--dry-run` แบบเต็ม (ไม่ใส่ `--skip-network`) ในสภาพแวดล้อม
ที่ไม่มี `iproute2` ติดตั้งมาแต่แรก (ตรงกับที่แซนด์บ็อกซ์นี้เป็นจริง ๆ) แทนที่จะรันแค่โหมด
ย่อสำหรับพัฒนา ถ้ารันแค่โหมดย่อจะไม่มีทางเจอบั๊กทั้งสองข้อนี้เลย — เป็นตัวอย่างว่าทำไมต้อง
ทดสอบ "เส้นทางที่ยังไม่เคยลอง" ไม่ใช่แค่เส้นทางที่คุ้นเคย

## 16. แหล่งอ้างอิง

- openNDS FAS documentation — https://opennds.readthedocs.io/en/stable/fas.html
- openNDS repository — https://github.com/openNDS/openNDS
- การจัดเก็บ Log file ตาม พ.ร.บ.คอมพิวเตอร์ 2560 — https://ditc.co.th/knowledge/log-file/
- Log File กับร้านกาแฟ (ประชาชาติธุรกิจ) — https://www.prachachat.net/ict/news-379181
- การจัดเก็บ Log file ตามกฎหมาย (UIH) — https://www.uih.co.th/th/log-file-law-2560/
- FAQ การคุ้มครองข้อมูลส่วนบุคคล PDPA (DGA) — https://www.dga.or.th/wp-content/uploads/2022/10/1.FAQ-เกี่ยวกับการคุ้มครองข้อมูลส่วนบุคคล-PDPA.pdf
- Raspberry Pi OS based on Debian 13 Trixie — https://9to5linux.com/raspberry-pi-os-is-now-based-on-debian-13-trixie-with-fresh-new-look
