"""Index management service for poster index lifecycle."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, Callable

from PySide6 import QtCore

from studiohub.config_manager import ConfigManager
from studiohub.hub_models.poster_index import load_poster_index
from studiohub.services.poster_index_worker import PosterIndexWorker
from studiohub.services.index_watcher import IndexWatcher


class IndexManager(QtCore.QObject):
    """
    Manages poster index lifecycle.
    
    Handles background indexing, file watching, and incremental updates.
    """
    
    # =====================================================
    # Signals - MUST be defined as class attributes
    # =====================================================
    index_started = QtCore.Signal()
    index_finished = QtCore.Signal(int, str)  # duration_ms, status
    index_error = QtCore.Signal(str)
    poster_updated = QtCore.Signal(str)  # poster_key
    status_message = QtCore.Signal(str)  # For status bar updates
    
    def __init__(
        self,
        config_manager: ConfigManager,
        status_callback: Optional[Callable[[str], None]] = None,
        parent: QtCore.QObject | None = None,
    ):
        """
        Initialize index manager.
        
        Args:
            config_manager: Configuration manager
            status_callback: Optional callback for status messages
            parent: Parent Qt object
        """
        super().__init__(parent)
        
        self._config = config_manager
        self._status_callback = status_callback
        self._index_running = False
        self._recently_indexed: dict[Path, float] = {}
        
        # Worker thread components
        self._index_thread: QtCore.QThread | None = None
        self._index_worker: PosterIndexWorker | None = None
        
        # Pending results from worker
        self._pending_result: tuple[int, str] | None = None
        self._pending_error: str | None = None
        
        # Incremental updates
        self._incremental_worker = PosterIndexWorker(config_manager)
        self._incremental_worker.poster_updated.connect(
            self._on_poster_updated,
            QtCore.Qt.QueuedConnection
        )
        
        # File watcher
        self._watcher: IndexWatcher | None = None
    
    # =====================================================
    # Internal helpers
    # =====================================================
    
    def _emit_status(self, message: str):
        """Emit status message via signal or callback."""
        self.status_message.emit(message)
        if self._status_callback:
            try:
                self._status_callback(message)
            except Exception:
                pass
    
    # =====================================================
    # Public API
    # =====================================================
    
    def load_index(self) -> dict:
        """
        Load poster index from disk.
        
        Returns:
            Index dictionary with fallback on error
        """
        try:
            path = self._config.get_poster_index_path()
            self._emit_status(f"Loading index from {path}")
            return load_poster_index(path)
        except Exception as e:
            self._emit_status(f"Failed to load index: {str(e)[:40]}")
            return {"posters": {"archive": {}, "studio": {}}}
    
    def start_full_index(self) -> bool:
        """
        Start a full background index operation.
        
        Returns:
            True if started, False if already running
        """
        if self._index_running:
            self._emit_status("Index already running")
            return False
        
        self._index_running = True
        self._pending_result = None
        self._pending_error = None
        self.index_started.emit()
        self._emit_status("Starting full index rebuild...")
        
        # Create worker thread
        self._index_thread = QtCore.QThread()
        self._index_worker = PosterIndexWorker(self._config)
        self._index_worker.moveToThread(self._index_thread)
        
        # Connect signals
        self._index_worker.finished.connect(
            self._on_index_finished,
            QtCore.Qt.QueuedConnection
        )
        self._index_worker.error.connect(
            self._on_index_error,
            QtCore.Qt.QueuedConnection
        )
        self._index_worker.status.connect(self._emit_status)
        
        self._index_thread.started.connect(self._index_worker.run)
        self._index_thread.finished.connect(
            self._on_thread_finished,
            QtCore.Qt.QueuedConnection
        )
        
        self._index_thread.start()
        return True
    
    def start_file_watcher(self) -> None:
        """Start file system watcher for incremental updates."""
        if self._watcher is not None:
            return
        
        try:
            archive_root = Path(self._config.get("paths", "archive_root", ""))
            studio_root = Path(self._config.get("paths", "studio_root", ""))
            
            if not archive_root.exists() or not studio_root.exists():
                self._emit_status("Cannot start file watcher: paths not configured")
                return
            
            self._watcher = IndexWatcher(
                index_worker=self._incremental_worker,
                archive_root=archive_root,
                studio_root=studio_root,
            )
            
            self._watcher.poster_dirty.connect(self._on_poster_dirty)
            self._watcher.start()
            self._emit_status("File watcher started")
            
        except Exception as e:
            self._emit_status(f"File watcher failed: {str(e)[:40]}")
    
    @property
    def is_running(self) -> bool:
        """Check if index operation is currently running."""
        return self._index_running
    
    # =====================================================
    # Signal handlers
    # =====================================================
    
    @QtCore.Slot(int, str)
    def _on_index_finished(self, duration_ms: int, status: str) -> None:
        """Handle index worker completion."""
        self._pending_result = (duration_ms, status)
        if self._index_thread and self._index_thread.isRunning():
            self._index_thread.quit()
    
    @QtCore.Slot(str)
    def _on_index_error(self, message: str) -> None:
        """Handle index worker error."""
        self._pending_error = message
        if self._index_thread and self._index_thread.isRunning():
            self._index_thread.quit()
    
    @QtCore.Slot()
    def _on_thread_finished(self) -> None:
        """Cleanup after thread finishes."""
        try:
            if self._index_worker is not None:
                self._index_worker.deleteLater()
            if self._index_thread is not None:
                self._index_thread.deleteLater()
        finally:
            self._index_worker = None
            self._index_thread = None
            self._index_running = False
        
        # Emit results
        if self._pending_error:
            self.index_error.emit(self._pending_error)
            self._pending_error = None
        elif self._pending_result:
            duration_ms, status = self._pending_result
            self.index_finished.emit(duration_ms, status)
            self._emit_status(f"Index finished in {duration_ms}ms")
            self._pending_result = None
    
    @QtCore.Slot(str)
    def _on_poster_dirty(self, poster_path_str: str) -> None:
        """
        Handle file watcher notification.
        
        Args:
            poster_path_str: Path to modified poster
        """
        if self._index_running:
            return
        
        poster_path = Path(poster_path_str)
        now = time.time()
        
        # Debounce rapid updates
        last = self._recently_indexed.get(poster_path)
        if last and (now - last) < 2.0:
            return
        
        self._recently_indexed[poster_path] = now
        self._emit_status(f"Poster changed: {poster_path.name}")
        # Incremental worker will handle the update
    
    @QtCore.Slot(str)
    def _on_poster_updated(self, poster_key: str) -> None:
        """
        Handle incremental poster update.
        
        Args:
            poster_key: Updated poster identifier
        """
        self.poster_updated.emit(poster_key)
        self._emit_status(f"Poster updated: {poster_key}")