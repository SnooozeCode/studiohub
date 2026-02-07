from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QFontMetrics, QPalette, QPaintEvent

from studiohub.theme.styles.typography import apply_typography

ART_SIZE = 112
LINE_SPACING = 6


# =====================================================
# Elided QLabel (PySide6-safe)
# =====================================================

class ElidedLabel(QtWidgets.QLabel):
    def __init__(self, text: str = "", parent: Optional[QtWidgets.QWidget] = None):
        super().__init__("", parent)
        self._full_text = text or ""
        self._elide_mode = Qt.ElideRight
        self.setWordWrap(False)
        super().setText(self._full_text)

    def setFullText(self, text: str) -> None:
        self._full_text = text or ""
        super().setText(self._full_text)
        self.update()
        self.updateGeometry()

    def setText(self, text: str) -> None:
        self.setFullText(text)

    def sizeHint(self):
        fm = self.fontMetrics()
        capped = self._full_text[:28] + "…" if len(self._full_text) > 28 else self._full_text
        return QtCore.QSize(fm.horizontalAdvance(capped) + 2, fm.height() + 2)

    def minimumSizeHint(self):
        fm = self.fontMetrics()
        return QtCore.QSize(fm.horizontalAdvance("…") + 2, fm.height() + 2)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        rect = self.contentsRect()
        if rect.width() <= 0:
            return

        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self._full_text, self._elide_mode, rect.width())
        painter.setPen(self.palette().color(QPalette.WindowText))
        painter.drawText(rect, int(self.alignment()) | Qt.TextSingleLine, elided)


# =====================================================
# Studio Mood Panel
# =====================================================

class StudioMoodPanel(QtWidgets.QWidget):
    """
    Studio Mood Panel (BODY ONLY)

    Header (Active Time) is owned by DashboardViewQt / DashboardCard.
    This panel emits active_time_changed(text) for header-right updates.
    """

    active_time_changed = QtCore.Signal(str)

    STATUS_UPDATE_MS = 30_000
    TIME_UPDATE_MS = 60_000  # minute granularity is perfect for "Active"

    def __init__(self, metrics, media_service, parent=None):
        super().__init__(parent)

        self.metrics = metrics
        self.media_service = media_service

        self._app_started_at = datetime.now()

        self._build_ui()
        self._bind_signals()

        # Prime UI state immediately
        self._refresh_time_context()
        self._update_status()
        self._emit_active_time()

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # -------------------------------------------------
        # Panel description (matches StudioPanel pattern)
        # -------------------------------------------------
        self.description = QtWidgets.QLabel(
            "Current studio vibe and music."
        )
        apply_typography(self.description, "caption")
        self.description.setObjectName("DashboardCardSubtitle")
        self.description.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(self.description)

        # ---------- MEDIA ROW ----------
        media_row = QtWidgets.QHBoxLayout()
        media_row.setSpacing(16)

        self.artwork = QtWidgets.QLabel()
        self.artwork.setFixedSize(ART_SIZE, ART_SIZE)
        self.artwork.setAlignment(Qt.AlignCenter)
        self.artwork.setProperty("role", "media-artwork")

        media_text = QtWidgets.QVBoxLayout()
        media_text.setSpacing(LINE_SPACING)
        media_text.setAlignment(Qt.AlignVCenter)

        self.lbl_song = ElidedLabel("—")
        apply_typography(self.lbl_song, "body-small")
        self.lbl_song.setStyleSheet("font-weight: 600;")
        self.lbl_song.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_song.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.lbl_artist = ElidedLabel("")
        apply_typography(self.lbl_artist, "caption")
        self.lbl_artist.setProperty("muted", True)

        self.lbl_album = ElidedLabel("")
        apply_typography(self.lbl_album, "caption")
        self.lbl_album.setProperty("muted", True)

        media_text.addWidget(self.lbl_song)
        media_text.addWidget(self.lbl_artist)
        media_text.addWidget(self.lbl_album)

        media_row.addWidget(self.artwork)
        media_row.addLayout(media_text)
        media_row.addStretch(1)

        root.addLayout(media_row)

        # ---------- DIVIDER ----------
        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Plain)
        divider.setObjectName("StudioMoodDivider")
        root.addWidget(divider)

        # ---------- SESSION CONTEXT (centered) ----------
        context_block = QtWidgets.QVBoxLayout()
        context_block.setSpacing(6)
        context_block.setAlignment(Qt.AlignHCenter)

        # Weather (muted, smallest)
        self.lbl_weather = QtWidgets.QLabel("")  # hide when empty
        apply_typography(self.lbl_weather, "caption")
        self.lbl_weather.setProperty("muted", True)
        self.lbl_weather.setAlignment(Qt.AlignHCenter)
        self.lbl_weather.hide()

        # Session (primary)
        self.lbl_time_of_day = QtWidgets.QLabel("")
        apply_typography(self.lbl_time_of_day, "body-small")
        self.lbl_time_of_day.setStyleSheet("font-weight: 600;")
        self.lbl_time_of_day.setAlignment(Qt.AlignHCenter)

        # Activity (secondary)
        self.lbl_activity = QtWidgets.QLabel("")
        apply_typography(self.lbl_activity, "caption")
        self.lbl_activity.setProperty("muted", True)
        self.lbl_activity.setAlignment(Qt.AlignHCenter)

        context_block.addWidget(self.lbl_weather)
        context_block.addWidget(self.lbl_time_of_day)
        context_block.addWidget(self.lbl_activity)

        root.addLayout(context_block)
        root.addStretch(1)

    # =====================================================
    # Signals / Timers
    # =====================================================

    def _bind_signals(self):
        # Media service may be None (lazy init / disabled)
        if self.media_service is not None and hasattr(self.media_service, "updated"):
            try:
                self.media_service.updated.connect(self._update_media)
            except Exception:
                pass

        # Status updates (printing/designing/maintenance/standing by)
        self._status_timer = QtCore.QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(self.STATUS_UPDATE_MS)

        # Time context + active time updates
        self._time_timer = QtCore.QTimer(self)
        self._time_timer.timeout.connect(self._on_minute_tick)
        self._time_timer.start(self.TIME_UPDATE_MS)

    def _on_minute_tick(self):
        self._refresh_time_context()
        self._emit_active_time()

    # =====================================================
    # Updates
    # =====================================================

    def _refresh_time_context(self):
        now = datetime.now()

        if 5 <= now.hour < 12:
            session = "Morning Session"
        elif 12 <= now.hour < 17:
            session = "Afternoon Session"
        elif 17 <= now.hour < 21:
            session = "Evening Session"
        else:
            session = "Late Night Session"

        self.lbl_time_of_day.setText(session)

    def _emit_active_time(self):
        """
        Emit header-right label text (e.g. "Active · 1:42" or "Active · 18m")
        """
        now = datetime.now()
        elapsed = now - self._app_started_at
        mins = int(elapsed.total_seconds() // 60)
        h, m = divmod(mins, 60)

        if h > 0:
            active = f"{h}:{m:02d}"
        else:
            active = f"{m}m"

        self.active_time_changed.emit(f"Active · {active}")

    def _update_media(self, payload: dict):
        title = payload.get("title") or "—"
        self.lbl_song.setFullText(title)
        self.lbl_song.setToolTip(title)

        self.lbl_artist.setFullText(payload.get("artist") or "")
        self.lbl_album.setFullText(payload.get("album") or "")

        pm = payload.get("pixmap")
        if isinstance(pm, QPixmap):
            self.artwork.setPixmap(
                pm.scaled(
                    ART_SIZE,
                    ART_SIZE,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

    def _update_status(self):
        # Maintenance: printer offline
        try:
            if not self.metrics.printer_online():
                self.lbl_activity.setText("Maintenance")
                return
        except Exception:
            # If printer status can't be checked, don't force "Maintenance"
            pass

        # Printing: last print within 5 minutes
        try:
            last_print = self.metrics.get_last_print_timestamp()
            if last_print and (datetime.now() - last_print).total_seconds() < 300:
                self.lbl_activity.setText("Printing")
                return
        except Exception:
            pass

        # Designing: active design app present
        try:
            app = self.metrics.get_active_design_app()
            if app:
                self.lbl_activity.setText("Designing")
                return
        except Exception:
            pass

        # Default: calm idle state
        self.lbl_activity.setText("Standing By")

    # =====================================================
    # Weather (wired-in label; actual fetch comes next)
    # =====================================================

    def set_weather_text(self, text: str | None) -> None:
        """
        Set the optional weather line (e.g. "Rainy Morning · 42°F").
        Pass None/"" to hide.
        """
        t = (text or "").strip()
        if not t:
            self.lbl_weather.clear()
            self.lbl_weather.hide()
            return
        self.lbl_weather.setText(t)
        self.lbl_weather.show()
