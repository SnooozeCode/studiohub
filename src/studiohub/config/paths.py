# studiohub/config/paths.py
"""Legacy path utilities that delegate to utils.path."""

from __future__ import annotations

from pathlib import Path
from studiohub.utils.path import (
    get_appdata_root as _get_appdata_root,
    get_config_path as _get_config_path,
    get_local_cache_root as _get_local_cache_root,
    get_poster_index_path as _get_poster_index_path,
)

# Re-export for backward compatibility
get_appdata_root = _get_appdata_root
get_config_path = _get_config_path
get_local_cache_root = _get_local_cache_root
get_poster_index_path = _get_poster_index_path