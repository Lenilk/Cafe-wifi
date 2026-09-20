---
name: pi-dhcp-and-portal-milestone
description: "2026-09-16 breakthrough: real DHCP + captive portal + login now work end-to-end on real Pi hardware. Three real bugs fixed (N17 nftables chicken-and-egg, N18 openNDS heartbeat, N19 double-encoded redirect). Supersedes the old 'broadcast UDP is broken on this Pi' theory, which rested on invalid tests."
metadata:
  type: project
---

**สถานะ (2026-09-16): ปลดล็อกได้แล้ว — ลูกค้าจริงเชื่อมต่อและ login ได้ครบวงจร**

## บั๊กจริง 3 ตัวที่แก้วันนี้ (commit N17, N18, N19)

**N17 — ไก่กับไข่ใน nftables (ตัวที่บล็อกทั้งโปรเจกต์มาตลอด)**
`chain input` มี `policy drop` และอนุญาต DHCP เฉพาะ `ip saddr $CLIENT_NET udp dport 67`
แต่ลูกค้าที่ยังไม่มี IP ต้องส่ง DHCPDISCOVER จาก `0.0.0.0` ตาม RFC 2131 เสมอ จึงตกไปโดน
policy drop ทุกครั้ง → **ลูกค้าจริงขอ IP ไม่ได้เลยสักคน** แก้ด้วย `udp sport 68 udp dport 67 accept`

**N18 — openNDS heartbeat ค้าง** `check_heartbeat()` อ่าน `/tmp/ndscids/heartbeat` ถ้ายังไม่
หมดอายุจะ exit 1 พร้อม "openNDS is already running" ไฟล์ค้างทุกครั้งที่หยุดไม่สะอาด
(เคยวินิจฉัยผิดว่าเป็น `/tmp/ndsctl.lock`) แก้ด้วย systemd drop-in ที่ลบ heartbeat ก่อนสตาร์ท
เมื่อไม่มี process จริง — ใช้ drop-in เพราะ `make install` ของ openNDS ทับไฟล์ unit ทุกครั้ง

**N19 — double-encoding ทำให้ลูกค้าเห็น 404 หลัง login สำเร็จ** openNDS ส่ง `originurl` มา
แบบ percent-encoded อยู่แล้ว แต่เรา `quote()` ซ้ำ → openNDS ถอดกลับชั้นเดียวได้
`http%3a%2f%2f...` ซึ่งไม่มี `://` → เบราว์เซอร์ตีเป็น path สัมพัทธ์ ต่อท้าย `/opennds_auth/`
→ 404 แก้ด้วย `unquote()` ก่อนเสมอ

## แก้ความเข้าใจผิดครั้งใหญ่
บันทึกเดิมสรุปว่า "broadcast UDP ไม่ถึง socket เลยบนเครื่องนี้" — **ผิด** หลักฐานที่ใช้สรุป
เป็นเทสต์ที่ใช้ตัดสินไม่ได้ (source IP ไม่ routable → `rp_filter` drop อย่างถูกต้อง) ความจริงคือ
firewall ของเราเองบล็อก DHCP (N17) วันนี้พิสูจน์แล้วว่า broadcast UDP เข้า socket ได้ปกติทั้ง
`eth0` และ `wlan0`

**กฎที่ช่วยไว้ได้จริงและต้องใช้ตลอด: ผลลบของการทดสอบเครือข่ายต้องมี `tcpdump` คู่ขนานยืนยันเสมอ**
วันนี้เกือบสรุปผิดซ้ำตอน socket timeout แต่ tcpdump เผยว่าแพ็กเก็ตไม่เคยมาถึง (สวิตช์ยังไม่ตั้งค่า)

## ผลทดสอบที่ผ่านแล้ว (ของจริงทั้งหมด ไม่มี static IP/lease ปลอมแล้ว)
- ✅ DHCP จริง: โน้ตบุ๊คได้ `10.10.0.179` จาก Pi (`PrefixOrigin=Dhcp`) lease อยู่ในไฟล์จริง
- ✅ captive portal เด้ง: `307 → http://10.10.0.1:8080/login?fas=..&iv=..`
- ✅ login ด้วย voucher: `Authenticating 10.10.0.179` ใน log openNDS
- ✅ redirect หลัง login: `302 → /opennds_auth/?tok=..&redir=..` → `307 → http://neverssl.com/`
  (กลับไปเว็บเดิมของลูกค้าถูกต้อง ไม่ 404 แล้ว)

## รอบบ่าย 2026-09-16 — เจอเพิ่มอีก 3 บั๊ก (N20, N21, N22)

**N20 — ตัวตรวจจับ bypass เขียนแถวซ้ำทุกนาที** เจอ `bypass_alert` 239 แถวใน 2 ชม. จากอุปกรณ์
เดิม 9 เครื่องในวง uplink ของแล็บ = 12,960 แถว/วัน ถมทั้ง `bypass_alert` และ `audit_log`
(ซึ่งเป็นหลักฐานตามกฎหมาย) แก้ด้วย cooldown ต่อคู่ (ip, mac) ค่าเริ่มต้น 60 นาที ผ่าน
`BYPASS_ALERT_COOLDOWN_MIN` — cooldown กันแค่การเขียนซ้ำ ไม่ใช่การตรวจจับ

**N21 — ตรวจพบ log ถูกแก้ย้อนหลังแล้วไม่มีหลักฐานในฐานข้อมูล** เดิม `logger/integrity.py`
log ERROR ลงไฟล์อย่างเดียว ซึ่งคนร้ายที่แก้ไฟล์ log ได้ก็ลบทิ้งได้ และ `cafe-maintenance.service`
ใช้ `ExecStart=-` ทุกบรรทัด exit 1 จึงถูกกลืน แก้ด้วยการเขียน `audit_log` action=`integrity_failed`

**N22 — เพิกถอน/หมดอายุ voucher แล้วตัดลูกค้าออกไม่ได้จริง (ตัวร้ายแรงที่สุดของวัน)**
ในโค้ดเขียนเตือนตัวเองไว้ว่า `ndsctl deauth` "ยังไม่เคยทดสอบกับ openNDS จริง" พอทดสอบก็พบว่า
**ไม่เคยทำงานเลยสักครั้ง** DB บันทึกว่าปิด session แล้วแต่ลูกค้ายังออกเน็ตได้ พังซ้อน 4 ชั้น:
1. `cafe-enforce.service` รันเป็น `cafewifi` → อ่าน `/etc/config/opennds` (0640 root:root) ไม่ได้
2. `PrivateTmp=yes` → มองไม่เห็น `/tmp/ndsctl.sock` (และ `NoNewPrivileges` ปิดทาง sudo)
3. `ProtectSystem=strict` ทำให้ `/tmp` เป็น read-only → `connect()` unix socket ไม่ได้
   (แก้ด้วย `ReadWritePaths=/tmp` ยังคง strict ไว้)
4. **openNDS เทียบ MAC แบบ case-sensitive และใช้ตัวพิมพ์เล็กเสมอ** แต่ DB เก็บตัวพิมพ์ใหญ่
   → `Client C8:A3:... not found.` ทุกครั้ง
แก้เพิ่ม: ถ้า deauth ล้มเหลว **ห้ามปิด session** ไม่งั้นรอบหน้ามองไม่เห็นแถวนั้นอีกเลย
(คิวรีหาเฉพาะ `ended_at IS NULL`) ลูกค้าจะใช้เน็ตต่อได้ตลอดไปโดยไม่มีการลองตัดซ้ำ

**บทเรียน:** คอมเมนต์ 🔶 "ยังไม่เคยทดสอบบนฮาร์ดแวร์จริง" ในโค้ดคือแผนที่ขุมทรัพย์ — ทุกจุดที่
เขียนไว้แบบนั้นควรถูกทดสอบก่อนส่งงาน เพราะ N19 และ N22 มาจากคอมเมนต์แบบนี้ทั้งคู่

## ผลทดสอบที่ผ่านแล้วทั้งหมด (ของจริงบนฮาร์ดแวร์)
- ✅ DHCP จริง / captive portal / login ด้วย voucher / redirect กลับหน้าเดิม
- ✅ ลูกค้าที่ login แล้วออกเน็ตได้ (HTTP 200, HTTPS 200)
- ✅ ลูกค้าที่ยังไม่ login ถูกบล็อกจริง: HTTP → 307 เข้า portal, HTTPS → timeout,
  ping → ถูก reject ตัวนับ `ndsNET reject` เพิ่มจริง
- ✅ hash chain: `logrotate -f` → ผนึก 10 ไฟล์ สาย `prev_sha256` ต่อกันถูก ไฟล์ที่หมุนแล้ว
  มีแฟล็ก append-only (`chattr +a`) แกล้งแก้แล้วจับได้ + เขียน `audit_log`
- ✅ backup DB, purge, disk check, บังคับ voucher หมดอายุ/เพิกถอน (ตัดคนออกจริง)

## ยังไม่ได้ทดสอบ / ค้างอยู่

## 2026-09-19 — ทดสอบไฟดับ (T15) ผ่าน + N23 นาฬิกา

**T15 — บริการกลับมาครบ แต่ลูกค้าขอ IP ไม่ได้ (แก้แล้ว ดูข้างล่าง):** Pi ถูกปิดไว้ตั้งแต่ 16 ก.ย. (17-18 ไม่ได้มาแล็บ) เปิดเครื่องใหม่แล้วบริการ 10 ตัว + timer
3 ตัวกลับมาเองครบ ไม่มีตัวไหน failed · openNDS วน restart 15 รอบ (ทุก ~25 วิ) เพราะ `eth0` ไม่มี
สัญญาณสายจนวินาทีที่ 401 (ช่วงที่กำลังตั้งสวิตช์) แล้ว**ขึ้นเองภายใน 3 วิหลังสายขึ้น** — ถูกต้อง ไม่ใช่
บั๊ก (`wait_for_interface` ใน libopennds.sh รอ macvlan `state UP` แค่ 10 วิ ซึ่ง macvlan จะ UP ได้
ก็ต่อเมื่อ eth0 มี carrier) · drop-in heartbeat (N18) ทำงานจริง

**N23 — ห้ามปล่อยลูกค้าออกเน็ตก่อนนาฬิกา sync:** Pi 4 ไม่มี RTC บูตมานาฬิกาผิด ~3 วัน (เริ่มที่
16 ก.ย. 14:20:33 ทุกครั้ง เพราะ `/var/lib/systemd/timesync/clock` ไม่เคยถูกอัปเดต — เครื่องใช้ chrony
ไม่ใช่ timesyncd) · เดิม openNDS พร้อมก่อน chrony sync ~106 วิ = log ลูกค้าจะติดวันที่ผิดปนกับข้อมูล
จริง · แก้: เปิด `chrony-wait.service` + openNDS (drop-in `cafe-wifi-time-sync.conf`) และ cafe-logger
`After/Wants=time-sync.target` · ทดสอบรีบูตจริง 3 แบบ: ปกติ (ช้าลง ~10 วิ), NTP ไม่มา (รอสูงสุด 180 วิ
แล้วเปิดให้ใช้), chronyd พัง (เปิดทันที) — ร้านไม่ล่มทุกกรณี · ข้อจำกัด: สองกรณีหลังนาฬิกายังผิดตอน
เปิดร้าน ทางแก้ถาวร = RTC DS3231 · `conn_log` id 1635 ติดเวลาผิดจากการทดสอบ (SSH ของผู้ทดสอบ)
ไม่ได้ลบ
**⚠️ แก้คำตัดสิน T15 (เจอบ่ายวันเดียวกันตอนย้ายไป Aruba):** รีบูตแล้วลูกค้า**ขอ DHCP ไม่ได้เลย**
เพราะกฎ N17 (`udp sport 68 udp dport 67 accept`) เมื่อ 16 ก.ย. ถูกเพิ่มแค่ในไฟร์วอลล์ที่รันอยู่
(`nft insert`) + แก้ install.sh แต่**ไม่เคยเขียนลง `/etc/nftables.conf`** (ไฟล์นั้นมาจากการติดตั้ง
16 ก.ย. 14:23 ก่อนเจอบั๊ก) รีบูตแล้วกฎหาย แก้แล้ว: เพิ่มบรรทัดในไฟล์ (สำรองเดิมไว้ที่
`/root/nftables.conf.pre-n17-persist`) + รีบูตพิสูจน์ซ้ำ → ได้ lease + portal 307 ✅ T15 ผ่านจริงแล้ว
**บทเรียน 2 ข้อ:** (1) แก้บนเครื่องจริงแบบ live ต้องเขียนลงไฟล์ที่โหลดตอนบูตด้วยเสมอ ไม่ใช่แค่แก้
install.sh (2) ทดสอบรีบูตต้องเช็ค**การใช้งานจริง** (ขอ IP + portal) ไม่ใช่แค่ `systemctl is-active`
**ควรรัน install.sh ซ้ำบน Pi ก่อนเดโม** เพื่อให้เครื่องตรงกับ repo 100% และจับ drift แบบนี้ตัวอื่น

**บทเรียนการตั้งเทสต์:** chrony **ไม่รับคอมเมนต์ท้ายบรรทัด** (`server x iburst #...` → Fatal parse
error, chronyd ไม่ขึ้น) — ตรวจ config ด้วย `chronyd -p -f <file>` ก่อนรีบูตทุกครั้ง

## 2026-09-19 — T13 มือถือจริงผ่าน AP ✅
Redmi Note 14 5G ต่อ SSID `Cafe-Guest` (AP-515 บน Aruba 6100 พอร์ต 1/1/8 PoE) → ได้ `10.10.0.224` จาก Pi
โดยตรง (Pi เห็น MAC มือถือเอง = AP เป็น Network assigned ถูกต้อง ไม่ NAT) → portal เด้งเองด้วย CPD ของ
Android (`cpd_can`, Xiaomi probe `www.google.cn`) → login ด้วย voucher `CAFE-CFK34` (voucher id 2) →
Authenticated → ใช้แอปได้ (Facebook ฯลฯ) · log ครบ: `conn_log` 425 แถว / 84 ปลายทาง, `dns_log` 630 แถว
พร้อม MAC, `portal_session` ผูก voucher+MAC+IP
**ข้อสังเกต:** MAC มือถือเป็น MAC สุ่มของ Android (`42:...` locally administered) คงที่ต่อ SSID ·
login ครั้งเดียวได้ `portal_session` 2 แถวห่างกัน 2 วิ (id 6 ปิดด้วย `reauth`, id 7 ใช้งานจริง) +
`login_ok` 2 ครั้ง — POST ซ้ำจาก webview ของ CPD หรือกดซ้ำ ยังไม่ได้ไล่สาเหตุ ไม่กระทบความถูกต้อง
ของ log แต่เป็นแถวขยะ · AP เอง (`10.10.0.142`) เป็นลูกค้า preauth ของ openNDS ด้วย (ออกเน็ตเองไม่ได้)
**แอดมิน:** ผู้ใช้ `admin` · ลืมรหัส → `sudo bash -c 'set -a; . /etc/cafe-wifi/secrets.env; cd
/opt/cafe-wifi && PYTHONPATH=/opt/cafe-wifi venv/bin/python -m tools.reset_admin admin'` (docstring ใน
reset_admin.py บอก `sudo -E` ซึ่งใช้ไม่ได้ เพราะ env ของ ras ไม่มี DB_PASS) · โดนล็อก 10 นาที → ตัวนับอยู่ใน
หน่วยความจำ `systemctl restart cafe-admin` ล้างได้

**แท็บเล็ต Samsung Tab A9** (Android, MAC สุ่ม `d2:c1:...`) ใช้ voucher เดียวกันได้ `10.10.0.170` →
Authenticated · session แถวเดียว (ที่มือถือได้ 2 แถวน่าจะเป็นการกดซ้ำ/เฉพาะ Xiaomi) · **ลิมิตเครื่อง ✅**
voucher `max_devices=2` ครบแล้ว เครื่องที่ 3 (โน้ตบุ๊ค) ถูกปฏิเสธพร้อมข้อความชัดเจน ไม่มี session/device
ใหม่ และ audit บันทึก `login_fail reason=device_limit_exceeded`
**Wi-Fi ของ Pi หลุดเอง 15:24** — handshake กับ `NetworkLab` (5 GHz 5200 MHz) หมดเวลา reason=15 แต่
wpa_supplicant/NM เข้าใจว่ารหัสผิด → NM ขอ secret ใหม่ ไม่มี agent (headless) → เลิกลองถาวร สัญญาณ
-31 dBm จึงไม่ใช่สัญญาณอ่อน ยังไม่รู้ว่า AP-515 รบกวนหรือไม่ · กู้ด้วยการตั้ง Ethernet 5 ของโน้ตบุ๊ค
เป็น static `172.20.18.129/24` (ไม่ใส่ gateway) แล้ว SSH ไป `172.20.18.128` (ไฟร์วอลล์ปิด 22 เฉพาะ
CLIENT_NET) → `nmcli connection up netplan-wlan0-NetworkLab` + ตัวเฝ้า transient `lab-wifi-watchdog`
(systemd-run ทุก 60 วิ หายเองตอนรีบูต) · `pi.py` รับ `PI_HOST=` เพื่อสลับเส้นทาง SSH

## 2026-09-19 บ่าย — AP ช่องชน + รัน install.sh ทับ (N24, N25, N26)
**Wi-Fi ของ Pi หลุด = AP-515 แย่งคลื่น:** แล็บ `NetworkLab` 5 GHz ช่อง 40 ที่ 80 MHz (กิน 36-48) ·
AP-515 เริ่มที่ช่อง 36 (Aruba ตั้ง 80 MHz เป็นค่าเริ่มต้น) → handshake หมดเวลาเฉพาะย่าน 5 GHz หลังเสียบ
AP · แก้: AP Configuration → Access Points → Edit → Radio → 5 GHz **Administrator assigned ช่อง 149,
15.0 dBm** (ต้องกรอก Transmit power ด้วย ไม่งั้นเซฟไม่ได้) → **ไม่หลุดอีกเลย** · Pi สแกนช่อง 149 ไม่เห็น
(เฟิร์มแวร์ Broadcom) แต่หน้า AP ยืนยันว่าอยู่ 149 จริง · AP เปิด OWE transition (`_owetm_...`) ·
นาฬิกา AP ผิดเพราะ openNDS บล็อก AP (preauth) ออก NTP — ร้านจริงควร trust MAC ของ AP
**รัน install.sh ทับ (ครั้งแรกที่เคยทำ):** สำรองที่ `/root/pre-reinstall-20260919/` (DB + /etc) ·
sync ทั้ง repo ด้วย `git archive HEAD` แทนการ copy ทีละไฟล์ · คำสั่ง `sudo ./install.sh -y --nic eth0
--uplink-cidr 172.20.18.128/24 --uplink-gw 172.20.18.1` · **ต้องยกเลิก dead-man switch ภายใน 5 นาที**
(`systemctl stop cafe-wifi-nft-failsafe.timer`) ไม่งั้นไฟร์วอลล์ถูกล้าง · เจอ 2 บั๊กที่ทำให้รันทับไม่ได้ =
**N24** (preflight FAIL เพราะพอร์ตของบริการเราเอง + `opennds -v` คืน exit 1 เสมอใต้ pipefail — บั๊กใน
โค้ด N16 ของผมเอง) · หลังแก้ รันทับ 2 รอบ ข้อมูลครบ เครื่องตรง repo งานค้าง debuglevel/log-dhcp หายเอง
**N25:** logrotate `delaycompress` บีบอัดไฟล์ที่ผนึกแล้วเป็น `.gz` → ตัวตรวจฟ้อง missing_file ผิดทุกไฟล์
(audit ขยะ 21 แถว ไม่ลบ) + ผนึกซ้ำ 6 แถว (ไม่ลบ เพราะ prev_sha256 อ้างถึง) → แก้ให้ตาม .gz
**N26:** postrotate ไม่สั่ง gunicorn เปิดไฟล์ใหม่ → เขียนต่อลงไฟล์ที่ผนึกแล้ว (เสี่ยง log login หายถาวร)
→ เพิ่ม `systemctl kill -s USR1 --kill-whom=main cafe-fas.service cafe-admin.service` ·
**แจ้งเตือน hash_mismatch ของ `cafe-fas-access.log-2026-09-16` จะขึ้นทุกคืนต่อไป — เป็นของจริง
(หลักฐานของ N26) ไม่แก้ย้อนหลัง**
**กับดักใหม่:** `git archive` บน Windows ใส่ CRLF ให้ทุกไฟล์ข้อความ (ไม่ใช่แค่ .sh) — ระบบยังรันได้
แต่เทียบ hash กับ repo ไม่ตรง → ตัด CR ทุกไฟล์ใน ~/cafe-wifi และ /opt/cafe-wifi (ยกเว้น venv)
ทางแก้ถาวรที่ยังไม่ได้ทำ: `.gitattributes` `* text=auto eol=lf`

## 2026-09-19 เย็น — N28 + ทดสอบทิ้งไว้ข้ามคืน
**N28 (regression จาก N22 ของผมเอง):** `ndsctl deauth` ของเครื่องที่ไม่อยู่ใน openNDS แล้ว ได้ stdout
`Client ... not found.` exit 1 → N22 นับเป็นล้มเหลว → session ไม่ถูกปิดตลอดกาล (ลูกค้ากลับบ้านก่อน
voucher หมด = กรณีที่พบบ่อยที่สุด) → แก้ให้ "not found" นับว่าสำเร็จ
**ตั้งไว้ตอนผู้ใช้ไม่อยู่ (ทั้งหมดเป็น transient หายเองตอนรีบูต):** `lab-monitor` (systemd-run ทุก 5 นาที
→ `/root/lab-monitor-20260919.csv`: อุณหภูมิ, throttled, load, RAM, conntrack, จำนวนลูกค้า, ดิสก์, DB,
unit ที่ล้ม, wlan0) + `lab-wifi-watchdog` · ทดสอบ voucher `CAFE-CFK34` หมดอายุตามเวลาจริง 19:19 —
แท็บเล็ตทิ้งไว้ในแล็บ (ต้องถูกตัดจริง), มือถือผู้ใช้เอาไป (ต้องปิด session ด้วย N28)
**งานที่ต้องให้ผู้ใช้อยู่:** quota used_up + ส่งออกหลักฐาน + ลบข้อมูล PDPA (ต้อง login แอดมิน), iOS,
หลายเครื่องพร้อมกัน · งานที่บ้าน: IPv6, DHCP off, Access Control, bypass T17

**ผล 19:19 ✅ (voucher หมดอายุตามเวลาจริงครั้งแรก):** valid_until 19:19:46 → enforce รอบ 19:21:50 ตั้ง
`expired` + ปิด 2 session (`voucher_expired`) · แท็บเล็ตที่ยังดูวิดีโอถูกตัดจริง (openNDS กลับเป็น
Preauthenticated) · มือถือที่ออกไปแล้วปิดได้ด้วย N28 ("ไม่อยู่ใน openNDS แล้ว ถือว่าตัดสำเร็จ") · ERROR 0 ·
**ช้ากว่าเวลาหมดอายุ ~2 นาที** (timer ทุก 5 นาที → สูงสุด 5 นาที ควรเขียนในเล่ม) · ended_at ของมือถือ
= 19:21 ทั้งที่ออกไปตั้งแต่ ~16:35 (ข้อจำกัด M1 ที่รู้อยู่แล้ว) · มือถืออัปโหลด ~1.4 GB (น่าจะสำรองรูป)
· monitor: 65-66°C ไม่ throttle, RAM คงที่ ~3350 MB, Wi-Fi Pi ไม่หลุดเลย
ตั้งตรวจรอบดึกไว้ 03:50 (logrotate 00:52 + งานรายคืน 03:30 = ทดสอบ N25/N26 ของจริงครั้งแรก)

**ผลข้ามคืน 2026-09-20 03:50 ✅ (N25/N26 ของจริงครั้งแรก):** logrotate 00:52 → gunicorn ทั้ง cafe-fas และ
cafe-admin ชี้ไฟล์ live ไม่ใช่ archive (N26 ใช้ได้) · ไฟล์รอบ 09-19 ถูกบีบอัดเป็น .gz แล้ว**ไม่ถูกผนึกซ้ำ**
และไม่มี missing_file (N25 ใช้ได้) · ผนึกใหม่ 10 ไฟล์ · integrity_failed มีแถวเดียว = ไฟล์ 09-16 ที่รู้อยู่แล้ว
(ตัว .gz ของมันถูกผนึกเป็นรายการใหม่ id 24 ตามดีไซน์ เพราะเนื้อหาต่างจากตอนผนึก) · backup 438 KB, purge
ผ่าน · monitor 132 ตัวอย่าง/11 ชม.: 63.8-67.2°C ไม่ throttle, RAM ว่าง 3279-3364 MB (ไม่รั่ว), ไม่มี unit
ล้ม, wlan0 ไม่หลุดเลย, enforce ERROR 0 · dnsmasq.log ~5.4 MB/10 ชม. ตอนแท็บเล็ตสตรีม (log-queries)

## 2026-09-20 — ทดสอบโควตา แล้วเจอบั๊กพ่วงอีก 3 ตัว (N29, N30, N31)
**N29 โควตาไม่เคยถูกบังคับใช้เลย** (ตรรกะวงกลม: used_mb อัปเดตตอนปิด session / session ปิดเมื่อ
voucher ไม่ active / voucher used_up เมื่อ used_mb>=quota) → แก้ให้รวมทราฟฟิกของ session ที่ยังเปิด
อยู่ · ยืนยัน: 500 MB quota, แท็บเล็ต 265 + โน้ตบุ๊ค 253.7 → "ใช้ครบโควตา (518/500)" → ตัด 2 เครื่อง →
`quota_exceeded` → โน้ตบุ๊ค 307
**N30 session ผี + M1** FAS บันทึก session/ผูกอุปกรณ์/audit login_ok ก่อน openNDS รับรอง ถ้า openNDS
ปฏิเสธ (หน้า login ค้างจน preauth idle timeout 10 นาที รหัสในหน้าหมดอายุ) DB จะบอกว่าออนไลน์ทั้งที่ใช้
ไม่ได้ + กินโควตาเครื่อง → แก้ด้วยการเทียบกับ `ndsctl json` ทุก 5 นาที ปิดตัวที่ไม่มีจริงด้วยสาเหตุ
`disconnected` (ผ่อนผัน 180 วิ; อ่าน ndsctl ไม่ได้ = ข้ามรอบ ไม่ใช่ปิดทั้งร้าน) · ยืนยันของจริงแล้ว
**N31 หลักฐานหายตอนทราฟฟิกหนัก (ร้ายแรงสุดของวัน)** โหลด 5 ไฟล์ 100 MB บันทึกได้ 2 → ดักเทียบทีละ
รายการเจอ `conntrack: WARNING: We have hit ENOBUFS! We are losing events.` ซึ่ง **โค้ดเดิมไม่เคยอ่าน
stderr เลย** (ถ้าท่อเต็ม 64 KB conntrack ค้าง = หยุดเก็บ log เงียบ ๆ) แก้ 4 จุด: `--buffer-size 8MB` ·
แยกเธรดอ่าน stdout เข้าคิว (เดิมอ่าน+เขียน DB ในลูปเดียว ท่อตันจน ENOBUFS) · เธรดอ่าน stderr + บันทึก
`audit_log action=log_gap` · `flush_buffer` เก็บ record ไว้ลองใหม่เมื่อ DB ล่ม (เดิม clear() ทิ้งทันที
ทั้งที่คอมเมนต์บอกว่าจะลองใหม่ — หายจริงตอน MariaDB รีสตาร์ท 19 ก.ย.) · ยืนยัน: โหลด 6 ไฟล์ บันทึกครบ 6
ENOBUFS 0
**บทเรียน:** อ่านโค้ดก่อนเริ่มทดสอบฟีเจอร์ ช่วยให้เจอ N29 ก่อนเสียเวลานั่งรอผลที่ไม่มีวันเกิด ·
ทุกครั้งที่ subprocess มี stderr=PIPE ต้องมีคนอ่าน ไม่งั้นค้างทั้งระบบ
**UX ที่ควรปรับก่อนส่ง:** หน้า portal ที่เปิดค้างไว้นานแล้ว login จะขึ้น "ไม่พบหน้านี้ — กรุณาต่อ Wi-Fi
ใหม่อีกครั้ง" ซึ่งชวนสับสน ควรเป็น "หน้านี้หมดอายุ กรุณาเปิดเว็บใดก็ได้ใหม่"

**ข้อ 8 (ส่งออกหลักฐาน + PDPA) 2026-09-20:** export ทำผ่าน CLI (`tools.export_evidence`) ไม่ใช่หน้าเว็บ ·
**N32**: `--to YYYY-MM-DD` เคยหมายถึงเที่ยงคืนต้นวัน → ไฟล์หลักฐานขาดข้อมูลวันสุดท้ายทั้งวันแบบเงียบ ๆ และ
ขอข้อมูลวันเดียวไม่ได้ → แก้ให้เป็นสิ้นวัน · ยืนยัน: 7,478 + 741 แถว, sha256 ใน manifest ตรงกับ
`sha256sum` จริง, audit `export_log` ครบ · **PDPA erase**: `natid_enc` ถูกล้าง, `natid_hash` เป็น
`PURGED-<id>`, แถวลูกค้าคงไว้ (FK), conn_log/dns_log ไม่ถูกแตะ · **N33 (ผู้ใช้เลือกทางนี้เอง)**: ห้ามลบ
ตัวตนระหว่างยังอยู่ในระยะเก็บบังคับ (LOG_RETENTION_DAYS=180) เพราะ ม.26 บังคับเก็บ "ข้อมูลผู้ใช้บริการ"
ด้วย ไม่ใช่แค่ข้อมูลจราจร — PDPA เองยกเว้นสิทธิ์ขอลบเมื่อมีกฎหมายอื่นบังคับ · คำขอที่ถูกปฏิเสธถูกบันทึก
เป็น audit `erase_refused` พร้อมวันที่ปลดล็อก · `purge_old_data` ลบให้อัตโนมัติเมื่อพ้นกำหนดอยู่แล้ว
**N31 รอบสอง:** ENOBUFS ยังเกิดแม้แก้แล้ว (เห็นช้าเพราะ stderr ของ conntrack มีบัฟเฟอร์ — ตรวจทันที
หลังทดสอบจึงไม่เห็น เป็นบทเรียนซ้ำรอยเรื่อง "ผลลบต้องมีหลักฐานคู่ขนาน") · ขยายเป็น 32 MB + `Nice=-5`
แล้วยังเจอ 1 ครั้งเมื่อสร้าง 3,000 การเชื่อมต่อใน 26 วิ · ที่อัตราปกติไม่พบการสูญหาย · **จุดยืนที่เขียน
ในเล่ม: ระบบรู้ตัวและบันทึก `log_gap` ไว้ ไม่ใช่อ้างว่าเก็บครบ 100%** · งานอนาคต: reconcile กับ
`conntrack -L` หรือย้ายไป NFLOG/IPFIX

## 2026-09-20 เย็น — ย้ายไปเราเตอร์จริง TP-Link ER706W (ปิด T16, T17, IPv6)
**ผัง:** เน็ตแล็บ → WAN2 ER706W (172.20.18.140) · วง `cafe-lan` VLAN 50 = 192.168.50.0/24 ปิด DHCP
ปิด IPv6 · Pi 192.168.50.2 ที่ LAN4 (untagged VLAN50) · โน้ตบุ๊ค LAN3 · SSID `Cafe-Guest` ของเราเตอร์
ผูกกับ cafe-lan · **ไม่ต้องใช้ Aruba/AP-515 แล้ว** และ DHCP ของแล็บอยู่หลัง WAN จึงแย่งจ่าย IP ไม่ได้อีก
**IPv6:** ปิดที่เราเตอร์ → ดักฟัง RA 40 วิ ไม่มีสักแพ็กเก็ต, Pi ไม่ได้ IPv6 global ✅
**T16:** ตั้งโน้ตบุ๊ค static 192.168.50.100 → **ก่อนมี ACL ออกเน็ตได้เต็มที่ และ conn_log/dns_log
0 แถว** · หลังตั้ง Firewall→Access Control (Allow GRP_PI=192.168.50.2 **เหนือ** Block
GRP_CAFE=192.168.50.0/24, LAN→WAN) → ถูกบล็อกหมด Pi และลูกค้าที่ login แล้วยังปกติ ✅
**T17:** ตรวจพบภายใน 1 นาที (bypass_alert + audit bypass_detected ระบุวง 192.168.50.0/24 ถูกต้อง
= ยืนยัน N27 ทำงาน)
**กับดักที่เจอ:** ย้ายเครือข่ายแล้วรัน install.sh ทันที → ค้างที่ pip นานหลายนาที เพราะสคริปต์ตั้ง
ค่าเครือข่าย **หลัง** ติดตั้งแพ็กเกจ เครื่องจึงยังใช้ default route เก่าที่ตายแล้ว (preflight เตือน
แต่ไม่หยุด) → แก้เฉพาะหน้าด้วย `ip addr add/del` + `ip route replace` เองก่อน แล้วสคริปต์ไปต่อได้
**ยังไม่ได้แก้: ควรตั้งค่าเครือข่ายก่อนติดตั้งแพ็กเกจเมื่อผู้ใช้ระบุ --uplink-cidr**
**ตั้งค่าเครื่องผู้ใช้ (เร็วกว่าหน้า Settings):** `netsh interface ip set address name="Ethernet 5"
static 192.168.50.100 255.255.255.0 192.168.50.1` / คืนค่า `... dhcp` — หน้า Settings ของ Windows
เคยตั้งไม่ติด 2 ครั้ง (DHCP ยัง Enabled อยู่ ทำให้ผลทดสอบหลอก ต้องเช็ค `Get-NetIPInterface` ยืนยัน)

## 2026-09-20 — T6 Client Isolation ผ่าน (ปิด O4)
**กฎกันลูกค้าคุยกันเองบน Pi (`ip saddr $CLIENT_NET ip daddr $CLIENT_NET drop`) บังคับใช้ไม่ได้จริง**
— พิสูจน์แล้วด้วยการวัด: ลูกค้า 2 เครื่อง ping กันได้ 100% ทั้งที่กฎมีอยู่ เพราะอยู่ L2 เดียวกัน
ทราฟฟิกไม่เคยผ่าน Pi (ตรงกับที่ D9 เตือน) → **มาตรการนี้ต้องทำที่เราเตอร์/AP เท่านั้น**
**ER706W ไม่มีตัวเลือกชื่อ Client Isolation** ตัวที่ใช้คือช่อง **Guest Network** ในหน้า SSID ·
คำอธิบายของ TP-Link ("block clients from reaching any private IP subnet") อ่านแล้วเหมือนจะตัด
Pi ไปด้วย **แต่ผลจริงตรงข้าม**: client↔client ถูกบล็อก 100% ขณะที่ยังถึง Pi 10.10.0.1, portal 307,
หลัง login HTTP/HTTPS 200 และยังบล็อกอยู่แม้ login แล้ว → ✅ O4 มีหลักฐานรองรับ
**บทเรียน:** อย่าเชื่อคำอธิบายฟีเจอร์ของผู้ผลิต ต้องวัดจริงทั้ง 3 อย่าง (ลูกค้าคุยกันเอง / ถึง
gateway+portal / ออกเน็ตหลัง login) เพราะยี่ห้ออื่น Guest Mode อาจตัดขาดจาก LAN จนใช้ไม่ได้
**สถานะเครื่องตอนนี้: ผู้ใช้ปิด Guest Network กลับแล้ว** (ทดสอบเสร็จ) — ถ้าจะเดโมหรือใช้จริง
ต้องเปิดใหม่ · ยังไม่ได้วัดคู่ไร้สาย↔ไร้สายโดยตรง (วัดจากเครื่องต่อสาย → เครื่องไร้สาย)
รายละเอียดเต็มใน `docs/hardware-test-log.md` §3.2

## 2026-09-20 ค่ำ — วัดตัวชี้วัด §14 + ปิด T11
**ผ่าน 3 ไม่ผ่าน 1:** หน้า login พร้อมใน 1.70-3.12 วิ (เป้า ≤10) · log ครบ 500/500 = 100%
(เป้า ≥99%) · ความเร็ว 319-324 Mbit/s (เป้า ≥200) · **เวลา login 3.90 วิ เกินเป้า ≤3 วิ**
**เวลา login แยกขั้นตอนแล้วไม่ใช่ความผิดของโค้ดเรา:** FAS 0.35 วิ · openNDS 3.32 วิ ·
จับเวลา `ndsctl auth` ตรง ๆ ได้ 1.86-2.12 วิ (openNDS สั่ง nftables ผ่านเชลล์หลายรอบต่อการ
อนุญาต 1 ครั้ง) → **ตัดสินใจไม่แก้ บันทึกเป็นข้อจำกัดข้อ 9** ถ้าจะแก้ต้องแตะ openNDS เอง
**วิธีวัด throughput บนชุดนี้ (ไว้ทำซ้ำ):** ไฟล์ 300 MB ใน `/dev/shm` (ห้ามใช้ microSD =
คอขวด) + `python3 -m http.server 18080 --bind 10.10.0.1` + **ต้องเปิด 2 ที่**: `nft insert
rule inet filter input ...` และ `nft insert rule ip nds_filter ndsRTR tcp dport 18080 accept`
เพราะ openNDS มี chain `ndsRTR` (hook input priority -100) ที่ reject ทุกพอร์ตนอกจาก
53/67/2050/8080/22/443 — ไม่รู้ข้อนี้จะ timeout แล้วสรุปผิดว่าไฟร์วอลล์เราพัง
**คอขวดคือการ์ดแลน USB ของโน้ตบุ๊ค (ASIX USB 2.0 ~320 Mbit/s)** ไม่ใช่ Pi — พิสูจน์ด้วย
CPU ว่าง 85-98% + 2 สายพร้อมกันได้รวมเท่าเดิม + เซิร์ฟเวอร์ทดสอบทำได้ 4,500 Mbit/s บนเครื่อง
**ยังวัดไม่ได้:** กรณี hairpin (เข้า-ออกสายเดียวกัน) เพราะไม่มีเครื่องที่สองฝั่งอัปลิงก์
**T11:** ใส่แถวอายุ 200 วัน + 170 วันลง conn_log/dns_log แล้วรัน `tools.purge_old_data` →
ลบเฉพาะเกิน 180 วัน ถูกต้อง · ลบข้อมูลจำลองออกหมดแล้ว
**สร้าง voucher ทดสอบจาก CLI ได้** (`PYTHONPATH=/opt/cafe-wifi/app venv/bin/python` แล้ว
`from common import crypto, db, audit`) — เผื่อทดสอบตอนไม่มีรหัสแอดมิน · เพิกถอนคืนแล้ว
**เก็บกวาด:** `bypass_alert` 503 แถว (ขยะแล็บ) ล้างแล้ว dump ไว้ที่
`/root/lab-cleanup/bypass_alert-lab-20260920.sql` + บันทึก audit `bypass_alert_cleared`
**กับดักเครื่องมือ:** PowerShell 5.1 พัง parser ถ้าใช้คีย์ภาษาไทยใน hash literal ·
`Restart-NetAdapter` ต้องสิทธิ์แอดมิน แต่ `ipconfig /release` + `/renew` ไม่ต้อง

## 2026-09-20 ดึก — N38 + N39 (ไล่หาสาเหตุ log_gap)
**N38:** แอดมิน logout ไม่เคยถูกบันทึก audit ทั้งที่ login ถูกบันทึก → ตรวจย้อนหลังไม่ได้ว่า
session ของแอดมินจบเมื่อไร · แก้แล้ว (ต้องติดตั้งใหม่บน Pi ถึงมีผล — **ยังไม่ได้ deploy**)
**N39 — หลักฐานสูญหายจริง วัดได้ ไม่ใช่แค่ข้อความเตือน:** วิธีที่ใช้พิสูจน์คือรันตัวฟัง
conntrack คู่ขนานเป็น "ตัวอ้างอิง" แล้ว **เทียบพอร์ตต้นทางทีละรายการ** (comm -23) กับแถวใน
conn_log → รอบหนึ่งยิง 300 ตัวอ้างอิงเห็น 300 แต่ DB ได้ 283 = หาย 17 (5.7%) · รายการที่หาย
มี timestamp ห่างกัน <1 ms = **หายเป็นชุด ไม่ใช่กระจาย**
**ผลรวมทุกรอบ:** 500→500 (100%), 300→283, 300→286, 150→150, 150→150 · **การสูญหายเกิดเฉพาะ
รอบที่มี ENOBUFS ไม่ได้ขึ้นกับปริมาณทราฟฟิก** — ถ้าไม่เกิด burst จะครบ 100% เสมอ
**ตัดออกไปแล้ว (อย่าไปเสียเวลาซ้ำ):** ขนาดบัฟเฟอร์ (conntrack รายงาน 64 MB อยู่แล้ว เพราะมี
CAP_NET_ADMIN จึงใช้ SO_RCVBUFFORCE ข้าม `net.core.rmem_max` ได้) · CPU (ว่าง 85-98%) ·
ARP หายชั่วคราว (สุ่ม 450 ครั้ง ไม่หายเลย REACHABLE/DELAY/STALE เท่านั้น) · ตัวฟังตัวที่สอง
รบกวน (ทดสอบซ้ำแล้วไม่ใช่) · cgroup limit (unit ไม่มี CPUQuota/MemoryMax)
**แก้ไปแล้วแต่ยังไม่หายขาด:** เธรดอ่านเหลือแค่ `put_nowait(line)` (ย้ายการ parse ไปลูปหลัก) +
ขยายท่อเป็น 1 MB ผ่าน `F_SETPIPE_SZ=1031` + ยกเพดาน rmem_max (กันเหนียว)
**เบาะแสที่เหลือ:** ชุดเหตุการณ์พรวดเดียวน่าจะมาจากการหมดอายุพร้อมกันของรายการ conntrack
(เช่น ping sweep 254 รายการ/นาทีของ bypass_detector ที่หมดอายุพร้อมกัน) — ตั้งตัวเฝ้า 30 นาที
ไว้ที่ `/tmp/ref_long.out` (unit `ref-long`) เพื่อจับว่าวินาทีที่เกิด ENOBUFS มีเหตุการณ์กี่รายการ
**เส้นทางแก้ถ้ายังไม่หาย:** ให้ conntrack เขียนลงไฟล์แล้วเรา tail แทนการอ่านผ่านท่อ (ตัดตัวเรา
ออกจากเส้นทางวิกฤติทั้งหมด) หรือย้ายไป NFLOG/IPFIX
**วิธี deploy ไฟล์เดียวไป Pi:** `python put.py "<local>|/home/ras/x.py"` แล้ว `install -o
cafewifi -g cafewifi -m 0644 ...` · **โค้ดบน Pi อยู่ที่ `/opt/cafe-wifi/logger/` ไม่ใช่
`/opt/cafe-wifi/app/logger/`** (โครงสร้างต่างจาก repo)

## 2026-09-20 ดึก (ต่อ) — N40/N41 เจอต้นตอ log_gap แล้ว **ปิดจบ**
**ต้นตอ: ตัวตรวจจับ bypass ของเราเอง** ยิง ping ทั้งวง 254 IP ทุกนาที (T17) → เคอร์เนลสร้าง
รายการ conntrack 254 รายการ → **ตัวเก็บกวาดของเคอร์เนลลบทั้งหมดพร้อมกันในรอบเดียว** →
เหตุการณ์ DESTROY 250-290 รายการในวินาทีเดียว ทุก 60-70 วินาที → บัฟเฟอร์ล้น → หลักฐาน
ลูกค้าหาย ~5% · **ฟีเจอร์ความปลอดภัยของเราเองทำลายหลักฐานของเราเอง**
**วิธีจับได้:** เฝ้า `conntrack -E` 13 นาที แล้ว **นับเหตุการณ์รายวินาที** (`awk` ตัด epoch
ทิ้งเศษวินาที + `uniq -c | sort -rn`) เห็นยอดพุ่งเป็นคาบ แล้วเปิดดูเนื้อหาวินาทีนั้น
**N40 (ทยอยยิงทีละ 16 เว้น 0.5 วิ) ไม่ช่วย** เพราะการลบเป็นรอบ ไม่ใช่ทีละรายการ — คงไว้
เพราะลดภาระเครื่อง (ไม่ต้อง fork 254 โปรเซสพร้อมกัน) แต่ไม่ใช่ทางแก้
**N41 = ทางแก้จริง:** `table ip raw` + `notrack` สำหรับ ICMP ที่ Pi ยิงเองในวง uplink
**ต้องเพิ่มกฎ input อนุญาต echo-reply ด้วย** (limit rate 300/s) ไม่งั้น reply ถูกทิ้งเพราะ
ไม่เข้า `ct state established` แล้ว T17 จะเพี้ยน · ยืนยัน: ping เราเตอร์ยังได้ 0% loss
**ผลหลังแก้:** ยอดสูงสุด 250-290 → 20-36/วินาที · ICMP ในระบบติดตาม = 0 · ENOBUFS 0 ·
ทดสอบความครบถ้วน 150/150
**กับดักสำคัญ:** `nft -f /etc/nftables.conf` มี `flush ruleset` → **ลบตารางของ openNDS
ทั้ง 3 ตารางด้วย** ลูกค้าหลุดหมดและ portal พัง → ต้อง `systemctl restart opennds` ทุกครั้ง
หลังโหลดกฎใหม่ แล้วเช็ค `nft list tables | grep -c nds` ต้องได้ 3
**เอกสารใหม่:** `docs/isp-router-runbook.md` = คู่มือย้ายไปเราเตอร์ค่ายเน็ต (สำรวจ 7 ข้อ
ก่อนถอดสาย → ลำดับย้ายที่ห้ามสลับ → ตรวจ 7 ข้อหลังย้าย → ตารางอาการ/สาเหตุ/ทางแก้)

**คิวถัดไป** — ทั้งสามข้อแรกทำให้เน็ตของโน้ตบุ๊คดับ ต้องบอกก่อนทุกครั้ง
1. ~~รีบูต Pi (T15)~~ ✅ ผ่านแล้ว 2026-09-19
2. ~~มือถือจริง Android~~ ✅ 2026-09-19 · **iOS ยังไม่ได้ทดสอบ**
3. ~~หลายเครื่องพร้อมกัน (T14)~~ ผู้ใช้สั่งข้าม · ~~T6 client isolation~~ ✅ 2026-09-20
4. **ที่เหลือจริง ๆ:** T7 ARP spoof (ควรถามอาจารย์ก่อน), iOS/macOS, จับเวลาออก voucher หน้างาน,
   อัตราเด้ง portal 4 OS × 10 ครั้ง, ทดสอบกับเราเตอร์ ISP ที่บ้าน (~~T11~~ ✅ ปิดแล้ว 2026-09-20)

**งานบ้านที่ค้าง (ไม่กระทบลูกค้า)**
4. openNDS ยังตั้ง `debuglevel 3` — ลดกลับเป็น `1` (ต้อง restart opennds = ลูกค้าหลุด)
5. dnsmasq ยังเปิด `log-dhcp` — `dnsmasq.log` โต 637 KB ใน 2 ชม.
6. ยังไม่ codify: การปลด NetworkManager จาก eth0 เข้า `install.sh`
7. `portal_session` ยังไม่ถูกปิดเมื่อลูกค้าเดินออกไปเฉย ๆ (voucher ยัง active) — `online_now`
   บนแดชบอร์ดจะค้างเกินจริง โค้ดเขียนยอมรับข้อจำกัดนี้ไว้เองแล้ว (M1) ยังไม่มีแผนแก้
8. FAS GET `/login` ไม่มีสาขา `status=authenticated` ตกไป `manual.html` (ยังไม่เจอผลเสียจริง)

**หมายเหตุสภาพเครื่องตอนนี้:** มี drop-in `/etc/systemd/system/cafe-enforce.service.d/
ndsctl-access.conf` วางไว้บน Pi ให้ตรงกับที่แก้ใน `install.sh` แล้ว (ลงใหม่จาก install.sh
จะได้ผลเดียวกันโดยไม่ต้องมี drop-in) · `bypass_alert` มีขยะจากแล็บ 266 แถว ถ้าจะเดโมควรล้าง

ดู [[real-pi-deployment]]
