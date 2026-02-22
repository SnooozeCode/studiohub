from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

from PySide6 import QtCore

INCHES_PER_FOOT = 12.0


class PaperLedger(QtCore.QObject):
    """
    Canonical authority for paper state.

    Backed by an append-only JSONL ledger.
    All derived state (remaining_ft, totals) is recomputed
    by replaying events to guarantee cross-machine consistency.
    """

    changed = QtCore.Signal()
    status_message = QtCore.Signal(str)

    def __init__(self, runtime_root: Path):
        super().__init__()

        self.log_path = runtime_root / "logs" / "paper_ledger.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

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
        self._events.clear()

        if not self.log_path.exists():
            return

        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except Exception:
                continue
            self._events.append(event)

        self._recompute_from_events()

    def _append(self, event: dict) -> None:
        self._events.append(event)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

        # Recompute after every append to keep in-memory state honest
        self._recompute_from_events()

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
