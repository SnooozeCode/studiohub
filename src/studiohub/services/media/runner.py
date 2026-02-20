from __future__ import annotations

import asyncio
import threading
import time
import traceback
from pathlib import Path

from studiohub.config.manager import ConfigManager
from studiohub.services.media.worker import MediaWorker
from studiohub.services.media.lock import MediaWorkerLock


def start_media_worker(config: ConfigManager) -> None:
    """
    Start MediaWorker in a background daemon thread with auto-restart.
    """
    media_dir = config.get_appdata_root() / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    
    lock_path = media_dir / "media_worker.lock"

    def _run_worker():
        """Run worker with automatic restart on crash."""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            lock = MediaWorkerLock(lock_path)
            
            try:
                lock.acquire()
                
                # Run the worker
                asyncio.run(MediaWorker(config).run())
                break  # Normal exit
                
            except RuntimeError:
                # Worker already running elsewhere
                break
                
            except Exception as e:
                print(f"[MediaWorker] Worker crashed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
            finally:
                try:
                    lock.release()
                except:
                    pass

    thread = threading.Thread(
        target=_run_worker,
        name="MediaWorker",
        daemon=True,
    )
    thread.start()