import sqlite3
from app.config import DATABASE_URL

def get_conn():
    path = DATABASE_URL.replace("sqlite:///", "")
    return sqlite3.connect(path, check_same_thread=False)

def init_db():
    conn = get_conn()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        message_id TEXT PRIMARY KEY,
        from_msisdn TEXT NOT NULL,
        to_msisdn TEXT NOT NULL,
        ts TEXT NOT NULL,
        text TEXT,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()
