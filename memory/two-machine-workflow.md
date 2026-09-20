---
name: two-machine-workflow
description: How the cafe-wifi project and Claude's context move between the user's two Windows machines, and which machine owns which kind of work
metadata:
  type: project
---

ผู้ใช้ทำงานโปรเจกต์นี้บน **2 เครื่อง** และแบ่งงานกันตามเครื่องมือที่ติดตั้งไว้:

- **เครื่องนี้ (`C:\Users\lenul\Desktop\cafe-wifi`)** — เครื่องหลักของงานโค้ด/ฮาร์ดแวร์
  **ไม่มี Microsoft Word/PowerPoint และไม่มี LibreOffice** (ยืนยัน 2026-09-21) จึง
  **เรนเดอร์ .docx/.pptx เพื่อตรวจหน้าตาไม่ได้เลย** ดู [[pptx-generation-windows-notes]]
- **อีกเครื่อง** — มี Word + PowerPoint และมี **สกิลที่ผู้ใช้ให้ Claude สร้างไว้สำหรับทำ
  "เล่มโครงการ"** งานเอกสารเล่ม/สไลด์ควรทำที่เครื่องนั้น

**ช่องทางส่งต่อบริบทให้ Claude อีกเครื่อง: โฟลเดอร์ `memory/` ที่รากรีโป**
ผู้ใช้ตั้งกลไกนี้ไว้เองตั้งแต่ต้น — ไฟล์ `claude อ่านซะ.txt` ที่รากบอกว่า *"อ่านไฟล์ทั้งหมด
ใน memory\ แล้วก็อบไปไว้ใน memory directory ของตัวเอง"* โฟลเดอร์นี้ **git track ไว้**
(ไม่ได้อยู่ใน .gitignore) จึงเดินทางไปกับ `git clone`/`git pull` ได้เอง

→ **กฎที่ต้องทำ:** เมื่อเขียน/แก้ความจำในไดเรกทอรีความจำจริง ให้ `cp` ไปทับ `memory/`
ในรีโปแล้ว commit ด้วย ไม่งั้นอีกเครื่องจะได้ของค้างเก่า (เคยค้างมาแล้วเกือบเดือน —
สแนปช็อต 2026-08-28 มี 6 ไฟล์ ขณะที่ของจริงมี 10 ไฟล์ ขาดงาน Pi จริง/Aruba/N17-N33 ทั้งหมด
แก้ไปใน commit 512e412)

**สิ่งที่ git พาไปไม่ได้** (อยู่ใน .gitignore): `รายงานเล่ม/` (.docx/.pdf ของเล่ม) และ
`*.pptx` — ต้องหิ้วไฟล์เองทุกรอบ (USB/คลาวด์) เหตุผลเดิมคือกลัว git history บวม

**repo:** `https://github.com/lenulk/Cafe-wifi.git` — เป็น **private** (GitHub ตอบ 404
กับคนนอก) จึงใส่ข้อมูลวงแลบ/รหัสอุปกรณ์ทดสอบใน memory/ ได้

**ข้อควรระวัง:** อย่าแก้ไฟล์เดียวกันพร้อมกันทั้งสองเครื่องบน `master` — ถ้าอีกเครื่องจะทำ
งานเล่ม ให้แยก branch
