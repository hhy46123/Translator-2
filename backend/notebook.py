from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from .db import connect_sqlite


NOTEBOOK_SCHEMA = """
CREATE TABLE IF NOT EXISTS notebook_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    direction TEXT NOT NULL,
    senses_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    correct_count INTEGER DEFAULT 0,
    wrong_attempts INTEGER DEFAULT 0,
    learned INTEGER DEFAULT 0
);
"""


@dataclass
class NotebookItem:
    id: int
    source_text: str
    translated_text: str
    direction: str
    senses: list[dict]
    correct_count: int
    wrong_attempts: int
    learned: bool


def init_notebook(db_path) -> None:
    conn = connect_sqlite(db_path)
    conn.executescript(NOTEBOOK_SCHEMA)
    conn.commit()
    conn.close()


def add_item(
    conn: sqlite3.Connection,
    source_text: str,
    translated_text: str,
    direction: str,
    senses: list[dict],
) -> int:
    cur = conn.execute(
        """
        INSERT INTO notebook_items(source_text, translated_text, direction, senses_json)
        VALUES (?, ?, ?, ?)
        """,
        (source_text, translated_text, direction, json.dumps(senses, ensure_ascii=False)),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_items(conn: sqlite3.Connection, limit: int = 100) -> list[NotebookItem]:
    cur = conn.execute(
        """
        SELECT id, source_text, translated_text, direction, senses_json,
               correct_count, wrong_attempts, learned
        FROM notebook_items
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    items = []
    for row in cur.fetchall():
        items.append(
            NotebookItem(
                id=row["id"],
                source_text=row["source_text"],
                translated_text=row["translated_text"],
                direction=row["direction"],
                senses=json.loads(row["senses_json"]),
                correct_count=row["correct_count"],
                wrong_attempts=row["wrong_attempts"],
                learned=bool(row["learned"]),
            )
        )
    return items


def get_item(conn: sqlite3.Connection, item_id: int) -> NotebookItem | None:
    row = conn.execute(
        """
        SELECT id, source_text, translated_text, direction, senses_json,
               correct_count, wrong_attempts, learned
        FROM notebook_items
        WHERE id = ?
        """,
        (item_id,),
    ).fetchone()
    if not row:
        return None
    return NotebookItem(
        id=row["id"],
        source_text=row["source_text"],
        translated_text=row["translated_text"],
        direction=row["direction"],
        senses=json.loads(row["senses_json"]),
        correct_count=row["correct_count"],
        wrong_attempts=row["wrong_attempts"],
        learned=bool(row["learned"]),
    )


def mark_learned(conn: sqlite3.Connection, item_id: int, learned: bool) -> None:
    conn.execute(
        "UPDATE notebook_items SET learned = ? WHERE id = ?",
        (1 if learned else 0, item_id),
    )
    conn.commit()


def wrong_delta(conn: sqlite3.Connection, item_id: int, delta: int) -> None:
    conn.execute(
        "UPDATE notebook_items SET wrong_attempts = MAX(wrong_attempts + ?, 0) WHERE id = ?",
        (delta, item_id),
    )
    conn.commit()


def increment_correct(conn: sqlite3.Connection, item_id: int) -> None:
    conn.execute(
        "UPDATE notebook_items SET correct_count = correct_count + 1 WHERE id = ?",
        (item_id,),
    )
    conn.commit()
