from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from PySide6 import QtCore

from studiohub.hub_models.poster_index import load_poster_index
from studiohub.hub_models.poster_index_builder import SIZES

from studiohub.services.photoshop import run_jsx
from studiohub.services.print_log_writer import append_print_log
from studiohub.services.paper_ledger import PaperLedger


# =====================================================
# Application paths
# =====================================================

def _appdata_base() -> Path:
    base = Path(os.getenv("APPDATA", Path.home()))
    p = base / "SnooozeCo" / "StudioHub"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _print_jobs_dir() -> Path:
    p = _appdata_base() / "print_jobs"
    p.mkdir(parents=True, exist_ok=True)
    return p


# =====================================================
# Queue Item
# =====================================================

@dataclass(frozen=True)
class QueueItem:
    name: str
    path: str
    size: str
    source: str
    poster_key: str = ""
    background_key: str = ""
    background_label: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "source": self.source,
            "poster_key": self.poster_key,
            "background_key": self.background_key,
            "background_label": self.background_label,
        }


# =====================================================
# Print Manager Model (Poster Index v2 — backgrounds-aware)
# =====================================================

class PrintManagerModelQt(QtCore.QObject):
    scan_started = QtCore.Signal(str)
    scan_finished = QtCore.Signal(str, dict)

    queue_changed = QtCore.Signal(list)
    last_batch_changed = QtCore.Signal(bool)

    send_started = QtCore.Signal()
    send_finished = QtCore.Signal(list)
    error = QtCore.Signal(str)
    print_log_updated = QtCore.Signal()

    def __init__(self, *, missing_model, config_manager, paper_ledger: PaperLedger, parent=None):
        super().__init__(parent)

        self.missing_model = missing_model
        self.config_manager = config_manager
        self.paper_ledger = paper_ledger

        # Availability cache (per source)
        self._available: Dict[str, dict] = {
            "patents": {},
            "studio": {},
        }

        # Print queue + last batch
        self._queue: List[QueueItem] = []
        self._last_batch: List[QueueItem] = []

    # -------------------------------------------------
    # JSX workers
    # -------------------------------------------------

    def _get_jsx_worker(self, name: str) -> Path:
        """
        Resolve a JSX worker by filename from the configured workers directory.
        Config: paths.jsx_workers_dir
        """
        workers_dir_raw = self.config_manager.get("paths", "jsx_root", None)
        if not workers_dir_raw:
            raise RuntimeError("paths.jsx_root is not set in settings/config")

        workers_dir = Path(workers_dir_raw)

        worker_path = workers_dir / name
        if not worker_path.exists():
            raise FileNotFoundError(f"JSX worker not found: {worker_path}")

        return worker_path

    # -------------------------------------------------
    # Availability
    # -------------------------------------------------

    def ensure(self, source: str) -> None:
        if source not in ("patents", "studio"):
            return
        if not self._available.get(source):
            self.refresh(source)

    def refresh(self, source: str) -> None:
        if source not in ("patents", "studio"):
            return

        self.scan_started.emit(source)

        try:
            data = self._build_available_from_index(source)
        except Exception as e:
            data = {}
            self.error.emit(f"{source} refresh failed: {e}")
        finally:
            self._available[source] = data or {}
            self.scan_finished.emit(source, self._available[source])

    def get_available(self, source: str) -> dict:
        if source not in ("patents", "studio"):
            return {}
        return self._available.get(source, {}) or {}

    # -------------------------------------------------
    # Queue
    # -------------------------------------------------

    def get_queue(self) -> List[dict]:
        return [q.as_dict() for q in self._queue]

    def add_to_queue(self, items: Sequence[Dict[str, Any]]) -> None:
        for it in items:
            self._queue.append(
                QueueItem(
                    name=it["name"],
                    path=it["path"],
                    size=it["size"],
                    source=it["source"],
                    poster_key=it.get("poster_key", ""),
                    background_key=it.get("background_key", ""),
                    background_label=it.get("background_label", ""),
                )
            )
        self.queue_changed.emit(self.get_queue())

    def remove_from_queue(self, paths: Sequence[str]) -> None:
        if not paths:
            return
        remove = set(paths)
        self._queue = [q for q in self._queue if q.path not in remove]
        self.queue_changed.emit(self.get_queue())

    def clear_queue(self) -> None:
        self._queue.clear()
        self.queue_changed.emit([])

    # -------------------------------------------------
    # Reprint
    # -------------------------------------------------

    def has_last_batch(self) -> bool:
        return bool(self._last_batch)

    def reprint_last_batch(self) -> None:
        if not self._last_batch:
            return
        self._queue = list(self._last_batch)
        self.queue_changed.emit(self.get_queue())

    # -------------------------------------------------
    # Job building
    # -------------------------------------------------

    def build_jobs(self) -> List[List[str]]:
        jobs: List[List[str]] = []

        twelves = [q.path for q in self._queue if q.size == "12x18"]
        singles = [q for q in self._queue if q.size != "12x18"]

        i = 0
        while i < len(twelves):
            if i + 1 < len(twelves):
                jobs.append([twelves[i], twelves[i + 1]])
                i += 2
            else:
                jobs.append([twelves[i]])
                i += 1

        for q in singles:
            jobs.append([q.path])

        return jobs

    # -------------------------------------------------
    # Cost estimation (settings-driven)
    # -------------------------------------------------

    def _estimate_print_cost_usd(self, *, sheet_size: str) -> float:
        try:
            w_str, h_str = sheet_size.lower().split("x", 1)
            w_in = float(w_str)
            h_in = float(h_str)
        except Exception:
            return 0.0

        paper_cost_per_foot = float(
            self.config_manager.get("print_cost", "paper_cost_per_foot", 47.95 / 60.0)
        )
        waste_pct = float(self.config_manager.get("print_cost", "waste_pct", 0.10))
        ink_cost_per_ml = float(self.config_manager.get("print_cost", "ink_cost_per_ml", 32.0 / 70.0))
        ink_ml_per_sqft = float(self.config_manager.get("print_cost", "ink_ml_per_sqft", 70.0 / (11.0 * 6.0)))

        length_in = max(w_in, h_in)
        paper_feet = (length_in / 12.0) * (1.0 + max(0.0, waste_pct))
        paper_cost = paper_feet * paper_cost_per_foot

        area_sqft = (w_in * h_in) / 144.0
        ink_ml = area_sqft * ink_ml_per_sqft
        ink_cost = ink_ml * ink_cost_per_ml

        cost = paper_cost + ink_cost
        return float(cost) if cost > 0 else 0.0


    def _planned_length_in_for_sheet(self, sheet_size: str) -> float:
        """
        For 18x24 -> 24 inches, 24x36 -> 36 inches, etc.
        This is the planned feed length, not actual (actual comes from failure dialog).
        """
        try:
            w_str, h_str = sheet_size.lower().split("x", 1)
            return float(max(float(w_str), float(h_str)))
        except Exception:
            return 0.0

    # -------------------------------------------------
    # Send to Photoshop
    # -------------------------------------------------

    def send(self, *, is_reprint: bool = False) -> None:
        self.send_started.emit()

        try:
            jsx_path = self._get_jsx_worker("print_worker.jsx")

            out_dir = _print_jobs_dir()
            for f in out_dir.glob("job_*.txt"):
                f.unlink(missing_ok=True)

            jobs = self.build_jobs()
            written: List[str] = []

            # Lookup queue items by path
            by_path: Dict[str, QueueItem] = {q.path: q for q in self._queue}

            for i, paths in enumerate(jobs, 1):
                p = out_dir / f"job_{i:04d}.txt"
                p.write_text("\n".join(x.replace("\\", "/") for x in paths), encoding="utf-8")
                written.append(str(p))

            # Run Photoshop JSX
            run_jsx(jsx_path, self.config_manager)

            # -------------------------------------------------
            # Append to Print Log (JSONL)
            # -------------------------------------------------
            if self.config_manager.get("printing", "is_primary_printer", False):
                log_path = self.config_manager.get_print_log_path()

                for paths in jobs:
                    if not paths:
                        continue

                    printed_files: List[dict] = []
                    for pth in paths:
                        q = by_path.get(pth)
                        if not q:
                            continue
                        printed_files.append({
                            "path": pth,
                            "source": q.source,
                            "poster_id": q.name,
                        })

                    if not printed_files:
                        continue

                    mode = "2up" if len(printed_files) == 2 else "single"
                    sheet_size = "18x24" if mode == "2up" else (by_path[paths[0]].size if paths else "")

                    print_cost_usd = self._estimate_print_cost_usd(sheet_size=sheet_size)

                    rec = append_print_log(
                        log_path=log_path,
                        mode=mode,
                        size=sheet_size,
                        print_cost_usd=print_cost_usd,
                        files=printed_files,
                        is_reprint=bool(is_reprint),
                        waste_incurred=bool(is_reprint),
                    )

                    # -------------------------------------------------
                    # Commit paper usage (authoritative ledger)
                    # -------------------------------------------------
                    auto_commit = bool(self.config_manager.get("printing", "auto_commit_paper", True))
                    if auto_commit and rec and rec.get("timestamp"):
                        job_id = rec["timestamp"]
                        planned_in = self._planned_length_in_for_sheet(sheet_size)
                        if planned_in > 0:
                            self.paper_ledger.commit_print(job_id=job_id, length_in=planned_in)


            self.print_log_updated.emit()

            # Preserve last batch
            self._last_batch = list(self._queue)
            self.last_batch_changed.emit(True)

            # Clear queue
            self._queue.clear()
            self.queue_changed.emit([])

            self.send_finished.emit(written)

        except Exception as e:
            self.error.emit(str(e))

    def send_reprint_job(self, job: dict) -> None:
        if job.get("schema") != "print_log_v2":
            raise RuntimeError("Reprint only supported for v2 jobs")

        try:
            jsx_path = self._get_jsx_worker("print_worker.jsx")

            out_dir = _print_jobs_dir()
            for f in out_dir.glob("job_*.txt"):
                f.unlink(missing_ok=True)

            paths = [f["path"].replace("\\", "/") for f in job.get("files", [])]
            if not paths:
                raise RuntimeError("Reprint job contains no files")

            job_file = out_dir / "job_0001.txt"
            job_file.write_text("\n".join(paths), encoding="utf-8")

            run_jsx(jsx_path, self.config_manager)

            # Log reprint as NEW entry
            self._append_reprint_log(job)

            # Let dashboard know
            self.print_log_updated.emit()

        except Exception as e:
            self.error.emit(str(e))

    def _append_reprint_log(self, job: dict) -> None:
        if job.get("schema") != "print_log_v2":
            return

        log_path = self.config_manager.get_print_log_path()
        sheet_size = job.get("size") or ""
        print_cost_usd = self._estimate_print_cost_usd(sheet_size=sheet_size)

        rec = append_print_log(
            log_path=log_path,
            mode=job.get("mode", "single"),
            size=sheet_size,
            print_cost_usd=print_cost_usd,
            files=job.get("files", []),
            is_reprint=True,
            waste_incurred=True,
        )

        auto_commit = bool(self.config_manager.get("printing", "auto_commit_paper", True))
        if auto_commit and rec and rec.get("timestamp"):
            job_id = rec["timestamp"]
            planned_in = self._planned_length_in_for_sheet(sheet_size)
            if planned_in > 0:
                self.paper_ledger.commit_print(job_id=job_id, length_in=planned_in)


    # -------------------------------------------------
    # Poster Index v2
    # -------------------------------------------------

    def _load_index(self) -> Dict[str, Any]:
        p: Path | None = None
        try:
            candidate = self.config_manager.get_poster_index_path()
            p = Path(candidate) if candidate else None
        except Exception:
            p = None

        if p and p.exists() and p.is_file():
            data = load_poster_index(p)
        else:
            data = load_poster_index()

        if not isinstance(data, dict):
            return {"posters": {"patents": {}, "studio": {}}}

        if "posters" not in data or not isinstance(data.get("posters"), dict):
            data["posters"] = {"patents": {}, "studio": {}}

        for k in ("patents", "studio"):
            if not isinstance(data["posters"].get(k), dict):
                data["posters"][k] = {}

        return data

    def _build_available_from_index(self, source: str) -> Dict[str, List[dict]]:
        index = self._load_index()
        posters = (index.get("posters") or {}).get(source) or {}

        if isinstance(posters, list):
            posters = {
                (it.get("id") or it.get("key") or f"poster_{i}"): it
                for i, it in enumerate(posters)
                if isinstance(it, dict)
            }
        if not isinstance(posters, dict):
            posters = {}

        results: Dict[str, List[dict]] = {s: [] for s in SIZES}

        for poster_key, meta in posters.items():
            display = meta.get("display_name") or poster_key
            sizes = meta.get("sizes") or {}

            for size in SIZES:
                size_meta = sizes.get(size) or {}
                if not size_meta.get("exists"):
                    continue

                # Patents: background-aware
                bgs = size_meta.get("backgrounds") or {}
                if bgs:
                    for bg_key, bg_rec in bgs.items():
                        if not isinstance(bg_rec, dict):
                            continue
                        if bg_rec.get("exists") is not True:
                            continue

                        bg_label = (bg_rec.get("label") or bg_key).strip()
                        path = bg_rec.get("path")
                        if not path:
                            continue

                        results[size].append({
                            "name": f"{display} — {bg_label}",
                            "path": path,
                            "size": size,
                            "source": source,
                            "poster_key": poster_key,
                            "background_key": bg_key,
                            "background_label": bg_label,
                        })
                    continue

                # Studio (or non-bg): fallback
                for path in (size_meta.get("files") or []):
                    results[size].append({
                        "name": display,
                        "path": path,
                        "size": size,
                        "source": source,
                        "poster_key": poster_key,
                        "background_key": "",
                        "background_label": "",
                    })

        for s in results:
            results[s].sort(key=lambda r: (r["name"].lower(), r["path"].lower()))

        return results
