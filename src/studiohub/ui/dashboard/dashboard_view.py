from __future__ import annotations

from PySide6 import QtCore
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel
from PySide6.QtCore import Signal, Qt

from studiohub.services.dashboard.service import DashboardService
from studiohub.ui.dashboard.dashboard_container import DashboardContainer
from studiohub.services.dashboard.notes_store import DashboardNotesStore
from studiohub.services.media.service_qt import MediaServiceQt  # NEW
from studiohub.ui.dashboard.panels.dashboard_panels import (
    ContentHealthPanel,
    PrintReadinessPanel,
    MonthlyPrintCountsPanel,
    MonthlyCostPanel,
    RevenuePanel,
    NotesPanel,
    NewPrintJobPanel,
    OpenPrintLogPanel,
)
from studiohub.ui.dashboard.panels.studio_mood import StudioMoodPanel

from studiohub.style.typography.rules import apply_typography

class DashboardView(QWidget):
    """
    The main dashboard view. It now receives a DashboardNotesStore
    and MediaServiceQt for the Studio Mood panel.
    """

    # Signals that the main window may still listen to
    new_print_job_requested = Signal()
    open_print_log_requested = Signal()
    replace_paper_requested = Signal()

    def __init__(
        self,
        dashboard_service: DashboardService,
        notes_store: DashboardNotesStore,
        media_service: MediaServiceQt,
        print_log_state,
        parent=None,
    ):
        super().__init__(parent)

        # Store injected dependencies
        self._service = dashboard_service
        self._notes_store = notes_store
        self._media_service = media_service
        self._print_log_state = print_log_state

        # =====================================================
        # UI Construction
        # =====================================================
        
        # Row 1 — status
        self.content_health_panel = ContentHealthPanel()
        self.print_readiness_panel = PrintReadinessPanel()
        
        # ===== FIXED: Create Studio Mood panel with media service =====
        # We'll create it later after we have the container
        self._studio_mood_placeholder = QLabel("Loading media...")
        self._studio_mood_placeholder.setAlignment(Qt.AlignCenter)
        self._studio_mood_placeholder.setObjectName("DashboardPlaceholder")
        self.studio_mood_panel = self._studio_mood_placeholder  # Placeholder for now
        # =============================================================

        # Row 2 — operations
        self.new_print_job_panel = NewPrintJobPanel()
        self.open_print_log_panel = OpenPrintLogPanel()
        self.monthly_print_counts_panel = MonthlyPrintCountsPanel()

        # Row 3 — financials / notes
        self.monthly_cost_panel = MonthlyCostPanel()
        self.revenue_panel = RevenuePanel()
        self.notes_panel = NotesPanel(self._notes_store)

        # Signal wiring for action panels
        self.new_print_job_panel.triggered.connect(
            self.new_print_job_requested.emit
        )
        self.open_print_log_panel.triggered.connect(
            self.open_print_log_requested.emit
        )

        # =====================================================
        # Layout (grid)
        # =====================================================
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
        
        # ===== FIXED: Studio Mood container with active time header =====
        self.studio_mood_container = DashboardContainer("Studio Mood", self.studio_mood_panel)
        
        # Add active time label to header
        self.studio_mood_active_lbl = QLabel("Active · 0m")
        apply_typography(self.studio_mood_active_lbl, "small")
        self.studio_mood_active_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.studio_mood_active_lbl.setObjectName("StudioMoodActive")
        self.studio_mood_container.set_header_widget(self.studio_mood_active_lbl)
        
        grid.addWidget(self.studio_mood_container, 0, 2)
        # =============================================================

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

        # Stretch behavior
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # ===== NEW: Create actual Studio Mood panel after UI is built =====
        QtCore.QTimer.singleShot(0, self._init_studio_mood_panel)
        # =================================================================

        # Initial data load
        self.refresh()

        # Load persisted notes
        saved_html = self._notes_store.load_html()
        if saved_html:
            self.notes_panel.set_data(saved_html)

    def _init_studio_mood_panel(self):
        """Create and initialize the real Studio Mood panel."""
        try:
            from studiohub.ui.dashboard.panels.studio_mood import StudioMoodPanel
            
            # Create the REAL panel with print_log_state
            real_panel = StudioMoodPanel(
                media_service=self._media_service,
                print_log_state=self._print_log_state,  # PASS IT HERE
                parent=self.studio_mood_container
            )
            
            # Connect active time signal to header
            real_panel.active_time_changed.connect(
                self.studio_mood_active_lbl.setText
            )
            
            # Replace placeholder in container
            self.studio_mood_container.replace_content(real_panel)
            
            # Store reference
            self.studio_mood_panel = real_panel
            
        except Exception as e:
            print(f"[Dashboard] Failed to initialize Studio Mood panel: {e}")
            import traceback
            traceback.print_exc()


    def refresh(self) -> None:
        """Refresh all panels with latest data."""
        snapshot = self._service.get_snapshot()

        # Row 1
        self.content_health_panel.set_data(snapshot.archive, snapshot.studio)
        
        if snapshot.paper and snapshot.ink:
            self.print_readiness_panel.set_data(snapshot.paper, snapshot.ink)
        

        # Row 2
        self.monthly_print_counts_panel.set_data(snapshot.monthly_print_count)

        # Row 3
        self.monthly_cost_panel.set_data(snapshot.monthly_costs)
        self.revenue_panel.set_data(snapshot.revenue)

    def set_loading(self, key: str, is_loading: bool) -> None:
        """Set loading state for panels."""
        if key in ("archive", "studio"):
            if hasattr(self.content_health_panel, "set_loading"):
                self.content_health_panel.set_loading(is_loading)

    def _save_notes_to_store(self, html: str) -> None:
        """Persist notes to store."""
        self._notes_store.save_html(html)

    def request_replace_paper(self) -> None:
        """Request paper replacement."""
        self.replace_paper_requested.emit()