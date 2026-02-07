"""Dependency injection container for application components."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6 import QtCore

from studiohub.config_manager import ConfigManager
from studiohub.services.paper_ledger import PaperLedger
from studiohub.services.poster_index_state import PosterIndexState
from studiohub.services.dashboard_metrics import DashboardMetrics
from studiohub.services.dashboard_metrics_adapter import (
    DashboardMetricsAdapter,
    PrintCountAdapter,
)
from studiohub.services.print_log_state import PrintLogState
from studiohub.services.notifications.notification_service import NotificationService

from studiohub.hub_models.missing_files_model_qt import MissingFilesModelQt
from studiohub.hub_models.print_manager_model_qt import PrintManagerModelQt
from studiohub.hub_models.mockup_generator_model_qt import MockupGeneratorModelQt
from studiohub.hub_models.index_log_model_qt import IndexLogModelQt
from studiohub.hub_models.print_job_config import PrintJobConfig


@dataclass
class Dependencies:
    """
    Container for application dependencies.
    
    This centralizes dependency creation and makes testing easier
    by allowing mock injection.
    """
    
    # Configuration
    config_manager: ConfigManager
    print_job_config: PrintJobConfig
    
    # Services
    paper_ledger: PaperLedger
    poster_index_state: PosterIndexState
    dashboard_metrics: DashboardMetrics
    dashboard_metrics_adapter: DashboardMetricsAdapter
    print_count_adapter: PrintCountAdapter
    print_log_state: PrintLogState
    notification_service: NotificationService
    
    # Models
    missing_model: MissingFilesModelQt
    print_manager_model: PrintManagerModelQt
    mockup_model: MockupGeneratorModelQt
    index_log_model: IndexLogModelQt


class DependencyContainer:
    """
    Factory for creating application dependencies.
    
    This class handles the complex initialization order and
    dependency wiring, keeping it separate from the UI code.
    """
    
    @staticmethod
    def create(parent: QtCore.QObject | None = None) -> Dependencies:
        """
        Create all application dependencies.
        
        Args:
            parent: Parent Qt object for memory management
            
        Returns:
            Fully initialized dependencies
        """
        # Configuration (first - others depend on it)
        config_manager = ConfigManager()
        print_job_config = PrintJobConfig.from_config(config_manager)
        
        # Services
        runtime_root = Path(config_manager.get("paths", "runtime_root", ""))
        if not runtime_root or not Path(runtime_root).exists():
            # Fallback for initial setup
            runtime_root = config_manager.get_appdata_root()
        else:
            runtime_root = Path(runtime_root)
            
        paper_ledger = PaperLedger(runtime_root)
        
        poster_index_state = PosterIndexState(parent)
        poster_index_state.load(config_manager.get_poster_index_path())
        
        print_log_state = PrintLogState(
            log_path=config_manager.get_print_log_path(),
            parent=parent,
        )
        
        # Load print log with error handling
        try:
            print_log_state.load()
        except Exception:
            pass  # Fail silently during initial setup
        
        dashboard_metrics = DashboardMetrics(
            print_log_path=config_manager.get_print_log_path(),
            paper_ledger=paper_ledger,
        )
        
        dashboard_metrics_adapter = DashboardMetricsAdapter(
            poster_index_state=poster_index_state,
            parent=parent,
        )
        
        print_count_adapter = PrintCountAdapter(
            print_log_state=print_log_state,
            poster_index_state=poster_index_state,
            parent=parent,
        )
        
        notification_service = NotificationService()
        
        # Models
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
        
        return Dependencies(
            config_manager=config_manager,
            print_job_config=print_job_config,
            paper_ledger=paper_ledger,
            poster_index_state=poster_index_state,
            dashboard_metrics=dashboard_metrics,
            dashboard_metrics_adapter=dashboard_metrics_adapter,
            print_count_adapter=print_count_adapter,
            print_log_state=print_log_state,
            notification_service=notification_service,
            missing_model=missing_model,
            print_manager_model=print_manager_model,
            mockup_model=mockup_model,
            index_log_model=index_log_model,
        )
