"""R2-06: log ต้องไม่หายเมื่อ cafe-logger ถูก restart/reboot"""
import os
import threading
import time

import pytest

from logger import dns_collector, run_all
from logger.dns_collector import load_offset, resume_position, save_offset
from logger.telemetry import CollectorTelemetry


def _q(n: int) -> str:
    return f"Sep 30 10:00:{n:02d} dnsmasq[1]: query[A] host{n}.example from 10.10.0.5\n"


# ---------- resume_position / offset state ----------

def test_first_run_starts_at_end_of_file():
    assert resume_position(None, inode=7, size=500) == (500, None)


def test_same_inode_resumes_from_saved_offset():
    assert resume_position((7, 120), inode=7, size=500) == (120, None)


def test_rotated_while_down_reads_new_file_from_start_and_reports_gap():
    offset, gap = resume_position((7, 120), inode=8, size=500)
    assert offset == 0 and "หมุน" in gap


def test_truncated_file_reads_from_start_and_reports_gap():
    offset, gap = resume_position((7, 900), inode=7, size=500)
    assert offset == 0 and gap


def test_offset_roundtrip_and_corrupt_state(tmp_path):
    path = str(tmp_path / "state.json")
    assert load_offset(path) is None
    save_offset(path, 7, 120)
    assert load_offset(path) == (7, 120)
    (tmp_path / "state.json").write_text("{not json", encoding="utf-8")
    assert load_offset(path) is None


def test_previous_heartbeat_is_read_before_overwrite(tmp_path):
    t = CollectorTelemetry("conn", tmp_path)
    assert t.previous_heartbeat() is None
    t.heartbeat(force=True)
    assert CollectorTelemetry("conn", tmp_path).previous_heartbeat()


# ---------- dns_collector.run_forever ----------

@pytest.fixture
def dns_env(tmp_path, monkeypatch):
    inserted: list[str] = []
    gaps: list[str] = []
    monkeypatch.setattr(dns_collector, "insert_dns_rows",
                        lambda rows, cache, on_unmapped=None:
                        inserted.extend(r["qname"] for r in rows) or len(rows))
    monkeypatch.setattr(dns_collector, "_record_gap", gaps.append)
    log_path = tmp_path / "dnsmasq.log"
    log_path.write_text("", encoding="utf-8")
    return log_path, inserted, gaps


def _run(log_path, stop, **kw):
    t = threading.Thread(target=dns_collector.run_forever, args=(str(log_path),),
                         kwargs=dict(stop_event=stop, **kw), daemon=True)
    t.start()
    return t


def _wait_for(cond, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return
        time.sleep(0.05)
    raise AssertionError("รอเกินเวลา")


def _append(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def test_stop_flushes_buffer_before_exit(dns_env):
    log_path, inserted, _ = dns_env
    stop = threading.Event()
    t = _run(log_path, stop, batch_size=1000, flush_interval=3600)
    time.sleep(0.2)
    _append(log_path, _q(1) + _q(2))
    time.sleep(0.8)
    assert inserted == []  # ยังค้างใน buffer (batch ใหญ่ + flush_interval ยาว)
    stop.set()
    t.join(timeout=5)
    assert not t.is_alive()
    assert inserted == ["host1.example", "host2.example"]


def test_lines_written_while_down_are_read_after_restart(dns_env):
    log_path, inserted, gaps = dns_env
    stop = threading.Event()
    t = _run(log_path, stop, batch_size=1)
    time.sleep(0.2)
    _append(log_path, _q(1))
    _wait_for(lambda: inserted == ["host1.example"])
    stop.set()
    t.join(timeout=5)

    _append(log_path, _q(2) + _q(3))  # dnsmasq เขียนระหว่าง logger ดับ

    stop = threading.Event()
    t = _run(log_path, stop, batch_size=1)
    _wait_for(lambda: len(inserted) == 3)
    stop.set()
    t.join(timeout=5)
    assert inserted == ["host1.example", "host2.example", "host3.example"]
    assert gaps == []


def test_partial_line_is_not_parsed_until_complete(dns_env):
    log_path, inserted, _ = dns_env
    stop = threading.Event()
    t = _run(log_path, stop, batch_size=1)
    time.sleep(0.2)
    line = _q(4)
    _append(log_path, line[:30])
    time.sleep(0.8)
    _append(log_path, line[30:])
    _wait_for(lambda: inserted == ["host4.example"])
    stop.set()
    t.join(timeout=5)


def test_rotation_while_down_is_recorded_as_gap(dns_env):
    log_path, inserted, gaps = dns_env
    stop = threading.Event()
    t = _run(log_path, stop, batch_size=1)
    time.sleep(0.2)
    stop.set()
    t.join(timeout=5)

    os.rename(log_path, str(log_path) + ".1")
    log_path.write_text(_q(5), encoding="utf-8")

    stop = threading.Event()
    t = _run(log_path, stop, batch_size=1)
    _wait_for(lambda: inserted == ["host5.example"])
    stop.set()
    t.join(timeout=5)
    assert len(gaps) == 1


# ---------- run_all.main ----------

def test_main_lets_both_collectors_finish_on_sigterm(monkeypatch, tmp_path):
    finished: list[str] = []

    def fake(name):
        def run(*args, stop_event):
            stop_event.wait()
            time.sleep(0.2)  # จำลองการ flush หลังได้สัญญาณ
            finished.append(name)
        return run

    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setattr(run_all.conn_collector, "run_forever", fake("conn"))
    monkeypatch.setattr(run_all.dns_collector, "run_forever", fake("dns"))
    monkeypatch.setattr(run_all, "_stop", threading.Event())
    monkeypatch.setattr(run_all.signal, "signal", lambda *a: None)  # ไม่ยุ่ง handler ของ pytest
    threading.Timer(0.3, run_all._handle_signal, args=(15, None)).start()

    assert run_all.main() == 0
    assert sorted(finished) == ["conn", "dns"]


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_main_stops_the_other_collector_when_one_dies(monkeypatch, tmp_path):
    finished: list[str] = []

    def dies(*args, stop_event):
        raise RuntimeError("conntrack หยุดทำงาน")

    def survives(*args, stop_event):
        stop_event.wait()
        finished.append("dns")

    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setattr(run_all.conn_collector, "run_forever", dies)
    monkeypatch.setattr(run_all.dns_collector, "run_forever", survives)
    monkeypatch.setattr(run_all, "_stop", threading.Event())
    monkeypatch.setattr(run_all.signal, "signal", lambda *a: None)  # ไม่ยุ่ง handler ของ pytest

    assert run_all.main() == 1
    assert finished == ["dns"]
