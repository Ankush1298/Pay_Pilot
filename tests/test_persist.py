"""Accounts live in the database: they survive losing the in-memory caches (a restart)."""
import pytest

from app import auth, persist, registry
from app.db import engine, sessions


def test_account_and_wallet_state_survive_a_restart():
    uid = auth.create_user("persist-test-user")
    with registry.REG.use(uid) as gw:
        gw.st.credentials["cred1"] = {"id": "cred1", "pub_key_bytes": b"\x01\x02"}
    token, sid = auth.new_session(uid, "dev_x", "127.0.0.1", "ua")

    registry._gateways.pop(uid); persist._last.clear()                      # a restart empties the caches
    with registry.REG.use(uid) as again:
        assert again.st.credentials["cred1"]["pub_key_bytes"] == b"\x01\x02"
    assert auth.get_user_by_id(uid)["username"] == "persist-test-user"
    assert [s["id"] for s in auth.list_sessions(uid)] == [sid]


def test_tokens_are_stored_hashed_and_names_are_unique_ignoring_case():
    uid = auth.create_user("HashCheck")
    token, _ = auth.new_session(uid, "dev_y", "127.0.0.1", "ua")
    with engine.connect() as c:
        stored = [r[0] for r in c.execute(sessions.select().with_only_columns(sessions.c.token_hash))]
    assert token not in stored and auth._h(token) in stored
    with pytest.raises(auth.AuthError) as e:
        auth.create_user("hASHcHECK")
    assert e.value.status_code == 409
