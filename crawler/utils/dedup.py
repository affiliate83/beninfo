import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "dedup.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS seen (
            source_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            wp_post_id INTEGER,
            detail_fetched INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )"""
    )
    try:
        conn.execute("ALTER TABLE seen ADD COLUMN detail_fetched INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    return conn


def is_seen(source_id: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM seen WHERE source_id = ?", (source_id,)
        ).fetchone()
    return row is not None


def mark_seen(source_id: str, source_type: str, wp_post_id: int = None):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO seen (source_id, source_type, wp_post_id) VALUES (?, ?, ?)",
            (source_id, source_type, wp_post_id),
        )
        conn.commit()


def get_pending_detail(source_type: str, limit: int = 100) -> list[tuple]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT source_id, wp_post_id FROM seen WHERE source_type=? AND detail_fetched=0 LIMIT ?",
            (source_type, limit),
        ).fetchall()
    return rows


def mark_detail_fetched(source_id: str):
    with _conn() as conn:
        conn.execute(
            "UPDATE seen SET detail_fetched=1 WHERE source_id=?",
            (source_id,),
        )
        conn.commit()