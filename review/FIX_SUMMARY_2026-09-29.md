# สรุปการแก้ไขตาม Static Code Review (29 กันยายน 2026)

เอกสารนี้สรุปการแก้ข้อค้นพบ R01–R13 จาก [รายงานรีวิว](STATIC_CODE_REVIEW_2026-09-29.md) ใน commits `871731e`, `bd78b59`, `3fbe042`, `99f111e`, `5d53dc1` และ `a920ae1` พร้อมวิธีทดสอบและสิ่งที่ **ยังไม่ได้ยืนยันบน Raspberry Pi จริง** ผลทดสอบอัตโนมัติไม่ได้ใช้แทนการตรวจรับระบบ gateway หน้างาน

## สิ่งที่แก้

| ข้อ | การเปลี่ยนแปลง | จุดหลักในโค้ด |
|---|---|---|
| R01 | DNS collector ตรวจ inode เมื่ออ่านถึงท้ายไฟล์; เมื่อ logrotate เปลี่ยนไฟล์ จะเปิดไฟล์ใหม่จากต้นไฟล์ ไม่ค้างอยู่กับ inode เก่า | `app/logger/dns_collector.py` |
| R02 | ล้าง DNS buffer หลังเขียน DB สำเร็จเท่านั้น; หากล้มเหลวจะ retry โดยจำกัดคิวใน RAM ที่ 20,000 รายการ หากเกินเพดานจะบันทึก `log_gap` พร้อมจำนวนและช่วงเวลาใน service log และตัวนับ dropped | `app/logger/dns_collector.py`, `app/logger/telemetry.py` |
| R03 | ตัวหลักตรวจว่า collector threads ยังอยู่และออก nonzero หากตัวใดหยุด; connection collector ตรวจ subprocess `conntrack` และ reader threads ด้วย มี heartbeat/ตัวนับแยกชนิด log บนหน้า Admin `/status` | `app/logger/run_all.py`, `app/logger/conn_collector.py`, `app/logger/telemetry.py`, `app/admin/templates/status.html` |
| R04 | Connection ที่หา MAC ไม่พบยังถูกบันทึกด้วย IP และ `mac=NULL` พร้อมนับ `unmapped` แทนการข้ามเหตุการณ์ | `app/logger/conn_collector.py`, `sql/001_schema.sql` |
| R05 | ค้นหาและส่งออก log โดยโยงกับ `portal_session` ที่ยืนยันแล้ว ตรง MAC, IP และช่วงเวลา; หากพบหลาย session หรือไม่มีข้อมูลพอ จะไม่เดาชื่อลูกค้า | `app/admin/app.py`, `tools/export_evidence.py` |
| R06 | เลื่อนการล้างข้อมูลระบุตัวตนตามกิจกรรมที่ยังต้องเก็บ รวมเวลาจบ session และ log ล่าสุด; คำขอลบรายคนใช้หลักเดียวกัน | `app/common/customer.py`, `tools/purge_old_data.py`, `app/admin/app.py` |
| R07 | FAS เก็บ context ที่ถอดจาก openNDS ไว้ฝั่ง server อายุสั้น; POST ส่ง nonce แทน hidden fields สำคัญ และตรวจ IP/gateway/authdir ก่อนสร้าง authorization URL | `app/fas/app.py`, `sql/001_schema.sql` |
| R08 | สร้าง session เป็น `pending` ก่อน; timer ตรวจ `ndsctl json` แล้วเลื่อนเป็น `authenticated` เฉพาะเมื่อ state, IP และเวลาเริ่ม session ตรงกัน; timeout ปิดรายการหลัง deauth สำเร็จ และกัน pending ซ้อนจาก MAC เดียวกัน | `tools/reconcile_pending.py`, `app/fas/app.py`, `install.sh` |
| R09 | รหัส voucher ที่ต้องแสดงครั้งเดียวเก็บเข้ารหัสฝั่ง server อายุ 5 นาที; cookie ถือเพียง token และ token ใช้ซ้ำไม่ได้ | `app/admin/app.py`, `app/admin/templates/issue_result.html`, `sql/001_schema.sql` |
| R10 | งานอ่อนไหว เช่น ออก/ยกเลิก voucher, เปิดเลขบัตรเต็ม, ค้นหาและส่งออกหลักฐาน ต้องบันทึก audit สำเร็จก่อนจึงดำเนินต่อ; งานฐานข้อมูลที่เกี่ยวข้องใช้งานใน transaction เดียวกันเมื่อทำได้ | `app/common/audit.py`, `app/admin/app.py`, `tools/export_evidence.py` |
| R11 | หยุดให้ logrotate ลบ archive อัตโนมัติ (`rotate -1`); งาน integrity ตรวจ hash ก่อนลบไฟล์ครบอายุ บันทึก audit และสถานะการลบใน manifest เพื่อแยกจากไฟล์หายผิดปกติ | `app/logger/integrity.py`, `install.sh`, `sql/001_schema.sql` |
| R12 | ตัวติดตั้งปฏิเสธ `--retention-days` ต่ำกว่า 90 วัน แม้ใช้ `-y` หรือ `--dry-run`; งาน purge/integrity ตรวจขั้นต่ำด้วย | `install.sh`, `tools/purge_old_data.py`, `app/logger/integrity.py` |
| R13 | เก็บ DNS `query` และ `answer` เป็นเหตุการณ์แยกกัน ไม่จับคู่คำตอบจากชื่อโดเมนอย่างเดียว; หน้า Admin ระบุชนิดเหตุการณ์ | `app/logger/dns_collector.py`, `app/admin/templates/logs_search.html`, `sql/001_schema.sql` |

## วิธีทดสอบในเครื่องพัฒนา

รันจากราก repository โดยมี dependencies ของโครงการและ `pytest`:

```bash
PYTHONPATH=app pytest -q tests
bash -n install.sh
python3 -m compileall -q app tools tests
```

หากใช้ชุด Docker Compose สำหรับทดสอบที่มีใน workspace นี้ ให้ทำตาม `docs/docker-test.md` และรัน `docker compose run --rm tests` ชุดนี้ใช้ gateway จำลอง ไม่ใช่ openNDS จริง ผลตรวจครั้งล่าสุดหลังแก้ทั้งหมด: **277 passed**; ตรวจ shell/Python syntax ผ่าน และทดสอบสร้าง schema ใหม่บน MariaDB แยกได้สำเร็จ

กรณีสำคัญที่มี automated tests: หมุนไฟล์ DNS แล้วอ่านไฟล์ใหม่ตั้งแต่ต้น, DB เขียน DNS ไม่สำเร็จแล้ว buffer ไม่หาย, collector หยุดแล้วตัวหลักคืน nonzero, telemetry แยก idle/stale, FAS context ถูกแก้หรือใช้ nonce ซ้ำ, pending session และ MAC ซ้อน, audit ล้มเหลว, log attribution ที่ไม่แน่ชัด, การลบ archive ตามอายุ และ DNS query/answer แยกกัน ดู `tests/test_logger.py`, `tests/test_telemetry.py`, `tests/test_fas_flow.py`, `tests/test_reconcile_pending.py`, `tests/test_logs_search.py` และ `tests/test_purge_and_export.py`

ทดสอบ validation ของ installer โดยไม่ติดตั้งจริง:

```bash
bash install.sh --dry-run -y --retention-days 30
```

คำสั่งนี้ **ต้องจบด้วย exit code ที่ไม่ใช่ศูนย์** และแจ้งว่าค่า retention ต่ำกว่า 90 วัน; อย่าใช้ผลจากข้อความอย่างเดียว ให้ตรวจ exit code ด้วย

## รายการตรวจรับบน Raspberry Pi จริง — ยังไม่ได้ทำในรอบนี้

ก่อนเริ่ม ให้สำรอง DB, raw logs, manifest และไฟล์ config; บันทึกเวอร์ชันระบบและเวลาทดสอบ ใช้ voucher/ลูกค้าทดสอบเท่านั้น ทดสอบการหยุดบริการ DB, หมุนไฟล์ และไฟดับเฉพาะช่วง maintenance ที่ผู้ดูแลอนุญาต เพราะอาจทำให้ลูกค้าใช้งานไม่ได้หรือหลักฐานช่วงนั้นขาด อย่าลบหรือแก้ raw log จริงเพื่อทดสอบ

1. **ติดตั้งและ schema:** บนเครื่องทดสอบใหม่ รัน installer ตาม topology จริงและตรวจบริการด้วย `systemctl status cafe-logger cafe-fas cafe-admin opennds cafe-reconcile.timer` ตรวจตาราง/คอลัมน์ใหม่ ได้แก่ `fas_context`, `voucher_reveal`, `pending_mac_claim`, `portal_session.state/authenticated_at`, `dns_log.event_kind`, `log_manifest.deletion_state` และ `conn_log.mac` ที่ยอมรับ `NULL`
2. **R01–R03 (เก็บ log ต่อเนื่อง):** มีทราฟฟิกทดสอบก่อน/หลัง logrotate ทั้งตอนเงียบและตอนมีทราฟฟิก ตรวจว่า DNS query หลังหมุนเข้า `dns_log` และ `/status` มี heartbeat ของ `dns`/`conn` ล่าสุด; ตรวจ `journalctl -u cafe-logger -n 100 --no-pager` ว่ามีข้อความเปิดไฟล์ใหม่ ใช้สถานการณ์ DB ไม่พร้อมแบบควบคุมเพื่อยืนยัน retry และตัวนับ dropped/log_gap; หยุด collector หรือ `conntrack` เฉพาะเครื่องทดสอบแล้วตรวจว่า service ออกผิดพลาดและ systemd เริ่มใหม่
3. **R04, R13 (ความครบและความหมายของ log):** สร้าง connection ขณะที่ ARP ไม่มี MAC แล้วตรวจว่าแถวยังมี IP และ MAC ว่าง; สร้าง DNS query ชื่อเดียวกันจากสองเครื่องพร้อมกัน ตรวจว่าแต่ละ query มี IP ถูกต้อง และ answer ไม่ถูกอ้างว่าเป็นของเครื่องใดโดยไม่มีหลักฐาน
4. **R07–R08 (FAS/openNDS จริง):** ใช้อุปกรณ์จริง login ผ่าน captive portal ตรวจลำดับ `pending` → openNDS อนุญาต → `authenticated` และตัวเลขหน้า Admin; ทดสอบ browser ไม่ตาม redirect, voucher หมดอายุ, nonce ใช้ซ้ำ, คำขอซ้อนจาก MAC เดียวกัน และ `ndsctl json` อ่านไม่ได้ ตรวจว่าไม่มี session ผีถูกนับออนไลน์ และ timer `cafe-reconcile.timer` ยังทำงาน
5. **R05–R06 (ผูกตัวตนและ retention):** ใช้ MAC เดิมกับ voucher สองใบในช่วงซ้อนกัน ตรวจ `/logs` และ export ว่าไม่แสดงเหตุการณ์หนึ่งเป็นลูกค้าสองคน; จำลองข้อมูลเก่าใน DB ทดสอบแยก ตรวจว่าข้อมูลตัวตนไม่ถูกล้างก่อน session/log ล่าสุดครบอายุ และคำขอลบรายคนใช้ cutoff เดียวกัน
6. **R09–R10 (ความลับและ audit):** ออก voucher ทดสอบ ตรวจ browser cookie ว่าไม่มี plaintext password; เปิดหน้าผลลัพธ์ได้ครั้งเดียวและหมดอายุ; จำลอง audit failure ในสภาพแวดล้อมทดสอบแล้วตรวจว่าการออก/ยกเลิก voucher และการเปิดเลขเต็ม/ค้นหา/export ไม่สำเร็จโดยไม่มี audit
7. **R11–R12 (archive):** ใช้ไฟล์จำลองใน environment ทดสอบ ตรวจผนึก, ตรวจ hash, บันทึก audit และสถานะ `deleted` เมื่อครบอายุ; ไฟล์ที่ถูกแก้ hash หรือหายโดยไม่ผ่านกระบวนการต้องถูกรายงานผิดปกติ ตรวจว่า installer ปฏิเสธ retention ต่ำกว่า 90 วันทั้งแบบถามตอบและ `-y`
8. **ความทนทาน:** รีบูต/จำลองไฟดับในช่วงทดสอบ ตรวจว่าบริการและ timer กลับมา, คิว RAM ที่ยังไม่เขียน DB มีข้อจำกัดตามด้านล่าง, ตรวจความต่อเนื่องของ `conn_log`/`dns_log` และบันทึกช่วงหลักฐานที่ขาดจริง

บันทึกผลพร้อม timestamp, เวอร์ชัน openNDS/dnsmasq/MariaDB, คำสั่งและผลลัพธ์ที่ไม่เปิดเผยข้อมูลลูกค้า ลงใน `docs/hardware-test-log.md`; รายการด้านบนยังถือว่า **ไม่ผ่านการยืนยัน** จนมีหลักฐานจาก Pi จริง

## ข้อจำกัดและเงื่อนไขก่อนนำไปใช้

- **ฐานข้อมูลที่ติดตั้งแล้วต้องมี migration แยก:** `sql/001_schema.sql` ใช้ `CREATE TABLE IF NOT EXISTS` จึงไม่เปลี่ยนคอลัมน์ในตารางเดิมโดยอัตโนมัติ โค้ดใหม่นี้อาศัยคอลัมน์/ตารางใหม่หลายจุด ห้ามนำโค้ดไปอัปเกรด Pi เดิมโดยเพียงรัน schema ซ้ำ ต้องทำและทดสอบ migration กับสำเนา DB พร้อมแผน rollback ก่อน deploy
- DNS/connection buffer อยู่ใน RAM: retry ได้เมื่อ DB กลับมา แต่ process crash หรือไฟดับก่อน flush ยังทำให้ข้อมูลค้างหายได้ เพดาน DNS คือ 20,000 รายการ และเมื่อเกินเพดานจะบันทึกช่องว่างใน journal/telemetry ไม่ได้กู้รายการที่ทิ้งกลับมา
- Heartbeat บอกว่าลูป collector ยังทำงาน ไม่ได้พิสูจน์ว่าครบทุก packet หรือเขียน DB สำเร็จเสมอ ต้องดู `written`, `dropped`, `last_error`, service journal และ DB ร่วมกัน; การหา MAC ไม่พบยังทำให้โยงตัวตนไม่ได้
- การยืนยัน pending พึ่งรูปแบบผล `ndsctl json` ของ openNDS ที่ติดตั้งจริง โดยเฉพาะ `state`, IP และ `session_start`; ต้องตรวจ JSON จริงและ timezone/เวลา session บน Pi ก่อนเชื่อถือผล หน้าทดสอบ Docker จำลอง gateway เท่านั้น
- DNS text log ไม่มี request ID ที่เชื่อถือได้สำหรับจับ query กับ answer เมื่อมีคำขอพร้อมกัน จึงเก็บแยกและไม่ควรใช้ answer เดี่ยว ๆ ระบุตัวบุคคล; DNS-over-HTTPS ที่ไม่ผ่าน dnsmasq จะไม่ปรากฏใน log นี้
- Hash chain ช่วย **ตรวจพบ** การเปลี่ยนแปลงตามขอบเขตที่ยังมี manifest/ฐานข้อมูลให้เทียบ ไม่ใช่หลักฐานยืนยันตัวบุคคลหรือการป้องกันการแก้ไขทุกกรณี การลบ archive ผูกกับงาน integrity และสิทธิ์ filesystem; ต้องเฝ้าความสำเร็จของ maintenance จริง
- เรื่อง network isolation, bypass, พฤติกรรม captive portal บนอุปกรณ์จริง, กฎหมาย/นโยบายข้อมูล และสำรองข้อมูลนอกเครื่อง ยังต้องตรวจแยกตามหัวข้อ S01–S05 และแผนทดสอบเดิม ไม่ถือว่าการแก้ R01–R13 ปิดความเสี่ยงเหล่านั้น
