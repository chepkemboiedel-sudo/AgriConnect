"""SQLite data layer.

Every table carries a ``tenant_id``. The access helpers always filter by
tenant, which is how AgriConnect enforces tenant isolation in this slice.
(The production target is PostgreSQL + pgvector; the schema maps 1:1.)
"""
from __future__ import annotations
import json
import sqlite3
import time
from typing import Any, Optional

from . import config


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id  TEXT NOT NULL,
    title      TEXT NOT NULL,
    source     TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL,
    document_id INTEGER NOT NULL,
    ord         INTEGER NOT NULL,
    text        TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL,
    sku         TEXT NOT NULL,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price       REAL NOT NULL,
    stock       INTEGER NOT NULL,
    unit        TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'bot',   -- bot | waiting_staff | staff | closed
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    tenant_id       TEXT NOT NULL,
    role            TEXT NOT NULL,              -- customer | assistant | staff | system
    text            TEXT NOT NULL,
    meta            TEXT,                        -- JSON: tool, sources, abstained, counts
    created_at      REAL NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS handoffs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    tenant_id       TEXT NOT NULL,
    reason          TEXT NOT NULL,
    created_at      REAL NOT NULL,
    resolved        INTEGER NOT NULL DEFAULT 0
);
"""


def init_db(reset: bool = False) -> None:
    conn = get_conn()
    try:
        if reset:
            for t in ("handoffs", "messages", "conversations", "chunks",
                      "documents", "products", "tenants"):
                conn.execute(f"DROP TABLE IF EXISTS {t}")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Tenant boundary
# ----------------------------------------------------------------------
def tenant_exists(conn: sqlite3.Connection, tenant_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    return row is not None


def list_tenants() -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute("SELECT id, name FROM tenants ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Conversations & messages (always tenant-scoped)
# ----------------------------------------------------------------------
def create_conversation(tenant_id: str, customer_name: str) -> int:
    now = time.time()
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO conversations (tenant_id, customer_name, status, created_at, updated_at)"
            " VALUES (?, ?, 'bot', ?, ?)",
            (tenant_id, customer_name, now, now),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_conversation(tenant_id: str, conversation_id: int) -> Optional[dict]:
    """Return the conversation ONLY if it belongs to tenant_id (isolation)."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ? AND tenant_id = ?",
            (conversation_id, tenant_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_conversation_status(tenant_id: str, conversation_id: int, status: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE conversations SET status = ?, updated_at = ? WHERE id = ? AND tenant_id = ?",
            (status, time.time(), conversation_id, tenant_id),
        )
        conn.commit()
    finally:
        conn.close()


def add_message(tenant_id: str, conversation_id: int, role: str, text: str,
                meta: Optional[dict] = None) -> dict:
    now = time.time()
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, tenant_id, role, text, meta, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, tenant_id, role, text,
             json.dumps(meta) if meta else None, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ? AND tenant_id = ?",
            (now, conversation_id, tenant_id),
        )
        conn.commit()
        return {
            "id": int(cur.lastrowid), "conversation_id": conversation_id,
            "role": role, "text": text, "meta": meta or {}, "created_at": now,
        }
    finally:
        conn.close()


def get_messages(tenant_id: str, conversation_id: int) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? AND tenant_id = ? ORDER BY id",
            (conversation_id, tenant_id),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["meta"] = json.loads(d["meta"]) if d["meta"] else {}
            out.append(d)
        return out
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Products (tenant-scoped catalog lookup)
# ----------------------------------------------------------------------
def search_products(tenant_id: str, terms: list[str], limit: int = 5) -> list[dict]:
    if not terms:
        return []
    conn = get_conn()
    try:
        clause = " OR ".join(["LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?"] * len(terms))
        params: list[Any] = [tenant_id]
        for t in terms:
            like = f"%{t.lower()}%"
            params.extend([like, like, like])
        rows = conn.execute(
            f"SELECT * FROM products WHERE tenant_id = ? AND ({clause}) LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def all_products(tenant_id: str) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM products WHERE tenant_id = ?", (tenant_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_products(tenant_id: str) -> int:
    conn = get_conn()
    try:
        return int(conn.execute(
            "SELECT COUNT(*) FROM products WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()[0])
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Handoffs / staff inbox
# ----------------------------------------------------------------------
def create_handoff(tenant_id: str, conversation_id: int, reason: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO handoffs (conversation_id, tenant_id, reason, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, tenant_id, reason, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def inbox_conversations(tenant_id: str) -> list[dict]:
    """Conversations that need or have staff attention, with context preview."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE tenant_id = ? AND status IN ('waiting_staff','staff')"
            " ORDER BY updated_at DESC",
            (tenant_id,),
        ).fetchall()
        out = []
        for r in rows:
            c = dict(r)
            last = conn.execute(
                "SELECT text, role FROM messages WHERE conversation_id = ? AND tenant_id = ?"
                " ORDER BY id DESC LIMIT 1",
                (c["id"], tenant_id),
            ).fetchone()
            ho = conn.execute(
                "SELECT reason FROM handoffs WHERE conversation_id = ? AND tenant_id = ?"
                " ORDER BY id DESC LIMIT 1",
                (c["id"], tenant_id),
            ).fetchone()
            c["last_message"] = last["text"] if last else ""
            c["last_role"] = last["role"] if last else ""
            c["reason"] = ho["reason"] if ho else ""
            out.append(c)
        return out
    finally:
        conn.close()
