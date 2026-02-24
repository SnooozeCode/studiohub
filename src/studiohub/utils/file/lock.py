# studiohub/utils/file/lock.py
"""File-based locking for cross-process synchronization."""

from __future__ import annotations

import os
import time
from pathlib import Path


class FileLock:
    """
    Simple file-based lock for cross-process synchronization.
    
    Usage:
        with FileLock("/path/to/lock.file"):
            # Critical section
    """
    
    def __init__(self, lock_path: Path, timeout: float = 10.0):
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self._fd = None
    
    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        while True:
            try:
                self._fd = os.open(
                    str(self.lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                break
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock: {self.lock_path}")
                time.sleep(0.1)
        
        os.write(self._fd, str(os.getpid()).encode())
        os.fsync(self._fd)
        
        return self
    
    def __exit__(self, *args):
        if self._fd is not None:
            os.close(self._fd)
            try:
                self.lock_path.unlink()
            except:
                pass