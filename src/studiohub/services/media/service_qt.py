# studiohub/services/media/service_qt.py
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QFileSystemWatcher, QTimer
from PySide6.QtGui import QPixmap

from studiohub.config.manager import ConfigManager


class MediaServiceQt(QObject):
    """
    Media service using file system watching instead of polling.
    Includes debouncing to handle rapid file writes.
    """
    updated = Signal(dict)

    # Debounce delay in milliseconds
    DEBOUNCE_MS = 500

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)

        base = config.get_appdata_root() / "media"
        self._json_path = base / "now_playing.json"
        self._art_path = base / "artwork.png"

        self._last_payload: Optional[dict] = None
        self._last_read_time = 0
        self._pending_update = False
        
        # Create file watcher
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        
        # Debounce timer
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._process_file_change)
        
        # Set up watching
        self._setup_watcher()
        
        # Initial load (if file exists and has content)
        if self._json_path.exists() and self._json_path.stat().st_size > 0:
            self._on_file_changed()

    def _setup_watcher(self):
        """Set up file watching for both files."""
        # Remove any existing paths
        if self._watcher.files():
            self._watcher.removePaths(self._watcher.files())
        
        # Watch JSON file if it exists (or watch directory for creation)
        if self._json_path.exists():
            self._watcher.addPath(str(self._json_path))
        else:
            # Watch parent directory for file creation
            self._watcher.addPath(str(self._json_path.parent))
        
        # Watch artwork file if it exists
        if self._art_path.exists():
            self._watcher.addPath(str(self._art_path))

    def _on_file_changed(self, path: str = None):
        """
        Handle file change events with debouncing.
        This prevents rapid successive reads when a file is being written.
        """
        # Don't process changes too frequently
        current_time = time.time()
        if current_time - self._last_read_time < 0.5:  # 500ms cooldown
            # Schedule a debounced update
            if not self._pending_update:
                self._pending_update = True
                self._debounce_timer.start(self.DEBOUNCE_MS)
            return
        
        self._last_read_time = current_time
        self._pending_update = False
        self._process_file_change()

    def _process_file_change(self):
        """Actually process the file change after debouncing."""
        self._pending_update = False
        
        if not self._json_path.exists():
            # No file yet - emit inactive state
            payload = {
                "active": False,
                "artist": "",
                "title": "",
                "album": "",
                "pixmap": None,
            }
            if payload != self._last_payload:
                self._last_payload = payload
                self.updated.emit(payload)
            return

        # Check if file has content
        try:
            if self._json_path.stat().st_size == 0:
                # Empty file - probably being written, wait for next event
                return
        except OSError:
            return

        try:
            # Read JSON file
            content = self._json_path.read_text(encoding="utf-8")
            if not content.strip():
                # Empty content - ignore
                return
                
            data = json.loads(content)
        except json.JSONDecodeError as e:
            # File might be partially written - schedule a retry
            print(f"[MediaService] JSON decode error (will retry): {e}")
            if not self._pending_update:
                self._pending_update = True
                self._debounce_timer.start(self.DEBOUNCE_MS)
            return
        except Exception as e:
            print(f"[MediaService] Error reading JSON: {e}")
            return

        # Build payload
        payload = dict(data)
        
        # Add artwork if available
        if payload.get("artwork") and self._art_path.exists():
            try:
                pm = QPixmap(str(self._art_path))
                payload["pixmap"] = pm if not pm.isNull() else None
            except Exception:
                payload["pixmap"] = None
        else:
            payload["pixmap"] = None

        # Only emit if changed
        if payload != self._last_payload:
            self._last_payload = payload
            self.updated.emit(payload)
        
        # Ensure we're watching both files (in case they were created after startup)
        self._setup_watcher()

    def refresh(self):
        """Manually trigger a refresh."""
        self._on_file_changed()