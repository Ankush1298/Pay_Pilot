"""SQLite persistence for chat conversations, messages and the per-conversation context.

Every query is scoped by user_id, so one user can never read or edit another user's chats.
Set PAYPILOT_DB to a file path (default ./paypilot.db); tests use ':memory:'.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time

from . import config

_lock = threading.Lock()
_db = sqlite3.connect(config.DB_PATH, check_same_thread=False)
_db.row_factory = sqlite3.Row
_db.executescript("""
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, title TEXT NOT NULL DEFAULT 'New chat',
  context TEXT NOT NULL DEFAULT '{}', created REAL NOT NULL, updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, updated DESC);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL, role TEXT NOT NULL CHECK (role IN ('user','agent')), content TEXT NOT NULL,
  data TEXT NOT NULL DEFAULT '{}', ts REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id, id);
PRAGMA foreign_keys = ON;
""")


def _conv(row) -> dict:
    return {"id": row["id"], "title": row["title"], "context": json.loads(row["context"]),
            "created": row["created"], "updated": row["updated"]}


def create(user_id: str, title: str = "New chat") -> dict:
    cid, now = "cv_" + secrets.token_hex(6), time.time()
    with _lock, _db:
        _db.execute("INSERT INTO conversations(id,user_id,title,created,updated) VALUES (?,?,?,?,?)",
                    (cid, user_id, title, now, now))
    return get(user_id, cid)  # type: ignore[return-value]


def get(user_id: str, cid: str) -> dict | None:
    with _lock:
        row = _db.execute("SELECT * FROM conversations WHERE id=? AND user_id=?", (cid, user_id)).fetchone()
    return _conv(row) if row else None


def list_for(user_id: str, limit: int = 50) -> list[dict]:
    with _lock:
        rows = _db.execute("SELECT * FROM conversations WHERE user_id=? ORDER BY updated DESC LIMIT ?",
                           (user_id, limit)).fetchall()
    return [_conv(r) for r in rows]


def add_message(user_id: str, cid: str, role: str, content: str, data: dict | None = None) -> None:
    now = time.time()
    with _lock, _db:
        _db.execute("INSERT INTO messages(conversation_id,user_id,role,content,data,ts) VALUES (?,?,?,?,?,?)",
                    (cid, user_id, role, content, json.dumps(data or {}), now))
        _db.execute("UPDATE conversations SET updated=? WHERE id=? AND user_id=?", (now, cid, user_id))


def messages(user_id: str, cid: str, limit: int = 200) -> list[dict]:
    with _lock:
        rows = _db.execute("SELECT * FROM (SELECT * FROM messages WHERE conversation_id=? AND user_id=? "
                           "ORDER BY id DESC LIMIT ?) ORDER BY id", (cid, user_id, limit)).fetchall()
    return [{"id": r["id"], "role": r["role"], "content": r["content"], "ts": r["ts"], **json.loads(r["data"])}
            for r in rows]


def set_context(user_id: str, cid: str, ctx: dict) -> None:
    with _lock, _db:
        _db.execute("UPDATE conversations SET context=?, updated=? WHERE id=? AND user_id=?",
                    (json.dumps(ctx), time.time(), cid, user_id))


def set_title(user_id: str, cid: str, title: str) -> None:
    with _lock, _db:
        _db.execute("UPDATE conversations SET title=? WHERE id=? AND user_id=? AND title='New chat'",
                    (title[:60], cid, user_id))


def delete(user_id: str, cid: str) -> bool:
    with _lock, _db:
        n = _db.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (cid, user_id)).rowcount
        _db.execute("DELETE FROM messages WHERE conversation_id=? AND user_id=?", (cid, user_id))
    return bool(n)
