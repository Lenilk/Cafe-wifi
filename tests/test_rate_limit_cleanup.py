"""การเก็บกวาด rate limit ต้องไม่เปลี่ยนเพดานและช่วงเวลาล็อกอิน"""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from admin import app as admin_app
from fas import app as fas_app


@pytest.mark.parametrize("module", [admin_app, fas_app])
def test_expired_buckets_are_removed_and_current_window_is_preserved(monkeypatch, module):
    clock = [1000.0]
    monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: clock[0]))
    monkeypatch.setattr(module, "_last_attempt_cleanup", 1000.0)
    module._attempts.clear()
    try:
        module._attempts.update(stale=[999.0], recent=[1500.0])
        clock[0] = 1600.0
        assert not module.rate_limited("new")
        assert "stale" not in module._attempts
        assert "new" not in module._attempts
        assert module._attempts["recent"] == [1500.0]

        for _ in range(module.MAX_ATTEMPTS):
            module.record_attempt("new")
        assert module.rate_limited("new")
        clock[0] += module.WINDOW_SEC
        assert not module.rate_limited("new")
        assert "new" not in module._attempts
    finally:
        module._attempts.clear()


@pytest.mark.parametrize("module", [admin_app, fas_app])
def test_concurrent_attempts_are_recorded_without_losing_hits(monkeypatch, module):
    monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: 1000.0))
    monkeypatch.setattr(module, "_last_attempt_cleanup", 0.0)
    module._attempts.clear()
    try:
        def attempt(_):
            module.rate_limited("shared")
            module.record_attempt("shared")

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(attempt, range(40)))
        assert len(module._attempts["shared"]) == 40
    finally:
        module._attempts.clear()
