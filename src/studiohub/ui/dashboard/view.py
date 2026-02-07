from __future__ import annotations

from pathlib import Path
from datetime import datetime

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt

from studiohub.ui.dashboard.cards import DashboardCard, KPICard, ConsumableKPICard
from studiohub.ui.dashboard.panels.print_count_panel import PatentsVsStudioChart
from studiohub.ui.layout.row_layout import configure_view, RowProfile
from studiohub.services.dashboard_metrics import DashboardMetrics
from studiohub.ui.dashboard.panels.monthly_cost_ledger import MonthlyCostLedgerPanel, MonthlyCostBreakdown


# =========================================================
# Splitter that LOOKS like spaced rows but CANNOT be dragged
# =========================================================

class _NoDragSplitterHandle(QtWidgets.QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event): event.ignore()
    def mouseMoveEvent(self, event): event.ignore()
    def mouseReleaseEvent(self, event): event.ignore()
    def mouseDoubleClickEvent(self, event): event.ignore()


class _NoDragSplitter(QtWidgets.QSplitter):
    def createHandle(self):  # noqa: N802
        return _NoDragSplitterHandle(self.orientation(), self)

class DashboardPrintJobEntry(QtWidgets.QFrame):

    def __init__(
        self,
        *,
        names: list[str],
        badge_text: str,
        is_two_up: bool,
        row_parity: int = 0,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)

        ROW_HEIGHT = 18
        BADGE_WIDTH = 64
        BADGE_RADIUS = 6

        self.setObjectName("DashboardPrintJobEntry")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty(
            "row",
            "even" if row_parity % 2 == 0 else "odd",
        )

        # Layout
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(2, 4, 2, 4)
        grid.setHorizontalSpacing(5)
        grid.setVerticalSpacing(3)

        # Left: poster names (1 or 2 rows)
        def _make_name_label(text: str) -> QtWidgets.QLabel:
            lbl = QtWidgets.QLabel(text or "—")
            lbl.setProperty("typography", "body-small")
            lbl.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            lbl.setWordWrap(False)
            lbl.setTextInteractionFlags(Qt.NoTextInteraction)
            return lbl

        name1 = _make_name_label(names[0] if len(names) > 0 else "—")
        grid.addWidget(name1, 0, 0)

        if is_two_up:
            name2 = _make_name_label(names[1] if len(names) > 1 else "—")
            grid.addWidget(name2, 1, 0)

        # Right: badge
        badge = QtWidgets.QLabel(badge_text)
        badge.setObjectName("DashboardSizeBadge")
        badge.setAlignment(Qt.AlignCenter)

        # Styling hooks
        badge.setProperty("role", "dashboard-size-badge")
        badge.setProperty("variant", "two-up" if is_two_up else "single")

        # Density-correct sizing
        badge.setFixedWidth(BADGE_WIDTH)
        badge.setMinimumHeight(ROW_HEIGHT if not is_two_up else ROW_HEIGHT * 2 + grid.verticalSpacing())
        badge.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed,
        )

        if is_two_up:
            grid.addWidget(badge, 0, 1, 2, 1)   # span both rows
        else:
            grid.addWidget(badge, 0, 1)


        # Row heights (ensures consistent density)
        grid.setRowMinimumHeight(0, ROW_HEIGHT)
        if is_two_up:
            grid.setRowMinimumHeight(1, ROW_HEIGHT)



class DashboardViewQt(QtWidgets.QWidget):
    queue_readd_requested = QtCore.Signal(list)

    ROW_COUNT = 3
    OUTER_MARGINS = 16
    ROW_SPACING = 22  # splitter handle width (visual gap)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        cfg = self._get_config()

        # Services
        # NOTE: Do NOT hardcode print_log_path here; the dashboard must respect
        # ConfigManager's readonly/shared log path on other machines.
        self.metrics = DashboardMetrics(
            print_log_path=cfg.get_print_log_path()
        )

        # State
        self._loading = {"patents": False, "studio": False}
        self._patents_cache: dict = {}
        self._studio_cache: dict = {}
        self._last_index: dict = {}

        # Debounce equal sizing
        self._equalize_timer = QtCore.QTimer(self)
        self._equalize_timer.setSingleShot(True)
        self._equalize_timer.timeout.connect(self._equalize_splitter_rows)

        self._build_ui()
        QtCore.QTimer.singleShot(0, self._equalize_splitter_rows)

    # =========================================================
    # Helpers
    # =========================================================

    def _format_date(self, iso_str: str | None) -> str:
        if not iso_str:
            return "—"
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%b %d, %Y")
        except Exception:
            return "—"

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(
            self.OUTER_MARGINS,
            self.OUTER_MARGINS,
            self.OUTER_MARGINS,
            self.OUTER_MARGINS,
        )
        root.setSpacing(0)

        self.splitter = _NoDragSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(self.ROW_SPACING)
        self.splitter.setOpaqueResize(True)
        self.splitter.setFocusPolicy(Qt.NoFocus)
        self.splitter.setAttribute(Qt.WA_Hover, False)

        self.splitter.setStyleSheet("""
        QSplitter::handle { background: transparent; }
        """)

        self.row_top = self._build_row_top()
        self.row_mid = self._build_row_mid()
        self.row_bot = self._build_row_bot()

        for row in (self.row_top, self.row_mid, self.row_bot):
            row.setMinimumHeight(0)
            row.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
            )
            self.splitter.addWidget(row)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 1)

        root.addWidget(self.splitter, 1)

    def _build_row_top(self) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # --- Col 1: Archive + Studio (stacked) ---
        col_left = QtWidgets.QWidget()
        col_left_l = QtWidgets.QVBoxLayout(col_left)
        col_left_l.setContentsMargins(0, 0, 0, 0)
        col_left_l.setSpacing(12)

        self.kpi_patents = KPICard("ARCHIVE", "0")
        self.kpi_studio = KPICard("STUDIO", "0")

        col_left_l.addWidget(self.kpi_patents, 1)
        col_left_l.addWidget(self.kpi_studio, 1)

        # --- Col 2: Paper + Ink (stacked) ---
        col_mid = QtWidgets.QWidget()
        col_mid_l = QtWidgets.QVBoxLayout(col_mid)
        col_mid_l.setContentsMargins(0, 0, 0, 0)
        col_mid_l.setSpacing(12)

        self.kpi_paper = ConsumableKPICard("PAPER STOCK", unit="ft")
        self.kpi_ink = ConsumableKPICard("INK LEVELS", unit="%")

        col_mid_l.addWidget(self.kpi_paper, 1)
        col_mid_l.addWidget(self.kpi_ink, 1)

        self.kpi_paper.replace_requested.connect(self._on_replace_paper)
        self.kpi_ink.replace_requested.connect(self._on_replace_ink)

        # --- Col 3: Overview ---
        self.card_overview = DashboardCard("OVERVIEW")
        self.card_overview.add_widget(self._placeholder("Reserved"), 1)

        layout.addWidget(col_left, 1)
        layout.addWidget(col_mid, 1)
        layout.addWidget(self.card_overview, 1)

        return row

    def _build_row_mid(self) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        a = DashboardCard("Print Volume (Last 30 Days)")
        a.add_widget(self._placeholder("Chart placeholder"), 1)
        
        b = DashboardCard("PATENTS VS STUDIO")
        self.patents_vs_studio_chart = PatentsVsStudioChart()
        b.set_subtitle(datetime.now().strftime("%B %Y"))
        b.add_widget(self.patents_vs_studio_chart, 1)

        layout.addWidget(a, 2)
        layout.addWidget(b, 1)
        return row

    def _build_row_bot(self) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # -------------------------------------------------
        # LEFT: Full-height panel (placeholder for now)
        # -------------------------------------------------
        self.left_full_card = DashboardCard("Left Panel")
        self.left_full_card.add_widget(self._placeholder("Reserved"), 1)

        # -------------------------------------------------
        # CENTER: Stack (Last Jobs + Last Indexes)
        # -------------------------------------------------
        center_stack = QtWidgets.QWidget()
        center_stack.setLayout(QtWidgets.QVBoxLayout())
        center_layout = center_stack.layout()

        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(16)

        # --- Last Print Jobs ---
        self.last_job_card = DashboardCard("RECENT PRINT JOBS")
        self.last_job_card.setProperty("header", "compact")

        self.last_job_container = QtWidgets.QWidget()
        self.last_job_container_layout = QtWidgets.QVBoxLayout(self.last_job_container)
        self.last_job_container_layout.setContentsMargins(0, 0, 0, 0)
        self.last_job_container_layout.setSpacing(6)

        self.last_job_card.add_widget(self.last_job_container, 1)

        # --- Last Print Indexes ---
        self.last_index_card = DashboardCard("RECENT POSTER INDEXES")
        self.last_index_card.setProperty("header", "compact")

        self.last_index_container = QtWidgets.QWidget()
        self.last_index_container_layout = QtWidgets.QVBoxLayout(self.last_index_container)
        self.last_index_container_layout.setContentsMargins(0, 0, 0, 0)
        self.last_index_container_layout.setSpacing(6)

        self.last_index_card.add_widget(self.last_index_container, 1)

        center_layout.addWidget(self.last_job_card, 1)
        center_layout.addWidget(self.last_index_card, 1)

        # -------------------------------------------------
        # RIGHT: Monthly Cost
        # -------------------------------------------------
        c = DashboardCard("MONTHLY PRODUCTION COST")
        self.panel_monthly_cost = MonthlyCostLedgerPanel(parent=self)

        c.set_subtitle(datetime.now().strftime("%B %Y"))
        c.add_widget(self.panel_monthly_cost, 1)

        # -------------------------------------------------
        # Assemble
        # -------------------------------------------------
        layout.addWidget(self.left_full_card, 1)
        layout.addWidget(center_stack, 1)
        layout.addWidget(c, 1)

        return row


    def _placeholder(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setObjectName("DashboardPlaceholder")
        return lbl

    # =========================================================
    # Equal sizing
    # =========================================================

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QtCore.QTimer.singleShot(0, self._equalize_splitter_rows)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._equalize_splitter_rows)

    def _equalize_splitter_rows(self) -> None:
        rect = self.splitter.contentsRect()
        total = rect.height()
        if total <= 0:
            return

        handle_space = self.splitter.handleWidth() * (self.ROW_COUNT - 1)
        usable = max(1, total - handle_space)

        base = usable // self.ROW_COUNT
        remainder = usable - (base * self.ROW_COUNT)

        sizes = [base] * self.ROW_COUNT
        for i in range(remainder):
            sizes[i] += 1

        self.splitter.blockSignals(True)
        self.splitter.setSizes(sizes)
        self.splitter.blockSignals(False)

    # =========================================================
    # Data binding (hub compatibility)
    # =========================================================

    def update_from_cache(self, index: dict, patents_cache=None, studio_cache=None, **__):

        cfg = self._get_config()

        # Always rebind to the authoritative readonly path (never guess/fallback here)
        try:
            self.metrics.print_log_path = cfg.get_print_log_path()
            
        except Exception as e:
            # Graceful degrade: keep existing path, but do not crash dashboard rendering
            print("[Dashboard] Could not resolve readonly print log path:", e)

        # Optional: only call reload if your DashboardMetrics actually caches rows.
        # If yours doesn't cache, this is safe to remove.

        self._last_index = index or {}

        # Provide index to metrics for poster classification
        try:
            self.metrics.set_index(self._last_index)
        except Exception as e:
            print("DashboardMetrics.set_index error:", e)


        self._patents_cache = patents_cache or {}
        self._studio_cache = studio_cache or {}

        posters = index.get("posters", {}) if isinstance(index, dict) else {}
        patents = posters.get("patents", {}) if isinstance(posters, dict) else {}
        studio = posters.get("studio", {}) if isinstance(posters, dict) else {}

        self.kpi_patents.set_value(str(len(patents)))
        self.kpi_studio.set_value(str(len(studio)))

        def _calculate_missing_stats(cache: dict) -> tuple[int, int]:
            if not isinstance(cache, dict):
                return 0, 0
            issues = 0
            missing = 0
            for _poster_id, files in cache.items():
                if files:
                    issues += 1
                    missing += len(files)
            return issues, missing

        issues, missing = _calculate_missing_stats(self._patents_cache)
        self.kpi_patents.set_issues(issues)
        self.kpi_patents.set_missing(missing)

        issues, missing = _calculate_missing_stats(self._studio_cache)
        self.kpi_studio.set_issues(issues)
        self.kpi_studio.set_missing(missing)

        # Paper KPI
        try:
            paper_status = self.metrics.get_paper_status()
            self.kpi_paper.set_status(int(paper_status["feet"]), paper_status["percent"])
            self.kpi_paper.set_last_replaced(cfg.get("consumables", "paper_roll_reset_at", ""))
        except Exception as e:
            print("Paper KPI error:", e)

        # Ink KPI
        try:
            ink_percent = self.metrics.get_ink_percent()
            self.kpi_ink.set_status(ink_percent, ink_percent)
            self.kpi_ink.set_last_replaced(cfg.get("consumables", "ink_reset_at", ""))
        except Exception as e:
            print("Ink KPI error:", e)
            
        # Patents vs Studio (30 days)
        try:
            counts = self.metrics.get_print_counts_last_30_days()

            self.patents_vs_studio_chart.set_values(
                patents=counts["patents"],
                studio=counts["studio"],
            )

        except Exception as e:
            print("Patents vs Studio chart error:", e)


        self._refresh_print_logs()
        self._refresh_print_indexes()

        # -------------------------------------------------
        # Monthly Cost Ledger (calendar month)
        # -------------------------------------------------
        try:
            monthly = self.metrics.get_monthly_costs()

            shipping_per_print = cfg.get("consumables", "shipping_cost_per_print", 0.0)

            breakdown = MonthlyCostBreakdown(
                ink=monthly["ink"],
                paper=monthly["paper"],
                shipping_supplies=monthly["prints"] * shipping_per_print,
                prints=monthly["prints"],
            )

            self.panel_monthly_cost.update_costs(breakdown)

        except Exception as e:
            print("Monthly cost panel error:", e)



    def _refresh_print_logs(self) -> None:
        layout = self.last_job_container_layout

        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        jobs = self.metrics.get_recent_print_jobs(limit=2)

        if not jobs:
            layout.addWidget(QtWidgets.QLabel("No recent print jobs"))
            return

        for idx, job in enumerate(jobs):
            mode = (job.get("mode") or "single").lower()
            size = (job.get("size") or "").replace("×", "x")
            files = job.get("files") or []

            names = [Path(f).stem for f in files if isinstance(f, str)]
            is_two_up = (mode == "2up")

            if is_two_up:
                display_names = (names + ["—", "—"])[:2]
                badge_text = f"2UP"
            else:
                display_names = [names[0]] if names else ["—"]
                badge_text = size

            entry = DashboardPrintJobEntry(
                names=display_names,
                badge_text=badge_text,
                is_two_up=is_two_up,
                row_parity=idx,
            )

            entry.setProperty("job_payload", job)
            entry.setCursor(Qt.PointingHandCursor)
            self._wire_recent_job_interaction(entry)

            layout.addWidget(entry)


    def _refresh_print_indexes(self) -> None:
        layout = self.last_index_container_layout

        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        events = self.metrics.get_recent_index_events(limit=2)

        if not events:
            layout.addWidget(QtWidgets.QLabel("No recent indexing activity"))
            return

        for evt in events:
            ts = evt.get("timestamp")
            ts_str = ts.strftime("%b %d · %I:%M %p").lstrip("0") if ts else "—"

            lbl = QtWidgets.QLabel(
                f"{ts_str} · Archive {evt.get('patents', 0)} · Studio {evt.get('studio', 0)}"
            )
            lbl.setProperty("typography", "body-small")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            layout.addWidget(lbl)



    def set_loading(self, source: str, is_loading: bool) -> None:
        if source not in self._loading:
            return
        self._loading[source] = bool(is_loading)

    # =========================================================
    # Replace buttons
    # =========================================================

    def _on_replace_paper(self):
        cfg = self._get_config()
        now = datetime.now().isoformat()
        cfg.set("consumables", "paper_roll_reset_at", now)
        self.metrics.reload()
        self.update_from_cache(self._last_index, self._patents_cache, self._studio_cache)

    def _on_replace_ink(self):
        cfg = self._get_config()
        now = datetime.now().isoformat()
        cfg.set("consumables", "ink_reset_at", now)
        cfg.set("consumables", "ink_reset_percent", 100)
        self.metrics.reload()
        self.update_from_cache(self._last_index, self._patents_cache, self._studio_cache)

    # =========================================================
    # Config access
    # =========================================================

    def _get_config(self):
        w = self
        while w:
            if hasattr(w, "config_manager"):
                return w.config_manager
            w = w.parent()
        raise RuntimeError("ConfigManager not found")

    # =========================================================
    # Recent Jobs interaction (badge double-click)
    # =========================================================

    def _resolve_source(self, poster_id: str) -> str:
        """Best-effort source resolution for queue re-add."""
        posters = self._last_index.get("posters", {}) if isinstance(self._last_index, dict) else {}
        patents = posters.get("patents", {}) if isinstance(posters, dict) else {}
        studio = posters.get("studio", {}) if isinstance(posters, dict) else {}

        if isinstance(patents, dict) and poster_id in patents:
            return "patents"
        if isinstance(studio, dict) and poster_id in studio:
            return "studio"
        return ""

    def _readd_job(self, job: dict) -> None:
        """Convert a dashboard job row back into print-queue items."""
        payload: list[dict] = []

        mode = (job.get("mode") or "single")
        sheet_size = (job.get("size") or "")
        files = job.get("files") or []

        # 2-UP log rows represent a sheet size (18x24 or 24x36) but the queue
        # operates on individual posters.
        if mode == "2up":
            if sheet_size == "18x24":
                poster_size = "12x18"
            elif sheet_size == "24x36":
                poster_size = "18x24"
            else:
                return

            for f in files:
                name = Path(f).stem
                payload.append({
                    "name": name,
                    "size": poster_size,
                    "path": f,
                    "source": self._resolve_source(name),
                })
        else:
            for f in files:
                name = Path(f).stem
                payload.append({
                    "name": name,
                    "size": sheet_size,
                    "path": f,
                    "source": self._resolve_source(name),
                })

        if payload:
            self.queue_readd_requested.emit(payload)

    def _wire_recent_job_interaction(self, row: QtWidgets.QWidget) -> None:
        def mouse_double_click(event):
            if event.button() != QtCore.Qt.LeftButton:
                return
            job = row.property("job_payload")
            if not job:
                return
            self._readd_job(job)

        # Your badge uses role="dashboard-size-badge"
        for lbl in row.findChildren(QtWidgets.QLabel):
            if lbl.property("role") == "dashboard-size-badge":
                lbl.mouseDoubleClickEvent = mouse_double_click
                lbl.setCursor(Qt.PointingHandCursor)