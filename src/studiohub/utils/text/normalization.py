from __future__ import annotations
import re
from typing import Dict, Tuple

# =====================================================
# Constants (Maintained for External Exports)
# =====================================================

ACRONYMS = {"nasa", "cs", "fps", "ram", "tv", "id", "usa"}

# Renamed for internal use but exported as FRANCHISE_ALIASES for external files
FRANCHISE_ALIASES: Dict[str, str] = {
    "rickandmorty": "Rick and Morty",
    "fallout": "Fallout",
    "valorant": "Valorant",
    "nasa": "NASA",
    "callofduty": "Call of Duty",
    "fortnite": "Fortnite",
    "counterstrike": "Counter-Strike",
    "cs": "Counter-Strike",
    "destiny": "Destiny",
}

# =====================================================
# Core Formatting Engine
# =====================================================

def split_words(text: str) -> list[str]:
    """
    Maintained for external use. 
    Uses the improved regex to tokenize strings.
    """
    if not text: return []
    # Handle 'and' spacing
    text = re.sub(r'([a-z])(and)([A-Z])', r'\1 \2 \3', text, flags=re.IGNORECASE)
    # Tokenize CamelCase and Acronyms
    return re.findall(r'[A-Z][a-z]+|[A-Z]{2,}(?=[A-Z][a-z]|$)|[A-Z]+|[a-z]+|[0-9]+', text)

def _format_text(text: str) -> str:
    """Internal helper to join tokens into a clean label."""
    words = split_words(text)
    parts = []
    for w in words:
        lw = w.lower()
        if lw == "and": parts.append("and")
        elif lw in ACRONYMS or (w.isupper() and len(w) > 1): parts.append(w.upper())
        else: parts.append(w.capitalize())
    return " ".join(parts)

# =====================================================
# Exported Functions (Maintained for Backwards Compat)
# =====================================================

def normalize_studio_name(raw: str) -> Dict[str, str]:
    """
    The new primary logic. 
    1. Checks for '__' (New System)
    2. Checks for FRANCHISE_ALIASES (Legacy System)
    3. Fallback to clean TitleCase
    """
    # New System (__ separator)
    if "__" in raw:
        series_raw, title_raw = raw.split("__", 1)
        series_label = _format_text(series_raw)
        title_label = _format_text(title_raw)
        return {
            "display_name": f"{series_label} - {title_label}",
            "key": raw.lower().replace("__", "_"),
            "franchise_label": series_label,
            "title_label": title_label
        }

    # Legacy System (Franchise Mapping)
    raw_lower = raw.lower()
    for key, clean_label in FRANCHISE_ALIASES.items():
        if raw_lower.startswith(key):
            title_part = raw[len(key):].lstrip("_").lstrip("-")
            title_label = _format_text(title_part)
            return {
                "display_name": f"{clean_label} - {title_label}" if title_label else clean_label,
                "key": f"{key}_{title_part.lower()}".strip("_"),
                "franchise_label": clean_label,
                "title_label": title_label
            }

    # Fallback
    label = _format_text(raw)
    return {
        "display_name": label,
        "key": raw.lower(),
        "franchise_label": "",
        "title_label": label
    }

def normalize_poster_name(raw: str) -> Dict[str, str]:
    """Alias for normalize_studio_name used by IndexManager."""
    res = normalize_studio_name(raw)
    # Add legacy field names if some older code expects 'label' instead of 'display_name'
    res["label"] = res["display_name"]
    return res

def normalize_name(raw: str) -> str:
    """Returns just the string label. Used by Sidebar UI."""
    return normalize_studio_name(raw)["display_name"]

def normalize_background_name(raw: str) -> Dict[str, str]:
    """Used for Studio variants in the UI."""
    label = _format_text(raw)
    return {"key": raw.lower(), "label": label}

def normalize_patent_name(raw: str) -> str:
    """
    Maintained for Archive Patent files (e.g., 'Tombstone-AntiqueParchment').
    """
    if "-" in raw:
        left, right = raw.split("-", 1)
        return f"{_format_text(left)} - {_format_text(right)}"
    return _format_text(raw)

# =====================================================
# New Archive-Specific Helpers (For your refined scanner)
# =====================================================

def normalize_archive_folder(folder_name: str) -> str:
    return _format_text(folder_name)

def normalize_archive_filename(filename: str, folder_name: str) -> str:
    stem = filename.rsplit('.', 1)[0]
    # Replace the folder name prefix to isolate the background name
    pattern = re.compile(re.escape(folder_name), re.IGNORECASE)
    bg_raw = pattern.sub("", stem).strip("_").strip("-")
    return _format_text(bg_raw) if bg_raw else "Standard"