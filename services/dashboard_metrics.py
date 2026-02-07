from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Any

import psutil
import re
from PySide6 import QtCore
from studiohub.config_manager import ConfigManager

# NOTE:
# Dashboard jobs intentionally expose `files: []`
# and must NOT be treated as raw print_log rows.

# ============================================================
# Helpers
# ============================================================

def start_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None

# ============================================================
# Dashboard Metrics Service
# ============================================================

class DashboardMetrics(QtCore.QObject):

    paper_changed = QtCore.Signal(dict)
    ink_changed = QtCore.Signal(dict)

    def __init__(self, *, print_log_path: Path, paper_ledger):
        super().__init__()

        self.paper_ledger = paper_ledger
        self._print_log_rows: list[dict] = []
        self.print_log_path = Path(print_log_path)
        self._rows: list[dict[str, Any]] = []
        self._index: dict[str, Any] = {}
        self.reload()

        self.config = ConfigManager()

    # ============================================================
    # Replace Paper and Ink: Auto Update Dashboard
    # ============================================================

    def replace_paper(self, *, name: str, total_length: float) -> None:
        """
        Replace the active paper roll.

        total_length is expected to be in FEET.
        """

        now = datetime.now().isoformat()

        # Persist authoritative values
        self.config.set("consumables", "paper_name", name)
        self.config.set("consumables", "paper_roll_start_feet", float(total_length))
        self.config.set("consumables", "paper_roll_reset_at", now)

        # Recompute derived metrics
        status = self.get_paper_status()

        # Emit live update (no reloads, no parent traversal)
        self.paper_changed.emit({
            "name": name,
            "feet": status["feet"],
            "percent": status["percent"],
            "reset_at": now,
        })

    def replace_ink(self) -> None:
        """
        Replace ink cartridges.

        Resets ink percentage to 100 and emits a live update.
        """

        now = datetime.now().isoformat()

        # Persist authoritative values
        self.config.set("consumables", "ink_reset_percent", 100)
        self.config.set("consumables", "ink_reset_at", now)

        # Emit live update (no reloads)
        self.ink_changed.emit({
            "percent": 100,
            "reset_at": now,
        })

    # --------------------------------------------------------
    # Print log loader
    # --------------------------------------------------------
    def _iter_log_posters(self, row: dict):
        """Yield printed file entries from a print log row.

        Supports:
        - v1: {file_1, file_2}
        - v2: {files: [ {path, poster_id, source, ...}, ... ]}

        Yields dicts with at least:
            {"source": "patents"|"studio"|None, "poster_id": str|None, "path": str|None, "stem": str|None}
        """
        # v2 schema
        files = row.get("files")
        if isinstance(files, list):
            for it in files:
                if isinstance(it, dict):
                    path = it.get("path")
                    stem = None
                    try:
                        if path:
                            stem = Path(path).stem
                    except Exception:
                        stem = None
                    yield {
                        "source": it.get("source"),
                        "poster_id": it.get("poster_id") or it.get("id"),
                        "path": path,
                        "stem": stem,
                    }
                elif isinstance(it, str):
                    # tolerate legacy: list[str]
                    stem = None
                    try:
                        stem = Path(it).stem
                    except Exception:
                        pass
                    yield {"source": None, "poster_id": None, "path": it, "stem": stem}
            return

        # v1 schema fallback
        f1 = row.get("file_1")
        f2 = row.get("file_2")

        if f1:
            yield {"source": None, "poster_id": None, "path": f1, "stem": Path(str(f1)).stem}
        if f2:
            yield {"source": None, "poster_id": None, "path": f2, "stem": Path(str(f2)).stem}


    def _norm_key(self, s: str) -> str:
        """
        Normalize poster identifiers so filenames and index keys match.
        """
        return (
            s.strip()
            .lower()
            .replace(" ", "")
            .replace("_", "")
            .replace("-", "")
        )
    def _classify_poster(self, printed: object) -> str | None:
        """Return 'patents' or 'studio' for a printed file entry.

        Prefers explicit 'source' from print_log v2 entries.
        Falls back to poster_id/stem lookup against the loaded poster index.
        """
        # v2 entries often include explicit source
        if isinstance(printed, dict):
            src = printed.get("source")
            if src in ("patents", "studio"):
                return src

            candidate = printed.get("poster_id") or printed.get("id") or printed.get("stem")
            if isinstance(candidate, str) and candidate:
                return self._classify_poster(candidate)
            return None

        if not isinstance(printed, str) or not printed:
            return None

        if not hasattr(self, "_patents_norm"):
            return None  # index not loaded yet

        base_name = printed.split("-", 1)[0]
        key = self._norm_key(base_name)

        if key in self._patents_norm:
            return "patents"

        if key in self._studio_norm:
            return "studio"

        return None



    def _normalize_poster_name(self, filename: str) -> str:
        return Path(filename).stem.split("-", 1)[0]

    def _load_print_log(self) -> list[dict]:
        path = self.print_log_path

        if not path or not path.exists() or path.is_dir():
            return []

        rows = []
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
        except Exception:
            return []

        return rows

    # --------------------------------------------------------
    # Patents / Studio counts
    # --------------------------------------------------------

    def get_mtd_counts(self, index: dict) -> dict[str, int]:
        now = datetime.now()
        month_start = start_of_month(now)

        counts = {"patents": 0, "studio": 0}

        for row in self._rows:
            ts = _parse_iso(row.get("timestamp"))
            if not ts or ts < month_start:
                continue

            for poster in self._iter_log_posters(row):
                source = self._classify_poster(poster)
                if source:
                    counts[source] += 1

        return counts

    # --------------------------------------------------------
    # Paper roll metrics
    # --------------------------------------------------------

    def get_paper_status(self) -> dict[str, float | int]:
        """
        Authoritative paper state from PaperLedger.
        """
        ledger = self.paper_ledger

        if not ledger or ledger.remaining_ft is None or ledger.total_ft is None:
            return {"feet": 0, "percent": 0}

        percent = (
            int((ledger.remaining_ft / ledger.total_ft) * 100)
            if ledger.total_ft > 0
            else 0
        )

        return {
            "feet": int(ledger.remaining_ft),
            "percent": percent,
        }

    
    def _estimate_print_cost_usd(self, *, sheet_size: str) -> float:
        try:
            w_str, h_str = sheet_size.lower().split("x", 1)
            w_in = float(w_str)
            h_in = float(h_str)
        except Exception:
            return 0.0

        paper_cost_per_foot = float(
            self.config.get("print_cost", "paper_cost_per_foot", 47.95 / 60.0)
        )
        waste_pct = float(
            self.config.get("print_cost", "waste_pct", 0.10)
        )

        ink_cost_per_ml = float(
            self.config.get("print_cost", "ink_cost_per_ml", 32.0 / 70.0)
        )

        ink_ml_per_sqft = float(
            self.config.get("print_cost", "ink_ml_per_sqft", 70.0 / (11.0 * 6.0))
        )

        length_in = max(w_in, h_in)
        paper_feet = (length_in / 12.0) * (1.0 + max(0.0, waste_pct))
        paper_cost = paper_feet * paper_cost_per_foot

        area_sqft = (w_in * h_in) / 144.0
        ink_ml = area_sqft * ink_ml_per_sqft
        ink_cost = ink_ml * ink_cost_per_ml

        cost = paper_cost + ink_cost
        return float(cost) if cost > 0 else 0.0

    def set_print_log_rows(self, rows: list[dict]) -> None:
        self._print_log_rows = rows or []

    def get_monthly_costs(self) -> dict:
        now = datetime.now()
        month_start = start_of_month(now)

        prints = 0
        ink_cost = 0.0
        paper_cost = 0.0

        for row in self._rows:
            ts = _parse_iso(row.get("timestamp"))
            if not ts or ts < month_start:
                continue

            qty = int(row.get("quantity", 1))
            size = row.get("size") or ""
            if not size:
                continue

            per_print_cost = self._estimate_print_cost_usd(sheet_size=size)

            prints += qty

            # Split estimated cost into ink vs paper proportionally
            # (keeps your UI semantic honest)
            total_cost = per_print_cost * qty

            # Recompute components for clarity
            # (same math, but separated)
            w_str, h_str = size.lower().split("x", 1)
            w_in = float(w_str)
            h_in = float(h_str)

            length_in = max(w_in, h_in)
            paper_feet = (length_in / 12.0)
            paper_cost_per_foot = float(
                self.config.get("print_cost", "paper_cost_per_foot", 47.95 / 60.0)
            )
            paper_cost += paper_feet * paper_cost_per_foot * qty

            area_sqft = (w_in * h_in) / 144.0
            ink_ml_per_sqft = float(
                self.config.get("print_cost", "ink_ml_per_sqft", 70.0 / (11.0 * 6.0))
            )
            ink_cost_per_ml = float(
                self.config.get("print_cost", "ink_cost_per_ml", 32.0 / 70.0)
            )
            ink_cost += area_sqft * ink_ml_per_sqft * ink_cost_per_ml * qty

        return {
            "prints": prints,
            "ink": ink_cost,
            "paper": paper_cost,
        }



    # --------------------------------------------------------
    # Ink metrics (estimated)
    # --------------------------------------------------------

    def get_ink_percent(self) -> int:
        start_pct = self.config.get(
            "consumables",
            "ink_reset_percent",
            100,
        )
        reset_at = self.config.get(
            "consumables",
            "ink_reset_at",
            "",
        )

        try:
            start_pct = int(start_pct)
        except Exception:
            start_pct = 100

        reset_at_dt = _parse_iso(reset_at)
        if not reset_at_dt:
            return start_pct

        # Conservative estimate: ~0.15% per print
        used_pct = 0.0

        for entry in self._load_print_log():
            ts = _parse_iso(entry.get("timestamp"))
            if not ts or ts < reset_at_dt:
                continue

            qty = int(entry.get("quantity", 1))
            used_pct += 0.15 * qty

        return max(int(start_pct - used_pct), 0)
    
    # --------------------------------------------------------
    # Paper metadata
    # --------------------------------------------------------

    def get_paper_meta(self) -> dict:
        return {
            "name": self.config.get("consumables", "paper_name", ""),
            "reset_at": self.config.get("consumables", "paper_roll_reset_at", ""),
        }


    # --------------------------------------------------------
    # Ink metadata
    # --------------------------------------------------------

    def get_ink_meta(self) -> dict:
        return {
            "reset_at": self.config.get("consumables", "ink_reset_at", ""),
        }

    
    # ========================================================
    # NEW: Recent activity (dashboard panels)
    # ========================================================

    def get_recent_print_jobs(self, limit: int = 2) -> list[dict]:
        jobs: list[dict] = []

        for entry in reversed(self._load_print_log()):
            schema = entry.get("schema", "print_log_v1")

            ts = _parse_iso(entry.get("timestamp"))
            if not ts:
                continue

            # -------------------------------------------------
            # v2 entries (preferred, authoritative)
            # -------------------------------------------------
            if schema == "print_log_v2":
                if not entry.get("files"):
                    continue

                entry = dict(entry)  # shallow copy
                entry["timestamp"] = ts
                jobs.append(entry)

            # -------------------------------------------------
            # v1 entries (legacy fallback)
            # -------------------------------------------------
            elif schema == "print_log_v1":
                files = []
                if entry.get("file_1"):
                    files.append(entry["file_1"])
                if entry.get("file_2"):
                    files.append(entry["file_2"])

                if not files:
                    continue

                jobs.append({
                    "schema": "print_log_v1",
                    "timestamp": ts,
                    "mode": entry.get("mode", "single"),
                    "size": entry.get("size", ""),
                    "files": files,
                })

            if len(jobs) >= limit:
                break

        return jobs



    def get_recent_index_events(self, limit: int = 5) -> list[dict]:
        events: list[dict] = []

        # index log is a DIFFERENT file — load it explicitly
        index_log_path = (
            Path(os.getenv("APPDATA"))
            / "SnooozeCo"
            / "StudioHub"
            / "logs"
            / "index_log.jsonl"
        )
        if not index_log_path.exists():
            return events

        with index_log_path.open("r", encoding="utf-8") as f:
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
                    "status": entry.get("status"),  # ← ADD THIS
                })


        events.sort(key=lambda e: e["timestamp"], reverse=True)
        return events[:limit]
    
    def set_index(self, index: dict) -> None:
        """
        Provide poster index data for classification.
        This is REQUIRED for dashboard metrics.
        """
        if not isinstance(index, dict):
            self._index = {}
            self._patents_norm = set()
            self._studio_norm = set()
            return

        posters = index.get("posters", {})
        patents = posters.get("patents", {}) if isinstance(posters, dict) else {}
        studio = posters.get("studio", {}) if isinstance(posters, dict) else {}

        self._index = index

        # Normalized lookup sets (fast, stable)
        self._patents_norm = {self._norm_key(k) for k in patents.keys()}
        self._studio_norm = {self._norm_key(k) for k in studio.keys()}


    # -------------------------------------------------
    # Print counts (last 30 days)
    # -------------------------------------------------

    def get_print_counts_last_30_days(self) -> dict[str, int]:
        cutoff = datetime.now() - timedelta(days=30)

        patents = 0
        studio = 0

        rows = self._load_print_log()  # ✅ correct method

        for row in rows:
            ts = _parse_iso(row.get("timestamp"))
            if not ts or ts < cutoff:
                continue

            for poster in self._iter_log_posters(row):
                source = self._classify_poster(poster)
                if source == "patents":
                    patents += 1
                elif source == "studio":
                    studio += 1

        return {
            "patents": patents,
            "studio": studio,
        }

    def get_monthly_print_counts_with_delta(self) -> dict:
        """
        Current month print counts and deltas vs previous month.

        Deltas are always returned (0 if no prior data).
        """
        now = datetime.now()

        # Current month start (local time)
        start_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_current = now

        # Previous month window
        last_month_end = start_current - timedelta(seconds=1)
        start_previous = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        current = self._count_prints_between(start_current, end_current)
        previous = self._count_prints_between(start_previous, last_month_end)

        p_now = int(current.get("patents", 0))
        s_now = int(current.get("studio", 0))

        p_prev = int(previous.get("patents", 0))
        s_prev = int(previous.get("studio", 0))

        return {
            "patents": p_now,
            "studio": s_now,
            "delta_patents": p_now - p_prev,
            "delta_studio": s_now - s_prev,
            "delta_total": (p_now + s_now) - (p_prev + s_prev),
        }


    def _count_prints_between(self, start_dt: datetime, end_dt: datetime) -> dict[str, int]:
        """
        Counts prints between two datetimes, grouped by source ("patents" | "studio").

        Uses the same poster-level logic as get_print_counts_last_30_days().
        """
        patents = 0
        studio = 0

        rows = self._load_print_log()

        for row in rows:
            ts = _parse_iso(row.get("timestamp"))
            if not ts or ts < start_dt or ts > end_dt:
                continue

            for poster in self._iter_log_posters(row):
                source = self._classify_poster(poster)
                if source == "patents":
                    patents += 1
                elif source == "studio":
                    studio += 1

        return {
            "patents": patents,
            "studio": studio,
        }


    def reload(self) -> None:

        self._rows = []

        try:
            p = Path(self.print_log_path)
            if not p.exists() or p.is_dir():
                return

            # JSONL: one JSON object per line
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        if isinstance(row, dict):
                            self._rows.append(row)
                    except Exception:
                        # skip bad lines, never crash dashboard
                        continue

        except Exception:
            # never crash dashboard due to log issues
            self._rows = []

    def get_last_print_timestamp(self) -> datetime | None:
        rows = self._load_print_log()
        for row in reversed(rows):
            ts = _parse_iso(row.get("timestamp"))
            if ts:
                return ts
        return None


    def printer_online(self) -> bool:
        # Placeholder — wire to real printer state later
        return True


    def get_active_design_app(self) -> str | None:
        try:
            import psutil
        except ImportError:
            return None  # Silent fallback → Idle

        try:
            for p in psutil.process_iter(attrs=["name"]):
                name = (p.info.get("name") or "").lower()
                if name == "photoshop.exe":
                    return "Photoshop"
                if name == "illustrator.exe":
                    return "Illustrator"
        except Exception:
            pass

        return None

    def get_now_playing_spotify_local(self) -> dict:
        """
        Detect Spotify playback via window title inspection (Windows).

        Returns:
            {
                "active": bool,
                "playing": bool,
                "artist": str | None,
                "title": str | None,
            }
        """
        for proc in psutil.process_iter(attrs=["name", "pid"]):
            try:
                if proc.info["name"] and "spotify.exe" in proc.info["name"].lower():
                    import win32gui
                    import win32process

                    def enum_handler(hwnd, result):
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid == proc.pid and win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            if title:
                                result.append(title)

                    titles: list[str] = []
                    win32gui.EnumWindows(enum_handler, titles)

                    if not titles:
                        return {
                            "active": True,
                            "playing": False,
                            "artist": None,
                            "title": None,
                        }

                    window_title = titles[0]

                    # Spotify paused / idle states
                    if window_title.lower() in ("spotify", "advertisement"):
                        return {
                            "active": True,
                            "playing": False,
                            "artist": None,
                            "title": None,
                        }

                    # Typical format: Artist – Song
                    if " - " in window_title:
                        artist, title = window_title.split(" - ", 1)
                        return {
                            "active": True,
                            "playing": True,
                            "artist": artist.strip(),
                            "title": title.strip(),
                        }

                    return {
                        "active": True,
                        "playing": False,
                        "artist": None,
                        "title": None,
                    }

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue

        # Spotify not running
        return {
            "active": False,
            "playing": False,
            "artist": None,
            "title": None,
        }
