from __future__ import annotations

import asyncio
import json
import hashlib
import time
from pathlib import Path
from typing import Optional
import os
import atexit
import sys

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager
    )
    from winsdk.windows.storage.streams import DataReader
except ImportError as e:
    print("[media_worker] winsdk unavailable:", e)
    raise SystemExit(0)

# ======================================================
# Runtime paths (LOCAL, NOT SHARED)
# ======================================================

OUT_DIR = Path(os.getenv('APPDATA', str(Path.home()))) / 'SnooozeCo' / 'StudioHub' / 'media'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

JSON_PATH = OUT_DIR / "now_playing.json"
ART_PATH = OUT_DIR / "artwork.png"
PID_PATH = OUT_DIR / "media_worker.pid"


# ======================================================
# Singleton guard (PID file)
# ======================================================

def _cleanup_pid():
    try:
        PID_PATH.unlink(missing_ok=True)
    except Exception:
        pass


def _pid_is_running(pid: int) -> bool:
    try:
        import psutil
    except Exception:
        # If psutil is unavailable, be conservative and assume running
        return True

    try:
        p = psutil.Process(pid)
        return p.is_running()
    except Exception:
        return False


if PID_PATH.exists():
    try:
        old_pid = int(PID_PATH.read_text(encoding="utf-8").strip())
    except Exception:
        old_pid = None

    if old_pid and _pid_is_running(old_pid):
        raise SystemExit("[media_worker] PID file exists; exiting (already running)")
    else:
        # Stale PID file
        try:
            PID_PATH.unlink(missing_ok=True)
        except Exception:
            pass

PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
atexit.register(_cleanup_pid)

# ======================================================
# Windows-safe write (overwrite with retry)
# ======================================================

def write_file(path: Path, data: bytes | str) -> None:
    for _ in range(5):
        try:
            if isinstance(data, str):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
            else:
                with open(path, "wb") as f:
                    f.write(data)
            return
        except PermissionError:
            time.sleep(0.05)
    raise PermissionError(f"Could not write {path}")


# ======================================================
# Thumbnail reader
# ======================================================

async def read_thumbnail(props) -> tuple[Optional[bytes], Optional[str]]:
    thumb = getattr(props, "thumbnail", None)
    if not thumb:
        return None, None

    stream = await thumb.open_read_async()
    reader = DataReader(stream)

    size = int(stream.size)
    if size <= 0:
        return None, None

    await reader.load_async(size)
    buf = bytearray(size)
    reader.read_bytes(buf)

    data = bytes(buf)
    return data, hashlib.md5(data).hexdigest()


# ======================================================
# Media Worker
# ======================================================

class MediaWorker:
    def __init__(self) -> None:
        self.manager = None
        self.session = None

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._changed_evt = asyncio.Event()

        self._last_payload: Optional[dict] = None
        self._last_art_hash: Optional[str] = None

    # -----------------------------
    # WinRT callback → asyncio
    # -----------------------------

    def _signal_changed(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._changed_evt.set)

    def _attach_session_handlers(self) -> None:
        if not self.session:
            return

        self.session.add_media_properties_changed(
            lambda *_: self._signal_changed()
        )
        self.session.add_playback_info_changed(
            lambda *_: self._signal_changed()
        )

    # -----------------------------
    # Session management
    # -----------------------------

    async def _refresh_session(self) -> None:
        self.session = self.manager.get_current_session()
        if self.session:
            self._attach_session_handlers()
            self._signal_changed()

    # -----------------------------
    # Snapshot + write (ONLY ON CHANGE)
    # -----------------------------

    async def _snapshot_and_write(self) -> None:
        if not self.session:
            payload = {
                "active": False,
                "updated": time.time(),
            }
        else:
            props = await self.session.try_get_media_properties_async()

            artist = props.artist or ""
            title = props.title or ""
            album = props.album_title or ""

            art_bytes, art_hash = await read_thumbnail(props)
            if art_hash and art_hash != self._last_art_hash and art_bytes:
                write_file(ART_PATH, art_bytes)
                self._last_art_hash = art_hash

            payload = {
                "active": True,
                "updated": time.time(),
                "app": self.session.source_app_user_model_id,
                "artist": artist,
                "title": title,
                "album": album,
                "artwork": ART_PATH.name if self._last_art_hash else None,
            }

        if payload != self._last_payload:
            write_file(JSON_PATH, json.dumps(payload, indent=2))
            self._last_payload = payload

    # -----------------------------
    # Main loop
    # -----------------------------

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()

        print("[media_worker] JSON:", JSON_PATH)
        print("[media_worker] ART :", ART_PATH)

        self.manager = await MediaManager.request_async()
        self.manager.add_current_session_changed(
            lambda *_: self._signal_changed()
        )

        await self._refresh_session()

        while True:
            try:
                await asyncio.wait_for(self._changed_evt.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                pass

            self._changed_evt.clear()
            await self._refresh_session()

            try:
                await self._snapshot_and_write()
            except Exception as e:
                write_file(JSON_PATH, json.dumps({"error": str(e)}))
                print("[media_worker] ERROR:", e)


# ======================================================
# Entrypoint
# ======================================================

async def main() -> None:
    worker = MediaWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())