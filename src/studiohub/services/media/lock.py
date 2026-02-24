# studiohub/services/media/lock.py

from __future__ import annotations

from pathlib import Path

from studiohub.utils import FileLock, get_logger

logger = get_logger(__name__)


class MediaWorkerLock:
    """
    OS-level singleton lock for MediaWorker.

    Uses a non-blocking file lock:
    - Prevents multiple workers across processes
    - Automatically released on crash / exit
    - No stale PID files
    """

    def __init__(self, lock_path: Path):
        self._path = lock_path
        self._lock: FileLock | None = None

    def acquire(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use FileLock from utils with stale detection
        self._lock = FileLock(self._path, timeout=0, stale_timeout=5.0)  # Non-blocking with stale detection
        try:
            self._lock.__enter__()
            logger.debug(f"Acquired media worker lock: {self._path}")
        except TimeoutError:
            raise RuntimeError("MediaWorker already running")
        except Exception as e:
            logger.error(f"Failed to acquire media worker lock: {e}")
            raise

    def release(self):
        if self._lock:
            try:
                self._lock.__exit__(None, None, None)
                logger.debug("Released media worker lock")
            except Exception as e:
                logger.error(f"Failed to release media worker lock: {e}")
            finally:
                self._lock = None