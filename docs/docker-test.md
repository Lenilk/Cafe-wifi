# ทดสอบด้วย Docker Compose

ชุดนี้ใช้เฉพาะข้อมูลและกุญแจปลอมใน `docker/test.env` ทุกบริการอยู่ในเครือข่าย Compose แยกกัน ฐานข้อมูลไม่เปิดพอร์ตออกโฮสต์ และมีเพียง proxy ที่เปิด `127.0.0.1:8080` (FAS, HTTP) กับ `127.0.0.1:8443` (Admin, HTTPS) ห้ามนำชุดนี้ไปใช้กับข้อมูลจริง

ต้องมี Docker Engine และ Compose plugin ทำงานก่อน (`docker compose version` และ `docker info`) คำสั่งด้านล่างให้รันจากรากรีโป หากมีคำสั่ง standalone เท่านั้น ให้แทน `docker compose` ด้วย `docker-compose`

```bash
docker compose config --quiet
docker compose build admin fas tests jobs dns-collector
docker compose up -d db admin fas proxy
docker compose ps
curl -fsS http://127.0.0.1:8080/health
curl -kfsS https://localhost:8443/health
```

เปิด `https://localhost:8443/setup` ใน browser และใช้ setup token `docker-test-setup-token` เพื่อสร้างบัญชีทดสอบครั้งแรก ใบรับรอง HTTPS ออกภายใน container และ browser จะเตือนว่า CA ยังไม่น่าเชื่อถือ; ใช้เฉพาะการทดสอบ ไม่ต้องติดตั้ง CA ลงโฮสต์ FAS เปิดที่ `http://127.0.0.1:8080/login` และการทดสอบ flow ใช้ gateway จำลองใน `tests/test_fas_flow.py` ไม่ได้รัน openNDS จริง

## Pytest และงานแยก

```bash
docker compose run --rm tests
docker compose run --rm jobs python -m tools.purge_old_data
docker compose run --rm jobs python -m tools.export_evidence --from 2000-01-01 --to 2100-01-01 --out /var/log/cafe-wifi/exports
docker compose run --rm jobs python -m tools.backup_db
docker compose run --rm jobs python -m logger.integrity
docker compose run --rm jobs ls -lh /var/log/cafe-wifi/exports /var/backups/cafe-wifi
```

`purge` ลบเฉพาะข้อมูลเก่าตามระยะเก็บในฐานข้อมูลทดสอบ `export` เขียน CSV และ manifest ลง volume `test-logs`; `backup` เขียน `.sql.gz` ลง volume `test-backups` ส่วน `integrity` ผนึกและตรวจไฟล์ใน `test-logs/archive` หากต้องการเห็นรายการ hash ให้สร้างไฟล์ log ตัวอย่างใน volume ก่อนเรียกงาน:

```bash
docker compose run --rm jobs sh -c 'mkdir -p /var/log/cafe-wifi/archive && printf "docker test log\n" > /var/log/cafe-wifi/archive/example.log-2026-09-29'
docker compose run --rm jobs python -m logger.integrity
```

## DNS collector

Collector สร้าง `dnsmasq.log` ว่างก่อนเปิดอ่าน และข้ามเนื้อหาที่อยู่ในไฟล์ก่อนเริ่ม จึงต้องรอให้สถานะเป็น `healthy` ใน `docker compose ps` แล้วค่อยเพิ่ม log:

```bash
docker compose --profile dns up -d dns-collector
docker compose ps dns-collector
docker compose exec -T dns-collector sh -c 'ts="$(date "+%b %e %T")"; printf "%s dnsmasq[1234]: query[A] example.test from 10.10.0.105\n%s dnsmasq[1234]: reply example.test is 192.0.2.10\n" "$ts" "$ts" >> /var/log/cafe-wifi/dnsmasq.log'
```

รอประมาณ 6 วินาทีให้ batch flush (ค่าเริ่มต้น 5 วินาที) แล้วดูแถวในฐานข้อมูลและตารางสำคัญ:

```bash
docker compose exec -T db sh -lc 'MYSQL_PWD="$MARIADB_PASSWORD" mariadb -u "$MARIADB_USER" "$MARIADB_DATABASE" -e "SHOW TABLES; SELECT ts, client_ip, mac, qname, qtype, answer FROM dns_log ORDER BY ts DESC LIMIT 5; SELECT filename, sha256 FROM log_manifest ORDER BY id DESC LIMIT 5;"'
```

ค่า `mac` ของ DNS ตัวอย่างอาจเป็น `NULL` เพราะ container ไม่มี ARP ของ gateway จริง นั่นไม่กระทบการตรวจว่า collector เขียน DNS query ลง DB ได้

## หยุดและล้างข้อมูลทดสอบ

```bash
docker compose --profile dns down
docker compose --profile dns down --volumes
```

คำสั่งแรกหยุดและลบ container แต่เก็บข้อมูลไว้ คำสั่งที่สองลบ named volumes ของ Compose project `cafe-wifi-docker-test` รวม DB, log/export, backup, setup token และใบรับรองทดสอบเท่านั้น ข้อมูลใน volumes เหล่านี้กู้คืนไม่ได้ คำสั่งนี้ไม่แตะฐานข้อมูลหรือไฟล์บนโฮสต์นอกชุดทดสอบ

Compose นี้ตรวจบริการแอปและฐานข้อมูลได้ แต่ไม่จำลอง gateway, openNDS, nftables, conntrack, DHCP, AP isolation หรือฮาร์ดแวร์ Raspberry Pi จริง
