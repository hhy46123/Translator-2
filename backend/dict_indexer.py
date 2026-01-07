from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Iterable

from .db import configure_build_pragmas, connect_sqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ko_headword TEXT NOT NULL,
    ko_norm TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS senses (
    sense_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    sense_no TEXT,
    definition_ko TEXT,
    FOREIGN KEY(entry_id) REFERENCES entries(entry_id)
);
CREATE TABLE IF NOT EXISTS equivalents (
    equiv_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sense_id INTEGER NOT NULL,
    en_lemma TEXT NOT NULL,
    en_norm TEXT NOT NULL,
    FOREIGN KEY(sense_id) REFERENCES senses(sense_id)
);
CREATE INDEX IF NOT EXISTS idx_entries_ko_norm ON entries(ko_norm);
CREATE INDEX IF NOT EXISTS idx_equiv_en_norm ON equivalents(en_norm);
"""


class BuildError(RuntimeError):
    pass


def normalize_ko(text: str) -> str:
    return " ".join(text.strip().split())


def normalize_en(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _iter_lexical_entries(payload: object) -> Iterable[dict]:
    if not isinstance(payload, dict):
        return []
    lexical_resource = payload.get("LexicalResource")
    if not isinstance(lexical_resource, dict):
        return []
    lexicon = lexical_resource.get("Lexicon")
    if isinstance(lexicon, list):
        lexicons = lexicon
    elif isinstance(lexicon, dict):
        lexicons = [lexicon]
    else:
        lexicons = []
    for lex in lexicons:
        if not isinstance(lex, dict):
            continue
        lexical_entry = lex.get("LexicalEntry")
        if isinstance(lexical_entry, list):
            entries = lexical_entry
        elif isinstance(lexical_entry, dict):
            entries = [lexical_entry]
        else:
            entries = []
        for entry in entries:
            if isinstance(entry, dict):
                yield entry


def _extract_headword(entry: dict) -> str | None:
    lemma = entry.get("Lemma")
    if isinstance(lemma, dict):
        headword = lemma.get("writtenForm") or lemma.get("WrittenForm")
        if isinstance(headword, str) and headword.strip():
            return headword.strip()
    headword = entry.get("headword")
    if isinstance(headword, str) and headword.strip():
        return headword.strip()
    return None


def _extract_senses(entry: dict) -> list[dict]:
    senses = entry.get("Sense")
    if isinstance(senses, list):
        return [s for s in senses if isinstance(s, dict)]
    if isinstance(senses, dict):
        return [senses]
    return []


def _extract_definition(sense: dict) -> str | None:
    definition = sense.get("definition") or sense.get("Definition")
    if isinstance(definition, dict):
        text = definition.get("writtenForm") or definition.get("WrittenForm")
        if isinstance(text, str) and text.strip():
            return text.strip()
    if isinstance(definition, str) and definition.strip():
        return definition.strip()
    return None


def _extract_equivalents(sense: dict) -> list[str]:
    items: list[str] = []
    equivalents = sense.get("Equivalent") or sense.get("equivalent")
    if isinstance(equivalents, list):
        for item in equivalents:
            if isinstance(item, dict):
                text = item.get("writtenForm") or item.get("WrittenForm")
                if isinstance(text, str) and text.strip():
                    items.append(text.strip())
            elif isinstance(item, str) and item.strip():
                items.append(item.strip())
    elif isinstance(equivalents, dict):
        text = equivalents.get("writtenForm") or equivalents.get("WrittenForm")
        if isinstance(text, str) and text.strip():
            items.append(text.strip())
    elif isinstance(equivalents, str) and equivalents.strip():
        items.append(equivalents.strip())
    return items


def _load_json_from_zip(zip_path: Path, name: str) -> object:
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(name) as handle:
            return json.load(handle)


def _json_names(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        return [n for n in zf.namelist() if n.lower().endswith(".json")]


def _json_paths(root_dir: Path) -> list[Path]:
    return [path for path in root_dir.rglob("*.json") if path.is_file()]


def _load_json_from_file(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _dir_stats(paths: list[Path]) -> tuple[str, str, str]:
    if not paths:
        return "0", "0", "0"
    total_size = sum(path.stat().st_size for path in paths)
    max_mtime = max(path.stat().st_mtime for path in paths)
    return str(max_mtime), str(total_size), str(len(paths))


def _update_meta_zip(conn: sqlite3.Connection, zip_path: Path) -> None:
    stat = zip_path.stat()
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
        ("zip_mtime", str(stat.st_mtime)),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
        ("zip_size", str(stat.st_size)),
    )


def _update_meta_dir(conn: sqlite3.Connection, paths: list[Path]) -> None:
    mtime, total_size, file_count = _dir_stats(paths)
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
        ("dir_mtime", mtime),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
        ("dir_size", total_size),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
        ("dir_file_count", file_count),
    )


def _read_meta(conn: sqlite3.Connection) -> tuple[str | None, str | None]:
    cur = conn.execute("SELECT key, value FROM meta")
    data = {row["key"]: row["value"] for row in cur.fetchall()}
    return data.get("zip_mtime"), data.get("zip_size")


def needs_build(
    conn: sqlite3.Connection,
    zip_path: Path | None = None,
    dir_path: Path | None = None,
) -> bool:
    try:
        conn.execute("SELECT 1 FROM meta LIMIT 1").fetchone()
    except sqlite3.OperationalError as exc:
        if "no such table: meta" in str(exc):
            return True
        raise
    if dir_path is not None:
        if not dir_path.exists():
            raise BuildError(f"Offline dictionary directory missing: {dir_path}")
        paths = _json_paths(dir_path)
        stored_mtime_row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", ("dir_mtime",)
        ).fetchone()
        stored_size_row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", ("dir_size",)
        ).fetchone()
        stored_count = conn.execute(
            "SELECT value FROM meta WHERE key = ?", ("dir_file_count",)
        ).fetchone()
        current_mtime, current_size, current_count = _dir_stats(paths)
        stored_mtime = stored_mtime_row["value"] if stored_mtime_row else None
        stored_size = stored_size_row["value"] if stored_size_row else None
        if stored_count is None:
            return True
        return (
            stored_mtime != current_mtime
            or stored_size != current_size
            or stored_count["value"] != current_count
        )
    if zip_path is None or not zip_path.exists():
        raise BuildError(f"Offline dictionary ZIP missing: {zip_path}")
    stored_mtime, stored_size = _read_meta(conn)
    stat = zip_path.stat()
    current_mtime = str(stat.st_mtime)
    current_size = str(stat.st_size)
    return stored_mtime != current_mtime or stored_size != current_size


def build_dictionary_from_zip(zip_path: Path, db_path: Path) -> None:
    conn = connect_sqlite(db_path)
    configure_build_pragmas(conn)
    conn.executescript(SCHEMA)
    conn.execute("DELETE FROM entries")
    conn.execute("DELETE FROM senses")
    conn.execute("DELETE FROM equivalents")

    batch: list[dict] = []
    json_names = _json_names(zip_path)
    if not json_names:
        raise BuildError("No JSON files found in dictionary ZIP")

    for name in json_names:
        try:
            payload = _load_json_from_zip(zip_path, name)
        except (json.JSONDecodeError, zipfile.BadZipFile, OSError):
            continue
        for entry in _iter_lexical_entries(payload):
            try:
                headword = _extract_headword(entry)
                if not headword:
                    continue
                senses = []
                for sense in _extract_senses(entry):
                    definition = _extract_definition(sense)
                    equivalents = _extract_equivalents(sense)
                    if not definition and not equivalents:
                        continue
                    senses.append(
                        {
                            "sense_no": str(sense.get("senseNumber"))
                            if sense.get("senseNumber")
                            else None,
                            "definition": definition,
                            "equivs": equivalents,
                        }
                    )
                if not senses:
                    continue
                batch.append({"headword": headword, "senses": senses})
                if len(batch) >= 250:
                    _flush_batch(conn, batch)
            except Exception:
                continue
    _flush_batch(conn, batch)
    _update_meta_zip(conn, zip_path)
    conn.commit()
    conn.close()


def build_dictionary_from_dir(dir_path: Path, db_path: Path) -> None:
    conn = connect_sqlite(db_path)
    configure_build_pragmas(conn)
    conn.executescript(SCHEMA)
    conn.execute("DELETE FROM entries")
    conn.execute("DELETE FROM senses")
    conn.execute("DELETE FROM equivalents")

    batch: list[dict] = []
    json_paths = _json_paths(dir_path)
    if not json_paths:
        raise BuildError(f"No JSON files found in directory: {dir_path}")

    for path in json_paths:
        try:
            payload = _load_json_from_file(path)
        except (json.JSONDecodeError, OSError):
            continue
        for entry in _iter_lexical_entries(payload):
            try:
                headword = _extract_headword(entry)
                if not headword:
                    continue
                senses = []
                for sense in _extract_senses(entry):
                    definition = _extract_definition(sense)
                    equivalents = _extract_equivalents(sense)
                    senses.append(
                        {
                            "sense_no": str(sense.get("senseNumber"))
                            if sense.get("senseNumber")
                            else None,
                            "definition": definition,
                            "equivs": equivalents,
                        }
                    )
                senses = [s for s in senses if s["definition"] or s["equivs"]]
                if not senses:
                    continue
                batch.append({"headword": headword, "senses": senses})
                if len(batch) >= 250:
                    _flush_batch(conn, batch)
            except Exception:
                continue
    _flush_batch(conn, batch)
    _update_meta_dir(conn, json_paths)
    conn.commit()
    conn.close()


def has_dictionary_data(conn: sqlite3.Connection) -> bool:
    try:
        row = conn.execute("SELECT COUNT(*) AS count FROM entries").fetchone()
        return bool(row["count"])
    except sqlite3.Error:
        return False


def _flush_batch(conn: sqlite3.Connection, batch: list[dict]) -> None:
    if not batch:
        return
    entry_rows = [(item["headword"], normalize_ko(item["headword"])) for item in batch]
    cur = conn.executemany(
        "INSERT INTO entries(ko_headword, ko_norm) VALUES(?, ?)",
        entry_rows,
    )
    start_id = cur.lastrowid - len(entry_rows) + 1
    entry_ids = list(range(start_id, start_id + len(entry_rows)))

    sense_rows: list[tuple[int, str | None, str | None]] = []
    sense_equivs: list[list[str]] = []
    for entry_id, item in zip(entry_ids, batch):
        for sense in item["senses"]:
            sense_rows.append((entry_id, sense.get("sense_no"), sense.get("definition")))
            sense_equivs.append(sense.get("equivs", []))

    if sense_rows:
        cur = conn.executemany(
            "INSERT INTO senses(entry_id, sense_no, definition_ko) VALUES(?, ?, ?)",
            sense_rows,
        )
        start_sense_id = cur.lastrowid - len(sense_rows) + 1
        sense_ids = list(range(start_sense_id, start_sense_id + len(sense_rows)))
    else:
        sense_ids = []

    equiv_rows: list[tuple[int, str, str]] = []
    for sense_id, equivs in zip(sense_ids, sense_equivs):
        for equiv in equivs:
            en_norm = normalize_en(equiv)
            if en_norm:
                equiv_rows.append((sense_id, equiv, en_norm))
    if equiv_rows:
        conn.executemany(
            "INSERT INTO equivalents(sense_id, en_lemma, en_norm) VALUES(?, ?, ?)",
            equiv_rows,
        )

    batch.clear()
