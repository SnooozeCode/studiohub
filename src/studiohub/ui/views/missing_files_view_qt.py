# studiohub/ui/views/missing_files_view_qt.py

from __future__ import annotations

from typing import Any, Dict, Optional
import subprocess
import os
from pathlib import Path

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QIcon, QColor, QAction

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
        
        # Draw background
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        icon = index.data(Qt.DecorationRole)
        
        if icon and isinstance(icon, QtGui.QIcon):
            # Draw icon only
            opt.text = ""
            opt.icon = QtGui.QIcon()
            style = opt.widget.style()
            style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, opt.widget)
            
            rect = option.rect
            pm = icon.pixmap(QtCore.QSize(self.ICON_SIZE, self.ICON_SIZE))
            x = rect.x() + (rect.width() - self.ICON_SIZE) // 2
            y = rect.y() + (rect.height() - self.ICON_SIZE) // 2
            painter.drawPixmap(x, y, pm)
        else:
            # Draw text (for em dash)
            text = index.data(Qt.DisplayRole)
            if text:
                painter.setPen(option.palette.text().color())
                font = painter.font()
                font.setPixelSize(12)
                painter.setFont(font)
                painter.drawText(option.rect, Qt.AlignCenter, text)
            else:
                # Fall back to default
                super().paint(painter, option, index)
        
        painter.restore()


# =====================================================
# Missing Files View
# =====================================================

class MissingFilesViewQt(QtWidgets.QFrame):
    """
    Missing Files View — table-first view with native QHeaderView.
    Optimized for first-open performance.
    """

    refresh_requested = QtCore.Signal(str)
    source_changed = QtCore.Signal(str)

    def __init__(self, config_manager=None, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        # =================================================
        # ROOT IDENTITY / SURFACE
        # =================================================
        self.setObjectName("MissingFilesView")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self._active_source = "archive"

        self._config = config_manager

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
        
        # Debounce timer for index updates
        self._update_timer = QtCore.QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._delayed_refresh)
        self._pending_update = False

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

        # Use native header so alignment is correct
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

                    
        # Enable context menu
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

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
            self._source = "archive"  # Default to archive
            self._has_been_activated = True

        self._update_header_buttons()

        # Check if we have data for the current source
        if self._data.get(self._source):
            QtCore.QTimer.singleShot(0, self._render)
            QtCore.QTimer.singleShot(0, self._apply_column_widths)
        else:
            self.refresh_requested.emit(self._source)
            # Show empty state while loading
            self._show_empty_state()

        self.source_changed.emit(self._source)

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
                # Check if any poster has backgrounds
                has_backgrounds = False
                for folder, info in data.items():
                    missing = info.get("missing", {})
                    if missing.get("backgrounds"):
                        has_backgrounds = True

                        break
                
                if has_backgrounds:
                    
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

    # Handle index updates with debouncing
    def on_index_updated(self):
        """Called when index changes - debounce to prevent too many refreshes."""
        if not self._pending_update:
            self._pending_update = True
            self._update_timer.start(500)  # 500ms debounce

    def _delayed_refresh(self):
        """Actually perform the refresh after debouncing."""
        self._pending_update = False
        if self._index and self._data.get(self._source):
            self._render()
            self._apply_column_widths()

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

    def _get_excluded_sizes(self, poster_key: str) -> set:
        """Get excluded sizes for a poster from config."""
        # If we don't have a config, try to get it from the main window
        config = self._config
        if config is None:
            main_window = self.window()
            if main_window and hasattr(main_window, '_deps'):
                config = main_window._deps.config_manager
        
        if not config:
            return set()
        
        source_exclusions = config.get("poster_exclusions", self._source, {})
        excluded = source_exclusions.get(poster_key, [])
        return set(excluded)

    def _render(self) -> None:
        """Render the tree with optimizations."""
        if self._is_rendering:
            self._pending_refresh = True
            return

        current_data = self._data.get(self._source, {})
        
        self._is_rendering = True
        self._pending_refresh = False

        try:
            state = self._capture_tree_state()

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
                    self.lbl_empty.setText(f"No {self._source} posters found in index")
                    self.lbl_empty.setVisible(True)
                    self.tree.setVisible(False)
                    self.lbl_status.setVisible(False)
                    return

                ok_color = self._resolve_token_color("text_primary", fallback=QtGui.QPalette.Text)
                missing_color = self._resolve_token_color("accent", fallback=QtGui.QPalette.Highlight)
                
                ok_icon = _get_cached_icon("status_ok", ok_color)
                missing_icon = _get_cached_icon("status_missing", missing_color)

                sorted_folders = sorted(posters.keys(), key=str.lower)
                
                for folder in sorted_folders:
                    meta = posters[folder]
                    if not isinstance(meta, dict):
                        continue

                    display_name = meta.get("display_name", folder)
                    parent = QtWidgets.QTreeWidgetItem(self.tree)
                    parent.setText(0, display_name)

                    missing = current_data.get(folder, {}).get("missing", {})
                    excluded_sizes = self._get_excluded_sizes(folder)
                    
                    exists = meta.get("exists", {})
                    has_master = bool(exists.get("master", False))
                    master_ok = has_master and not missing.get("master", False)
                    parent.setIcon(1, ok_icon if master_ok else missing_icon)
                    parent.setText(1, "")
                    parent.setTextAlignment(1, Qt.AlignCenter)

                    has_web = bool(exists.get("web", False))
                    web_ok = has_web and not missing.get("web", False)
                    parent.setIcon(2, ok_icon if web_ok else missing_icon)
                    parent.setText(2, "")
                    parent.setTextAlignment(2, Qt.AlignCenter)

                    sizes_meta = meta.get("sizes", {})
                    missing_sizes = set(missing.get("sizes") or [])

                    for idx, size in enumerate(PRINT_SIZES, start=3):
                        if size in excluded_sizes:
                            parent.setText(idx, "—")  # em dash
                            parent.setIcon(idx, QtGui.QIcon())  # clear any icon
                            parent.setTextAlignment(idx, Qt.AlignCenter)
                            continue
                        
                        size_meta = sizes_meta.get(size, {})
                        
                        if self._source == "archive":
                            # Archive: check if size exists and has backgrounds
                            size_exists = size_meta.get("exists", False)
                            bgs = size_meta.get("backgrounds", {})
                            has_any_bg = any(
                                isinstance(bg_rec, dict) and bg_rec.get("exists") is True
                                for bg_rec in bgs.values()
                            )
                            ok = size_exists and has_any_bg and size not in missing_sizes
                        else:
                            # Studio: check if size exists
                            ok = size_meta.get("exists", False) and size not in missing_sizes

                        parent.setIcon(idx, ok_icon if ok else missing_icon)
                        parent.setText(idx, "")
                        parent.setTextAlignment(idx, Qt.AlignCenter)

                    # ===== ADD CHILDREN FOR BACKGROUNDS/VARIANTS =====
                    # For archive, we need to check ALL backgrounds, not just missing ones
                    # Get the size metadata to find what backgrounds exist
                    all_backgrounds = set()
                    
                    # Collect all backgrounds from all sizes
                    for size in PRINT_SIZES:
                        if size in excluded_sizes:
                            continue
                        size_meta = sizes_meta.get(size, {})
                        backgrounds = size_meta.get("backgrounds", {})
                        for bg_key, bg_rec in backgrounds.items():
                            if isinstance(bg_rec, dict) and bg_rec.get("exists", False):
                                all_backgrounds.add((bg_key, bg_rec.get("label", bg_key)))
                    
                    # Also check missing backgrounds if they exist in the missing data
                    missing_bgs = missing.get("backgrounds", {})
                    
                    # Combine all backgrounds we know about
                    backgrounds_to_show = {}
                    
                    # Add backgrounds from index
                    for bg_key, bg_label in all_backgrounds:
                        backgrounds_to_show[bg_key] = {
                            "label": bg_label,
                            "sizes": []
                        }
                    
                    # Add any missing backgrounds that might not be in the index
                    for bg_key, bg_data in missing_bgs.items():
                        if bg_key not in backgrounds_to_show:
                            backgrounds_to_show[bg_key] = {
                                "label": bg_data.get("label", bg_key),
                                "sizes": []
                            }
                    
                    # Now create child items for each background
                    if backgrounds_to_show:
                        parent.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
                        
                        # ===== CUSTOM SORT ORDER =====
                        # Define sort priority: Default first, then Light, then Alternate, then alphabetically
                        def get_sort_key(item):
                            bg_key = item[0]
                            bg_label = item[1]["label"]
                            
                            # Priority mapping
                            if bg_label == "Default" or bg_key == "Default":
                                return (0, bg_label)  # Default always first
                            elif bg_label == "Light" or bg_key == "Light":
                                return (1, bg_label)  # Light second
                            elif bg_label == "Alternate" or bg_key == "Alternate" or bg_label == "Alternative":
                                return (2, bg_label)  # Alternate third
                            elif bg_label == "Dark" or bg_key == "Dark":
                                return (3, bg_label)  # Dark fourth (if you have it)
                            else:
                                return (4, bg_label.lower())  # Everything else alphabetically
                        
                        # Sort backgrounds using custom sort key
                        sorted_backgrounds = sorted(
                            backgrounds_to_show.items(),
                            key=get_sort_key
                        )
                        
                        for bg_key, bg_info in sorted_backgrounds:
                            bg_label = bg_info["label"]
                            child = QtWidgets.QTreeWidgetItem(parent)
                            child.setText(0, bg_label)
                            
                            # Check each size for this background
                            for idx, size in enumerate(PRINT_SIZES, start=3):
                                if size in excluded_sizes:
                                    child.setIcon(idx, ok_icon)
                                    child.setText(idx, "")
                                    child.setTextAlignment(idx, Qt.AlignCenter)
                                    continue
                                
                                # Check if this background exists for this size
                                size_meta = sizes_meta.get(size, {})
                                backgrounds = size_meta.get("backgrounds", {})
                                
                                bg_exists = False
                                if bg_key in backgrounds:
                                    bg_rec = backgrounds[bg_key]
                                    if isinstance(bg_rec, dict):
                                        bg_exists = bg_rec.get("exists", False)
                                
                                # Check if it's marked as missing in the missing data
                                is_marked_missing = False
                                if bg_key in missing_bgs:
                                    missing_sizes_for_bg = set(missing_bgs[bg_key].get("sizes", []))
                                    if size in missing_sizes_for_bg:
                                        is_marked_missing = True
                                
                                # Icon is OK if it exists and NOT marked as missing
                                ok = bg_exists and not is_marked_missing
                                
                                child.setIcon(idx, ok_icon if ok else missing_icon)
                                child.setText(idx, "")
                                child.setTextAlignment(idx, Qt.AlignCenter)
                        
                        parent.setExpanded(False)

                self.lbl_empty.setVisible(False)
                self.tree.setVisible(True)
                self.lbl_status.setVisible(False)

            finally:
                self.tree.blockSignals(False)
                self.tree.setUpdatesEnabled(True)

            self._restore_tree_state(state)
            self.tree.viewport().update()

        finally:
            self._is_rendering = False

        if self._pending_refresh:
            QtCore.QTimer.singleShot(0, self._render)

    def _show_context_menu(self, position):
        """Show context menu for the selected poster."""
        # Get the item at the click position
        item = self.tree.itemAt(position)
        if not item:
            return
        
        # Get the poster key (folder name) from the item
        poster_key = None
        if item.parent() is None:
            # This is a top-level poster item
            poster_key = self._get_poster_key_from_item(item)
        else:
            # This is a child (background/variant) item
            poster_key = self._get_poster_key_from_item(item.parent())
        
        if not poster_key:
            return
        
        # Create the context menu
        menu = QMenu(self)
        
        # ===== ADD "OPEN IN FOLDER" OPTION =====
        open_action = QAction("Open in Folder", menu)
        open_action.setData(poster_key)
        open_action.triggered.connect(self._on_open_in_folder)
        menu.addAction(open_action)
        
        menu.addSeparator()  # Add separator after open action
        
        # Get current exclusions for this poster
        excluded_sizes = self._get_excluded_sizes(poster_key)
        
        # Create submenu for size exclusions
        exclude_menu = menu.addMenu("Exclude from sizes...")
        
        # Add options for each print size
        for size in PRINT_SIZES:
            action = QAction(PRINT_SIZES_DISPLAY[size], exclude_menu)
            action.setCheckable(True)
            action.setChecked(size in excluded_sizes)
            action.setData({"poster": poster_key, "size": size})
            action.triggered.connect(self._on_exclude_size_toggled)
            exclude_menu.addAction(action)
        
        # Add separator
        menu.addSeparator()
        
        # Add option to clear all exclusions for this poster
        if excluded_sizes:
            clear_action = QAction("Clear all exclusions", menu)
            clear_action.setData(poster_key)
            clear_action.triggered.connect(self._on_clear_exclusions)
            menu.addAction(clear_action)
        
        # Show the menu
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def _get_poster_key_from_item(self, item):
        """Extract the poster key (folder name) from a tree widget item."""
        # Get the display name from the item
        display_name = item.text(0)
        
        # First try to find in the index (most reliable)
        posters = self._index.get("posters", {}).get(self._source, {})
        for folder_key, meta in posters.items():
            if meta.get("display_name") == display_name:
                return folder_key
        
        # Fallback: try to find in the current data
        current_data = self._data.get(self._source, {})
        for folder_key, folder_data in current_data.items():
            # Some data structures might have display_name at the top level
            if isinstance(folder_data, dict):
                if folder_data.get("display_name") == display_name:
                    return folder_key
        
        # Last resort: try to normalize the display name to a folder key
        # Convert display name to potential folder key by lowercasing and replacing spaces with underscores
        potential_key = display_name.lower().replace(" ", "_")
        if potential_key in posters:
            return potential_key
        
        print(f"[DEBUG] Could not find poster key for display name: {display_name}")
        return display_name
    
    def _get_poster_path(self, poster_key: str) -> Optional[Path]:
        """Get the full filesystem path for a poster."""
        # If we don't have a config, try to get it from the main window
        config = self._config
        if config is None:
            # Try to get config from main window
            main_window = self.window()
            if main_window and hasattr(main_window, '_deps'):
                config = main_window._deps.config_manager
            if config is None:
                print("[DEBUG] No config available for path resolution")
                return None
        
        # Get the root paths from index or config
        posters = self._index.get("posters", {}).get(self._source, {})
        if poster_key not in posters:
            return None
        
        # Get the root path for the source
        if self._source == "archive":
            root_path = config.get("paths", "archive_root", "")
        else:
            root_path = config.get("paths", "studio_root", "")
        
        if not root_path:
            print(f"[DEBUG] No root path configured for {self._source}")
            return None
        
        # Get the folder name from index or use the key
        poster_meta = posters.get(poster_key, {})
        folder_name = poster_meta.get("folder_name", poster_key)
        
        path = Path(root_path) / folder_name
        print(f"[DEBUG] Poster path: {path}")
        return path

    def _on_open_in_folder(self):
        """Open the poster folder in file explorer."""
        action = self.sender()
        poster_key = action.data()
        
        if not poster_key:
            return
        
        # Get the full path to the poster folder
        poster_path = self._get_poster_path(poster_key)
        
        if not poster_path or not poster_path.exists():
            print(f"[DEBUG] Poster folder not found: {poster_path}")
            return
        
        # Open in file explorer based on platform
        import sys
        import subprocess
        
        try:
            if sys.platform == 'win32':
                # Windows: use explorer
                subprocess.run(['explorer', str(poster_path)])
            elif sys.platform == 'darwin':
                # macOS: use open
                subprocess.run(['open', str(poster_path)])
            else:
                # Linux: use xdg-open
                subprocess.run(['xdg-open', str(poster_path)])
        except Exception as e:
            print(f"[DEBUG] Failed to open folder: {e}")

    def _on_exclude_size_toggled(self, checked):
        """Handle toggling a size exclusion for a poster."""
        action = self.sender()
        data = action.data()
        poster_key = data["poster"]
        size = data["size"]
        
        # Get config safely
        config = self._get_config()
        if not config:
            print("[DEBUG] No config available to save exclusions")
            return
        
        # Get current exclusions from config
        exclusions = config.get("poster_exclusions", self._source, {})
        poster_exclusions = set(exclusions.get(poster_key, []))
        
        if checked:
            poster_exclusions.add(size)
        else:
            poster_exclusions.discard(size)
        
        # Update exclusions
        if poster_exclusions:
            exclusions[poster_key] = list(poster_exclusions)
        else:
            # Remove the poster from exclusions if empty
            exclusions.pop(poster_key, None)
        
        # Save to config
        config.set("poster_exclusions", self._source, exclusions)
        config.save()
        
        # Refresh the view to show updated status
        self.refresh_requested.emit(self._source)

    def _on_clear_exclusions(self):
        """Clear all exclusions for a poster."""
        action = self.sender()
        poster_key = action.data()
        
        # Get config safely
        config = self._get_config()
        if not config:
            print("[DEBUG] No config available to clear exclusions")
            return
        
        # Get current exclusions
        exclusions = config.get("poster_exclusions", self._source, {})
        
        # Remove this poster from exclusions
        if poster_key in exclusions:
            del exclusions[poster_key]
            config.set("poster_exclusions", self._source, exclusions)
            config.save()
            
            # Refresh the view
            self.refresh_requested.emit(self._source)

    def _get_config(self):
        """Get the config manager, trying multiple sources."""
        if self._config is not None:
            return self._config
        
        # Try to get from main window
        main_window = self.window()
        if main_window and hasattr(main_window, '_deps'):
            self._config = main_window._deps.config_manager
            return self._config
        
        return None
    
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