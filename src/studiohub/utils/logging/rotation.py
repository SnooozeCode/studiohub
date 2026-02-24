# studiohub/utils/logging/rotation.py
"""Log rotation and management utilities."""

from __future__ import annotations

import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from studiohub.utils.logging.core import get_logger

logger = get_logger(__name__)


def get_log_stats(appdata_root: Path) -> dict:
    """Get statistics about log files."""
    log_dir = appdata_root / "logs"
    stats = {
        "total_size": 0,
        "file_count": 0,
        "files": []
    }
    
    for log_file in log_dir.glob("*.log*"):
        if log_file.name.endswith('.zip'):
            continue
        size = log_file.stat().st_size
        stats["total_size"] += size
        stats["file_count"] += 1
        stats["files"].append({
            "name": log_file.name,
            "size": size,
            "size_mb": size / (1024 * 1024),
            "modified": datetime.fromtimestamp(log_file.stat().st_mtime)
        })
    
    stats["total_size_mb"] = stats["total_size"] / (1024 * 1024)
    return stats


def archive_old_logs(appdata_root: Path, days: int = 30):
    """Archive logs older than specified days."""
    log_dir = appdata_root / "logs"
    archive_dir = log_dir / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    cutoff = datetime.now() - timedelta(days=days)
    logger = get_logger(__name__)
    
    for log_file in log_dir.glob("*.log*"):
        if log_file.name.endswith('.zip'):
            continue
        
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mtime < cutoff:
            # Compress old log
            zip_name = archive_dir / f"{log_file.stem}_{mtime.strftime('%Y%m%d')}.zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(log_file, log_file.name)
            
            # Remove original
            log_file.unlink()
            logger.info(f"Archived old log: {log_file.name}")