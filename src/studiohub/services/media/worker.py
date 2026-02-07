from __future__ import annotations

import asyncio
import json
import hashlib
import time
from pathlib import Path
from typing import Optional

from studiohub.config.manager import ConfigManager

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager
    )
    from winsdk.windows.storage.streams import DataReader
except ImportError:
    MediaManager = None
    DataReader = None


class MediaWorkerUnavailable(RuntimeError):
    pass


class MediaWorker:
    def __init__(self, config: ConfigManager) -> None:
        if MediaManager is None:
            raise MediaWorkerUnavailable("winsdk not available")

        self._config = config

        base = config.get_appdata_root() / "media"
        base.mkdir(parents=True, exist_ok=True)

        self.json_path = base / "now_playing.json"
        self.art_path = base / "artwork.png"

        self.manager = None
        self.session = None

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._changed_evt = asyncio.Event()

        self._last_payload: Optional[dict] = None
        self._last_art_hash: Optional[str] = None

    # -------------------------
    # WinRT → asyncio bridge
    # -------------------------

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

    # -------------------------
    # Session management
    # -------------------------

    async def _refresh_session(self) -> None:
        self.session = self.manager.get_current_session()
        if self.session:
            self._attach_session_handlers()
            self._signal_changed()

    # -------------------------
    # IO helpers
    # -------------------------

    async def _read_thumbnail(self, props) -> tuple[Optional[bytes], Optional[str]]:
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

    def _write_json(self, payload: dict) -> None:
        self.json_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    # -------------------------
    # Snapshot
    # -------------------------

    async def _snapshot(self) -> None:
        if not self.session:
            payload = {
                "active": False,
                "updated": time.time(),
            }
        else:
            props = await self.session.try_get_media_properties_async()

            art_bytes, art_hash = await self._read_thumbnail(props)
            if art_hash and art_hash != self._last_art_hash and art_bytes:
                self.art_path.write_bytes(art_bytes)
                self._last_art_hash = art_hash

            payload = {
                "active": True,
                "updated": time.time(),
                "app": self.session.source_app_user_model_id,
                "artist": props.artist or "",
                "title": props.title or "",
                "album": props.album_title or "",
                "artwork": self.art_path.name if self._last_art_hash else None,
            }

        if payload != self._last_payload:
            self._write_json(payload)
            self._last_payload = payload

    # -------------------------
    # Main loop
    # -------------------------

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()

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
            await self._snapshot()
