# รายงานรีวิวโค้ดรอบที่ 2 — Cafe Wi-Fi (29 กันยายน 2026)

> **ขอบเขต:** รีวิวจากการอ่านโค้ดอย่างเดียว (static review) **ไม่ได้ทดสอบบน Raspberry Pi จริง**
> ต่อยอดจาก [รายงานรอบแรก](STATIC_CODE_REVIEW_2026-09-29.md) และ [สรุปการแก้ R01–R13](FIX_SUMMARY_2026-09-29.md)
> — รายงานนี้ไม่นับซ้ำข้อที่แก้ไปแล้ว ใช้รหัส **R2-xx** เพื่อไม่ให้ชนกับ R01–R13 และรหัสบั๊กเดิมในโค้ด (C/H/M/N)

## 1. บทสรุป

| รายการ | ผล |
|---|---|
| ชุดทดสอบอัตโนมัติ | `PYTHONPATH=app pytest -q tests` → **277 passed** (venv ชั่วคราว) |
| ตรวจ syntax ตัวติดตั้ง | `bash -n install.sh` → ผ่าน |
| R01–R13 จากรอบแรก | แก้ครบตามที่ FIX_SUMMARY ระบุ |
| ข้อค้นพบใหม่รอบนี้ | **สูง 3 ข้อ, กลาง 7 ข้อ, ต่ำ 6 ข้อ** + ข้อความในเล่มที่ต้องปรับ 3 เรื่อง |

ปัญหาที่เหลือกระจุกอยู่ 2 จุดที่ตรงกับวัตถุประสงค์หลักของโครงงานพอดี:

- **Captive Portal / FAS (วัตถุประสงค์ 1.2.1)** — อุปกรณ์ถูกล็อกถาวรหลังชนเพดานจำนวนเครื่อง (R2-01)
- **Connection Log (วัตถุประสงค์ 1.2.3, ขอบเขต 1.3.4)** — log เชื่อมโยงผิดคนได้ และเวลาที่บันทึกคือเวลาจบ connection ไม่ใช่เวลาเริ่ม (R2-02)
- **ความปลอดภัยใน LAN (วัตถุประสงค์ 1.2.4)** — SSH เข้าได้จากฝั่งลูกค้าทาง IPv6 และข้อความในเล่มเรื่องกัน ARP spoof ไม่ตรงกับสิ่งที่ Pi ทำได้จริง (R2-03, หัวข้อ 4)

### สถานะการแก้ไข (สร้าง 29 ก.ย. 2026 · อัปเดต 1 ต.ค. 2026)

| ข้อ | สถานะ | commit | ทดสอบบน Pi |
|---|---|---|---|
| R2-01 | ✅ แก้แล้ว | `6c1267c` | ยังไม่ได้ทดสอบ |
| R2-02 | ✅ แก้แล้ว | `4f232c3` | ยังไม่ได้ทดสอบ (ต้องตรวจรูปแบบเอาต์พุตของ conntrack จริง) |
| R2-03 | ⚠️ แก้บางส่วน — ปิดช่องทาง IPv6 แล้ว ช่องทางตั้ง IP ในวง uplink ยังเปิดอยู่ | `6247ff4` | ยังไม่ได้ทดสอบ |
| R2-04 | ✅ แก้แล้ว | `fd604a5` | — (มีเทสต์อัตโนมัติครอบแล้ว) |
| R2-09 | ✅ แก้แล้ว | `bc7aaec` | ควรลองกดทุกปุ่มใน Admin บน Pi หนึ่งรอบ |
| R2-05 | ✅ แก้แล้ว | `9969b02` | ควรลองระงับลูกค้าที่ออนไลน์อยู่แล้วรอ enforce รอบถัดไป (≤ 5 นาที) |
| R2-08 | ✅ แก้แล้ว | `5c80836` | ควรดู `/logs` ว่า DNS query ชุดแรกหลัง login โยงหาลูกค้าได้ และเวลา `authenticated_at` ตรงกับ `session_start` ใน `ndsctl json` |
| R2-10 | ✅ แก้แล้ว | `93f8ef1` | ควรลอง `--natid` กับลูกค้าที่มี session จริง และ `ls -l` ว่าไฟล์เป็น `-rw-------` |
| R2-06 | ✅ แก้แล้ว | `17b2641` | ต้องรัน `install.sh` ใหม่ (unit เปลี่ยน) แล้ว `systemctl restart cafe-logger` ระหว่างมีทราฟฟิก และดูว่ามีไฟล์ `collector-*.json` กับ `collector-dns.offset.json` ใน `/var/log/cafe-wifi` |
| R2-07 | ✅ แก้แล้ว | `47ba1d5` | ควรดู `journalctl -u cafe-maintenance` หลังรอบ 03:30 ว่ามีบรรทัด "ลบ raw log ที่ครบอายุ…" แม้มี issue อื่นค้าง |
| หัวข้อ 4 (DoT/ข้อความในเล่ม) | ✅ แก้โค้ดและข้อความส่งต่อ | commit นี้ | ยังไม่ได้ติดตั้งหรือทดสอบ DoT บน Pi |
| R2-L02 | ✅ แก้แล้ว | commit นี้ | — (เทสต์อัตโนมัติผ่าน) |
| R2-L05 | ✅ แก้โค้ดแล้ว | commit นี้ | ยังไม่ได้ทดสอบบน Pi |
| R2-L03 | ✅ แก้โค้ดแล้ว | commit นี้ | — (เทสต์อัตโนมัติผ่าน) |
| R2-L01 | ✅ แก้โค้ดแล้ว | commit นี้ | ยังไม่ได้ทดสอบบน Pi |
| R2-L04, R2-L06 | ⏳ ยังไม่ได้แก้ | — | — |

ชุดทดสอบหลังแก้ R2-01: `PYTHONPATH=app pytest -q tests` → **297 passed** · หลังแก้ R2-10 → **320 passed** · หลังแก้ R2-06 → **332 passed** · หลังแก้ R2-07 → **339 passed** · หลังแก้ R2-L02 → **344 passed** · หลังแก้ R2-L05 → **347 passed** · หลังแก้ R2-L03 → **353 passed** · หลังแก้ R2-L01 → **356 passed**

### ระดับความสำคัญ

- **สูง** — กระทบการใช้งานจริงของลูกค้า ความถูกต้องของหลักฐานตามกฎหมาย หรือเปิดช่องเข้าถึงระบบจัดการ ควรแก้ก่อนสาธิต/ส่งเล่ม
- **กลาง** — ผิดพลาดในกรณีที่เกิดได้จริงแต่ไม่บ่อย หรือกระทบบางส่วน
- **ต่ำ** — ความเสี่ยงต่ำ ขอบกรณี หรือเป็นเรื่องความเรียบร้อย

---

## 2. ข้อค้นพบระดับสูง

### R2-01 — อุปกรณ์ถูกล็อกถาวรหลังชนเพดานจำนวนเครื่อง แม้ได้รหัสใหม่ [สูง · ยืนยันด้วยเทสต์แล้ว]

**ตำแหน่ง:** `app/fas/app.py:235-274`, `tools/reconcile_pending.py`, `app/common/db.py:24-34`

**กลไก:**

1. ใน POST `/login` โค้ดทำ `INSERT IGNORE INTO pending_mac_claim (mac)` (บรรทัด 243) **ก่อน** ตรวจเพดานจำนวนอุปกรณ์
2. ถ้าเกินเพดาน (บรรทัด 257) หรือ nonce ถูกใช้ไปแล้ว (บรรทัด 266) โค้ด `return` ออกจากกลาง `with get_conn() as conn`
3. `get_conn()` เป็น `@contextmanager` ที่ `commit()` หลัง `yield` เมื่อออกจาก block แบบปกติ — การ `return` ถือว่าปกติ **จึง commit แถว claim ที่ `portal_session_id = NULL` ลง DB**
4. `reconcile_pending.py` ลบ claim เฉพาะ `WHERE mac=%s AND portal_session_id=%s` ของ session ที่มีอยู่จริง — แถวที่เป็น `NULL` **ไม่มีใครลบเลย**
5. ครั้งถัดไปที่ MAC นี้ login: `INSERT IGNORE` ได้ `rowcount = 0` → ตอบ 409 "อุปกรณ์นี้กำลังรอยืนยันสิทธิ์" **ตลอดไป**

**สถานการณ์จริง:** ลูกค้าได้รหัสสำหรับ 2 เครื่อง แล้วลองใช้กับเครื่องที่ 3 → ได้ 403 ตามปกติ → พนักงานออกรหัสใหม่ให้ → เครื่องที่ 3 ใช้รหัสใหม่ไม่ได้อีกเลย แก้ได้ทางเดียวคือลบแถวใน DB ด้วยมือ

**หลักฐาน:** ทดสอบด้วยเทสต์ชั่วคราว (ลบทิ้งแล้ว ไม่ได้ commit) โดยใช้ fake DB ชุดเดียวกับ `tests/test_fas_flow.py`:

```python
code, pw = _make_voucher(max_devices=1)
# เครื่อง 01 login สำเร็จ -> 302
# เครื่อง 03 ใช้รหัสเดิม -> 403 (ถูกต้อง) แต่ CLAIMS["AA:BB:CC:DD:EE:03"] = None ค้างอยู่
code2, pw2 = _make_voucher(max_devices=2)   # รหัสใหม่
# เครื่อง 03 ใช้รหัสใหม่ -> 409  (ควรได้ 302)
```

ผลที่ได้: `claim left behind: None True` และ `new voucher on same device -> 409`

เทสต์เดิม `test_device_limit_enforced` ตรวจแค่ว่าได้ 403 ไม่ได้ตรวจว่า claim ถูกคืน จึงไม่เจอปัญหานี้

**แนวทางแก้:**

- ย้ายการตรวจเพดานอุปกรณ์ไปไว้**ก่อน** `INSERT IGNORE INTO pending_mac_claim` หรือ
- เรียก `conn.rollback()` ก่อน `return` ทุกจุดใน block นั้น (บรรทัด 241, 245, 260, 267) หรือเปลี่ยนให้ early-exit เป็นการ `raise` exception เฉพาะแล้วจับข้างนอก `with`
- เพิ่มงานเก็บกวาดใน `reconcile_pending.run()`: `DELETE FROM pending_mac_claim WHERE portal_session_id IS NULL` (หรือเพิ่มคอลัมน์ `created_at` แล้วลบรายการที่ค้างเกิน 1 นาที)
- เพิ่มเทสต์: หลังได้ 403/400 ต้องไม่มี claim ค้าง และ MAC เดิมใช้รหัสใหม่ได้

> **✅ แก้แล้ว — commit `6c1267c`**
>
> - `app/fas/app.py`: ย้ายขั้นตอนจอง MAC/โควตา/nonce/สร้าง pending ไปไว้ใน `_reserve_pending_session()` ถ้าถูกปฏิเสธจะคืน response กลับมา แล้ว `login()` สั่ง `conn.rollback()` ก่อน return ทุกกรณี (ไม่ต้องไล่ใส่ rollback ทีละจุด)
> - `tools/reconcile_pending.py`: เพิ่ม `purge_orphan_claims()` ลบ claim ที่ `portal_session_id IS NULL` ทุกรอบ เพื่อเก็บกวาดแถวที่ค้างบนเครื่องที่ติดตั้งไว้แล้ว แยกเป็น transaction สั้นที่แตะแค่ตารางนี้ เพื่อไม่ให้ลำดับ lock ชนกับ `/login` (claim ของ `/login` ที่ยังไม่ commit จะผูก `portal_session_id` ก่อน commit เสมอ จึงไม่ถูกลบ)
> - `tests/test_fas_flow.py`: `FakeConn` มี `rollback()` ที่ย้อนข้อมูลจริง, `test_device_limit_enforced` ตรวจว่าไม่มี claim ค้าง, เพิ่ม `test_device_rejected_at_limit_can_use_new_voucher` และ `test_consumed_nonce_rejection_leaves_no_claim` — ทั้ง 3 เทสต์ fail กับโค้ดเดิม
> - ยังไม่ได้ทดสอบบน MariaDB/Pi จริง (ดูหัวข้อ 6 ข้อ 1)

---

### R2-02 — Connection Log เชื่อมโยงผิดคนได้ และเวลาที่บันทึกคือเวลาจบ connection [สูง]

**ตำแหน่ง:** `app/logger/conn_collector.py:51, 146-170, 271-272`; ส่วนที่ใช้ผล `app/admin/app.py:562-570`, `app/common/customer.py:228-231`

**กลไก:**

1. ตัวเก็บรันด้วย `conntrack -E -e DESTROY` บันทึกเฉพาะเหตุการณ์ **DESTROY** ค่า `ts` จึงเป็นเวลาที่ entry ถูกลบออกจากตาราง conntrack
2. MAC หาจาก `/proc/net/arp` **ตอนเขียน DB** (`insert_conn_records` → `mac_cache.get(r.src_ip)`) ไม่ใช่ตอนเกิด connection
3. เวลา DESTROY ห่างจากการใช้งานจริงได้มาก:
   - TCP ที่ปิดปกติ: ค้างใน TIME_WAIT ~120 วินาที
   - UDP: 30–180 วินาที
   - TCP ที่ลูกค้าหายไปเฉย ๆ (เดินออกจากร้าน ปิด Wi-Fi): ค้างสถานะ ESTABLISHED ได้ถึง `nf_conntrack_tcp_timeout_established` = **432000 วินาที (5 วัน)** ตามค่าปริยาย
   - ถ้า DB ล่ม record ค้างใน buffer และหา MAC ตอน retry ซึ่งช้ากว่านั้นอีก
4. ระหว่างนั้น IP อาจถูก DHCP แจกให้ลูกค้าคนใหม่ → record ได้ **MAC ของผู้ถือ IP คนใหม่** และ `ts` อยู่ในช่วง session ของคนใหม่
5. `_MAPPING_JOIN` ในหน้า `/logs` จับคู่ด้วย `mac + ip + authenticated_at <= ts <= ended_at` → **แสดงว่าเป็นทราฟฟิกของลูกค้าคนใหม่**

**ผลกระทบ:** ขัดวัตถุประสงค์ 1.2.3 โดยตรง หลักฐานตาม ม.26 อาจชี้ไปที่บุคคลที่ไม่เกี่ยวข้อง กรณีที่ไม่ได้ผิดคนก็มักได้ `mac = NULL` (ARP หมดอายุแล้ว) ทำให้โยงตัวตนไม่ได้ ต่างจากที่ R04 ตั้งใจไว้

นอกจากนี้ conn_log ยังไม่มีเวลาเริ่ม connection เลย ซึ่งควรระบุในเล่ม (ดูหัวข้อ 4)

**แนวทางแก้ (เรียงตามความคุ้มค่า):**

1. ผูก MAC ตั้งแต่ตอนเปิด connection: ฟัง `-e NEW,DESTROY` แล้วเก็บ `{conntrack id → (mac, start_ts)}` ในหน่วยความจำ ตอน DESTROY จึงใช้ MAC ที่จับไว้ตอน NEW (ต้องใช้ `-o id` เพื่อให้ได้ id) หรือ
2. หา MAC จากประวัติที่มีเวลากำกับ เช่น `portal_session` (`ip` + ช่วงเวลา) หรือ dnsmasq DHCP lease log แทน ARP ณ ปัจจุบัน
3. เปิด `sysctl net.netfilter.nf_conntrack_timestamp=1` เพื่อให้ event DESTROY มี `[start=…] [stop=…]` แล้วเพิ่มคอลัมน์ `started_at` ใน `conn_log` (ต้องทำ migration)
4. พิจารณาลด `nf_conntrack_tcp_timeout_established` สำหรับวงลูกค้า (เช่น 1–2 ชั่วโมง)
5. เพิ่มเทสต์: IP เดียวกันเปลี่ยน MAC ระหว่าง NEW กับ DESTROY แล้ว record ต้องได้ MAC เดิม

ดูเพิ่ม R2-L05 (log ทราฟฟิกของ Pi เองปนเข้ามา)

> **✅ แก้แล้ว — commit `4f232c3`** (ทำแนวทางข้อ 1, 3, 4, 5 และใช้ข้อ 2 เป็นทางสำรอง)
>
> - `conn_collector` ฟัง `-e NEW,DESTROY -o id` แล้ว `ConnTracker` จำ `{id → (mac, start)}` ตั้งแต่ตอน NEW ไว้ใช้ตอน DESTROY (จำกัด 131072 รายการ ถ้าเกินจะไล่ตัวเก่าที่สุดออกพร้อมเตือน)
> - ถ้าไม่เห็น NEW (เช่น restart หรือ ENOBUFS) จะไม่เดา MAC จาก ARP ปัจจุบัน แต่หาจาก `portal_session` ณ เวลาเริ่ม และปล่อยเป็น `NULL` ถ้าไม่ได้ MAC เดียวชัด ๆ
> - `sql/007`: เพิ่มคอลัมน์ `conn_log.started_at` (`ts` ยังเป็นเวลาจบ) ส่วน `/logs`, retention hold และ `export_evidence` ใช้ `COALESCE(started_at, ts)` และหน้า `/logs` แสดงทั้งเวลาเริ่มและเวลาจบ
> - `install.sh`: เปิด `nf_conntrack_timestamp=1` และลด `nf_conntrack_tcp_timeout_established` เหลือ 7440 วินาที (ขั้นต่ำตาม RFC 5382) ทั้งตอนติดตั้งและทุกครั้งที่บูต
> - เทสต์: IP ถูกแจกใหม่ระหว่าง NEW กับ DESTROY แล้ว record ยังได้ MAC เดิม, การ parse, การไล่ออก, การหาจากประวัติ และการ join ใน `/logs`
> - **ยังไม่ได้ตรวจบน Pi:** เอาต์พุตของ conntrack จริงมี `id=` ทั้งใน NEW/DESTROY และมี `delta-time=` เมื่อเปิด timestamp หรือไม่ และ event NEW ที่เพิ่มขึ้นทำให้ ENOBUFS กลับมาหรือไม่

---

### R2-03 — SSH/Admin เข้าได้จากฝั่งลูกค้าผ่าน IPv6 หรือการตั้ง IP ในวง uplink [สูง]

**ตำแหน่ง:** `install.sh` ฟังก์ชันเขียน `/etc/nftables.conf` (ประมาณบรรทัด 1116-1154)

```nft
ip saddr $CLIENT_NET tcp dport ${ADMIN_PORT} drop
ip saddr $CLIENT_NET tcp dport 22 drop
tcp dport ${ADMIN_PORT} accept
tcp dport 22 accept
```

**กลไก:** กฎ drop เทียบเฉพาะ `ip saddr` (IPv4 และเฉพาะวงลูกค้า) ส่วนกฎ accept ไม่จำกัด source เลย ในสถาปัตยกรรมสายเส้นเดียว (ลูกค้าอยู่ L2 เดียวกับ Pi และเราเตอร์) จึงมีทางเข้า 2 ทาง:

1. **IPv6 link-local** — Pi มี `fe80::…` บน eth0/macvlan ตามปกติ และ `sshd` ฟังที่ `::` เป็นค่าปริยาย แพ็กเก็ต IPv6 ไม่เข้าเงื่อนไข `ip saddr` จึงตกไปที่ `tcp dport 22 accept` ลูกค้าที่ `ping6 ff02::1%wlan0` จะเจอ Pi แล้ว SSH เข้าได้ ไม่พบว่า `install.sh` ปิด IPv6 บน Pi (`grep disable_ipv6` ไม่เจอ) ส่วน runbook เราเตอร์ปิดแค่ RA/DHCPv6 ฝั่งเราเตอร์ ไม่ได้ปิด link-local บน Pi
   - Admin Panel ผ่าน nginx ยังไม่โดน เพราะ `listen ${ADMIN_PORT} ssl;` ผูกแค่ IPv4 แต่ถ้าวันหนึ่งเพิ่ม `listen [::]:…` จะหลุดทันที
2. **ตั้ง IP ตัวเองในวง uplink** — ช่องทางเดียวกับที่ `bypass_detector` พยายามตรวจจับ ถ้าตั้ง IP ในวงเราเตอร์ ก็เข้า Admin Panel และ SSH ได้ด้วย ไม่ใช่แค่ออกเน็ต

ความเสี่ยงสูงขึ้นอีก เพราะเครื่องทดลองจริงยังใช้ SSH แบบรหัสผ่านที่เดาง่าย

**แนวทางแก้:**

- เปลี่ยนกฎ accept เป็น allowlist: `ip saddr <IP/วงของเครื่องแอดมิน> tcp dport { 22, ${ADMIN_PORT} } accept` และ/หรือจำกัดด้วย `ether saddr`
- เพิ่ม `meta nfproto ipv6 drop` ใน chain input (ยกเว้น `iif lo`) หรือปิด IPv6 บน Pi ด้วย `net.ipv6.conf.all.disable_ipv6=1` ถ้าไม่ได้ใช้
- ตั้ง SSH ให้ใช้กุญแจอย่างเดียว (`PasswordAuthentication no`) และเปลี่ยนรหัสผ่านผู้ใช้เริ่มต้นก่อนนำไปวางหน้างาน
- เพิ่มการทดสอบใน `docs/test-plan.md`: จากเครื่องลูกค้า `ssh -6 user@fe80::…%wlan0` และจาก IP ที่ตั้งเองในวง uplink ต้องเชื่อมต่อไม่ได้

> **⚠️ แก้บางส่วน — commit `6247ff4`**
>
> - ✅ **ช่องทาง 1 (IPv6):** `install.sh` เพิ่มกฎ drop IPv6 ขาเข้าทั้งหมดต่อจาก `iif lo accept` ใน chain input (ระบบใช้ IPv4 อย่างเดียว ส่วน `::1` ยังใช้ได้) ตรวจ ruleset ที่ได้ด้วย `nft -c` และ `nft -f` บน Debian bookworm แล้ว แต่ยังไม่ได้ทดสอบบน Pi
> - ⏳ **ช่องทาง 2 (ตั้ง IP ในวง uplink):** ยังไม่ได้แก้ ข้อจำกัดคือระบบต้องเป็น Pi ตัวเดียวต่อสาย LAN เส้นเดียวเข้าเราเตอร์ร้าน แยก interface/VLAN สำหรับจัดการไม่ได้ จึงต้องป้องกันด้วยการยืนยันตัวตน (SSH แบบกุญแจอย่างเดียว เปลี่ยนรหัสผ่านเริ่มต้น) และ/หรือ allowlist แทน
> - ⏳ SSH ยังใช้รหัสผ่าน และยังไม่ได้เพิ่มการทดสอบใน `docs/test-plan.md`

---

## 3. ข้อค้นพบระดับกลางและต่ำ

### R2-04 — Open redirect หลัง login Admin [กลาง]

**ตำแหน่ง:** `app/admin/app.py:269-270`

```python
nxt = request.args.get("next", "")
return redirect(nxt if nxt.startswith("/") else url_for("dashboard"))
```

`//evil.example/` และ `/\evil.example/` ขึ้นต้นด้วย `/` แต่ browser ตีความเป็น URL ข้ามโดเมน ผู้โจมตีส่งลิงก์ `https://<pi>:<port>/login?next=//evil.example/` ให้พนักงาน พนักงาน login จริงแล้วถูกพาไปหน้าปลอมที่หน้าตาเหมือน Admin Panel ได้ (phishing)

**แก้:** ยอมรับเฉพาะ path ที่ขึ้นต้นด้วย `/` ตัวเดียวและไม่มี `\` เช่น `nxt.startswith("/") and not nxt.startswith(("//", "/\\"))` หรือตรวจด้วย `urllib.parse.urlsplit(nxt)` ว่าไม่มี `scheme`/`netloc` พร้อมเพิ่มเทสต์

> **✅ แก้แล้ว — commit `fd604a5`**
>
> เพิ่ม `safe_next()` ใน `app/admin/app.py` รับเฉพาะ path ที่ขึ้นต้นด้วย `/` ตัวเดียว ไม่มี `\` ไม่มีอักขระควบคุม (browser ตัด tab/newline ทิ้ง ทำให้ `/\t/evil` กลายเป็น `//evil`) และ `urlsplit()` ต้องไม่มี scheme/netloc ไม่ผ่านเงื่อนไขจะกลับไปหน้า dashboard เทสต์ใน `tests/test_setup_flow.py` ครอบ path ภายในปกติและรูปแบบโจมตี 7 แบบ (4 แบบ fail กับโค้ดเดิม)

---

### R2-05 — ระงับลูกค้าแล้ว อุปกรณ์ที่ออนไลน์อยู่ยังใช้เน็ตต่อได้ [กลาง]

**ตำแหน่ง:** `app/admin/app.py:492-504`, `tools/enforce_voucher_expiry.py:147-154`

`toggle_block_customer` ตั้งแค่ `customer.is_blocked = 1` ส่วน `find_sessions_to_close` หา session ที่ต้องตัดจาก `v.status != 'active'` อย่างเดียว ไม่ดู `is_blocked` ผลคือการระงับมีผลแค่กับการ login ครั้งถัดไป (FAS ตรวจ `is_blocked`) ลูกค้าที่ออนไลน์อยู่ใช้ต่อได้จนรหัสหมดอายุ (สูงสุด 24 ชม.)

**แก้:** ตอนระงับให้ `UPDATE voucher SET status='revoked' WHERE customer_id=%s AND status='active'` ใน transaction เดียวกันพร้อม audit (enforce รอบถัดไปจะตัดให้เอง ≤ 5 นาที) หรือเพิ่ม `OR c.is_blocked` ในคิวรีของ enforce และเพิ่ม cause `customer_blocked` ใน `TERMINATE_CAUSE_BY_STATUS`

> **✅ แก้แล้ว — commit `9969b02`** (ใช้แนวทางที่ 2: ตรวจ `is_blocked` ใน enforce)
>
> - `tools/enforce_voucher_expiry.py`: `find_sessions_to_close()` JOIN `customer` แล้วเลือก session ที่ `v.status != 'active' OR c.is_blocked` คืนสถานะ `blocked` ถ้า voucher ยัง active (ถ้า voucher ไม่ active อยู่แล้วใช้สาเหตุจาก voucher) และ map `blocked → customer_blocked` ใน `TERMINATE_CAUSE_BY_STATUS`
> - ไม่เปลี่ยน voucher เป็น `revoked` เพราะการระงับเป็นแบบสลับได้ — ยกเลิกการระงับแล้วลูกค้าใช้รหัสเดิมต่อได้เลย ไม่ต้องออกรหัสใหม่
> - หน้า Admin แจ้งว่าอุปกรณ์ที่ออนไลน์จะถูกตัดภายใน 5 นาที (รอบของ `cafe-enforce.timer` — แอป Admin รันเป็น `cafewifi` สั่ง `ndsctl deauth` เองไม่ได้)
> - เทสต์: รันคิวรีจริงบน sqlite ครอบกรณีถูกระงับ/ปกติ/หมดอายุ/ปิดแล้ว/pending และกรณีเข้าทั้งสองเงื่อนไข — fail กับโค้ดเดิม · ชุดทดสอบทั้งหมด **308 passed**
> - ยังไม่ได้ทดสอบบน MariaDB/Pi จริง

---

### R2-06 — Log หายทุกครั้งที่ restart/reboot cafe-logger [กลาง]

**ตำแหน่ง:** `app/logger/run_all.py` (สร้าง thread แบบ `daemon=True`), `app/logger/dns_collector.py:172`

1. เมื่อได้ SIGTERM `main()` return ทันที ส่วน collector threads เป็น daemon จึงถูกฆ่าตอน interpreter ปิด **บล็อก `finally: flush_buffer(...)` ใน `conn_collector.run_forever` ไม่ได้ทำงาน** record ที่ค้างใน buffer (สูงสุด 5 วินาที / 100–200 แถว) และในคิว `events` หายทุกครั้งที่ `systemctl restart`, อัปเดตระบบ หรือ reboot
2. `dns_collector` เริ่มด้วย `f.seek(0, 2)` (ข้ามไปท้ายไฟล์) บรรทัด DNS ที่ dnsmasq เขียนระหว่าง logger ดับ (รวมรอบ `RestartSec=10` หลัง crash) **ไม่ถูกอ่านเลย**

ทั้งสองข้อนี้ไม่ถูกนับใน telemetry `dropped` จึงไม่มีร่องรอยว่าหลักฐานขาด

**แก้:**

- ส่ง `stop_event` เข้าไปใน `run_forever` ของทั้งสองตัว ให้ออกจากลูปแล้ว flush เอง จากนั้น `main()` ค่อย `join(timeout=…)`
- บันทึก `(inode, offset)` ที่อ่านถึงลงไฟล์สถานะ (เช่นคู่กับ `collector-dns.json`) แล้วเริ่มอ่านต่อจากจุดนั้นเมื่อ inode ยังเป็นตัวเดิม
- บันทึก `log_gap` เมื่อ start ใหม่แล้วพบว่ามีช่วงที่ไม่ได้อ่าน

> **สถานะ: ✅ แก้แล้ว (`17b2641`)**
>
> - `run_all` ส่ง stop event เข้า collector ทั้งสองตัวแล้ว `join` (สูงสุด 20 วินาที) ก่อน return ถ้าตัวหนึ่งตาย จะสั่งให้อีกตัว flush ก่อนออกด้วย
> - `dns_collector` บันทึก `(inode, offset)` ลง `collector-dns.offset.json` เฉพาะเมื่อ buffer ว่าง (ทุกบรรทัดก่อนหน้าลง DB แล้ว) และอ่านต่อจากจุดนั้นเมื่อเริ่มใหม่ ถ้า inode เปลี่ยนหรือไฟล์ถูกตัดระหว่างดับ จะบันทึก `log_gap` ลง audit_log · ไม่แปลงบรรทัดที่ dnsmasq ยังเขียนไม่จบ · ถ้าดับหลัง INSERT แต่ก่อนบันทึกตำแหน่ง อาจอ่านซ้ำได้ไม่กี่แถว (เลือกซ้ำดีกว่าหาย)
> - `conn_collector` เมื่อหยุด จะปิด conntrack แล้วดูดเหตุการณ์ที่ค้างในท่อ/คิวมาเขียนให้หมด · เหตุการณ์ช่วงที่ logger ดับกู้ไม่ได้ (`conntrack -E` เห็นแค่เหตุการณ์สด) จึงบันทึก `log_gap` พร้อมเวลา heartbeat ล่าสุดของรอบก่อน
> - **พบเพิ่ม:** unit `cafe-logger` มี `ProtectSystem=strict` แต่ไม่มี `ReadWritePaths` จึงเขียนอะไรลง `LOG_DIR` ไม่ได้เลย รวมถึง `collector-*.json` ที่หน้า Admin อ่าน (ล้มเหลวแค่ warning) เพิ่ม `ReadWritePaths=${LOG_DIR}` และ `KillMode=mixed` (SIGTERM ไปที่ python ตัวเดียว กัน conntrack ตายก่อนจนดูเหมือน crash)
> - เทสต์ใหม่ `tests/test_logger_restart.py` 12 เคส — ชุดทดสอบทั้งหมด **332 passed** · ส่วนปิด conntrack ต้องใช้ root จึงยังไม่มีเทสต์อัตโนมัติ ต้องตรวจบน Pi

---

### R2-07 — Integrity check เจอปัญหาใดก็ตามแล้วไม่ลบ archive อีกเลย (ดิสก์เต็มในระยะยาว) [กลาง]

**ตำแหน่ง:** `app/logger/integrity.py:275-290`, `208-210`, `241-263`

- `main()` จะ `return 1` ก่อนถึง `prune_archives()` เมื่อ `verify_chain` เจอ issue ใดก็ได้ ปัญหาเดียวที่แก้ไม่ได้ (เช่นไฟล์เดียวที่ hash ไม่ตรงซึ่งต้องเก็บไว้เป็นหลักฐาน) จะ**หยุดการลบตามอายุของทุกไฟล์ถาวร**
- เกิด deadlock ได้: ถ้าการลบค้างกลางทาง (`set_deletion('pending')` สำเร็จ แต่ `unlink` หรือ `set_deletion('deleted')` ล้ม) รายการนั้นเป็น `pending_delete` ซึ่งนับเป็น issue → prune ไม่รัน และ prune เองก็ข้ามรายการที่ไม่ใช่ `active` → ไม่มีทางกลับไปทำให้เสร็จ

**แก้:** แยกประเภท issue — `pending_delete` ให้ prune รอบถัดไปทำต่อได้ (ถ้าไฟล์หายแล้วให้ตั้ง `deleted`, ถ้ายังอยู่และ hash ตรงให้ลบต่อ) ส่วน issue ของไฟล์หนึ่งไม่ควรบล็อกการลบไฟล์อื่นที่ hash ตรงและครบอายุ แค่รายงาน/audit และให้ exit code ไม่ใช่ 0 ต่อไป ร่วมกับ `check_disk` ที่มีอยู่แล้ว

> **สถานะ: ✅ แก้แล้ว (`47ba1d5`)**
>
> - `main()` ไม่ return ก่อนถึง prune แล้ว — ไฟล์ที่มี issue ซึ่งต้องเก็บเป็นหลักฐาน (`hash_mismatch`, `chain_broken`, `unexpected_file`, `invalid_filename`) ถูกส่งเป็น `hold` ให้ prune ข้ามเฉพาะไฟล์นั้น ไฟล์อื่นที่ครบอายุและ hash ตรงยังลบตามปกติ · exit code ยังเป็น 1 และบันทึก `integrity_failed` ลง audit_log ตามเดิม
> - `prune_archives` ทำรายการ `pending` ที่ค้างให้เสร็จ: ไฟล์หายแล้ว → ตั้ง `deleted` · ไฟล์ยังอยู่และ hash ตรง → ลบต่อ · hash ไม่ตรง → ไม่ลบ ค้าง `pending` ไว้ให้ตรวจ (ไม่บันทึก `raw_log_delete` ซ้ำ เพราะบันทึกไปแล้วก่อนตั้ง `pending`)
> - ไฟล์หนึ่งลบไม่สำเร็จ (เช่น `chattr -a` ใช้ไม่ได้, DB ล่มกลางทาง) ไม่หยุดทั้งรอบแล้ว รายการนั้นค้างเป็น `pending` ให้รอบถัดไปทำต่อ
> - `pending_delete`/`missing_file` ของรายการที่ prune ปิดได้ในรอบเดียวกันไม่ถูกฟ้องเป็น `integrity_failed` — deadlock เดิมจึงหายเองในรอบ 03:30 ถัดไปโดยไม่ต้องแก้ DB มือ
> - เทสต์ใหม่ 7 เคสใน `tests/test_logger.py` (6 เคสล้มกับโค้ดเดิม) — ชุดทดสอบทั้งหมด **339 passed**

---

### R2-08 — `authenticated_at` ช้ากว่าเวลาเปิดสิทธิ์จริง และลำดับการตรวจ timeout ใน reconcile [กลาง]

**ตำแหน่ง:** `tools/reconcile_pending.py:50-61, 92`

1. เวลาที่บันทึกเป็น `authenticated_at = NOW()` ตอน timer มาเจอ (ทุก 5 วินาที หรือนานกว่านั้นถ้า `ndsctl` ช้า) ไม่ใช่เวลาที่ openNDS เปิดสิทธิ์จริง ทั้งที่ `confirmed_since()` อ่าน `session_start` มาแล้ว DNS query ชุดแรกหลังเปิดสิทธิ์ (เบราว์เซอร์ไปหน้า `originurl` ทันที) จะมี `ts < authenticated_at` จึง**โยงหาลูกค้าไม่ได้** ใน `/logs` และ `retention_hold_until`
2. ในลูป ตรวจ `pending_until <= now` (หมดเวลา → deauth) **ก่อน** ตรวจว่า openNDS ยืนยันแล้วหรือยัง ถ้าลูกค้ากดตาม redirect ใกล้วินาทีที่ 180 openNDS เปิดสิทธิ์แล้ว แต่รอบ reconcile ถัดไปเห็นว่าหมดเวลาก่อน จึงตัดสิทธิ์ลูกค้าที่ login ถูกต้อง

**แก้:** ใช้ `datetime.fromtimestamp(session_start)` เป็น `authenticated_at` และสลับลำดับให้ตรวจการยืนยันก่อน แล้วค่อยตรวจ timeout เฉพาะรายการที่ยังไม่ยืนยัน

> **สถานะ: ✅ แก้แล้ว (`5c80836`)** — `confirmed_since()` เปลี่ยนเป็น `confirmed_at()` คืนเวลา `session_start` ของ openNDS แล้วบันทึกค่านั้นเป็น `authenticated_at` ลูปตรวจการยืนยันก่อน timeout เสมอ (ถ้าอ่าน `ndsctl json` ไม่ได้ ยังใช้ timeout ตามเดิม) มีเทสต์ขับ `run()` ด้วย cursor ปลอม ซึ่ง fail กับโค้ดเก่า — ชุดทดสอบทั้งหมด **310 passed**

---

### R2-09 — ฟอร์ม Admin ไม่มี CSRF token [กลาง]

**ตำแหน่ง:** `app/admin/templates/*.html` (ทุก `<form method="post">`), `app/admin/app.py`

ทุก POST ที่มีผล (ออกรหัส, ยกเลิกรหัส, ระงับ, ลบข้อมูล DSR, เปิดเลขบัตร, logout) ป้องกัน CSRF ด้วย `SESSION_COOKIE_SAMESITE="Lax"` เพียงชั้นเดียว ซึ่งกันกรณีทั่วไปได้ แต่ไม่ใช่มาตรการที่ผู้ตรวจงานความปลอดภัยยอมรับเป็นหลัก และไม่กันกรณีต้นทางอยู่ใน "site" เดียวกัน (เช่น หน้าอื่นบน host/IP เดียวกันที่ถูกฝังสคริปต์)

**แก้:** ใช้ Flask-WTF `CSRFProtect` หรือทำ token เองใน session แล้วใส่ hidden field ทุกฟอร์ม พร้อมเทสต์ว่า POST ที่ไม่มี token ได้ 400

> **✅ แก้แล้ว — commit `bc7aaec`**
>
> ทำ token เองแบบ synchronizer token (ไม่เพิ่ม dependency ใหม่ให้ต้องติดตั้งบน Pi): `csrf_token()` ใน `app/admin/app.py` สุ่ม token 32 ไบต์เก็บใน session แล้วส่งเข้า template ผ่าน context processor ส่วน `gate()` (before_request) ตรวจ **ทุก POST** รวม `/login` และ `/setup` (กัน login CSRF) ด้วย `secrets.compare_digest` รับจาก field `csrf_token` หรือ header `X-CSRF-Token` ไม่ผ่านได้ 400 พร้อมหน้า error ภาษาไทย และลง `audit_log` เป็น `csrf_reject` token ถูกสร้างใหม่ทุกครั้งที่ session ถูกล้าง (login/logout) จึงใช้ token ก่อน login ต่อไม่ได้
>
> ใส่ hidden field ครบ 10 ฟอร์มใน 7 template (ออกรหัส, ยกเลิกรหัส, ระงับ, ลบข้อมูล DSR, เปิดเลขบัตร, ตรวจ log 2 จุด, logout, login, setup) เทสต์เดิมที่ไม่ได้ทดสอบ CSRF ปิดด้วย `CSRF_ENABLED=False` ส่วนเทสต์ใหม่ท้าย `tests/test_setup_flow.py` (8 เคส) เปิดการตรวจจริง: ไม่มี/ผิด token ได้ 400 และไม่มีผล, token หมุนหลัง login, header ใช้ได้ และตรวจว่าทุก `<form method="post">` ใน template มี `csrf_token` (กันลืมเวลาเพิ่มฟอร์มใหม่) — ตอนเปิดการตรวจกับเทสต์เดิมทั้งหมด POST ไม่มี token fail 43 ข้อ ยืนยันว่าบังคับใช้จริง ชุดทดสอบรวม → **305 passed**

---

### R2-10 — ไฟล์ส่งออกหลักฐานไม่ระบุตัวบุคคล และเอกสารอ้างความสามารถที่ไม่มี [กลาง]

**ตำแหน่ง:** `tools/export_evidence.py`

- docstring บอกว่าใช้ `--natid 1234567890123` ได้ แต่ `argparse` **ไม่มีตัวเลือกนี้** (รันแล้ว error)
- CSV มีเฉพาะคอลัมน์ traffic ไม่มี voucher/customer/masked natid — ขัดกับที่ FIX_SUMMARY ข้อ R05 ระบุว่า export โยงผ่าน `portal_session` แล้ว (ที่ทำจริงคือหน้า `/logs` เท่านั้น)
- `--mac` ไม่แปลงเป็นตัวพิมพ์ใหญ่ ใส่ `aa:bb:…` จะได้ 0 แถวแบบเงียบ ๆ (DB เก็บเป็นตัวใหญ่)
- ไฟล์ส่งออกถูกเขียนด้วย umask ปริยาย (มักเป็น 0644) ใน `/var/log/cafe-wifi/exports` ทั้งที่เป็นข้อมูลจราจรจำนวนมาก

**แก้:** เพิ่ม `--natid` (หา `customer.id` ด้วย `natid_hash`, เลือก session ผ่าน voucher แล้ว export ตาม `mac + ip + ช่วงเวลา` ของแต่ละ session) เพิ่มคอลัมน์ `voucher_username`, `natid_masked` ด้วย `_MAPPING_JOIN` เดียวกับ `/logs` แปลง MAC เป็นตัวใหญ่ และ `chmod 0600` ไฟล์ผลลัพธ์ แล้วแก้ข้อความใน FIX_SUMMARY ให้ตรง

> **✅ แก้แล้ว — commit `93f8ef1`**
>
> - ย้าย JOIN โยง log → `portal_session` → voucher → customer ไปไว้ที่ `app/common/log_mapping.py` ใช้ร่วมกันทั้งหน้า `/logs` และ `export_evidence` (จับคู่ตัวบุคคลแบบเดียวกันเป๊ะ)
> - `--natid`: ตรวจ checksum → หา `customer.id` ด้วย `natid_hash` → หาคู่ `(mac, ip)` จาก session ของลูกค้า → คิวรี่ทีละคู่พร้อมกรอง `c.id` แถวที่เข้าได้หลาย session จะไม่ถูกเดาใส่ (ใช้ `--mac` ค้นต่อเอง) ใช้ `--mac` คู่กับ `--natid` ไม่ได้ ชื่อไฟล์/audit/manifest ใช้ `customer:<id>` + `natid_masked` ไม่มีเลขเต็ม
> - CSV ทั้ง conn/dns มีคอลัมน์ `voucher_username`, `natid_masked` ทุกโหมด
> - `--mac` แปลงเป็นตัวใหญ่ (รับ `-` คั่นได้) และปฏิเสธรูปแบบผิดแทนการคืน 0 แถว
> - ไฟล์ CSV และ manifest สร้างด้วยสิทธิ์ `0600` ตั้งแต่ตอนเปิดไฟล์ โฟลเดอร์ใหม่ `0700`
> - แก้ข้อความ R05 ใน FIX_SUMMARY ให้ตรงความจริง · เพิ่มเทสต์ 10 ข้อใน `tests/test_purge_and_export.py`

---

### R2-L01 — FAS ปล่อยผ่านเมื่อหา ARP ไม่เจอ และ payload ของ openNDS แก้ไขได้บางส่วน [ต่ำ]

**ตำแหน่ง:** `app/fas/app.py` (POST `/login`), `app/fas/opennds_proto.py`

เมื่อ `resolve_mac(real_ip)` ได้ `None` โค้ดยอมรับ `ctx.clientmac` จาก payload ตรง ๆ payload ของ openNDS เข้ารหัสด้วย AES-CBC ที่ไม่มี MAC/HMAC จึงมีทางดัดแปลงบิตได้ในทางทฤษฎี (ต้องรู้ตำแหน่ง plaintext) ผลที่แย่ที่สุดคือบันทึก session ด้วย MAC ของคนอื่น ซึ่ง reconcile จะไม่ยืนยันแล้ว deauth MAC นั้นเมื่อหมดเวลา (DoS/ข้อมูลเพี้ยน) **ไม่ใช่การข้ามการยืนยันตัวตน** เพราะ openNDS เปิดสิทธิ์ตาม `hid`

**แก้:** ถ้า ARP ไม่เจอ ให้ลองกระตุ้น ARP (เช่นส่ง ping 1 ครั้งไปที่ `real_ip`) แล้วอ่านใหม่ ถ้ายังไม่เจอให้ปฏิเสธพร้อมข้อความให้ลองอีกครั้ง

**สถานะ 1 ต.ค. 2026:** แก้โค้ดแล้ว — ping `real_ip` หนึ่งครั้งเมื่อ ARP ว่าง แล้วอ่านซ้ำ; หากยังไม่พบหรือ MAC ไม่ตรงจะไม่สร้าง session ใช้ MAC ที่ยืนยันจาก ARP ในขั้นตอน login เทสต์อัตโนมัติผ่าน รอทดสอบบน Pi

### R2-L02 — Login ซ้ำ (reauth) ไม่บวกยอดเข้า `used_mb` [ต่ำ]

**ตำแหน่ง:** `tools/reconcile_pending.py:80-88`

ตอนปิด session เก่าด้วยเหตุ `reauth` บันทึก `bytes_out/bytes_in` แต่ไม่บวกเข้า `voucher.used_mb` เหมือนที่ `close_session()` ใน enforce ทำ ลูกค้าที่ต่อ Wi-Fi ใหม่บ่อย ๆ จะใช้เกินโควตาได้ ควรเรียก `close_session()` ตัวเดียวกัน

`sum_session_traffic_bytes` ยังนับจาก `ts >= started_at` โดยไม่มีขอบบน (`ended_at`) และ `find_quota_exceeded_vouchers` นับ session ที่ยัง `pending` ด้วย ทำให้ยอดนับซ้อนกันได้ในบางลำดับเหตุการณ์

**สถานะ 30 ก.ย. 2026:** แก้แล้ว — reauth ปิด session ผ่าน `close_session()` และบวกยอดให้ voucher ของ session เก่า; ใช้ `authenticated_at` ถึง `ended_at` เป็นช่วงนับและไม่นับ session `pending` ในโควตา เทสต์อัตโนมัติครอบกรณี reauth และรอยต่อเวลาแล้ว ส่วน conntrack ที่ส่ง `DESTROY` หลังปิด session ยังอาจไม่ถูกนับในยอดนี้

### R2-L03 — Session ของพนักงานไม่ตรวจสถานะบัญชีซ้ำ [ต่ำ]

**ตำแหน่ง:** `app/admin/app.py:108-123`

`login_required`/`admin_required` เชื่อค่าใน cookie session ตลอด 8 ชม. ถ้าปิดบัญชี (`is_active=0`) หรือลดสิทธิ์จาก admin เป็น staff ผู้ใช้ที่ login ค้างไว้ยังทำงานได้ต่อจนหมดอายุ ควรโหลด `staff` จาก DB ใน `before_request` แล้ว `session.clear()` ถ้าบัญชีถูกปิดหรือ role เปลี่ยน

### R2-L04 — Backup DB ใช้ไม่ได้ถ้ากุญแจหายไปพร้อม SD card [ต่ำ · ด้านปฏิบัติการ]

**ตำแหน่ง:** `tools/backup_db.py`

backup มี `natid_enc` ที่ถอดได้ด้วย `NATID_DEK` ใน `secrets.env` เท่านั้น ถ้า SD card พังและไม่มีสำเนา `secrets.env` นอกเครื่อง backup จะกู้ข้อมูลตัวตนไม่ได้ (ขัด ม.26) ตัวติดตั้งเตือนให้สำรองแล้ว แต่ควรเขียนขั้นตอนเก็บกุญแจนอกเครื่อง (แยกจาก backup) ใน runbook และในเล่ม ไฟล์ `.tmp` ระหว่าง dump ยังถูกสร้างด้วย umask ปริยายก่อน `chmod 0600` ควรตั้ง `os.umask(0o077)` ก่อนเปิดไฟล์

### R2-L05 — Connection Log เก็บทราฟฟิกของ Pi เองด้วย [ต่ำ · ประสิทธิภาพ]

**ตำแหน่ง:** `app/logger/conn_collector.py:271`

คำสั่ง `conntrack -E` ไม่ได้กรอง source จึงเก็บทราฟฟิกของ Pi เอง (NTP, apt, DNS upstream ของ dnsmasq, การเชื่อมต่อ SSH/Admin) ปนกับของลูกค้า ทำให้ตารางโตโดยไม่จำเป็นและเพิ่มโอกาสเกิด ENOBUFS ควรกรองเฉพาะ `src` ที่อยู่ใน `CLIENT_NET` ใน `parse_conntrack_line` (วิธีที่แน่นอนที่สุด) หรือใช้ตัวกรองของ conntrack เอง (`--orig-src` ร่วมกับ `--mask-src`) ถ้าเวอร์ชันบน Pi รองรับในโหมด `-E` ซึ่งต้องตรวจก่อน

> **✅ แก้โค้ดแล้ว — commit นี้ / รอทดสอบบน Pi**: logger กรอง original source ก่อนส่งทั้ง `NEW` และ `DESTROY` เข้า tracker รวมถึงช่วงระบายคิวตอนหยุด โดยใช้ `CLIENT_CIDR` จาก `secrets.env` และตัด IP gateway ของ Pi ออกด้วย การกรองใน Python ลดงานของ tracker และแถว DB แต่ไม่ได้ลด event ที่ส่งผ่าน netlink จึงยังต้องเฝ้า ENOBUFS และตรวจความเข้ากันได้ของตัวกรองฝั่ง `conntrack -E` บน Pi

### R2-L06 — ต้องตรวจบน Pi: `compress/delaycompress` ชนกับ `chattr +a` หรือไม่ [ต่ำ · ยังไม่ยืนยัน]

**ตำแหน่ง:** `install.sh` ฟังก์ชัน `configure_logrotate`

`postrotate` ใส่ `chattr +a` ให้ `archive/*.log-*` ทุกไฟล์ ถ้า logrotate บีบอัดไฟล์รอบก่อน (delaycompress) **หลัง** postrotate จะลบไฟล์ต้นฉบับไม่ได้ (unlink ไฟล์ +a ไม่ได้แม้เป็น root) ลำดับจริงขึ้นกับเวอร์ชัน logrotate จึงต้องตรวจบน Pi ด้วย `logrotate -d`/`-f` แล้วดู `lsattr archive/` และ log ของ logrotate ว่ามี error "failed to compress" หรือไม่ ถ้าชนจริงให้ย้าย `chattr +a` ไปทำใน `cafe-maintenance` หลัง seal แทน

### ข้อสังเกตเล็กน้อย

- `docker-compose.yaml` รัน gunicorn `--workers 2` แต่ production ใช้ `--workers 1 --threads 4` rate limit แบบเก็บในหน่วยความจำจึงทำงานต่างกัน ผลทดสอบ rate limit ใน Docker ไม่แทน production ได้
- `_attempts` (rate limit) ทั้งใน FAS และ Admin โตไม่จำกัดตามจำนวน MAC/IP ที่เคยเห็น (หน่วยความจำรั่วช้า ๆ บนเครื่องที่รันนาน)
- `bypass_detector` ใช้ `net.hosts()` ของวง uplink ถ้าวงเป็น /16 จะยิง ping ~65,000 ครั้งทุกนาที ควรจำกัดขนาดวงหรือปฏิเสธวงที่ใหญ่กว่า /23
- memory `cafe-wifi-source-of-truth.md` ล้าสมัย (บอกว่าโค้ดอยู่ในทาร์บอลและไม่มี git) ซึ่งไม่ตรงกับสภาพปัจจุบัน

---

## 4. ข้อความในเล่มที่ต้องปรับให้ตรงกับโค้ด

| เรื่อง | ที่โค้ด/เอกสารอ้าง | ความจริง | ข้อเสนอ |
|---|---|---|---|
| กันลูกค้าโจมตีกันเอง (วัตถุประสงค์ 1.2.4) | คอมเมนต์เดิมใน nftables อ้างว่ากฎกัน sniffing / ARP spoof ภายในวงเดียวกัน | ลูกค้าในวงเดียวกันคุยกันตรงที่ L2 โดยไม่ผ่าน Pi; ผลที่ยืนยัน client isolation แล้วเป็นของ ER706W ส่วน Aruba ยังต้องทดสอบ | ✅ แก้คอมเมนต์ D9 และข้อความส่งต่อเล่มแล้ว; กฎบน Pi กันได้เฉพาะทราฟฟิกที่ผ่าน Pi |
| Connection Log (ขอบเขต 1.3.4) | เก็บ "ข้อมูลการเชื่อมต่อ" | `ts` คือเวลาจบ ไม่ใช่เวลาเริ่ม; โค้ด R2-02 เพิ่ม `started_at` และผูก MAC ตอน `NEW` แล้ว | ✅ เตรียมข้อความส่งต่อเล่มเรื่องเวลาเริ่ม/จบและกรณี `mac=NULL` แล้ว; รอผลตรวจ conntrack บน Pi |
| DNS Log | เก็บ DNS query ของลูกค้า | DoT พอร์ต 853 และ DoH ไม่ผ่าน dnsmasq | ✅ เพิ่มกฎ drop TCP/UDP 853 สำหรับทราฟฟิกผ่าน Pi และข้อความข้อจำกัดแล้ว; รอทดสอบ DoT/Android บน Pi; DoH ยังไม่ถูกบล็อก |

ข้อความพร้อมนำไปใส่เล่มอยู่ที่ [docs/thesis-text-round2-topic4.md](../docs/thesis-text-round2-topic4.md)

---

## 5. ลำดับการแก้ที่แนะนำ

| ลำดับ | ข้อ | เหตุผล | ขนาดงาน | สถานะ |
|---|---|---|---|---|
| 1 | R2-01 | ลูกค้าเจอได้ในการสาธิต/ใช้งานจริง แก้ไม่กี่บรรทัด | เล็ก | ✅ `6c1267c` |
| 2 | R2-03 | ปิดช่องเข้า SSH/Admin จากฝั่งลูกค้า | เล็ก | ⚠️ IPv6 แก้แล้ว `6247ff4` / ช่องทาง uplink ยังไม่แก้ |
| 3 | R2-04, R2-05 | แก้ง่าย ตรงกับฟังก์ชันที่จะสาธิต | เล็ก | R2-04 ✅ `fd604a5` / R2-05 ✅ `9969b02` |
| 4 | R2-02 | กระทบความถูกต้องของหลักฐานตามวัตถุประสงค์ 1.2.3 มากที่สุด | ใหญ่ (ต้องมี migration และทดสอบบน Pi) | ✅ `4f232c3` (รอตรวจบน Pi) |
| 5 | R2-06, R2-08 | ลดช่องว่างของ log | กลาง | R2-06 ✅ `17b2641` / R2-08 ✅ `5c80836` |
| 6 | R2-07, R2-09, R2-10 | ความทนทานระยะยาวและความครบของหลักฐาน | กลาง | R2-09 ✅ `bc7aaec` / R2-10 ✅ `93f8ef1` / R2-07 ⏳ |
| 7 | R2-L01 ถึง R2-L06 | ปรับปรุงตามเวลาที่มี | เล็ก–กลาง | R2-L01 ✅ (รอ Pi) / R2-L02, R2-L03, R2-L05 ✅ / R2-L04, R2-L06 ⏳ |

ทุกข้อที่แก้ควรเพิ่มเทสต์อัตโนมัติคู่กัน โดยเฉพาะ R2-01 (claim ต้องไม่ค้าง), R2-02 (MAC ต้องมาจากตอนเปิด connection), R2-04 (`next=//…` ต้องไม่ redirect ออกนอก) และ R2-05 (ระงับแล้วต้องถูกตัด)

## 6. รายการตรวจบน Raspberry Pi หลังแก้

> ข้อ 1–5 โค้ดแก้แล้ว (ข้อ 3 เฉพาะส่วน IPv6) รอทดสอบบน Pi ส่วนข้อ 6 ยังรอแก้โค้ดก่อน
> สำหรับ R2-02 ให้ตรวจเพิ่มด้วยว่า `conntrack -E -e NEW,DESTROY -o id` บน Pi มี `id=` ทั้งสองแบบ และมี `delta-time=` หลังเปิด `nf_conntrack_timestamp` และดู log ของ cafe-logger ว่าไม่มี ENOBUFS เพิ่มขึ้น

1. **R2-01:** ใช้รหัส `max_devices=1` กับเครื่องที่ 2 → ได้ 403 → ตรวจ `SELECT * FROM pending_mac_claim` ต้องไม่มีแถวของเครื่องที่ 2 → ออกรหัสใหม่ เครื่องที่ 2 ต้อง login ได้
2. **R2-02:** เปิด connection ยาวจากเครื่อง A แล้วตัด Wi-Fi ของ A → ให้เครื่อง B ได้ IP เดิม (ลด lease time ชั่วคราว) → รอ DESTROY ของ A → ตรวจว่าแถวใน `conn_log` ไม่ถูกโยงไปหา B ในหน้า `/logs`
3. **R2-03:** จากเครื่องลูกค้า `ssh -6 <user>@fe80::<pi>%wlan0` และตั้ง IP เองในวง uplink แล้วลอง SSH/Admin ต้องไม่สำเร็จ
4. **R2-05:** ระงับลูกค้าที่ออนไลน์อยู่ → ภายใน 5 นาทีต้องออกเน็ตไม่ได้ และ `terminate_cause` ถูกต้อง
5. **R2-06:** รัน `install.sh` ใหม่ก่อน (unit เปลี่ยน) → `systemctl restart cafe-logger` ระหว่างมีทราฟฟิกและ DNS query ต่อเนื่อง → เทียบจำนวนแถวกับตัวอ้างอิง (เช่น tcpdump) ว่า DNS ไม่มีช่วงหาย และ `audit_log` มีแถว `log_gap` ของ conn_log ตรงช่วงที่ดับ · ตรวจว่ามี `collector-conn.json`, `collector-dns.json`, `collector-dns.offset.json` ใน `/var/log/cafe-wifi`
6. **R2-L06:** `logrotate -f /etc/logrotate.d/cafe-wifi` สองรอบติดกัน → ตรวจ `lsattr`, ไฟล์ `.gz` และ error ของ logrotate

บันทึกผลลงใน `docs/hardware-test-log.md` ตามรูปแบบเดิม
