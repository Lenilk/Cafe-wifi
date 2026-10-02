---
name: cafe-wifi-source-of-truth
description: "Cafe Wi-Fi source code and Git history live in the current repository; old tarballs are historical snapshots"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4acee012-a445-4450-b73e-0ccdbf0a9616
  modified: 2026-10-02
---

ซอร์สโค้ดปัจจุบันอยู่ใน Git repository นี้โดยตรง: `app/`, `tools/`, `tests/`,
`sql/`, `docs/`, `infra/`, `install.sh` และ `PROJECT_PLAN.md` ที่รากโปรเจกต์
ให้ตรวจ `git status` และอ่านไฟล์ใน working tree ก่อนแก้ไข

ทาร์บอล `cafe-wifi-project.tar.gz` และ `cafe-wifi-project-fixed.tar.gz` เป็น
snapshot เก่า ไม่ใช่แหล่งซอร์สปัจจุบัน ห้ามแตกทับ working tree เพื่อเริ่มงานใหม่
ขั้นตอนใน `CODING_BRIEF.md` §0 ที่เคยสั่งให้แตกทาร์บอลและ `git init` เป็นประวัติ
ช่วงก่อนมี repository นี้แล้ว ไม่ใช่ขั้นตอนที่ต้องทำซ้ำ

ดู [[track-fixes-and-issues]]
