# studiohub/utils/text/__init__.py
"""Text normalization utilities for StudioHub."""

from __future__ import annotations

from studiohub.utils.text.normalization import (
    normalize_name,
    normalize_poster_name,
    normalize_background_name,
    normalize_studio_name,
    normalize_patent_name,
    split_words,
    ACRONYMS,
    FRANCHISE_ALIASES,
)

__all__ = [
    "normalize_name",
    "normalize_poster_name",
    "normalize_background_name",
    "normalize_studio_name",
    "normalize_patent_name",
    "split_words",
    "ACRONYMS",
    "FRANCHISE_ALIASES",
]