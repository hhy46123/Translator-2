from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .dict_indexer import normalize_en, normalize_ko


@dataclass
class SenseResult:
    sense_id: int
    entry_id: int
    ko_headword: str
    definition_ko: str | None
    en_equivalents: list[str]


def detect_language(text: str) -> str:
    for ch in text:
        if "\uac00" <= ch <= "\ud7a3":
            return "ko"
    return "en"


def _query_senses(
    conn: sqlite3.Connection,
    column: str,
    value: str,
    like_mode: str | None = None,
    limit: int = 10,
) -> list[SenseResult]:
    if like_mode == "prefix":
        param = f"{value}%"
        clause = f"{column} LIKE ?"
    elif like_mode == "substring":
        param = f"%{value}%"
        clause = f"{column} LIKE ?"
    else:
        param = value
        clause = f"{column} = ?"

    sql = f"""
        SELECT senses.sense_id, senses.entry_id, entries.ko_headword, senses.definition_ko
        FROM senses
        JOIN entries ON entries.entry_id = senses.entry_id
        JOIN equivalents ON equivalents.sense_id = senses.sense_id
        WHERE {clause}
        GROUP BY senses.sense_id
        ORDER BY entries.ko_headword
        LIMIT ?
    """
    cur = conn.execute(sql, (param, limit))
    senses = []
    for row in cur.fetchall():
        equivalents = conn.execute(
            "SELECT en_lemma FROM equivalents WHERE sense_id = ?",
            (row["sense_id"],),
        ).fetchall()
        senses.append(
            SenseResult(
                sense_id=row["sense_id"],
                entry_id=row["entry_id"],
                ko_headword=row["ko_headword"],
                definition_ko=row["definition_ko"],
                en_equivalents=[eq["en_lemma"] for eq in equivalents],
            )
        )
    return senses


def _query_ko_senses(
    conn: sqlite3.Connection,
    ko_value: str,
    like_mode: str | None = None,
    limit: int = 10,
) -> list[SenseResult]:
    if like_mode == "prefix":
        param = f"{ko_value}%"
        clause = "entries.ko_norm LIKE ?"
    elif like_mode == "substring":
        param = f"%{ko_value}%"
        clause = "entries.ko_norm LIKE ?"
    else:
        param = ko_value
        clause = "entries.ko_norm = ?"

    sql = f"""
        SELECT senses.sense_id, senses.entry_id, entries.ko_headword, senses.definition_ko
        FROM senses
        JOIN entries ON entries.entry_id = senses.entry_id
        WHERE {clause}
        ORDER BY senses.sense_id
        LIMIT ?
    """
    cur = conn.execute(sql, (param, limit))
    senses = []
    for row in cur.fetchall():
        equivalents = conn.execute(
            "SELECT en_lemma FROM equivalents WHERE sense_id = ?",
            (row["sense_id"],),
        ).fetchall()
        senses.append(
            SenseResult(
                sense_id=row["sense_id"],
                entry_id=row["entry_id"],
                ko_headword=row["ko_headword"],
                definition_ko=row["definition_ko"],
                en_equivalents=[eq["en_lemma"] for eq in equivalents],
            )
        )
    return senses


def search_dictionary(
    conn: sqlite3.Connection,
    text: str,
    direction: str,
    limit: int = 10,
) -> list[SenseResult]:
    if direction == "auto":
        direction = detect_language(text)

    if direction == "ko":
        normalized = normalize_ko(text)
        for mode in (None, "prefix", "substring"):
            senses = _query_ko_senses(conn, normalized, mode, limit)
            if senses:
                return senses
        return []

    normalized = normalize_en(text)
    for mode in (None, "prefix", "substring"):
        senses = _query_senses(conn, "equivalents.en_norm", normalized, mode, limit)
        if senses:
            return senses
    return []
