"""
Print log management for StudioHub.

Provides:
- PrintLogState: Canonical, read-only state for all print jobs
- PrintLogWriter: Atomic append operations for print logs
- PrintJobRecord: Data class representing a print job
- Batch operations and log maintenance utilities
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Iterable

from PySide6 import QtCore

from studiohub.utils import get_logger, log_performance, atomic_write, FileLock

logger = get_logger(__name__)

# =====================================================
# Schema Constants
# =====================================================

PRINT_LOG_SCHEMA_V1 = "print_log_v1"
PRINT_LOG_SCHEMA_V2 = "print_log_v2"
PRINT_LOG_EVENT_V1 = "print_log_event_v1"


# =====================================================
# Canonical Job Row (base job + merged event fields)
# =====================================================

@dataclass(frozen=True)
class PrintJobRecord:
    """
    Immutable record representing a print job with all its metadata.
    
    Base fields (from print_log_v2):
        timestamp: When the job was printed
        mode: "single" or "2up"
        size: Paper size (e.g., "12x18", "18x24", "24x36")
        files: List of files printed, each with path, source, poster_id
        cost_usd: Estimated cost of the print
    
    Derived fields (merged from events):
        failed: Whether the job failed
        failed_at: When the failure occurred
        actual_in: Actual paper length used (if failure)
        fail_reason: Why the job failed
        reprinted: Whether the job was reprinted
        reprinted_at: When the reprint occurred
    """
    
    # Base (from print_log_v2)
    timestamp: datetime
    mode: str
    size: str
    files: List[Dict[str, Any]]   # {path, source, poster_id}
    cost_usd: float

    # Derived / merged (from events)
    failed: bool = False
    failed_at: Optional[datetime] = None
    actual_in: Optional[float] = None
    fail_reason: Optional[str] = None

    reprinted: bool = False
    reprinted_at: Optional[datetime] = None


# =====================================================
# Print Log State (Read-only, Canonical)
# =====================================================

class PrintLogState(QtCore.QObject):
    """
    Single source of truth for print job history.

    - Base records: schema == "print_log_v2"
    - Event records (preferred): schema == "print_log_event_v1"
      - {"schema":"print_log_event_v1","event":"failure",  "parent_job_id":..., "failed_at":..., "actual_in":..., "reason":...}
      - {"schema":"print_log_event_v1","event":"reprint",  "parent_job_id":..., "reprinted_at":..., "reprint_job_id":...}

    Back-compat:
    - Legacy "failure correction" lines that are missing mode/size/files will be treated as a failure event.
    """

    changed = QtCore.Signal()
    error = QtCore.Signal(str)

    def __init__(self, log_path: Path, parent=None) -> None:
        super().__init__(parent)
        self._path = Path(log_path)
        self._jobs: List[PrintJobRecord] = []
        self._writer = PrintLogWriter(log_path)

    # -------------------------------------------------
    # Lifecycle
    # -------------------------------------------------

    @log_performance()
    def load(self) -> None:
        """Load and parse the print log from disk."""
        try:
            if not self._path.exists():
                self._jobs = []
                self.changed.emit()
                return

            base_jobs: Dict[str, PrintJobRecord] = {}
            events: List[Tuple[str, Dict[str, Any]]] = []

            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    schema = record.get("schema")

                    # -----------------------------
                    # Base job records
                    # -----------------------------
                    if schema == PRINT_LOG_SCHEMA_V2 and self._looks_like_base_job(record):
                        job = self._parse_base_job(record)
                        if job:
                            base_jobs[job.timestamp.isoformat()] = job
                        continue

                    # -----------------------------
                    # Event records (preferred)
                    # -----------------------------
                    if schema == PRINT_LOG_EVENT_V1:
                        ev = self._parse_event_record(record)
                        if ev:
                            events.append(ev)
                        continue

                    # -----------------------------
                    # Back-compat: legacy failure correction record
                    # schema print_log_v2 but missing base fields
                    # -----------------------------
                    if schema == PRINT_LOG_SCHEMA_V2 and self._looks_like_failure_correction(record):
                        ev = self._parse_legacy_failure_correction(record)
                        if ev:
                            events.append(ev)
                        continue

                    # Unknown -> ignore safely
                    continue

            # Apply events onto base jobs (do NOT delete base fields)
            merged = dict(base_jobs)
            for ev_type, ev in events:
                parent_job_id = str(ev.get("parent_job_id") or "")
                if not parent_job_id:
                    continue

                base = merged.get(parent_job_id)
                if not base:
                    continue

                if ev_type == "failure":
                    merged[parent_job_id] = self._apply_failure(base, ev)
                elif ev_type == "reprint":
                    merged[parent_job_id] = self._apply_reprint(base, ev)

            jobs = list(merged.values())
            jobs.sort(key=lambda j: j.timestamp, reverse=True)
            self._jobs = jobs
            self.changed.emit()

        except Exception as exc:
            self.error.emit(f"Print log load failed: {exc}")

    # -------------------------------------------------
    # Accessors
    # -------------------------------------------------

    @property
    def jobs(self) -> List[PrintJobRecord]:
        """Get all print jobs, newest first."""
        return list(self._jobs)

    # -------------------------------------------------
    # Persistence (events) - Delegated to writer
    # -------------------------------------------------

    def record_failure(
        self,
        *,
        job_id: str,
        actual_in: float,
        reason: str | None = None,
        failed_at: datetime | None = None,
    ) -> None:
        """
        Append a failure event for a given parent job.

        IMPORTANT:
        - Does NOT rewrite history
        - Does NOT delete base job fields
        """
        ts = (failed_at or datetime.now(timezone.utc)).isoformat(timespec="seconds")

        record = {
            "schema": PRINT_LOG_EVENT_V1,
            "event": "failure",
            "parent_job_id": job_id,
            "failed_at": ts,
            "actual_in": float(actual_in),
            "reason": (reason or None),
        }

        try:
            self._writer.append(record)
            self.load()  # Reload to incorporate the new event
        except Exception as exc:
            self.error.emit(f"Failed to record print failure: {exc}")

    def record_reprint(
        self,
        *,
        parent_job_id: str,
        reprinted_at: datetime | None = None,
        reprint_job_id: str | None = None,
    ) -> None:
        """
        Append a reprint event for a given parent job.

        This marks the ORIGINAL failed job as "reprinted" in the UI,
        while the new print job will appear as its own base row (written elsewhere).
        """
        ts = (reprinted_at or datetime.now(timezone.utc)).isoformat(timespec="seconds")

        record = {
            "schema": PRINT_LOG_EVENT_V1,
            "event": "reprint",
            "parent_job_id": parent_job_id,
            "reprinted_at": ts,
            "reprint_job_id": reprint_job_id,
        }

        try:
            self._writer.append(record)
            self.load()  # Reload to incorporate the new event
        except Exception as exc:
            self.error.emit(f"Failed to record reprint event: {exc}")

    # -------------------------------------------------
    # Internal parsing
    # -------------------------------------------------

    @staticmethod
    def _looks_like_base_job(record: Dict[str, Any]) -> bool:
        """Check if a record looks like a base job (has required fields)."""
        return (
            "timestamp" in record
            and isinstance(record.get("files", []), list)
            and any(k in record for k in ("mode", "size", "files", "print_cost_usd"))
        )

    @staticmethod
    def _looks_like_failure_correction(record: Dict[str, Any]) -> bool:
        """Check if a record is a legacy failure correction."""
        if record.get("failed") is not True:
            return False
        if "actual_in" not in record:
            return False
        if any(k in record for k in ("mode", "size", "files")):
            return False
        return True

    def _parse_base_job(self, record: Dict[str, Any]) -> Optional[PrintJobRecord]:
        """Parse a base job record into a PrintJobRecord."""
        try:
            ts = datetime.fromisoformat(record["timestamp"])
        except Exception:
            return None

        files: list[dict[str, Any]] = []
        for f in record.get("files", []) or []:
            if not isinstance(f, dict):
                continue
            source = self._normalize_source(f.get("source"))
            files.append({
                "path": f.get("path"),
                "source": source,
                "poster_id": f.get("poster_id") or f.get("name") or "",
            })

        return PrintJobRecord(
            timestamp=ts,
            mode=str(record.get("mode") or ""),
            size=str(record.get("size") or ""),
            files=files,
            cost_usd=float(record.get("print_cost_usd", 0.0)),
        )

    def _parse_event_record(self, record: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Parse an event record."""
        ev = str(record.get("event") or "").lower().strip()
        if ev not in ("failure", "reprint"):
            return None

        parent_job_id = record.get("parent_job_id")
        if not parent_job_id:
            return None

        if ev == "failure":
            return ("failure", {
                "parent_job_id": str(parent_job_id),
                "failed_at": record.get("failed_at"),
                "actual_in": record.get("actual_in"),
                "reason": record.get("reason"),
            })

        return ("reprint", {
            "parent_job_id": str(parent_job_id),
            "reprinted_at": record.get("reprinted_at"),
            "reprint_job_id": record.get("reprint_job_id"),
        })

    def _parse_legacy_failure_correction(self, record: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Parse a legacy failure correction record."""
        parent_job_id = str(record.get("timestamp") or "")
        if not parent_job_id:
            return None
        return ("failure", {
            "parent_job_id": parent_job_id,
            "failed_at": None,  # unknown
            "actual_in": record.get("actual_in"),
            "reason": record.get("reason") or None,
        })

    @staticmethod
    def _parse_dt(value: Any) -> Optional[datetime]:
        """Parse a datetime from a string."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return None

    def _apply_failure(self, job: PrintJobRecord, ev: Dict[str, Any]) -> PrintJobRecord:
        """Apply a failure event to a job record."""
        failed_at = self._parse_dt(ev.get("failed_at")) or job.failed_at
        try:
            actual_in = float(ev.get("actual_in")) if ev.get("actual_in") is not None else job.actual_in
        except Exception:
            actual_in = job.actual_in

        reason = ev.get("reason")
        if reason is not None:
            reason = str(reason)
        else:
            reason = job.fail_reason

        return PrintJobRecord(
            timestamp=job.timestamp,
            mode=job.mode,
            size=job.size,
            files=list(job.files),
            cost_usd=job.cost_usd,
            failed=True,
            failed_at=failed_at,
            actual_in=actual_in,
            fail_reason=reason,
            reprinted=job.reprinted,
            reprinted_at=job.reprinted_at,
        )

    def _apply_reprint(self, job: PrintJobRecord, ev: Dict[str, Any]) -> PrintJobRecord:
        """Apply a reprint event to a job record."""
        reprinted_at = self._parse_dt(ev.get("reprinted_at")) or job.reprinted_at
        return PrintJobRecord(
            timestamp=job.timestamp,
            mode=job.mode,
            size=job.size,
            files=list(job.files),
            cost_usd=job.cost_usd,
            failed=job.failed,
            failed_at=job.failed_at,
            actual_in=job.actual_in,
            fail_reason=job.fail_reason,
            reprinted=True,
            reprinted_at=reprinted_at,
        )

    @staticmethod
    def _normalize_source(value: Any) -> Optional[str]:
        """Normalize source string to 'archive' or 'studio'."""
        if not value:
            return None
        v = str(value).lower()
        if v in ("archive"):
            return "archive"
        if v == "studio":
            return "studio"
        return None


# =====================================================
# Print Log Writer (Atomic Operations)
# =====================================================

class PrintLogWriter:
    """
    Handles atomic append operations to the print log.
    
    Uses file locking and atomic writes to prevent corruption
    from concurrent writes or system crashes.
    """

    def __init__(self, log_path: Path):
        self._path = Path(log_path)
        self._lock_path = log_path.with_suffix('.lock')

    def append(self, record: dict) -> None:
        """
        Append a single record to the log atomically.
        
        Args:
            record: The record to append (will be JSON-serialized)
        """
        self._atomic_append_jsonl(record)

    def append_batch(self, records: list[dict]) -> bool:
        """
        Append multiple records in a single atomic operation.
        
        Args:
            records: List of records to append
        
        Returns:
            True if successful, False otherwise
        """
        if not records:
            return True

        try:
            with FileLock(self._lock_path, timeout=5.0):
                # Read existing content
                existing = ""
                if self._path.exists():
                    existing = self._path.read_text(encoding='utf-8')

                # Append all new lines
                new_lines = [json.dumps(r, ensure_ascii=False) for r in records]
                new_content = existing + "\n".join(new_lines) + ("\n" if new_lines else "")

                # Write atomically with backup
                atomic_write(self._path, new_content, encoding='utf-8', make_backup=True)

            logger.info(f"Successfully appended {len(records)} records to {self._path}")
            return True

        except Exception as e:
            logger.error(f"Failed to append batch to log: {e}")
            return False

    def _atomic_append_jsonl(self, record: dict) -> None:
        """
        Atomically append a JSON line to the log file.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Determine if we should create a backup (every 100 writes)
        should_backup = self._should_create_backup()

        try:
            # Use file lock to prevent concurrent writes
            with FileLock(self._lock_path, timeout=5.0):
                # Read existing content
                existing = ""
                if self._path.exists():
                    existing = self._path.read_text(encoding='utf-8')

                # Append new line
                new_content = existing + json.dumps(record, ensure_ascii=False) + "\n"

                # Write atomically with optional backup
                atomic_write(self._path, new_content, encoding='utf-8', make_backup=should_backup)

        except TimeoutError:
            logger.error(f"Could not acquire lock for {self._path} after 5 seconds")
            # Fall back to simple append (risky, but better than nothing)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to append to log: {e}")
            raise

    def _should_create_backup(self, frequency: int = 100) -> bool:
        """
        Determine if we should create a backup based on file size.
        
        Args:
            frequency: Create backup every N writes (approximated by file size)
        
        Returns:
            True if backup should be created
        """
        if not self._path.exists():
            return False

        try:
            size = self._path.stat().st_size
            if size == 0:
                return False

            # Create backup every ~100 writes (assuming average line length ~200 bytes)
            # Also backup if file is large (>10MB)
            return (size // 20000) % frequency == 0 or size > 10 * 1024 * 1024
        except Exception:
            return False

    def rotate_if_needed(self, max_size_mb: int = 100) -> bool:
        """
        Rotate the log file if it exceeds the maximum size.
        
        Args:
            max_size_mb: Maximum size in megabytes
        
        Returns:
            True if log was rotated, False otherwise
        """
        if not self._path.exists():
            return False

        try:
            size_mb = self._path.stat().st_size / (1024 * 1024)
            if size_mb <= max_size_mb:
                return False

            # Create rotated filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_path = self._path.with_name(f"{self._path.stem}_{timestamp}{self._path.suffix}")

            with FileLock(self._lock_path, timeout=5.0):
                # Rename current log
                self._path.rename(rotated_path)
                # Create new empty log
                self._path.touch()

            logger.info(f"Rotated log {self._path} to {rotated_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to rotate log: {e}")
            return False


# =====================================================
# Convenience Functions (Backward Compatibility)
# =====================================================

def append_print_log(
    *,
    log_path: Path,
    mode: str,
    size: str,
    print_cost_usd: float,
    files: Optional[Iterable[dict]] = None,
    is_reprint: bool = False,
    waste_incurred: Optional[bool] = None,
    file_1: Optional[str] = None,
    file_2: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """
    Convenience function for backward compatibility.
    Delegates to PrintLogWriter.
    """
    timestamp = datetime.now().isoformat(timespec="seconds")
    machine = socket.gethostname()

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

    writer = PrintLogWriter(log_path)
    writer.append(record)
    return record


def append_print_log_batch(log_path: Path, records: list[dict]) -> bool:
    """
    Convenience function for backward compatibility.
    Delegates to PrintLogWriter.
    """
    writer = PrintLogWriter(log_path)
    return writer.append_batch(records)


def rotate_log_if_needed(log_path: Path, max_size_mb: int = 100) -> bool:
    """
    Convenience function for backward compatibility.
    Delegates to PrintLogWriter.
    """
    writer = PrintLogWriter(log_path)
    return writer.rotate_if_needed(max_size_mb)