from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    data_dir: Path
    cache_dir: Path
    offline_dict_dir_path: Path | None
    offline_dict_include_non_ko: bool
    offline_dict_zip_path: Path
    offline_dict_db_path: Path
    notebook_db_path: Path
    build_lock_path: Path
    max_senses: int = 10


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    cache_dir = data_dir / "cache"
    offline_dir_env = os.environ.get("OFFLINE_DICT_DIR_PATH")
    offline_dir = Path(offline_dir_env) if offline_dir_env else None
    include_non_ko = os.environ.get("OFFLINE_DICT_INCLUDE_NON_KO", "").lower() in {
        "1",
        "true",
        "yes",
        "y",
    }
    offline_dict_zip = Path(
        os.environ.get("OFFLINE_DICT_ZIP_PATH", data_dir / "offline_dict.zip")
    )
    offline_dict_db = cache_dir / "offline_dict.sqlite"
    notebook_db = data_dir / "notebook.sqlite"
    build_lock = cache_dir / "offline_build.lock"
    return Settings(
        base_dir=base_dir,
        data_dir=data_dir,
        cache_dir=cache_dir,
        offline_dict_dir_path=offline_dir,
        offline_dict_include_non_ko=include_non_ko,
        offline_dict_zip_path=offline_dict_zip,
        offline_dict_db_path=offline_dict_db,
        notebook_db_path=notebook_db,
        build_lock_path=build_lock,
    )
