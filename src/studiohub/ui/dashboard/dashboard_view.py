
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout
from PySide6.QtCore import Signal          # <-- NEW IMPORT

from studiohub.services.dashboard.service import DashboardService
from studiohub.ui.dashboard.dashboard_container import DashboardContainer
from studiohub.services.dashboard.notes_store import DashboardNotesStore
from studiohub.ui.dashboard.dashboard_panels import (
    ContentHealthPanel,
    PrintReadinessPanel,
    MonthlyPrintCountsPanel,
    MonthlyCostPanel,
    StudioMoodPanel,
    RevenuePanel,
    NotesPanel,                 # <-- NEW IMPORT
    NewPrintJobPanel,
    OpenPrintLogPanel,
)

class DashboardView(QWidget):
    """
    The main dashboard view. It now receives a DashboardNotesStore
    so that the NotesPanel can persist its rich‑text content.
    """

    # Signals that the main window may still listen to
    new_print_job_requested = Signal()
    open_print_log_requested = Signal()
    replace_paper_requested = Signal()

    def __init__(
        self,
        dashboard_service: DashboardService,
        notes_store: DashboardNotesStore,   # <-- NEW ARGUMENT
        parent=None,
    ):
        super().__init__(parent)

        # -----------------------------------------------------------------
        # Store injected dependencies
        # -----------------------------------------------------------------
        self._service = dashboard_service
        self._notes_store = notes_store          # <-- keep a reference

        # -----------------------------------------------------------------
        # UI construction (unchanged from your original code)
        # -----------------------------------------------------------------
        # Row 1 — status
        self.content_health_panel = ContentHealthPanel()
        self.print_readiness_panel = PrintReadinessPanel()
        self.studio_mood_panel = StudioMoodPanel()

        # Row 2 — operations
        self.new_print_job_panel = NewPrintJobPanel()
        self.open_print_log_panel = OpenPrintLogPanel()
        self.monthly_print_counts_panel = MonthlyPrintCountsPanel()

        # Row 3 — financials / notes
        self.monthly_cost_panel = MonthlyCostPanel()
        self.revenue_panel = RevenuePanel()
        self.notes_panel = NotesPanel(self._notes_store)  # <-- our rich‑text widget

        # -----------------------------------------------------------------
        # Signal wiring for the two action panels
        # -----------------------------------------------------------------
        self.new_print_job_panel.triggered.connect(
            self.new_print_job_requested.emit
        )
        self.open_print_log_panel.triggered.connect(
            self.open_print_log_requested.emit
        )

        # -----------------------------------------------------------------
        # Layout (grid)
        # -----------------------------------------------------------------
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
            DashboardContainer("Monthly Print Counts", self.monthly_print_counts_panel),
            1,
            2,
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

        # Stretch behavior (unchanged)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # -----------------------------------------------------------------
        # Initial data load
        # -----------------------------------------------------------------
        self.refresh()

        # -----------------------------------------------------------------
        # Load persisted notes (if any) and push them into the panel
        # -----------------------------------------------------------------
        saved_html = self._notes_store.load_html()
        if saved_html:
            self.notes_panel.set_data(saved_html)

        # -----------------------------------------------------------------
        # Wire the panel’s “edited” signal to the store
        # -----------------------------------------------------------------
        if hasattr(self.notes_panel, "notesEdited"):
            self.notes_panel.notesEdited.connect(self._save_notes_to_store)

    # -----------------------------------------------------------------
    # Public API – refresh all panels
    # -----------------------------------------------------------------
    def refresh(self) -> None:
        snapshot = self._service.get_snapshot()

        # Row 1
        self.content_health_panel.set_data(snapshot.archive, snapshot.studio)
        self.print_readiness_panel.set_data(snapshot.studio)
        self.studio_mood_panel.set_data(snapshot.studio_mood)

        # Row 2
        self.monthly_print_counts_panel.set_data(snapshot.monthly_print_count)

        # Row 3
        self.monthly_cost_panel.set_data(snapshot.monthly_costs)
        self.revenue_panel.set_data(snapshot.revenue)
        # Notes panel is handled separately (loaded from the store)

    def set_loading(self, key: str, is_loading: bool) -> None:
        """
        key represents an index pipeline ("archive" or "studio").
        Only panels that depend on index data should react.
        """

        if key in ("archive", "studio"):
            if hasattr(self.content_health_panel, "set_loading"):
                self.content_health_panel.set_loading(is_loading)

    # -----------------------------------------------------------------
    # Slot that writes the current HTML to the notes store
    # -----------------------------------------------------------------
    def _save_notes_to_store(self, html: str) -> None:
        """Persist the notes whenever the editor emits a change."""
        self._notes_store.save_html(html)

    # -----------------------------------------------------------------
    # Miscellaneous UI slots (unchanged)
    # -----------------------------------------------------------------
    def request_replace_paper(self) -> None:
        self.replace_paper_requested.emit()