from pathlib import Path
import os
import json
import time

from PySide6 import QtCore
from PySide6.QtGui import QPixmap


class MediaSessionService(QtCore.QObject):
    """
    UI-facing media service.

    Responsibilities:
    - Poll runtime/media/now_playing.json (written by media_worker)
    - Emit media updates for UI
    - Send media control commands to media_worker via control.json

    NOTE:
    - Does NOT import winsdk
    - Does NOT control media directly
    """

    updated = QtCore.Signal(dict)

    POLL_INTERVAL_MS = 1000

    def __init__(self, root_path=None, parent=None):
        super().__init__(parent)

        # Authoritative runtime media directory
        self.media_dir = Path(os.getenv('APPDATA', str(Path.home()))) / 'SnooozeCo' / 'StudioHub' / 'media'
        self.media_dir.mkdir(parents=True, exist_ok=True)

        self.json_path = self.media_dir / "now_playing.json"
        self.art_path = self.media_dir / "artwork.png"

        self._last_payload: dict | None = None

        # Poll timer (JSON → UI)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(self.POLL_INTERVAL_MS)


    # =====================================================
    # JSON polling → UI updates
    # =====================================================

    def _poll(self):
        if not self.json_path.exists():
            return

        try:
            data = json.loads(
                self.json_path.read_text(encoding="utf-8")
            )
        except Exception:
            return

        payload = {
            "active": data.get("active", False),
            "artist": data.get("artist"),
            "title": data.get("title"),
            "album": data.get("album"),
        }

        if self.art_path.exists():
            pm = QPixmap(str(self.art_path))
            if not pm.isNull():
                payload["pixmap"] = pm

        if payload == self._last_payload:
            return

        self._last_payload = payload
        self.updated.emit(payload)