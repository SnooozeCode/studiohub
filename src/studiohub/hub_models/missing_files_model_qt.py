
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PySide6 import QtCore

from studiohub.config_manager import ConfigManager
from studiohub.hub_models.index_normalization import normalize_background_name
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
    - Emits view-shaped data that lists ONLY what is missing.
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
                self._cache_archive = self._build_archive(index)
            else:
                self._cache_studio = self._build_studio(index)

            # IMPORTANT: emit for BOTH sources
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
    # Helpers (index-v2 truth)
    # -------------------------------------------------

    def _patent_size_has_output(self, size_meta: Dict[str, Any]) -> bool:
        """
        A patent size is considered present if ANY background variant exists.
        """
        if not isinstance(size_meta, dict):
            return False

        bgs = size_meta.get("backgrounds")
        if not isinstance(bgs, dict) or not bgs:
            return False

        for bg_rec in bgs.values():
            if isinstance(bg_rec, dict) and bg_rec.get("exists") is True:
                return True

        return False

    def _studio_size_has_output(self, size_meta: Dict[str, Any]) -> bool:
        """
        A studio size is considered present if there is at least one file.
        """
        if not isinstance(size_meta, dict):
            return False

        files = size_meta.get("files") or []
        return isinstance(files, list) and len(files) > 0

    # -------------------------------------------------
    # Builders
    # -------------------------------------------------

    def _build_archive(self, index: Dict[str, Any]) -> Dict[str, Any]:
        posters = (index.get("posters") or {}).get("archive") or {}
        out: Dict[str, Any] = {}

        for folder_name, meta in sorted(posters.items(), key=lambda kv: kv[0].lower()):
            display_name = (meta.get("display_name") or folder_name).strip()
            sizes_meta = meta.get("sizes") or {}

            # Legacy fields: index v2 does not track master/web -> never mark missing
            missing_master = False
            missing_web = False

            # Determine which sizes actually have printable output
            size_has_output = {}
            for size in PRINT_SIZES:
                sm = sizes_meta.get(size) or {}
                size_has_output[size] = self._patent_size_has_output(sm)

            missing_sizes = [s for s in PRINT_SIZES if not size_has_output.get(s, False)]

            # Background missing is computed only for sizes that DO have output at all
            missing_bgs: Dict[str, Dict[str, Any]] = {}

            for size in PRINT_SIZES:
                if not size_has_output.get(size, False):
                    continue

                sm = sizes_meta.get(size) or {}
                bgs = sm.get("backgrounds") or {}

                # Normalize existing bg keys before comparison
                existing_bg_keys_norm = set()
                if isinstance(bgs, dict):
                    for raw_bg_key, bg_rec in bgs.items():
                        if not (isinstance(bg_rec, dict) and bg_rec.get("exists") is True):
                            continue
                        try:
                            norm = normalize_background_name(raw_bg_key)["key"]
                        except Exception:
                            norm = str(raw_bg_key).strip().lower().replace(" ", "_")
                        existing_bg_keys_norm.add(norm)

                for expected_key, expected_label in EXPECTED_PATENT_BG:
                    if expected_key not in existing_bg_keys_norm:
                        slot = missing_bgs.setdefault(
                            expected_key, {"label": expected_label, "sizes": []}
                        )
                        slot["sizes"].append(size)

            stable_bgs = {
                k: {"label": missing_bgs[k]["label"], "sizes": sorted(missing_bgs[k]["sizes"])}
                for k in sorted(missing_bgs.keys())
                if missing_bgs[k].get("sizes")
            }

            any_missing = bool(missing_sizes) or bool(stable_bgs) or missing_master or missing_web
            if not any_missing:
                continue

            missing_payload: Dict[str, Any] = {}

            if missing_master:
                missing_payload["master"] = True

            if missing_web:
                missing_payload["web"] = True

            if missing_sizes:
                missing_payload["sizes"] = missing_sizes

            if any(v.get("sizes") for v in stable_bgs.values()):
                missing_payload["backgrounds"] = stable_bgs

            if not missing_payload:
                continue

            out[folder_name] = {
                "display_name": display_name,
                "path": folder_name,
                "missing": missing_payload,
            }

        return {k: out[k] for k in sorted(out.keys(), key=lambda x: x.lower())}

    def _build_studio(self, index: Dict[str, Any]) -> Dict[str, Any]:
        posters = (index.get("posters") or {}).get("studio") or {}
        out: Dict[str, Any] = {}

        for folder_name, meta in sorted(posters.items(), key=lambda kv: kv[0].lower()):
            display_name = (meta.get("display_name") or folder_name).strip()
            sizes_meta = meta.get("sizes") or {}

            # Index v2: master/web are authoritative and present in index
            exists = meta.get("exists") or {}
            missing_master = not bool(exists.get("master"))
            missing_web = not bool(exists.get("web"))

            size_has_output = {}
            for size in PRINT_SIZES:
                sm = sizes_meta.get(size) or {}
                size_has_output[size] = self._studio_size_has_output(sm)

            missing_sizes = [s for s in PRINT_SIZES if not size_has_output.get(s, False)]

            missing_payload: Dict[str, Any] = {}

            if missing_master:
                missing_payload["master"] = True

            if missing_web:
                missing_payload["web"] = True

            if missing_sizes:
                missing_payload["sizes"] = missing_sizes

            if not missing_payload:
                continue

            out[folder_name] = {
                "display_name": display_name,
                "missing": missing_payload,
            }

        return {k: out[k] for k in sorted(out.keys(), key=lambda x: x.lower())}
