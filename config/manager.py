from __future__ import annotations

from pathlib import Path
from typing import Any

from studiohub.config.schema import AppConfig
from studiohub.config.io import load_or_create, write_config
from studiohub.config.paths import (
    get_config_path,
    get_local_cache_root,
    get_poster_index_path,
    get_appdata_root,
)
from studiohub.config.validation import assert_runtime_not_in_studio


class ConfigManager:
    """
    Single source of truth for application configuration.
    """

    def __init__(self):
        self.path: Path = get_config_path()
        self.data: AppConfig = load_or_create(self.path)

    # ---------------------------
    # Persistence
    # ---------------------------

    def save(self) -> None:
        write_config(self.path, self.data)

    # ---------------------------
    # Generic accessors
    # ---------------------------

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        self.data.setdefault(section, {})[key] = value
        self.save()

    # ---------------------------
    # Path helpers
    # ---------------------------

    def get_runtime_root(self) -> Path:
        raw = self.get("paths", "runtime_root", "").strip()
        if not raw:
            raise RuntimeError("Runtime root not configured (paths.runtime_root)")

        p = Path(raw).expanduser()
        if not p.exists() or not p.is_dir():
            raise RuntimeError(f"Invalid runtime root: {p}")

        return p

    def get_mockup_templates_root(self) -> Path:
        raw = self.get("paths", "mockup_templates_root", "").strip()
        if not raw:
            raise RuntimeError("Mockup templates folder not configured")

        p = Path(raw).expanduser()
        if not p.exists() or not p.is_dir():
            raise RuntimeError(f"Invalid mockup templates folder: {p}")

        return p

    def get_mockup_output_root(self) -> Path:
        raw = self.get("paths", "mockup_output_root", "").strip()
        if not raw:
            raise RuntimeError("Mockup output folder not configured")

        p = Path(raw).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_print_log_path(self) -> Path:
        runtime = self.get_runtime_root()
        path = runtime / "logs" / "print_log.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def get_local_cache_root(self) -> Path:
        return get_local_cache_root()

    def get_poster_index_path(self) -> Path:
        return get_poster_index_path()

    # ---------------------------
    # Guards
    # ---------------------------

    def assert_runtime_not_in_studio(self) -> None:
        assert_runtime_not_in_studio(self.data)

    # ---------------------------
    # Legacy path passthroughs
    # ---------------------------

    def get_appdata_root(self) -> Path:
        return get_appdata_root()
