# studiohub/ui/widgets/exclusion_manager.py

from __future__ import annotations

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from studiohub.constants import PRINT_SIZES, PRINT_SIZES_DISPLAY
from studiohub.style.typography.rules import apply_typography
from studiohub.ui.layout.row_layout import configure_view, RowProfile


class ExclusionManager(QtWidgets.QWidget):
    """Widget for managing poster size exclusions with table headers."""
    
    changed = Signal()  # Emitted when exclusions change
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self._config = config_manager
        self._source = "archive"
        self._poster_widgets = []
        self._current_filter = ""
        
        self._build_ui()
        self._load_data()
    
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Source toggle row
        source_row = QtWidgets.QHBoxLayout()
        
        self.btn_archive = QtWidgets.QPushButton("Archive")
        self.btn_studio = QtWidgets.QPushButton("Studio")
        
        for btn in (self.btn_archive, self.btn_studio):
            btn.setCheckable(True)
            btn.setObjectName("SourceToggle")
            btn.setMinimumWidth(100)
            apply_typography(btn, "body")
        
        self.btn_archive.setChecked(True)
        self.btn_archive.clicked.connect(lambda: self._set_source("archive"))
        self.btn_studio.clicked.connect(lambda: self._set_source("studio"))
        
        source_row.addWidget(self.btn_archive)
        source_row.addWidget(self.btn_studio)
        source_row.addStretch()
        
        layout.addLayout(source_row)
        
        # =====================================================
        # TABLE VIEW WITH HEADERS
        # =====================================================
        
        # Create a scroll area for the table
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Container for the table
        self.table_container = QtWidgets.QWidget()
        self.table_layout = QtWidgets.QVBoxLayout(self.table_container)
        self.table_layout.setContentsMargins(0, 0, 0, 0)
        self.table_layout.setSpacing(0)
        
        # Create the header row
        self.header_widget = self._create_header_row()
        self.table_layout.addWidget(self.header_widget)
        
        # Add a separator line below header
        header_sep = QtWidgets.QFrame()
        header_sep.setFrameShape(QtWidgets.QFrame.HLine)
        header_sep.setFixedHeight(1)
        header_sep.setProperty("role", "section-divider")
        self.table_layout.addWidget(header_sep)
        
        # Container for poster rows
        self.rows_container = QtWidgets.QWidget()
        self.rows_layout = QtWidgets.QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(1)  # 1px gap between rows
        
        self.table_layout.addWidget(self.rows_container)
        self.table_layout.addStretch()
        
        self.scroll.setWidget(self.table_container)
        layout.addWidget(self.scroll)
        
        
        # Save button
        self.btn_save = QtWidgets.QPushButton("Save Exclusions")
        self.btn_save.setObjectName("SegmentedButton")
        self.btn_save.clicked.connect(self._save)
        apply_typography(self.btn_save, "body")
        layout.addWidget(self.btn_save)
    
    def _create_header_row(self) -> QtWidgets.QWidget:
        """Create the header row with size columns."""
        header = QtWidgets.QWidget()
        header.setObjectName("ExclusionHeader")
        header.setProperty("role", "table-header")
        
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Poster column
        poster_header = QtWidgets.QLabel("Poster")
        poster_header.setProperty("role", "field-label")
        apply_typography(poster_header, "body-strong")
        poster_header.setMinimumWidth(200)
        layout.addWidget(poster_header)
        
        # Add stretch after poster to push size headers to the right
        layout.addStretch()
        
        # Size headers
        for size in PRINT_SIZES:
            size_label = QtWidgets.QLabel(PRINT_SIZES_DISPLAY[size])
            size_label.setAlignment(Qt.AlignCenter)
            size_label.setMinimumWidth(70)
            apply_typography(size_label, "body-strong")
            layout.addWidget(size_label)
        
        return header
    
    def _create_poster_row(self, poster_key: str, display_name: str, excluded_sizes: list) -> QtWidgets.QWidget:
        """Create a row for a single poster."""
        row = QtWidgets.QWidget()
        row.setObjectName("ExclusionRow")
        row.setProperty("poster_key", poster_key)
        
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Poster name
        name_label = QtWidgets.QLabel(display_name)
        name_label.setMinimumWidth(200)
        apply_typography(name_label, "body")
        layout.addWidget(name_label)
        
        # Add stretch after name
        layout.addStretch()
        
        # Size checkboxes - use a container widget for each checkbox to center it
        checkboxes = {}
        for size in PRINT_SIZES:
            # Create a container widget to center the checkbox
            container = QtWidgets.QWidget()
            container.setFixedWidth(70)
            container_layout = QtWidgets.QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setAlignment(Qt.AlignCenter)
            
            cb = QtWidgets.QCheckBox()
            cb.setChecked(size in excluded_sizes)
            cb.setProperty("size", size)
            cb.setProperty("poster_key", poster_key)
            
            # Connect to mark changed
            cb.toggled.connect(self._on_exclusion_toggled)
            
            # Add checkbox to container and center it
            container_layout.addWidget(cb)
            
            checkboxes[size] = cb
            layout.addWidget(container)
        
        # Store checkboxes on the row widget for easy access
        row.checkboxes = checkboxes
        row.poster_key = poster_key
        
        return row
    
    def _on_exclusion_toggled(self, checked: bool):
        """Mark that changes have been made (enable save button state)."""
        # We could update a dirty flag here if needed
        pass
    
    def _set_source(self, source: str):
        self._source = source
        self.btn_archive.setChecked(source == "archive")
        self.btn_studio.setChecked(source == "studio")
        self._load_data()
    
    def _load_data(self):
        """Load poster list and current exclusions."""
        # Clear existing rows
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get posters from index
        try:
            from studiohub.models.poster_index import load_poster_index
            index_path = self._config.get_poster_index_path()
            data = load_poster_index(index_path)
            posters = data.get("posters", {}).get(self._source, {})
        except Exception as e:
            posters = {}
        
        if not posters:
            empty = QtWidgets.QLabel("No posters found. Run index first.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setObjectName("PanelPlaceholder")
            apply_typography(empty, "body")
            self.rows_layout.addWidget(empty)
            return
        
        # Get current exclusions
        exclusions = self._config.get("poster_exclusions", self._source, {})
        
        # Create rows for each poster
        self._poster_widgets = []
        for poster_key in sorted(posters.keys(), key=str.lower):
            meta = posters.get(poster_key, {})
            display_name = meta.get("display_name", poster_key)
            
            row = self._create_poster_row(
                poster_key,
                display_name,
                exclusions.get(poster_key, [])
            )
            self.rows_layout.addWidget(row)
            self._poster_widgets.append(row)
        
        self.rows_layout.addStretch()
    
    def _filter_posters(self, text: str):
        """Filter posters by search text."""
        text_lower = text.lower()
        for row in self._poster_widgets:
            # Get the name label (first widget in layout)
            name_label = row.layout().itemAt(0).widget()
            visible = text_lower in name_label.text().lower() or text_lower in row.poster_key.lower()
            row.setVisible(visible)
    
    def _save(self):
        """Save exclusions to config."""
        exclusions = {}
        for row in self._poster_widgets:
            if not row.isVisible():
                continue
            
            excluded_sizes = []
            for size, cb in row.checkboxes.items():
                if cb.isChecked():
                    excluded_sizes.append(size)
            
            if excluded_sizes:
                exclusions[row.poster_key] = excluded_sizes
        
        self._config.set("poster_exclusions", self._source, exclusions)
        self._config.save()
        
        self.changed.emit()
        
        # Show confirmation
        QtWidgets.QMessageBox.information(
            self,
            "Exclusions Saved",
            f"Saved {len(exclusions)} poster exclusions for {self._source}."
        )