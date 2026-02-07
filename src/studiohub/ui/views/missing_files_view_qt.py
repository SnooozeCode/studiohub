from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor

from studiohub.style.utils.repolish import repolish
from studiohub.style.typography.rules import apply_view_typography, apply_header_typography, apply_typography

from studiohub.ui.layout.row_layout import configure_view, RowProfile
from studiohub.ui.icons import render_svg


HEADER_HEIGHT = 45
SIZES = ("12x18", "18x24", "24x36")


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
    Missing Files View — table-first view with native QHeaderView.

    Key decision:
      - Use the tree's REAL header (QHeaderView) so header/body alignment is guaranteed.
      - Column sizing is driven by the header (resize modes + resizeSection).
      - Icons remain centered via delegate for status columns.
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
        self._active_source = "patents"

        # =================================================
        # STATE
        # =================================================
        self._source = "patents"
        self._data: Dict[str, Any] = {}
        self._index: Dict[str, Any] = {}
        self._icon_cache: Dict[tuple[str, str], QtGui.QIcon] = {}
        self._has_been_activated = False

        # =================================================
        # WIDGETS (NO LAYOUT)
        # =================================================
        self.lbl_title = QtWidgets.QLabel("Missing Files")
        self.lbl_title.setProperty("typography", "h3")

        self.btn_patents = QtWidgets.QPushButton("Patents")
        self.btn_studio = QtWidgets.QPushButton("Studio")

        apply_typography(self.btn_patents, "body")
        apply_typography(self.btn_studio, "body")
        self.btn_patents.setAttribute(Qt.WA_SetFont, True)
        self.btn_studio.setAttribute(Qt.WA_SetFont, True)

        for b in (self.btn_patents, self.btn_studio):
            b.setCheckable(True)
            b.setMinimumWidth(120)
            b.setObjectName("SourceToggle")
            b.setCursor(QtCore.Qt.PointingHandCursor)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setVisible(False)
        self.lbl_status.setContentsMargins(12, 0, 12, 0)
        self.lbl_status.setProperty("role", "status-inline")

        # =================================================
        # Tree widget
        # =================================================
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setProperty("role", "missing-tree")
        self.tree.setColumnCount(6)

        # ✅ Use native header so alignment is correct
        self.tree.setHeaderHidden(False)
        self.tree.setHeaderLabels(["Poster", "Master", "Web", "12×18", "18×24", "24×36"])

        self.tree.setRootIsDecorated(True)
        self.tree.setItemsExpandable(True)
        self.tree.setFrameShape(QtWidgets.QFrame.NoFrame)

        configure_view(
            self.tree,
            profile=RowProfile.STANDARD,
            role="missing-tree",
            alternating=True,
        )

        apply_view_typography(self.tree, "tree")

        delegate = CenteredIconDelegate(self.tree)
        for col in range(1, 6):
            self.tree.setItemDelegateForColumn(col, delegate)

        # Configure header behavior
        header = self.tree.header()
        apply_header_typography(header, "h4")        
        header.setProperty("role", "missing-header")  # optional QSS hook
        header.setSectionsClickable(False)
        header.setHighlightSections(False)
        header.setSortIndicatorShown(False)
        header.setStretchLastSection(False)

        # Try to enforce a consistent header height (depends on style/QSS)
        header.setMinimumHeight(HEADER_HEIGHT)
        header.setFixedHeight(HEADER_HEIGHT)

        # Header text alignment (must be set on the header item)
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

        self.btn_patents.clicked.connect(lambda: self.set_source("patents"))
        self.btn_studio.clicked.connect(lambda: self.set_source("studio"))

        # Keep group alive (prevents lifetime edge cases)
        self._source_group = QtWidgets.QButtonGroup(self)
        self._source_group.setExclusive(True)
        self._source_group.addButton(self.btn_patents)
        self._source_group.addButton(self.btn_studio)

        # =================================================
        # INIT STATE
        # =================================================
        self._update_header_buttons()
        repolish(self)

        # Ensure initial column sizing
        QtCore.QTimer.singleShot(0, self._apply_column_widths)

    # =================================================
    # UI
    # =================================================

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -------------------------------------------------
        # View header surface (title + source toggles)
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
        header_lay.addWidget(self.btn_patents)
        header_lay.addWidget(self.btn_studio)

        header_outer = QtWidgets.QWidget()
        header_outer_lay = QtWidgets.QVBoxLayout(header_outer)
        header_outer_lay.setContentsMargins(12, 12, 12, 12)
        header_outer_lay.setSpacing(0)
        header_outer_lay.addWidget(header_frame)

        root.addWidget(header_outer)

        # -------------------------------------------------
        # Status label
        # -------------------------------------------------
        root.addWidget(self.lbl_status)

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
        self._apply_column_widths()

    def _apply_column_widths(self) -> None:
        """
        Let the header drive sizing, but set the actual section widths.
        This keeps header/body perfectly aligned and avoids fake-header math.
        """
        header = self.tree.header()

        # Use viewport width so we ignore scrollbars correctly
        viewport_width = self.tree.viewport().width()
        if viewport_width <= 0:
            return

        poster_width = int(viewport_width * 0.35)
        remaining = max(0, viewport_width - poster_width)
        status_width = int(remaining / 5) if remaining > 0 else 0

        # Poster stretches (or fixed via resizeSection)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(0, poster_width)

        for col in range(1, 6):
            header.setSectionResizeMode(col, QtWidgets.QHeaderView.Fixed)
            header.resizeSection(col, status_width)

    # =================================================
    # Public API
    # =================================================

    def on_activated(self) -> None:
        # 🔑 enforce default only once
        if not self._has_been_activated:
            self._source = "patents"
            self._has_been_activated = True

        self._update_header_buttons()

        if self._index and self._data:
            self._render()
            self._apply_column_widths()

        self.refresh_requested.emit(self._source)


    def current_source(self) -> str:
        return self._source

    def set_source(self, source: str) -> None:
        if source == self._source:
            return
        self._source = source
        self._update_header_buttons()
        self.source_changed.emit(source)
        self.refresh_requested.emit(source)

    def set_loading(self, source: str, text: str) -> None:
        if source != self._source:
            return
        self.lbl_status.setText(text)
        self.lbl_status.setVisible(True)

    def set_error(self, source: str, text: str) -> None:
        if source != self._source:
            return
        self.lbl_status.setText(text)
        self.lbl_status.setVisible(True)

    def set_data(self, source: str, data: Dict[str, Any]) -> None:
        # If the hub pushes data for a different source, adopt it
        if source != self._source:
            self._source = source
            self._update_header_buttons()   # keep toggles in sync
            # don't emit signals here; this is a passive update

        self._data = data or {}
        self.lbl_status.setVisible(False)
        self._render()
        self._apply_column_widths()


    def set_index(self, index: Dict[str, Any]) -> None:
        self._index = index or {}
        if self._data:  # only re-render if we have missing payload too
            self._render()


    # =================================================
    # Rendering
    # =================================================

    def refresh(self) -> None:
            self._render()
            self._apply_column_widths()

    def _capture_tree_state(self) -> dict:
        """
        Capture expanded state + scroll position.
        """
        expanded = set()

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.isExpanded():
                expanded.add(item.text(0))  # display_name is stable

        scrollbar = self.tree.verticalScrollBar()
        scroll_value = scrollbar.value() if scrollbar else 0

        return {
            "expanded": expanded,
            "scroll": scroll_value,
        }

    def _restore_tree_state(self, state: dict) -> None:
        """
        Restore expanded state + scroll position.
        """
        expanded = state.get("expanded", set())

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.text(0) in expanded:
                item.setExpanded(True)

        scrollbar = self.tree.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(state.get("scroll", 0))


    def _render(self) -> None:

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
                return

            missing_by_folder = self._data or {}

            for folder in sorted(posters.keys(), key=str.lower):
                meta = posters[folder]
                missing = missing_by_folder.get(folder, {}).get("missing", {})

                display_name = meta.get("display_name", folder)
                parent = QtWidgets.QTreeWidgetItem(self.tree)
                parent.setText(0, display_name)

                exists = meta.get("exists", {})
                has_master = bool(exists.get("master", False))
                has_web = bool(exists.get("web", False))

                self._icon(parent, 1, has_master and not missing.get("master", False))
                self._icon(parent, 2, has_web and not missing.get("web", False))

                missing_sizes = set(missing.get("sizes") or [])

                # 👇 background-aware size logic (as fixed earlier)
                sizes_with_missing_bg = set()
                if self._source == "patents":
                    for bg_rec in (missing.get("backgrounds") or {}).values():
                        for s in bg_rec.get("sizes", []):
                            sizes_with_missing_bg.add(s)

                for idx, size in enumerate(SIZES, start=3):
                    size_exists = size in meta.get("sizes", {})
                    size_missing_output = size in missing_sizes

                    if self._source == "patents":
                        size_missing_bg = size in sizes_with_missing_bg
                        ok = size_exists and not size_missing_output and not size_missing_bg
                    else:
                        ok = size_exists and not size_missing_output

                    self._icon(parent, idx, ok)

                if self._source == "patents":
                    parent.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)

                    sizes_meta = meta.get("sizes", {})
                    bg_defs = self._collect_backgrounds(sizes_meta)

                    for bg_key, bg_label in bg_defs:
                        child = QtWidgets.QTreeWidgetItem(parent)
                        child.setText(0, bg_label)

                        missing_bg = (
                            missing
                            .get("backgrounds", {})
                            .get(bg_key, {})
                            .get("sizes", [])
                        )

                        for idx, size in enumerate(SIZES, start=3):
                            size_meta = sizes_meta.get(size, {})
                            self._icon(
                                child,
                                idx,
                                bg_key in size_meta.get("backgrounds", {})
                                and size not in missing_bg,
                            )

                parent.setExpanded(False)

        finally:
            self.tree.blockSignals(False)
            self.tree.setUpdatesEnabled(True)

            # ⬇️ RESTORE STATE LAST (after items exist)
            self._restore_tree_state(state)

            self.tree.viewport().update()



    # =================================================
    # Helpers
    # =================================================

    def _update_header_buttons(self) -> None:
        self.btn_patents.setChecked(self._source == "patents")
        self.btn_studio.setChecked(self._source == "studio")

        # 🔑 FORCE STYLE REFRESH
        self.btn_patents.style().unpolish(self.btn_patents)
        self.btn_patents.style().polish(self.btn_patents)

        self.btn_studio.style().unpolish(self.btn_studio)
        self.btn_studio.style().polish(self.btn_studio)


    def _collect_backgrounds(self, sizes_meta: Dict[str, Any]):
        seen: Dict[str, str] = {}
        for size_data in sizes_meta.values():
            bgs = size_data.get("backgrounds") or {}
            for bg_key, bg_rec in bgs.items():
                if bg_key not in seen:
                    seen[bg_key] = bg_rec.get("label", bg_key)
        return sorted(seen.items(), key=lambda x: x[0].lower())

    # -------------------------------------------------
    # Token-first coloring (safe fallback)
    # -------------------------------------------------

    def _resolve_token_color(
        self,
        token_name: str,
        *,
        fallback: QtGui.QPalette.ColorRole,
    ) -> QtGui.QColor:
        app = QtWidgets.QApplication.instance()
        tokens = app.property("theme_tokens") if app else None

        if tokens is not None:
            # attribute-style tokens
            try:
                val = getattr(tokens, token_name, None)
                if isinstance(val, str) and val:
                    return QtGui.QColor(val)
            except Exception:
                pass

            # dict-style tokens
            try:
                if isinstance(tokens, dict):
                    val = tokens.get(token_name)
                    if isinstance(val, str) and val:
                        return QtGui.QColor(val)
            except Exception:
                pass

        return self.palette().color(fallback)

    def _get_cached_icon(self, icon_name: str, color: QtGui.QColor) -> QtGui.QIcon:
        key = (icon_name, color.name(QtGui.QColor.HexArgb))
        icon = self._icon_cache.get(key)
        if icon is not None:
            return icon

        pm = render_svg(icon_name, size=16, color=color)
        icon = QtGui.QIcon(pm)
        self._icon_cache[key] = icon
        return icon


    def _icon(self, item: QtWidgets.QTreeWidgetItem, col: int, ok: bool) -> None:
        if ok:
            color = self._resolve_token_color("text_primary", fallback=QtGui.QPalette.Text)
            icon_name = "status_ok"
        else:
            color = self._resolve_token_color("accent", fallback=QtGui.QPalette.Highlight)
            icon_name = "status_missing"

        item.setIcon(col, self._get_cached_icon(icon_name, color))
        item.setText(col, "")
        item.setTextAlignment(col, Qt.AlignCenter)


    def on_theme_changed(self):
        self._icon_cache.clear()
        self._render()
