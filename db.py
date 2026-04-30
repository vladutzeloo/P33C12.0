import sqlite3
import os
from schemas import NIMUsageLog

DB_PATH = os.getenv("DB_PATH", "p33c1.db")


def init_db():
    """Create tables if not exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            latency_sec REAL,
            endpoint TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Initialized p33c1.db")


def log_usage(entry: NIMUsageLog):
    """Log NIM API call to SQLite."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO api_usage (model, input_tokens, output_tokens, total_tokens, latency_sec, endpoint, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        entry.model,
        entry.input_tokens,
        entry.output_tokens,
        entry.total_tokens,
        entry.latency_sec,
        entry.endpoint,
        entry.timestamp.isoformat(),
    ))
    conn.commit()
    conn.close()


def get_usage_summary() -> list[dict]:
    """Return total tokens per model."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT model, SUM(input_tokens), SUM(output_tokens), SUM(total_tokens), COUNT(*)
        FROM api_usage
        GROUP BY model
    """)
    rows = c.fetchall()
    conn.close()
    return [
        {"model": r[0], "input": r[1], "output": r[2], "total": r[3], "calls": r[4]}
        for r in rows
    ]
