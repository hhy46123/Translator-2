from __future__ import annotations

import os
import time
from pathlib import Path

from .config import Settings
from .db import connect_sqlite
from .dict_indexer import (
    build_dictionary_from_dir,
    build_dictionary_from_zip,
    has_dictionary_data,
    needs_build,
)
from .notebook import init_notebook


class BuildLockTimeout(RuntimeError):
    pass


def acquire_lock(lock_path: Path, timeout: int = 120) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return
        except FileExistsError:
            if time.time() - start > timeout:
                raise BuildLockTimeout("Timed out waiting for offline dict build lock")
            time.sleep(1)


def release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return


def ensure_offline_dict(settings: Settings) -> None:
    conn = connect_sqlite(settings.offline_dict_db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()
    use_dir = settings.offline_dict_dir_path is not None
    if use_dir:
        needs_rebuild = needs_build(conn, dir_path=settings.offline_dict_dir_path)
    else:
        needs_rebuild = needs_build(conn, zip_path=settings.offline_dict_zip_path)

    if not needs_rebuild and has_dictionary_data(conn):
        conn.close()
        return
    conn.close()

    acquire_lock(settings.build_lock_path)
    try:
        if use_dir:
            build_dictionary_from_dir(
                settings.offline_dict_dir_path, settings.offline_dict_db_path
            )
        else:
            build_dictionary_from_zip(
                settings.offline_dict_zip_path, settings.offline_dict_db_path
            )
    finally:
        release_lock(settings.build_lock_path)


def ensure_notebook(settings: Settings) -> None:
    init_notebook(settings.notebook_db_path)
