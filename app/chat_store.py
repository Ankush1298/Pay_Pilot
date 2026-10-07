"""Persistence for chat conversations, messages and the per-conversation context (MySQL via app.db).

Every query is scoped by user_id, so one user can never read or edit another user's chats.
"""
from __future__ import annotations

import json
import secrets
import time

from sqlalchemy import delete as sa_delete, desc, insert, select, update

from .db import conversations, engine, messages as msg_t


def _conv(row) -> dict:
    return {"id": row["id"], "title": row["title"], "context": json.loads(row["context"]),
            "created": row["created"], "updated": row["updated"]}


def create(user_id: str, title: str = "New chat") -> dict:
    cid, now = "cv_" + secrets.token_hex(6), time.time()
    with engine.begin() as c:
        c.execute(insert(conversations).values(id=cid, user_id=user_id, title=title, context="{}", created=now, updated=now))
    return get(user_id, cid)  # type: ignore[return-value]


def get(user_id: str, cid: str) -> dict | None:
    with engine.connect() as c:
        row = c.execute(select(conversations).where(conversations.c.id == cid, conversations.c.user_id == user_id)).mappings().first()
    return _conv(row) if row else None


def list_for(user_id: str, limit: int = 50) -> list[dict]:
    with engine.connect() as c:
        rows = c.execute(select(conversations).where(conversations.c.user_id == user_id)
                         .order_by(desc(conversations.c.updated)).limit(limit)).mappings().all()
    return [_conv(r) for r in rows]


def add_message(user_id: str, cid: str, role: str, content: str, data: dict | None = None) -> None:
    now = time.time()
    with engine.begin() as c:
        c.execute(insert(msg_t).values(conversation_id=cid, user_id=user_id, role=role, content=content,
                                          data=json.dumps(data or {}), ts=now))
        c.execute(update(conversations).where(conversations.c.id == cid, conversations.c.user_id == user_id).values(updated=now))


def messages(user_id: str, cid: str, limit: int = 200) -> list[dict]:
    with engine.connect() as c:
        rows = c.execute(select(msg_t).where(msg_t.c.conversation_id == cid, msg_t.c.user_id == user_id)
                         .order_by(desc(msg_t.c.id)).limit(limit)).mappings().all()
    return [{"id": r["id"], "role": r["role"], "content": r["content"], "ts": r["ts"], **json.loads(r["data"])}
            for r in reversed(rows)]


def set_context(user_id: str, cid: str, ctx: dict) -> None:
    with engine.begin() as c:
        c.execute(update(conversations).where(conversations.c.id == cid, conversations.c.user_id == user_id)
                  .values(context=json.dumps(ctx), updated=time.time()))


def set_title(user_id: str, cid: str, title: str) -> None:
    with engine.begin() as c:
        c.execute(update(conversations).where(conversations.c.id == cid, conversations.c.user_id == user_id,
                                              conversations.c.title == "New chat").values(title=title[:60]))


def delete(user_id: str, cid: str) -> bool:
    with engine.begin() as c:
        c.execute(sa_delete(msg_t).where(msg_t.c.conversation_id == cid, msg_t.c.user_id == user_id))
        n = c.execute(sa_delete(conversations).where(conversations.c.id == cid, conversations.c.user_id == user_id)).rowcount
    return bool(n)

