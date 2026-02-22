from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Sequence

from PySide6 import QtCore

from studiohub.constants import PRINT_SIZES

# =====================================================
# Constants
# =====================================================

# Fixed: Need parents[2] to get to studiohub/ root
APP_ROOT = Path(__file__).resolve().parents[2]
JSX_DIR = APP_ROOT / "scripts" / "jsx"
JSX_MOCKUP_WORKER = JSX_DIR / "mockup_worker.jsx"

# =====================================================
# Mockup Generator Model
# =====================================================

class MockupGeneratorModelQt(QtCore.QObject):
    """
    Mockup Generator Model

    Contract:
    - NEVER scans filesystem
    - Reads ONLY poster_index.json (v2)
    - Performs NO name normalization
    - Consumes display_name directly from index
    - Emits size-grouped poster data
    """

    # ---- posters ----
    posters_ready = QtCore.Signal(str, dict)

    # ---- templates ----
    templates_ready = QtCore.Signal(list)

    # ---- queue ----
    queue_changed = QtCore.Signal(list)

    # ---- errors ----
    error = QtCore.Signal(str)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)

        self._cfg = config_manager
        self._poster_index_path = Path(self._cfg.get_poster_index_path()).resolve()

        # -------------------------------------------------
        # Local job cache (AppData, ephemeral)
        # -------------------------------------------------
        self._jobs_dir = (
            self._cfg.get_appdata_root()
            / "cache"
            / "mockup_jobs"
        )
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

        self._posters: Dict[str, Dict[str, List[dict]]] = {
            "archive": {s: [] for s in PRINT_SIZES},
            "studio": {s: [] for s in PRINT_SIZES},
        }

        self._queue: List[dict] = []
        self._templates: List[dict] = []

    # =================================================
    # Posters (INDEX v2)
    # =================================================

    def load_from_index(self, source: str) -> None:
        try:
            data = self._build_available_from_index(source)
            self._posters[source] = data
            self.posters_ready.emit(source, data)
        except Exception as e:
            self.error.emit(str(e))

    def _load_index(self) -> dict:
        if not self._poster_index_path.exists():
            raise FileNotFoundError(
                f"Poster index not found: {self._poster_index_path}"
            )

        data = json.loads(
            self._poster_index_path.read_text(encoding="utf-8")
        )

        if data.get("cache_version") != 2:
            raise ValueError("poster_index.json must be cache_version 2")

        return data

    def _build_available_from_index(self, source: str) -> Dict[str, List[dict]]:
        """
        Index-native availability (PARITY with PrintManagerModelQt):

        - Archive: sizes[*].backgrounds[*].path
        - Studio: sizes[*].files fallback
        """
        index = self._load_index()

        posters = (
            index.get("posters", {})
                .get(source, {})
        )

        results: Dict[str, List[dict]] = {s: [] for s in PRINT_SIZES}

        for poster_key, meta in posters.items():
            if not isinstance(meta, dict):
                continue

            display = meta.get("display_name") or poster_key
            sizes = meta.get("sizes") or {}

            for size in PRINT_SIZES:
                size_meta = sizes.get(size) or {}

                # v2 explicit existence flag
                if not size_meta.get("exists"):
                    continue

                # -----------------------------
                # ARCHIVE → background-aware
                # -----------------------------
                backgrounds = size_meta.get("backgrounds") or {}
                if backgrounds:
                    for bg_key, bg_rec in backgrounds.items():
                        if not isinstance(bg_rec, dict):
                            continue
                        if bg_rec.get("exists") is not True:
                            continue

                        path = bg_rec.get("path")
                        if not path:
                            continue

                        bg_label = (bg_rec.get("label") or bg_key).strip()

                        results[size].append({
                            "name": f"{display} — {bg_label}",
                            "path": path,
                            "size": size,
                            "source": source,
                            "poster_key": poster_key,
                            "background_key": bg_key,
                            "background_label": bg_label,
                        })
                    continue  # do NOT fall through to files

                # -----------------------------
                # STUDIO → file-based fallback
                # -----------------------------
                for path in size_meta.get("files", []):
                    results[size].append({
                        "name": display,
                        "path": path,
                        "size": size,
                        "source": source,
                        "poster_key": poster_key,
                        "background_key": "",
                        "background_label": "",
                    })

        # Stable ordering (UI consistency)
        for s in results:
            results[s].sort(
                key=lambda r: (r["name"].lower(), r["path"].lower())
            )

        return results


    # =================================================
    # Queue
    # =================================================

    def get_queue(self) -> List[dict]:
        return list(self._queue)

    def add_to_queue(self, items: Sequence[dict]) -> None:
        self._queue.extend(items)
        self.queue_changed.emit(self.get_queue())

    def clear_queue(self) -> None:
        self._queue.clear()
        self.queue_changed.emit([])

    def remove_from_queue(self, items: list[dict]) -> None:
        if not items:
            return

        remove_keys = {
            (it.get("path"), it.get("template"))
            for it in items
        }

        self._queue = [
            it for it in self._queue
            if (it.get("path"), it.get("template")) not in remove_keys
        ]

        self.queue_changed.emit(self._queue)

    # =================================================
    # Templates
    # =================================================

    def load_templates(self) -> None:
        """
        Loads mockup templates from:
        cfg.paths.mockup_templates_root
        """
        try:
            root = self._cfg.get_mockup_templates_root()
        except Exception as e:
            self.error.emit(str(e))
            self.templates_ready.emit([])
            return

        items: List[dict] = []

        for p in sorted(root.glob("*.psd")):
            items.append({
                "name": p.stem,
                "path": str(p),
            })

        self._templates = items
        self.templates_ready.emit(items)

    def generate_mockups(self) -> None:
        """
        Build mockup job files and invoke Photoshop JSX worker.
        """
        if not self._queue:
            self.error.emit("Mockup queue is empty")
            return

        if not self._templates:
            self.error.emit("No mockup templates available")
            return

        jobs_dir = self._jobs_dir

        # Resolve paths
        try:
            output_root = self._cfg.get_mockup_output_root()
        except Exception as e:
            self.error.emit(f"Failed to get mockup output root: {e}")
            return

        # Template lookup
        template_map = {
            t["name"]: t["path"]
            for t in self._templates
            if "name" in t and "path" in t
        }

        # Clear previous jobs
        try:
            for f in jobs_dir.glob("job_*.json"):
                f.unlink(missing_ok=True)
        except Exception as e:
            self.error.emit(f"Failed to clear old job files: {e}")
            return

        written = 0

        for i, item in enumerate(self._queue, 1):
            poster_path = item.get("path")
            template_name = item.get("template")

            if not poster_path or not template_name:
                continue

            psd_path = template_map.get(template_name)
            if not psd_path:
                self.error.emit(f"Template not found: {template_name}")
                return

            try:
                poster_path = Path(poster_path)
                out_name = f"{poster_path.stem}__{template_name}.jpg"
                output_path = output_root / out_name

                job = {
                    "schema": "mockup_job_v1",
                    "template_psd": psd_path,
                    "poster_tiff": str(poster_path),
                    "output_jpg": str(output_path),
                    "smart_object_layer": "ARTWORK",
                    "jpg_quality": 92,
                    "reset_transform": True,
                }

                job_file = jobs_dir / f"job_{i:04d}.json"
                job_file.write_text(
                    json.dumps(job, indent=2),
                    encoding="utf-8",
                )

                written += 1
                
            except Exception as e:
                self.error.emit(f"Failed to create job {i}: {e}")
                return

        if written == 0:
            self.error.emit("No mockup jobs were generated")
            return

        # Invoke Photoshop (run JSX worker)
        try:
            from studiohub.services.photoshop import run_jsx
        except ImportError as e:
            self.error.emit(f"Failed to import run_jsx: {e}")
            return

        # Resolve JSX worker path
        try:
            # First try to get JSX root from config
            jsx_root = self._cfg.get("paths", "jsx_root")
            if jsx_root:
                jsx_path = Path(jsx_root) / "mockup_worker.jsx"
            else:
                # Fallback to relative path
                jsx_path = JSX_MOCKUP_WORKER
            
            if not jsx_path.exists():
                self.error.emit(f"JSX worker not found at: {jsx_path}")
                return
                
        except Exception as e:
            self.error.emit(f"Failed to resolve JSX worker path: {e}")
            return

        try:
            run_jsx(jsx_path, self._cfg)
        except FileNotFoundError as e:
            self.error.emit(f"Photoshop executable not found: {e}")
        except Exception as e:
            self.error.emit(f"Failed to run mockup worker: {e}")