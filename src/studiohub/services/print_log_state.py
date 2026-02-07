# services/print_log_state.py
from __future__ import annotations

# =====================================================
# PrintLogState
#
# Canonical, read-only state for all print jobs.
#
# Responsibilities:
# - Load JSONL print log from disk
# - Parse print_log_v2 job records
# - Parse lightweight event records (failure / reprint)
# - Merge events onto base job rows (WITHOUT deleting fields)
# - Expose authoritative job rows for Qt models
# - Emit change notifications
#
# Explicitly does NOT:
# - Know about Qt views or tables
# - Format display strings
# - Compute dashboard metrics
# =====================================================

import json
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from PySide6 import QtCore


# =====================================================
# Canonical Job Row (base job + merged event fields)
# =====================================================

@dataclass(frozen=True)
class PrintJobRecord:
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
# Print Log State
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

    # -------------------------------------------------
    # Lifecycle
    # -------------------------------------------------

    def load(self) -> None:
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
                    if schema == "print_log_v2" and self._looks_like_base_job(record):
                        job = self._parse_base_job(record)
                        if job:
                            base_jobs[job.timestamp.isoformat()] = job
                        continue

                    # -----------------------------
                    # Event records (preferred)
                    # -----------------------------
                    if schema == "print_log_event_v1":
                        ev = self._parse_event_record(record)
                        if ev:
                            events.append(ev)
                        continue

                    # -----------------------------
                    # Back-compat: legacy failure correction record
                    # schema print_log_v2 but missing base fields
                    # -----------------------------
                    if schema == "print_log_v2" and self._looks_like_failure_correction(record):
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
        return list(self._jobs)

    # -------------------------------------------------
    # Persistence (events)
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
            "schema": "print_log_event_v1",
            "event": "failure",
            "parent_job_id": job_id,
            "failed_at": ts,
            "actual_in": float(actual_in),
            "reason": (reason or None),
        }

        try:
            self._append_jsonl(record)
            self.load()
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
            "schema": "print_log_event_v1",
            "event": "reprint",
            "parent_job_id": parent_job_id,
            "reprinted_at": ts,
            "reprint_job_id": reprint_job_id,
        }

        try:
            self._append_jsonl(record)
            self.load()
        except Exception as exc:
            self.error.emit(f"Failed to record reprint event: {exc}")

    # -------------------------------------------------
    # Internal parsing
    # -------------------------------------------------

    @staticmethod
    def _looks_like_base_job(record: Dict[str, Any]) -> bool:
        # Minimum base fields (so we don't accidentally treat event-like lines as jobs)
        return (
            "timestamp" in record
            and isinstance(record.get("files", []), list)
            and any(k in record for k in ("mode", "size", "files", "print_cost_usd"))
        )

    @staticmethod
    def _looks_like_failure_correction(record: Dict[str, Any]) -> bool:
        # Older format: schema print_log_v2 with failed=True and actual_in present,
        # but without mode/size/files.
        if record.get("failed") is not True:
            return False
        if "actual_in" not in record:
            return False
        if any(k in record for k in ("mode", "size", "files")):
            return False
        return True

    def _parse_base_job(self, record: Dict[str, Any]) -> Optional[PrintJobRecord]:
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
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return None

    def _apply_failure(self, job: PrintJobRecord, ev: Dict[str, Any]) -> PrintJobRecord:
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

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    @staticmethod
    def _normalize_source(value: Any) -> Optional[str]:
        if not value:
            return None
        v = str(value).lower()
        if v in ("archive", "patents"):
            return "archive"
        if v == "studio":
            return "studio"
        return None

    def _append_jsonl(self, record: Dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
