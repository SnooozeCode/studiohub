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

from studiohub.config_manager import ConfigManager
from studiohub.hub_models.print_job_config import PrintJobConfig

# --------------------------------------------------
# Core services
# --------------------------------------------------

from studiohub.services.paper_ledger import PaperLedger
from studiohub.services.poster_index_state import PosterIndexState
from studiohub.services.print_log_state import PrintLogState
from studiohub.services.dashboard.service import DashboardService
from studiohub.services.notifications.notification_service import NotificationService

# --------------------------------------------------
# Qt-facing models
# --------------------------------------------------

from studiohub.hub_models.missing_files_model_qt import MissingFilesModelQt
from studiohub.hub_models.print_manager_model_qt import PrintManagerModelQt
from studiohub.hub_models.mockup_generator_model_qt import MockupGeneratorModelQt
from studiohub.hub_models.index_log_model_qt import IndexLogModelQt


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
    notification_service: NotificationService

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
        # Core services
        # --------------------------------------------------

        paper_ledger = PaperLedger(runtime_root)

        poster_index_state = PosterIndexState(parent)
        poster_index_state.load(config_manager.get_poster_index_path())

        print_log_state = PrintLogState(
            log_path=config_manager.get_print_log_path(),
            parent=parent,
        )

        # Print log may not exist during first launch — never crash
        try:
            print_log_state.load()
        except Exception:
            pass

        dashboard_service = DashboardService(
            config_manager=config_manager,
            paper_ledger=paper_ledger,
            poster_index_state=poster_index_state,
            print_log_state=print_log_state,
            print_log_path=config_manager.get_print_log_path(),
        )

        notification_service = NotificationService()

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
            notification_service=notification_service,
            missing_model=missing_model,
            print_manager_model=print_manager_model,
            mockup_model=mockup_model,
            index_log_model=index_log_model,
        )
