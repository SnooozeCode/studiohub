# studiohub/models/missing_files_model_qt.py

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PySide6 import QtCore

from studiohub.config.manager import ConfigManager
from studiohub.utils.text.normalization import normalize_background_name, normalize_name, normalize_studio_name

from studiohub.constants import PRINT_SIZES


# Background variants expected for archive (normalized keys + display labels)
_EXPECTED_BG_RAW: Tuple[str, ...] = ("Antique Parchment", "Blueprint", "Chalkboard")
EXPECTED_PATENT_BG: Tuple[Tuple[str, str], ...] = tuple(
    (normalize_background_name(x)["key"], normalize_background_name(x)["label"])
    for x in _EXPECTED_BG_RAW
)


class MissingFilesModelQt(QtCore.QObject):
    """
    Missing Files Model (v3.2)

    Contract:
    - NEVER scans filesystem directly.
    - Reads ONLY poster_index.json (cache_version=2).
    - Emits view-shaped data that contains ALL posters with their missing status.
    """

    scan_started = QtCore.Signal(str)            # source
    scan_finished = QtCore.Signal(str, object)   # source, data
    scan_error = QtCore.Signal(str, str)         # source, message

    def __init__(self, config_manager: ConfigManager, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._cache_archive: Dict[str, Any] = {}
        self._cache_studio: Dict[str, Any] = {}

    # -------------------------------------------------
    # Cache access
    # -------------------------------------------------

    def get_cache(self, source: str) -> Dict[str, Any]:
        if source == "archive":
            return self._cache_archive
        if source == "studio":
            return self._cache_studio
        return {}

    # -------------------------------------------------
    # Refresh
    # -------------------------------------------------

    def refresh(self, source: str) -> None:
        if source not in ("archive", "studio"):
            return

        self.scan_started.emit(source)

        try:
            index = self._load_index()

            if source == "archive":
                self._cache_archive = self._build_archive_status(index)
            else:
                self._cache_studio = self._build_studio_status(index)

            # Emit for the requested source
            self.scan_finished.emit(source, self.get_cache(source))

        except Exception as e:
            self.scan_error.emit(source, str(e))

    # -------------------------------------------------
    # Index loading
    # -------------------------------------------------

    def _load_index(self) -> Dict[str, Any]:
        index_path = self.config_manager.get_poster_index_path()

        if not index_path.exists():
            raise FileNotFoundError(f"poster_index.json not found: {index_path}")

        data = json.loads(index_path.read_text(encoding="utf-8"))

        if data.get("cache_version") != 2:
            raise ValueError(
                f"poster_index.json cache_version must be 2 (found {data.get('cache_version')})"
            )

        posters = data.get("posters")
        if not isinstance(posters, dict):
            raise ValueError("poster_index.json missing 'posters' object")

        return data

    # -------------------------------------------------
    # Status Builders (for ALL posters)
    # -------------------------------------------------

    def _build_archive_status(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Build status data for ALL archive posters."""
        posters = (index.get("posters") or {}).get("archive") or {}
        out: Dict[str, Any] = {}

        for folder_name, meta in sorted(posters.items(), key=lambda kv: kv[0].lower()):
            if not isinstance(meta, dict):
                continue

            display_name = (meta.get("display_name") or folder_name).strip()
            sizes_meta = meta.get("sizes") or {}
            exists = meta.get("exists") or {}

            # Track what's missing
            missing = {
                "master": not bool(exists.get("master", False)),
                "web": not bool(exists.get("web", False)),
                "sizes": [],
                "backgrounds": {}
            }

            # Check each size
            for size in PRINT_SIZES:
                sm = sizes_meta.get(size) or {}
                
                # Check if size has any output
                has_output = False
                bgs = sm.get("backgrounds") or {}
                
                if bgs:
                    # Archive: check backgrounds
                    for bg_key, bg_rec in bgs.items():
                        if isinstance(bg_rec, dict) and bg_rec.get("exists") is True:
                            has_output = True
                            break
                
                if not has_output:
                    missing["sizes"].append(size)

                # Check expected backgrounds for this size
                if has_output:
                    # Normalize existing bg keys
                    existing_bg_keys_norm = set()
                    for raw_bg_key, bg_rec in bgs.items():
                        if isinstance(bg_rec, dict) and bg_rec.get("exists") is True:
                            try:
                                norm = normalize_background_name(raw_bg_key)["key"]
                            except Exception:
                                norm = str(raw_bg_key).strip().lower().replace(" ", "_")
                            existing_bg_keys_norm.add(norm)

                    # Check each expected background
                    for expected_key, expected_label in EXPECTED_PATENT_BG:
                        if expected_key not in existing_bg_keys_norm:
                            # This background is missing for this size
                            bg_missing = missing["backgrounds"].setdefault(
                                expected_key, {
                                    "label": expected_label,
                                    "sizes": []
                                }
                            )
                            if size not in bg_missing["sizes"]:
                                bg_missing["sizes"].append(size)

            # Store ALL posters with their missing status
            out[folder_name] = {
                "display_name": display_name,
                "path": folder_name,
                "missing": missing,
            }

        return {k: out[k] for k in sorted(out.keys(), key=lambda x: x.lower())}

    def _build_studio_status(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Build status data for ALL studio posters."""
        posters = (index.get("posters") or {}).get("studio") or {}
        out: Dict[str, Any] = {}

        for folder_name, meta in sorted(posters.items(), key=lambda kv: kv[0].lower()):
            if not isinstance(meta, dict):
                continue

            display_name = (meta.get("display_name") or folder_name).strip()
            sizes_meta = meta.get("sizes") or {}
            exists = meta.get("exists") or {}

            # Track what's missing
            missing = {
                "master": not bool(exists.get("master", False)),
                "web": not bool(exists.get("web", False)),
                "sizes": []
            }

            # Check each size
            for size in PRINT_SIZES:
                sm = sizes_meta.get(size) or {}
                
                # Studio: check if size has files
                files = sm.get("files") or []
                has_files = isinstance(files, list) and len(files) > 0
                
                if not has_files:
                    missing["sizes"].append(size)

            # Store ALL posters with their missing status
            out[folder_name] = {
                "display_name": display_name,
                "missing": missing,
            }

        return {k: out[k] for k in sorted(out.keys(), key=lambda x: x.lower())}