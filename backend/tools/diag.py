from __future__ import annotations

import json
from pathlib import Path

from ..config import load_settings
from ..db import connect_sqlite
from ..dict_indexer import BuildError, needs_build
from ..notebook import init_notebook


def main() -> None:
    settings = load_settings()
    if settings.offline_dict_dir_path:
        print("Offline dictionary DIR:", settings.offline_dict_dir_path)
        json_files = list(settings.offline_dict_dir_path.rglob("*.json"))
        print("JSON files found:", len(json_files))
    else:
        print("Offline dictionary ZIP:", settings.offline_dict_zip_path)
        if settings.offline_dict_zip_path.exists():
            print("ZIP size:", settings.offline_dict_zip_path.stat().st_size)
        else:
            print("ZIP missing")

    conn = connect_sqlite(settings.offline_dict_db_path)
    try:
        try:
            if settings.offline_dict_dir_path:
                print(
                    "Needs build:",
                    needs_build(conn, dir_path=settings.offline_dict_dir_path),
                )
            else:
                print("Needs build:", needs_build(conn, settings.offline_dict_zip_path))
        except BuildError as exc:
            print("Needs build: error:", exc)
        counts = {}
        for table in ["entries", "senses", "equivalents"]:
            try:
                counts[table] = conn.execute(
                    f"SELECT COUNT(*) AS count FROM {table}"
                ).fetchone()["count"]
            except Exception:
                counts[table] = "n/a"
        print("Counts:", json.dumps(counts))
        samples = conn.execute(
            """
            SELECT entries.ko_headword, senses.definition_ko
            FROM entries
            LEFT JOIN senses ON senses.entry_id = entries.entry_id
            ORDER BY entries.entry_id
            LIMIT 2
            """
        ).fetchall()
        if samples:
            print("Sample records:")
            for row in samples:
                print(f"  - {row['ko_headword']}: {row['definition_ko']}")
    finally:
        conn.close()

    init_notebook(settings.notebook_db_path)
    print("Notebook DB:", settings.notebook_db_path)


if __name__ == "__main__":
    main()
