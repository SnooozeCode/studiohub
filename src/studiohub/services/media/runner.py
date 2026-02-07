from __future__ import annotations

import asyncio
import threading

from studiohub.config.manager import ConfigManager
from studiohub.services.media.worker import MediaWorker
from studiohub.services.media.lock import MediaWorkerLock


def start_media_worker(config: ConfigManager) -> None:
    """
    Start MediaWorker in a background daemon thread.

    - Enforces OS-level singleton via lock file
    - Safe to call once during app startup
    """

    def _run() -> None:
        lock_path = config.get_appdata_root() / "media_worker.lock"
        lock = MediaWorkerLock(lock_path)

        try:
            lock.acquire()
        except RuntimeError as e:
            # Worker already running elsewhere — this is OK
            print(f"[MediaWorker] {e}")
            return

        try:
            asyncio.run(MediaWorker(config).run())
        finally:
            lock.release()

    thread = threading.Thread(
        target=_run,
        name="MediaWorker",
        daemon=True,
    )
    thread.start()
