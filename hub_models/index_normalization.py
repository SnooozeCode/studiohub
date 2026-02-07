from __future__ import annotations

import re
from typing import Tuple, Dict


# =====================================================
# Configuration
# =====================================================

ACRONYMS = {
    "nasa",
    "cs",
    "fps",
}

# Filesystem-safe → display franchise names
FRANCHISE_ALIASES: Dict[str, str] = {
    "ram": "Rick and Morty",
    "rickandmorty": "Rick and Morty",
    "cs": "Counter-Strike",
    "counterstrike": "Counter-Strike",
    "callofduty": "Call of Duty",
}


# =====================================================
# Core helpers
# =====================================================

_WORD_RE = re.compile(
    r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[0-9]+"
)


def split_words(text: str) -> list[str]:
    """
    Split CamelCase, snake_case, kebab-case, and glued words into tokens.
    """
    if not text:
        return []
    text = text.replace("_", " ").replace("-", " ")
    return _WORD_RE.findall(text)


def normalize_words(words: list[str]) -> Tuple[str, str]:
    """
    Convert word list into (key, label).

    key   → snake_case, lowercase, stable
    label → Title Case with acronym preservation
    """
    key_parts = []
    label_parts = []

    for w in words:
        lw = w.lower()
        key_parts.append(lw)

        if lw in ACRONYMS:
            label_parts.append(w.upper())
        else:
            label_parts.append(w.capitalize())

    key = "_".join(key_parts)
    label = " ".join(label_parts)

    return key, label


# =====================================================
# Poster / patent normalization
# =====================================================

def normalize_poster_name(raw: str) -> Dict[str, str]:
    """
    Normalize a poster or patent folder name.

    Returns:
      {
        "key": "anatomical_body",
        "label": "Anatomical Body"
      }
    """
    words = split_words(raw)
    key, label = normalize_words(words)
    return {
        "key": key,
        "label": label,
    }


# =====================================================
# Background normalization
# =====================================================

def normalize_background_name(raw: str) -> Dict[str, str]:
    """
    Normalize a background variant name.

    Examples:
      AntiqueParchment -> antique_parchment / Antique Parchment
      chalkboard       -> chalkboard / Chalkboard
    """
    words = split_words(raw)
    key, label = normalize_words(words)
    return {
        "key": key,
        "label": label,
    }


# =====================================================
# Studio poster normalization
# =====================================================

def normalize_studio_name(raw: str) -> Dict[str, str]:
    """
    Normalize a studio poster name with franchise enrichment.

    Returns:
      {
        "franchise_key": "rick_and_morty",
        "franchise_label": "Rick and Morty",
        "title_key": "get_your_shit_alt",
        "title_label": "Get Your Shit Alt",
        "display_name": "Rick and Morty - Get Your Shit Alt"
      }
    """
    if not raw:
        return {
            "franchise_key": "",
            "franchise_label": "",
            "title_key": "",
            "title_label": "",
            "display_name": "",
        }

    s = raw.strip()

    # Filesystem-normalized string for alias matching
    fs = (
        s.lower()
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
    )

    # Franchise detection
    for alias_key, franchise_label in FRANCHISE_ALIASES.items():
        if fs.startswith(alias_key):
            remainder = s[len(alias_key):].lstrip("_- ")

            title_words = split_words(remainder)
            title_key, title_label = normalize_words(title_words)

            franchise_words = split_words(franchise_label)
            franchise_key, _ = normalize_words(franchise_words)

            display_name = (
                f"{franchise_label} - {title_label}"
                if title_label
                else franchise_label
            )

            return {
                "franchise_key": franchise_key,
                "franchise_label": franchise_label,
                "title_key": title_key,
                "title_label": title_label,
                "display_name": display_name,
            }

    # Fallback: no franchise detected
    words = split_words(s)
    title_key, title_label = normalize_words(words)

    return {
        "franchise_key": "",
        "franchise_label": "",
        "title_key": title_key,
        "title_label": title_label,
        "display_name": title_label,
    }
