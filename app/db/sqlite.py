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
                error TEXT,
                created_at TEXT
            )
        """)

def insert_source(source_id: str, filename: str, file_type: str, status: str, created_at: str) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            INSERT INTO sources (id, filename, file_type, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (source_id, filename, file_type, status, created_at))


def update_source_status(source_id: str, status: str, error: str | None = None) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "UPDATE sources SET status = ?, error = ? WHERE id = ?",
            (status, error, source_id),
        )
# No input, output is list of dicts with keys: id, filename, file_type, status, error, created_at
# 1. Connect to sql lite  using DB_PATH 
# 2. use connection.row_factory = sqlite3.Row to get rows as dicts, without sqlite3.Row, the rows will be tuples and we will have to manually convert them to dicts with column names 
# 3. Execute the query "SELECT * FROM sources" to get all rows from the sources table
def list_sources() -> list[dict]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row # every row is type Row, which is like dict
        rows = connection.execute("SELECT * FROM sources ORDER BY created_at DESC").fetchall() # rows is list of Row objects
        return [dict(row) for row in rows] # convert each Row into dict, and return list of dict

def get_source(source_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return dict(row) if row else None

def delete_source(source_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        return cursor.rowcount > 0

    