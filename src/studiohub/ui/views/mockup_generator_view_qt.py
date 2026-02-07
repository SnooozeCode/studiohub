from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from studiohub.style.utils.repolish import repolish
from studiohub.ui.layout.row_layout import configure_view, RowProfile
from studiohub.ui.layout.queue import QueueRowFactory
from studiohub.style.typography.rules import apply_view_typography, apply_typography
from PySide6.QtGui import QFont

from studiohub.ui.layout.row_layout import configure_view, RowProfile 


HEADER_HEIGHT = 40

# ============================================================
# Data Tokens
# ============================================================

@dataclass(frozen=True)
class PosterDTO:
    id: str
    name: str
    size: str
    source: str  # "patents" | "studio"


@dataclass(frozen=True)
class TemplateDTO:
    id: str
    name: str


@dataclass(frozen=True)
class QueueItemDTO:
    id: str
    label: str


# =====================================================
# Queue Widget (Drag + Drop aware)
# =====================================================

class QueueList(QtWidgets.QListWidget):
    items_dropped = QtCore.Signal(list)
    remove_requested = QtCore.Signal(list)  # list[dict] queue items to remove

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Ensure this widget can take focus + receive shortcut context
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        # -------------------------------------------------
        # Reliable Delete / Backspace handling
        # -------------------------------------------------
        self._delete_shortcut = QtGui.QShortcut(QtGui.QKeySequence.Delete, self)
        self._delete_shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self._delete_shortcut.activated.connect(self._on_delete)

        self._backspace_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Backspace),
            self
        )
        self._backspace_shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self._backspace_shortcut.activated.connect(self._on_delete)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        # Match Print Manager behavior: focus immediately, ensure current item is real
        self.setFocus(QtCore.Qt.MouseFocusReason)

        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item = self.itemAt(pos)
        if item is not None:
            self.setCurrentItem(item)
            if not item.isSelected() and (item.flags() & QtCore.Qt.ItemIsSelectable):
                item.setSelected(True)

        super().mousePressEvent(event)

    def _on_delete(self):
        selected = self.selectedItems()
        if not selected:
            return
        self.remove_requested.emit(selected)

    def dropEvent(self, event: QtGui.QDropEvent):
        source = event.source()

        if isinstance(source, QtWidgets.QTreeWidget):
            items = []
            for it in source.selectedItems():
                data = it.data(0, QtCore.Qt.UserRole)
                if data:
                    items.append(data)

            if items:
                self.items_dropped.emit(items)

            event.acceptProposedAction()
            return

        super().dropEvent(event)


# ============================================================
# Drawer Handle
# ============================================================

class VerticalTextButton(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setCheckable(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedWidth(22)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Expanding
        )
        self.setProperty("role", "drawer-handle")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, False)

    def sizeHint(self):
        return QtCore.QSize(self.width(), 120)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        opt = QtWidgets.QStyleOptionToolButton()
        self.initStyleOption(opt)

        painter.translate(0, self.height())
        painter.rotate(-90)
        opt.rect = QtCore.QRect(0, 0, self.height(), self.width())

        self.style().drawComplexControl(
            QtWidgets.QStyle.CC_ToolButton, opt, painter, self
        )


# ============================================================
# Mockup Generator View
# ============================================================

class MockupGeneratorViewQt(QtWidgets.QFrame):

    source_changed = QtCore.Signal(str)
    clear_queue_requested = QtCore.Signal()
    generate_requested = QtCore.Signal()

    queue_add_requested = QtCore.Signal(list)
    queue_remove_requested = QtCore.Signal(list)  # list[dict]

    BADGE_WIDTH = 100
    INDICATOR_WIDTH = 4

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._available_by_source: dict[str, list] = {
            "patents": [],
            "studio": [],
        }

        # =================================================
        # STATE
        # =================================================
        self._drawer_open = False
        self._drawer_anim: Optional[QtCore.QPropertyAnimation] = None
        self.drawer_target_width = 280

        self._current_source = "patents"
        self._posters_cache: Dict[str, Optional[dict]] = {"patents": None, "studio": None}
        self._selected_template: Optional[dict] = None

        # =================================================
        # SOURCE TOGGLES (ACTIVE STATE)
        # =================================================
        self.btn_patents = QtWidgets.QPushButton("Patents")
        self.btn_studio = QtWidgets.QPushButton("Studio")
        apply_typography(self.btn_patents, "body")
        apply_typography(self.btn_studio, "body")
        self.btn_patents.setAttribute(Qt.WA_SetFont, True)
        self.btn_studio.setAttribute(Qt.WA_SetFont, True)

        for b in (self.btn_patents, self.btn_studio):
            b.setCheckable(True)
            b.setMinimumWidth(100)
            b.setObjectName("SourceToggle")
            b.setCursor(QtCore.Qt.PointingHandCursor)

        self.btn_patents.setChecked(True)

        source_group = QtWidgets.QButtonGroup(self)
        source_group.setExclusive(True)
        source_group.addButton(self.btn_patents)
        source_group.addButton(self.btn_studio)

        self.btn_patents.clicked.connect(lambda: self._set_source("patents"))
        self.btn_studio.clicked.connect(lambda: self._set_source("studio"))

        # =================================================
        # QUEUE / ACTION BUTTONS
        # =================================================
        self.btn_clear = QtWidgets.QPushButton("Clear Queue")
        apply_typography(self.btn_clear, "body")
        self.btn_clear.setAttribute(Qt.WA_SetFont, True)
        self.btn_clear.setObjectName("SourceToggle")
        self.btn_clear.setProperty("danger", True)
        self.btn_clear.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_queue_requested.emit)

        self.btn_generate = QtWidgets.QPushButton("Send to Photoshop")
        apply_typography(self.btn_generate, "body")
        self.btn_generate.setAttribute(Qt.WA_SetFont, True)
        self.btn_generate.setProperty("primary", True)
        self.btn_generate.setObjectName("SourceToggle")
        self.btn_generate.clicked.connect(self.generate_requested.emit)

        # =================================================
        # POSTERS TREE
        # =================================================
        self.poster_list = QtWidgets.QTreeWidget()
        self.poster_list.setHeaderHidden(True)
        self.poster_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.poster_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.poster_list.setDragEnabled(True)
        self.poster_list.setRootIsDecorated(True)
        self.poster_list.setItemsExpandable(True)
        self.poster_list.setExpandsOnDoubleClick(True)
        self.poster_list.setAnimated(False)


        configure_view(
            self.poster_list,
            profile=RowProfile.STANDARD,
            role="posters-tree",
            alternating=True,
        )

        self.poster_list.itemDoubleClicked.connect(self._emit_add_selected)
        apply_view_typography(self.poster_list, "tree")
        
        # =================================================
        # DRAWER (Templates)
        # =================================================
        self.drawer_handle = VerticalTextButton()
        self.drawer_handle.setText("Mockups ⯆")
        self.drawer_handle.clicked.connect(self.toggle_drawer)

        self.drawer = QtWidgets.QFrame()
        self.drawer.setProperty("role", "panel")
        self.drawer.setProperty("square", True)
        self.drawer.setFixedWidth(0)

        self.template_list = QtWidgets.QTreeWidget()
        self.template_list.setHeaderHidden(True)
        self.template_list.setAlternatingRowColors(False)
        apply_view_typography(self.template_list, "tree")

        # Match Print Manager table behavior
        self.template_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.template_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.template_list.setRootIsDecorated(False)
        self.template_list.setItemsExpandable(False)
        self.template_list.setExpandsOnDoubleClick(False)
        self.template_list.setAnimated(False)

        configure_view(self.template_list, profile=RowProfile.STANDARD, role="plain-tree")
        self.template_list.itemSelectionChanged.connect(self._on_template_selection_changed)

        # NOTE: configure_view() historically assumed QTreeView/QTableView APIs.
        # Keep the call pattern consistent, but fail soft for QListWidget.
        try:
            configure_view(
                self.template_list,
                profile=RowProfile.STANDARD,
                role="plain-tree",
            )
        except Exception:
            pass

        dlay = QtWidgets.QVBoxLayout(self.drawer)
        dlay.setContentsMargins(12, 12, 12, 12)
        dlay.setSpacing(10)
        dlay.addWidget(self.template_list, 1)

        # =================================================
        # QUEUE LIST
        # =================================================
        self.queue_list = QueueList()
        self.queue_list.setAlternatingRowColors(False)  # ✅ REQUIRED

        # Shared, canonical queue row widgets (single source of truth)
        self._queue_rows = QueueRowFactory(
            badge_width=100,
            indicator_width=4,
        )

        apply_view_typography(self.queue_list, "body")
        self.queue_list.items_dropped.connect(self._on_queue_items_dropped)
        self.queue_list.remove_requested.connect(self._on_queue_remove_requested)
        self.queue_list.itemSelectionChanged.connect(self._sync_queue_row_selection_props)

        # NOTE: configure_view() historically assumed QTreeView/QTableView APIs.
        # Keep the call pattern consistent, but fail soft for QListWidget.
        try:
            configure_view(
                self.queue_list,
                profile=RowProfile.STANDARD,
                role="plain-list",
            )
        except Exception:
            pass

        self.lbl_summary = QtWidgets.QLabel("Posters: 0 · Mockups: 0 · Total: 0")
        self.lbl_summary.setProperty("role", "muted")
        apply_typography(self.lbl_summary, "caption")

        # =================================================
        # ROOT GRID
        # =================================================
        root = QtWidgets.QGridLayout(self)
        root.setContentsMargins(24, 12, 24, 12)
        root.setHorizontalSpacing(12)
        root.setVerticalSpacing(10)
        root.setColumnStretch(0, 6)
        root.setColumnStretch(1, 4)

        # =================================================
        # CONTROL ROW — LEFT (POSTERS)
        # =================================================
        left_controls = QtWidgets.QHBoxLayout()
        left_controls.setSpacing(8)
        left_controls.setContentsMargins(0, 10, 0, 10)

        left_controls.addWidget(self.btn_patents)
        left_controls.addWidget(self.btn_studio)
        left_controls.addStretch(1)

        root.addLayout(left_controls, 0, 0)

        # =================================================
        # CONTROL ROW — RIGHT (QUEUE)
        # =================================================
        right_controls = QtWidgets.QHBoxLayout()
        right_controls.addStretch(1)
        right_controls.addWidget(self.btn_clear)

        root.addLayout(right_controls, 0, 1)

        # =================================================
        # POSTERS TABLE (WITH DRAWER INSIDE)
        # =================================================
        posters_table = QtWidgets.QFrame()
        posters_table.setObjectName("TableSurface")
        posters_table.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        pt = QtWidgets.QHBoxLayout(posters_table)
        pt.setContentsMargins(0, 0, 0, 0)
        pt.setSpacing(0)

        pt.addWidget(self.drawer_handle)
        pt.addWidget(self.drawer)
        pt.addWidget(self.poster_list, 1)

        root.addWidget(posters_table, 1, 0)

        # =================================================
        # QUEUE TABLE
        # =================================================
        queue_table = QtWidgets.QFrame()
        queue_table.setObjectName("TableSurface")
        queue_table.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        qt = QtWidgets.QVBoxLayout(queue_table)
        qt.setContentsMargins(0, 0, 0, 0)
        qt.setSpacing(0)
        qt.addWidget(self.queue_list, 1)

        root.addWidget(queue_table, 1, 1)

        # =================================================
        # FOOTER ROW
        # =================================================
        left_footer = QtWidgets.QHBoxLayout()
        left_footer.addStretch(1)

        right_footer = QtWidgets.QHBoxLayout()
        right_footer.addStretch(1)
        right_footer.addWidget(self.btn_generate)

        root.addLayout(left_footer, 2, 0)
        root.addLayout(right_footer, 2, 1)

        # =================================================
        # INIT STATE
        # =================================================
        repolish(self)

    # =================================================
    # Construction helpers
    # =================================================

    def _build_posters_tree(self) -> QtWidgets.QTreeWidget:
        tree = QtWidgets.QTreeWidget()
        tree.setHeaderHidden(True)
        apply_view_typography(tree, "tree")

        # Semantic behavior (view-owned)
        tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tree.setDragEnabled(True)
        tree.setRootIsDecorated(True)
        tree.setItemsExpandable(True)
        tree.setExpandsOnDoubleClick(True)
        tree.setAnimated(False)
        tree.setAlternatingRowColors(True)

        # Centralized row behavior
        configure_view(tree, profile=RowProfile.STANDARD, role="posters-tree")

        tree.itemDoubleClicked.connect(self._emit_add_selected)
        return tree


    # =================================================
    # Queue row widgets (shared canonical implementation)
    # =================================================

    def _base_row_frame(self, *, variant: str) -> QtWidgets.QFrame:
        return self._queue_rows.base_row_frame(variant=variant)


    def _build_queue_poster_row_widget(self, payload: dict) -> QtWidgets.QFrame:
        # Ensure expected keys exist
        it = dict(payload or {})
        it.setdefault("name", "")
        it.setdefault("size", "")

        frame = self._queue_rows.build_single_frame(
            it,
            show_badge=False,
            show_indicator=False,
        )

        lbls = frame.findChildren(QtWidgets.QLabel)
        if lbls:
            lbl = lbls[0]

            # Typography: smaller than template header
            apply_typography(lbl, "body-small")

            # Color: text_primary via palette
            pal = lbl.palette()
            pal.setColor(
                QtGui.QPalette.WindowText,
                self.queue_list.palette().color(QtGui.QPalette.Text)
            )
            lbl.setPalette(pal)

        return frame


    def _build_queue_template_header_widget(self, template_name: str) -> QtWidgets.QFrame:
        # Header row uses the same base frame + spacing as Print Manager rows.
        frame = self._queue_rows.base_row_frame(variant="header")
        layout = frame.layout()

        lbl = QtWidgets.QLabel(template_name or "-- No Template --")
        lbl.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        lbl.setFocusPolicy(QtCore.Qt.NoFocus)

        apply_typography(lbl, "body")

        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)

        pal = lbl.palette()
        pal.setColor(
            QtGui.QPalette.WindowText,
            self.queue_list.palette().color(QtGui.QPalette.Highlight)
        )
        
        lbl.setPalette(pal)

        layout.addWidget(lbl, 1)

        # Keep right-edge alignment consistent (indicator column)
        ind = self._queue_rows.build_indicator()
        ind.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(ind)

        return frame

    def toggle_drawer(self):
        self._drawer_open = not self._drawer_open
        self.drawer_handle.setChecked(self._drawer_open)

        start = self.drawer.width()
        end = self.drawer_target_width if self._drawer_open else 0

        anim = QtCore.QPropertyAnimation(self.drawer, b"maximumWidth", self)
        anim.setDuration(160)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        anim.start()

        self._drawer_anim = anim

    # =================================================
    # Template selection
    # =================================================

    def _on_template_selection_changed(self):
        selected = self.template_list.selectedItems()
        if not selected:
            self._selected_template = None
            return

        payload = selected[0].data(0, QtCore.Qt.UserRole)
        self._selected_template = payload if isinstance(payload, dict) else None

    def _set_source(self, source: str):
        self._current_source = source
        self.source_changed.emit(source)

        # If we don't have cached posters for this source yet, load now.
        if self._model is not None:
            cached_now = self._available_by_source.get(source)
            if not cached_now:
                self._model.load_from_index(source)

        data = getattr(self, "_posters_cache", {}).get(source)
        if data:
            self._render_posters(data)

    def set_available(self, source: str, available: list[dict]) -> None:
        self._available_by_source[source] = available or []

        if source == self._current_source:
            self._render_available(available)

    # =================================================
    # Model binding
    # =================================================

    def _current_template_label(self) -> str:
        if self._selected_template and isinstance(self._selected_template, dict):
            return self._selected_template.get("name", "-- No Template --")
        return "-- No Template --"

    def bind_model(self, model):
        self._model = model
        self._posters_cache = {"patents": None, "studio": None}
        self._current_source = "patents"

        model.posters_ready.connect(self.set_posters)
        model.templates_ready.connect(self.set_templates)

        model.load_from_index("patents")
        model.load_templates()

    def set_posters(self, source: str, data: dict):
        self._posters_cache[source] = data
        if source == self._current_source:
            self._render_posters(data)

    def set_templates(self, items: list):
        self._render_templates(items)

    # =================================================
    # Lifecycle
    # =================================================

    def on_activated(self):
        # Push cached posters for the active source, if available
        data = self._posters_cache.get(self._current_source)
        if data:
            self._render_posters(data)

        # If nothing cached yet (fresh boot), trigger a load for this source.
        if not data and self._model is not None:
            self._model.load_from_index(self._current_source)

        # Push queue if the model already has one
        if hasattr(self, "_model"):
            queue = self._model.get_queue()
            if queue is not None:
                self.set_queue(queue)

    # =================================================
    # Queue input (double click / drag-drop)
    # =================================================

    def _emit_add_selected(self):
        posters = []
        for it in self.poster_list.selectedItems():
            data = it.data(0, QtCore.Qt.UserRole)
            if data:
                posters.append(data)

        if posters:
            self._emit_queue_add(posters)

    def _on_queue_items_dropped(self, posters: list):
        if posters:
            self._emit_queue_add(posters)

    def _emit_queue_add(self, posters: list):
        template = self._selected_template
        if not template:
            QtWidgets.QMessageBox.warning(
                self,
                "No Template Selected",
                "Please select a mockup template before adding posters to the queue."
            )
            return

        template_label = template.get("name")

        out = []
        for p in posters:
            if not isinstance(p, dict):
                continue
            out.append({**p, "template": template_label})

        if out:
            self.queue_add_requested.emit(out)

    # =================================================
    # Rendering
    # =================================================

    def _render_posters(self, data: dict):
        self.poster_list.setUpdatesEnabled(False)
        self.poster_list.clear()

        # Mockups use ONLY 12x18
        items = (data or {}).get("12x18") or []

        for it in items:
            display_name = it.get("name", "")

            row = QtWidgets.QTreeWidgetItem([display_name])
            row.setData(0, QtCore.Qt.UserRole, it)
            row.setFlags(
                QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsDragEnabled
            )

            self.poster_list.addTopLevelItem(row)

        self.poster_list.setUpdatesEnabled(True)

    def _render_templates(self, items: list):
        self.template_list.setUpdatesEnabled(False)
        self.template_list.clear()

        for it in items or []:
            name = (it or {}).get("name", "")
            row = QtWidgets.QTreeWidgetItem([name])
            row.setData(0, QtCore.Qt.UserRole, it)
            row.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.template_list.addTopLevelItem(row)

        self.template_list.setUpdatesEnabled(True)

    # =================================================
    # Queue rendering
    # =================================================

    def set_queue(self, items: List[dict]):
        """
        Render as:
        Template
            Poster
            Poster
        """
        self.queue_list.setUpdatesEnabled(False)
        self.queue_list.clear()

        grouped: Dict[str, List[dict]] = {}
        for it in items or []:
            tpl = it.get("template") or "-- No Template --"
            grouped.setdefault(tpl, []).append(it)

        first_group = True

        for tpl in sorted(grouped.keys(), key=lambda s: (s or "").lower()):
            posters = grouped[tpl]
            posters.sort(key=lambda p: (p.get("name") or "").lower())

            # ---- spacing between template groups ----
            if not first_group:
                spacer = QtWidgets.QListWidgetItem("")
                spacer.setFlags(QtCore.Qt.NoItemFlags)
                spacer.setData(QtCore.Qt.UserRole, None)
                spacer.setSizeHint(QtCore.QSize(0, 10))
                self.queue_list.addItem(spacer)

            first_group = False

            # ---- template header (widget row; print manager style) ----
            header_item = QtWidgets.QListWidgetItem()
            header_item.setData(QtCore.Qt.UserRole, None)  # critical for delete semantics
            header_item.setData(QtCore.Qt.UserRole + 1, "template-header")

            header_frame = self._build_queue_template_header_widget(tpl)
            header_item.setSizeHint(header_frame.sizeHint())

            header_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.queue_list.addItem(header_item)
            self.queue_list.setItemWidget(header_item, header_frame)

            # ---- posters under template (widget rows; print manager style) ----
            for p in posters:
                li = QtWidgets.QListWidgetItem()
                li.setData(QtCore.Qt.UserRole, p)
                li.setData(QtCore.Qt.UserRole + 1, "poster-row")

                frame = self._build_queue_poster_row_widget(p)
                li.setSizeHint(frame.sizeHint())

                self.queue_list.addItem(li)
                self.queue_list.setItemWidget(li, frame)

        posters_count = len(items or [])
        self.lbl_summary.setText(
            f"Posters: {posters_count} · Mockups: {posters_count} · Total: {posters_count}"
        )

        self.queue_list.setUpdatesEnabled(True)
        self._sync_queue_row_selection_props()

    # =================================================
    # Selection syncing (properties only; theme controls visuals)
    # =====================================================

    def _sync_queue_row_selection_props(self) -> None:
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            widget = self.queue_list.itemWidget(item)
            if not widget:
                continue

            widget.setProperty("selected", bool(item.isSelected()))
            repolish(widget)

    # =================================================
    # Deletion handling
    # =================================================

    def _on_queue_remove_requested(self, selected_items: list[QtWidgets.QListWidgetItem]):
        """
        Convert UI selection into concrete queue dicts, then emit queue_remove_requested(list[dict]).
        Supports:
          - poster row delete (dict payload)
          - template header delete (remove all posters under that template)
          - ignores spacers
        """
        if not selected_items:
            return

        # Snapshot current queue dicts from the list widget
        all_queue_dicts: list[dict] = []
        for i in range(self.queue_list.count()):
            li = self.queue_list.item(i)
            data = li.data(QtCore.Qt.UserRole)
            if isinstance(data, dict):
                all_queue_dicts.append(data)

        to_remove: list[dict] = []

        for item in selected_items:
            kind = item.data(QtCore.Qt.UserRole + 1)  # "poster-row" | "template-header" | None
            data = item.data(QtCore.Qt.UserRole)

            # Spacer / non-selectable rows: ignore defensively
            if item.flags() == QtCore.Qt.NoItemFlags:
                continue

            # Poster row
            if kind == "poster-row" and isinstance(data, dict):
                to_remove.append(data)
                continue

            # Template header
            if kind == "template-header":
                # For widget rows, item.text() is empty; derive from the widget label if needed.
                template_name = item.text()
                if not template_name:
                    w = self.queue_list.itemWidget(item)
                    if w is not None:
                        # Best-effort: first QLabel text
                        lbls = w.findChildren(QtWidgets.QLabel)
                        if lbls:
                            template_name = lbls[0].text()

                for d in all_queue_dicts:
                    if (d.get("template") or "-- No Template --") == template_name:
                        to_remove.append(d)
                continue

            # Fallback: if user selected something weird but it has dict payload
            if isinstance(data, dict):
                to_remove.append(data)

        # Deduplicate by (path, template) to match your previous behavior
        seen = set()
        unique: list[dict] = []
        for d in to_remove:
            key = (d.get("path"), d.get("template"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(d)

        if unique:
            self.queue_remove_requested.emit(unique)