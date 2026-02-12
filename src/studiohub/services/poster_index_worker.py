from __future__ import annotations

import json
import time
import os
from pathlib import Path
from typing import Dict
from datetime import datetime

from PySide6 import QtCore

from studiohub.hub_models.poster_index_builder import scan_single_poster


class PosterIndexWorker(QtCore.QObject):
    finished = QtCore.Signal(int, str)
    error = QtCore.Signal(str)
    status = QtCore.Signal(str)
    poster_updated = QtCore.Signal(str)

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager

        # Authoritative paths (ONE source of truth)
        self.index_path = self.config_manager.get_poster_index_path()
        self.mtime_cache_path = self.index_path.with_name("poster_mtime_cache.json")

        self.index: Dict | None = None
        self.mtime_cache = self._load_mtime_cache()

    # -------------------------------------------------
    # Full rebuild (manual / startup)
    # -------------------------------------------------

    @QtCore.Slot()
    def run(self) -> None:
        start = time.perf_counter()

        try:
            self.status.emit("Building index…")
            self._full_rebuild()
        except Exception as e:
            self.error.emit(str(e))
            return

        duration_ms = int((time.perf_counter() - start) * 1000)
        self.finished.emit(duration_ms, "OK")

    def _full_rebuild(self):
        archive_root = Path(self.config_manager.get("paths", "archive_root"))
        studio_root = Path(self.config_manager.get("paths", "studio_root"))

        posters = {
            "archive": self._scan_root(archive_root),
            "studio": self._scan_root(studio_root),
        }

        self.index = {
            "cache_version": 2,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
            "posters": posters,
        }

        print("Index path:", self.index_path)
        print("Archive root:", archive_root)
        print("Studio root:", studio_root)

        self._save_index()
        self._save_mtime_cache()

    # -------------------------------------------------
    # Incremental update (watcher-driven)
    # -------------------------------------------------

    def reindex_poster_by_path(self, poster_path: Path) -> bool:

        try:
            if self.index is None:
                self._load_index()

            key = poster_path.name
            poster_mtime = self._poster_fingerprint(poster_path)
            path_key = str(poster_path)

            

            if self.mtime_cache["dirs"].get(path_key) == poster_mtime:
                return False  # unchanged

            source = self._resolve_source(poster_path)
            if not source:
                return False

            poster_data = scan_single_poster(poster_path)
            poster_data["mtime"] = poster_mtime

            self.index["posters"][source][key] = poster_data
            self.index["generated_at"] = datetime.utcnow().isoformat(timespec="seconds")

            self.mtime_cache["dirs"][path_key] = poster_mtime

            self._save_index()
            self._save_mtime_cache()

            self.poster_updated.emit(key)
            return True

        except Exception as e:
            self.error.emit(str(e))
            return False

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _poster_fingerprint(self, poster_path: Path) -> int:
        """
        High-resolution fingerprint:
        - max mtime_ns of folder + all files
        - plus file count (catches deletions even if mtimes are weird)
        """
        max_ns = 0
        file_count = 0

        try:
            max_ns = max(max_ns, poster_path.stat().st_mtime_ns)
        except Exception:
            pass

        for p in poster_path.rglob("*"):
            if p.is_file():
                file_count += 1
                try:
                    max_ns = max(max_ns, p.stat().st_mtime_ns)
                except Exception:
                    pass

        # Combine both signals into one stable int
        return (max_ns << 20) + file_count


    def _scan_root(self, root: Path) -> Dict[str, dict]:
        out = {}
        if not root.exists():
            return out

        for d in root.iterdir():
            if d.is_dir():
                data = scan_single_poster(d)
                fingerprint = self._poster_fingerprint(d)
                data["mtime"] = fingerprint
                out[d.name] = data
                self.mtime_cache["dirs"][str(d)] = fingerprint

        return out

    def _resolve_source(self, poster_path: Path) -> str | None:
        if poster_path.parent == Path(self.config_manager.get("paths", "archive_root")):
            return "archive"
        if poster_path.parent == Path(self.config_manager.get("paths", "studio_root")):
            return "studio"
        return None

    def _load_index(self):
        if self.index_path.exists():
            self.index = json.loads(self.index_path.read_text(encoding="utf-8"))
        else:
            self.index = {
                "cache_version": 2,
                "generated_at": None,
                "posters": {"archive": {}, "studio": {}},
            }

    def _save_index(self):
        print("[IndexWorker] Updated at:", self.index_path)

        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.index, indent=2), encoding="utf-8")
        tmp.replace(self.index_path)

    def _load_mtime_cache(self) -> dict:
        if self.mtime_cache_path.exists():
            return json.loads(self.mtime_cache_path.read_text(encoding="utf-8"))
        return {"version": 1, "dirs": {}}

    def _save_mtime_cache(self):
        self.mtime_cache_path.write_text(
            json.dumps(self.mtime_cache, indent=2),
            encoding="utf-8",
        )
