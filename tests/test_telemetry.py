from datetime import datetime, timedelta

from logger.telemetry import CollectorTelemetry, read_collector_status


def test_collector_status_distinguishes_idle_from_stopped(tmp_path):
    t = CollectorTelemetry("dns", tmp_path)
    t.heartbeat(force=True)
    current = read_collector_status(tmp_path)
    assert current["dns"]["healthy"] is True
    assert current["dns"]["written"] == 0  # ไม่มีทราฟฟิกยังถือว่า collector คืบหน้า
    assert current["conn"]["healthy"] is False

    stale = read_collector_status(tmp_path, now=datetime.now() + timedelta(seconds=30))
    assert stale["dns"]["healthy"] is False


def test_collector_counts_received_written_dropped_and_unmapped(tmp_path):
    t = CollectorTelemetry("conn", tmp_path)
    t.event()
    t.write(1)
    t.drop(2)
    t.missing_mac(1)
    t.heartbeat(force=True)
    status = read_collector_status(tmp_path)["conn"]
    assert (status["received"], status["written"], status["dropped"], status["unmapped"]) == (1, 1, 2, 1)
    assert status["last_write_at"]
    assert "ทิ้ง" in status["last_error"]
