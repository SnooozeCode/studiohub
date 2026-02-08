from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout

from studiohub.ui.dashboard.dashboard_container import DashboardContainer
from studiohub.services.dashboard.service import DashboardService
from studiohub.ui.dashboard.dashboard_panels import (
    ContentHealthPanel,
    PrintReadinessPanel,
    MonthlyPrintCountsPanel,
    MonthlyCostPanel,
    LastIndexPanel,
    RevenuePanel,
    NotesPanel,
    NewPrintJobPanel,
    OpenPrintLogPanel,
)

class DashboardView(QWidget):

    new_print_job_requested = Signal()
    open_print_log_requested = Signal()
    replace_paper_requested = Signal()

    def __init__(self, dashboard_service, parent=None):
        super().__init__(parent)

        self._service = dashboard_service

        # ──────────────────────────────────────────
        # Panels
        # ──────────────────────────────────────────

        # Row 1 — status
        self.content_health_panel = ContentHealthPanel()
        self.print_readiness_panel = PrintReadinessPanel()
        self.studio_mood_panel = LastIndexPanel()

        # Row 2 — operations
        self.new_print_job_panel = NewPrintJobPanel()
        self.open_print_log_panel = OpenPrintLogPanel()
        self.monthly_print_counts_panel = MonthlyPrintCountsPanel()

        # Row 3 — financials / notes
        self.monthly_cost_panel = MonthlyCostPanel()
        self.revenue_panel = RevenuePanel()
        self.notes_panel = NotesPanel()

        self.new_print_job_panel.triggered.connect(
            self.new_print_job_requested.emit
        )

        self.open_print_log_panel.triggered.connect(
            self.open_print_log_requested.emit
        )


        # ──────────────────────────────────────────
        # Grid layout
        # ──────────────────────────────────────────

        grid = QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(16)

        # Row 1
        grid.addWidget(
            DashboardContainer("Content Health", self.content_health_panel), 0, 0
        )
        grid.addWidget(
            DashboardContainer("Print Readiness", self.print_readiness_panel), 0, 1
        )
        grid.addWidget(
            DashboardContainer("Studio Mood", self.studio_mood_panel), 0, 2
        )

        # Row 2 — actions
        grid.addWidget(self.new_print_job_panel, 1, 0)
        grid.addWidget(self.open_print_log_panel, 1, 1)
        grid.addWidget(
            DashboardContainer("Monthly Print Counts", self.monthly_print_counts_panel), 1, 2
        )

        # Row 3
        grid.addWidget(
            DashboardContainer("Monthly Costs", self.monthly_cost_panel), 2, 0
        )
        grid.addWidget(
            DashboardContainer("Revenue", self.revenue_panel), 2, 1
        )
        grid.addWidget(
            DashboardContainer("Notes", self.notes_panel), 2, 2
        )

        # Stretch behavior
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        self.refresh()

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def refresh(self) -> None:
        snapshot = self._service.get_snapshot()

        # Row 1
        self.content_health_panel.set_data(snapshot.archive, snapshot.studio)
        self.print_readiness_panel.set_data(snapshot.studio)
        self.studio_mood_panel.set_data(snapshot.index)

        # Row 2
        self.monthly_print_counts_panel.set_data(snapshot.monthly_print_count)

        # Row 3
        self.monthly_cost_panel.set_data(snapshot.monthly_costs)
        self.revenue_panel.set_data(snapshot.revenue)
        self.notes_panel.set_data(snapshot.notes)


    def request_replace_paper(self) -> None:
        self.replace_paper_requested.emit()
