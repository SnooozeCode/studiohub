# studiohub/services/dashboard/notes_store.py

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Adjust the import path if your ConfigManager lives elsewhere
from studiohub.config_manager import ConfigManager


class DashboardNotesStore:
    """
    Simple persistence layer for the dashboard “Notes” panel.

    * Stores the editor’s HTML in a file (e.g. notes.html) inside the
      user‑specific app‑data directory.
    * Provides `load_notes()` → str and `save_notes(html: str)` → None
      which the DashboardView expects.
    * If the file does not exist, `load_notes()` returns an empty string.
    """

    def __init__(self, config_manager: ConfigManager):
        self._cfg = config_manager
        runtime_root: Path = self._cfg.get_runtime_root()
        self._notes_path: Path = runtime_root / "notes" / "dashboard_notes.json"
        self._notes_path.parent.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # Public API – used by DashboardView
    # -----------------------------------------------------------------

    def load_html(self) -> str:
        if not self._notes_path.exists():
            return ""

        try:
            data = json.loads(self._notes_path.read_text(encoding="utf-8"))
            return data.get("content", "")
        except Exception:
            return ""

    def save_html(self, html: str) -> None:
        payload = {
            "version": 1,
            "updated_at": datetime.utcnow().isoformat(),
            "content": html,
        }

        try:
            self._notes_path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[DashboardNotesStore] Failed to save notes: {exc}")