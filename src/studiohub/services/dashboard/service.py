from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from studiohub.services.dashboard.snapshot import (
    DashboardSnapshot,
    CompletenessSlice,
    MonthlyPrintCountSlice,
    PaperSlice,
    InkSlice,
    MonthlyCostBreakdown,
    IndexSlice,
)


# ============================================================
# Helpers
# ============================================================

def _start_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _normalize_source(src: str | None) -> str | None:
    if not src:
        return None
    v = str(src).lower()
    if v in ("patents", "archive"):
        return "archive"
    if v == "studio":
        return "studio"
    return None


# ============================================================
# DashboardService
# ============================================================

class DashboardService:
    """
    Single source of truth for dashboard state.

    Unifies:
      - dashboard_metrics.py (disk IO, consumables, costs, recents)
      - dashboard_metrics_adapter.py (index-derived completeness + print deltas)

    Rules:
      - No UI imports
      - Snapshot is immutable and UI-ready
      - Light caching for disk reads
    """

    def __init__(
        self,
        *,
        config_manager,
        paper_ledger=None,
        poster_index_state=None,         # optional, but enables archive/studio stats & print source inference
        print_log_path: Path | None = None,
        print_log_state=None,            # optional, preferred for v2 job aggregation
        index_log_path: Path | None = None,
    ) -> None:
        self._cfg = config_manager
        self._paper_ledger = paper_ledger
        self._poster_index_state = poster_index_state
        self._print_log_state = print_log_state

        # Disk paths
        self._print_log_path = Path(print_log_path) if print_log_path else None

        if index_log_path:
            self._index_log_path = Path(index_log_path)
        else:
            # matches your legacy logic
            appdata = Path(os.getenv("APPDATA", Path.home()))
            self._index_log_path = appdata / "SnooozeCo" / "StudioHub" / "logs" / "index_log.jsonl"

        # Caches
        self._print_log_cache_rows: list[dict[str, Any]] = []
        self._print_log_cache_mtime: float | None = None

        self._filename_to_source: dict[str, str] = {}  # for print fallback inference

    # --------------------------------------------------------
    # Public
    # --------------------------------------------------------

    def get_snapshot(self) -> DashboardSnapshot:
        """
        Build and return a complete dashboard snapshot.
        """

        # Completeness
        archive, studio = self._build_completeness()

        # Operational metrics
        monthly_print_count = self._monthly_print_count()
        paper = self._build_paper()
        ink = self._build_ink()

        # Costs
        monthly_costs = self._build_monthly_costs()

        # History
        recent_prints = self._build_recent_prints()
        recent_index_events = self._build_recent_index_events()

        # Index KPI
        index = self._build_index()

        return DashboardSnapshot(
            archive=archive,
            studio=studio,
            index=index,
            monthly_print_count=monthly_print_count,
            recent_prints=recent_prints,
            monthly_costs=monthly_costs,
            revenue=None,
            notes=None,
        )



    # --------------------------------------------------------
    # Index completeness (from poster index state snapshot)
    # --------------------------------------------------------

    def _build_completeness(self) -> tuple[CompletenessSlice, CompletenessSlice]:
        """
        Computes:
          - issues: posters with any missing required files
          - missing_files: total missing file count
          - complete_fraction: (total - issues)/total
        """
        default = CompletenessSlice(issues=0, missing_files=0, complete_fraction=0.0)

        state = self._poster_index_state
        if not state or not getattr(state, "is_loaded", False):
            return default, default

        snapshot = getattr(state, "snapshot", None) or {}
        posters_by_source = snapshot.get("posters", {}) or {}

        # normalize keys: "patents" -> "archive"
        normalized: dict[str, dict] = {}
        for src, posters in posters_by_source.items():
            n = _normalize_source(src) or str(src).lower()
            normalized[n] = posters

        archive_stats = self._compute_source_completeness(normalized.get("archive", {}) or {}, source="archive")
        studio_stats = self._compute_source_completeness(normalized.get("studio", {}) or {}, source="studio")
        return archive_stats, studio_stats

    def _compute_source_completeness(self, posters: dict, *, source: str) -> CompletenessSlice:
        total = 0
        issues = 0
        missing_files = 0

        for _poster_id, meta in (posters or {}).items():
            total += 1
            exists = (meta or {}).get("exists", {}) or {}
            sizes = (meta or {}).get("sizes", {}) or {}

            missing_for_poster = 0

            # Master/Web basic expectations
            if not exists.get("master", False):
                missing_for_poster += 1
            if not exists.get("web", False):
                missing_for_poster += 1

            # Archive semantics: size exists + backgrounds exist
            if source == "archive":
                for size_meta in sizes.values():
                    if not (size_meta or {}).get("exists", False):
                        backgrounds = (size_meta or {}).get("backgrounds", {}) or {}
                        missing_for_poster += len(backgrounds)
                        continue
                    for bg_meta in (size_meta or {}).get("backgrounds", {}).values():
                        if not (bg_meta or {}).get("exists", False):
                            missing_for_poster += 1

            # Studio semantics: one file per size
            elif source == "studio":
                for size_meta in sizes.values():
                    if not (size_meta or {}).get("exists", False):
                        missing_for_poster += 1

            if missing_for_poster > 0:
                issues += 1
            missing_files += missing_for_poster

        frac = ((total - issues) / total) if total > 0 else 0.0
        return CompletenessSlice(
            issues=int(issues),
            missing_files=int(missing_files),
            complete_fraction=float(max(0.0, min(1.0, frac))),
        )

    # --------------------------------------------------------
    # Monthly Print Count (this month vs last month)
    # --------------------------------------------------------

    def _monthly_print_count(self) -> MonthlyPrintCountSlice:
        """
        Uses PrintLogState (v2) if available, otherwise falls back to disk log rows.
        """
        now = datetime.now(timezone.utc)
        this_month = (now.year, now.month)
        last_month = ((now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1))

        a_this = s_this = 0
        a_last = s_last = 0

        # Prefer PrintLogState jobs if present
        entries = []
        if self._print_log_state is not None:
            entries = getattr(self._print_log_state, "jobs", []) or []

        if entries:
            self._maybe_build_filename_map()

            for job in entries:
                ts = getattr(job, "timestamp", None)
                if not isinstance(ts, datetime):
                    continue

                key = (ts.year, ts.month)
                files = getattr(job, "files", None) or []

                for f in files:
                    if not isinstance(f, dict):
                        continue

                    src = _normalize_source(f.get("source"))
                    if src not in ("archive", "studio"):
                        src = self._infer_source_from_path(f.get("path"))

                    if src not in ("archive", "studio"):
                        continue

                    if key == this_month:
                        a_this += 1 if src == "archive" else 0
                        s_this += 1 if src == "studio" else 0
                    elif key == last_month:
                        a_last += 1 if src == "archive" else 0
                        s_last += 1 if src == "studio" else 0

        else:
            # fallback to v1 disk log rows
            rows = self._load_print_log_rows()
            for row in rows:
                ts = _parse_iso(row.get("timestamp"))
                if not ts:
                    continue
                key = (ts.year, ts.month)

                src = _normalize_source(row.get("source"))
                if src not in ("archive", "studio"):
                    continue

                qty = int(row.get("quantity", 1))
                if key == this_month:
                    a_this += qty if src == "archive" else 0
                    s_this += qty if src == "studio" else 0
                elif key == last_month:
                    a_last += qty if src == "archive" else 0
                    s_last += qty if src == "studio" else 0

        return MonthlyPrintCountSlice(
            archive_this_month=int(a_this),
            studio_this_month=int(s_this),
            archive_last_month=int(a_last),
            studio_last_month=int(s_last),
            delta_archive=int(a_this - a_last),
            delta_studio=int(s_this - s_last),
            delta_total=int((a_this + s_this) - (a_last + s_last)),
        )


    def _maybe_build_filename_map(self) -> None:
        """
        Fallback inference: if print files lack a 'source', infer it from filename
        using the poster index state.
        """
        if self._filename_to_source:
            return

        state = self._poster_index_state
        if not state or not getattr(state, "is_loaded", False):
            return

        index = getattr(state, "snapshot", None) or {}
        posters = (index.get("posters", {}) or {})

        # normalize sources
        for src, posters_map in posters.items():
            src_norm = _normalize_source(src)
            if src_norm not in ("archive", "studio"):
                continue

            for meta in (posters_map or {}).values():
                sizes = (meta or {}).get("sizes", {}) or {}
                for size_meta in sizes.values():
                    for bg in ((size_meta or {}).get("backgrounds", {}) or {}).values():
                        p = bg.get("path")
                        if not p:
                            continue
                        name = Path(str(p)).name.lower()
                        self._filename_to_source[name] = src_norm

    def _infer_source_from_path(self, path: str | None) -> str | None:
        if not path:
            return None
        self._maybe_build_filename_map()
        filename = Path(str(path)).name.lower()
        return self._filename_to_source.get(filename)

    # --------------------------------------------------------
    # Paper (authoritative from PaperLedger + config metadata)
    # --------------------------------------------------------

    def _build_paper(self) -> PaperSlice:
        ledger = self._paper_ledger

        name = str(self._cfg.get("consumables", "paper_name", "") or "")
        last_replaced = _parse_iso(str(self._cfg.get("consumables", "paper_roll_reset_at", "") or ""))

        total_ft = 0.0
        remaining_ft = 0.0

        if ledger and getattr(ledger, "total_ft", None) is not None:
            try:
                total_ft = float(ledger.total_ft or 0.0)
            except Exception:
                total_ft = 0.0

        if ledger and getattr(ledger, "remaining_ft", None) is not None:
            try:
                remaining_ft = float(ledger.remaining_ft or 0.0)
            except Exception:
                remaining_ft = 0.0

        percent = int((remaining_ft / total_ft) * 100) if total_ft > 0 else 0
        percent = max(0, min(100, percent))

        # optional estimate using avg feet/print if available from print log state
        est_prints_left: Optional[int] = None
        avg = getattr(self._print_log_state, "avg_feet_per_print", None) if self._print_log_state else None
        try:
            avg_val = float(avg) if avg else 0.0
        except Exception:
            avg_val = 0.0
        if avg_val > 0:
            est_prints_left = int(remaining_ft / avg_val)

        return PaperSlice(
            paper_name=name,
            total_length_ft=total_ft,
            remaining_ft=remaining_ft,
            remaining_percent=percent,
            estimated_prints_left=est_prints_left,
            last_replaced=last_replaced,
        )


    # --------------------------------------------------------
    # Ink (estimated from config reset + print log)
    # --------------------------------------------------------

    def _build_ink(self) -> InkSlice:
        start_pct = self._cfg.get("consumables", "ink_reset_percent", 100)
        reset_at = self._cfg.get("consumables", "ink_reset_at", "")

        try:
            start_pct_int = int(start_pct)
        except Exception:
            start_pct_int = 100

        reset_at_dt = _parse_iso(str(reset_at) if reset_at is not None else "")
        if not reset_at_dt:
            return InkSlice(remaining_percent=start_pct_int, last_replaced=None)

        used_pct = 0.0

        # use disk rows because v2 jobs do not encode ink usage; matches legacy behavior
        for entry in self._load_print_log_rows():
            ts = _parse_iso(entry.get("timestamp"))
            if not ts or ts < reset_at_dt:
                continue
            qty = int(entry.get("quantity", 1))
            used_pct += 0.15 * qty  # legacy conservative estimate

        remaining = max(int(start_pct_int - used_pct), 0)
        return InkSlice(remaining_percent=remaining, last_replaced=reset_at_dt)

    # --------------------------------------------------------
    # Monthly costs (estimated from print log sizes + config)
    # --------------------------------------------------------

    def _estimate_print_cost_usd(self, *, sheet_size: str) -> float:
        try:
            w_str, h_str = sheet_size.lower().split("x", 1)
            w_in = float(w_str)
            h_in = float(h_str)
        except Exception:
            return 0.0

        paper_cost_per_foot = float(
            self._cfg.get("print_cost", "paper_cost_per_foot", 47.95 / 60.0)
        )
        waste_pct = float(
            self._cfg.get("print_cost", "waste_pct", 0.10)
        )
        ink_cost_per_ml = float(
            self._cfg.get("print_cost", "ink_cost_per_ml", 32.0 / 70.0)
        )
        ink_ml_per_sqft = float(
            self._cfg.get("print_cost", "ink_ml_per_sqft", 70.0 / (11.0 * 6.0))
        )

        length_in = max(w_in, h_in)
        paper_feet = (length_in / 12.0) * (1.0 + max(0.0, waste_pct))
        paper_cost = paper_feet * paper_cost_per_foot

        area_sqft = (w_in * h_in) / 144.0
        ink_ml = area_sqft * ink_ml_per_sqft
        ink_cost = ink_ml * ink_cost_per_ml

        cost = paper_cost + ink_cost
        return float(cost) if cost > 0 else 0.0

    def _build_monthly_costs(self) -> MonthlyCostBreakdown:
        now = datetime.now()
        month_start = _start_of_month(now)

        prints = 0
        ink_cost = 0.0
        paper_cost = 0.0

        rows = self._load_print_log_rows()

        for row in rows:
            ts = _parse_iso(row.get("timestamp"))
            if not ts or ts < month_start:
                continue

            qty = int(row.get("quantity", 1))
            size = row.get("size") or ""
            if not size:
                continue

            prints += qty

            # Separate ink/paper as in your legacy logic
            try:
                w_str, h_str = str(size).lower().split("x", 1)
                w_in = float(w_str)
                h_in = float(h_str)
            except Exception:
                continue

            length_in = max(w_in, h_in)
            paper_feet = (length_in / 12.0)

            paper_cost_per_foot = float(
                self._cfg.get("print_cost", "paper_cost_per_foot", 47.95 / 60.0)
            )
            paper_cost += paper_feet * paper_cost_per_foot * qty

            area_sqft = (w_in * h_in) / 144.0
            ink_ml_per_sqft = float(
                self._cfg.get("print_cost", "ink_ml_per_sqft", 70.0 / (11.0 * 6.0))
            )
            ink_cost_per_ml = float(
                self._cfg.get("print_cost", "ink_cost_per_ml", 32.0 / 70.0)
            )
            ink_cost += area_sqft * ink_ml_per_sqft * ink_cost_per_ml * qty

        shipping_per_print = float(self._cfg.get("consumables", "shipping_cost_per_print", 0.0) or 0.0)
        shipping = prints * shipping_per_print

        return MonthlyCostBreakdown(
            ink=float(ink_cost),
            paper=float(paper_cost),
            shipping_supplies=float(shipping),
            prints=int(prints),
        )

    # --------------------------------------------------------
    # Recent print jobs (matches your panel expectations)
    # --------------------------------------------------------

    def _get_recent_print_jobs(self, limit: int = 2) -> list[dict]:
        """
        Returns list[dict] shaped exactly like your RecentPrintJobsPanel expects:
          - v2: {"schema":"print_log_v2","mode":...,"files":[{"poster_id","path",...}, ...], ...}
          - v1: {"schema":"print_log_v1","file_1":..., ...}
        """
        jobs: list[dict] = []
        rows = self._load_print_log_rows()

        # treat disk rows as "print jobs" for the dashboard
        for entry in reversed(rows):
            schema = entry.get("schema") or "print_log_v1"

            # v2: already contains files list
            if schema == "print_log_v2":
                jobs.append(entry)
            else:
                # v1: normalize minimal fields used by the panel
                jobs.append({
                    "schema": "print_log_v1",
                    "mode": entry.get("mode") or "single",
                    "timestamp": entry.get("timestamp"),
                    "file_1": entry.get("file_1") or entry.get("file") or "",
                    "file_2": entry.get("file_2") or "",
                })

            if len(jobs) >= limit:
                break

        return jobs

    def _build_recent_prints(self) -> list[dict]:
        """
        Build recent prints for dashboard panels.

        Returns a list of dicts shaped for the UI (timestamp + a human label),
        while preserving the raw job dict under 'raw' for future expansion.
        """
        jobs = self._get_recent_print_jobs(limit=5)

        out: list[dict] = []
        for job in jobs:
            if not isinstance(job, dict):
                # extremely defensive; shouldn't happen
                continue

            schema = job.get("schema", "print_log_v1")
            ts = job.get("timestamp", "")

            # v2 jobs: have files list
            if schema == "print_log_v2":
                files = job.get("files") or []
                # build a compact label
                if files and isinstance(files, list):
                    first = files[0] if isinstance(files[0], dict) else {}
                    poster_id = first.get("poster_id") or ""
                    size = first.get("size") or job.get("size") or ""
                    label = f"{poster_id} {size}".strip() or "Print job"
                else:
                    label = "Print job"

            # v1 jobs: you normalized file_1/file_2 earlier
            else:
                f1 = (job.get("file_1") or "").strip()
                f2 = (job.get("file_2") or "").strip()
                if f1 and f2:
                    label = f"{Path(f1).name} + {Path(f2).name}"
                elif f1:
                    label = Path(f1).name
                else:
                    label = "Print job"

            out.append(
                {
                    "timestamp": ts,   # keep as string (panel can show it)
                    "label": label,
                    "raw": job,        # keep full payload for later UI upgrades
                }
            )

        return out


    # --------------------------------------------------------
    # Recent index events (matches your panel expectations)
    # --------------------------------------------------------

    def _get_recent_index_events(self, limit: int = 5) -> list[dict]:
        events: list[dict] = []

        path = self._index_log_path
        if not path or not path.exists():
            return events

        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if entry.get("schema") != "index_log_v1":
                        continue

                    ts = _parse_iso(entry.get("timestamp"))
                    if not ts:
                        continue

                    events.append({
                        "patents": entry.get("patents_count", 0),
                        "studio": entry.get("studio_count", 0),
                        "timestamp": ts,
                        "status": entry.get("status"),
                    })
        except Exception:
            return []

        events.sort(key=lambda e: e["timestamp"], reverse=True)
        return events[:limit]

    def _build_recent_index_events(self) -> list[dict]:
        """
        Build recent index events for dashboard panels.
        """
        events = self._get_recent_index_events(limit=5)

        out: list[dict] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue

            ts = ev.get("timestamp", "")
            kind = ev.get("type") or ev.get("event") or "index"
            detail = ev.get("detail") or ev.get("message") or ""

            label = f"{kind}: {detail}".strip(": ")

            out.append(
                {
                    "timestamp": ts,
                    "label": label or "Index event",
                    "raw": ev,
                }
            )

        return out

    def _build_index(self) -> IndexSlice:
        events = self._get_recent_index_events(limit=1)

        if not events:
            return IndexSlice(
                title="Index",
                subtitle="No index activity",
                status="unknown",
                timestamp=None,
            )

        ev = events[0]

        status = ev.get("status") or ev.get("result") or "ok"
        subtitle = ev.get("message") or ev.get("detail") or "Index updated"

        return IndexSlice(
            title="Index",
            subtitle=subtitle,
            status=status,
            timestamp=ev.get("timestamp"),
        )



    # --------------------------------------------------------
    # Disk log loading with mtime caching
    # --------------------------------------------------------

    def _load_print_log_rows(self) -> list[dict[str, Any]]:
        """
        Loads print log jsonl rows from disk (v1 + v2 compatible).
        Cached by file mtime for performance.
        """
        if not self._print_log_path:
            return []

        path = self._print_log_path
        if not path.exists():
            return []

        try:
            mtime = path.stat().st_mtime
        except Exception:
            mtime = None

        if mtime is not None and self._print_log_cache_mtime == mtime:
            return self._print_log_cache_rows

        rows: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            rows = []

        self._print_log_cache_rows = rows
        self._print_log_cache_mtime = mtime
        return rows
