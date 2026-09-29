# Cafe Wi-Fi Gateway & Management System

ระบบจัดการเครือข่าย Wi-Fi สำหรับคาเฟ่ พร้อมการยืนยันตัวตนด้วยเลขประจำตัวประชาชน
และการบันทึกข้อมูลจราจรทางคอมพิวเตอร์ตาม พ.ร.บ.คอมพิวเตอร์ มาตรา 26

> **เอกสารหลักของโปรเจกต์คือ [`PROJECT_PLAN.md`](PROJECT_PLAN.md)** — อ่านไฟล์นั้นก่อนเสมอ

## ติดตั้ง

```bash
git clone <repo> cafe-wifi && cd cafe-wifi
sudo ./install.sh
```

รองรับ Debian/Ubuntu/Raspberry Pi OS, Fedora/RHEL/Rocky, Arch, openSUSE, Alpine
(ตรวจ distro และเลือก package manager ให้อัตโนมัติ)

ดูก่อนว่าจะทำอะไรบ้างโดยไม่แก้ไขระบบจริง:

```bash
./install.sh --dry-run
```

พัฒนาบน VM/แล็ปท็อป (ไม่แตะ network config ของเครื่อง):

```bash
sudo ./install.sh -y --skip-network --skip-opennds
```

## ตั้งค่าครั้งแรก

หลังติดตั้งเสร็จ สคริปต์จะพิมพ์ URL และ Setup Token ออกมา

1. เปิด `https://<ip-gateway>:8443/setup`
2. กรอก Setup Token (ดูได้จาก `sudo cat /etc/cafe-wifi/setup.token`)
3. ตั้ง username/รหัสผ่านของผู้ดูแลระบบหลัก

หน้า `/setup` จะปิดตัวเองถาวรทันทีที่สร้างบัญชีแรกสำเร็จ และไฟล์ token ถูกลบอัตโนมัติ

ลืมรหัสผ่าน:

```bash
sudo -E /opt/cafe-wifi/venv/bin/python -m tools.reset_admin admin
```

## รันเทสต์

```bash
pip install pytest
PYTHONPATH=app pytest tests/ -v
```

สำหรับชุดทดสอบ Docker ที่มี MariaDB, Admin/FAS ผ่าน proxy, งาน CLI และ DNS collector ดู [วิธีใช้ Docker Compose](docs/docker-test.md)

## ถอนการติดตั้ง

```bash
sudo ./install.sh --uninstall
```

ฐานข้อมูล, log และ `/etc/cafe-wifi/secrets.env` จะไม่ถูกลบ (ต้องลบเอง)

## คำเตือนสำคัญ

- `/etc/cafe-wifi/secrets.env` คือกุญแจถอดรหัสเลขบัตรประชาชน **สำรองไว้นอกเครื่อง** ถ้าหายข้อมูลเดิมกู้ไม่ได้
- ห้าม commit `secrets.env` เข้า Git
- ห้ามทดสอบด้วยเลขบัตรประชาชนจริงของผู้อื่น — ใช้เลขสังเคราะห์ที่ขึ้นต้นด้วย 0
