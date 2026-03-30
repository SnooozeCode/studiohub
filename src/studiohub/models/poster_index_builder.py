from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Set

from studiohub.constants import PRINT_SIZES

# =====================================================
# Constants
# =====================================================

MASTER_EXTENSIONS = {".ai", ".psd", ".psb"}
IGNORED_FILENAMES = {
    "desktop.ini",
    ".ds_store",
    "thumbs.db",
}
VALID_PRINT_EXTENSIONS = {
    ".tif",
    ".tiff",
}

# Archive backgrounds - these should NEVER be treated as studio variants
ARCHIVE_BACKGROUNDS = {
    "antiqueparchment": "Antique Parchment",
    "antique_parchment": "Antique Parchment",
    "antique-parchment": "Antique Parchment",
    "antique parchment": "Antique Parchment",
    "blueprint": "Blueprint",
    "blue_print": "Blueprint",
    "blue-print": "Blueprint",
    "chalkboard": "Chalkboard",
    "chalk_board": "Chalkboard",
    "chalk-board": "Chalkboard",
}


def _is_archive_background(stem: str) -> Optional[str]:
    """
    Check if a filename is an archive background.
    Returns the background label if found, None otherwise.
    """
    stem_lower = stem.lower()
    
    for pattern, label in ARCHIVE_BACKGROUNDS.items():
        if pattern in stem_lower:
            return label
    
    return None


def _detect_studio_variant(filename: str, stem: str) -> Optional[Tuple[str, bool]]:
    """
    Detect studio variants with improved naming convention.
    
    Rules:
    - Files WITHOUT suffix: "Default" variant (primary)
    - Files with "-light" suffix: "Light" variant
    - Files with "-alternate" suffix: "Alternate" variant
    - Files with "-alt" suffix: "Alternate" variant
    
    Returns (variant_name, is_default) or None
    """
    filename_lower = filename.lower()
    stem_lower = stem.lower()
    
    # Check for variant suffix at the END of the filename
    # Patterns: -light, _light, -alternate, _alternate, -alt, _alt
    
    # Check for Light variant
    if (filename_lower.endswith("-light.tif") or 
        filename_lower.endswith("_light.tif") or
        stem_lower.endswith("-light") or 
        stem_lower.endswith("_light")):
        # Make sure it's not a word like "lighthouse"
        if "lighthouse" not in stem_lower and "daylight" not in stem_lower:
            return ("Light", False)
    
    # Check for Alternate variant (supports both -alternate and -alt)
    if (filename_lower.endswith("-alternate.tif") or 
        filename_lower.endswith("_alternate.tif") or
        filename_lower.endswith("-alt.tif") or 
        filename_lower.endswith("_alt.tif") or
        stem_lower.endswith("-alternate") or 
        stem_lower.endswith("_alternate") or
        stem_lower.endswith("-alt") or 
        stem_lower.endswith("_alt")):
        return ("Alternate", False)
    
    # Check for Dark variant (keeping for backward compatibility)
    if (filename_lower.endswith("-dark.tif") or 
        filename_lower.endswith("_dark.tif") or
        stem_lower.endswith("-dark") or 
        stem_lower.endswith("_dark")):
        # Make sure it's not a word like "darkness"
        if "darkness" not in stem_lower:
            return ("Dark", False)
    
    # No variant suffix found - this is the Default variant
    return ("Default", True)


# =====================================================
# Poster scanning
# =====================================================

def scan_single_poster(poster_dir: Path, config_manager=None) -> Dict[str, Any]:
    """Scan a single poster, detecting both archive backgrounds and studio variants."""
    display_name = poster_dir.name.replace("_", " ")
    
    master_dir = poster_dir / "MASTER"
    web_dir = poster_dir / "WEB"

    has_master = _has_valid_master(master_dir)
    has_web = web_dir.exists() and any(
        f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        for f in web_dir.iterdir()
    )
        
    sizes: Dict[str, Any] = {}
    print_root = poster_dir / "PRINT"
    
    # Determine if this is archive or studio
    is_studio = config_manager is not None
    
    # First pass: collect all variants across ALL sizes
    all_variants: Set[str] = set()
    variant_files: Dict[str, Dict[str, Any]] = {}  # variant_name -> {path, label, etc.}
    
    if is_studio:
        # Scan all sizes to find all unique variants
        for size in PRINT_SIZES:
            size_dir = print_root / size
            if not size_dir.exists():
                continue
                
            valid_files = [
                p for p in size_dir.iterdir()
                if (
                    p.is_file()
                    and p.name.lower() not in IGNORED_FILENAMES
                    and p.suffix.lower() in VALID_PRINT_EXTENSIONS
                )
            ]
            
            tifs = [p for p in valid_files if p.suffix.lower() in {".tif", ".tiff"}]
            
            for tif in tifs:
                stem = tif.stem.lower()
                filename = tif.name.lower()
                
                result = _detect_studio_variant(filename, stem)
                if result:
                    variant_name, is_default = result
                    all_variants.add(variant_name)
                    
                    # Store the file info for this variant (use first occurrence)
                    if variant_name not in variant_files:
                        variant_files[variant_name] = {
                            "label": variant_name,
                            "path": str(tif),
                            "mtime": int(tif.stat().st_mtime),
                            "is_default": is_default,
                        }
    
    # Now process each size with knowledge of all variants
    for size in PRINT_SIZES:
        size_dir = print_root / size

        entry = {
            "exists": False,
            "files": [],
            "backgrounds": {},
        }

        if not size_dir.exists():
            sizes[size] = entry
            continue

        # Filter valid print files ONLY
        valid_files = [
            p for p in size_dir.iterdir()
            if (
                p.is_file()
                and p.name.lower() not in IGNORED_FILENAMES
                and p.suffix.lower() in VALID_PRINT_EXTENSIONS
            )
        ]

        entry["exists"] = bool(valid_files)

        tifs = [p for p in valid_files if p.suffix.lower() in {".tif", ".tiff"}]
        
        if not tifs:
            sizes[size] = entry
            continue
            
        inferred_backgrounds: Dict[str, Dict[str, Any]] = {}
        
        if is_studio:
            # =====================================================
            # STUDIO POSTERS - Detect variants
            # Only show children if there's MORE THAN ONE variant across ALL sizes
            # =====================================================
            if len(all_variants) > 1:
                # Multiple variants exist across sizes - show children
                for tif in tifs:
                    stem = tif.stem.lower()
                    filename = tif.name.lower()
                    
                    result = _detect_studio_variant(filename, stem)
                    if result:
                        variant_name, is_default = result
                        
                        # Use the stored file info
                        if variant_name in variant_files:
                            inferred_backgrounds[variant_name] = {
                                "exists": True,
                                "label": variant_name,
                                "path": str(tif),
                                "mtime": int(tif.stat().st_mtime),
                                "is_default": is_default,
                            }
                
                # Sort variants: Default first, then alphabetically
                if inferred_backgrounds:
                    sorted_backgrounds = sorted(
                        inferred_backgrounds.items(),
                        key=lambda x: (0 if x[1].get("is_default", False) else 1, x[0])
                    )
                    inferred_backgrounds = dict(sorted_backgrounds)
                    entry["backgrounds"] = inferred_backgrounds
                else:
                    entry["files"] = [str(p) for p in tifs]
            else:
                # Single variant across ALL sizes - no children needed
                entry["files"] = [str(p) for p in tifs]
                
        else:
            # =====================================================
            # ARCHIVE POSTERS - Detect backgrounds
            # Always show children for backgrounds (multiple backgrounds per size)
            # =====================================================
            for tif in tifs:
                stem = tif.stem.lower()
                
                archive_bg = _is_archive_background(stem)
                if archive_bg:
                    bg_key = archive_bg.replace(" ", "")
                    inferred_backgrounds[bg_key] = _bg(archive_bg, tif)
            
            if inferred_backgrounds:
                entry["backgrounds"] = inferred_backgrounds
            else:
                entry["files"] = [str(p) for p in tifs]

        sizes[size] = entry

    return {
        "display_name": display_name,
        "exists": {
            "master": has_master,
            "web": has_web,
        },
        "sizes": sizes,
    }


# =====================================================
# Helpers
# =====================================================

def _has_valid_master(master_dir: Path) -> bool:
    """
    A poster has a MASTER only if a valid master file exists.
    Directory existence alone is NOT sufficient.
    """
    if not master_dir.exists():
        return False

    for p in master_dir.iterdir():
        if (
            p.is_file()
            and p.suffix.lower() in MASTER_EXTENSIONS
            and not p.name.startswith("~")
        ):
            return True

    return False


def _bg(label: str, path: Path) -> Dict[str, Any]:
    return {
        "exists": True,
        "label": label,
        "path": str(path),
        "mtime": int(path.stat().st_mtime),
    }