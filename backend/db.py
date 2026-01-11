from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_sqlite(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def configure_build_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=200000;")
