from __future__ import annotations

import os
from pathlib import Path

# Windows-only, intentional
import msvcrt

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
        self._file = None

    def acquire(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Open or create lock file
        self._file = open(self._path, "a+")

        try:
            # Lock 1 byte, non-blocking
            msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("MediaWorker already running")

    def release(self):
        if not self._file:
            return
        try:
            # Ensure file is unlocked even if process crashes
            import fcntl  # Use fcntl for better cross-platform
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        except:
            pass
        finally:
            try:
                self._file.close()
            except:
                pass
            self._file = None
