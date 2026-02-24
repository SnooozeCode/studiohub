"""Index logging functionality."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import socket
from typing import Optional, List, Dict, Any

from studiohub.utils import get_logger, log_performance, atomic_write, FileLock

logger = get_logger(__name__)

SCHEMA = "index_log_v1"


def append_index_log(
    *,
    log_path: Path,
    source: str,
    archive: int,
    studio: int,
    duration_ms: int,
    status: str,
) -> None:
    """
    Append a single index operation entry to a JSONL index log.

    This log is:
    - local to the machine
    - append-only
    - not shared across devices
    """
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "schema": SCHEMA,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "machine": socket.gethostname(),
            "source": source,              # startup | refresh_all | manual | etc
            "archive_count": archive,
            "studio_count": studio,
            "duration_ms": duration_ms,
            "status": status,              # OK | ERROR | started
        }

        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    except Exception as e:
        logger.warning(f"Failed to write index log: {e}")
        # Non-critical, continue


class IndexLogReader:
    """Reader for index log files."""
    
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
    
    def read_all(self) -> List[Dict[str, Any]]:
        """Read all entries from the index log."""
        entries = []
        
        if not self.log_path.exists():
            return entries
        
        try:
            with self.log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read index log: {e}")
        
        return entries
    
    def read_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Read the most recent entries."""
        entries = self.read_all()
        return entries[-limit:] if entries else []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about index operations."""
        entries = self.read_all()
        
        if not entries:
            return {
                "total_ops": 0,
                "avg_duration_ms": 0,
                "success_rate": 0,
                "last_op": None
            }
        
        successful = [e for e in entries if e.get("status") == "OK"]
        durations = [e.get("duration_ms", 0) for e in successful if e.get("duration_ms")]
        
        return {
            "total_ops": len(entries),
            "successful_ops": len(successful),
            "success_rate": (len(successful) / len(entries)) * 100 if entries else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "last_op": entries[-1] if entries else None
        }


def get_index_log_reader(log_path: Path) -> IndexLogReader:
    """Get a reader for the index log."""
    return IndexLogReader(log_path)