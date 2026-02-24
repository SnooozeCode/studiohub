# studiohub/ui/views/missing_files_view_qt.py

from __future__ import annotations

from typing import Any, Dict, Optional
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor

from studiohub.style.utils.repolish import repolish
from studiohub.style.typography.rules import apply_view_typography, apply_header_typography, apply_typography
from studiohub.ui.layout.row_layout import configure_view, RowProfile
from studiohub.ui.icons import render_svg
from studiohub.constants import PRINT_SIZES, PRINT_SIZES_DISPLAY

HEADER_HEIGHT = 45

# Global icon cache with size limit
_ICON_CACHE: Dict[tuple[str, str], QtGui.QIcon] = {}
_MAX_CACHE_SIZE = 200


def _get_cached_icon(icon_name: str, color: QtGui.QColor) -> QtGui.QIcon:
    """Get cached icon with size limit."""
    key = (icon_name, color.name(QtGui.QColor.HexArgb))
    
    # Check cache
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    
    # Enforce cache size limit
    if len(_ICON_CACHE) > _MAX_CACHE_SIZE:
        # Remove oldest 20% of entries
        items = list(_ICON_CACHE.items())
        for old_key, _ in items[:len(items) // 5]:
            del _ICON_CACHE[old_key]
    
    # Create new icon
    pm = render_svg(icon_name, size=16, color=color)
    icon = QtGui.QIcon(pm)
    _ICON_CACHE[key] = icon
    return icon


class CenteredIconDelegate(QtWidgets.QStyledItemDelegate):
    ICON_SIZE = 16

    def paint(self, painter, option, index):
        painter.save()

        # Draw selection/background like Qt would
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        # Prevent Qt from drawing text/icon itself
        opt.text = ""
        opt.icon = QtGui.QIcon()

        style = opt.widget.style()
        style.drawControl(
            QtWidgets.QStyle.CE_ItemViewItem,
            opt,
            painter,
            opt.widget,
        )

        icon = index.data(Qt.DecorationRole)
        if isinstance(icon, QtGui.QIcon):
            rect = option.rect
            size = QtCore.QSize(self.ICON_SIZE, self.ICON_SIZE)
            pm = icon.pixmap(size)

            x = rect.x() + (rect.width() - size.width()) // 2
            y = rect.y() + (rect.height() - size.height()) // 2
            painter.drawPixmap(x, y, pm)

        painter.restore()


# =====================================================
# Missing Files View
# =====================================================

class MissingFilesViewQt(QtWidgets.QFrame):
    """
    Missing Files View â€” table-first view with native QHeaderView.
    Optimized for first-open performance.
    """

    refresh_requested = QtCore.Signal(str)
    source_changed = QtCore.Signal(str)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        # =================================================
        # ROOT IDENTITY / SURFACE
        # =================================================
        self.setObjectName("MissingFilesView")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self._active_source = "archive"

        # =================================================
        # STATE
        # =================================================
        self._source = "archive"
        self._data: Dict[str, Any] = {
            "archive": {},
            "studio": {}
        }  # Store data for both sources
        self._index: Dict[str, Any] = {}
        self._has_been_activated = False
        self._pending_refresh = False
        self._is_rendering = False

        # =================================================
        # WIDGETS (NO LAYOUT)
        # =================================================
        self.lbl_title = QtWidgets.QLabel("Missing Files")
        self.lbl_title.setProperty("typography", "h3")

        self.btn_archive = QtWidgets.QPushButton("Archive")
        self.btn_studio = QtWidgets.QPushButton("Studio")

        apply_typography(self.btn_archive, "body")
        apply_typography(self.btn_studio, "body")
        self.btn_archive.setAttribute(Qt.WA_SetFont, True)
        self.btn_studio.setAttribute(Qt.WA_SetFont, True)

        for b in (self.btn_archive, self.btn_studio):
            b.setCheckable(True)
            b.setMinimumWidth(120)
            b.setObjectName("SourceToggle")
            b.setCursor(QtCore.Qt.PointingHandCursor)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setVisible(False)
        self.lbl_status.setContentsMargins(12, 0, 12, 0)
        self.lbl_status.setProperty("role", "status-inline")
        
        # Add empty state label
        self.lbl_empty = QtWidgets.QLabel("No missing files found")
        self.lbl_empty.setObjectName("PanelPlaceholder")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setVisible(False)
        apply_typography(self.lbl_empty, "body")

        # =================================================
        # Tree widget with deferred initialization
        # =================================================
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setProperty("role", "missing-tree")
        self.tree.setColumnCount(6)

        # âœ… Use native header so alignment is correct
        self.tree.setHeaderHidden(False)
        self.tree.setHeaderLabels(
            ["Poster", "Master", "Web", 
            PRINT_SIZES_DISPLAY["12x18"], 
            PRINT_SIZES_DISPLAY["18x24"], 
            PRINT_SIZES_DISPLAY["24x36"]]
        )

        self.tree.setRootIsDecorated(True)
        self.tree.setItemsExpandable(True)
        self.tree.setFrameShape(QtWidgets.QFrame.NoFrame)

        # Set uniform row heights for better performance
        self.tree.setUniformRowHeights(True)

        configure_view(
            self.tree,
            profile=RowProfile.STANDARD,
            role="missing-tree",
            alternating=True,
        )

        apply_view_typography(self.tree, "tree")

        # Use single delegate instance
        self._delegate = CenteredIconDelegate(self.tree)
        for col in range(1, 6):
            self.tree.setItemDelegateForColumn(col, self._delegate)

        # Configure header behavior
        header = self.tree.header()
        apply_header_typography(header, "h4")        
        header.setProperty("role", "missing-header")
        header.setSectionsClickable(False)
        header.setHighlightSections(False)
        header.setSortIndicatorShown(False)
        header.setStretchLastSection(False)

        # Try to enforce a consistent header height
        header.setMinimumHeight(HEADER_HEIGHT)
        header.setFixedHeight(HEADER_HEIGHT)

        # Header text alignment
        hi = self.tree.headerItem()
        hi.setTextAlignment(0, Qt.AlignVCenter | Qt.AlignLeft)
        for col in range(1, 6):
            hi.setTextAlignment(col, Qt.AlignCenter)

        # =================================================
        # Table surface frame
        # =================================================
        self.table_frame = QtWidgets.QFrame()
        self.table_frame.setProperty("role", "panel")
        self.table_frame.setProperty("variant", "missing-table")
        self.table_frame.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        # =================================================
        # BUILD UI (LAYOUT)
        # =================================================
        self._build_ui()

        # =================================================
        # WIRING
        # =================================================

        self.btn_archive.clicked.connect(lambda: self.set_source("archive"))
        self.btn_studio.clicked.connect(lambda: self.set_source("studio"))

        # Keep group alive
        self._source_group = QtWidgets.QButtonGroup(self)
        self._source_group.setExclusive(True)
        self._source_group.addButton(self.btn_archive)
        self._source_group.addButton(self.btn_studio)

        # =================================================
        # INIT STATE
        # =================================================
        self._update_header_buttons()
        repolish(self)

        # Defer column sizing to first show
        self._column_sizing_pending = True

    # =================================================
    # UI
    # =================================================

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -------------------------------------------------
        # View header surface
        # -------------------------------------------------
        header_frame = QtWidgets.QFrame()
        header_frame.setFixedHeight(HEADER_HEIGHT)
        header_frame.setProperty("role", "view-header")
        header_frame.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        header_lay = QtWidgets.QHBoxLayout(header_frame)
        header_lay.setContentsMargins(0, 0, 0, 0)
        header_lay.setSpacing(12)

        header_lay.addWidget(self.lbl_title)
        header_lay.addStretch(1)
        header_lay.addWidget(self.btn_archive)
        header_lay.addWidget(self.btn_studio)

        header_outer = QtWidgets.QWidget()
        header_outer_lay = QtWidgets.QVBoxLayout(header_outer)
        header_outer_lay.setContentsMargins(12, 12, 12, 12)
        header_outer_lay.setSpacing(0)
        header_outer_lay.addWidget(header_frame)

        root.addWidget(header_outer)

        # -------------------------------------------------
        # Status and empty state
        # -------------------------------------------------
        root.addWidget(self.lbl_status)
        root.addWidget(self.lbl_empty)

        # -------------------------------------------------
        # Table wrapper
        # -------------------------------------------------
        table_outer = QtWidgets.QFrame()
        table_outer.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        outer_lay = QtWidgets.QVBoxLayout(table_outer)
        outer_lay.setContentsMargins(12, 0, 12, 12)
        outer_lay.setSpacing(0)

        table_lay = QtWidgets.QVBoxLayout(self.table_frame)
        table_lay.setContentsMargins(0, 0, 0, 0)
        table_lay.setSpacing(0)

        table_lay.addWidget(self.tree, 1)

        outer_lay.addWidget(self.table_frame)
        root.addWidget(table_outer, 1)

    # =================================================
    # Resize handling / column sizing
    # =================================================

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        # Only apply column widths if we have data
        if self._data.get(self._source):
            self._apply_column_widths()

    def _apply_column_widths(self) -> None:
        """Let the header drive sizing."""
        header = self.tree.header()
        viewport_width = self.tree.viewport().width()
        
        if viewport_width <= 0:
            return

        poster_width = int(viewport_width * 0.35)
        remaining = max(0, viewport_width - poster_width)
        status_width = int(remaining / 5) if remaining > 0 else 0

        # Block signals during resize to prevent recursive calls
        header.blockSignals(True)
        try:
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
            header.resizeSection(0, poster_width)

            for col in range(1, 6):
                header.setSectionResizeMode(col, QtWidgets.QHeaderView.Fixed)
                header.resizeSection(col, status_width)
        finally:
            header.blockSignals(False)

    # =================================================
    # Public API
    # =================================================

    def on_activated(self) -> None:
        """Called when view becomes active."""
        if not self._has_been_activated:
            self._source = "archive"
            self._has_been_activated = True

        self._update_header_buttons()

        # Trigger refresh but don't block
        if self._index and self._data.get(self._source):
            # Use single-shot to defer rendering
            QtCore.QTimer.singleShot(0, self._render)
            QtCore.QTimer.singleShot(0, self._apply_column_widths)
        else:
            # Show empty state if no data
            self._show_empty_state()

        self.refresh_requested.emit(self._source)

    def current_source(self) -> str:
        return self._source

    def set_source(self, source: str) -> None:
        if source == self._source:
            return
        self._source = source
        self._update_header_buttons()
        self.source_changed.emit(source)
        
        # Show appropriate view
        if self._data.get(source):
            QtCore.QTimer.singleShot(0, self._render)
            QtCore.QTimer.singleShot(0, self._apply_column_widths)
            self.lbl_empty.setVisible(False)
            self.tree.setVisible(True)
        else:
            self._show_empty_state()
        
        self.refresh_requested.emit(source)

    def set_loading(self, source: str, text: str) -> None:
        if source != self._source:
            return
        self.lbl_status.setText(text)
        self.lbl_status.setVisible(True)
        self.lbl_empty.setVisible(False)
        self.tree.setVisible(False)

    def set_error(self, source: str, text: str) -> None:
        if source != self._source:
            return
        self.lbl_status.setText(f"Error: {text}")
        self.lbl_status.setVisible(True)
        self.lbl_empty.setVisible(False)
        self.tree.setVisible(False)

    def set_data(self, source: str, data: Dict[str, Any]) -> None:
        """Set missing data and trigger render."""
        self._data[source] = data or {}
        
        # Only update UI if this is the current source
        if source == self._source:
            self.lbl_status.setVisible(False)
            
            if data:
                self.lbl_empty.setVisible(False)
                self.tree.setVisible(True)
                # Defer render to avoid blocking
                if not self._is_rendering:
                    QtCore.QTimer.singleShot(0, self._render)
                    QtCore.QTimer.singleShot(0, self._apply_column_widths)
            else:
                self._show_empty_state()

    def set_index(self, index: Dict[str, Any]) -> None:
        """Set poster index data."""
        self._index = index or {}
        if self._data.get(self._source) and not self._is_rendering:
            QtCore.QTimer.singleShot(0, self._render)

    def _show_empty_state(self) -> None:
        """Show empty state message."""
        self.tree.clear()
        self.tree.setVisible(False)
        self.lbl_status.setVisible(False)
        
        if self._source == "archive":
            self.lbl_empty.setText("No archive posters found")
        else:
            self.lbl_empty.setText("No studio posters found")
        
        self.lbl_empty.setVisible(True)

    # =================================================
    # Rendering (optimized)
    # =================================================

    def _capture_tree_state(self) -> dict:
        """Capture expanded state + scroll position."""
        expanded = set()
        root = self.tree.invisibleRootItem()
        
        for i in range(root.childCount()):
            item = root.child(i)
            if item and item.isExpanded():
                expanded.add(item.text(0))

        scrollbar = self.tree.verticalScrollBar()
        scroll_value = scrollbar.value() if scrollbar else 0

        return {
            "expanded": expanded,
            "scroll": scroll_value,
        }

    def _restore_tree_state(self, state: dict) -> None:
        """Restore expanded state + scroll position."""
        expanded = state.get("expanded", set())
        root = self.tree.invisibleRootItem()
        
        for i in range(root.childCount()):
            item = root.child(i)
            if item and item.text(0) in expanded:
                item.setExpanded(True)

        scrollbar = self.tree.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(state.get("scroll", 0))

    def _resolve_token_color(self, token_name: str, fallback: QtGui.QPalette.ColorRole) -> QtGui.QColor:
        """Resolve token color with caching."""
        app = QtWidgets.QApplication.instance()
        tokens = app.property("theme_tokens") if app else None

        if tokens is not None:
            # Try attribute-style
            try:
                val = getattr(tokens, token_name, None)
                if isinstance(val, str) and val:
                    return QtGui.QColor(val)
            except Exception:
                pass

            # Try dict-style
            try:
                if isinstance(tokens, dict):
                    val = tokens.get(token_name)
                    if isinstance(val, str) and val:
                        return QtGui.QColor(val)
            except Exception:
                pass

        return self.palette().color(fallback)

    def _icon(self, item: QtWidgets.QTreeWidgetItem, col: int, ok: bool) -> None:
        """Set icon with caching."""
        if ok:
            color = self._resolve_token_color("text_primary", fallback=QtGui.QPalette.Text)
            icon_name = "status_ok"
        else:
            color = self._resolve_token_color("accent", fallback=QtGui.QPalette.Highlight)
            icon_name = "status_missing"

        item.setIcon(col, _get_cached_icon(icon_name, color))
        item.setText(col, "")
        item.setTextAlignment(col, Qt.AlignCenter)

    def _collect_backgrounds(self, sizes_meta: Dict[str, Any]):
        """Collect unique backgrounds with caching."""
        cache_key = str(sizes_meta)
        if hasattr(self, '_bg_cache') and cache_key in self._bg_cache:
            return self._bg_cache[cache_key]
        
        seen: Dict[str, str] = {}
        for size_data in sizes_meta.values():
            bgs = size_data.get("backgrounds") or {}
            for bg_key, bg_rec in bgs.items():
                if bg_key not in seen:
                    seen[bg_key] = bg_rec.get("label", bg_key)
        
        result = sorted(seen.items(), key=lambda x: x[0].lower())
        
        # Cache result
        if not hasattr(self, '_bg_cache'):
            self._bg_cache = {}
        self._bg_cache[cache_key] = result
        
        return result

    # studiohub/ui/views/missing_files_view_qt.py

    def _render(self) -> None:
        """Render the tree with optimizations."""
        if self._is_rendering:
            self._pending_refresh = True
            return

        # Get data for current source
        current_data = self._data.get(self._source, {})
        
        # Even if current_data is empty, we still want to render all posters
        # with checkmarks (meaning nothing is missing)

        self._is_rendering = True
        self._pending_refresh = False

        try:
            state = self._capture_tree_state()

            # Block signals and updates for faster population
            self.tree.setUpdatesEnabled(False)
            self.tree.blockSignals(True)
            
            try:
                self.tree.clear()

                posters = (
                    self._index
                    .get("posters", {})
                    .get(self._source, {})
                )
                
                if not posters:
                    # If no posters in index, show empty state
                    self.lbl_empty.setText(f"No {self._source} posters found in index")
                    self.lbl_empty.setVisible(True)
                    self.tree.setVisible(False)
                    self.lbl_status.setVisible(False)
                    return

                # Pre-calculate colors for performance
                ok_color = self._resolve_token_color("text_primary", fallback=QtGui.QPalette.Text)
                missing_color = self._resolve_token_color("accent", fallback=QtGui.QPalette.Highlight)
                
                # Pre-create frequently used icons
                ok_icon = _get_cached_icon("status_ok", ok_color)
                missing_icon = _get_cached_icon("status_missing", missing_color)

                # Sort folders once
                sorted_folders = sorted(posters.keys(), key=str.lower)
                
                items_added = False

                for folder in sorted_folders:
                    meta = posters[folder]
                    if not isinstance(meta, dict):
                        continue
                    
                    items_added = True

                    display_name = meta.get("display_name", folder)
                    parent = QtWidgets.QTreeWidgetItem(self.tree)
                    parent.setText(0, display_name)

                    # Get missing data for this poster (empty dict if none)
                    missing = current_data.get(folder, {}).get("missing", {})
                    
                    # Master status
                    exists = meta.get("exists", {})
                    has_master = bool(exists.get("master", False))
                    master_ok = has_master and not missing.get("master", False)
                    parent.setIcon(1, ok_icon if master_ok else missing_icon)
                    parent.setText(1, "")
                    parent.setTextAlignment(1, Qt.AlignCenter)

                    # Web status
                    has_web = bool(exists.get("web", False))
                    web_ok = has_web and not missing.get("web", False)
                    parent.setIcon(2, ok_icon if web_ok else missing_icon)
                    parent.setText(2, "")
                    parent.setTextAlignment(2, Qt.AlignCenter)

                    # Size statuses
                    sizes_meta = meta.get("sizes", {})
                    missing_sizes = set(missing.get("sizes") or [])

                    for idx, size in enumerate(PRINT_SIZES, start=3):
                        size_meta = sizes_meta.get(size, {})
                        
                        if self._source == "archive":
                            # Archive: check if size exists and has backgrounds
                            size_exists = size_meta.get("exists", False)
                            size_missing = size in missing_sizes
                            
                            # Also check backgrounds
                            bgs = size_meta.get("backgrounds", {})
                            has_any_bg = any(
                                isinstance(bg_rec, dict) and bg_rec.get("exists") is True
                                for bg_rec in bgs.values()
                            )
                            
                            ok = size_exists and has_any_bg and not size_missing
                        else:
                            # Studio: check if size has files
                            files = size_meta.get("files", [])
                            has_files = isinstance(files, list) and len(files) > 0
                            size_missing = size in missing_sizes
                            ok = has_files and not size_missing

                        parent.setIcon(idx, ok_icon if ok else missing_icon)
                        parent.setText(idx, "")
                        parent.setTextAlignment(idx, Qt.AlignCenter)

                    # Add children for archive source (backgrounds)
                    if self._source == "archive":
                        parent.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)

                        # Get missing backgrounds for this poster
                        missing_bgs = missing.get("backgrounds", {})
                        
                        # Collect all backgrounds from all sizes
                        all_bgs = {}
                        for size in PRINT_SIZES:
                            size_meta = sizes_meta.get(size, {})
                            bgs = size_meta.get("backgrounds", {})
                            for bg_key, bg_rec in bgs.items():
                                if bg_key not in all_bgs:
                                    all_bgs[bg_key] = bg_rec.get("label", bg_key)

                        # Sort backgrounds
                        for bg_key, bg_label in sorted(all_bgs.items(), key=lambda x: x[1].lower()):
                            child = QtWidgets.QTreeWidgetItem(parent)
                            child.setText(0, bg_label)

                            # Check which sizes this background exists in
                            missing_bg_sizes = set(missing_bgs.get(bg_key, {}).get("sizes", []))

                            for idx, size in enumerate(PRINT_SIZES, start=3):
                                size_meta = sizes_meta.get(size, {})
                                bgs = size_meta.get("backgrounds", {})
                                bg_exists = bg_key in bgs and bgs[bg_key].get("exists", False)
                                
                                ok = bg_exists and size not in missing_bg_sizes
                                
                                child.setIcon(idx, ok_icon if ok else missing_icon)
                                child.setText(idx, "")
                                child.setTextAlignment(idx, Qt.AlignCenter)

                        parent.setExpanded(False)

                # Hide empty state, show tree
                self.lbl_empty.setVisible(False)
                self.tree.setVisible(True)
                self.lbl_status.setVisible(False)

            finally:
                self.tree.blockSignals(False)
                self.tree.setUpdatesEnabled(True)

            # Restore state
            self._restore_tree_state(state)
            self.tree.viewport().update()

        finally:
            self._is_rendering = False

        # Handle any pending refreshes
        if self._pending_refresh:
            QtCore.QTimer.singleShot(0, self._render)

    # =================================================
    # Helpers
    # =================================================

    def _update_header_buttons(self) -> None:
        """Update source toggle buttons."""
        self.btn_archive.setChecked(self._source == "archive")
        self.btn_studio.setChecked(self._source == "studio")

        # Force style refresh
        self.btn_archive.style().unpolish(self.btn_archive)
        self.btn_archive.style().polish(self.btn_archive)

        self.btn_studio.style().unpolish(self.btn_studio)
        self.btn_studio.style().polish(self.btn_studio)

    def on_theme_changed(self):
        """Clear caches on theme change."""
        global _ICON_CACHE
        _ICON_CACHE.clear()
        if hasattr(self, '_bg_cache'):
            self._bg_cache.clear()
        if self._data.get(self._source):
            QtCore.QTimer.singleShot(0, self._render)