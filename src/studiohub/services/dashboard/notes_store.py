# studiohub/services/dashboard/notes_store.py

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from studiohub.config_manager import ConfigManager
from studiohub.utils.logging import get_logger
from studiohub.utils.file_utils import atomic_write_json, safe_read_json, FileLock

logger = get_logger(__name__)


class DashboardNotesStore:
    """
    Simple persistence layer for the dashboard “Notes” panel.

    * Stores the editor’s HTML in a file (e.g. notes.html) inside the
      user‑specific app‑data directory.
    * Provides `load_notes()` → str and `save_notes(html: str)` → None
      which the DashboardView expects.
    * Uses atomic writes and file locking to prevent corruption.
    * If the file does not exist, `load_notes()` returns an empty string.
    """

    def __init__(self, config_manager: ConfigManager):
        self._cfg = config_manager
        runtime_root: Path = self._cfg.get_runtime_root()
        self._notes_path: Path = runtime_root / "notes" / "dashboard_notes.json"
        self._lock_path = self._notes_path.with_suffix('.lock')
        self._notes_path.parent.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # Public API – used by DashboardView
    # -----------------------------------------------------------------

    def load_html(self) -> str:
        """
        Load notes safely with automatic backup fallback.
        
        Returns:
            Notes content as string, or empty string if file doesn't exist
        """
        if not self._notes_path.exists():
            return ""

        # Use safe_read_json which automatically falls back to backups
        data = safe_read_json(self._notes_path, default={})
        
        if not data:
            return ""
            
        return data.get("content", "")

    def save_html(self, html: str) -> None:
        """
        Save notes atomically with file locking.
        
        Args:
            html: Notes content to save
        """
        payload = {
            "version": 1,
            "updated_at": datetime.utcnow().isoformat(),
            "content": html,
        }

        try:
            # Use file lock to prevent concurrent writes
            with FileLock(self._lock_path, timeout=2.0):
                # Write atomically with backup
                atomic_write_json(
                    self._notes_path,
                    payload,
                    make_backup=True,
                    indent=2
                )
            
            logger.debug(f"Notes saved successfully ({len(html)} chars)")
            
        except TimeoutError:
            logger.warning("Could not acquire lock for notes, trying without lock")
            # Fall back to atomic write without lock
            try:
                atomic_write_json(self._notes_path, payload, make_backup=True, indent=2)
            except Exception as e:
                logger.error(f"Failed to save notes even without lock: {e}")
                
        except Exception as exc:
            logger.error(f"Failed to save notes: {exc}")

    # -----------------------------------------------------------------
    # Additional Utility Methods
    # -----------------------------------------------------------------

    def load_raw(self) -> dict:
        """
        Load the raw notes data structure.
        
        Returns:
            Dictionary with version, timestamp, and content
        """
        return safe_read_json(self._notes_path, default={
            "version": 1,
            "updated_at": None,
            "content": ""
        })

    def get_last_modified(self) -> datetime | None:
        """
        Get the last modification time of the notes file.
        
        Returns:
            Datetime of last modification, or None if file doesn't exist
        """
        if not self._notes_path.exists():
            return None
        
        try:
            mtime = self._notes_path.stat().st_mtime
            return datetime.fromtimestamp(mtime)
        except Exception as e:
            logger.error(f"Failed to get last modified time: {e}")
            return None

    def clear_notes(self) -> None:
        """
        Clear all notes (save empty string).
        """
        self.save_html("")

    def backup_exists(self) -> bool:
        """
        Check if there are any backups of the notes file.
        
        Returns:
            True if at least one backup exists
        """
        backup_dir = self._notes_path.parent / ".backups"
        if not backup_dir.exists():
            return False
        
        pattern = f"{self._notes_path.name}.*.bak"
        return len(list(backup_dir.glob(pattern))) > 0

    def recover_from_backup(self) -> bool:
        """
        Attempt to recover notes from the most recent backup.
        
        Returns:
            True if recovery succeeded
        """
        from studiohub.utils.recovery import recover_from_backup
        return recover_from_backup(self._notes_path)