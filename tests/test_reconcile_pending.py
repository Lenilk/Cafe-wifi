"""Gateway confirmation must match state, IP, and a new gateway session."""
from datetime import datetime, timedelta

from tools.reconcile_pending import confirmed_since


def test_confirmed_since_requires_fresh_gateway_session():
    now = datetime.now().replace(microsecond=0)
    client = dict(state="Authenticated", ip="10.10.0.105",
                  session_start=str(int(now.timestamp())))
    assert confirmed_since(client, "10.10.0.105", now)
    assert not confirmed_since(client, "10.10.0.106", now)
    assert not confirmed_since({**client, "state": "Preauthenticated"}, "10.10.0.105", now)
    assert not confirmed_since({**client, "session_start": str(int((now - timedelta(minutes=5)).timestamp()))},
                               "10.10.0.105", now)
    assert not confirmed_since({**client, "session_start": None}, "10.10.0.105", now)
