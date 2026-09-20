---
name: aruba-lab-switch
description: 2026-09-19 lab moved from MikroTik to an Aruba CX 6100 + Aruba AP-515 (MikroTik has no PoE); console/login facts from the user's training decks, and the AP settings that must not be got wrong
metadata:
  type: project
---

**ทำไมเปลี่ยน:** MikroTik CRS326 ไม่มี PoE จ่ายไฟให้ AP ไม่ได้ ต้องใช้ AP เพื่อทดสอบมือถือจริง
(T13) จึงย้ายไปสวิตช์ Aruba ของแล็บ (2026-09-19) — **ตัวที่ใช้จริงคือ CX 6100** (สไลด์เทรนเป็น 6200F แต่
AOS-CX เหมือนกัน คำสั่งใช้แทนกันได้) · 6100 มีทั้งรุ่น PoE (JL679A/JL677A/JL675A = "PoE4") และ
ไม่มี PoE (JL678A/JL676A) ต้องเช็ครหัสรุ่น · ยังไม่รู้ว่า 6100 รองรับ `dhcpv4-snooping` ไหม

**ข้อมูลจากสไลด์เทรนของผู้ใช้** (`C:\Users\lenul\Desktop\aruba\` — SW/IAP/MC .pptx, ไฟล์ละ
~90-130 MB ส่วนใหญ่เป็นรูป ดึงข้อความด้วย zipfile + regex `<a:t>`):
- สวิตช์ HPE Aruba CX 6200F (AOS-CX) console USB-C/RJ-45 **115200** baud · `admin` ไม่มีรหัส
  แล้วบังคับตั้งใหม่ · สไลด์เทรนใช้ `P@ssw0rd` · พอร์ตตั้งด้วย `no routing` / `vlan access N` /
  `no shut`
- AP Aruba Instant AP-515 · รีเซ็ต: กดปุ่มค้าง >10 วิ · ปล่อย SSID `SetMeUp-XX:XX:XX` ·
  login `admin` + Serial Number ตัวพิมพ์ใหญ่
- `GEMINI.md` ในโฟลเดอร์นั้น = รูปแบบที่ผู้ใช้ชอบเวลาอธิบายแล็บ: ทีละขั้น (จุดประสงค์, ไดอะแกรม,
  หลักการ, คำสั่ง CLI จริง, คำสั่งตรวจสอบ, ข้อควรระวัง) + ไดอะแกรม Mermaid

**ข้อห้ามตอนตั้ง SSID:** Client IP assignment ต้องเป็น **Network assigned** (bridge ลงสาย)
ห้ามเลือก Virtual Controller assigned — AP จะ NAT ลูกค้าทุกคนหลัง IP เดียว Pi เห็นทั้งร้านเป็น
MAC เดียว log รายบุคคลตาม ม.26 พังทันที · ปิด captive portal ของ AP เอง (openNDS ทำหน้าที่นี้)

**สวิตช์จริง:** JL677A 6100 24G CL4 4SFP+ (PoE 370W) เฟิร์มแวร์ PL.10.11.1011 hostname `6100`
มีคอนฟิกเทรนค้างอยู่ (VLAN 10/20/30/100, trunk 1/1/1,4,5, access VLAN 10 ที่ 1/1/2-3) — **ไม่ลบ ไม่
`write memory`** ปิดเครื่องแล้วกลับสภาพเดิมของแล็บ · ต้องตั้งใหม่ทุกครั้งที่สวิตช์รีบูต
**พอร์ต:** 1/1/6 = Pi · 1/1/7 = โน้ตบุ๊ค · 1/1/8 = AP (PoE) · 1/1/24 = อัปลิงก์แล็บ
**คอนฟิกที่ใช้ (ยืนยันแล้ว 2026-09-19):** พอร์ต 6-8 `spanning-tree port-type admin-edge` +
`description` · `dhcpv4-snooping` global + `vlan 1` → `dhcpv4-snooping` + `interface 1/1/6` →
`dhcpv4-snooping trust` — ✅ ทิ้ง DHCP ของแล็บที่สวิตช์ได้จริง **ไม่ต้องถอดสายอัปลิงก์อีกแล้ว**
6100 แทรก option 82 โดยปริยาย (Circuit-ID = เลขพอร์ต, Remote-ID = MAC สวิตช์) — dnsmasq รับได้ปกติ
**อัปลิงก์แล็บบล็อก `neverssl.com`** (ทาง wlan0 ได้ ทาง eth0 ไม่ได้) — ทดสอบด้วย `example.com` แทน

ดู [[real-pi-deployment]], [[pi-dhcp-and-portal-milestone]]
