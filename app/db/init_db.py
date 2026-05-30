from pathlib import Path
import sqlite3

from app.core.config import ensure_runtime_dirs, load_settings


def init_db() -> None:
    settings = load_settings()
    ensure_runtime_dirs(settings)

    schema_path = Path(__file__).with_name("schema.sql")
    schema = schema_path.read_text(encoding="utf-8")

    conn = sqlite3.connect(settings.database_path)
    try:
        conn.executescript(schema)
        conn.commit()
        print(f"[OK] Database initialized: {settings.database_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()