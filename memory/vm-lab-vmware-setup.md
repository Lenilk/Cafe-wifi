---
name: vm-lab-vmware-setup
description: "How the cafe-wifi VM lab is wired in VMware Workstation on this machine, and two VMware traps hit while setting it up"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1cd1dc59-ab98-4dfa-9713-54278da60398
  modified: 2026-08-27T18:43:54.502Z
---

**สถานะ lab ปัจจุบัน (2026-08-27):** VM `OpenWrt-Router` (x86, 256MB) จำลองเราเตอร์บ้านตาม
§3.1.3 ของ [[cafe-wifi-source-of-truth|PROJECT_PLAN.md]] เสร็จและออกเน็ตได้แล้ว:
- `eth0` = WAN, Network Adapter 1 = **NAT** (vmnet8) → DHCP จริง ได้ `192.168.78.x`, ping 8.8.8.8 ผ่าน
- `eth1` = LAN, Network Adapter 2 = **Custom: VMnet2** (host-only, ตั้งเอง) → static `192.168.1.1/24`,
  DHCP server ปิด (`dhcp.lan.ignore=1`) เพราะ Pi (VM ถัดไป) จะ static เอง
- root password: `12345678`
- **จำสำคัญ: `eth0`/`eth1` mapping ไม่ตรงกับลำดับ Adapter ใน VMware UI เสมอไป** ต้องทดสอบด้วยการ
  add IP ชั่วคราวแล้ว ping gateway จริงก่อนเชื่อ (ห้ามเดาจากลำดับที่เห็นในหน้า Settings)
- Host (Windows) เข้าถึง LAN ได้ผ่าน adapter **"VMware Network Adapter VMnet2" = `192.168.1.99/24`**
  (ขยับจาก `.1` เพราะชนกับ OpenWrt) → **SSH เข้า OpenWrt ได้ตรง ๆ จาก host**:
  `ssh root@192.168.1.1` (รหัส `12345678`)

**กับดักที่ 1 — "Custom: Specific virtual network" กับ "LAN segment" เป็นคนละกลไก:**
ตอนสร้าง VM ครั้งแรก ตั้ง Network Adapter 2 เป็น **LAN Segment** ชื่อ "cafelan" (ไม่ใช่ VMnet เบอร์
จริง) — LAN Segment เป็นสวิตช์ส่วนตัวที่ผูกกับ VM เท่านั้น **ไม่โผล่ในรายการ Virtual Network Editor
เลย และไม่มีทางต่อ host adapter เข้าไปได้** ถ้าต้องการให้ host (Windows) เข้าถึงวงนั้นได้ด้วย (เช่น
จะ SSH จาก host) ต้องเปลี่ยนมาใช้ **"Custom: Specific virtual network" แล้วเลือกเลข VMnet จริง**
(เช่น VMnet2) แทน แล้วไปเพิ่ม/ตั้งค่า VMnet นั้นใน Virtual Network Editor (Type: Host-only, ปิด
"Use local DHCP service" เพราะแผนนี้ไม่ต้องการ DHCP บนวง LAN, ตั้ง Subnet IP เอง) — ทุก VM ที่ต้อง
อยู่วงเดียวกัน (OpenWrt, Pi, client ทดสอบ) ต้องเลือก VMnet เบอร์เดียวกันหมด ห้ามใช้ LAN Segment อีก

**กับดักที่ 2 — คอนโซล VMware (ไม่ใช่ SSH) กลืนตัวอักษรตอนพิมพ์/paste คำสั่งยาว:**
พิมพ์ `uci set network.wan.device='eth0'` ผ่านคอนโซล VM ตรง ๆ แล้วจุด (`.`) หรือบางส่วนของคำสั่งหาย
กลางทาง ทำให้เกิด section ขยะ (`network.wandevice=eth0`, `network.proto=dhcp`) โดยไม่มี error เตือน
ชัดเจน — เกิดซ้ำหลายรอบ ไม่ใช่ typo ของคนพิมพ์ **วิธีแก้ที่ได้ผล: เปิดทาง SSH เข้า VM โดยเร็วที่สุด
แล้วสั่งงานผ่าน SSH แทนคอนโซลเสมอ** (ใช้ `ssh` จาก Git Bash ได้ปกติ, มี askpass helper สำหรับ auth
แบบ non-interactive ถ้าจำเป็น) อย่าพิมพ์คำสั่งที่มีจุดหรือความยาวเกิน ~1 บรรทัดผ่านคอนโซล VMware ตรง ๆ

**Why:** ทั้งสองเรื่องนี้เสียเวลาไปหลายรอบกว่าจะรู้สาเหตุ (โดยเฉพาะกับดักที่ 2 ที่ดูเหมือนบั๊กของ
uci เอง แต่จริง ๆ คือ input corruption) — เจอซ้ำได้ง่ายถ้าลืมและไปตั้ง VM ใหม่ (เช่น VM "Pi",
VM ลูกค้าทดสอบ) แบบเดิม
**How to apply:** ตอนสร้าง VM ใหม่ในชุด lab นี้ ให้ตั้ง Network Adapter เป็น "Custom: VMnet2" ตั้งแต่
แรก (ไม่ใช้ LAN Segment) และเปิด SSH ให้เร็วที่สุดหลังบูต ก่อนจะเริ่มพิมพ์คำสั่ง config ยาว ๆ ผ่าน
คอนโซล

**กับดักที่ 3 — คอนโซล VMware กลืน/สลับตัวอักษรแม้ตอน "คนพิมพ์เอง" ก็เจอ (ไม่ใช่แค่ตอน automation):**
ตอนติดตั้ง Debian VM ตัวที่สอง ("Debian 13 pi") ผู้ใช้พิมพ์เองที่คอนโซลโดยตรง (ไม่ใช่ synthetic
input จาก Claude) ก็ยังเจอ `sed 's/^#*PermitRootLogin.*/PermitRootLogin yes/'` เขียนผิดเป็น
`PermitRootLign` (ตัวอักษรสลับ/หาย) ทำให้ sshd config พังและ sshd ไม่ยอมสตาร์ท (`sshd -t` บอก
"Bad configuration option") — และ `--no-pager`/`|` ก็เพี้ยนเป็น `--no-paper`/`!` ในคำสั่งเดียวกัน
**สรุป: นี่คือปัญหาของ VMware remote console เอง (การ render/ส่งสัญญาณคีย์บอร์ดผ่าน display
protocol) ไม่ใช่ปัญหาเฉพาะ automation** — ต้องระวังทุกครั้งที่มีใครพิมพ์คำสั่งยาวผ่านคอนโซลนี้
(ทั้งคนและ Claude) โดยเฉพาะที่มี `.`, `|`, `-`, หรือ flag ยาว ๆ
**How to apply:** เมื่อ config ไฟล์พังจากการพิมพ์ผ่านคอนโซล ให้ดูที่บรรทัด/error message ตรง ๆ
(เช่น `sshd -t`, `nft -c -f`, `uci show`) แทนการเดา แล้วแก้เฉพาะจุดด้วยคำสั่งอ้างเลขบรรทัด
(`sed -i 'N s/.../.../'`) แทนการ match ด้วย pattern ที่อาจไม่ตรงกับของเสียที่เกิดขึ้นจริง —
และย้ายไปทำงานผ่าน SSH ให้เร็วที่สุดเสมอเมื่อเป็นไปได้ (SSH ผ่าน terminal จริงไม่เจอปัญหานี้เลย)

**กับดักที่ 4 — อย่า `pkill -9 opennds` ตอน cleanup ระหว่างทดสอบ ให้ `systemctl stop` เสมอ:**
`pkill -9` ฆ่า process ทันทีไม่ให้มีโอกาส cleanup lock/pid file ของตัวเอง — รอบถัดไปที่
`opennds.service` พยายาม start จะเจอ "openNDS is already running, status [ 1 ]. Retry
later..." แล้ว fail ซ้ำหลายรอบ (systemd auto-restart จะรอ retry จนกว่า lock จะหมดอายุเอง
ใช้เวลาประมาณ 1-2 นาที) — **นี่คือ testing artifact จากการ cleanup ของเราเอง ไม่ใช่บั๊กของ
install.sh** เจอครั้งแรกดูเหมือน WARN "openNDS ยังไม่มี unit" (ข้อความ error message ของ
install.sh เดิมเข้าใจผิดสาเหตุนี้ — แก้ให้ไม่ซ่อน stderr แล้วในเวอร์ชันล่าสุด) วิธี cleanup
ที่ถูกต้อง: `systemctl stop opennds` ก่อนเสมอ ค่อย `pkill` ถ้ายังไม่ตายจริงๆ

**Debian VM "Debian 13 pi" — sshd เจอปัญหาเพิ่ม: `Missing privilege separation directory:
/run/sshd`** หลัง `apt install openssh-server` ใหม่ ๆ — โฟลเดอร์ `/run/sshd` (บน tmpfs) ยังไม่ถูก
สร้าง ต้อง `mkdir -p /run/sshd` ก่อน `systemctl restart ssh` ถึงจะขึ้น (เจอเฉพาะรอบแรกหลังติดตั้ง
บนระบบนี้ ปกติควรมี ExecStartPre สร้างให้เองแต่ไม่ทำงานในเคสนี้)

**Debian default: `PermitRootLogin prohibit-password`** — SSH ด้วย root/password ไม่ได้จนกว่าจะ
แก้ค่านี้เป็น `yes` ใน `/etc/ssh/sshd_config` เอง (ปกติของ Debian ไม่ใช่บั๊ก) ส่วน user ธรรมดา
(`nulk`) SSH ด้วย password ได้ปกติแต่ไม่มี `sudo` ติดตั้งมาให้ (ต้องลง `apt install sudo` เอง
ถ้าจะใช้ user ธรรมดาเป็นหลัก — ในที่นี้เลือกเปิด root แทนเพราะเร็วกว่า)

**สถานะล่าสุด (2026-08-27, จบเซสชันนี้):** ทั้ง 3 VM/2 ตัวที่ตั้งเสร็จแล้วพร้อมใช้:
- `OpenWrt-Router`: WAN=NAT(`192.168.78.x`)/eth0, LAN=VMnet2 static `192.168.1.1/24`/eth1,
  root `12345678`, SSH ที่ `192.168.1.1`
- `Debian 13 pi` (path: `C:\Users\lenul\OneDrive\เอกสาร\Virtual Machines\Debian 13 pi\`):
  NIC เดียว (`ens33`) บน VMnet2, static `192.168.1.2/24` (uplink) + `10.10.0.1/24` (customer
  gateway, ตรง §3.1.2 เป๊ะ) gateway `192.168.1.1`, hostname `pi`, root `12345678` /
  user `nulk` `12345678`, SSH เข้าได้ทั้งคู่, ออกเน็ตผ่าน double-NAT ยืนยันแล้ว (`ping 8.8.8.8` ผ่าน)
  เป็น Debian 13 (Trixie) ไม่ใช่ 12 (Bookworm) ตามที่แผนระบุ แต่ผู้ใช้ยืนยันให้ใช้ตัวนี้ได้
- Host (Windows) เข้าถึง LAN ผ่าน `VMware Network Adapter VMnet2` = `192.168.1.99/24`
- โค้ดโปรเจกต์อยู่ที่ `/root/cafe-wifi` บน Debian VM แล้ว (scp จาก git repo บน host)
- **สถานะสุดท้าย (2026-08-28, ปิด session): VM lab ทดสอบครบทุกอย่างที่ทำได้โดยไม่มีฮาร์ดแวร์
  จริงแล้ว** — VM สะอาด รัน `install.sh` จริงล่าสุดผ่านหมด service ครบ 14 ตัว active, ndsctl
  status ปกติ พร้อมให้ทดสอบต่อบน Raspberry Pi จริงได้เลย
- **A1 ปิดแล้ว** (openNDS บนอินเทอร์เฟซเดียว ผ่าน macvlan) — ดู [[r11-opennds-macvlan-resolved]]
- **A3/A5/T3/T4/T10 ปิดแล้ว**: จำลอง "ลูกค้า" ด้วย macvlan+netns บน VM เดียวกัน (ไม่ต้องตั้ง
  VM ที่ 3) ทดสอบ login เต็มวงจรจริงผ่าน openNDS จริงสำเร็จ, conn_log/dns_log จับ traffic จริง
  ถูกต้อง (proto/bytes) — เจอ+แก้บั๊กเพิ่มอีก 4 ตัว: dhcp-leasefile ชื่อผิด (ลูกค้าจริง login
  ไม่ได้เลยถ้าไม่แก้), double-base64 encoding ใน FAS protocol, proto parser เข้าใจ "ipv4"
  prefix ผิดเป็นชื่อโปรโตคอล, ไม่เคยเปิด nf_conntrack_acct (bytes เป็น 0 เสมอ, quota_mb
  ใช้งานไม่ได้จริง) — ดูรายละเอียดเต็มที่ [[r11-opennds-macvlan-resolved]]
- **T15 ปิดแล้ว**: ไฟบ้านตกจริงกลางเซสชันทดสอบ กลายเป็นโอกาสทดสอบ recovery ธรรมชาติ — พบว่า
  macvlan ไม่รอดจาก reboot (บั๊กใน network persistence logic) แก้ด้วย
  `cafe-wifi-netsetup.service` แล้วยืนยันด้วย reboot จริงแบบควบคุมเอง: ครบทุก service ใน ~17 วิ
- **T16 baseline ยืนยันแล้ว**: ไม่มี Access Control บนเราเตอร์ = bypass ได้จริง (ping ผ่าน)
- **T17 แก้ข้อจำกัดร้ายแรง**: `bypass_detector.py` เดิมอ่าน ARP cache แบบ passive ตรวจจับ
  อุปกรณ์ที่ไม่คุยกับ Pi โดยตรงไม่ได้เลย แก้ด้วย `active_arp_refresh()` (ping-sweep ทั้งวงก่อน
  อ่าน) — ยืนยันว่าจับอุปกรณ์ภายนอกจริงได้ แต่ทดสอบกับ "อุปกรณ์ bypass" ที่จำลองด้วย macvlan
  บนเครื่องเดียวกับ Pi เองไม่ได้ (ข้อจำกัดของ Linux macvlan bridge mode เอง ไม่ใช่บั๊กโค้ด)
- **ยังเหลือที่ต้องทำบน Pi จริงเท่านั้น**: T13 (จับเวลา Wi-Fi จริงกับ OS 4 ตัว), T14 (load test
  20 client จริง), T16/T17 เต็มรูปแบบกับอุปกรณ์แยกเครื่องจริง, T16 กรณีเปิด Access Control,
  throughput วัดจริง, ความร้อน/SD card endurance

ดู [[cafe-wifi-source-of-truth]]
