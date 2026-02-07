from __future__ import annotations

from pathlib import Path
from datetime import datetime

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator

from studiohub.services.paper_ledger import PaperLedger

from studiohub.theme.styles.typography import apply_typography
from studiohub.theme.styles.utils import repolish

from studiohub.ui.dialogs.replace_paper import ReplacePaperDialog
from studiohub.ui.icons import render_svg

# =====================================================
# Settings View
# =====================================================

class SettingsViewQt(QtWidgets.QFrame):
    """
    Settings View — single-scroll, anchored sections.

    Structural guarantees:
      - All widgets constructed before layout
      - One scroll surface
      - Role-based theming only
      - Matches PrintManagerViewQt lifecycle phases
    """

    # Emitted after the user confirms a paper roll replacement.
    # Hub uses this to refresh dashboard + other views immediately.
    paper_replaced = QtCore.Signal(dict)

    index_log_requested = QtCore.Signal()
    settings_saved = QtCore.Signal(str)

    # =================================================
    # Init
    # =================================================

    def __init__(
        self,
        *,
        config_manager,
        paper_ledger, 
        get_theme_tokens,
        parent: QtWidgets.QWidget | None = None
    ):
        super().__init__(parent)

        self.get_theme_tokens = get_theme_tokens
        self.config = config_manager
        self.paper_ledger = paper_ledger

        # =================================================
        # STATE
        # =================================================
        self._paper_reset_at: str | None = None
        self._ink_reset_at: str | None = None

        # =================================================
        # ROOT SURFACE
        # =================================================
        self.setObjectName("SettingsView")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.get_theme_tokens = get_theme_tokens
        self.tokens = self.get_theme_tokens()

        # =================================================
        # NAV BUTTONS (NO LAYOUT)
        # =================================================
        self.btn_nav_general = self._nav_button("General")
        self.btn_nav_paths = self._nav_button("Paths")
        self.btn_nav_appearance = self._nav_button("Appearance")
        self.btn_nav_printing = self._nav_button("Printing")
        self.btn_nav_operations = self._nav_button("Operations")

        nav_group = QtWidgets.QButtonGroup(self)
        nav_group.setExclusive(True)

        for b in (
            self.btn_nav_general,
            self.btn_nav_paths,
            self.btn_nav_appearance,
            self.btn_nav_printing,
            self.btn_nav_operations,
        ):
            nav_group.addButton(b)

        self.btn_nav_general.setChecked(True)


        # =================================================
        # SCROLL + CONTENT (NO LAYOUT)
        # =================================================
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setObjectName("SettingsScroll")
        self.scroll.viewport().setAttribute(QtCore.Qt.WA_StyledBackground, True)

        self.content = QtWidgets.QWidget()
        self.content.setObjectName("SettingsContent")
        self.content.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.scroll.setWidget(self.content)

        # =================================================
        # SECTIONS (BUILT, NOT PLACED)
        # =================================================
        self.section_general = self._build_section_general()
        self.section_paths = self._build_section_paths()

        # -------------------------------------------------
        # Appearance (grid-based, canonical)
        # -------------------------------------------------
        seg = self._segmented_control(["Dracula", "Alucard"])
        self.btn_theme_dracula = seg.buttons["dracula"]
        self.btn_theme_alucard = seg.buttons["alucard"]

        self.section_appearance = self._settings_grid_section(
            title="Appearance",
            description="Visual theme and presentation preferences.",
            rows=[
                {
                    "label": "Application theme",
                    "subtitle": "Controls the color scheme used throughout the app",
                    "control": seg,
                },
            ],
        )

        self.section_printing = self._build_section_printing()
        self.section_operations = self._build_section_operations()

        # =================================================
        # FOOTER BUTTONS
        # =================================================
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        apply_typography(self.btn_cancel, "body")
        self.btn_cancel.setObjectName("SourceToggle")
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.setAttribute(Qt.WA_SetFont, True)
 
        self.btn_save = QtWidgets.QPushButton("Save Changes")
        apply_typography(self.btn_save, "body")
        self.btn_save.setDefault(True)
        self.btn_save.setObjectName("SourceToggle")
        self.btn_save.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_save.setAttribute(Qt.WA_SetFont, True)

        self.btn_save.clicked.connect(self._on_save_clicked)


        # =================================================
        # ROOT LAYOUT (FIRST LAYOUT CREATED)
        # =================================================
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(50, 24, 50, 24)
        root.setSpacing(28)

        # -------------------------------------------------
        # Top navigation
        # -------------------------------------------------
        nav = QtWidgets.QHBoxLayout()
        nav.setSpacing(28)
        nav.addStretch(1)
        nav.addWidget(self.btn_nav_general)
        nav.addWidget(self.btn_nav_paths)
        nav.addWidget(self.btn_nav_appearance)
        nav.addWidget(self.btn_nav_printing)
        nav.addWidget(self.btn_nav_operations)
        nav.addStretch(1)
        root.addLayout(nav)

        root.addSpacing(16)
        root.addWidget(self.scroll, 1)

        # -------------------------------------------------
        # Fixed footer (non-scroll)
        # -------------------------------------------------
        footer = QtWidgets.QHBoxLayout()
        footer.setContentsMargins(0, 16, 0, 0)
        footer.setSpacing(12)

        footer.addStretch(1)
        footer.addWidget(self.btn_cancel)
        footer.addWidget(self.btn_save)

        root.addLayout(footer)


        # -------------------------------------------------
        # Scroll content layout
        # -------------------------------------------------
        content_lay = QtWidgets.QVBoxLayout(self.content)
        content_lay.setContentsMargins(36, 0, 36, 0)
        content_lay.setSpacing(20)

        sections = [
            self.section_general,
            self.section_paths,
            self.section_appearance,
            self.section_printing,
            self.section_operations,
        ]

        SECTION_GAP = 48

        for i, section in enumerate(sections):
            if i > 0:
                content_lay.addSpacing(SECTION_GAP // 2)
                content_lay.addWidget(self._section_divider())
                content_lay.addSpacing(SECTION_GAP // 2)

            content_lay.addWidget(section)

        content_lay.addSpacing(16)
        content_lay.addStretch(1)

        # =================================================
        # ANCHOR WIRING
        # =================================================
        self.btn_nav_general.clicked.connect(
            lambda: self.scroll.ensureWidgetVisible(self.section_general)
        )
        self.btn_nav_paths.clicked.connect(
            lambda: self.scroll.ensureWidgetVisible(self.section_paths)
        )
        self.btn_nav_appearance.clicked.connect(
            lambda: self.scroll.ensureWidgetVisible(self.section_appearance)
        )
        self.btn_nav_printing.clicked.connect(
            lambda: self.scroll.ensureWidgetVisible(self.section_printing)
        )
        self.btn_nav_operations.clicked.connect(
            lambda: self.scroll.ensureWidgetVisible(self.section_operations)
        )

        # =================================================
        # FINAL POLISH
        # =================================================
        from studiohub.theme.styles.utils import repolish
        repolish(self)
        repolish(self.scroll)
        repolish(self.content)

        # Hydrate UI from config
        self.load_from_config(self.config)

        # =================================================
        # Path widget registry (for validation / highlighting)
        # =================================================
        self._path_widgets = {
            "paths.photoshop_exe": self.row_photoshop,
            "paths.patents_root": self.row_patents,
            "paths.studio_root": self.row_studio,
            "paths.mockup_templates_root": self.row_mockup_templates,
            "paths.mockup_output_root": self.row_mockup_output,
            "paths.runtime_root": self.row_runtime_root,
            "paths.print_jobs_root": self.row_print_jobs,
            "paths.jsx_root": self.row_jsx,
        }

    # =========================================================
    # Section builders

    def _section_divider(self):
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFixedHeight(1)
        line.setProperty("role", "section-divider")
        line.setAttribute(Qt.WA_StyledBackground, True)
        return line

    # =========================================================

    def _section(self, title: str, subtitle: str | None = None):
        wrapper = QtWidgets.QFrame()
        wrapper.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        wrapper.setProperty("role", "section")

        outer = QtWidgets.QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        # ---- Header stack (title + subtitle) ----
        header = QtWidgets.QVBoxLayout()
        header.setSpacing(8)

        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setProperty("role", "section-title")
        apply_typography(lbl_title, "h3")
        lbl_title.setAttribute(Qt.WA_SetFont, True)

        header.addWidget(lbl_title)

        if subtitle:
            lbl_sub = QtWidgets.QLabel(subtitle)
            lbl_sub.setProperty("role", "muted")
            apply_typography(lbl_sub, "caption")
            lbl_sub.setAttribute(Qt.WA_SetFont, True)
            lbl_sub.setWordWrap(True)
            header.addWidget(lbl_sub)

        outer.addLayout(header)

        outer.addSpacing(16)

        # ---- Section content ----
        content = QtWidgets.QVBoxLayout()
        content.setSpacing(16)
        outer.addLayout(content)

        return wrapper, content

    # ---------------- General ----------------


    def _build_section_general(self):
        self.seg_scan_patents = self._boolean_segmented()
        self.seg_scan_patents.setObjectName("ToggleSwitch")
        self.seg_scan_studio = self._boolean_segmented()
        self.seg_scan_studio.setObjectName("ToggleSwitch")
        self.seg_rebuild_index = self._boolean_segmented()
        self.seg_rebuild_index.setObjectName("ToggleSwitch")


        for seg in (
            self.seg_scan_patents,
            self.seg_scan_studio,
            self.seg_rebuild_index,
        ):
            seg.setCursor(Qt.PointingHandCursor)
            seg.setObjectName("ToggleSwitch")

        return self._settings_grid_section(
            title="General",
            description="Startup behavior that affects scanning and indexing.",
            rows=[
                {
                    "label": "Scan patents on launch",
                    "subtitle": "Automatically scan patent artwork when the app starts",
                    "control": self.seg_scan_patents,
                },
                {
                    "label": "Scan studio on launch",
                    "subtitle": "Automatically scan studio posters when the app starts",
                    "control": self.seg_scan_studio,
                },
                {
                    "label": "Rebuild poster index on launch",
                    "subtitle": "Forces a full index rebuild instead of incremental updates",
                    "control": self.seg_rebuild_index,
                },
            ],
        )
    
    # ---------------- Paths ----------------

    def _build_section_paths(self):
        w, lay = self._section(
            "Paths",
            "Folder locations and executables used by the Hub.",
        )

        self.row_photoshop = self._path_row(
            "Photoshop Executable",
            "Path to Photoshop.exe"
        )

        self.row_patents = self._path_row(
            "Archive Folder",
            "Root folder containing restored patent artwork"
        )

        self.row_studio = self._path_row(
            "Studio Folder",
            "Root folder for Studio posters and game artwork"
        )

        self.row_mockup_templates = self._path_row(
            "Mockup Templates Folder",
            "Folder containing PSD mockup templates"
        )

        self.row_mockup_output = self._path_row(
            "Mockup Output Folder",
            "Where generated mockup images are written"
        )

        self.row_runtime_root = self._path_row(
            "Runtime Folder",
            "Shared runtime data (logs, notes, analytics, cache)"
        )

        self.row_print_jobs = self._path_row(
            "Print Jobs Folder",
            "Temporary working directory for print batches"
        )

        self.row_jsx = self._path_row(
            "JSX Scripts Folder",
            "Photoshop automation scripts used by the Hub"
        )

        for row in [
            self.row_photoshop,
            self.row_patents,
            self.row_studio,
            self.row_mockup_templates,
            self.row_mockup_output,
            self.row_runtime_root,
            self.row_print_jobs,
            self.row_jsx,
        ]:
            lay.addWidget(row)

        self.row_photoshop.browse_button.clicked.connect(self.browse_photoshop_exe)
        for row in [
            self.row_patents,
            self.row_studio,
            self.row_mockup_templates,
            self.row_mockup_output,
            self.row_runtime_root,
            self.row_print_jobs,
            self.row_jsx,
        ]:
            row.browse_button.clicked.connect(
                lambda _, r=row: self.browse_directory(r.line_edit)
            )

        return w


    def _section_row_header(self, title: str, subtitle: str):
        left = QtWidgets.QVBoxLayout()
        left.setSpacing(4)

        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setProperty("role", "section-title")
        apply_typography(lbl_title, "h3")
        lbl_title.setAttribute(Qt.WA_SetFont, True)

        lbl_sub = QtWidgets.QLabel(subtitle)
        lbl_sub.setProperty("role", "muted")
        apply_typography(lbl_sub, "caption")
        lbl_sub.setAttribute(Qt.WA_SetFont, True)
        lbl_sub.setWordWrap(True)

        left.addWidget(lbl_title)
        left.addWidget(lbl_sub)

        return left
    
    
    def _segmented_control(self, options: list[str]):
        container = QtWidgets.QWidget()
        container.setObjectName("SegmentedControl")

        lay = QtWidgets.QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        group = QtWidgets.QButtonGroup(container)
        group.setExclusive(True)
        container.button_group = group

        buttons = {}

        for i, text in enumerate(options):
            btn = QtWidgets.QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setObjectName("SegmentedButton")
            btn.setFixedHeight(42) 
            btn.setSizePolicy(
                QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.Expanding,
            )

            if i == 0:
                btn.setProperty("segment", "first")
            elif i == len(options) - 1:
                btn.setProperty("segment", "last")
            else:
                btn.setProperty("segment", "middle")

            apply_typography(btn, "body")
            btn.setAttribute(Qt.WA_SetFont, True)

            group.addButton(btn)
            lay.addWidget(btn)
            buttons[text.lower()] = btn

        container.buttons = buttons
        return container
    

    def _boolean_segmented(self):
        """
        Standard Off / On segmented control for boolean settings.
        Returns the container widget.
        """
        seg = self._segmented_control(["Off", "On"])
        seg.buttons["off"].setChecked(True)
        return seg


    # ---------------- Printing ----------------

    def _read_only_value(self, min_width: int = 160):
        lbl = QtWidgets.QLabel("—")
        lbl.setMinimumWidth(min_width)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setProperty("role", "muted")
        apply_typography(lbl, "body")
        lbl.setAttribute(Qt.WA_SetFont, True)
        return lbl
    

    def _action_button(self, text: str):
        btn = QtWidgets.QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("SegmentedButton")  # reuse button styling
        apply_typography(btn, "body")
        btn.setAttribute(Qt.WA_SetFont, True)
        return btn
    
    def _on_replace_paper_clicked(self):
        
        dlg = ReplacePaperDialog(
            self,
            current_name=self.config.get("consumables", "paper_name", ""),
            current_total_length=float(
                self.config.get("consumables", "paper_roll_start_feet", 0.0)
            ),
        )

        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return

        new_name, new_total_length = dlg.get_values()
        if not new_name or new_total_length <= 0:
            return

        # --- update config (current state) ---
        self.config.set("consumables", "paper_name", new_name)
        self.config.set("consumables", "paper_roll_start_feet", float(new_total_length))
        self.config.set("consumables", "paper_roll_waste_feet", 0.0)
        self.config.set("consumables", "paper_roll_last_replaced", datetime.utcnow().isoformat() + "Z")

        if hasattr(self.config, "save"):
            self.config.save()

        # --- canonical paper event ---
        self.paper_ledger.replace_paper(new_name, float(new_total_length))

        # --- refresh Settings UI ---
        self.lbl_paper_name.setText(new_name)
        self.lbl_paper_remaining.setText(f"{new_total_length:.1f} ft")

    def on_paper_ledger_changed(self):
        self.load_from_config(self.config)

    def _build_section_printing(self):
        # ---- Read-only paper info ----
        self.lbl_paper_name = self._read_only_value()
        self.lbl_paper_remaining = self._read_only_value()

        # ---- Replace action ----
        self.btn_replace_paper = QtWidgets.QPushButton("Replace Paper Roll")
        self.btn_replace_paper.setCursor(Qt.PointingHandCursor)
        self.btn_replace_paper.setObjectName("SegmentedButton")
        apply_typography(self.btn_replace_paper, "body")
        self.btn_replace_paper.setAttribute(Qt.WA_SetFont, True)

        self.btn_replace_paper.clicked.connect(self._on_replace_paper_clicked)

        # ---- Warning toggles ----
        self.seg_warn_paper = self._boolean_segmented()
        self.seg_warn_ink = self._boolean_segmented()

        return self._settings_grid_section(
            title="Printing",
            description="Paper status, roll changes, and print safety warnings.",
            rows=[
                {
                    "label": "Paper stock",
                    "subtitle": "Currently loaded paper type",
                    "control": self.lbl_paper_name,
                },
                {
                    "label": "Paper remaining",
                    "subtitle": "Estimated remaining length on current roll",
                    "control": self.lbl_paper_remaining,
                },
                {
                    "label": "Paper roll",
                    "subtitle": "Update paper type and reset remaining length",
                    "control": self.btn_replace_paper,
                },
                {
                    "label": "Warn when paper is running low",
                    "subtitle": "Triggers a warning when paper drops below 15 feet",
                    "control": self.seg_warn_paper,
                },
                {
                    "label": "Warn when ink is running low",
                    "subtitle": "Triggers a warning when ink drops below 25%",
                    "control": self.seg_warn_ink,
                },
            ],
        )


    # ---------------- Operations ----------------

    def _build_section_operations(self):
        self.seg_confirm_print_clear = self._boolean_segmented()
        self.seg_confirm_print_clear.setObjectName("ToggleSwitch")
        self.seg_confirm_print_send = self._boolean_segmented()
        self.seg_confirm_print_send.setObjectName("ToggleSwitch")

        for seg in (
            self.seg_confirm_print_clear,
            self.seg_confirm_print_send,
        ):
            seg.setCursor(Qt.PointingHandCursor)
            seg.setObjectName("ToggleSwitch")

        return self._settings_grid_section(
            title="Operations",
            description="Enable or disable operational safeguards.",
            rows=[
                {
                    "label": "Confirm before removing all print jobs",
                    "subtitle": None,
                    "control": self.seg_confirm_print_clear,
                },
                {
                    "label": "Confirm before sending jobs to Photoshop",
                    "subtitle": None,
                    "control": self.seg_confirm_print_send,
                },
            ],
        )


    # =========================================================
    # Helpers
    # =========================================================

    def _settings_grid_section(self, title: str, description: str, rows: list[dict]):
        wrapper = QtWidgets.QWidget()
        wrapper.setAttribute(Qt.WA_StyledBackground, True)
        wrapper.setProperty("role", "section")

        grid = QtWidgets.QGridLayout(wrapper)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(32)
        grid.setVerticalSpacing(0)

        # Columns:
        # 0 = section header
        # 1 = row labels
        # 2 = controls
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 5)
        grid.setColumnStretch(2, 2)

        # -------------------------------------------------
        # Section header (shares first row)
        # -------------------------------------------------
        header = QtWidgets.QVBoxLayout()
        header.setContentsMargins(0, 18, 0, 0)
        header.setSpacing(6)

        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setProperty("role", "section-title")
        apply_typography(lbl_title, "h3")
        lbl_title.setAttribute(Qt.WA_SetFont, True)

        lbl_desc = QtWidgets.QLabel(description)
        lbl_desc.setProperty("role", "muted")
        apply_typography(lbl_desc, "caption")
        lbl_desc.setAttribute(Qt.WA_SetFont, True)
        lbl_desc.setWordWrap(True)

        header.addWidget(lbl_title)
        header.addWidget(lbl_desc)

        # Header is placed in the SAME row as the first setting
        grid.addLayout(header, 0, 0, Qt.AlignTop)

        # -------------------------------------------------
        # Rows
        # -------------------------------------------------
        for r, row in enumerate(rows):
            row_widget = QtWidgets.QWidget()
            row_widget.setAttribute(Qt.WA_StyledBackground, True)
            row_widget.setProperty("role", "settings-row")
            row_widget.setProperty("isLast", r == len(rows) - 1)

            row_lay = QtWidgets.QGridLayout(row_widget)
            row_lay.setContentsMargins(0, 18, 0, 32)  # canonical row rhythm
            row_lay.setHorizontalSpacing(32)
            row_lay.setColumnStretch(0, 5)
            row_lay.setColumnStretch(1, 2)

            # ---- Label column ----
            qcol = QtWidgets.QVBoxLayout()
            qcol.setSpacing(4)

            lbl = QtWidgets.QLabel(row["label"])
            lbl.setProperty("role", "field-label")
            apply_typography(lbl, "body")
            lbl.setAttribute(Qt.WA_SetFont, True)
            qcol.addWidget(lbl)

            if row.get("subtitle"):
                sub = QtWidgets.QLabel(row["subtitle"])
                sub.setProperty("role", "muted")
                apply_typography(sub, "caption")
                sub.setAttribute(Qt.WA_SetFont, True)
                sub.setWordWrap(True)
                qcol.addWidget(sub)

            row_lay.addLayout(qcol, 0, 0)

            # ---- Control column ----
            row_lay.addWidget(
                row["control"],
                0,
                1,
                Qt.AlignRight | Qt.AlignVCenter,
            )

            # First row shares the header row (r = 0)
            grid.addWidget(row_widget, r, 1, 1, 2)

        return wrapper



    def _nav_button(self, text: str) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text)

        # Typography
        apply_typography(btn, "body")
        btn.setAttribute(QtCore.Qt.WA_SetFont, True)

        # Toggle behavior
        btn.setCheckable(True)
        btn.setMinimumWidth(110)
        btn.setCursor(QtCore.Qt.PointingHandCursor)

        # IMPORTANT: reuse the SAME objectName as your other toggles
        btn.setObjectName("SourceToggle")

        return btn

    def _tokens(self):
        t = self.get_theme_tokens()
        return t if hasattr(t, "__dict__") else t

    def _path_row(self, title: str, subtitle: str | None = None):
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setSpacing(24)
        layout.setContentsMargins(0, 0, 0, 0)

        # ---- Left text ----
        text_col = QtWidgets.QVBoxLayout()
        text_col.setSpacing(4)

        lbl = QtWidgets.QLabel(title)
        lbl.setProperty("role", "field-label")
        apply_typography(lbl, "body-strong")
        lbl.setAttribute(Qt.WA_SetFont, True)
        text_col.addWidget(lbl)

        if subtitle:
            sub = QtWidgets.QLabel(subtitle)
            sub.setProperty("role", "muted")
            apply_typography(sub, "caption")
            sub.setAttribute(Qt.WA_SetFont, True)
            sub.setWordWrap(True)
            text_col.addWidget(sub)

        # ---- Read-only path field ----
        line_edit = QtWidgets.QLineEdit()
        line_edit.setReadOnly(True)
        line_edit.setMinimumHeight(30)
        apply_typography(line_edit, "body")
        line_edit.setAttribute(Qt.WA_SetFont, True)

        btn = QtWidgets.QToolButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setAutoRaise(True)
        btn.setObjectName("IconButton")

        SIZE = 30
        ICON_SIZE = 16
        btn.setFixedSize(SIZE, SIZE)

        def _current_tokens():
            app = QtWidgets.QApplication.instance()
            return app.property("theme_tokens")

        def _set_icon(color: QtGui.QColor):
            btn.setIcon(
                QtGui.QIcon(
                    render_svg(
                        "edit",
                        size=ICON_SIZE,
                        color=color,
                    )
                )
            )
            btn.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))

        def _apply_muted():
            tokens = _current_tokens()
            if not tokens:
                return
            base = QtGui.QColor(tokens.text_primary)
            base.setAlphaF(0.55)
            _set_icon(base)

        def _apply_active():
            tokens = _current_tokens()
            if not tokens:
                return
            _set_icon(QtGui.QColor(tokens.text_primary))

        def _on_show():
            _apply_muted()

        btn.showEvent = lambda e: (_on_show(), QtWidgets.QToolButton.showEvent(btn, e))[1]

        btn.enterEvent = lambda e: _apply_active()
        btn.leaveEvent = lambda e: _apply_muted()

        layout.addLayout(text_col, 3)
        layout.addWidget(line_edit, 4)
        layout.addWidget(btn, 0)

        row.line_edit = line_edit
        row.browse_button = btn
        return row

    
    def showEvent(self, event):
        super().showEvent(event)
        for row in getattr(self, "_path_widgets", {}).values():
            if hasattr(row, "browse_button"):
                row.browse_button.leaveEvent(None)


    def _toggle_row(self, title: str, subtitle: str | None = None):
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)

        chk = self._boolean_segmented()
        chk.setFocusPolicy(QtCore.Qt.StrongFocus)
        apply_typography(chk, "body")
        chk.setAttribute(Qt.WA_SetFont, True)

        text_col = QtWidgets.QVBoxLayout()
        text_col.setSpacing(2)

        lbl = QtWidgets.QLabel(title)
        lbl.setProperty("role", "field-label")
        apply_typography(lbl, "body")
        lbl.setAttribute(Qt.WA_SetFont, True)

        text_col.addWidget(lbl)

        if subtitle:
            sub = QtWidgets.QLabel(subtitle)
            sub.setProperty("role", "muted")
            apply_typography(sub, "caption")
            sub.setAttribute(Qt.WA_SetFont, True)
            sub.setWordWrap(True)
            text_col.addWidget(sub)

        # Order matters: control first, then text
        row.addWidget(chk, 0)
        row.addLayout(text_col, 1)

        row.checkbox = chk
        return row

    def _theme_toggle_row(self, label: str):
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)

        btn = QtWidgets.QPushButton(label)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedWidth(80)

        # Reuse your existing toggle styling
        btn.setObjectName("SourceToggle")

        apply_typography(btn, "body")
        btn.setAttribute(Qt.WA_SetFont, True)

        row.addWidget(btn, 0)
        row.addStretch(1)

        row.button = btn
        return row


    def _number_edit_row(self, label: str, min_v: int, max_v: int):
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)

        lbl = QtWidgets.QLabel(label)
        lbl.setProperty("role", "field-label")
        apply_typography(lbl, "body")
        lbl.setAttribute(Qt.WA_SetFont, True)

        edit = QtWidgets.QLineEdit()
        edit.setFixedWidth(110)
        edit.setFixedHeight(28)
        edit.setValidator(QIntValidator(min_v, max_v, edit))

        apply_typography(edit, "body")
        edit.setAttribute(Qt.WA_SetFont, True)

        row.addWidget(lbl, 1)
        row.addWidget(edit, 0)

        row.line_edit = edit
        return row

    def _text_row(self, label: str):
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)

        lbl = QtWidgets.QLabel(label)
        lbl.setProperty("role", "field-label")
        apply_typography(lbl, "body")
        lbl.setAttribute(Qt.WA_SetFont, True)

        edit = QtWidgets.QLineEdit()
        edit.setMinimumWidth(220)
        edit.setMinimumHeight(30)
        apply_typography(edit, "body")
        edit.setAttribute(Qt.WA_SetFont, True)

        row.addWidget(lbl, 1)
        row.addWidget(edit)

        row.line_edit = edit
        return row


    
    def _on_save_clicked(self) -> None:
        """
        Apply settings and notify host that save succeeded.
        """
        self.apply_to_config(self.config)

        # Persist config if it has an explicit save
        if hasattr(self.config, "save"):
            self.config.save()

        # Emit quiet confirmation for status bar
        self.settings_saved.emit("Changes saved")

    def _set_bool_segmented(self, seg, value: bool):
        seg.buttons["on"].setChecked(value)
        seg.buttons["off"].setChecked(not value)

    def _get_bool_segmented(self, seg) -> bool:
        return seg.buttons["on"].isChecked()


    # =========================================================
    # Reset handlers
    # =========================================================

    def _reset_paper_roll(self):
        self._paper_reset_at = datetime.now().isoformat()

    def _reset_ink(self):
        self._ink_reset_at = datetime.now().isoformat()

    # =========================================================
    # Dialog helpers
    # =========================================================

    def browse_photoshop_exe(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Photoshop Executable",
            "",
            "Photoshop Executable (Photoshop.exe)",
        )
        if path:
            self.row_photoshop.line_edit.setText(path)

    def browse_directory(self, target: QtWidgets.QLineEdit):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            target.setText(path)

    # =========================================================
    # Ops toggle sync (schema does not yet have mockup_generator)
    # =========================================================

    from studiohub.theme.styles.utils import repolish

    def highlight_missing_paths(self, missing_keys: list[str]) -> None:
        """
        Visually mark missing required paths.
        """
        if not hasattr(self, "_path_widgets"):
            return
        
        # Clear previous error states
        for row in self._path_widgets.values():
            row.setProperty("error", False)
            row.setToolTip("")
            repolish(row)

        # Apply error state
        for key in missing_keys:
            row = self._path_widgets.get(key)
            if not row:
                continue

            row.setProperty("error", True)
            row.setToolTip("This path is required to use the application")
            repolish(row)

        # Ensure Paths section is visible
        self.scroll.ensureWidgetVisible(self.section_paths)



    def load_from_config(self, cfg):
        # ---- Paths (match DEFAULT_CONFIG paths keys)
        self.row_photoshop.line_edit.setText(
            cfg.get("paths", "photoshop_exe", "")
        )
        self.row_patents.line_edit.setText(
            cfg.get("paths", "patents_root", "")
        )
        self.row_studio.line_edit.setText(
            cfg.get("paths", "studio_root", "")
        )

        # Mockups
        self.row_mockup_templates.line_edit.setText(
            cfg.get("paths", "mockup_templates_root", "")
        )
        self.row_mockup_output.line_edit.setText(
            cfg.get("paths", "mockup_output_root", "")
        )

        self.row_runtime_root.line_edit.setText(
            cfg.get("paths", "runtime_root", "")
        )
        self.row_print_jobs.line_edit.setText(
            cfg.get("paths", "print_jobs_root", "")
        )
        self.row_jsx.line_edit.setText(
            cfg.get("paths", "jsx_root", "")
        )

        # ---- Appearance
        theme = cfg.get("appearance", "theme", "dracula")
        self.btn_theme_dracula.setChecked(theme == "dracula")
        self.btn_theme_alucard.setChecked(theme == "alucard")

        # ---- Startup (boolean segmented)
        self._set_bool_segmented(
            self.seg_scan_patents,
            cfg.get("startup", "scan_patents_on_launch", True),
        )
        self._set_bool_segmented(
            self.seg_scan_studio,
            cfg.get("startup", "scan_studio_on_launch", True),
        )
        self._set_bool_segmented(
            self.seg_rebuild_index,
            cfg.get("startup", "rebuild_index_on_launch", False),
        )

        # ---- Operations (persisted under print_manager.* only)
        self._set_bool_segmented(
            self.seg_confirm_print_clear,
            cfg.get("print_manager", "confirm_clear", True),
        )
        self._set_bool_segmented(
            self.seg_confirm_print_send,
            cfg.get("print_manager", "confirm_send", True),
        )

        # ---- Printing warnings
        self._set_bool_segmented(
            self.seg_warn_paper,
            cfg.get("warnings", "paper_low_enabled", True),
        )
        self._set_bool_segmented(
            self.seg_warn_ink,
            cfg.get("warnings", "ink_low_enabled", True),
        )
        # ---- Printing: paper state (authoritative source = consumables + paper ledger) ----
        self.lbl_paper_name.setText(cfg.get("consumables", "paper_name", "Unknown"))

        # Prefer ledger-derived remaining; fall back to the configured start length.
        remaining_ft = None
        try:
            runtime_root = cfg.get("paths", "runtime_root", "")
            if runtime_root:
                ledger = PaperLedger(Path(runtime_root))
                remaining_ft = ledger.remaining_ft
        except Exception:
            remaining_ft = None

        if remaining_ft is None:
            remaining_ft = float(cfg.get("consumables", "paper_roll_start_feet", 0.0) or 0.0)

        if remaining_ft <= 0:
            self.lbl_paper_remaining.setText("—")
        else:
            self.lbl_paper_remaining.setText(f"{remaining_ft:.1f} ft")


    def apply_to_config(self, cfg):
        # ---- Paths (match DEFAULT_CONFIG paths keys)
        cfg.set("paths", "photoshop_exe", self.row_photoshop.line_edit.text())
        cfg.set("paths", "patents_root", self.row_patents.line_edit.text())
        cfg.set("paths", "studio_root", self.row_studio.line_edit.text())
        cfg.set(
            "paths",
            "mockup_templates_root",
            self.row_mockup_templates.line_edit.text(),
        )
        cfg.set(
            "paths",
            "mockup_output_root",
            self.row_mockup_output.line_edit.text(),
        )
        cfg.set("paths", "runtime_root", self.row_runtime_root.line_edit.text())
        cfg.set("paths", "print_jobs_root", self.row_print_jobs.line_edit.text())
        cfg.set("paths", "jsx_root", self.row_jsx.line_edit.text())

        # ---- Appearance
        cfg.set(
            "appearance",
            "theme",
            "dracula" if self.btn_theme_dracula.isChecked() else "alucard",
        )

        # ---- Startup (boolean segmented)
        cfg.set(
            "startup",
            "scan_patents_on_launch",
            self._get_bool_segmented(self.seg_scan_patents),
        )
        cfg.set(
            "startup",
            "scan_studio_on_launch",
            self._get_bool_segmented(self.seg_scan_studio),
        )
        cfg.set(
            "startup",
            "rebuild_index_on_launch",
            self._get_bool_segmented(self.seg_rebuild_index),
        )

        # ---- Operations (persisted under print_manager.* only)
        cfg.set(
            "print_manager",
            "confirm_clear",
            self._get_bool_segmented(self.seg_confirm_print_clear),
        )
        cfg.set(
            "print_manager",
            "confirm_send",
            self._get_bool_segmented(self.seg_confirm_print_send),
        )

        # ---- Printing warnings
        cfg.set(
            "warnings",
            "paper_low_enabled",
            self._get_bool_segmented(self.seg_warn_paper),
        )
        cfg.set(
            "warnings",
            "ink_low_enabled",
            self._get_bool_segmented(self.seg_warn_ink),
        )
