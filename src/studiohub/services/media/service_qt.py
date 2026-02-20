from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QPixmap

from studiohub.config.manager import ConfigManager


class MediaServiceQt(QObject):
    updated = Signal(dict)

    POLL_MS = 1500

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)

        base = config.get_appdata_root() / "media"
        self._json_path = base / "now_playing.json"
        self._art_path = base / "artwork.png"

        self._last_payload: Optional[dict] = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(self.POLL_MS)

    def _poll(self) -> None:
        if not self._json_path.exists():
            return

        try:
            data = json.loads(self._json_path.read_text(encoding="utf-8"))
        except Exception:
            return

        if data == self._last_payload:
            return

        payload = dict(data)

        if payload.get("artwork") and self._art_path.exists():
            pm = QPixmap(str(self._art_path))
            payload["pixmap"] = pm if not pm.isNull() else None
        else:
            payload["pixmap"] = None

        self._last_payload = data
        self.updated.emit(payload)