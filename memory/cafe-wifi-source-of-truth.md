---
name: cafe-wifi-source-of-truth
description: "cafe-wifi repo has no source code on disk — it lives in a tarball, and the root copies of install.sh/PROJECT_PLAN.md are newer than the tarball's"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4acee012-a445-4450-b73e-0ccdbf0a9616
  modified: 2026-08-26T07:03:25.023Z
---

ในโฟลเดอร์ `cafe-wifi` ไม่มีซอร์สโค้ดอยู่บนดิสก์เลย มีแค่ `PROJECT_PLAN.md`,
`install.sh`, ทาร์บอล 2 ก้อน, pptx และโฟลเดอร์ `รายงานเล่ม/` — โค้ดจริง
(`app/ tools/ tests/ sql/ docs/ infra/`) อยู่ใน `cafe-wifi-project-fixed.tar.gz` เท่านั้น
(`cafe-wifi-project.tar.gz` คือของเก่า 2026-08-23 อย่าใช้)

**กับดัก:** ทาร์บอล `-fixed` มี `install.sh` (1,363 บรรทัด) และ `PROJECT_PLAN.md`
(1,098 บรรทัด) ติดมาด้วย แต่ทั้งคู่**เก่ากว่า**ที่รากโฟลเดอร์ (1,503 และ 1,111 บรรทัด
ณ 2026-08-26) — แตกทาร์บอลทับตรง ๆ = ย้อนงานหาย ต้องสำรองสองไฟล์นี้ก่อนเสมอ

**ยังไม่มี git repo** ทั้งที่ Task Board §9 ติ๊ก `[x] สร้าง Git repo` ไปแล้ว และ
D17/R11 ในแผนอ้างว่า "โค้ด 2-อินเทอร์เฟซเดิมยังอยู่ใน git history" ซึ่งไม่จริง

ขั้นตอนตั้งต้นที่ถูกต้องเขียนไว้ใน `CODING_BRIEF.md` §0 แล้ว

**Why:** เสียเวลาไล่หาว่าไฟล์ไหนคือตัวจริงทุกครั้งที่เปิด session ใหม่ และเสี่ยง
ทำงานที่แก้ไปแล้ว 15 บั๊กหายทั้งก้อน
**How to apply:** ก่อนแตะโค้ดโปรเจกต์นี้ ให้ทำตาม `CODING_BRIEF.md` §0 เสมอ —
สำรอง `PROJECT_PLAN.md`/`install.sh` → แตกทาร์บอล `--strip-components=1` → เอาคืน →
`git init` ทันที

ดู [[track-fixes-and-issues]]
