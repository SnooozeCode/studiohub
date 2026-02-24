# studiohub/utils/file/lock.py

"""File-based locking for cross-process synchronization."""

from __future__ import annotations

import os
import time
import psutil
from pathlib import Path


class FileLock:
    """
    Simple file-based lock for cross-process synchronization.
    
    Usage:
        with FileLock("/path/to/lock.file"):
            # Critical section
    """
    
    def __init__(self, lock_path: Path, timeout: float = 10.0, stale_timeout: float = 5.0):
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.stale_timeout = stale_timeout  # Time after which a lock is considered stale
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
                # Write PID to lock file for debugging
                os.write(self._fd, str(os.getpid()).encode())
                os.fsync(self._fd)
                break
            except FileExistsError:
                # Check if lock is stale
                if self._is_lock_stale():
                    # Remove stale lock and try again
                    try:
                        self.lock_path.unlink()
                        continue
                    except Exception:
                        pass
                
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock: {self.lock_path}")
                time.sleep(0.1)
        
        return self
    
    def _is_lock_stale(self) -> bool:
        """Check if the existing lock is stale."""
        try:
            # Read PID from lock file
            content = self.lock_path.read_text().strip()
            if not content:
                return True
            
            pid = int(content)
            
            # Check if process is still running
            return not psutil.pid_exists(pid)
            
        except (ValueError, IOError, OSError, psutil.NoSuchProcess):
            # If we can't read the file or the PID doesn't exist, it's stale
            return True
        except Exception:
            return False
    
    def __exit__(self, *args):
        if self._fd is not None:
            os.close(self._fd)
            try:
                self.lock_path.unlink()
            except:
                pass