---
name: two-machine-workflow
description: Role split between the user's two machines (notebook = field testing on real hardware, desktop = documents only) and how evidence and context flow between them
metadata:
  type: project
---

ผู้ใช้แบ่งงานโปรเจกต์นี้ออกเป็น **2 เครื่อง คนละหน้าที่กันชัดเจน** (ยืนยัน 2026-09-21):

- **โน้ตบุ๊ก = `C:\Users\lenul\Desktop\cafe-wifi` (เครื่องที่ Claude ทำงานอยู่)**
  เอาไว้ **หิ้วไปทดลองกับของจริง** — Pi 4B, สวิตช์ Aruba, หน้างานจริง
  ดู [[real-pi-deployment]], [[aruba-lab-switch]], [[pi-dhcp-and-portal-milestone]]
  **ไม่มี Microsoft Word/PowerPoint และไม่มี LibreOffice** → เรนเดอร์ .docx/.pptx
  เพื่อตรวจหน้าตาไม่ได้เลย ดู [[pptx-generation-windows-notes]]

- **อีกเครื่อง (เดสก์ท็อป) = ทำเอกสารอย่างเดียว ไม่ได้ทำโปรเจกต์แล้ว**
  มี Word + PowerPoint และมีสกิลที่ผู้ใช้ให้ Claude สร้างไว้สำหรับทำ "เล่มโครงการ"
  เครื่องนี้ไม่ต้องรันโค้ด ไม่ต้องต่อฮาร์ดแวร์ — ต้องการแค่ **หลักฐานผลทดสอบ + บริบท**

**ทิศทางการไหลของข้อมูลจึงเป็นทางเดียว: โน้ตบุ๊ก → เดสก์ท็อป**
ภาคสนามเก็บหลักฐาน แล้วส่งให้เครื่องเอกสารเอาไปเขียนเล่ม

**ช่องทางที่ git พาไปให้อัตโนมัติ** (อยู่ใน repo, track ไว้แล้ว):
- `memory/` ที่รากรีโป — สำเนาความจำของ Claude ไฟล์ `claude อ่านซะ.txt` ที่รากสั่งไว้ว่า
  *"อ่านไฟล์ทั้งหมดใน memory\ แล้วก็อบไปไว้ใน memory directory ของตัวเอง"*
- `docs/hardware-test-log.md` — บันทึกผลทดสอบฮาร์ดแวร์จริง (ก้อนใหญ่สุดที่เล่มต้องใช้)
- `docs/test-plan.md`, `PROJECT_PLAN.md`, `install.sh`
- `รายงานเล่ม/ข้อมูลทดสอบ/` — ข้อมูลดิบจากภาคสนาม (CSV/log) เปิดให้ผ่าน git แล้วใน
  commit ที่แก้ .gitignore เพราะเป็นของที่ต้องส่งข้ามเครื่องบ่อยและเป็นไฟล์ข้อความเล็ก

→ **กฎนี้ถูกทำเป็นอัตโนมัติแล้ว:** `.githooks/pre-commit` ซิงก์ความจำจากไดเรกทอรีจริง
เข้า `memory/` แล้ว `git add` ให้เองทุกครั้งที่ commit ไม่ต้อง `cp` มือแล้ว
- เปิดใช้ครั้งเดียวต่อเครื่อง: `git config core.hooksPath .githooks`
  (`core.hooksPath` เป็น config ของ clone ไม่ติดไปกับ git ต้องสั่งเองที่เครื่องใหม่)
- hook หาโฟลเดอร์ความจำจาก path ของโปรเจกต์เอง (`C:/Users/x/Desktop/cafe-wifi` ->
  `C--Users-x-Desktop-cafe-wifi`) เครื่องที่ไม่มีความจำจะข้ามเงียบ ๆ ไม่พัง
- ถ้าลบความจำที่ผิดออก hook จะ **เตือน** ว่ามีไฟล์ค้างใน `memory/` แต่ไม่ลบให้เอง
  ต้อง `git rm` เอง (ตั้งใจให้เป็นแบบนี้ -- ลบไฟล์อัตโนมัติเสี่ยงเกินไป)
- ข้ามชั่วคราวด้วย `git commit --no-verify`

(ก่อนมี hook เคยค้างมาเกือบเดือน แก้ใน commit 512e412)

**ที่ยังต้องหิ้วเอง** (.gitignore กันไว้เพราะไฟล์ไบนารีใหญ่ ทำ history บวม):
`รายงานเล่ม/*.docx`, `*.pdf`, `รายงานเล่ม/ตัวอย่างเล่ม/` (~13 MB), `*.pptx`
ตัวเล่มที่แก้ที่เดสก์ท็อปต้องส่งกลับมือ — git ไม่พากลับ

**repo:** `https://github.com/lenulk/Cafe-wifi.git` — **private** (GitHub ตอบ 404 กับคนนอก)
จึงใส่ข้อมูลวงแลบ/รหัสอุปกรณ์ทดสอบใน memory/ ได้

**ข้อควรระวัง:** เครื่องเอกสารไม่ได้แตะโค้ด โอกาสชนกันต่ำ แต่ถ้ามันจะแก้ไฟล์ในรีโป
ให้แยก branch (`git checkout -b report`) อย่าเขียนทับ master พร้อมกัน
