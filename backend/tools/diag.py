from __future__ import annotations

import json
from pathlib import Path

from ..config import load_settings
from ..db import connect_sqlite
from ..dict_indexer import BuildError, needs_build
from ..notebook import init_notebook


def main() -> None:
    settings = load_settings()
    print("Offline dictionary ZIP:", settings.offline_dict_zip_path)
    if settings.offline_dict_zip_path.exists():
        print("ZIP size:", settings.offline_dict_zip_path.stat().st_size)
    else:
        print("ZIP missing")

    conn = connect_sqlite(settings.offline_dict_db_path)
    try:
        try:
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
    finally:
        conn.close()

    init_notebook(settings.notebook_db_path)
    print("Notebook DB:", settings.notebook_db_path)


if __name__ == "__main__":
    main()
