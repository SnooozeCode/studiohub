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

        print(f"\n[MODEL: {source}] ===== REFRESH CALLED =====")
        self.scan_started.emit(source)

        try:
            index = self._load_index()
            
            if source == "archive":
                new_data = self._build_archive_status(index)
                
                # DEBUG: Check if CallofDuty_RayGun is in the data
                if "CallofDuty_RayGun" in new_data:
                    print(f"[MODEL DEBUG] CallofDuty_RayGun found in new_data!")
                    print(f"  missing.web: {new_data['CallofDuty_RayGun']['missing']['web']}")
                else:
                    print(f"[MODEL DEBUG] CallofDuty_RayGun NOT in new_data")
                
                # Check if data changed
                if str(self._cache_archive) != str(new_data):
                    print(f"[MODEL: {source}] Data CHANGED, updating cache")
                    self._cache_archive = new_data
                else:
                    print(f"[MODEL: {source}] Data UNCHANGED")
                    
                # DEBUG: What's in the cache now?
                if "CallofDuty_RayGun" in self._cache_archive:
                    print(f"[MODEL DEBUG] After update, CallofDuty_RayGun in cache!")
                else:
                    print(f"[MODEL DEBUG] After update, CallofDuty_RayGun NOT in cache")
                    
            else:  # studio
                new_data = self._build_studio_status(index)
                
                # DEBUG: Check if CallofDuty_RayGun is in the data
                if "CallofDuty_RayGun" in new_data:
                    print(f"[MODEL DEBUG] CallofDuty_RayGun found in new_data!")
                    print(f"  missing.web: {new_data['CallofDuty_RayGun']['missing']['web']}")
                else:
                    print(f"[MODEL DEBUG] CallofDuty_RayGun NOT in new_data")
                
                # Check if data changed
                if str(self._cache_studio) != str(new_data):
                    print(f"[MODEL: {source}] Data CHANGED, updating cache")
                    self._cache_studio = new_data
                else:
                    print(f"[MODEL: {source}] Data UNCHANGED")
                    
                # DEBUG: What's in the cache now?
                if "CallofDuty_RayGun" in self._cache_studio:
                    print(f"[MODEL DEBUG] After update, CallofDuty_RayGun in cache!")
                    print(f"  cached missing.web: {self._cache_studio['CallofDuty_RayGun']['missing']['web']}")
                else:
                    print(f"[MODEL DEBUG] After update, CallofDuty_RayGun NOT in cache")

            # Emit the data from cache
            cache_data = self.get_cache(source)
            print(f"[MODEL: {source}] Emitting scan_finished with {len(cache_data)} items")
            self.scan_finished.emit(source, cache_data)

        except Exception as e:
            print(f"[MODEL: {source}] ERROR: {e}")
            self.scan_error.emit(source, str(e))

    # -------------------------------------------------
    # Index loading
    # -------------------------------------------------

    def _load_index(self) -> Dict[str, Any]:
        index_path = self.config_manager.get_poster_index_path()
        
        if not index_path.exists():
            raise FileNotFoundError(f"poster_index.json not found: {index_path}")
        
        data = json.loads(index_path.read_text(encoding="utf-8"))
        
        print(f"\n[MODEL INDEX DEBUG] Full index structure:")
        print(f"  Keys: {list(data.keys())}")
        
        posters = data.get("posters", {})
        print(f"  posters type: {type(posters)}")
        print(f"  posters keys: {list(posters.keys())}")
        
        if "studio" in posters:
            studio_data = posters["studio"]
            print(f"  studio type: {type(studio_data)}")
            if isinstance(studio_data, dict):
                print(f"  studio keys (first 5): {list(studio_data.keys())[:5]}")
                print(f"  studio count: {len(studio_data)}")
        
        if data.get("cache_version") != 2:
            raise ValueError(f"poster_index.json cache_version must be 2 (found {data.get('cache_version')})")
        
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
        posters = index.get("posters", {}).get("studio", {})
        out: Dict[str, Any] = {}

        print(f"[MODEL DEBUG] Studio posters found: {len(posters)}")
        
        for folder_name, meta in sorted(posters.items(), key=lambda kv: kv[0].lower()):
            if not isinstance(meta, dict):
                continue

            display_name = (meta.get("display_name") or folder_name).strip()
            sizes_meta = meta.get("sizes") or {}
            exists = meta.get("exists") or {}

            missing = {
                "master": not bool(exists.get("master", False)),
                "web": not bool(exists.get("web", False)),
                "sizes": []
            }

            for size in PRINT_SIZES:
                sm = sizes_meta.get(size) or {}
                
                files = sm.get("files") or []
                has_files = isinstance(files, list) and len(files) > 0
                
                if not has_files:
                    missing["sizes"].append(size)

            out[folder_name] = {
                "display_name": display_name,
                "missing": missing,
            }

        print(f"[MODEL DEBUG] Built {len(out)} studio items")
        return {k: out[k] for k in sorted(out.keys(), key=lambda x: x.lower())}