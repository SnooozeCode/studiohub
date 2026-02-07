from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Set

from PySide6 import QtCore
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class _PosterFolderHandler(FileSystemEventHandler):
    """
    File- and directory-level handler.
    All events are resolved upward to poster root.
    """

    def __init__(self, mark_dirty: Callable[[Path], None]):
        self._mark_dirty = mark_dirty

    def on_created(self, event):
        self._mark_dirty(Path(event.src_path))

    def on_modified(self, event):
        self._mark_dirty(Path(event.src_path))

    def on_deleted(self, event):
        self._mark_dirty(Path(event.src_path))


class IndexWatcher(QtCore.QObject):
    """
    Watches Archive/ and Studio/ roots.
    Emits poster_dirty for debounced poster-level changes.
    """
    poster_dirty = QtCore.Signal(str)

    DEBOUNCE_SECONDS = 0.4

    def __init__(
        self,
        index_worker,
        archive_root: Path,
        studio_root: Path,
        parent=None,
    ):
        super().__init__(parent)

        self.index_worker = index_worker
        self.archive_root = archive_root
        self.studio_root = studio_root

        self._observer = Observer()
        self._pending: Set[Path] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

        handler = _PosterFolderHandler(self._mark_dirty)

        self._observer.schedule(handler, str(archive_root), recursive=True)
        self._observer.schedule(handler, str(studio_root), recursive=True)

    def start(self):
        self._observer.start()
        print("[IndexWatcher] started")

    def stop(self):
        self._observer.stop()
        self._observer.join()

    # ----------------------------
    # Internal
    # ----------------------------

    def _mark_dirty(self, path: Path):
        poster_path = self._resolve_poster_root(path)
        if not poster_path:
            return

        with self._lock:
            self._pending.add(poster_path)

            if self._timer:
                self._timer.cancel()

            self._timer = threading.Timer(
                self.DEBOUNCE_SECONDS,
                self._flush,
            )
            self._timer.start()

    def _flush(self):
        with self._lock:
            posters = list(self._pending)
            self._pending.clear()

        for poster_path in posters:
            self.poster_dirty.emit(str(poster_path))

    def _resolve_poster_root(self, path: Path) -> Path | None:
        for parent in [path, *path.parents]:
            if parent.parent == self.archive_root:
                return parent
            if parent.parent == self.studio_root:
                return parent
        return None
