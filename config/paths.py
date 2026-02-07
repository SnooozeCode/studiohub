from __future__ import annotations

import os
from pathlib import Path


APP_VENDOR = "SnooozeCo"
APP_NAME = "StudioHub"


def get_appdata_root() -> Path:
    base = Path(os.getenv("APPDATA", Path.home()))
    root = base / APP_VENDOR / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_config_path() -> Path:
    root = get_appdata_root()
    return root / "config.json"


def get_local_cache_root() -> Path:
    root = get_appdata_root() / "cache"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_poster_index_path() -> Path:
    path = get_local_cache_root() / "poster_index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
