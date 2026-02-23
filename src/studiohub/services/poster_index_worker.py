from __future__ import annotations

import json
import time
import os
from pathlib import Path
from typing import Dict
from datetime import datetime

from PySide6 import QtCore

from studiohub.hub_models.poster_index_builder import scan_single_poster
from studiohub.utils.logging import get_logger
from studiohub.utils.file_utils import atomic_write_json, safe_read_json, FileLock

logger = get_logger(__name__)


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
        self.lock_path = self.index_path.with_suffix('.lock')

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
        max_ns = 0
        file_count = 0
        
        try:
            max_ns = max(max_ns, poster_path.stat().st_mtime_ns)
        except Exception as e:
            self.status.emit(f"Warning: Could not read mtime for {poster_path.name}")
            logger.debug(f"Failed to get mtime for {poster_path}: {e}")
        
        for p in poster_path.rglob("*"):
            if p.is_file():
                file_count += 1
                try:
                    max_ns = max(max_ns, p.stat().st_mtime_ns)
                except Exception as e:
                    # Don't spam status for every file
                    logger.warning(f"Failed to get mtime for {p}: {e}")
        
        return max_ns

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

    def _load_index(self) -> None:
        """
        Load index safely with fallback to defaults.
        Uses safe_read_json for automatic backup fallback.
        """
        self.index = safe_read_json(
            self.index_path,
            default={
                "cache_version": 2,
                "generated_at": None,
                "posters": {"archive": {}, "studio": {}}
            }
        )
        logger.debug(f"Loaded index with {len(self.index.get('posters', {}))} posters")

    def _save_index(self) -> None:
        """Save index atomically with file locking."""
        logger.info(f"Saving index to {self.index_path}")
        
        try:
            # Use file lock to prevent concurrent writes
            with FileLock(self.lock_path, timeout=5.0):
                # Write atomically with backup
                atomic_write_json(self.index_path, self.index, make_backup=True)
                
        except TimeoutError:
            logger.error(f"Could not acquire lock for {self.index_path} after 5 seconds")
            # Fall back to atomic write without lock (still safe, but might race)
            atomic_write_json(self.index_path, self.index, make_backup=True)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise

    def _load_mtime_cache(self) -> dict:
        """
        Load mtime cache safely.
        Returns default cache if file doesn't exist or is corrupted.
        """
        return safe_read_json(
            self.mtime_cache_path,
            default={"version": 1, "dirs": {}}
        )

    def _save_mtime_cache(self) -> None:
        """Save mtime cache atomically."""
        try:
            atomic_write_json(self.mtime_cache_path, self.mtime_cache, make_backup=False)
            logger.debug(f"Saved mtime cache with {len(self.mtime_cache['dirs'])} entries")
        except Exception as e:
            logger.error(f"Failed to save mtime cache: {e}")
            # Non-critical, continue

    # -------------------------------------------------
    # Recovery Methods
    # -------------------------------------------------

    def verify_index_integrity(self) -> bool:
        """
        Verify that the index file is valid JSON.
        Returns True if valid, False otherwise.
        """
        if not self.index_path.exists():
            return True
        
        try:
            data = safe_read_json(self.index_path)
            return data is not None and "cache_version" in data
        except Exception as e:
            logger.error(f"Index integrity check failed: {e}")
            return False

    def recover_index_from_backup(self) -> bool:
        """
        Attempt to recover the index from the most recent backup.
        Returns True if recovery succeeded.
        """
        from studiohub.utils.recovery import recover_from_backup
        return recover_from_backup(self.index_path)