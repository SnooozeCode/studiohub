"""
Studio Mood Panel - Matches first image exactly with:
- Active time in header (handled by container)
- Track, Artist, Album in correct order with QSS styling
- Session time (Morning/Afternoon Session)
- Current task (Designing/Printing/Standing By)
- Proper spacing between elements
- Larger artwork (80x80)
- NO padding (container handles it)
"""

from __future__ import annotations

from datetime import datetime
import psutil

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

from studiohub.style.typography.rules import apply_typography

class StudioMoodPanel(QtWidgets.QWidget):
    """
    Studio Mood panel that matches the first image exactly.
    """
    
    # Signal emitted when active time changes (for header)
    active_time_changed = Signal(str)
    
    def __init__(self, media_service, print_log_state=None, parent=None):
        super().__init__(parent)
        self.setObjectName("StudioMoodPanel")
        
        self._media_service = media_service
        self._print_log_state = print_log_state
        self._active_start_time = None
        self._current_media_active = False
        
        # Active time timer (updates every second)
        self._active_timer = QtCore.QTimer(self)
        self._active_timer.timeout.connect(self._update_active_time)
        self._active_timer.setInterval(1000)
        
        # Task check timer (checks every 10 seconds)
        self._task_timer = QtCore.QTimer(self)
        self._task_timer.timeout.connect(self._update_current_task)
        self._task_timer.setInterval(10000)
        
        self._build_ui()
        self._connect_signals()
        
        # Initial updates
        self._update_session_time()
        self._update_current_task()
        self._task_timer.start()
        
    def _build_ui(self):
        """Build the panel UI matching the first image exactly."""
        # NO PADDING - container handles it
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Subtitle
        subtitle = QLabel("Current studio vibe and music.")
        subtitle.setObjectName("DashboardSubtitle")
        apply_typography(subtitle, "caption")
        subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        subtitle.setFixedHeight(14)
        layout.addWidget(subtitle)
        
        # =====================================================
        # Media row
        # =====================================================
        media_row = QtWidgets.QHBoxLayout()
        media_row.setContentsMargins(0, 0, 0, 0)
        media_row.setSpacing(16)
        
        # Album artwork - 102x102
        self.artwork_label = QtWidgets.QLabel()
        self.artwork_label.setObjectName("StudioMoodArtwork")
        self.artwork_label.setFixedSize(102, 102)
        self.artwork_label.setScaledContents(False)
        self.artwork_label.setAlignment(Qt.AlignCenter)

        # Container for text to allow vertical centering
        text_container = QtWidgets.QWidget()
        text_container.setObjectName("StudioMoodTextContainer")
        text_layout = QtWidgets.QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        
        # Add stretch before and after to center vertically
        text_layout.addStretch()
        
        # Track title (first)
        self.track_label = QtWidgets.QLabel("")
        self.track_label.setObjectName("StudioMoodTrack")
        apply_typography(self.track_label, "body")
        self.track_label.setWordWrap(True)
        self.track_label.hide()  # Hide by default
        text_layout.addWidget(self.track_label)
        
        # Artist name (second)
        self.artist_label = QtWidgets.QLabel("")
        self.artist_label.setObjectName("StudioMoodArtist")
        apply_typography(self.artist_label, "body-small")
        self.artist_label.setWordWrap(True)
        self.artist_label.hide()
        text_layout.addWidget(self.artist_label)
        
        # Album name (third)
        self.album_label = QtWidgets.QLabel("")
        self.album_label.setObjectName("StudioMoodAlbum")
        apply_typography(self.album_label, "body-small")
        self.album_label.setWordWrap(True)
        self.album_label.hide()
        text_layout.addWidget(self.album_label)
        
        # Placeholder when no media
        self.no_media_label = QtWidgets.QLabel("No media playing")
        self.no_media_label.setObjectName("StudioMoodNoMedia")
        self.no_media_label.setWordWrap(True)
        text_layout.addWidget(self.no_media_label)
        
        text_layout.addStretch()
        
        media_row.addWidget(self.artwork_label)
        media_row.addWidget(text_container, 1)  # Give text container stretch
        media_row.addStretch()
        
        layout.addLayout(media_row)
        
        # Extra spacing after media section
        layout.addSpacing(8)

        # =====================================================
        # Divider
        # =====================================================
        divider = QtWidgets.QFrame()
        divider.setObjectName("DashboardDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        
        # =====================================================
        # Session + Task row (side by side)
        # =====================================================
        session_task_row = QtWidgets.QHBoxLayout()
        session_task_row.setContentsMargins(0, 0, 0, 0)
        session_task_row.setSpacing(8)
        
        # Session time (Morning Session / Afternoon Session)
        self.session_label = QtWidgets.QLabel("Afternoon Session")
        apply_typography(self.session_label, "body")
        self.session_label.setObjectName("StudioMoodSession")
        
        # Current task (Designing/Printing/Standing By) - right aligned
        self.task_label = QtWidgets.QLabel("Designing")
        apply_typography(self.task_label, "body")
        self.task_label.setObjectName("StudioMoodTask")
        self.task_label.setAlignment(Qt.AlignRight)
        
        session_task_row.addWidget(self.session_label)
        session_task_row.addStretch()
        session_task_row.addWidget(self.task_label)
        
        layout.addLayout(session_task_row)
        
        # Extra spacing after session row
        layout.addSpacing(12)
        layout.addStretch()

    def _connect_signals(self):
        """Connect to media service signals."""
        if self._media_service:
            self._media_service.updated.connect(self._on_media_updated)
    

    def _on_media_updated(self, payload: dict):
        """Handle media updates from the service with text truncation."""
        active = payload.get("active", False)
        artist = payload.get("artist", "")
        title = payload.get("title", "")
        album = payload.get("album", "")
        pixmap = payload.get("pixmap")
        
        self._current_media_active = active
        
        if active and (title or artist or album):
            # Hide no media label
            self.no_media_label.hide()
            
            # Store full text and show track (first)
            if title:
                self.track_label._full_text = title
                self.track_label.setText(title)  # Will be truncated after layout
                self.track_label.show()
            else:
                self.track_label.hide()
            
            # Store full text and show artist (second)
            if artist:
                self.artist_label._full_text = artist
                self.artist_label.setText(artist)
                self.artist_label.show()
            else:
                self.artist_label.hide()
            
            # Store full text and show album (third)
            if album:
                self.album_label._full_text = album
                self.album_label.setText(album)
                self.album_label.show()
            else:
                self.album_label.hide()
            
            # Start/update active timer
            if not self._active_start_time:
                self._active_start_time = datetime.now()
                self._active_timer.start()
                self._update_active_time()
            
            # Update artwork
            if pixmap and isinstance(pixmap, QPixmap):
                self._set_scaled_artwork(pixmap)
            else:
                self.artwork_label.clear()
            
            # Apply truncation after layout is complete
            QtCore.QTimer.singleShot(0, self._apply_truncation)
            
        else:
            # Show no media label
            self.no_media_label.show()
            self.track_label.hide()
            self.artist_label.hide()
            self.album_label.hide()
            self.artwork_label.clear()
            self._active_start_time = None
            self._active_timer.stop()
            self.active_time_changed.emit("Active · 0m")

    def _truncate_text_to_fit(self, text: str, label: QLabel) -> str:
        """
        Truncate text with ellipsis to fit the label's current width.
        """
        if not text:
            return text
            
        font_metrics = label.fontMetrics()
        # Leave 10px padding on each side
        available_width = label.width() - 20
        
        # If text already fits, return as-is
        if font_metrics.horizontalAdvance(text) <= available_width:
            return text
        
        # Binary search for the maximum length that fits
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            truncated = text[:mid] + "…"
            if font_metrics.horizontalAdvance(truncated) <= available_width:
                low = mid
            else:
                high = mid - 1
        
        return text[:low] + "…"

    def _apply_truncation(self):
        """Apply dynamic truncation to all visible text labels."""
        # Store full text in user data if not already set
        if self.track_label.isVisible():
            # Store full text as user data if not already done
            if not hasattr(self.track_label, '_full_text'):
                self.track_label._full_text = self.track_label.text()
            
            full_text = self.track_label._full_text
            truncated = self._truncate_text_to_fit(full_text, self.track_label)
            self.track_label.setText(truncated)
            self.track_label.setToolTip(full_text if truncated != full_text else "")
        
        if self.artist_label.isVisible():
            if not hasattr(self.artist_label, '_full_text'):
                self.artist_label._full_text = self.artist_label.text()
            
            full_text = self.artist_label._full_text
            truncated = self._truncate_text_to_fit(full_text, self.artist_label)
            self.artist_label.setText(truncated)
            self.artist_label.setToolTip(full_text if truncated != full_text else "")
        
        if self.album_label.isVisible():
            if not hasattr(self.album_label, '_full_text'):
                self.album_label._full_text = self.album_label.text()
            
            full_text = self.album_label._full_text
            truncated = self._truncate_text_to_fit(full_text, self.album_label)
            self.album_label.setText(truncated)
            self.album_label.setToolTip(full_text if truncated != full_text else "")

    def resizeEvent(self, event):
        """Handle resize events to re-apply truncation."""
        super().resizeEvent(event)
        # Re-apply truncation when panel is resized
        if hasattr(self, '_apply_truncation'):
            QtCore.QTimer.singleShot(0, self._apply_truncation)


    def _set_scaled_artwork(self, pixmap: QPixmap):
        """
        Scale artwork to fit within 102x102 while preserving aspect ratio.
        The label's fixed size ensures the container stays at 102x102.
        """
        if pixmap.isNull():
            self.artwork_label.clear()
            return
        
        # Scale to fit WITHIN 102x102 while maintaining aspect ratio
        # This ensures the entire image is visible
        scaled = pixmap.scaled(
            102, 102,
            Qt.KeepAspectRatio,           # Preserve aspect ratio
            Qt.SmoothTransformation        # High quality scaling
        )
        
        # Create a new pixmap with the scaled image
        self.artwork_label.setPixmap(scaled)
        
    def _update_active_time(self):
        """Update the active time counter for header."""
        if not self._active_start_time or not self._current_media_active:
            return
        
        elapsed = datetime.now() - self._active_start_time
        minutes = int(elapsed.total_seconds() // 60)
        
        if minutes < 60:
            time_str = f"Active · {minutes}m"
        else:
            hours = minutes // 60
            mins = minutes % 60
            time_str = f"Active · {hours}h {mins}m"
        
        self.active_time_changed.emit(time_str)
    
    def _update_session_time(self):
        """Update session time based on current hour."""
        current_hour = datetime.now().hour
        
        if 5 <= current_hour < 12:
            session = "Morning Session"
        elif 12 <= current_hour < 17:
            session = "Afternoon Session"
        elif 17 <= current_hour < 21:
            session = "Evening Session"
        else:
            session = "Night Session"
        
        self.session_label.setText(session)
    
    def _update_current_task(self):
        """Update current task and trigger style refresh."""
        task = self._detect_current_task()
        self.task_label.setText(task)
        
        # Set property for QSS styling
        if task == "Designing":
            self.task_label.setProperty("task", "designing")
        elif task == "Printing":
            self.task_label.setProperty("task", "printing")
        else:
            self.task_label.setProperty("task", "standing")
        
        # Force style refresh
        self.task_label.style().unpolish(self.task_label)
        self.task_label.style().polish(self.task_label)
    
    def _detect_current_task(self) -> str:
        """
        Detect current task:
        - Photoshop/Illustrator open → "Designing"
        - Print in last 5 minutes → "Printing"
        - Otherwise → "Standing By"
        """

        adobe_apps = ["photoshop.exe", "illustrator.exe"]
        
        try:
            for proc in psutil.process_iter(['name']):
                proc_name = proc.info['name'].lower() if proc.info['name'] else ""
                if any(app in proc_name for app in adobe_apps):
                    return "Designing"
        except Exception:
            pass
        
        # Check for recent prints
        if self._print_log_state:
            try:
                jobs = getattr(self._print_log_state, "jobs", [])
                if jobs:
                    latest = jobs[-1]
                    if hasattr(latest, 'timestamp') and latest.timestamp:
                        now = datetime.now()
                        if hasattr(latest.timestamp, 'tzinfo') and latest.timestamp.tzinfo:
                            if (now.astimezone() - latest.timestamp).total_seconds() < 300:
                                return "Printing"
                        else:
                            from datetime import timezone
                            if (now.astimezone(timezone.utc) - latest.timestamp.replace(tzinfo=timezone.utc)).total_seconds() < 300:
                                return "Printing"
            except Exception:
                pass
        
        return "Standing By"