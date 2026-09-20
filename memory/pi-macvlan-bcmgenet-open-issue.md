---
name: pi-macvlan-bcmgenet-open-issue
description: "RESOLVED 2026-09-16: broadcast UDP reaches userspace sockets normally on both eth0 (bcmgenet) and wlan0 after a fresh OS install (kernel 6.18.50). The August blocker is gone; no need for dhcrelay or a USB NIC. Key lesson kept here: a negative broadcast test is only valid with a paired tcpdump — two wrong conclusions came from skipping that."
metadata: 
  node_type: memory
  type: project
  originSessionId: b4fd18de-813b-4d0e-a000-7d22cbd2d64e
  modified: 2026-08-28T11:14:22.791Z
---

**สถานะ (2026-08-28, ไล่ตัวแปรจนสุดทางในเซสชันนี้): ไม่ใช่ปัญหา macvlan เลย — เป็นปัญหาทั่วเครื่อง**

## สรุปผลการไล่ตัวแปรจนถึงที่สุด
1. DAI ของมหาวิทยาลัย → เป็นสาเหตุจริงของปัญหา **unicast** ที่เจอรอบแรก (ตัด `ether24` แก้ได้จริง)
2. `--local-service` ของ dnsmasq → เป็นบั๊กจริง แก้แล้ว แต่ไม่ใช่สาเหตุหลักของปัญหา DHCP
3. **broadcast UDP ไม่ถึง socket ไหนเลยบนเครื่องนี้ ไม่ว่าจะ interface ไหน** — ทดสอบยืนยันสามชั้น:
   - `dnsmasq --log-dhcp` (foreground debug) ไม่เห็น transaction เลย ทั้งที่ tcpdump เห็นแพ็กเก็ต
   - raw `nc -ul 67` บน `cafe-wifi-cli0` (macvlan) — ไม่ได้รับอะไรเลย แม้ `nft flush ruleset`
     (ลบ firewall ทั้งหมด) แล้วก็ตาม
   - **raw Python socket (`SO_BROADCAST` set ชัดเจน) บน `eth0` ตรง ๆ (ไม่เกี่ยว macvlan เลย)**
     ฟังพอร์ต `5678` ที่เห็น broadcast UDP จริงจากอุปกรณ์อื่นในเน็ตเวิร์กผ่าน tcpdump ชัดเจน —
     **ก็ยัง TIMEOUT ไม่ได้รับอะไรเลย**

ข้อที่ 3 นี้คือหลักฐานที่ฟันธง: **ปัญหาไม่เกี่ยวกับ macvlan/`cafe-wifi-cli0` เลยแม้แต่นิดเดียว** —
เป็นปัญหาที่ตัวเครื่อง/kernel ของ Pi นี้เองที่ไม่ส่ง broadcast UDP ขึ้นไปให้ userspace socket ไหน
ได้เลย ไม่ว่าจะ bind อินเทอร์เฟซไหนก็ตาม ทั้งที่ NIC ระดับ tcpdump เห็นแพ็กเก็ตมาถึงจริงเสมอ

## ผลกระทบจริงต่อโปรเจกต์ (สำคัญมาก — แก้ไขจากที่เคยสรุปผิดไว้ก่อนหน้า)
เดิมเคยสรุปว่า "ปิดเคสแล้ว ระบบทำงานสมบูรณ์" — **ผิด** เพราะการทดสอบ login ที่ "สำเร็จ" ใช้ static IP
+ DHCP lease ปลอมที่สร้างขึ้นเอง ไม่ใช่ DHCP จริง พอทดสอบด้วย Automatic (DHCP) จริงจึงเจอว่า
**ลูกค้าจริงเชื่อมต่อไม่ได้เลยแม้แต่คนเดียว** เพราะ dnsmasq (หรือ daemon ไหนก็ตาม) ไม่มีทางได้รับ
DHCPDISCOVER เข้า socket ตัวเองได้เลยบนเครื่องนี้

**สิ่งสำคัญ: นี่ไม่ใช่เหตุผลให้กลับไปใช้สถาปัตยกรรม 2-อินเทอร์เฟซ** เพราะปัญหาไม่เกี่ยวกับ
macvlan/single-NIC เลย — ถ้าเป็นปัญหา kernel/OS ทั่วเครื่องจริง สถาปัตยกรรมไหนก็เจอปัญหาเดียวกัน
หมด (2-อินเทอร์เฟซก็ยังต้องรับ DHCPDISCOVER ผ่าน socket เดียวกันอยู่ดี) ต้องแก้ที่ตัวเครื่อง/OS
โดยตรง ไม่ใช่แก้ที่สถาปัตยกรรมเน็ตเวิร์ก

## ทฤษฎีที่ตัดออกเพิ่มเติมแล้ว (ทดสอบยืนยันหมดในรอบล่าสุด 2026-08-28 ช่วงเย็น)
- **reboot Pi ทั้งเครื่อง** — รีบูตแล้ว ยังพังเหมือนเดิมเป๊ะ (ตัดทฤษฎี "kernel state ค้างจากการ
  ทดสอบเอง" ออกได้)
- **`nf_conntrack`** — เพิ่ม `nft` raw table + rule `notrack` ให้ทั้ง `udp dport 67` และ
  `udp sport 67` (บายพาส conntrack ทั้งหมดสำหรับ DHCP traffic) แล้วทดสอบซ้ำ **ยังพังเหมือนเดิม**
  ตัดทฤษฎี conntrack ออกได้เช่นกัน
- ยืนยันด้วยวิธี capture คู่ (`tcpdump` + raw socket listener พร้อมกัน คนละ SSH channel เวลา
  เดียวกันเป๊ะ) ว่า **DHCPDISCOVER มาถึงจริง 3 ครั้งในหน้าต่างเวลาเดียวกับที่ socket listener
  timeout ไม่ได้อะไรเลย** — หมดข้อสงสัยเรื่อง timing/จังหวะไม่ตรงกันแล้ว

## หลักฐานระดับลึกสุด (strace, 2026-08-28 เย็น — จุดสุดท้ายที่ตรวจได้โดยไม่แตะ SD การ์ด)
```
ppoll([{fd=3, events=POLLIN}], 1, {tv_sec=25, tv_nsec=0}, NULL, 0) = 0 (Timeout) <25.025143>
```
`strace -tt -T python3 dhcp_test.py` ระหว่างมี DHCPDISCOVER จริงมาถึง (ยืนยันคู่กับ tcpdump ในรอบ
ก่อนหน้าว่ามาถึงจริงในช่วงเวลาเดียวกัน) — **kernel เองไม่เคยส่ง `POLLIN` ให้ socket นี้เลยตลอด 25
วิ** แปลว่าปัญหาอยู่ *ก่อน* `recvfrom()` ด้วยซ้ำ — kernel ไม่เคย enqueue แพ็กเก็ตเข้า receive
buffer ของ socket เลย ทั้งที่ NIC/tcpdump เห็นแพ็กเก็ตแน่นอน นี่คือจุดลึกสุดที่ไล่ได้จาก userspace
ล้วน ๆ โดยไม่ต้อง kprobe/ftrace เข้า kernel เอง (`udp_rcv`, `ip_local_deliver` เป็นจุดที่ต้องดูต่อ
ถ้าจะไปลึกกว่านี้ — เกินขอบเขตที่ทำผ่าน SSH ธรรมดาได้)

## SD การ์ด: มีใบเดียว ไม่มี Pi/การ์ดสำรอง
ก่อนจะลอง flash image อื่น (ทางที่เหลืออยู่ที่มีโอกาสสูงสุด) **ต้อง backup การ์ดปัจจุบันก่อนเสมอ**
เพราะไม่มีของสำรองกู้คืนได้เลยถ้าพัง — แนะนำใช้ Raspberry Pi Imager หรือ `dd`/`rpi-clone` จาก
คอมพิวเตอร์อีกเครื่องสร้าง image สำรองไว้ก่อน แล้วค่อย flash Raspberry Pi OS (ไม่ใช่ Debian
cloud-init image แบบเดิม) ทดสอบ broadcast UDP อย่างง่าย (ใช้สคริปต์ทดสอบใน
`C:\Users\lenul\AppData\Local\Temp\claude\...\scratchpad\dhcp_test.py` เป็นต้นแบบ) ก่อนจะ
ลง install.sh เต็มระบบใหม่ — ถ้า broadcast UDP ใช้ได้ปกติบน image ใหม่ = ยืนยันว่าเป็นปัญหาเฉพาะ
image/kernel เดิม (`6.18.34+rpt-rpi-v8`, cloud-init Debian) ไม่ใช่ฮาร์ดแวร์ Pi เสีย

## ทางที่ยังไม่ได้ลอง (เรียงตามลำดับที่ควรทำ)
1. **Flash Raspberry Pi OS ใหม่ (backup การ์ดเดิมก่อนเสมอ)** — ทางที่มีโอกาสเจอคำตอบสูงสุด
   หลังตัดทฤษฎีอื่นออกหมดแล้ว (macvlan, firewall, conntrack, kernel state ค้างจากการทดสอบ,
   และตอนนี้ยืนยันด้วย strace ระดับ syscall แล้วว่าปัญหาอยู่ใน kernel receive path จริง)
2. เช็ค `nstat -az UdpInErrors UdpRcvbufErrors UdpNoPorts UdpIgnoredMulti` ก่อน/หลังทดสอบคู่กัน
   ให้ชัดเจนกว่าที่เคยดูผ่าน ๆ (ยังทำได้โดยไม่ต้องแตะการ์ด แต่ให้ข้อมูลน้อยกว่าการ flash ใหม่)
3. ค้นหา "linux udp broadcast not delivered to socket" / "6.18 kernel udp broadcast regression"
   ใน kernel bug tracker/mailing list (ยังไม่มี browser access ในเซสชันนี้)
4. ถ้ามีโอกาสยืม Pi เครื่องอื่นได้ในอนาคต ทดสอบเทียบฮาร์ดแวร์แยกจาก image

**Why:** blocker ระดับใช้งานจริงไม่ได้เลยถ้าไม่แก้ — ลูกค้าจริงทุกคนเชื่อมด้วย DHCP ปกติเสมอ
**How to apply:** ตัดทฤษฎีเป็นไปได้แล้วเกือบหมด (macvlan, firewall, conntrack, kernel state
ค้าง) เหลือทางเดียวที่ให้ผลชัดเจนสุดคือ flash image อื่นทดสอบเทียบ — **backup การ์ดเดิมก่อนเสมอ
เพราะมีใบเดียวไม่มีสำรอง**

ดู [[real-pi-deployment]], [[r11-opennds-macvlan-resolved]]

---

## ⚠️ แก้ข้อสรุปเดิม (2026-09-16, Pi ลง OS ใหม่ที่ห้องแล็บ)

**ข้อสรุปที่เขียนไว้ข้างบนว่า "broadcast UDP ไม่ถึง socket เลยไม่ว่าอินเทอร์เฟซไหน" — ไม่ถูกต้อง**

ทดสอบบน Pi ที่ลง OS ใหม่ (kernel `6.18.50+rpt-rpi-v8` 11 ก.ย. เทียบกับของเดิม `6.18.34` 9 มิ.ย.,
ยังเป็น Debian 13 + cloud-init เหมือนเดิม, flash ด้วย rpi-imager) โดยยิง broadcast UDP จาก
โน้ตบุ๊ค (`192.168.0.174`) เข้า **`wlan0`** ของ Pi (`192.168.0.171`) ที่พอร์ต 9999 —
**socket ธรรมดา (`bind 0.0.0.0:9999` + `SO_BROADCAST`) ได้รับปกติทั้ง `255.255.255.255` และ
`192.168.0.255`** ยืนยันคู่กับ tcpdump ในหน้าต่างเวลาเดียวกัน (24 แพ็กเก็ตเข้า, socket ได้ 3 ก่อน
ปิดตัวเอง)

**ทำไมข้อสรุปเดิมถึงผิด:** หลักฐานที่ใช้สรุปว่า "eth0 ก็พัง" คือการฟังพอร์ต 5678 ซึ่ง
**เป็นเทสต์ที่ใช้ตัดสินไม่ได้** — ทราฟฟิกนั้นมี source เป็น `192.168.10.1` ซึ่ง Pi ไม่มี route ไป
ถึงเลย `rp_filter=2` (loose) จึง drop ทิ้งอย่างถูกต้องตามหลักการอยู่แล้ว ไม่เกี่ยวกับบั๊กใด ๆ
สิ่งที่ยืนยันได้จริงในเซสชัน 28 ส.ค. มีแค่ **macvlan (`cafe-wifi-cli0`) + พอร์ต 67** เท่านั้น

**ยังไม่รู้ ณ ตอนบันทึกนี้:** `eth0` (ไดรเวอร์ `bcmgenet`) รับ broadcast เข้า socket ได้ไหม —
ต้องให้โน้ตบุ๊คอยู่วง `172.20.18.0/24` ผ่านสวิตช์ก่อนถึงจะทดสอบได้ (ตอนนี้โน้ตบุ๊คเสียบพอร์ต 1 =
`ether1` ซึ่ง defconf ไม่ได้ใส่ใน bridge ไหนเลย เลยไม่ได้ IP — ต้องย้ายไปพอร์ต 2-8 ที่อยู่ bridge
เดียวกับ Pi)

**How to apply:** ถ้า `eth0` ผ่านด้วย = ปัญหาหายไปกับ image/kernel ใหม่ ลง `install.sh` ต่อได้เลย
ถ้า `eth0` ไม่ผ่านแต่ `wlan0` ผ่าน = ชี้ชัดว่าเป็นไดรเวอร์ `bcmgenet` โดยเฉพาะ → ไปแผน B4
(USB Ethernet สำหรับฝั่งลูกค้า) ได้ตรงเป้าโดยไม่ต้องเดาต่อ

## ✅ ปิดเคสแล้ว (2026-09-16): OS ใหม่แก้ปัญหาได้จริง

ทดสอบซ้ำบน **`eth0` (bcmgenet)** ด้วยโน้ตบุ๊คที่อยู่วงเดียวกันผ่านสวิตช์ (`172.20.18.129` →
Pi `172.20.18.128`) ยิง broadcast UDP พอร์ต 9999 ทั้ง `255.255.255.255` และ `172.20.18.255` —
**socket ได้รับปกติ 3/3 ครั้ง** (`GOT ('172.20.18.129', 64126) b'eth0-probe'`)

รวมกับผลบน `wlan0` ก่อนหน้า สรุปว่า **broadcast UDP → userspace socket ทำงานถูกต้องทั้งสอง
อินเทอร์เฟซบน image/เคอร์เนลใหม่** (`6.18.50+rpt-rpi-v8`) — บั๊กที่บล็อกมาตั้งแต่ 28 ส.ค. หายไป
พร้อมกับการลง OS ใหม่ **ไม่ต้องใช้แผน B1 (dhcrelay) หรือ B4 (USB Ethernet) แล้ว** เดินสถาปัตยกรรม
เดิม (single-NIC + macvlan ตาม D17) ต่อได้ตามปกติ

**สาเหตุที่แท้จริงของรอบเดิมยังไม่ทราบแน่ชัด** (เคอร์เนลเก่า `6.18.34` หรือ state ที่สะสมจากการ
ทดลองยาว ๆ วันนั้น) แต่ไม่คุ้มจะไล่ต่อเพราะ image ปัจจุบันใช้งานได้แล้ว — ถ้าเจออาการเดิมซ้ำใน
อนาคต ให้กลับมาอ่านไล่ทฤษฎีที่ตัดออกไปแล้วข้างบนก่อน

**บทเรียนสำคัญที่ต้องจำ:** ผลลบของการทดสอบ broadcast **ต้องมี tcpdump คู่ขนานยืนยันเสมอ** —
รอบ 28 ส.ค. สรุปผิดว่า "eth0 ก็พัง" จากเทสต์พอร์ต 5678 ที่ source ไม่ routable และวันนี้ก็เกือบ
สรุปผิดซ้ำอีกครั้งตอนที่ socket timeout แต่ tcpdump เผยว่าแพ็กเก็ตไม่เคยมาถึง Pi เลย (สวิตช์ยังไม่
ได้ตั้งค่า) — กฎนี้ช่วยไว้ได้จริง

## 🔎 สาเหตุจริงของอาการ "DHCP ไม่ทำงาน" (พบ 2026-09-16 ตอนเย็น)
ไม่ใช่เคอร์เนลและไม่ใช่ macvlan — เป็น **firewall ของเราเอง** `chain input` มี `policy drop` และ
อนุญาต DHCP เฉพาะ `ip saddr $CLIENT_NET` แต่ลูกค้าที่ยังไม่มี IP ต้องส่ง DHCPDISCOVER จาก
`0.0.0.0` เสมอ → โดน drop ทุกครั้ง (ไก่กับไข่) แก้แล้วใน commit N17 ด้วย
`udp sport 68 udp dport 67 accept` รายละเอียดครบอยู่ที่ [[pi-dhcp-and-portal-milestone]]
