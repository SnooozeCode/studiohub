# studiohub/utils/path/resolver.py
"""Path resolution for application assets, config, and data directories."""

from __future__ import annotations

import os
from pathlib import Path
from importlib import resources
from typing import Optional

APP_VENDOR = "SnooozeCo"
APP_NAME = "StudioHub"


def asset_path(*parts: str) -> str:
    """
    Return an absolute filesystem path to a bundled asset.
    Works for editable installs, namespace packages, and packaging.
    
    Args:
        *parts: Path parts relative to the assets directory
        
    Returns:
        Absolute path to the asset as a string
        
    Example:
        >>> asset_path("icons", "sidebar", "menu.svg")
        'C:/.../studiohub/assets/icons/sidebar/menu.svg'
    """
    try:
        # Try using importlib.resources (Python 3.7+)
        base = resources.files("studiohub")
        path = base.joinpath("assets")
        for part in parts:
            path = path.joinpath(part)
        return str(Path(path))
    except (ImportError, AttributeError):
        # Fallback for older Python or when running as script
        # This assumes the script is running from the project root
        base = Path(__file__).resolve().parents[3]  # Go up to project root
        path = base / "assets"
        for part in parts:
            path = path / part
        return str(path)


def get_appdata_root() -> Path:
    """
    Get the application data directory.
    
    Returns:
        Path to the app data directory (e.g., %APPDATA%\\SnooozeCo\\StudioHub)
    """
    base = Path(os.getenv("APPDATA", Path.home()))
    root = base / APP_VENDOR / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_config_path() -> Path:
    """
    Get the path to the configuration file.
    
    Returns:
        Path to config.json in the app data directory
    """
    return get_appdata_root() / "config.json"


def get_local_cache_root() -> Path:
    """
    Get the root directory for local cache files.
    
    Returns:
        Path to the cache directory (created if it doesn't exist)
    """
    cache_root = get_appdata_root() / "cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def get_poster_index_path() -> Path:
    """
    Get the path to the poster index JSON file.
    
    Returns:
        Path to poster_index.json in the cache directory
    """
    return get_local_cache_root() / "poster_index.json"


def get_logs_root() -> Path:
    """
    Get the root directory for log files.
    
    Returns:
        Path to the logs directory (created if it doesn't exist)
    """
    logs_root = get_appdata_root() / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    return logs_root


def get_media_root() -> Path:
    """
    Get the root directory for media files (artwork, etc.).
    
    Returns:
        Path to the media directory (created if it doesn't exist)
    """
    media_root = get_appdata_root() / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    return media_root


def get_notes_path() -> Path:
    """
    Get the path to the dashboard notes file.
    
    Returns:
        Path to dashboard_notes.json in the notes directory
    """
    notes_dir = get_appdata_root() / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    return notes_dir / "dashboard_notes.json"


def get_print_log_path(runtime_root: Optional[Path] = None) -> Path:
    """
    Get the path to the print log file.
    
    Args:
        runtime_root: Optional runtime root path. If not provided,
                     uses appdata root.
    
    Returns:
        Path to print_log.jsonl
    """
    if runtime_root:
        base = runtime_root
    else:
        base = get_appdata_root()
    
    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "print_log.jsonl"


def get_paper_ledger_path(runtime_root: Optional[Path] = None) -> Path:
    """
    Get the path to the paper ledger file.
    
    Args:
        runtime_root: Optional runtime root path. If not provided,
                     uses appdata root.
    
    Returns:
        Path to paper_ledger.jsonl
    """
    if runtime_root:
        base = runtime_root
    else:
        base = get_appdata_root()
    
    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "paper_ledger.jsonl"