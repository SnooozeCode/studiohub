from __future__ import annotations

from typing import Optional, List

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from studiohub.constants import PRINT_SIZES, PRINT_SIZES_DISPLAY
from studiohub.ui.layout.row_layout import configure_view, RowProfile
from studiohub.ui.layout.queue import QueueRowFactory

from studiohub.style.typography.rules import apply_view_typography, apply_typography
from PySide6.QtGui import QFont

HEADER_HEIGHT = 40

# =====================================================
# Styling helpers
# =====================================================

def repolish(w: QtWidgets.QWidget) -> None:
    """Force Qt to re-evaluate stylesheet for this widget."""
    style = w.style()
    style.unpolish(w)
    style.polish(w)
    w.update()

# =====================================================
# Queue Widget (Drag + Drop aware)
# =====================================================

class QueueList(QtWidgets.QListWidget):
    items_dropped = QtCore.Signal(list)
    remove_requested = QtCore.Signal(list)  # list[str] paths

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
        # Reliable Delete / Backspace handling (QShortcut)
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
        self.setFocus(QtCore.Qt.MouseFocusReason)

        # Ensure the clicked visual row sets a real QListWidgetItem as current/selected
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item = self.itemAt(pos)
        if item is not None:
            self.setCurrentItem(item)
            if not item.isSelected():
                item.setSelected(True)

        super().mousePressEvent(event)

    def _on_delete(self):
        selected = self.selectedItems()
        if not selected:
            return

        paths_to_remove: list[str] = []
        for item in selected:
            payload = item.data(QtCore.Qt.UserRole) or []
            for p in payload:
                path = p.get("path")
                if path:
                    paths_to_remove.append(path)

        # Deduplicate while preserving order
        seen = set()
        uniq = []
        for p in paths_to_remove:
            if p not in seen:
                seen.add(p)
                uniq.append(p)

        if uniq:
            self.remove_requested.emit(uniq)

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


# =====================================================
# Print Manager View
# =====================================================

class PrintManagerViewQt(QtWidgets.QFrame):
    """
    Print Manager UI for selecting posters, managing the print queue,
    and initiating print jobs.

    Responsibilities:
        - Render available posters by source and size
        - Maintain UI state (active source, active size, active background filter)
        - Cache data provided by the hub
        - Emit intent signals (rescan, queue changes, send)

    This class does not perform filesystem scans or printing logic.
    """
    source_changed = QtCore.Signal(str)
    rescan_requested = QtCore.Signal()

    queue_add_requested = QtCore.Signal(list)
    queue_remove_requested = QtCore.Signal(list)  # list[str] paths
    queue_clear_requested = QtCore.Signal()
    send_requested = QtCore.Signal(bool)  # is_reprint
    reprint_requested = QtCore.Signal()

    BADGE_WIDTH = 100
    INDICATOR_WIDTH = 4

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        """
        Construct the Print Manager view and initialize UI state.

        Initializes:
            - Default source and size
            - Local data cache and signatures
            - UI controls, layouts, and signal wiring

        Data is not loaded here; population occurs via lifecycle hooks
        and explicit data injection.
        """
        super().__init__(parent)

        # =================================================
        # STATE
        # =================================================
        self._source = "archive"
        self._active_size = PRINT_SIZES[0]  # "12x18"
        self._avail_sig = {"archive": -1, "studio": -1}
        self._data_cache = {"archive": {}, "studio": {}}
        self._current_bg_filter: Optional[str] = None
        self._background_buttons: List[QtWidgets.QPushButton] = []
        self._background_button_group = QtWidgets.QButtonGroup(self)
        self._background_button_group.setExclusive(False)  # Allow toggling off

        # -------------------------------------------------
        # Model auto-binding (hub-side wiring safety)
        # -------------------------------------------------
        self._model_bound: bool = False
        self._model = None

        # =================================================
        # CREATE ALL WIDGETS FIRST (NO LAYOUTS YET)
        # =================================================
        
        # SOURCE TOGGLES
        self.btn_archive = QtWidgets.QPushButton("Archive")
        self.btn_studio = QtWidgets.QPushButton("Studio")
        
        # SIZE TOGGLES
        self.btn_12x18 = QtWidgets.QPushButton()
        self.btn_18x24 = QtWidgets.QPushButton()
        self.btn_24x36 = QtWidgets.QPushButton()
        
        # Set button text using constants AFTER creation
        self.btn_12x18.setText(PRINT_SIZES_DISPLAY[PRINT_SIZES[0]])  # "12×18"
        self.btn_18x24.setText(PRINT_SIZES_DISPLAY[PRINT_SIZES[1]])  # "18×24"
        self.btn_24x36.setText(PRINT_SIZES_DISPLAY[PRINT_SIZES[2]])  # "24×36"

        # Configure source buttons
        for b in (self.btn_archive, self.btn_studio):
            b.setCheckable(True)
            b.setMinimumWidth(80)
            b.setObjectName("SourceToggle")
            b.setCursor(QtCore.Qt.PointingHandCursor)
            font = b.font()
            font.setPointSize(9)
            b.setFont(font)

        # Configure size buttons
        for b in (self.btn_12x18, self.btn_18x24, self.btn_24x36):
            b.setCheckable(True)
            b.setMinimumWidth(70)
            b.setObjectName("SourceToggle")
            b.setCursor(QtCore.Qt.PointingHandCursor)
            font = b.font()
            font.setPointSize(9)
            b.setFont(font)

        self.btn_12x18.setChecked(True)

        # FILTER CONTAINER
        self.filter_container = QtWidgets.QWidget()
        self.filter_container.setVisible(False)  # Only visible for Archive
        self.filter_layout = QtWidgets.QHBoxLayout(self.filter_container)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(4)

        # QUEUE / ACTION BUTTONS
        self.btn_clear = QtWidgets.QPushButton("Clear Queue")
        self.btn_clear.setObjectName("SourceToggle")
        self.btn_clear.setProperty("danger", True)
        self.btn_clear.setCursor(QtCore.Qt.PointingHandCursor)
        
        font = self.btn_clear.font()
        font.setPointSize(9)
        self.btn_clear.setFont(font)

        self.btn_reprint = QtWidgets.QPushButton("Reprint Last Batch")
        self.btn_reprint.setObjectName("SourceToggle")
        self.btn_reprint.setEnabled(False)
        self.btn_reprint.setVisible(False)
        self.btn_reprint.setFont(font)

        self.btn_send = QtWidgets.QPushButton("Send to Photoshop")
        self.btn_send.setProperty("primary", True)
        self.btn_send.setObjectName("SourceToggle")
        self.btn_send.setFont(font)

        # DATA VIEWS
        self.available_stack = QtWidgets.QStackedWidget()
        self.tree_archive = self._build_available_tree()
        self.tree_studio = self._build_available_tree()
        self.available_stack.addWidget(self.tree_archive)
        self.available_stack.addWidget(self.tree_studio)

        self.list_queue = QueueList()
        try:
            apply_view_typography(self.list_queue, "body")
        except:
            pass

        # =================================================
        # SIGNAL WIRING (WIDGETS EXIST, LAYOUTS NOT YET)
        # =================================================
        
        self.btn_archive.clicked.connect(lambda: self._set_source("archive"))
        self.btn_studio.clicked.connect(lambda: self._set_source("studio"))

        source_group = QtWidgets.QButtonGroup(self)
        source_group.setExclusive(True)
        source_group.addButton(self.btn_archive)
        source_group.addButton(self.btn_studio)

        size_group = QtWidgets.QButtonGroup(self)
        size_group.setExclusive(True)
        size_group.addButton(self.btn_12x18)
        size_group.addButton(self.btn_18x24)
        size_group.addButton(self.btn_24x36)

        self.btn_12x18.clicked.connect(lambda: self._set_size(PRINT_SIZES[0]))
        self.btn_18x24.clicked.connect(lambda: self._set_size(PRINT_SIZES[1]))
        self.btn_24x36.clicked.connect(lambda: self._set_size(PRINT_SIZES[2]))

        self.btn_clear.clicked.connect(self.queue_clear_requested.emit)
        self.btn_send.clicked.connect(self._confirm_and_send)

        self.list_queue.items_dropped.connect(self.queue_add_requested)
        self.list_queue.remove_requested.connect(self._on_remove_paths_requested)
        self.list_queue.itemSelectionChanged.connect(
            self._sync_queue_row_selection_props
        )

        # =================================================
        # SHARED RESOURCES
        # =================================================
        
        # Shared, canonical queue row widgets (single source of truth)
        self._queue_rows = QueueRowFactory(
            badge_width=self.BADGE_WIDTH,
            indicator_width=self.INDICATOR_WIDTH,
        )

        # =================================================
        # BUILD LAYOUT (NOW ALL WIDGETS EXIST)
        # =================================================
        
        # ROOT GRID
        root = QtWidgets.QGridLayout(self)
        root.setContentsMargins(24, 12, 24, 12)
        root.setHorizontalSpacing(12)
        root.setVerticalSpacing(10)
        root.setColumnStretch(0, 6)
        root.setColumnStretch(1, 4)

        # TOP ROW - Source toggles + Filter buttons (left), Clear (right)
        top_row_left = QtWidgets.QHBoxLayout()
        top_row_left.setSpacing(8)
        top_row_left.addWidget(self.btn_archive)
        top_row_left.addWidget(self.btn_studio)
        top_row_left.addStretch(1)
        top_row_left.addWidget(self.filter_container)  # Filter buttons here, right-aligned

        top_row_right = QtWidgets.QHBoxLayout()
        top_row_right.addStretch(1)
        top_row_right.addWidget(self.btn_clear)

        root.addLayout(top_row_left, 0, 0)
        root.addLayout(top_row_right, 0, 1)

        # POSTERS TABLE
        posters_table = QtWidgets.QFrame()
        posters_table.setObjectName("TableSurface")
        posters_table.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        pt = QtWidgets.QVBoxLayout(posters_table)
        pt.setContentsMargins(0, 0, 0, 0)
        pt.setSpacing(0)
        pt.addWidget(self.available_stack, 1)

        root.addWidget(posters_table, 1, 0)

        # QUEUE TABLE
        queue_table = QtWidgets.QFrame()
        queue_table.setObjectName("TableSurface")
        queue_table.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        qt = QtWidgets.QVBoxLayout(queue_table)
        qt.setContentsMargins(0, 0, 0, 0)
        qt.setSpacing(0)
        qt.addWidget(self.list_queue, 1)

        root.addWidget(queue_table, 1, 1)

        # BOTTOM ROW - Size toggles (left) and Send (right)
        bottom_row_left = QtWidgets.QHBoxLayout()
        bottom_row_left.setSpacing(8)
        bottom_row_left.addWidget(self.btn_12x18)
        bottom_row_left.addWidget(self.btn_18x24)
        bottom_row_left.addWidget(self.btn_24x36)
        bottom_row_left.addStretch(1)

        bottom_row_right = QtWidgets.QHBoxLayout()
        bottom_row_right.addStretch(1)
        bottom_row_right.addWidget(self.btn_reprint)
        bottom_row_right.addWidget(self.btn_send)

        root.addLayout(bottom_row_left, 2, 0)
        root.addLayout(bottom_row_right, 2, 1)

        # =================================================
        # INIT STATE
        # =================================================
        self.btn_archive.setChecked(True)
        self._set_source("archive", emit=False)

        repolish(self)

    # =================================================
    # Construction helpers
    # =================================================

    def _create_filter_button(self, text: str, bg_value: str) -> QtWidgets.QPushButton:
        """Create a filter button with exact same styling as source toggles"""
        btn = QtWidgets.QPushButton(text)
        btn.setCheckable(True)
        btn.setMinimumWidth(70)
        btn.setObjectName("SourceToggle")  # Same styling as Archive/Studio
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        
        # Same font as source toggles
        font = btn.font()
        font.setPointSize(9)
        btn.setFont(font)
        
        btn.setProperty("bg_value", bg_value)
        btn.clicked.connect(lambda checked, val=bg_value: self._on_filter_button_clicked(val))
        self._background_button_group.addButton(btn)
        
        return btn

    # =================================================
    # Send Confirmation (Reprint Flag)
    # =================================================

    def _confirm_and_send(self) -> None:
        dlg = QtWidgets.QDialog(self)
        dlg.setModal(True)
        dlg.setWindowTitle("Send to Photoshop")
        dlg.setObjectName("HubDialog")
        dlg.setProperty("variant", "confirm")

        root = QtWidgets.QVBoxLayout(dlg)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        # -------------------------------------------------
        # Message
        # -------------------------------------------------
        msg = QtWidgets.QLabel("Send to Photoshop?")
        msg.setWordWrap(True)
        root.addWidget(msg)

        # -------------------------------------------------
        # Reprint master toggle
        # -------------------------------------------------
        chk_reprint = QtWidgets.QCheckBox(
            "Does this queue include reprints?"
        )
        chk_reprint.setChecked(False)
        chk_reprint.setObjectName("ReprintCheckbox")
        root.addWidget(chk_reprint)

        # -------------------------------------------------
        # Expandable reprint section
        # -------------------------------------------------
        section = QtWidgets.QFrame()
        section.setObjectName("ReprintReasonSection")
        section.setVisible(False)

        sec_layout = QtWidgets.QVBoxLayout(section)
        sec_layout.setContentsMargins(12, 6, 12, 6)
        sec_layout.setSpacing(8)

        # ---- Item checklist ----
        lbl_items = QtWidgets.QLabel("Select reprinted items")
        lbl_items.setProperty("typography", "label")
        sec_layout.addWidget(lbl_items)

        item_checks: list[QtWidgets.QCheckBox] = []

        for i in range(self.list_queue.count()):
            item = self.list_queue.item(i)
            payload = item.data(QtCore.Qt.UserRole) or []

            # Build a human-readable label
            names = [p.get("name", "Untitled") for p in payload]
            size = payload[0].get("size", "").replace("x", "×") if payload else ""
            label = " / ".join(names) + (f" — {size}" if size else "")

            cb = QtWidgets.QCheckBox(label)
            cb.setProperty("queue_payload", payload)
            item_checks.append(cb)
            sec_layout.addWidget(cb)

        # ---- Reason radios ----
        sec_layout.addSpacing(10)

        lbl_reason = QtWidgets.QLabel("Reason for reprint")
        lbl_reason.setProperty("typography", "label")
        lbl_reason.setProperty("emphasis", "strong")
        sec_layout.addWidget(lbl_reason)

        reason_group = QtWidgets.QButtonGroup(dlg)

        reasons = [
            ("banding", "Banding"),
            ("alignment", "Alignment"),
            ("color", "Color"),
            ("paper", "Paper feed / jam"),
            ("template", "Template issue"),
            ("other", "Other"),
        ]

        for key, text in reasons:
            rb = QtWidgets.QRadioButton(text)
            rb.setProperty("reason_key", key)
            reason_group.addButton(rb)
            sec_layout.addWidget(rb)

        if reason_group.buttons():
            reason_group.buttons()[0].setChecked(True)

        root.addWidget(section)

        # -------------------------------------------------
        # Toggle behavior (expand / collapse + reset)
        # -------------------------------------------------
        def _on_toggle(checked: bool):
            section.setVisible(checked)

            if not checked:
                # Reset state on collapse
                for cb in item_checks:
                    cb.setChecked(False)

                if reason_group.buttons():
                    reason_group.buttons()[0].setChecked(True)

            # Force dialog to recompute size
            dlg.adjustSize()

        chk_reprint.toggled.connect(_on_toggle)

        # -------------------------------------------------
        # Buttons
        # -------------------------------------------------
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_ok = buttons.button(QtWidgets.QDialogButtonBox.Ok)
        btn_ok.setText("Send")
        btn_ok.setDefault(True)

        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        root.addWidget(buttons)

        # -------------------------------------------------
        # Finalize
        # -------------------------------------------------
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            is_reprint = chk_reprint.isChecked()

            # For next phase (not wired yet):
            if is_reprint:
                selected_payloads = [
                    cb.property("queue_payload")
                    for cb in item_checks
                    if cb.isChecked()
                ]

                reason_btn = reason_group.checkedButton()
                reason = (
                    reason_btn.property("reason_key")
                    if reason_btn is not None
                    else None
                )

                # selected_payloads + reason ready for logging

            self.send_requested.emit(bool(is_reprint))


    def _build_available_tree(self) -> QtWidgets.QTreeWidget:
        rowProfile = RowProfile.STANDARD

        tree = QtWidgets.QTreeWidget()
        tree.setHeaderHidden(True)
        try:
            apply_view_typography(tree, "tree")
        except:
            pass

        tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tree.setDragEnabled(True)
        tree.setRootIsDecorated(True)
        tree.setItemsExpandable(True)
        tree.setExpandsOnDoubleClick(True)
        tree.setAnimated(False)

        configure_view(tree, profile=rowProfile, role="posters-tree", alternating=True)

        tree.itemDoubleClicked.connect(self._emit_add_selected)
        return tree


    def _tree_for_source(self, source: str) -> QtWidgets.QTreeWidget:
        return self.tree_archive if source == "archive" else self.tree_studio

    # =================================================
    # Background Filter Methods
    # =================================================

    def _update_background_selector(self, source: str):
        """Show/hide filter buttons and populate with unique backgrounds"""
        if source == "archive":
            # Extract unique backgrounds from archive data
            backgrounds = set()
            data = self._data_cache.get("archive", {})
            for size_items in data.values():
                for item in size_items:
                    bg_label = item.get("background_label", "")
                    if bg_label:
                        backgrounds.add(bg_label)
            
            # Clear existing buttons
            for btn in self._background_buttons:
                btn.deleteLater()
            self._background_buttons.clear()
            
            # Remove all buttons from button group
            for btn in self._background_button_group.buttons():
                self._background_button_group.removeButton(btn)
            
            # Sort backgrounds alphabetically and create buttons
            if backgrounds:
                for bg in sorted(backgrounds):
                    btn = self._create_filter_button(bg, bg)
                    self.filter_layout.addWidget(btn)
                    self._background_buttons.append(btn)
                
                # Show filter container
                self.filter_container.setVisible(True)
            else:
                self.filter_container.setVisible(False)
            
            # No filter active by default
            self._current_bg_filter = None
        else:
            self.filter_container.setVisible(False)

    def _on_filter_button_clicked(self, bg_value: str):
        """Handle filter button clicks - toggle on/off"""
        if self._source != "archive":
            return
        
        # If clicking the same button, clear filter
        if self._current_bg_filter == bg_value:
            self._current_bg_filter = None
            # Uncheck all buttons
            for btn in self._background_button_group.buttons():
                btn.setChecked(False)
        else:
            # Uncheck all buttons first
            for btn in self._background_button_group.buttons():
                btn.setChecked(False)
            # Set new filter and check the clicked button
            self._current_bg_filter = bg_value
            # Find and check the button with this bg_value
            for btn in self._background_button_group.buttons():
                if btn.property("bg_value") == bg_value:
                    btn.setChecked(True)
                    break
        
        self._refresh_current_tree()

    def _populate_tree_with_filter(self, tree: QtWidgets.QTreeWidget, data: dict, bg_filter: Optional[str] = None):
        """Populate tree with optional background filter"""
        tree.setUpdatesEnabled(False)
        tree.blockSignals(True)
        tree.setSortingEnabled(False)
        tree.clear()

        items = (data or {}).get(self._active_size, []) or []
        
        for it in items:
            # Apply background filter if set
            if bg_filter and it.get("background_label", "") != bg_filter:
                continue
            
            # When a specific filter is active, show only the poster name without background
            if bg_filter:
                full_name = it.get("name", "")
                # Remove everything after " — " if it exists
                if " — " in full_name:
                    display_name = full_name.split(" — ")[0]
                else:
                    display_name = full_name
            else:  # No filter active - show full names with backgrounds
                display_name = it.get("name", "")
                
            row = QtWidgets.QTreeWidgetItem([display_name])
            row.setData(0, QtCore.Qt.UserRole, it)
            row.setFlags(
                QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsDragEnabled
            )
            tree.addTopLevelItem(row)

        tree.blockSignals(False)
        tree.setUpdatesEnabled(True)

    # =================================================
    # Public API
    # =================================================

    def set_reprint_available(self, available: bool):
        self.btn_reprint.setVisible(available)
        self.btn_reprint.setEnabled(available)

    def _on_remove_paths_requested(self, paths: list[str]):
        self.queue_remove_requested.emit(paths)

    def current_source(self) -> str:
        return self._source

    def set_loading(self, source: str, loading: bool):
        # Intentionally no-op: Print Manager status is handled by the main status bar
        pass

    # -------------------------------------------------
    # Lifecycle
    # -------------------------------------------------

    def _auto_bind_model(self) -> None:
        """Bind to SnooozeCoHub.print_model if hub forgot to wire signals."""
        if self._model_bound:
            return

        hub = self.window()
        model = getattr(hub, "print_model", None)

        if model is None:
            return

        self._model_bound = True
        self._model = model

        try:
            model.scan_finished.connect(self._on_model_scan_finished, QtCore.Qt.QueuedConnection)
        except Exception:
            try:
                model.scan_finished.connect(self._on_model_scan_finished)
            except Exception:
                pass

        try:
            model.error.connect(self._on_model_error, QtCore.Qt.QueuedConnection)
        except Exception:
            try:
                model.error.connect(self._on_model_error)
            except Exception:
                pass

    @QtCore.Slot(str, object)
    def _on_model_scan_finished(self, source: str, data: object) -> None:
        if isinstance(data, dict):
            self.set_data(source, data)
        else:
            self.set_data(source, {})

    @QtCore.Slot(str)
    def _on_model_error(self, msg: str) -> None:
        print("[PrintManager] refresh error:", msg)

    def on_activated(self):
        self._auto_bind_model()

        if self._model:
            self._model.refresh(self._source)

        self.source_changed.emit(self.current_source())




    def _data_signature(self, data: dict) -> int:
        parts: List[str] = []
        for size in PRINT_SIZES:
            for it in (data or {}).get(size, []) or []:
                parts.append(f"{size}|{it.get('path','')}|{it.get('name','')}")
        return hash("\n".join(parts))

    def _populate_tree(self, tree: QtWidgets.QTreeWidget, data: dict):
        """Standard tree population (no filter)"""
        self._populate_tree_with_filter(tree, data, None)


    def set_data(self, source: str, data: dict):
        """
        Receive and cache available poster data for a given source.
        """
        self._data_cache[source] = data or {}

        sig = self._data_signature(data or {})
        if self._avail_sig.get(source) == sig:
            if source == self._source:
                self._refresh_current_tree()
            return

        self._avail_sig[source] = sig

        tree = self._tree_for_source(source)
        self._populate_tree(tree, self._data_cache.get(source) or {})

        if source == self._source:
            self._apply_source_to_stack(source)
            # Update background selector when data changes
            self._update_background_selector(source)

    # =================================================
    # Queue Rendering
    # =================================================

    def set_queue(self, items: List[dict]):
        self.list_queue.clear()

        used = set()
        first = True

        for i, it in enumerate(items):
            if i in used:
                continue

            # ---- 12x18 pairing (2-UP) ----
            if it.get("size") == PRINT_SIZES[0]:  # "12x18"
                pair_idx = None
                for j in range(i + 1, len(items)):
                    if j not in used and items[j].get("size") == PRINT_SIZES[0]:
                        pair_idx = j
                        break

                if pair_idx is not None:
                    used.update({i, pair_idx})
                    frame = self._build_pair_frame([it, items[pair_idx]], first)
                    li = QtWidgets.QListWidgetItem()
                    li.setData(QtCore.Qt.UserRole, [it, items[pair_idx]])
                    li.setSizeHint(frame.sizeHint())
                    self.list_queue.addItem(li)
                    self.list_queue.setItemWidget(li, frame)
                    first = False
                    continue

            # ---- Single job ----
            used.add(i)
            frame = self._build_single_frame(it, first)
            li = QtWidgets.QListWidgetItem()
            li.setData(QtCore.Qt.UserRole, [it])
            li.setSizeHint(frame.sizeHint())
            self.list_queue.addItem(li)
            self.list_queue.setItemWidget(li, frame)
            first = False

        self._sync_queue_row_selection_props()
    # =================================================
    # Frame Builders (delegated to shared module)
    # =================================================

    def _base_row_frame(self, *, variant: str) -> QtWidgets.QFrame:
        return self._queue_rows.base_row_frame(variant=variant)

    def _build_pair_frame(self, pair: List[dict], first: bool) -> QtWidgets.QFrame:
        return self._queue_rows.build_pair_frame(pair)

    def _build_single_frame(self, it: dict, first: bool) -> QtWidgets.QFrame:
        return self._queue_rows.build_single_frame(it)

    def _build_badge(self, text: str, *, variant: str) -> QtWidgets.QLabel:
        return self._queue_rows.build_badge(text, variant=variant)

    def _build_indicator(self) -> QtWidgets.QFrame:
        return self._queue_rows.build_indicator()


    # =================================================
    # Selection syncing
    # =================================================

    def _sync_queue_row_selection_props(self) -> None:
        for i in range(self.list_queue.count()):
            item = self.list_queue.item(i)
            widget = self.list_queue.itemWidget(item)
            if not widget:
                continue

            widget.setProperty("selected", bool(item.isSelected()))
            repolish(widget)

    # =================================================
    # Internals
    # =================================================

    def _apply_source_to_stack(self, source: str):
        if source == "archive":
            self.available_stack.setCurrentWidget(self.tree_archive)
        else:
            self.available_stack.setCurrentWidget(self.tree_studio)


    def _refresh_current_tree(self):
        tree = self._current_available_tree()
        data = self._data_cache.get(self._source) or {}
        
        if hasattr(self, '_current_bg_filter') and self._source == "archive" and self._current_bg_filter:
            self._populate_tree_with_filter(tree, data, self._current_bg_filter)
        else:
            self._populate_tree(tree, data)


    def _set_size(self, size: str):
        if size == self._active_size:
            return

        # Validate size
        if size not in PRINT_SIZES:
            return

        self._active_size = size
        self._refresh_current_tree()


    def _set_source(self, source: str, emit: bool = True):
        """
        Switch the active poster source (archive or studio).
        """
        if source == self._source:
            return

        self._source = source
        self.btn_archive.setChecked(source == "archive")
        self.btn_studio.setChecked(source == "studio")

        # Reset filter when switching sources
        self._current_bg_filter = None
        for btn in self._background_button_group.buttons():
            btn.setChecked(False)

        self._update_background_selector(source)
        self._apply_source_to_stack(source)

        if not self._data_cache.get(source):
            self.rescan_requested.emit()

        self._refresh_current_tree()

        if emit:
            self.source_changed.emit(source)


    def _current_available_tree(self) -> QtWidgets.QTreeWidget:
        return self._tree_for_source(self._source)
    

    def _emit_add_selected(self):
        tree = self._current_available_tree()
        items = []
        for it in tree.selectedItems():
            data = it.data(0, QtCore.Qt.UserRole)
            if data:
                items.append(data)

        if items:
            self.queue_add_requested.emit(items)

    # =================================================
    # Public: Build a queue-style row for reuse (dashboard)
    # =================================================

    def build_queue_preview_row(self, items: list[dict]) -> QtWidgets.QFrame:
        """
        Build a queue-style row frame for read-only preview usage.
        - items: list of 1 (single) or 2 (pair) item dicts
        """
        if len(items) == 2:
            frame = self._build_pair_frame(items, first=False)
        else:
            frame = self._build_single_frame(items[0], first=False)

        frame.setCursor(QtCore.Qt.PointingHandCursor)
        return frame