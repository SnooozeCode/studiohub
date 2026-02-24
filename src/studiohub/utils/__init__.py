# studiohub/utils/__init__.py
"""
Utility modules for StudioHub.

Provides:
- File operations (atomic writes, locking, backups)
- Text normalization (names, acronyms, franchises)
- Logging setup and utilities
- Path resolution
"""

from __future__ import annotations

# Import from submodules
from studiohub.utils.file import (
    atomic_write,
    atomic_write_json,
    safe_read_json,
    FileLock,
    create_backup,
    recover_from_backup,
    cleanup_old_backups,
)

from studiohub.utils.text import (
    normalize_name,
    normalize_poster_name,
    normalize_background_name,
    normalize_studio_name,
    normalize_patent_name,
    split_words,
    ACRONYMS,
    FRANCHISE_ALIASES,
)

from studiohub.utils.logging import (
    setup_logging,
    get_logger,
    set_root_logger,
    log_performance,
    log_critical_operation,
    archive_old_logs,
    get_log_stats,
)

from studiohub.utils.path import asset_path, get_appdata_root

__all__ = [
    # File
    "atomic_write",
    "atomic_write_json",
    "safe_read_json",
    "FileLock",
    "create_backup",
    "recover_from_backup",
    "cleanup_old_backups",
    
    # Text
    "normalize_name",
    "normalize_poster_name",
    "normalize_background_name",
    "normalize_studio_name",
    "normalize_patent_name",
    "split_words",
    "ACRONYMS",
    "FRANCHISE_ALIASES",
    
    # Logging
    "setup_logging",
    "get_logger",
    "set_root_logger",
    "log_performance",
    "log_critical_operation",
    "archive_old_logs",
    "get_log_stats",
    
    # Path
    "asset_path",
    "get_appdata_root",
]