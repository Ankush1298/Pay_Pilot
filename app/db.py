"""Database: MySQL in real use (PAYPILOT_DATABASE_URL), in-memory SQLite for the test suite.

Tables hold the accounts, sessions, device tokens, per-user wallet/policy snapshots and chat history.
Session and device tokens are stored only as SHA-256 hashes, so a database leak cannot be replayed as cookies.
"""
from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.pool import StaticPool

from . import config

BigText = Text().with_variant(LONGTEXT(), "mysql")      # snapshots grow with the audit log

metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", String(40), primary_key=True),
    Column("username", String(40), nullable=False),
    Column("username_key", String(40), nullable=False, unique=True),      # lower-cased: names are unique ignoring case
    Column("created", Float, nullable=False),
)

sessions = Table(
    "sessions", metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("id", String(24), nullable=False, unique=True),
    Column("user_id", String(40), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("device_id", String(24), nullable=False),
    Column("status", String(12), nullable=False),
    Column("exp", Float, nullable=False, index=True),
    Column("ip", String(64)),
    Column("ua", String(200)),
    Column("created", Float, nullable=False),
)

device_tokens = Table(
    "device_tokens", metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("user_id", String(40), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("device_id", String(24), nullable=False),
)

gateways = Table(
    "gateways", metadata,
    Column("user_id", String(40), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("state", BigText, nullable=False),
    Column("ledger", BigText, nullable=False),
    Column("updated", Float, nullable=False),
)

conversations = Table(
    "conversations", metadata,
    Column("id", String(24), primary_key=True),
    Column("user_id", String(40), nullable=False),
    Column("title", String(80), nullable=False, default="New chat"),
    Column("context", Text, nullable=False),
    Column("created", Float, nullable=False),
    Column("updated", Float, nullable=False),
    Index("idx_conv_user", "user_id", "updated"),
)

messages = Table(
    "messages", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("conversation_id", String(24), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("user_id", String(40), nullable=False),
    Column("role", String(8), nullable=False),
    Column("content", BigText, nullable=False),
    Column("data", BigText, nullable=False),
    Column("ts", Float, nullable=False),
)


def _make_engine():
    url = config.DATABASE_URL
    if url.startswith("sqlite"):
        kw = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url.endswith("://"):
            kw["poolclass"] = StaticPool                      # one shared in-memory database for every thread
        return create_engine(url, **kw)
    return create_engine(url, pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800)


engine = _make_engine()
metadata.create_all(engine)
