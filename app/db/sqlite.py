from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "source.db"

def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                filename TEXT,
                file_type TEXT,
                status TEXT,
                created_at TEXT
            )
        """)

def insert_source(source_id: str, filename: str, file_type: str, status: str, created_at: str) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            INSERT INTO sources (id, filename, file_type, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (source_id, filename, file_type, status, created_at))