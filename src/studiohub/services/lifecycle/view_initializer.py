"""View initialization and wiring."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6 import QtCore, QtWidgets

if TYPE_CHECKING:
    from studiohub.app.dependency_container import Dependencies


class ViewInitializer:
    """
    Handles view creation and signal wiring.
    
    Separates complex view setup from the main window class.
    """
    
    def __init__(
        self,
        deps: Dependencies,
        parent: QtWidgets.QWidget,
    ):
        """
        Initialize view initializer.
        
        Args:
            deps: Application dependencies
            parent: Parent widget
        """
        self._deps = deps
        self._parent = parent
        self._views: dict[str, QtWidgets.QWidget] = {}
    
    def create_views(self) -> dict[str, QtWidgets.QWidget]:
        """
        Create all application views.
        
        Returns:
            Dictionary of view_key -> widget
        """
        from studiohub.ui.views.dashboard_view_qt import DashboardViewQt
        from studiohub.ui.views.print_manager_view_qt import PrintManagerViewQt
        from studiohub.ui.views.mockup_generator_view_qt import MockupGeneratorViewQt
        from studiohub.ui.views.missing_files_view_qt import MissingFilesViewQt
        from studiohub.ui.views.print_jobs_view_qt import PrintJobsViewQt
        from studiohub.ui.views.settings_view_qt import SettingsViewQt
        from studiohub.ui.views.index_log_view_qt import IndexLogViewQt
        from studiohub.ui.views.print_economics_qt import PrintEconomicsViewQt
        
        # Dashboard
        view_dashboard = DashboardViewQt(
            dashboard_metrics_adapter=self._deps.dashboard_metrics_adapter,
            print_count_adapter=self._deps.print_count_adapter,
            parent=self._parent,
        )
        view_dashboard.config_manager = self._deps.config_manager
        view_dashboard.set_metrics(self._deps.dashboard_metrics)
        
        # Print Manager
        view_print_manager = PrintManagerViewQt(parent=self._parent)
        
        # Mockup Generator
        view_mockup = MockupGeneratorViewQt(parent=self._parent)
        view_mockup.bind_model(self._deps.mockup_model)
        
        # Missing Files
        view_missing = MissingFilesViewQt(parent=self._parent)
        
        # Print Jobs
        view_print_jobs = PrintJobsViewQt(
            config_manager=self._deps.config_manager,
            paper_ledger=self._deps.paper_ledger,
            print_manager_model=self._deps.print_manager_model,
            print_log_state=self._deps.print_log_state,
            parent=self._parent,
        )
        
        # Settings (with placeholder for theme tokens getter)
        view_settings = SettingsViewQt(
            config_manager=self._deps.config_manager,
            paper_ledger=self._deps.paper_ledger,
            get_theme_tokens=lambda: {},  # Will be set by main window
            parent=self._parent,
        )
        
        # Index Log
        view_index_log = IndexLogViewQt(parent=self._parent)
        
        # Print Economics
        view_economics = PrintEconomicsViewQt(parent=self._parent)
        
        self._views = {
            "dashboard": view_dashboard,
            "print_manager": view_print_manager,
            "print_jobs": view_print_jobs,
            "mockup_generator": view_mockup,
            "missing_files": view_missing,
            "print_economics": view_economics,
            "settings": view_settings,
            "index_log": view_index_log,
        }
        
        return self._views
    
    def wire_signals(self) -> None:
        """Wire all view and model signals."""
        self._wire_dashboard()
        self._wire_mockup_generator()
        self._wire_print_manager()
        self._wire_missing_files()
        self._wire_settings()
        self._wire_index_log()
    
    def _wire_dashboard(self) -> None:
        """Wire dashboard-specific signals."""
        view = self._views["dashboard"]
        
        # Dashboard adapter changes trigger refresh
        self._deps.dashboard_metrics_adapter.changed.connect(
            lambda: view._refresh_dashboard(
                self._deps.dashboard_metrics_adapter.snapshot
            )
        )
        
        # Print log updates trigger dashboard refresh
        self._deps.print_manager_model.print_log_updated.connect(
            lambda: self._refresh_dashboard_callback()
        )
        
        # Paper ledger updates trigger dashboard refresh
        self._deps.paper_ledger.changed.connect(
            lambda: self._refresh_dashboard_callback()
        )
    
    def _wire_mockup_generator(self) -> None:
        """Wire mockup generator signals."""
        view = self._views["mockup_generator"]
        model = self._deps.mockup_model
        
        view.queue_add_requested.connect(model.add_to_queue)
        view.queue_remove_requested.connect(model.remove_from_queue)
        view.clear_queue_requested.connect(model.clear_queue)
        view.generate_requested.connect(model.generate_mockups)
        model.queue_changed.connect(view.set_queue)
    
    def _wire_print_manager(self) -> None:
        """Wire print manager signals."""
        # Print manager model signals are wired internally
        pass
    
    def _wire_missing_files(self) -> None:
        """Wire missing files signals."""
        # Missing files signals are wired internally
        pass
    
    def _wire_settings(self) -> None:
        """Wire settings signals."""
        view = self._views["settings"]
        
        # Paper ledger changes update settings view
        self._deps.paper_ledger.changed.connect(
            view.on_paper_ledger_changed
        )
    
    def _wire_index_log(self) -> None:
        """Wire index log signals."""
        view = self._views["index_log"]
        model = self._deps.index_log_model
        
        model.data_loaded.connect(view.set_rows)
        model.error.connect(self._on_index_log_error)
    
    def _refresh_dashboard_callback(self) -> None:
        """Centralized dashboard refresh hook."""
        view = self._views.get("dashboard")
        if view and hasattr(view, "_refresh_dashboard"):
            view._refresh_dashboard()
    
    def _on_index_log_error(self, message: str) -> None:
        """Handle index log errors."""
        # Could emit signal to main window for status bar update
        pass
    
    def set_theme_tokens_getter(self, getter) -> None:
        """
        Set the theme tokens getter for settings view.
        
        Args:
            getter: Callable that returns theme tokens dict
        """
        view = self._views.get("settings")
        if view:
            view.get_theme_tokens = getter
