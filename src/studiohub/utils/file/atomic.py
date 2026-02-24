# studiohub/utils/file/atomic.py
"""Atomic file write operations."""

from __future__ import annotations

import os
import tempfile
import errno
import time
from pathlib import Path
from typing import Any, Optional
import json

from studiohub.utils.logging.core import get_logger
from studiohub.utils.file.backup import create_backup

logger = get_logger(__name__)


def atomic_write(
    path: Path,
    content: str,
    encoding: str = "utf-8",
    make_backup: bool = True,
    max_retries: int = 3,
) -> None:
    """
    Write content to a file atomically.
    
    Uses a temporary file and rename (atomic on most filesystems).
    Creates parent directories if they don't exist.
    
    Args:
        path: Target file path
        content: Content to write
        encoding: File encoding
        make_backup: Create a backup of existing file
        max_retries: Number of retry attempts on failure
    
    Raises:
        IOError: If write fails after all retries
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create backup of existing file if requested
    if make_backup and path.exists():
        create_backup(path)
    
    # Write with retries
    for attempt in range(max_retries):
        try:
            _atomic_write_impl(path, content, encoding)
            logger.debug(f"Successfully wrote {path} (attempt {attempt + 1})")
            return
        except (IOError, OSError) as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to write {path} after {max_retries} attempts: {e}")
                raise
            
            wait_time = 0.1 * (2 ** attempt)
            logger.warning(f"Write attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)


def atomic_write_json(
    path: Path,
    data: Any,
    encoding: str = "utf-8",
    indent: Optional[int] = 2,
    make_backup: bool = True,
) -> None:
    """
    Write JSON data atomically.
    
    Args:
        path: Target JSON file path
        data: Data to serialize to JSON
        encoding: File encoding
        indent: JSON indentation (None for compact)
        make_backup: Create a backup of existing file
    """
    content = json.dumps(data, indent=indent, ensure_ascii=False)
    atomic_write(path, content, encoding, make_backup)


def _atomic_write_impl(path: Path, content: str, encoding: str) -> None:
    """Internal implementation of atomic write."""
    fd, temp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.tmp-",
        suffix=".atomic",
        text=True
    )
    
    try:
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(fd)
        
        temp_file = Path(temp_path)
        
        if os.name == 'nt':  # Windows
            _atomic_replace_windows(temp_file, path)
        else:  # Unix-like
            temp_file.replace(path)
            
    except Exception:
        try:
            os.unlink(temp_path)
        except:
            pass
        raise


def _atomic_replace_windows(src: Path, dst: Path) -> None:
    """Atomic replace on Windows with retries."""
    max_retries = 5
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            if dst.exists():
                dst.unlink()
            src.replace(dst)
            return
        except PermissionError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(retry_delay * (2 ** attempt))
        except OSError as e:
            if e.errno == errno.EACCES:
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay * (2 ** attempt))
            else:
                raise


def safe_read_json(
    path: Path,
    default: Any = None,
    max_retries: int = 3,
) -> Any:
    """
    Safely read JSON file with retries and backup fallback.
    
    If primary file is corrupted, attempts to read from .bak backup.
    
    Args:
        path: Path to JSON file
        default: Default value if file doesn't exist or is corrupted
        max_retries: Number of retry attempts
    
    Returns:
        Parsed JSON data or default
    """
    path = Path(path)
    
    if not path.exists():
        return default
    
    for attempt in range(max_retries):
        try:
            with path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError) as e:
            if attempt == max_retries - 1:
                backup = path.with_suffix(path.suffix + '.bak')
                if backup.exists():
                    logger.warning(f"Primary file corrupted, trying backup: {backup}")
                    try:
                        with backup.open('r', encoding='utf-8') as f:
                            return json.load(f)
                    except Exception as backup_e:
                        logger.error(f"Backup also corrupted: {backup_e}")
                        return default
                return default
            
            wait_time = 0.1 * (2 ** attempt)
            logger.warning(f"Read attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
    
    return default