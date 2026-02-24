"""
Dependency injection container for application components.

This module is the SINGLE place responsible for constructing and wiring:
- configuration
- services
- Qt models

UI code must never construct services directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6 import QtCore

# --------------------------------------------------
# Configuration
# --------------------------------------------------

from studiohub.config.manager import ConfigManager
from studiohub.models.print_job_config import PrintJobConfig

# --------------------------------------------------
# Core services
# --------------------------------------------------

from studiohub.services.core.print_log import PrintLogState
from studiohub.services.core.paper_ledger import PaperLedger
from studiohub.services.index import PosterIndexState

from studiohub.services.dashboard.service import DashboardService
from studiohub.services.notifications.notification_service import NotificationService
from studiohub.services.media.service_qt import MediaServiceQt
from studiohub.services.index import IndexManager

# --------------------------------------------------
# Qt-facing models
# --------------------------------------------------

from studiohub.models.missing_files_model_qt import MissingFilesModelQt
from studiohub.models.print_manager_model_qt import PrintManagerModelQt
from studiohub.models.mockup_generator_model_qt import MockupGeneratorModelQt
from studiohub.models.index_log_model_qt import IndexLogModelQt
from studiohub.services.dashboard.notes_store import DashboardNotesStore

# ==================================================
# Dependency container
# ==================================================

@dataclass
class Dependencies:
    """
    Fully constructed application dependencies.

    This object is immutable after creation and is passed
    into UI layers that need access to services or models.
    """

    # -----------------------------
    # Configuration
    # -----------------------------

    config_manager: ConfigManager
    print_job_config: PrintJobConfig

    # -----------------------------
    # Services (non-UI)
    # -----------------------------

    paper_ledger: PaperLedger
    poster_index_state: PosterIndexState
    print_log_state: PrintLogState
    dashboard_service: DashboardService
    index_manager: IndexManager  # ADD THIS
    notification_service: NotificationService
    notes_store: DashboardNotesStore
    
    # ===== NEW: Media service =====
    media_service: MediaServiceQt
    # ===============================

    # -----------------------------
    # Qt models
    # -----------------------------

    missing_model: MissingFilesModelQt
    print_manager_model: PrintManagerModelQt
    mockup_model: MockupGeneratorModelQt
    index_log_model: IndexLogModelQt


# ==================================================
# Factory
# ==================================================

class DependencyContainer:
    """
    Factory for creating application dependencies.

    This centralizes:
    - initialization order
    - error handling
    - dependency wiring

    Nothing outside this file should ever call constructors
    for services or models directly.
    """

    @staticmethod
    def create(parent: QtCore.QObject | None = None) -> Dependencies:
        # --------------------------------------------------
        # Configuration (MUST be first)
        # --------------------------------------------------

        config_manager = ConfigManager()
        print_job_config = PrintJobConfig.from_config(config_manager)

        # --------------------------------------------------
        # Runtime root resolution
        # --------------------------------------------------

        runtime_root_raw = config_manager.get("paths", "runtime_root", "")
        if runtime_root_raw:
            runtime_root = Path(runtime_root_raw).expanduser()
        else:
            runtime_root = config_manager.get_appdata_root()

        runtime_root.mkdir(parents=True, exist_ok=True)

        # --------------------------------------------------
        # Core services (order matters!)
        # --------------------------------------------------

        # 1. Paper ledger (no dependencies)
        paper_ledger = PaperLedger(runtime_root)

        # 2. Poster index state (no dependencies)
        poster_index_state = PosterIndexState(parent)
        poster_index_state.load(config_manager.get_poster_index_path())

        # 3. Print log state (needs dashboard service, but we create it first without dashboard_service)
        #    We'll update it after dashboard service is created
        print_log_state = PrintLogState(
            log_path=config_manager.get_print_log_path(),
            dashboard_service=None,  # Will set after dashboard service is created
            parent=parent,
        )

        # Load print log (may fail on first launch)
        try:
            print_log_state.load()
        except Exception as e:
            if parent and hasattr(parent, '_safe_emit_status'):
                parent._safe_emit_status(f"Warning: Failed to load print log - {str(e)[:50]}")
            else:
                print(f"[WARN] Failed to load print log: {e}")

        # 4. Notes store (needs config)
        notes_store = DashboardNotesStore(
            config_manager=config_manager
        )
        
        # 5. Dashboard service (needs everything)
        dashboard_service = DashboardService(
            config_manager=config_manager,
            paper_ledger=paper_ledger,
            poster_index_state=poster_index_state,
            print_log_state=print_log_state,  # Pass the print log state
            print_log_path=config_manager.get_print_log_path(),
        )

        # 6. Now update print log state with dashboard service reference
        print_log_state.set_dashboard_service(dashboard_service)

        # 7. Index manager (needs dashboard service)
        index_manager = IndexManager(
            config_manager=config_manager,
            status_callback=parent._safe_emit_status if parent else None,
            dashboard_service=dashboard_service,
            parent=parent,
        )

        # 8. Notification service (no dependencies)
        notification_service = NotificationService()
        
        # 9. Media service (needs config)
        media_service = MediaServiceQt(
            config=config_manager,
            parent=parent
        )

        # --------------------------------------------------
        # Qt-facing models
        # --------------------------------------------------

        missing_model = MissingFilesModelQt(
            config_manager=config_manager,
            parent=parent,
        )

        print_manager_model = PrintManagerModelQt(
            missing_model=missing_model,
            config_manager=config_manager,
            paper_ledger=paper_ledger,
            parent=parent,
        )

        mockup_model = MockupGeneratorModelQt(
            config_manager,
            parent=parent,
        )

        logs_root = config_manager.get_appdata_root() / "logs"
        logs_root.mkdir(parents=True, exist_ok=True)

        index_log_model = IndexLogModelQt(
            logs_root=logs_root,
            parent=parent,
        )

        # --------------------------------------------------
        # Assemble immutable dependency container
        # --------------------------------------------------

        return Dependencies(
            config_manager=config_manager,
            print_job_config=print_job_config,
            paper_ledger=paper_ledger,
            poster_index_state=poster_index_state,
            print_log_state=print_log_state,
            dashboard_service=dashboard_service,
            index_manager=index_manager,
            notes_store=notes_store,
            notification_service=notification_service,
            media_service=media_service,
            missing_model=missing_model,
            print_manager_model=print_manager_model,
            mockup_model=mockup_model,
            index_log_model=index_log_model,
        )