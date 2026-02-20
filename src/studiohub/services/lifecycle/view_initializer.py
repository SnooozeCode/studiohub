"""
View initialization and wiring.

Responsible for:
- constructing all Qt views
- wiring view <-> model signals
- keeping MainWindow clean
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6 import QtWidgets

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
        self._deps = deps
        self._parent = parent
        self._views: dict[str, QtWidgets.QWidget] = {}

    # ==================================================
    # View creation
    # ==================================================

    def create_views(self) -> dict[str, QtWidgets.QWidget]:
        """
        Create all application views.

        Returns:
            Dict of view_key -> QWidget
        """
        # -----------------------------
        # Imports (local to avoid cycles)
        # -----------------------------

        from studiohub.ui.dashboard.dashboard_view import DashboardView
        from studiohub.ui.views.print_manager_view_qt import PrintManagerViewQt
        from studiohub.ui.views.mockup_generator_view_qt import MockupGeneratorViewQt
        from studiohub.ui.views.missing_files_view_qt import MissingFilesViewQt
        from studiohub.ui.views.print_jobs_view_qt import PrintJobsViewQt
        from studiohub.ui.views.settings_view_qt import SettingsViewQt

        from studiohub.ui.views.print_economics_qt import PrintEconomicsViewQt

        # -----------------------------
        # Dashboard (NEW)
        # -----------------------------

        # Dashboard
        view_dashboard = DashboardView(
            dashboard_service=self._deps.dashboard_service,
            notes_store=self._deps.notes_store,
            media_service=self._deps.media_service,
            print_log_state=self._deps.print_log_state,
            parent=self._parent,
        )

        # -----------------------------
        # Print Manager
        # -----------------------------

        view_print_manager = PrintManagerViewQt(parent=self._parent)

        # -----------------------------
        # Mockup Generator
        # -----------------------------

        view_mockup = MockupGeneratorViewQt(parent=self._parent)
        view_mockup.bind_model(self._deps.mockup_model)

        # -----------------------------
        # Missing Files
        # -----------------------------

        view_missing = MissingFilesViewQt(parent=self._parent)

        # -----------------------------
        # Print Jobs
        # -----------------------------

        view_print_jobs = PrintJobsViewQt(
            config_manager=self._deps.config_manager,
            paper_ledger=self._deps.paper_ledger,
            print_manager_model=self._deps.print_manager_model,
            print_log_state=self._deps.print_log_state,
            parent=self._parent,
        )

        # -----------------------------
        # Settings
        # -----------------------------

        view_settings = SettingsViewQt(
            config_manager=self._deps.config_manager,
            paper_ledger=self._deps.paper_ledger,
            get_theme_tokens=lambda: {},  # injected later by main window
            parent=self._parent,
        )


        # -----------------------------
        # Print Economics
        # -----------------------------

        view_economics = PrintEconomicsViewQt(parent=self._parent)

        # -----------------------------
        # Registry
        # -----------------------------

        self._views = {
            "dashboard": view_dashboard,
            "print_manager": view_print_manager,
            "print_jobs": view_print_jobs,
            "mockup_generator": view_mockup,
            "missing_files": view_missing,
            "print_economics": view_economics,
            "settings": view_settings,
        }

        return self._views

    # ==================================================
    # Signal wiring
    # ==================================================

    def wire_signals(self) -> None:
        """
        Wire all view and model signals.
        """
        self._wire_mockup_generator()
        self._wire_print_manager()
        self._wire_missing_files()
        self._wire_settings()

        # NOTE:
        # Dashboard refresh is now SELF-CONTAINED
        # via DashboardView's internal timer.
        # No external wiring needed.

    # --------------------------------------------------
    # Dashboard
    # --------------------------------------------------
    # No wiring required anymore.
    # DashboardView pulls snapshots on its own.

    # --------------------------------------------------
    # Mockup Generator
    # --------------------------------------------------

    def _wire_mockup_generator(self) -> None:
        view = self._views["mockup_generator"]
        model = self._deps.mockup_model

        view.queue_add_requested.connect(model.add_to_queue)
        view.queue_remove_requested.connect(model.remove_from_queue)
        view.clear_queue_requested.connect(model.clear_queue)
        view.generate_requested.connect(model.generate_mockups)
        model.queue_changed.connect(view.set_queue)

    # --------------------------------------------------
    # Print Manager
    # --------------------------------------------------

    def _wire_print_manager(self) -> None:
        # Print manager wiring handled internally
        pass

    # --------------------------------------------------
    # Missing Files
    # --------------------------------------------------

    def _wire_missing_files(self) -> None:
        # Missing files wiring handled internally
        pass

    # --------------------------------------------------
    # Settings
    # --------------------------------------------------

    def _wire_settings(self) -> None:
        view = self._views["settings"]

        # Paper ledger updates affect settings view
        self._deps.paper_ledger.changed.connect(
            view.on_paper_ledger_changed
        )

    # ==================================================
    # Utilities
    # ==================================================

    def _on_index_log_error(self, message: str) -> None:
        """
        Handle index log errors.

        Currently no-op; could forward to status bar.
        """
        pass

    def set_theme_tokens_getter(self, getter) -> None:
        """
        Inject theme tokens getter for settings view.
        """
        view = self._views.get("settings")
        if view:
            view.get_theme_tokens = getter
