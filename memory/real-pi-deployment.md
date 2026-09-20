---
name: real-pi-deployment
description: "Raspberry Pi 4B hardware for cafe-wifi: connection details, lab topology (MikroTik switch), install parameters, and the operational gotchas that cost the most time"
metadata:
  type: project
---

**เครื่อง:** Raspberry Pi 4B, Debian 13 (trixie) aarch64, kernel `6.18.50+rpt-rpi-v8`
(flash ใหม่ 2026-09-16 ด้วย rpi-imager, มี cloud-init + NetworkManager) hostname `rasberripi4b`

## การเชื่อมต่อ (ณ 2026-09-16 ที่ห้องแล็บ)
- **SSH จัดการ: `ras@192.168.0.171` รหัส `1234`** (wlan0, DHCP จาก Wi-Fi ห้องแล็บ — IP เปลี่ยนได้)
- `eth0` = ฝั่งลูกค้า+อัปลิงก์ (D17 สายเส้นเดียว) static `172.20.18.128/24` gw `172.20.18.1`
- `cafe-wifi-cli0` (macvlan บน eth0) = `10.10.0.1/24` ฝั่งลูกค้า, DHCP `10.10.0.100-250`
- **ห้ามปิด Wi-Fi ของโน้ตบุ๊ค** ระหว่างทำงาน — SSH ไป Pi วิ่งผ่านวงนั้น และ firewall บล็อก
  พอร์ต 22 จากฝั่งลูกค้าตามดีไซน์ ถ้าปิดจะเข้าไปดูอะไรไม่ได้เลย
- เครื่อง Windows ไม่มี sshpass/plink — ใช้ Python `paramiko` + PTY + `sudo -S`
- `install.sh` ต้องใช้ `-y` เสมอ (`confirm()` ไม่รับ `y` ที่ส่งผ่าน pty)

## สวิตช์ MikroTik CRS326-24G-2S+RM
- เข้าผ่าน **serial COM3 + PuTTY** (`admin`, ไม่มีรหัส) — ปลอดภัย ไม่มีทางหลุดจากการแก้ config
- **สวิตช์ถูกรีเซ็ตเป็น defconf ระหว่าง 28 ส.ค. – 16 ก.ย.** (มีคนอื่นแตะ) — defconf มี 2 bridge
  + VLAN PVID ปนกัน ทำให้บางพอร์ตคุยกันไม่ได้ ต้องเช็ค `/interface bridge port print` ก่อนเสมอ
- สายที่ใช้: **พอร์ต 3 = Pi · พอร์ต 4 = โน้ตบุ๊ค (การ์ด USB) · พอร์ต 24 = อัปลิงก์แล็บ**
- **รูแลนในตัวโน้ตบุ๊คเสีย** ใช้ได้แต่ USB adapter ตัวเดียว (`Ethernet 5`, ASIX AX88179)
- ถอด/ใส่อัปลิงก์: `/interface bridge port remove [find interface=ether24]` และ
  `/interface bridge port add bridge=<ชื่อ bridge> interface=ether24`

## เมื่อไหร่ต้องถอดพอร์ต 24
ตอนทดสอบ **DHCP ของลูกค้า** เท่านั้น — เพราะ DHCP ของแล็บจะแย่งตอบก่อน Pi (เคยทำให้โน้ตบุ๊ค
ได้ `172.20.18.x` แทน `10.10.0.x`) ส่วนตอนทดสอบอย่างอื่นให้เสียบไว้ เพราะ:
- `install.sh` ต้องใช้เน็ตโหลดแพ็กเกจ + git clone openNDS
- หลัง login ต้องมีเน็ตจริงให้ redirect กลับไปหน้าเดิมของลูกค้า
lease มีอายุ 4 ชม. ลูกค้าจึงไม่ renew ระหว่างนั้น เสียบกลับได้โดยไม่เสีย lease

## กับดักที่เสียเวลาที่สุด (จำไว้)
1. **NetworkManager คุม `eth0`** — ต้องปลดก่อนรัน install.sh ทุกครั้ง ไม่งั้นแย่งกับ static IP:
   เขียน `/etc/NetworkManager/conf.d/99-cafe-wifi-unmanage-eth0.conf` (`[keyfile]` +
   `unmanaged-devices=interface-name:eth0`) แล้ว `nmcli device set eth0 managed no` + flush
   **ยังไม่ได้ codify เข้า install.sh**
2. **ไฟล์ `.bak` ใน `/etc/dnsmasq.d/` ทำให้ dnsmasq ไม่สตาร์ท** (อ่านทุกไฟล์ในโฟลเดอร์ →
   keyword ซ้ำ) — สำรองไฟล์ไว้ที่อื่นเสมอ
3. **เบราว์เซอร์เลือกออก Wi-Fi แทนสาย LAN** ทำให้ทดสอบ captive portal ได้ผลลวง —
   ใช้ `curl --interface 10.10.0.179 ...` บังคับเส้นทางแทน แม่นยำและเห็น HTTP status ทุกขั้น
4. **แท็บเบราว์เซอร์เก่าที่ค้าง URL 404 ไว้หลอกได้** — ปิดแท็บเก่าทุกครั้งก่อนทดสอบใหม่
5. หลัง scp โค้ดใหม่ ต้อง `sed -i 's/\r$//'` ทุกไฟล์ `.sh` (git บน Windows ให้ CRLF)
6. แก้โค้ดต้อง copy ไปทั้ง `/opt/cafe-wifi/` (ตัวที่รัน) และ `~/cafe-wifi/app/` (source ที่
   install.sh คัดลอกตอนรันซ้ำ) ไม่งั้นการแก้หายตอนติดตั้งใหม่

## ย้าย Pi ระหว่างแล็บกับบ้าน (2026-09-19)
IP ฝั่งเราเตอร์เป็น static ต้องรัน install.sh ใหม่ทุกครั้งที่ย้าย แล้ว**รีบูต 1 ครั้ง** (สคริปต์ใช้
`ip addr add` ไม่ลบ IP เก่า ตั้งใจเพื่อไม่ให้ SSH หลุดกลางทาง IP เก่าจะค้างบน eth0 จนรีบูต) ·
แล็บ: `--uplink-cidr 172.20.18.128/24 --uplink-gw 172.20.18.1` · บ้าน: ตาม IP เราเตอร์จริง (แผนคือ
`192.168.1.2/24` / `192.168.1.1`) · N27 ทำให้ secrets.env ตามไปด้วยแล้ว · ข้อมูลใน DB ไม่หาย
**wlan0 รู้จักแค่ Wi-Fi `NetworkLab`** ที่บ้าน SSH ทาง Wi-Fi ไม่ได้จนกว่าจะเพิ่ม Wi-Fi บ้าน (ผู้ใช้ทำเอง:
`nmcli dev wifi connect <SSID> password <รหัส>` NM จำทั้งสองวงแล้วต่อวงที่เจอเอง) · ทางสำรองเข้า Pi
ได้เสมอ: ตั้งการ์ด LAN ของโน้ตบุ๊คเป็น static ในวงเดียวกับ IP ฝั่งเราเตอร์ของ Pi (ไม่ใส่ gateway)
แล้ว SSH เข้า IP นั้น (ไฟร์วอลล์ปิด 22 เฉพาะวงลูกค้า)
**ที่แล็บต้องตั้งสวิตช์ Aruba ใหม่ทุกครั้ง** (ไม่ได้ write memory) ดู [[aruba-lab-switch]]

ดู [[cafe-wifi-source-of-truth]], [[pi-dhcp-and-portal-milestone]]
