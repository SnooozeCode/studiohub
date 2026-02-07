from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from PySide6 import QtCore

from studiohub.hub_models.poster_index import load_poster_index


SOURCE_KEY_MAP = {
    "patents": "archive",
    "studio": "studio",
}


class PosterIndexState(QtCore.QObject):
    """
    Single source of truth for the loaded poster index.

    Responsibilities:
      - Load poster_index.json from disk
      - Hold snapshot + metadata
      - Emit change notifications

    Explicitly does NOT:
      - Compute metrics
      - Perform scans
      - Own UI state
    """

    changed = QtCore.Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)

        self._snapshot: dict[str, Any] | None = None
        self._path: Path | None = None
        self._loaded_at: datetime | None = None
        self._last_error: Exception | None = None

    # -------------------------------------------------
    # Load / lifecycle
    # -------------------------------------------------

    def load(self, path: Path) -> None:
        try:
            data = load_poster_index(path)

            raw_posters = data.get("posters", {})
            normalized_posters: dict[str, Any] = {}

            for raw_key, posters in raw_posters.items():
                canonical_key = SOURCE_KEY_MAP.get(raw_key, raw_key)
                normalized_posters[canonical_key] = posters

            self._snapshot = {
                **data,
                "posters": normalized_posters,
            }

            self._path = path
            self._loaded_at = datetime.now(timezone.utc)
            self._last_error = None

            self.changed.emit()

        except Exception as exc:
            self._last_error = exc
            raise


    # -------------------------------------------------
    # State access
    # -------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._snapshot is not None

    @property
    def snapshot(self) -> dict[str, Any]:
        if self._snapshot is None:
            raise RuntimeError("PosterIndexState accessed before load()")
        return self._snapshot

    @property
    def loaded_at(self) -> datetime | None:
        return self._loaded_at

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def last_error(self) -> Exception | None:
        return self._last_error

    # -------------------------------------------------
    # Minimal canonical helpers (safe, boring)
    # -------------------------------------------------

    def sources(self) -> list[str]:
        if not self.is_loaded:
            return []
        return list(self.snapshot.get("posters", {}).keys())

    def posters(self, source: str) -> dict[str, Any]:
        if not self.is_loaded:
            return {}
        return self.snapshot.get("posters", {}).get(source, {})
