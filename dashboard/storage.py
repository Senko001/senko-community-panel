import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path("dashboard/dashboard.db")

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            moderator_id TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS mod_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            target_user_id TEXT NOT NULL,
            moderator_user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            reason TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def add_warn(guild_id: str, user_id: str, moderator_id: str, reason: str, created_at: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO warns (guild_id, user_id, moderator_id, reason, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (guild_id, user_id, moderator_id, reason, created_at))
    conn.commit()
    conn.close()

def get_warns_for_user(guild_id: str, user_id: str) -> list[dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM warns
        WHERE guild_id = ? AND user_id = ?
        ORDER BY id DESC
    """, (guild_id, user_id))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def delete_warn(warn_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM warns WHERE id = ?", (warn_id,))
    conn.commit()
    conn.close()

def add_mod_log(
    guild_id: str,
    target_user_id: str,
    moderator_user_id: str,
    action: str,
    reason: str | None,
    metadata: str | None,
    created_at: str,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO mod_logs (guild_id, target_user_id, moderator_user_id, action, reason, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (guild_id, target_user_id, moderator_user_id, action, reason, metadata, created_at))
    conn.commit()
    conn.close()

def get_logs_for_guild(guild_id: str, limit: int = 50) -> list[dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM mod_logs
        WHERE guild_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (guild_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
