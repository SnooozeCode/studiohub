"""
Atomic file operations for StudioHub.

Provides:
- Atomic write operations (prevents corruption)
- Safe file reading with retries
- Backup creation before critical writes
- Cross-platform compatibility (Windows, macOS, Linux)
"""

from __future__ import annotations

import os
import tempfile
import shutil
import errno
from pathlib import Path
from typing import Optional, Callable, Any
from datetime import datetime
import json
import time

from studiohub.utils.logging import get_logger

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
        make_backup: Create a .bak backup of existing file
        max_retries: Number of retry attempts on failure
    
    Raises:
        IOError: If write fails after all retries
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create backup of existing file if requested
    if make_backup and path.exists():
        _create_backup(path)
    
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
            
            wait_time = 0.1 * (2 ** attempt)  # Exponential backoff
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
        make_backup: Create a .bak backup of existing file
    """
    content = json.dumps(data, indent=indent, ensure_ascii=False)
    atomic_write(path, content, encoding, make_backup)


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
    
    # Try primary file
    for attempt in range(max_retries):
        try:
            with path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError) as e:
            if attempt == max_retries - 1:
                # Try backup file
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


def _atomic_write_impl(path: Path, content: str, encoding: str) -> None:
    """
    Internal implementation of atomic write.
    Uses a temporary file in the same directory for atomic rename.
    """
    # Create temporary file in same directory
    fd, temp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.tmp-",
        suffix=".atomic",
        text=True
    )
    
    try:
        # Write content
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(fd)  # Ensure data is written to disk
        
        temp_file = Path(temp_path)
        
        # On Windows, need to handle permission issues
        if os.name == 'nt':  # Windows
            _atomic_replace_windows(temp_file, path)
        else:  # Unix-like
            temp_file.replace(path)
            
    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise


def _atomic_replace_windows(src: Path, dst: Path) -> None:
    """
    Atomic replace on Windows.
    Handles permission issues and retries.
    """
    max_retries = 5
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            # Remove destination if it exists (Windows requires this)
            if dst.exists():
                dst.unlink()
            src.replace(dst)
            return
        except PermissionError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(retry_delay * (2 ** attempt))
        except OSError as e:
            if e.errno == errno.EACCES:  # Permission denied
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay * (2 ** attempt))
            else:
                raise


def _create_backup(path: Path) -> Path:
    """
    Create a timestamped backup of a file.
    
    Returns:
        Path to backup file
    """
    backup_dir = path.parent / ".backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{path.name}.{timestamp}.bak"
    
    shutil.copy2(path, backup_path)
    logger.debug(f"Created backup: {backup_path}")
    
    # Clean up old backups (keep last 5)
    _cleanup_old_backups(backup_dir, path.name, keep=5)
    
    return backup_path


def _cleanup_old_backups(backup_dir: Path, base_name: str, keep: int = 5) -> None:
    """
    Keep only the most recent N backups.
    """
    backups = sorted(backup_dir.glob(f"{base_name}.*.bak"))
    
    if len(backups) <= keep:
        return
    
    for old_backup in backups[:-keep]:
        try:
            old_backup.unlink()
            logger.debug(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.warning(f"Failed to remove old backup {old_backup}: {e}")


def safe_copy(src: Path, dst: Path, make_backup: bool = True) -> None:
    """
    Safely copy a file with backup of destination.
    
    Args:
        src: Source file
        dst: Destination file
        make_backup: Create backup of existing destination
    """
    src = Path(src)
    dst = Path(dst)
    
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    if make_backup and dst.exists():
        _create_backup(dst)
    
    shutil.copy2(src, dst)
    logger.debug(f"Copied {src} -> {dst}")


class FileLock:
    """
    Simple file-based lock for cross-process synchronization.
    
    Usage:
        with FileLock("/path/to/lock.file"):
            # Critical section
    """
    
    def __init__(self, lock_path: Path, timeout: float = 10.0):
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self._fd = None
    
    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        while True:
            try:
                # Open with O_CREAT | O_EXCL for atomic creation
                self._fd = os.open(
                    str(self.lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                break
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock: {self.lock_path}")
                time.sleep(0.1)
        
        # Write PID to lock file for debugging
        os.write(self._fd, str(os.getpid()).encode())
        os.fsync(self._fd)
        
        return self
    
    def __exit__(self, *args):
        if self._fd is not None:
            os.close(self._fd)
            try:
                self.lock_path.unlink()
            except:
                pass