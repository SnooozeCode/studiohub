"""Main application window."""
from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt

from studiohub.constants import UIConstants, APP_VERSION
from studiohub.app.dependency_container import DependencyContainer, Dependencies
from studiohub.services.navigation.navigation_service import NavigationService
from studiohub.services.index.index_manager import IndexManager
from studiohub.services.lifecycle.startup_manager import StartupManager
from studiohub.services.lifecycle.view_initializer import ViewInitializer
from studiohub.ui.widgets.notifications_drawer import NotificationsDrawer
from studiohub.ui.widgets.click_catcher import ClickCatcher
from studiohub.ui.sidebar.sidebar import Sidebar
from studiohub.style import apply_style as apply_app_theme
from studiohub.style.typography.rules import apply_typography


class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window.
    
    Orchestrates the UI layout and coordinates between services.
    Significantly reduced from original 1,400+ lines.
    """
    
    theme_changed = QtCore.Signal(str)
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        # Initialize dependencies
        self._deps = DependencyContainer.create(parent=self)

        self.config_manager = self._deps.config_manager

        # Initialize services
        self._index_manager = IndexManager(
            config_manager=self._deps.config_manager,
            parent=self,
        )
        
        self._startup_manager = StartupManager(
            config_manager=self._deps.config_manager,
            parent_window=self,
        )
        
        # Theme state
        self._theme_name = self._deps.config_manager.get(
            "appearance", "theme", "dracula"
        )
        
        # Media worker process
        self._media_worker_proc: subprocess.Popen | None = None
        self._start_media_worker()
        
        # Dashboard loading state
        self._dash_loading: set[str] = set()
        
        # Setup UI
        self._setup_window()
        self._build_ui()
        
        # Finalize startup
        self._finalize_startup()
    
    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("SnooozeCo Studio Hub")
        self.resize(UIConstants.DEFAULT_WIDTH, UIConstants.DEFAULT_HEIGHT)
    
    def _build_ui(self) -> None:
        """Build the complete UI."""
        # Root layout
        root = QtWidgets.QWidget()
        root.setObjectName("Root")
        layout = QtWidgets.QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(root)
        
        # Sidebar
        self._sidebar = self._create_sidebar()
        layout.addWidget(self._sidebar)
        
        # View container
        self._stack = QtWidgets.QStackedWidget()
        view_container = self._create_view_container(self._stack)
        layout.addWidget(view_container, 1)
        
        # Initialize views
        view_init = ViewInitializer(self._deps, self)
        self._view_init = view_init  # Keep reference for theme tokens
        views = view_init.create_views()
        
        # Set theme tokens getter for settings view
        view_init.set_theme_tokens_getter(self._get_theme_tokens)
        
        # Wire signals
        view_init.wire_signals()
        
        # Add views to stack
        for view in views.values():
            self._stack.addWidget(view)
        
        # Navigation service
        self._navigation = NavigationService(self._stack, views, parent=self)
        self._register_navigation_hooks()
        self._wire_navigation_signals()
        
        # Notifications
        self._setup_notifications()
        
        # Apply theme
        self.apply_theme()
    
    def _create_sidebar(self) -> Sidebar:
        """Create and configure sidebar."""
        sidebar = Sidebar(width=UIConstants.SIDEBAR_WIDTH)
        
        # Connect signals
        sidebar.theme_toggle_requested.connect(self.toggle_theme)
        sidebar.refresh_requested.connect(self._refresh_all)
        sidebar.notifications_requested.connect(self._toggle_notifications)
        
        # Add navigation items
        sidebar.add_hub("dashboard", "Dashboard", 
                       lambda: self._navigation.show_view("dashboard"))
        
        sidebar.add_group("print_manager_group", "Printing", icon="print_manager")
        sidebar.add_group_item("print_manager_group", "print_manager", 
                              "Print Manager",
                              lambda: self._navigation.show_view("print_manager"))
        sidebar.add_group_item("print_manager_group", "print_jobs",
                              "Print Jobs Log",
                              lambda: self._navigation.show_view("print_jobs"))
        
        sidebar.add_hub("print_economics", "Production Costs",
                       lambda: self._navigation.show_view("print_economics"))
        sidebar.add_hub("mockup_generator", "Mockup Generator",
                       lambda: self._navigation.show_view("mockup_generator"))
        sidebar.add_hub("missing_files", "Missing Files",
                       lambda: self._navigation.show_view("missing_files"))
        
        sidebar.btn_settings.clicked.connect(
            lambda: self._navigation.show_view("settings")
        )
        
        sidebar.finalize()
        sidebar.set_logo(self._theme_name)
        
        return sidebar
    
    def _create_view_container(
        self,
        stack: QtWidgets.QStackedWidget
    ) -> QtWidgets.QFrame:
        """Create view container with status bar."""
        container = QtWidgets.QFrame()
        container.setObjectName("ViewContainer")
        
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        layout.addWidget(stack, 1)
        
        # Status bar
        status_bar = self._create_status_bar()
        layout.addWidget(status_bar)
        
        return container
    
    def _create_status_bar(self) -> QtWidgets.QFrame:
        """Create status bar."""
        status_bar = QtWidgets.QFrame()
        status_bar.setObjectName("ViewStatusBar")
        status_bar.setFixedHeight(UIConstants.STATUS_BAR_HEIGHT)
        
        layout = QtWidgets.QHBoxLayout(status_bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignVCenter)
        
        # Left status
        self._status_left = QtWidgets.QLabel("Ready")
        self._status_left.setObjectName("StatusText")
        apply_typography(self._status_left, "body-small")
        
        # Right version
        self._status_right = QtWidgets.QLabel(APP_VERSION)
        self._status_right.setObjectName("StatusVersion")
        apply_typography(self._status_right, "body-small")
        
        layout.addWidget(self._status_left)
        layout.addStretch(1)
        layout.addWidget(self._status_right)
        
        return status_bar
    
    def _setup_notifications(self) -> None:
        """Setup notifications drawer and overlay."""
        self._notifications_drawer = NotificationsDrawer(self)
        self._notifications_overlay = ClickCatcher(self)
        self._notifications_overlay.hide()
        
        # Seed with existing notifications
        for notification in self._deps.notification_service.all():
            self._notifications_drawer.add_notification(notification)
        
        # Connect signals
        self._deps.notification_service.add_listener(
            self._on_notification_received
        )
        self._notifications_overlay.clicked.connect(
            self._toggle_notifications
        )
        self.theme_changed.connect(
            lambda _: self._notifications_drawer.refresh_theme()
        )
    
    def _register_navigation_hooks(self) -> None:
        """Register view activation hooks."""
        nav = self._navigation
        
        nav.register_activation_hook("dashboard", self._on_dashboard_activated)
        nav.register_activation_hook("print_manager", self._on_print_manager_activated)
        nav.register_activation_hook("mockup_generator", self._on_mockup_activated)
        nav.register_activation_hook("missing_files", self._on_missing_files_activated)
        nav.register_activation_hook("print_jobs", self._on_print_jobs_activated)
        nav.register_activation_hook("index_log", self._on_index_log_activated)
    
    def _wire_navigation_signals(self) -> None:
        """Wire navigation-related signals."""
        # Update sidebar when view changes
        self._navigation.view_changed.connect(self._on_view_changed)
        
        # Dashboard replace paper signal
        dashboard = self._navigation.get_view("dashboard")
        if dashboard:
            dashboard.replace_paper_requested.connect(
                self._on_replace_paper_requested
            )

        dashboard.open_print_log_requested.connect(
            lambda: self._navigate_to("print_jobs")
        )

        # Index manager signals
        self._index_manager.index_started.connect(self._on_index_started)
        self._index_manager.index_finished.connect(self._on_index_finished)
        self._index_manager.index_error.connect(self._on_index_error)
        self._index_manager.poster_updated.connect(self._on_poster_updated)
        
        # Theme changed updates sidebar
        self.theme_changed.connect(self._sidebar._sidebar_on_theme_changed)

        print_view = self._navigation.get_view("print_manager")
        model = self._deps.print_manager_model

        if print_view:
            # model → view (already partially present)
            model.scan_finished.connect(print_view.set_data)
            model.queue_changed.connect(print_view.set_queue)
            model.last_batch_changed.connect(print_view.set_reprint_available)

            # 🔑 view → model (THIS WAS MISSING)
            print_view.queue_add_requested.connect(model.add_to_queue)
            print_view.queue_remove_requested.connect(model.remove_from_queue)
            print_view.queue_clear_requested.connect(model.clear_queue)
            print_view.send_requested.connect(model.send)
            print_view.reprint_requested.connect(model.reprint_last_batch)


        
        # Missing files wiring (model -> view, view -> model)
        missing_view = self._navigation.get_view("missing_files")
        if missing_view:
            mm = self._deps.missing_model

            # view -> model
            missing_view.refresh_requested.connect(mm.refresh)

            # model -> view
            mm.scan_started.connect(lambda src: missing_view.set_loading(src, "Scanning..."))
            mm.scan_finished.connect(missing_view.set_data)
            mm.scan_error.connect(missing_view.set_error)

            # theme changes
            self.theme_changed.connect(missing_view.on_theme_changed)

    
    def _finalize_startup(self) -> None:
        """Complete application startup."""
        # Validate paths
        is_valid = self._startup_manager.validate_required_paths(
            on_incomplete=self._on_setup_incomplete
        )

        # Start index build on startup
        self._index_manager.start_full_index()
        self._sidebar.set_refresh_enabled(False)
        self._dash_loading = {"archive", "studio"}
        self.set_status("Building index...", decay_ms=None)

        
        if not is_valid:
            QtCore.QTimer.singleShot(0, lambda: self._navigation.show_view("settings"))
            return
        
        # Load index
        index = self._index_manager.load_index()
        self._apply_loaded_index(index)
        
        # Start file watcher
        self._index_manager.start_file_watcher()
        
        # Show dashboard
        QtCore.QTimer.singleShot(0, lambda: self._navigation.show_view("dashboard"))

    
    def _on_setup_incomplete(self, missing: list[str]) -> None:
        """Handle incomplete setup."""
        settings_view = self._navigation.get_view("settings")
        if settings_view and hasattr(settings_view, "highlight_missing_paths"):
            settings_view.highlight_missing_paths(missing)
    
    def _get_theme_tokens(self) -> dict:
        """Get current theme tokens."""
        manager = getattr(self, "theme_manager", None)
        if not manager or not getattr(manager, "current_theme", None):
            return {}
        return manager.current_theme.tokens
    
    # --------------------------------------------------
    # Theme Management
    # --------------------------------------------------
    
    def apply_theme(self) -> None:
        """Apply current theme to application."""
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        apply_app_theme(app, theme_name=self._theme_name, root=self)
    
    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self._theme_name = (
            "alucard" if self._theme_name == "dracula" else "dracula"
        )
        self._deps.config_manager.set("appearance", "theme", self._theme_name)
        self.apply_theme()
        
        self._sidebar.set_logo(self._theme_name)
        self.theme_changed.emit(self._theme_name)
        
        label = "Dracula" if self._theme_name == "dracula" else "Alucard"
        self.set_status(f"Theme switched to {label}", 
                       decay_ms=UIConstants.STATUS_DECAY_MS)
    
    # --------------------------------------------------
    # Status Bar
    # --------------------------------------------------
    
    def set_status(
        self,
        text: str,
        *,
        decay_ms: int | None = UIConstants.STATUS_DECAY_MS,
        timestamp: bool = False,
    ) -> None:
        """Set status bar text."""
        if timestamp:
            ts = datetime.now().strftime("%H:%M:%S")
            text = f"{text} • {ts}"
        
        self._status_left.setText(text)
        
        if decay_ms is not None:
            QtCore.QTimer.singleShot(decay_ms, 
                                    lambda: self._status_left.setText("Ready"))
    
    # --------------------------------------------------
    # Notifications
    # --------------------------------------------------
    
    def _toggle_notifications(self) -> None:
        """Toggle notifications drawer open/closed."""
        drawer = self._notifications_drawer
        overlay = self._notifications_overlay
        
        win_rect = self.rect()
        drawer_width = drawer.width()
        full_height = win_rect.height()
        
        closed_geo = QtCore.QRect(
            win_rect.width(),
            0,
            drawer_width,
            full_height,
        )
        
        open_geo = QtCore.QRect(
            win_rect.width() - drawer_width,
            0,
            drawer_width,
            full_height,
        )
        
        drawer.setFixedHeight(full_height)
        
        if drawer.is_open:
            # Close
            drawer._anim.stop()
            drawer._anim.setStartValue(drawer.geometry())
            drawer._anim.setEndValue(closed_geo)
            drawer._anim.start()
            
            overlay.hide()
            drawer.is_open = False
        else:
            # Open
            overlay.setGeometry(
                0,
                0,
                win_rect.width() - drawer_width,
                full_height,
            )
            overlay.show()
            overlay.raise_()
            
            drawer.setGeometry(closed_geo)
            drawer.show()
            drawer.raise_()
            
            drawer._anim.stop()
            drawer._anim.setStartValue(closed_geo)
            drawer._anim.setEndValue(open_geo)
            drawer._anim.start()
            
            drawer.is_open = True
    
    def _on_notification_received(self, notification) -> None:
        """Handle new notification."""
        self._notifications_drawer.add_notification(notification)
        btn = self._sidebar._notifications_button
        btn.set_badge_count(btn.badge_count + 1)
    
    # --------------------------------------------------
    # Navigation Hooks
    # --------------------------------------------------
    
    def _on_view_changed(self, view_key: str) -> None:
        """Handle view change."""
        self._sidebar.activate(view_key)
        self.set_status(view_key.replace("_", " ").title(), 
                       decay_ms=UIConstants.STATUS_DECAY_MS)
    
    def _on_dashboard_activated(self) -> None:
        """Handle dashboard activation."""
        self._refresh_dashboard_from_current_state()
        dashboard = self._navigation.get_view("dashboard")
        if dashboard:
            dashboard.set_loading("archive", "archive" in self._dash_loading)
            dashboard.set_loading("studio", "studio" in self._dash_loading)
    
    def _on_print_manager_activated(self) -> None:
        """Handle print manager activation."""
        for src in ("archive", "studio"):
            self._deps.print_manager_model.refresh(src)
    
    def _on_mockup_activated(self) -> None:
        """Handle mockup generator activation."""
        for src in ("archive", "studio"):
            try:
                self._deps.mockup_model.load_from_index(src)
            except Exception:
                pass
        
        queue = self._deps.mockup_model.get_queue()
        if queue is not None:
            mockup_view = self._navigation.get_view("mockup_generator")
            if mockup_view:
                mockup_view.set_queue(queue)
    
    def _on_missing_files_activated(self) -> None:
        try:
            missing_view = self._navigation.get_view("missing_files")
            if not missing_view:
                return

            # ensure index is current
            index = self._index_manager.load_index()
            missing_view.set_index(index)

            # let the view request refresh (wired to model.refresh)
            missing_view.on_activated()

        except Exception:
            pass


    def _on_print_jobs_activated(self) -> None:
        """Handle print jobs activation."""
        try:
            self._deps.print_log_state.load()
        except Exception:
            pass
    
    def _on_index_log_activated(self) -> None:
        """Handle index log activation."""
        self._deps.index_log_model.load()
    
    def _on_replace_paper_requested(self, name: str, total_ft: float) -> None:
        """Handle replace paper request."""
        self._deps.paper_ledger.replace_paper(name, total_ft)
    
    # --------------------------------------------------
    # Index Management
    # --------------------------------------------------
    
    def _refresh_all(self) -> None:
        """Refresh all data (triggered by sidebar button)."""
        self._index_manager.start_full_index()
        self._sidebar.set_refresh_enabled(False)
        self._dash_loading = {"archive", "studio"}
        self.set_status("Refreshing index...", decay_ms=None)
    
    def _on_index_started(self) -> None:
        """Handle index start."""
        self.set_status("Building index...", decay_ms=None)
    
    def _on_index_finished(self, duration_ms: int, status: str) -> None:
        """Handle index completion."""
        self._sidebar.set_refresh_enabled(True)
        self._dash_loading.clear()
        
        # Reload index and apply to models
        index = self._index_manager.load_index()
        self._apply_loaded_index(index)
        
        # Refresh active view
        active = self._navigation.active_view
        if active == "dashboard":
            self._refresh_dashboard_from_current_state()
            dashboard = self._navigation.get_view("dashboard")
            if dashboard:
                dashboard.set_loading("archive", False)
                dashboard.set_loading("studio", False)
        
        self.set_status("Index ready", timestamp=True, 
                       decay_ms=UIConstants.STATUS_DECAY_MS)
    
    def _on_index_error(self, message: str) -> None:
        """Handle index error."""
        self._sidebar.set_refresh_enabled(True)
        self._dash_loading.clear()
        self.set_status("Index failed", timestamp=True,
                       decay_ms=UIConstants.STATUS_DECAY_MS)
        QtWidgets.QMessageBox.critical(self, "Index Error", message)
    
    def _on_poster_updated(self, poster_key: str) -> None:
        """Handle incremental poster update."""
        index = self._index_manager.load_index()
        self._apply_loaded_index(index)
        
        if self._navigation.active_view == "dashboard":
            self._refresh_dashboard_from_current_state()
    
    def _apply_loaded_index(self, index: dict) -> None:
        """Apply loaded index to all models."""
        for src in ("archive", "studio"):
            self._deps.print_manager_model.refresh(src)
            self._deps.mockup_model.load_from_index(src)
            self._deps.missing_model.refresh(src)
        
        missing_view = self._navigation.get_view("missing_files")
        if missing_view:
            missing_view.set_index(index)
    
    def _refresh_dashboard_from_current_state(self) -> None:
        """Refresh dashboard with current state."""
        dashboard = self._navigation.get_view("dashboard")
        if dashboard:
            dashboard.refresh()
    
    # --------------------------------------------------
    # Media Worker Management
    # --------------------------------------------------
    
    def _start_media_worker(self) -> None:
        """Start the media worker subprocess."""
        try:
            import psutil
        except ImportError:
            return  # Can't manage worker without psutil
        
        media_dir = (
            Path(os.getenv("APPDATA", Path.home()))
            / "SnooozeCo"
            / "StudioHub"
            / "media"
        )
        media_dir.mkdir(parents=True, exist_ok=True)
        
        pid_path = media_dir / "media_worker.pid"
        log_path = media_dir / "media_worker.log"
        
        # Check for existing worker
        if pid_path.exists():
            try:
                pid = int(pid_path.read_text(encoding="utf-8").strip())
                if psutil.pid_exists(pid):
                    return  # Worker already running
            except Exception:
                pass
            
            # Clean up stale PID
            try:
                pid_path.unlink(missing_ok=True)
            except Exception:
                pass
        
        # Find worker script
        root = Path(__file__).resolve().parent.parent
        worker_path = root / "services" / "media_worker" / "media_worker.py"
        worker_python = root / "services" / "media_worker" / "venv311" / "Scripts" / "python.exe"
        
        if not worker_path.exists():
            return  # No worker available
        
        # Use venv python if available, otherwise system python
        python_exe = str(worker_python) if worker_python.exists() else "python"
        
        # Launch worker
        try:
            with open(log_path, "w") as log_file:
                self._media_worker_proc = subprocess.Popen(
                    [python_exe, str(worker_path)],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
        except Exception:
            pass  # Fail silently
    
    # --------------------------------------------------
    # Event Handlers
    # --------------------------------------------------
    
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Handle window resize."""
        super().resizeEvent(event)
        
        # Reposition notifications if open
        if self._notifications_drawer.is_open:
            win_rect = self.rect()
            drawer_width = self._notifications_drawer.width()
            
            self._notifications_drawer.setGeometry(
                win_rect.width() - drawer_width,
                0,
                drawer_width,
                win_rect.height(),
            )
            
            self._notifications_overlay.setGeometry(
                0,
                0,
                win_rect.width() - drawer_width,
                win_rect.height(),
            )
    
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle key press events."""
        # ESC closes notifications
        if (event.key() == Qt.Key_Escape and 
            self._notifications_drawer.is_open):
            self._toggle_notifications()
            event.accept()
            return
        
        super().keyPressEvent(event)
