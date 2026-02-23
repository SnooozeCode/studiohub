# ui/views/log_viewer.py
from studiohub.utils.logging import get_logger
from PySide6 import QtWidgets, QtCore, QtGui

from studiohub.constants import UIConstants

class LogViewer(QtWidgets.QDialog):
    """Simple log viewer for debugging."""
    
    def __init__(self, appdata_root, parent=None):
        super().__init__(parent)
        self.appdata_root = appdata_root
        self.setWindowTitle("Log Viewer")
        self.setMinimumSize(UIConstants.DEFAULT_WIDTH, UIConstants.DEFAULT_HEIGHT)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Controls
        controls = QtWidgets.QHBoxLayout()
        self.file_combo = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.level_combo = QtWidgets.QComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        
        controls.addWidget(QtWidgets.QLabel("Log file:"))
        controls.addWidget(self.file_combo, 1)
        controls.addWidget(QtWidgets.QLabel("Level:"))
        controls.addWidget(self.level_combo)
        controls.addWidget(self.refresh_btn)
        
        layout.addLayout(controls)
        
        # Log display
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QtGui.QFont("Courier New", 10))
        layout.addWidget(self.log_text)
        
        # Connect signals
        self.refresh_btn.clicked.connect(self.load_logs)
        self.file_combo.currentIndexChanged.connect(self.load_logs)
        self.level_combo.currentIndexChanged.connect(self.load_logs)
        
        self.refresh_files()
    
    def refresh_files(self):
        """Refresh list of log files."""
        log_dir = self.appdata_root / "logs"
        self.file_combo.clear()
        for log_file in sorted(log_dir.glob("*.log*"), reverse=True):
            self.file_combo.addItem(log_file.name, log_file)
    
    def load_logs(self):
        """Load and display logs with filtering."""
        log_file = self.file_combo.currentData()
        if not log_file:
            return
        
        try:
            content = log_file.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            # Filter by level
            level_filter = self.level_combo.currentText()
            if level_filter != "ALL":
                # Match log level pattern
                pattern = f"| {level_filter:8s} |"
                lines = [l for l in lines if pattern in l]
            
            # Show last 1000 lines
            self.log_text.setPlainText("\n".join(lines[-1000:]))
            
        except Exception as e:
            self.log_text.setPlainText(f"Error loading log: {e}")