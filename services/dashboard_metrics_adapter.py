from __future__ import annotations

# =====================================================
# Dashboard Adapters
#
# Read-only adapter layer between application state
# and dashboard views.
#
# Rules:
# - No disk I/O
# - No UI imports
# - No side effects
# =====================================================

from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict

from PySide6 import QtCore

from studiohub.services.poster_index_state import PosterIndexState


# =====================================================
# Poster Index–derived Metrics
# =====================================================

@dataclass(frozen=True)
class DashboardMetricsSnapshot:
    total_posters: int
    by_source_total: Dict[str, int]
    by_source_with_master: Dict[str, int]
    by_source_missing_master: Dict[str, int]
    by_source_issues: Dict[str, int]
    by_source_missing_files: Dict[str, int]
    by_size: Dict[str, int]
    last_updated: datetime | None


class DashboardMetricsAdapter(QtCore.QObject):
    """
    Computes dashboard metrics from PosterIndexState.

    Owns:
    - poster totals
    - completeness
    - issues
    - missing files

    Does NOT:
    - know about print history
    - know about UI
    """

    changed = QtCore.Signal()

    def __init__(
        self,
        *,
        poster_index_state: PosterIndexState,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._state = poster_index_state
        self._snapshot: DashboardMetricsSnapshot | None = None

        self._state.changed.connect(self._recompute)
        self._recompute()

    @property
    def snapshot(self) -> DashboardMetricsSnapshot:
        if self._snapshot is None:
            raise RuntimeError("DashboardMetricsAdapter accessed before computation")
        return self._snapshot

    # -------------------------------------------------

    def _recompute(self) -> None:
        if not self._state.is_loaded:
            self._snapshot = DashboardMetricsSnapshot(
                total_posters=0,
                by_source_total={},
                by_source_with_master={},
                by_source_missing_master={},
                by_source_issues={},
                by_source_missing_files={},
                by_size={},
                last_updated=None,
            )
            self.changed.emit()
            return

        snapshot = self._state.snapshot
        posters_by_source = snapshot.get("posters", {})

        total_posters = 0
        by_source_total: dict[str, int] = {}
        by_source_with_master: dict[str, int] = {}
        by_source_missing_master: dict[str, int] = {}
        by_source_issues: dict[str, int] = {}
        by_source_missing_files: dict[str, int] = {}
        by_size: dict[str, int] = {}

        for source, posters in posters_by_source.items():
            source_total = 0
            source_with_master = 0
            source_missing_master = 0
            source_issues = 0
            source_missing_files = 0

            for meta in posters.values():
                source_total += 1
                total_posters += 1

                exists = meta.get("exists", {})
                missing_files_for_poster = 0

                # Master / Web
                if not exists.get("master", False):
                    source_missing_master += 1
                    missing_files_for_poster += 1
                else:
                    source_with_master += 1

                if not exists.get("web", False):
                    missing_files_for_poster += 1

                sizes = meta.get("sizes", {}) or {}

                # Archive semantics (size × background)
                if source == "archive":
                    for size_meta in sizes.values():
                        if not size_meta.get("exists", False):
                            backgrounds = size_meta.get("backgrounds", {}) or {}
                            missing_files_for_poster += len(backgrounds)
                            continue

                        for bg_meta in size_meta.get("backgrounds", {}).values():
                            if not bg_meta.get("exists", False):
                                missing_files_for_poster += 1

                # Studio semantics (one file per size)
                elif source == "studio":
                    for size_meta in sizes.values():
                        if not size_meta.get("exists", False):
                            missing_files_for_poster += 1

                if missing_files_for_poster > 0:
                    source_issues += 1

                source_missing_files += missing_files_for_poster

                for size_name in sizes.keys():
                    by_size[size_name] = by_size.get(size_name, 0) + 1

            by_source_total[source] = source_total
            by_source_with_master[source] = source_with_master
            by_source_missing_master[source] = source_missing_master
            by_source_issues[source] = source_issues
            by_source_missing_files[source] = source_missing_files

        self._snapshot = DashboardMetricsSnapshot(
            total_posters=total_posters,
            by_source_total=by_source_total,
            by_source_with_master=by_source_with_master,
            by_source_missing_master=by_source_missing_master,
            by_source_issues=by_source_issues,
            by_source_missing_files=by_source_missing_files,
            by_size=by_size,
            last_updated=datetime.now(timezone.utc),
        )

        self.changed.emit()


# =====================================================
# Print Count Metrics (Month-over-Month)
# =====================================================

@dataclass(frozen=True)
class PrintCountSnapshot:
    archive_this_month: int
    studio_this_month: int
    archive_last_month: int
    studio_last_month: int
    delta_archive: int
    delta_studio: int
    delta_total: int


class PrintCountAdapter(QtCore.QObject):
    """
    Month-over-month print counts derived from PrintLogState (v2 records).

    Primary source-of-truth:
      - PrintJobRecord.files[*].source  ("archive" | "studio")

    Fallback:
      - If source is missing/None, infer by filename via poster_index_state.
    """

    changed = QtCore.Signal()

    def __init__(
        self,
        *,
        print_log_state,
        poster_index_state: PosterIndexState,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._state = print_log_state
        self._poster_index_state = poster_index_state

        self._snapshot: PrintCountSnapshot | None = None

        # Only used as fallback when a file entry has no source
        self._filename_to_source: dict[str, str] = {}

        # React to state changes
        if hasattr(self._state, "changed"):
            self._state.changed.connect(self._recompute)

        self._poster_index_state.changed.connect(self._on_index_changed)

        self._recompute()

    @property
    def snapshot(self) -> PrintCountSnapshot:
        if self._snapshot is None:
            raise RuntimeError("PrintCountAdapter accessed before computation")
        return self._snapshot

    # -------------------------------------------------

    @staticmethod
    def _normalize_source(src: str | None) -> str | None:
        if not src:
            return None
        v = str(src).lower()
        if v in ("patents", "archive"):
            return "archive"
        if v == "studio":
            return "studio"
        return None

    def _on_index_changed(self) -> None:
        self._filename_to_source.clear()
        self._recompute()

    def _build_filename_map_if_needed(self) -> None:
        if self._filename_to_source or not self._poster_index_state.is_loaded:
            return

        index = self._poster_index_state.snapshot.get("posters", {})
        for source, posters in index.items():
            src_norm = self._normalize_source(source)
            if src_norm not in ("archive", "studio"):
                continue

            for meta in posters.values():
                sizes = meta.get("sizes", {}) or {}
                for size_meta in sizes.values():
                    # Studio has empty backgrounds; archive has backgrounds populated
                    for bg in (size_meta.get("backgrounds", {}) or {}).values():
                        path = bg.get("path")
                        if not path:
                            continue
                        name = Path(str(path)).name.lower()
                        self._filename_to_source[name] = src_norm

    def _infer_source_from_path(self, path: str | None) -> str | None:
        if not path:
            return None
        self._build_filename_map_if_needed()
        filename = Path(str(path)).name.lower()
        return self._filename_to_source.get(filename)

    def _recompute(self) -> None:

        now = datetime.now(timezone.utc)
        this_month = (now.year, now.month)
        last_month = ((now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1))

        a_this = s_this = 0
        a_last = s_last = 0

        # PrintLogState contract: .jobs -> List[PrintJobRecord]
        entries = getattr(self._state, "jobs", []) or []

        # -------------------------------------------------
        # Aggregate counts
        # -------------------------------------------------
        for job in entries:
            ts = getattr(job, "timestamp", None)
            if not isinstance(ts, datetime):
                continue

            key = (ts.year, ts.month)
            files = getattr(job, "files", None) or []

            for f in files:
                if not isinstance(f, dict):
                    continue

                source = self._normalize_source(f.get("source"))
                if source not in ("archive", "studio"):
                    # Fallback inference (only if needed)
                    source = self._infer_source_from_path(f.get("path"))

                if source not in ("archive", "studio"):
                    continue

                if key == this_month:
                    if source == "archive":
                        a_this += 1
                    else:
                        s_this += 1
                elif key == last_month:
                    if source == "archive":
                        a_last += 1
                    else:
                        s_last += 1

        # -------------------------------------------------
        # Snapshot
        # -------------------------------------------------
        self._snapshot = PrintCountSnapshot(
            archive_this_month=a_this,
            studio_this_month=s_this,
            archive_last_month=a_last,
            studio_last_month=s_last,
            delta_archive=a_this - a_last,
            delta_studio=s_this - s_last,
            delta_total=(a_this + s_this) - (a_last + s_last),
        )
        self.changed.emit()
