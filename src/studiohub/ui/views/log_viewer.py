# ui/views/log_viewer.py
from studiohub.utils.logging import get_logger
from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path

from studiohub.constants import UIConstants
from datetime import datetime
import re

class LogViewer(QtWidgets.QDialog):
    """Enhanced log viewer with session filtering."""
    
    def __init__(self, appdata_root, parent=None):
        super().__init__(parent)
        self.appdata_root = appdata_root
        self.setWindowTitle("Log Viewer")
        self.setMinimumSize(UIConstants.DEFAULT_WIDTH, UIConstants.DEFAULT_HEIGHT)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Controls
        controls = QtWidgets.QHBoxLayout()
        
        # File selector
        self.file_combo = QtWidgets.QComboBox()
        
        # View mode selector (default to Current Session)
        self.view_mode_combo = QtWidgets.QComboBox()
        self.view_mode_combo.addItems(["Current Session Only", "All Logs"])
        self.view_mode_combo.setCurrentIndex(0)
        self.view_mode_combo.currentIndexChanged.connect(self.load_logs)
        
        # Level filter
        self.level_combo = QtWidgets.QComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.setCurrentIndex(0)
        self.level_combo.currentIndexChanged.connect(self.load_logs)
        
        # Search box
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Search logs...")
        self.search_edit.textChanged.connect(self.load_logs)
        
        # Refresh button
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_logs)
        
        # Clear search button
        self.clear_search_btn = QtWidgets.QPushButton("Clear")
        self.clear_search_btn.clicked.connect(self._clear_search)
        self.clear_search_btn.setEnabled(False)
        
        # Add controls
        controls.addWidget(QtWidgets.QLabel("Log file:"))
        controls.addWidget(self.file_combo, 1)
        controls.addWidget(QtWidgets.QLabel("View:"))
        controls.addWidget(self.view_mode_combo)
        controls.addWidget(QtWidgets.QLabel("Level:"))
        controls.addWidget(self.level_combo)
        controls.addWidget(self.search_edit)
        controls.addWidget(self.clear_search_btn)
        controls.addWidget(self.refresh_btn)
        
        layout.addLayout(controls)
        
        # Stats bar
        self.stats_bar = QtWidgets.QStatusBar()
        self.stats_bar.setFixedHeight(24)
        layout.addWidget(self.stats_bar)
        
        # Log display
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QtGui.QFont("Courier New", 10))
        
        # Line wrapping off for better readability
        self.log_text.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        
        layout.addWidget(self.log_text)
        
        # Session start time tracking
        self._session_start = datetime.now()
        self._current_log_file = None
        
        # Connect file change signal
        self.file_combo.currentIndexChanged.connect(self.load_logs)
        
        # Load initial files
        self.refresh_files()
    
    def _clear_search(self):
        """Clear the search box."""
        self.search_edit.clear()
        self.clear_search_btn.setEnabled(False)
    
    def refresh_files(self):
        """Refresh list of log files."""
        log_dir = self.appdata_root / "logs"
        self.file_combo.clear()
        
        # Add log files, most recent first
        for log_file in sorted(log_dir.glob("*.log*"), reverse=True):
            if log_file.name.endswith('.zip'):
                continue
            self.file_combo.addItem(log_file.name, log_file)
        
        # Auto-select the main log file
        for i in range(self.file_combo.count()):
            if "studiohub.log" in self.file_combo.itemText(i):
                self.file_combo.setCurrentIndex(i)
                break
    
    def _get_session_start_time(self, log_file: Path) -> datetime | None:
        """
        Parse the log file to find the start time of the current session.
        Looks for the "StudioHub starting up" marker.
        """
        try:
            # Read last 100KB to find the most recent session start
            with open(log_file, 'r', encoding='utf-8') as f:
                # Seek to near the end
                f.seek(0, 2)
                file_size = f.tell()
                read_size = min(100 * 1024, file_size)  # Last 100KB
                f.seek(max(0, file_size - read_size))
                
                content = f.read()
                lines = content.splitlines()
                
                # Look for session start markers from bottom up
                for line in reversed(lines):
                    if "StudioHub starting up" in line or "Starting StudioHub" in line:
                        # Extract timestamp (format: 2026-02-23 12:34:56)
                        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if match:
                            return datetime.fromisoformat(match.group(1).replace(' ', 'T'))
        except Exception as e:
            print(f"Error parsing session start: {e}")
        
        return None
    
    def _filter_current_session(self, lines: list[str]) -> list[str]:
        """Filter lines to only show current session."""
        if not lines:
            return lines
        
        # Find the most recent session start marker
        session_start_idx = -1
        for i, line in enumerate(lines):
            if "StudioHub starting up" in line or "Starting StudioHub" in line:
                session_start_idx = i
        
        if session_start_idx >= 0:
            # Return all lines from session start to end
            return lines[session_start_idx:]
        else:
            # If no session marker found, assume last 1000 lines is current session
            return lines[-1000:]
    
    def load_logs(self):
        """Load and display logs with filtering."""
        log_file = self.file_combo.currentData()
        if not log_file:
            return
        
        try:
            content = log_file.read_text(encoding='utf-8')
            lines = content.splitlines()
            total_lines = len(lines)
            
            # Apply session filtering (default is Current Session)
            view_mode = self.view_mode_combo.currentText()
            if view_mode == "Current Session Only":
                lines = self._filter_current_session(lines)
                session_lines = len(lines)
            else:
                session_lines = total_lines
            
            # Apply level filtering
            level_filter = self.level_combo.currentText()
            if level_filter != "ALL":
                pattern = f"| {level_filter:8s} |"
                lines = [l for l in lines if pattern in l]
            
            # Apply search filtering
            search_text = self.search_edit.text().strip()
            if search_text:
                lines = [l for l in lines if search_text.lower() in l.lower()]
                self.clear_search_btn.setEnabled(True)
            else:
                self.clear_search_btn.setEnabled(False)
            
            # Show last 1000 lines (or all if less)
            display_lines = lines[-1000:] if len(lines) > 1000 else lines
            self.log_text.setPlainText("\n".join(display_lines))
            
            # Scroll to bottom (most recent logs)
            cursor = self.log_text.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()
            
            # Update stats
            self._update_stats(
                total=total_lines,
                session=session_lines,
                filtered=len(display_lines),
                shown=len(display_lines),
                view_mode=view_mode,
                level=level_filter,
                search=search_text
            )
            
        except Exception as e:
            self.log_text.setPlainText(f"Error loading log: {e}")
            self._update_stats(error=str(e))
    
    def _update_stats(self, **kwargs):
        """Update the stats bar with current information."""
        if 'error' in kwargs:
            self.stats_bar.showMessage(f"Error: {kwargs['error']}")
            return
        
        file_name = self.file_combo.currentText()
        view_mode = kwargs.get('view_mode', 'Current Session Only')
        level = kwargs.get('level', 'INFO')
        search = kwargs.get('search', '')
        
        stats = []
        stats.append(f"File: {file_name}")
        stats.append(f"View: {view_mode}")
        stats.append(f"Level: {level}")
        if search:
            stats.append(f"Search: '{search}'")
        
        if 'total' in kwargs:
            stats.append(f"Total: {kwargs['total']:,} lines")
        if 'session' in kwargs and kwargs['session'] != kwargs['total']:
            stats.append(f"Session: {kwargs['session']:,} lines")
        if 'shown' in kwargs:
            stats.append(f"Showing: {kwargs['shown']:,} lines")
        
        self.stats_bar.showMessage(" · ".join(stats))
    
    def keyPressEvent(self, event):
        """Add keyboard shortcuts for quick filtering."""
        if event.modifiers() == QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_F:
                # Ctrl+F to focus search
                self.search_edit.setFocus()
                self.search_edit.selectAll()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key_S:
                # Ctrl+S to toggle session filter
                current = self.view_mode_combo.currentIndex()
                self.view_mode_combo.setCurrentIndex(1 - current)
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key_R:
                # Ctrl+R to refresh
                self.load_logs()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key_E:
                # Ctrl+E to clear search
                self._clear_search()
                event.accept()
                return
        
        super().keyPressEvent(event)
    
    def showEvent(self, event):
        """Auto-refresh when dialog is shown."""
        super().showEvent(event)
        self.load_logs()