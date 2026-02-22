from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from studiohub.constants import PRINT_SIZES

# =====================================================
# Constants
# =====================================================

MASTER_EXTENSIONS = {".tif", ".tiff", ".psd", ".psb"}
IGNORED_FILENAMES = {
    "desktop.ini",
    ".ds_store",
    "thumbs.db",
}
VALID_PRINT_EXTENSIONS = {
    ".tif",
    ".tiff",
}

# =====================================================
# Poster scanning (PURE, STATELESS)
# =====================================================

def scan_single_poster(poster_dir: Path) -> Dict[str, Any]:
    display_name = poster_dir.name.replace("_", " ")

    master_dir = poster_dir / "MASTER"
    web_dir = poster_dir / "WEB"

    has_master = _has_valid_master(master_dir)

    has_web = (
        web_dir.exists()
        and any(
            p.is_file()
            and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
            for p in web_dir.iterdir()
        )
    )

    sizes: Dict[str, Any] = {}
    print_root = poster_dir / "PRINT"

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

        # A size exists ONLY if it has valid print files
        entry["exists"] = bool(valid_files)

        tifs = [p for p in valid_files if p.suffix.lower() in {".tif", ".tiff"}]


        inferred_backgrounds: Dict[str, Dict[str, Any]] = {}

        for tif in tifs:
            stem = tif.stem.lower()

            if "antiqueparchment" in stem:
                inferred_backgrounds["AntiqueParchment"] = _bg("Antique Parchment", tif)
            elif "blueprint" in stem:
                inferred_backgrounds["Blueprint"] = _bg("Blueprint", tif)
            elif "chalkboard" in stem:
                inferred_backgrounds["Chalkboard"] = _bg("Chalkboard", tif)

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
