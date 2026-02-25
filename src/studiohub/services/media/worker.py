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
        
        self._session_changed_cb = lambda *_: self._signal_changed()
        self._props_changed_cb = lambda *_: self._signal_changed()
        self._playback_changed_cb = lambda *_: self._signal_changed()
        
        self._attached_session_id = None
        
        self._json_encoder = json.JSONEncoder(indent=2)
        self._last_write_time = 0
        self._last_snapshot_time = 0

    # -------------------------
    # WinRT → asyncio bridge
    # -------------------------

    def _signal_changed(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._changed_evt.set)

    def _attach_session_handlers(self) -> None:
        """Attach handlers to current session only if not already attached to THIS session."""
        if not self.session:
            return
        
        # Get a unique identifier for this session
        try:
            # Try to get a stable session ID - using object id as fallback
            current_session_id = id(self.session)
        except:
            current_session_id = None
        
        # Skip if we already attached handlers to THIS session
        if self._attached_session_id == current_session_id:
            return
        
        # Detach from old session if possible
        if self._attached_session_id is not None:
            self._detach_session_handlers()
        
        try:
            # Attach to new session using pre-created callbacks
            self.session.add_media_properties_changed(self._props_changed_cb)
            self.session.add_playback_info_changed(self._playback_changed_cb)
            self._attached_session_id = current_session_id
            # Optional: Comment this out after confirming it works
            # print(f"[MediaWorker] Handlers attached to session {current_session_id}")
        except Exception as e:
            print(f"[MediaWorker] Failed to attach session handlers: {e}")

    def _detach_session_handlers(self) -> None:
        """Try to detach handlers from old session."""
        if not self.session:
            return
        
        try:
            # Try to remove handlers (if API supports it)
            if hasattr(self.session, 'remove_media_properties_changed'):
                self.session.remove_media_properties_changed(self._props_changed_cb)
            if hasattr(self.session, 'remove_playback_info_changed'):
                self.session.remove_playback_info_changed(self._playback_changed_cb)
        except Exception as e:
            # Ignore errors - not all APIs support removal
            pass
        finally:
            self._attached_session_id = None

    # -------------------------
    # Session management
    # -------------------------

    async def _refresh_session(self) -> None:
        try:
            new_session = self.manager.get_current_session()
            
            if new_session != self.session:
                # Session changed
                if self.session:
                    self._detach_session_handlers()
                
                self.session = new_session
                
            if self.session:
                self._attach_session_handlers()
                self._signal_changed()
                
        except Exception as e:
            print(f"[MediaWorker] Session refresh error: {e}")
            self.session = None
            self._attached_session_id = None

    # -------------------------
    # IO helpers
    # -------------------------

    async def _read_thumbnail(self, props) -> tuple[Optional[bytes], Optional[str]]:
        thumb = getattr(props, "thumbnail", None)
        if not thumb:
            return None, None

        try:
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
        except Exception as e:
            print(f"[MediaWorker] Failed to read thumbnail: {e}")
            return None, None

    def _write_json(self, payload: dict) -> None:
        """Write JSON with throttling and proper file locking."""
        import time
        import os
        
        # Throttle writes - don't write more than once per 500ms
        current_time = time.time()
        if hasattr(self, '_last_write_time') and current_time - self._last_write_time < 0.5:
            return  # Skip this write, too frequent
        
        max_retries = 3
        retry_delay = 0.1
        
        # Create lock file path
        lock_path = self.json_path.with_suffix('.lock')
        content = self._json_encoder.encode(payload)
        
        for attempt in range(max_retries):
            try:
                # Try to create lock file exclusively
                try:
                    with open(lock_path, 'x') as f:
                        f.write(str(os.getpid()))
                except FileExistsError:
                    # Lock exists, check if it's stale
                    if lock_path.exists():
                        try:
                            # If lock is older than 2 seconds, assume it's stale
                            lock_age = time.time() - lock_path.stat().st_mtime
                            if lock_age > 2.0:
                                lock_path.unlink()
                                continue
                        except:
                            pass
                    
                    if attempt == max_retries - 1:
                        # Last attempt - skip write rather than force it
                        print(f"[MediaWorker] Could not acquire lock after {max_retries} attempts, skipping write")
                        return
                    
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                
                # We have the lock - now write the file
                try:
                    # Write directly to the target file (no temp file)
                    # This avoids rename issues
                    self.json_path.write_text(content, encoding='utf-8')
                    self._last_write_time = current_time
                    return  # Success!
                    
                finally:
                    # Always release the lock
                    try:
                        lock_path.unlink()
                    except:
                        pass
                        
            except PermissionError as e:
                if attempt == max_retries - 1:
                    print(f"[MediaWorker] Failed to write JSON after {max_retries} attempts: {e}")
                    # Skip write rather than risk corruption
                    return
                else:
                    time.sleep(retry_delay * (2 ** attempt))
            except Exception as e:
                print(f"[MediaWorker] Error writing JSON: {e}")
                return

    # -------------------------
    # Snapshot
    # -------------------------

    async def _snapshot(self) -> None:
        # Add throttle to prevent too frequent writes
        current_time = time.time()
        if hasattr(self, '_last_snapshot_time') and current_time - self._last_snapshot_time < 0.5:
            return  # Skip if last snapshot was less than 500ms ago
        
        try:
            if not self.session:
                payload = {
                    "active": False,
                    "updated": time.time(),
                }
            else:
                props = await self.session.try_get_media_properties_async()

                art_bytes, art_hash = await self._read_thumbnail(props)
                if art_hash and art_hash != self._last_art_hash and art_bytes:
                    try:
                        self.art_path.write_bytes(art_bytes)
                        self._last_art_hash = art_hash
                    except Exception as e:
                        print(f"[MediaWorker] Failed to write artwork: {e}")

                payload = {
                    "active": True,
                    "updated": time.time(),
                    "app": self.session.source_app_user_model_id or "",
                    "artist": props.artist or "",
                    "title": props.title or "",
                    "album": props.album_title or "",
                    "artwork": self.art_path.name if self._last_art_hash else None,
                }

            if payload != self._last_payload:
                self._write_json(payload)
                self._last_payload = payload
                self._last_snapshot_time = current_time
                
        except Exception as e:
            print(f"[MediaWorker] Snapshot error: {e}")
            # Write error state
            error_payload = {
                "active": False,
                "error": "Media worker error",
                "updated": time.time(),
            }
            self._write_json(error_payload)

    # -------------------------
    # Main loop
    # -------------------------

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()

        try:
            self.manager = await MediaManager.request_async()
            # Use pre-created callback
            self.manager.add_current_session_changed(self._session_changed_cb)
            # Optional: Comment this out after confirming it works
            # print("[MediaWorker] Media manager initialized")
        except Exception as e:
            print(f"[MediaWorker] Failed to initialize media manager: {e}")
            error_payload = {
                "active": False,
                "error": "Failed to initialize media manager",
                "updated": time.time(),
            }
            self._write_json(error_payload)
            return

        await self._refresh_session()

        while True:
            try:
                await asyncio.wait_for(self._changed_evt.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                # Timeout is normal - just continue
                pass
            except Exception as e:
                print(f"[MediaWorker] Event wait error: {e}")
                self._changed_evt.clear()
                await asyncio.sleep(1)
                continue

            self._changed_evt.clear()
            
            try:
                await self._refresh_session()
                await self._snapshot()
            except Exception as e:
                print(f"[MediaWorker] Main loop error: {e}")
                await asyncio.sleep(2)