from __future__ import annotations

import json
import socket
from pathlib import Path
from datetime import datetime
from typing import Optional, Iterable

from studiohub.utils.logging import get_logger
from studiohub.utils.file_utils import atomic_write, FileLock

logger = get_logger(__name__)

# =====================================================
# Schema Constants
# =====================================================

PRINT_LOG_SCHEMA_V1 = "print_log_v1"
PRINT_LOG_SCHEMA_V2 = "print_log_v2"


# =====================================================
# Public API
# =====================================================

def append_print_log(
    *,
    log_path: Path,
    mode: str,
    size: str,
    print_cost_usd: float,

    # --- v2 inputs (preferred)
    files: Optional[Iterable[dict]] = None,

    # --- v2 analytics flags
    is_reprint: bool = False,
    waste_incurred: Optional[bool] = None,

    # --- v1 legacy inputs (fallback)
    file_1: Optional[str] = None,
    file_2: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """
    Append a print log entry atomically.

    - Uses print_log_v2 when `files` is provided
    - Falls back to print_log_v1 for legacy callers
    - Uses file locking and atomic writes to prevent corruption
    - Creates backups of the log file periodically
    """

    try:
        timestamp = datetime.now().isoformat(timespec="seconds")
        machine = socket.gethostname()

        # =================================================
        # v2 Path (authoritative, deterministic reprint)
        # =================================================

        if files is not None:
            record = {
                "schema": PRINT_LOG_SCHEMA_V2,
                "timestamp": timestamp,
                "machine": machine,
                "mode": mode,
                "size": size,
                "files": list(files),
                "print_cost_usd": float(print_cost_usd),
                "is_reprint": bool(is_reprint),
                "waste_incurred": bool(waste_incurred if waste_incurred is not None else is_reprint),
            }

        # =================================================
        # v1 Legacy Path (unchanged behavior)
        # =================================================

        else:
            record = {
                "schema": PRINT_LOG_SCHEMA_V1,
                "timestamp": timestamp,
                "machine": machine,
                "source": source,
                "mode": mode,
                "size": size,
                "file_1": file_1,
                "file_2": file_2,
                "print_cost_usd": float(print_cost_usd),
                "is_reprint": bool(is_reprint),
                "waste_incurred": bool(waste_incurred if waste_incurred is not None else is_reprint),
            }

        # Atomic append with locking
        _atomic_append_jsonl(log_path, record)

        return record

    except Exception as e:
        logger.error(f"Failed to write print log: {e}")
        return {}


def _atomic_append_jsonl(log_path: Path, record: dict) -> None:
    """
    Atomically append a JSON line to a log file.
    
    Uses file locking and atomic write to prevent corruption
    from concurrent writes or system crashes.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = log_path.with_suffix('.lock')
    
    # Determine if we should create a backup (every 100 writes)
    should_backup = _should_create_backup(log_path)
    
    try:
        # Use file lock to prevent concurrent writes
        with FileLock(lock_path, timeout=5.0):
            # Read existing content
            existing = ""
            if log_path.exists():
                existing = log_path.read_text(encoding='utf-8')
            
            # Append new line
            new_content = existing + json.dumps(record, ensure_ascii=False) + "\n"
            
            # Write atomically with optional backup
            atomic_write(log_path, new_content, encoding='utf-8', make_backup=should_backup)
            
    except TimeoutError:
        logger.error(f"Could not acquire lock for {log_path} after 5 seconds")
        # Fall back to simple append (risky, but better than nothing)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to append to log: {e}")
        raise


def _should_create_backup(log_path: Path, frequency: int = 100) -> bool:
    """
    Determine if we should create a backup based on file size and write frequency.
    
    Args:
        log_path: Path to the log file
        frequency: Create backup every N writes (approximated by file size)
    
    Returns:
        True if backup should be created
    """
    if not log_path.exists():
        return False
    
    try:
        # Approximate number of lines by file size (rough estimate)
        size = log_path.stat().st_size
        if size == 0:
            return False
        
        # Create backup every ~100 writes (assuming average line length ~200 bytes)
        # Also backup if file is large (>10MB)
        return (size // 20000) % frequency == 0 or size > 10 * 1024 * 1024
    except Exception:
        return False


# =====================================================
# Batch Operations (for multiple prints)
# =====================================================

def append_print_log_batch(
    log_path: Path,
    records: list[dict],
) -> bool:
    """
    Append multiple print log entries in a single atomic operation.
    
    Args:
        log_path: Path to log file
        records: List of log records to append
    
    Returns:
        True if successful, False otherwise
    """
    if not records:
        return True
    
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = log_path.with_suffix('.lock')
    
    try:
        with FileLock(lock_path, timeout=5.0):
            # Read existing content
            existing = ""
            if log_path.exists():
                existing = log_path.read_text(encoding='utf-8')
            
            # Append all new lines
            new_lines = []
            for record in records:
                new_lines.append(json.dumps(record, ensure_ascii=False))
            
            new_content = existing + "\n".join(new_lines) + ("\n" if new_lines else "")
            
            # Write atomically with backup
            atomic_write(log_path, new_content, encoding='utf-8', make_backup=True)
            
        logger.info(f"Successfully appended {len(records)} records to {log_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to append batch to log: {e}")
        return False


# =====================================================
# Log Maintenance
# =====================================================

def rotate_log_if_needed(log_path: Path, max_size_mb: int = 100) -> bool:
    """
    Rotate the log file if it exceeds the maximum size.
    
    Args:
        log_path: Path to log file
        max_size_mb: Maximum size in megabytes
    
    Returns:
        True if log was rotated, False otherwise
    """
    if not log_path.exists():
        return False
    
    try:
        size_mb = log_path.stat().st_size / (1024 * 1024)
        if size_mb <= max_size_mb:
            return False
        
        # Create rotated filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_path = log_path.with_name(f"{log_path.stem}_{timestamp}{log_path.suffix}")
        
        lock_path = log_path.with_suffix('.lock')
        
        with FileLock(lock_path, timeout=5.0):
            # Rename current log
            log_path.rename(rotated_path)
            
            # Create new empty log
            log_path.touch()
        
        logger.info(f"Rotated log {log_path} to {rotated_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to rotate log: {e}")
        return False