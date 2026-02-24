from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

from PySide6 import QtCore

from studiohub.utils import (
    get_logger,
    log_performance,
    atomic_write,
    FileLock,
    recover_from_backup,
)

logger = get_logger(__name__)

INCHES_PER_FOOT = 12.0


class PaperLedger(QtCore.QObject):
    """
    Canonical authority for paper state.

    Backed by an append-only JSONL ledger with atomic writes and file locking
    to prevent corruption from concurrent access.
    """

    changed = QtCore.Signal()
    status_message = QtCore.Signal(str)

    def __init__(self, runtime_root: Path):
        super().__init__()

        self.log_path = runtime_root / "logs" / "paper_ledger.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.log_path.with_suffix('.lock')

        # Derived state (never persisted)
        self.paper_name: str | None = None
        self.total_ft: float | None = None
        self.remaining_ft: float | None = None
        self.last_replaced_ts: str | None = None

        # Raw event history
        self._events: list[dict] = []

        self._load()

    # -------------------------------------------------
    # Internal
    # -------------------------------------------------

    def _load(self) -> None:
        """Load events from disk with error recovery."""
        self._events.clear()

        if not self.log_path.exists():
            return

        try:
            # Read with file lock to prevent reading during write
            with FileLock(self.lock_path, timeout=2.0):
                content = self.log_path.read_text(encoding="utf-8")
        except TimeoutError:
            logger.warning("Could not acquire lock for reading, proceeding without lock")
            content = self.log_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read ledger: {e}")
            return

        # Parse lines, skipping invalid JSON
        valid_lines = 0
        for line_num, line in enumerate(content.splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                self._events.append(event)
                valid_lines += 1
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping invalid JSON at line {line_num}: {e}")
                continue

        logger.debug(f"Loaded {valid_lines} events from ledger")
        self._recompute_from_events()

    def _append(self, event: dict) -> None:
        """Append event atomically with file locking."""
        self._events.append(event)

        try:
            # Use file lock to prevent concurrent writes
            with FileLock(self.lock_path, timeout=5.0):
                # Read existing content
                existing = ""
                if self.log_path.exists():
                    existing = self.log_path.read_text(encoding='utf-8')
                
                # Append new event
                new_content = existing + json.dumps(event) + "\n"
                
                # Write atomically (create backup of entire file)
                atomic_write(self.log_path, new_content, make_backup=True)
                
        except TimeoutError:
            logger.error(f"Could not acquire lock for {self.log_path} after 5 seconds")
            # Still recompute from in-memory events
        except Exception as e:
            logger.error(f"Failed to append to ledger: {e}")
            # Don't raise - we still have the event in memory
        finally:
            # Recompute after every append to keep in-memory state honest
            self._recompute_from_events()

    @log_performance()
    def _recompute_from_events(self) -> None:
        """
        Replay the ledger to derive canonical paper state.
        This is the single source of truth.
        """
        self.paper_name = None
        self.total_ft = None
        self.remaining_ft = None
        self.last_replaced_ts = None

        remaining: float | None = None

        for event in self._events:
            et = event.get("event")

            if et == "paper_replaced":
                self.paper_name = event.get("paper_name")
                self.total_ft = float(event.get("total_ft", 0.0))
                remaining = self.total_ft
                self.last_replaced_ts = event.get("timestamp")

            elif et == "print_committed" and remaining is not None:
                length_in = float(event.get("length_in", 0.0))
                remaining -= length_in / INCHES_PER_FOOT

            elif et == "print_failed" and remaining is not None:
                planned_in = float(event.get("planned_in", 0.0))
                actual_in = float(event.get("actual_in", 0.0))
                restored_ft = max(
                    0.0,
                    (planned_in - actual_in) / INCHES_PER_FOOT,
                )
                remaining += restored_ft

        if remaining is not None:
            self.remaining_ft = max(0.0, remaining)

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def replace_paper(self, name: str, total_ft: float) -> None:
        logger.info(f"Replacing paper: {name} ({total_ft} ft)")
        event = {
            "event": "paper_replaced",
            "paper_name": name,
            "total_ft": float(total_ft),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._append(event)
        
        # Emit status message for notification system
        self.status_message.emit(f"Paper replaced: {name} ({total_ft} ft)")
        self.changed.emit()
        logger.debug("Paper replacement event appended")

    def commit_print(self, job_id: str, length_in: float) -> None:
        event = {
            "event": "print_committed",
            "job_id": job_id,
            "length_in": float(length_in),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._append(event)
        self.changed.emit()

    def fail_print(self, job_id: str, planned_in: float, actual_in: float) -> None:
        event = {
            "event": "print_failed",
            "job_id": job_id,
            "planned_in": float(planned_in),
            "actual_in": float(actual_in),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._append(event)
        self.changed.emit()

    def get_failed_jobs(self) -> dict[str, dict]:
        """
        Returns failed print jobs derived from persisted events.
        """
        failed: dict[str, dict] = {}

        for event in self._events:
            if event.get("event") != "print_failed":
                continue

            job_id = event.get("job_id")
            if not job_id:
                continue

            failed[job_id] = {
                "planned_in": float(event.get("planned_in", 0.0)),
                "actual_in": float(event.get("actual_in", 0.0)),
            }

        return failed

    def get_paper_changes(self) -> list[dict]:
        """
        Returns paper replacement events in chronological order.
        """
        changes: list[dict] = []

        for event in self._events:
            if event.get("event") != "paper_replaced":
                continue

            try:
                ts = datetime.fromisoformat(event["timestamp"])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            changes.append({
                "timestamp": ts,
                "paper_name": event.get("paper_name"),
                "total_ft": event.get("total_ft"),
            })

        return changes

    # -------------------------------------------------
    # Recovery Methods
    # -------------------------------------------------

    def verify_integrity(self) -> bool:
        """
        Verify that the on-disk ledger matches in-memory state.
        Returns True if consistent, False otherwise.
        """
        if not self.log_path.exists():
            return len(self._events) == 0

        try:
            with FileLock(self.lock_path, timeout=2.0):
                content = self.log_path.read_text(encoding='utf-8')
            
            disk_events = []
            for line in content.splitlines():
                if not line.strip():
                    continue
                try:
                    disk_events.append(json.loads(line))
                except json.JSONDecodeError:
                    return False
            
            # Compare number of events (don't compare content to avoid race)
            return len(disk_events) == len(self._events)
            
        except Exception as e:
            logger.error(f"Integrity check failed: {e}")
            return False

    def recover_from_backup(self) -> bool:
        """
        Attempt to recover the ledger from the most recent backup.
        Returns True if recovery succeeded.
        """
        return recover_from_backup(self.log_path)