# studiohub/services/media/runner.py

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Qt

from studiohub.config.manager import ConfigManager
from studiohub.services.media.worker import MediaWorker
from studiohub.services.media.lock import MediaWorkerLock
from studiohub.utils.logging.core import get_logger

logger = get_logger(__name__)


class MediaWorkerRunner(QObject):
    """Runner for media worker with Qt signals for status."""
    
    status_message = Signal(str)
    
    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config
        self._thread: threading.Thread | None = None
        self._running = False
        self._logger = logger  # Add logger instance
    
    def start(self):
        """Start the media worker thread."""
        if self._running:
            self.status_message.emit("Media worker already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._run_worker,
            name="MediaWorker",
            daemon=True,
        )
        self._thread.start()
        self.status_message.emit("Media worker thread started")
        self._logger.info("Media worker thread started")
    
    def stop(self):
        """Stop the media worker thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._logger.info("Media worker stopped")
        
    def _run_worker(self):
        """Run worker with automatic restart on crash."""
        media_dir = self._config.get_appdata_root() / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        
        lock_path = media_dir / "media_worker.lock"
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            if not self._running:
                break
                
            lock = MediaWorkerLock(lock_path)
            
            try:
                lock.acquire()
                self._emit_status("Starting media worker...")
                self._logger.info("Media worker starting")
                
                # Run the worker
                asyncio.run(MediaWorker(self._config).run())
                break  # Normal exit
                
            except RuntimeError as e:
                # Worker already running elsewhere
                msg = "Media worker already running in another process"
                self._emit_status(msg)
                self._logger.warning(f"{msg}: {e}")
                break
                
            except Exception as e:
                msg = f"Media worker crashed (attempt {attempt + 1}/{max_retries})"
                self._emit_status(msg)
                self._logger.error(f"{msg}: {e}", exc_info=True)
                
                if attempt < max_retries - 1 and self._running:
                    self._logger.info(f"Restarting media worker in {retry_delay}s...")
                    time.sleep(retry_delay)
                    
            finally:
                try:
                    lock.release()
                except Exception as e:
                    self._logger.error(f"Failed to release lock: {e}")
        
        if self._running:
            self._logger.info("Media worker stopped")
    
    def _emit_status(self, msg: str):
        """Emit status message safely from background thread."""
        # Direct emit - signals are thread-safe in Qt
        self.status_message.emit(msg)

# Convenience function for backward compatibility
def start_media_worker(config: ConfigManager, parent: Optional[QObject] = None) -> MediaWorkerRunner:
    """
    Start MediaWorker in a background daemon thread with auto-restart.
    
    Args:
        config: Configuration manager
        parent: Parent QObject for the runner (usually MainWindow)
    
    Returns:
        MediaWorkerRunner instance (can be ignored if not needed)
    """
    runner = MediaWorkerRunner(config)
    if parent:
        runner.setParent(parent)
    runner.start()
    return runner