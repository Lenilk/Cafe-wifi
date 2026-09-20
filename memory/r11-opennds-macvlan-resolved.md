---
name: r11-opennds-macvlan-resolved
description: "R11 (openNDS on single-NIC D17 topology) is confirmed working via macvlan, tested end-to-end on the VM lab — no longer an open risk"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1cd1dc59-ab98-4dfa-9713-54278da60398
  modified: 2026-08-27T17:55:50.461Z
---

**สถานะ (2026-08-28): R11 ปิดแล้ว ยืนยันด้วยการทดสอบจริง ไม่ใช่แค่ทฤษฎี**

Plan A เดิม (แปะ `CLIENT_CIDR` บน `$NIC` ตรง ๆ ให้มี 2 IP บนอินเทอร์เฟซเดียว) **ยืนยันว่าใช้
กับ openNDS 10.1.3 ไม่ได้จริง** — มันเช็คใน `libopennds.sh::check_gw_ip()` นับจำนวน IPv4 บน
interface ที่ระบุ ถ้า >1 ปฏิเสธทำงานทันทีพร้อม log "IP address aliasing forbidden. Configure
a VLAN instead." เป็น hard-code ในซอร์ส **ไม่มี config option ให้ปิดเช็คนี้ได้เลย**

**Plan B (macvlan) ตาม PROJECT_PLAN.md §3.1.6 ทดสอบแล้วว่าใช้งานได้จริง 100%** — `install.sh`
แก้ให้สร้าง macvlan `${APP_NAME}-cli0` ซ้อนบน `$NIC` อัตโนมัติ (`ip link add ... type macvlan
mode bridge`) ย้าย `CLIENT_CIDR` ไปไว้ที่นั่น แล้วให้ openNDS/dnsmasq ผูกกับ macvlan แทน
`$NIC` ตรง ๆ — ยืนยันด้วยการรัน `install.sh` จริง (ไม่ dry-run) จบครบ 3 รอบติดกันบน Debian 13
VM, service 12 ตัว active หมด, `ndsctl status` ถูกต้องครบ, FAS Flask ตอบ 200

**บั๊กอื่นที่เจอ+แก้ระหว่างทาง (สำคัญพอกัน ไม่ใช่แค่ R11):**
1. `install.sh` เขียน `opennds.conf` แบบ flat-text ไปที่ `/etc/opennds/opennds.conf` แต่
   openNDS **ไม่เคยอ่านไฟล์นั้นเลย** — อ่านจาก `/etc/config/opennds` (UCI format) ผ่าน
   `/usr/lib/opennds/libopennds.sh` เท่านั้นเสมอ (ไม่มี `uci` บน Debian → fallback ไป
   `cat`/`grep`/`awk` ไฟล์นี้ตรง ๆ) — แปลว่าการตั้งค่าทั้งหมดที่เคยเขียนไว้ไม่เคยมีผลจริงสักครั้ง
   ตั้งแต่โปรเจกต์เริ่ม จนกระทั่งรอบนี้ที่ได้รัน install.sh จริงครั้งแรก
2. openNDS มีบั๊กเทียบเวอร์ชัน libmicrohttpd เอง (`src/main.c`): `else if (minor <
   MIN_MHD_MINOR)` ไม่เช็คว่า major สูงกว่าแล้วหรือยัง ทำให้ MHD 1.0.1 (default บน
   Debian/Ubuntu ปัจจุบัน) ถูกเข้าใจผิดว่าเก่ากว่า 0.9.71 — เลี่ยงด้วย `use_outdated_mhd=1`
   (ปลอดภัยเพราะเวอร์ชันจริงใหม่กว่ามาก ไม่ใช่เก่าจริงตามที่มันเตือน)
3. `fas_secure_enabled≥2` ต้องมี `php-cli` (openNDS เข้ารหัส query string เองฝั่งมันก่อนส่งไป
   FAS แม้ FAS จะเป็น Flask ของเราเองก็ตาม ไม่ใช่แค่ตัวอย่างสคริปต์ที่แถมมา) — เพิ่มแล้ว
4. `--uninstall` ลบ `opennds.service` แต่ `build_opennds()` เดิมข้าม `make install` ทั้งดุ้น
   ถ้าเจอ binary เดิม (unit ไม่ถูกสร้างกลับ) — แก้ให้เช็ค unit file ควบคู่ไปด้วย
5. backtick ในคอมเมนต์ไทยกลาง unquoted heredoc หลุดเป็น command substitution จริง (เจอ 2 จุด
   คนละที่ในเซสชันเดียวกัน — ครั้งที่สองคือตัวเองพลาดซ้ำตอนเขียนคอมเมนต์อธิบายบั๊กแรกเอง)
6. `curl` ถูกเรียกเช็คเน็ตใน `preflight()` ก่อน `install_packages()` จะติดตั้งมันจริง

**Why:** R11 เป็น "ความเสี่ยงอันดับ 1" ที่ทำให้แผนทั้งหมดอาจต้องเปลี่ยนสถาปัตยกรรมกลับไปใช้
2 อินเทอร์เฟซ (ซื้อ USB Ethernet) — ตอนนี้ปิดแล้วด้วยหลักฐานจริง ไม่ต้องซื้อฮาร์ดแวร์เพิ่ม
**How to apply:** ถ้าจะแตะโค้ดส่วน network/openNDS อีก ให้อ่าน `configure_network()` และ
`build_opennds()` ใน install.sh ที่แก้แล้วก่อนเสมอ (มีคอมเมนต์อธิบายที่มาไว้ครบทุกจุด) — และ
**ระวังบั๊ก backtick-in-heredoc ซ้ำ** เวลาเขียนคอมเมนต์ไทยใหม่ในไฟล์นี้ทุกครั้ง (สแกนด้วย
awk script ที่ไล่ทุก unquoted heredoc หา backtick — มีอยู่ใน conversation history ถ้าต้องใช้ซ้ำ)

**อัปเดต (2026-08-28, รอบสอง — ทดสอบ FAS login flow เต็มวงจร + ไฟดับจริงระหว่างทดสอบ):**
พบบั๊กเพิ่มอีก 3 ตัว ทั้งหมดแก้แล้วและยืนยันด้วยการทดสอบจริง:
1. `dhcp-leasefile` ตั้งชื่อเอง (`cafe-wifi.leases`) แต่ `libopennds.sh::dhcp_check()` หา
   lease file จาก path hardcode 3 ที่เท่านั้น (`/tmp/dhcp.leases`,
   `/var/lib/misc/dnsmasq.leases`, `/var/db/dnsmasq.leases`) — **ลูกค้าจริงทุกคนจะ login
   ไม่ได้เลย** ด้วย "IP not allocated by dhcp" ทั้งที่ DHCP ทำงานถูกต้อง 100% แก้เป็นใช้
   `/var/lib/misc/dnsmasq.leases` ตามที่ openNDS คาดหวัง
2. **บั๊ก double-base64 encoding** ใน `fas/opennds_proto.py` — openNDS จริง (PHP reference
   ใน `src/http_microhttpd.c`) เรียก `base64_encode(openssl_encrypt(...,0,$iv))` โดย
   `$options=0` (ไม่ใส่ `OPENSSL_RAW_DATA`) ซึ่งทำให้ `openssl_encrypt()` เอง base64-encode
   มาให้แล้วในตัว แล้วโค้ดยัง encode ซ้ำอีกชั้น — พารามิเตอร์ `fas` จริงคือ base64 **2 ชั้น**
   โค้ดเดิม decode ชั้นเดียว ได้ "Invalid padding bytes" ทุกครั้งกับ openNDS จริง ทั้งที่
   เทสต์เดิม 15 เคส round-trip กับตัวเองผ่านหมด (ตรงกับที่กังวลไว้แต่แรกว่า mock ที่คุมทั้ง
   สองฝั่งเป็นจุดเสี่ยงที่สุด) — ยืนยันด้วยการ login จริงจนจบ: `"state":"Authenticated"`
3. **macvlan ไม่รอดจากรีบูต** (เจอจากไฟดับบ้านจริงกลางเซสชันทดสอบ ไม่ได้ตั้งใจ) —
   `configure_network()` เดิมเช็คแค่ `[[ -d /etc/systemd/network ]]` ซึ่งมีอยู่ทุก distro
   ที่ใช้ systemd แม้ไม่ได้เปิด `systemd-networkd` จริง (Debian นี้ใช้ `ifupdown`) แก้ด้วย
   `cafe-wifi-netsetup.service` (systemd oneshot ของเราเอง มี retry-loop รอ NIC ก่อนรัน
   `ip` commands ตรงๆ ทุกบูต ไม่ต้องเดา network manager) — ยืนยันด้วย reboot จริงแบบควบคุม:
   service ครบ 13 ตัว active ภายใน ~17 วิ (ปิด T15)

**กับดักที่เจอเอง (จำไว้กันพลาดซ้ำ):** ตอน deploy บั๊ก #2 ครั้งแรก scp ไฟล์แก้ไปที่
`/opt/cafe-wifi/fas/opennds_proto.py` (ตัวที่ deploy จริง) **แต่ลืม sync ไปที่
`/root/cafe-wifi/app/fas/opennds_proto.py` (source tree ที่ install.sh คัดลอกมาจากตอนรัน
`install_app_files()`)** — พอรัน install.sh ซ้ำอีกรอบ (เพื่อทดสอบบั๊ก #3) มันคัดลอกไฟล์เก่า
(บั๊กเดิม) ทับกลับไปเงียบๆ โดยไม่มีใครรู้ตัว จนไป verify แล้วเจอว่า decrypt พังอีกรอบ —
**กฎ: แก้โค้ดใน `app/` แล้วต้อง scp ไปทั้ง 2 ที่เสมอ** (`/root/cafe-wifi/app/...` = source ที่
install.sh จะคัดลอกมาใช้ตอนรันซ้ำ, `/opt/cafe-wifi/...` = ตัวที่รันจริงตอนนี้) ไม่งั้นการแก้
จะหายไปเงียบๆ ตอน uninstall→reinstall รอบถัดไป

เพิ่มเทสต์ regression `test_decrypt_real_capture_from_live_opennds` ใน
`tests/test_opennds_proto.py` ใช้ payload จริงที่จับจาก openNDS binary เป็น fixture —
ห้ามลบ/แก้เป็นค่าที่สร้างเอง เพราะเป็นเทสต์เดียวในไฟล์นี้ที่ไม่ได้ mock ทั้งสองฝั่ง

ดู [[vm-lab-vmware-setup]] สำหรับรายละเอียดการตั้ง VM lab ที่ใช้ทดสอบเรื่องนี้
