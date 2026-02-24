# studiohub/utils/file/backup.py
"""Backup creation and recovery utilities."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from studiohub.utils.logging.core import get_logger

logger = get_logger(__name__)


def create_backup(path: Path, backup_dir: Optional[Path] = None) -> Path:
    """
    Create a timestamped backup of a file.
    
    Args:
        path: File to back up
        backup_dir: Directory to store backup (default: path.parent/.backups)
    
    Returns:
        Path to backup file
    """
    path = Path(path)
    
    if backup_dir is None:
        backup_dir = path.parent / ".backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{path.name}.{timestamp}.bak"
    
    shutil.copy2(path, backup_path)
    logger.debug(f"Created backup: {backup_path}")
    
    # Clean up old backups (keep last 5)
    cleanup_old_backups(backup_dir, path.name, keep=5)
    
    return backup_path


def cleanup_old_backups(backup_dir: Path, base_name: str, keep: int = 5) -> None:
    """
    Keep only the most recent N backups.
    
    Args:
        backup_dir: Directory containing backups
        base_name: Base filename to match
        keep: Number of backups to keep
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


def recover_from_backup(path: Path) -> bool:
    """
    Attempt to recover a file from the most recent backup.
    
    Args:
        path: Path to file to recover
    
    Returns:
        True if recovery succeeded
    """
    path = Path(path)
    backup_dir = path.parent / ".backups"
    
    if not backup_dir.exists():
        return False
    
    backups = sorted(backup_dir.glob(f"{path.name}.*.bak"))
    if not backups:
        return False
    
    latest_backup = backups[-1]
    try:
        shutil.copy2(latest_backup, path)
        logger.info(f"Recovered {path} from {latest_backup}")
        return True
    except Exception as e:
        logger.error(f"Failed to recover from backup: {e}")
        return False