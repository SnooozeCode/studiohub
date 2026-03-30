# studiohub/models/missing_files_model_qt.py

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Set

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
    # Get exclusions for a source
    # -------------------------------------------------

    def _get_exclusions(self, source: str) -> Dict[str, Set[str]]:
        """Get excluded sizes for all posters in a source."""
        exclusions = self.config_manager.get("poster_exclusions", source, {})
        return {poster_key: set(excluded_sizes) for poster_key, excluded_sizes in exclusions.items()}

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
            print(f"[DEBUG] Loading index for {source}...")
            index = self._load_index()
            print(f"[DEBUG] Index loaded, has {len(index.get('posters', {}).get(source, {}))} posters")
            
            exclusions = self._get_exclusions(source)
            
            if source == "archive":
                print("[DEBUG] Building archive status...")
                new_data = self._build_archive_status(index, exclusions)
                
                # Compare safely
                if str(self._cache_archive) != str(new_data):
                    self._cache_archive = new_data
                    
            else:  # studio
                print("[DEBUG] Building studio status...")
                new_data = self._build_studio_status(index, exclusions)
                print(f"[DEBUG] Studio status built, has {len(new_data)} posters")
                
                # Compare safely
                try:
                    if self._cache_studio != new_data:
                        self._cache_studio = new_data
                except TypeError as e:
                    print(f"[DEBUG] Comparison error: {e}, assuming changed")
                    self._cache_studio = new_data

            # Emit the data from cache
            cache_data = self.get_cache(source)
            print(f"[DEBUG] Emitting data for {source}, {len(cache_data)} posters")
            self.scan_finished.emit(source, cache_data)

        except Exception as e:
            import traceback
            print(f"[ERROR] in refresh for {source}: {e}")
            traceback.print_exc()
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
            raise ValueError(f"poster_index.json cache_version must be 2 (found {data.get('cache_version')})")
        
        posters = data.get("posters")
        if not isinstance(posters, dict):
            raise ValueError("poster_index.json missing 'posters' object")
        
        return data

    # -------------------------------------------------
    # Status Builders (with exclusions)
    # -------------------------------------------------

    def _build_archive_status(self, index: Dict[str, Any], exclusions: Dict[str, Set[str]]) -> Dict[str, Any]:
        """Build status data for ALL archive posters, respecting exclusions."""
        posters = (index.get("posters") or {}).get("archive") or {}
        out: Dict[str, Any] = {}

        for folder_name, meta in sorted(posters.items(), key=lambda kv: kv[0].lower()):
            if not isinstance(meta, dict):
                continue

            display_name = (meta.get("display_name") or folder_name).strip()
            sizes_meta = meta.get("sizes") or {}
            exists = meta.get("exists") or {}
            
            # Get excluded sizes for this poster
            excluded_sizes = exclusions.get(folder_name, set())

            # Track what's missing
            missing = {
                "master": not bool(exists.get("master", False)),
                "web": not bool(exists.get("web", False)),
                "sizes": [],
                "backgrounds": {}
            }

            # Check each size
            for size in PRINT_SIZES:
                # Skip excluded sizes - they are not considered missing
                if size in excluded_sizes:
                    continue
                    
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



    def _build_studio_status(self, index: Dict[str, Any], exclusions: Dict[str, Set[str]]) -> Dict[str, Any]:
        """Build status data for studio posters, including ALL variants."""
        posters = index.get("posters", {}).get("studio", {})
        print(f"[DEBUG] _build_studio_status: Found {len(posters)} studio posters")
        
        out: Dict[str, Any] = {}

        for folder_name, meta in sorted(posters.items(), key=lambda kv: kv[0].lower()):
            if not isinstance(meta, dict):
                continue

            display_name = (meta.get("display_name") or folder_name).strip()
            sizes_meta = meta.get("sizes") or {}
            exists = meta.get("exists") or {}
            
            excluded_sizes = exclusions.get(folder_name, set())

            missing = {
                "master": not bool(exists.get("master", False)),
                "web": not bool(exists.get("web", False)),
                "sizes": [],
                "backgrounds": {}  # This will store ALL variants with their missing sizes
            }

            # First, collect ALL variants across all sizes
            all_variants = {}
            for size in PRINT_SIZES:
                if size in excluded_sizes:
                    continue
                    
                size_meta = sizes_meta.get(size) or {}
                backgrounds = size_meta.get("backgrounds") or {}
                
                for variant_key, variant_rec in backgrounds.items():
                    if not isinstance(variant_rec, dict):
                        continue
                    
                    variant_key_str = str(variant_key)
                    if variant_key_str not in all_variants:
                        all_variants[variant_key_str] = {
                            "label": str(variant_rec.get("label", variant_key_str)),
                            "sizes": []  # Will populate with sizes where this variant EXISTS
                        }
                    # Add this size to the variant's list of existing sizes
                    all_variants[variant_key_str]["sizes"].append(size)

            # Now, for EACH variant, determine which sizes it's missing from
            # This ensures ALL variants appear in the backgrounds dictionary
            for variant_key_str, variant_info in all_variants.items():
                existing_sizes = set(variant_info["sizes"])
                
                # Initialize this variant in missing["backgrounds"]
                missing["backgrounds"][variant_key_str] = {
                    "label": variant_info["label"],
                    "sizes": []  # Will store sizes where this variant is MISSING
                }
                
                # Check each size for this variant
                for size in PRINT_SIZES:
                    if size in excluded_sizes:
                        continue
                    
                    # If the variant doesn't exist for this size, it's missing
                    if size not in existing_sizes:
                        missing["backgrounds"][variant_key_str]["sizes"].append(size)

            # Also track which sizes are completely missing (no variants at all)
            for size in PRINT_SIZES:
                if size in excluded_sizes:
                    continue
                    
                size_meta = sizes_meta.get(size) or {}
                backgrounds = size_meta.get("backgrounds") or {}
                
                # If size has no variants at all, mark it as missing
                if not backgrounds:
                    if not size_meta.get("exists", False):
                        missing["sizes"].append(size)
                else:
                    # Size has variants - check if any exist
                    has_any_variant = any(
                        isinstance(bg_rec, dict) and bg_rec.get("exists") is True
                        for bg_rec in backgrounds.values()
                    )
                    if not has_any_variant:
                        missing["sizes"].append(size)

            out[folder_name] = {
                "display_name": display_name,
                "missing": missing,
            }

        return out