# FILE: C:\Users\snooo\Desktop\src\studiohub\src\studiohub\app\main_window.py

"""Main application window."""
from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, Slot


from studiohub.app.dependency_container import DependencyContainer, Dependencies
from studiohub.constants import UIConstants, APP_VERSION
from studiohub.services.navigation.navigation_service import NavigationService
from studiohub.services.index.index_manager import IndexManager
from studiohub.services.lifecycle.startup_manager import StartupManager
from studiohub.services.lifecycle.view_initializer import ViewInitializer
from studiohub.services.media.runner import start_media_worker
from studiohub.style import apply_style as apply_app_theme
from studiohub.style.typography.rules import apply_typography
from studiohub.ui.widgets.notifications_drawer import NotificationsDrawer
from studiohub.ui.widgets.click_catcher import ClickCatcher
from studiohub.ui.sidebar.sidebar import Sidebar

from studiohub.services.notifications.notification_service import Notification, NotificationAction


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
        
        self._status_callback = self._safe_emit_status
        
        # Initialize dependencies
        self._deps = DependencyContainer.create(parent=self)

        self.config_manager = self._deps.config_manager

        # Initialize services
        self._index_manager = IndexManager(
            config_manager=self._deps.config_manager,
            status_callback=self._safe_emit_status,
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
        
        # Track which notifications have been shown
        self._shown_notifications: set[str] = set()
        
        # Setup UI
        self._setup_window()
        self._build_ui()
        
        # Connect model status signals to status bar and notifications
        self._connect_model_status_signals()
        self._connect_status_to_notifications()
        
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
    
    # =====================================================
    # Status Bar Helpers
    # =====================================================
    
    @Slot(str)
    def _safe_emit_status(self, message: str, decay_ms: int | None = UIConstants.STATUS_DECAY_MS):
        """Safely emit a status message if the status bar exists."""
        try:
            if hasattr(self, '_status_left') and self._status_left:
                self.set_status(message, decay_ms=decay_ms)
            else:
                print(f"[Status] {message}")  # Fallback to console
        except Exception as e:
            print(f"[ERROR] Failed to emit status '{message}': {e}")

    def _connect_model_status_signals(self):
        """Connect all model status signals to the status bar."""
        try:
            # Missing files model
            if hasattr(self._deps.missing_model, 'status_message'):
                self._deps.missing_model.status_message.connect(self._safe_emit_status)
            
            # Print manager model
            if hasattr(self._deps.print_manager_model, 'status_message'):
                self._deps.print_manager_model.status_message.connect(self._safe_emit_status)
            
            # Mockup model
            if hasattr(self._deps.mockup_model, 'status_message'):
                self._deps.mockup_model.status_message.connect(self._safe_emit_status)
            
            # Print log state
            if hasattr(self._deps.print_log_state, 'status_message'):
                self._deps.print_log_state.status_message.connect(self._safe_emit_status)
            
            # Index manager
            if hasattr(self._index_manager, 'status_message'):
                self._index_manager.status_message.connect(self._safe_emit_status)
            
            # Paper ledger - MAKE SURE THIS IS CONNECTED
            if hasattr(self._deps.paper_ledger, 'status_message'):
                self._deps.paper_ledger.status_message.connect(self._safe_emit_status)
                
            print("[MainWindow] Connected model status signals")
            
        except Exception as e:
            print(f"[WARN] Failed to connect model status signals: {e}")
    
    def _connect_status_to_notifications(self):
        """Convert status messages to notifications (errors, warnings, successes)."""
        sources = [
            self._deps.missing_model,
            self._deps.print_manager_model,
            self._deps.mockup_model,
            self._deps.print_log_state,
            self._index_manager,
            self._deps.paper_ledger,
        ]
        
        # Add media runner if it exists
        if hasattr(self, '_media_runner'):
            sources.append(self._media_runner)
        
        for source in sources:
            if source and hasattr(source, 'status_message'):
                # Connect to notification filter
                try:
                    source.status_message.connect(self._filter_status_for_notification)
                except Exception as e:
                    print(f"[MainWindow] Failed to connect status for {source}: {e}")
    
    @Slot(str)
    def _filter_status_for_notification(self, message: str):
        """Filter status messages and convert to notifications."""
        # Always show in status bar
        self._safe_emit_status(message)
        
        # Check if this message should become a notification
        if self._should_be_notification(message):
            self._create_notification_from_status(message)
    
    def _should_be_notification(self, message: str) -> bool:
        """Determine if a status message should become a notification."""
        error_indicators = [
            "failed", "error", "unavailable", "cannot", "invalid",
            "missing", "not found", "crash", "warning"
        ]
        success_indicators = [
            "ready", "finished", "completed", "success", "started",
            "loaded", "updated", "refreshed", "saved", "replaced"
        ]
        msg_lower = message.lower()
        
        # Check for errors first
        if any(indicator in msg_lower for indicator in error_indicators):
            return True
        
        # Check for significant successes
        if any(indicator in msg_lower for indicator in success_indicators):
            # Filter out trivial messages
            trivial = ["status", "click", "hover", "theme"]
            if not any(t in msg_lower for t in trivial):
                return True
        
        return False
    
    def _create_notification_from_status(self, message: str):
        """Create a notification from a status message."""
        import hashlib
        
        # Generate a stable key from the message
        key = hashlib.md5(message.encode()).hexdigest()[:8]
        
        # Don't show duplicate notifications too frequently
        if key in self._shown_notifications:
            return
        
        self._shown_notifications.add(key)
        
        # Clear from shown set after a while to allow repeats
        QtCore.QTimer.singleShot(60000, lambda: self._shown_notifications.discard(key))
        
        # Parse message to determine title, level, and actions
        title, details, level, actions = self._parse_notification_details(message)
        
        # Determine auto-dismiss (warnings dismiss, errors persist, successes dismiss quickly)
        auto_dismiss = None
        if level == "warning":
            auto_dismiss = 60
        elif level == "success":
            auto_dismiss = 30  # Success notifications auto-dismiss after 30 seconds
        elif level == "info":
            auto_dismiss = 20  # Info notifications auto-dismiss after 20 seconds
        
        notification = Notification(
            key=f"status_{key}",
            level=level,
            title=title,
            message=details,
            timestamp=datetime.now(),
            actions=actions,
            auto_dismiss_seconds=auto_dismiss,
        )
        
        self._deps.notification_service.emit(notification)
    

    def _parse_notification_details(self, message: str) -> tuple[str, str, str, list]:
        """Parse status message into title, details, level, and actions."""
        actions = []
        msg_lower = message.lower()
        
        # ============ ERROR CASES ============
        if "Media service unavailable" in message:
            return (
                "Media Service Failed",
                "The media playback service is unavailable. System media controls may not work.",
                "error",
                self._create_actions_for_message(message)
            )
        
        if "Index failed" in message:
            return (
                "Index Build Failed",
                message,
                "error",
                self._create_actions_for_message(message)
            )
        
        if "Failed to load print log" in message:
            return (
                "Print Log Error",
                message,
                "error",
                self._create_actions_for_message(message)
            )
        
        if "File watcher failed" in message:
            return (
                "File Watching Disabled",
                "Automatic updates are disabled. Use refresh button to update.",
                "warning",
                self._create_actions_for_message(message)
            )
        
        if "missing required paths" in msg_lower or "setup incomplete" in msg_lower:
            return (
                "Setup Required",
                "Some required paths are not configured.",
                "warning",
                self._create_actions_for_message(message)
            )
        
        # ============ SUCCESS CASES ============
        if "settings saved" in msg_lower:
            return (
                "Settings Saved",
                "Your configuration changes have been applied.",
                "success",
                [
                    NotificationAction(
                        label="Dismiss",
                        callback=lambda: None,
                        icon="close"
                    )
                ]
            )
        
        if "paper replaced" in msg_lower:
            # Extract paper name and length if possible
            import re
            match = re.search(r"Paper replaced: (.*?) \((\d+\.?\d*) ft\)", message)
            if match:
                paper_name, length = match.groups()
                return (
                    "Paper Roll Replaced",
                    f"New roll installed: {paper_name} ({length} ft)",
                    "success",
                    [
                        NotificationAction(
                            label="View Paper Status",
                            callback=lambda: self._navigation.show_view("settings"),
                            icon="settings"
                        ),
                        NotificationAction(
                            label="Dismiss",
                            callback=lambda: None,
                            icon="close"
                        )
                    ]
                )
            return (
                "Paper Roll Replaced",
                message,
                "success",
                [
                    NotificationAction(
                        label="View Settings",
                        callback=lambda: self._navigation.show_view("settings"),
                        icon="settings"
                    ),
                    NotificationAction(
                        label="Dismiss",
                        callback=lambda: None,
                        icon="close"
                    )
                ]
            )
        
        if "index ready" in msg_lower or "index finished" in msg_lower:
            return (
                "Index Built Successfully",
                "Poster index has been updated and is ready to use.",
                "success",
                [
                    NotificationAction(
                        label="View Dashboard",
                        callback=lambda: self._navigation.show_view("dashboard"),
                        icon="dashboard"
                    ),
                    NotificationAction(
                        label="Dismiss",
                        callback=lambda: None,
                        icon="close"
                    )
                ]
            )
        
        if "media worker thread started" in msg_lower or "media worker started" in msg_lower:
            return (
                "Media Service Ready",
                "Media playback detection is now active.",
                "success",
                [
                    NotificationAction(
                        label="Dismiss",
                        callback=lambda: None,
                        icon="close"
                    )
                ]
            )
        
        if "file watcher started" in msg_lower:
            return (
                "File Watching Active",
                "Poster files will be automatically monitored for changes.",
                "success",
                [
                    NotificationAction(
                        label="Dismiss",
                        callback=lambda: None,
                        icon="close"
                    )
                ]
            )
        
        if "print log loaded" in msg_lower or "print log updated" in msg_lower:
            return (
                "Print Log Updated",
                "Print job history has been refreshed.",
                "info",
                [
                    NotificationAction(
                        label="View Print Log",
                        callback=lambda: self._navigation.show_view("print_jobs"),
                        icon="print_manager"
                    ),
                    NotificationAction(
                        label="Dismiss",
                        callback=lambda: None,
                        icon="close"
                    )
                ]
            )
        
        if "refreshing" in msg_lower and any(src in msg_lower for src in ["archive", "studio"]):
            return (
                "Scan Started",
                message,
                "info",
                [
                    NotificationAction(
                        label="Dismiss",
                        callback=lambda: None,
                        icon="close"
                    )
                ]
            )
        
        # ============ DEFAULT CASES ============
        # Determine level based on message content
        level = "info"
        if "error" in msg_lower or "failed" in msg_lower:
            level = "error"
        elif "warning" in msg_lower:
            level = "warning"
        elif "success" in msg_lower or "ready" in msg_lower or "finished" in msg_lower:
            level = "success"
        
        # Default title and actions
        title = message[:50] + "..." if len(message) > 50 else message
        
        # Add appropriate actions based on level
        if level == "error":
            actions = self._create_actions_for_message(message)
        else:
            actions = [
                NotificationAction(
                    label="Dismiss",
                    callback=lambda: None,
                    icon="close"
                )
            ]
        
        return title, message, level, actions
    
    def _create_actions_for_message(self, message: str) -> list:
        """Create notification actions based on message type."""
        actions = []
        msg_lower = message.lower()
        
        # Retry action for index failures
        if "Index failed" in message or "index" in msg_lower:
            actions.append(NotificationAction(
                label="Retry Index",
                callback=lambda: self._index_manager.start_full_index(),
                icon="refresh"
            ))
        
        # Configure action for missing paths
        if "missing required paths" in msg_lower or "setup incomplete" in msg_lower:
            actions.append(NotificationAction(
                label="Configure Paths",
                callback=lambda: self._navigation.show_view("settings"),
                icon="settings"
            ))
        
        # Retry action for media service
        if "Media service" in message:
            actions.append(NotificationAction(
                label="Restart Media",
                callback=self._restart_media_worker,
                icon="refresh"
            ))
        
        # View log action for print log errors
        if "print log" in msg_lower:
            actions.append(NotificationAction(
                label="View Print Log",
                callback=lambda: self._navigation.show_view("print_jobs"),
                icon="print_manager"
            ))
        
        # Always add dismiss action
        actions.append(NotificationAction(
            label="Dismiss",
            callback=lambda: None,
            icon="close"
        ))
        
        return actions
    
    def _restart_media_worker(self):
        """Restart the media worker service."""
        self._safe_emit_status("Restarting media service...")
        
        # Stop existing runner
        if hasattr(self, '_media_runner'):
            self._media_runner.stop()
        
        # Start new one
        self._start_media_worker()
    
    # =====================================================
    # UI Creation
    # =====================================================
    
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
        try:
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
            
            # Mark as successfully initialized
            self._notifications_available = True
            
        except Exception as e:
            self._safe_emit_status(f"Notifications unavailable: {str(e)[:30]}")
            self._notifications_available = False
            self._notifications_drawer = None
            self._notifications_overlay = None
    
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

            # FIXED: Use the correct signals from DashboardView
            dashboard.new_print_job_requested.connect(
                lambda: self._navigation.show_view("print_manager")
            )
            dashboard.open_print_log_requested.connect(
                lambda: self._navigation.show_view("print_jobs")
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
            model.scan_finished.connect(print_view.set_data)
            model.queue_changed.connect(print_view.set_queue)
            model.last_batch_changed.connect(print_view.set_reprint_available)
            print_view.queue_add_requested.connect(model.add_to_queue)
            print_view.queue_remove_requested.connect(model.remove_from_queue)
            print_view.queue_clear_requested.connect(model.clear_queue)
            print_view.send_requested.connect(model.send)
            print_view.reprint_requested.connect(model.reprint_last_batch)

        # Missing files wiring
        missing_view = self._navigation.get_view("missing_files")
        if missing_view:
            mm = self._deps.missing_model
            missing_view.refresh_requested.connect(mm.refresh)
            mm.scan_started.connect(lambda src: missing_view.set_loading(src, "Scanning..."))
            mm.scan_finished.connect(missing_view.set_data)
            mm.scan_error.connect(missing_view.set_error)
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
            self._safe_emit_status("Setup incomplete - please configure paths")
            QtCore.QTimer.singleShot(0, lambda: self._navigation.show_view("settings"))
            return
        
        # Load index
        index = self._index_manager.load_index()
        self._apply_loaded_index(index)
        
        # Start file watcher
        try:
            self._index_manager.start_file_watcher()
        except Exception as e:
            self._safe_emit_status("File watching unavailable - manual refresh only", decay_ms=4000)
                
        # Show dashboard
        QtCore.QTimer.singleShot(0, lambda: self._navigation.show_view("dashboard"))
        
        # Set initial theme tokens for dashboard
        QtCore.QTimer.singleShot(100, self._update_dashboard_theme)

    
    def _on_setup_incomplete(self, missing: list[str]) -> None:
        """Handle incomplete setup."""
        self._safe_emit_status(f"Missing {len(missing)} required paths")
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
    
    def _update_dashboard_theme(self):
        """Update dashboard with current theme tokens."""
        dashboard = self._navigation.get_view("dashboard")
        if dashboard and hasattr(dashboard, 'set_theme_tokens'):
            tokens = self._get_theme_tokens()
            dashboard.set_theme_tokens(tokens)

    def apply_theme(self) -> None:
        """Apply current theme to application."""
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        apply_app_theme(app, theme_name=self._theme_name, root=self)
        
        # Update dashboard with new theme tokens
        self._update_dashboard_theme()

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
        # Safety check - if drawer failed to initialize, do nothing
        if not hasattr(self, '_notifications_available') or not self._notifications_available:
            print("[MainWindow] Notifications drawer not available")
            return
            
        if not self._notifications_drawer or not self._notifications_overlay:
            return
            
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
        # Safety check
        if not hasattr(self, '_notifications_available') or not self._notifications_available:
            return
            
        if not self._notifications_drawer or not self._sidebar:
            return
        
        # None indicates removal - handled separately
        if notification is None:
            return
            
        self._notifications_drawer.add_notification(notification)
        btn = self._sidebar._notifications_button
        if btn:  # Check if button exists
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
        self._safe_emit_status("Refreshing print manager...")
        for src in ("archive", "studio"):
            self._deps.print_manager_model.refresh(src)
    
    def _on_mockup_activated(self) -> None:
        """Handle mockup generator activation."""
        for src in ("archive", "studio"):
            try:
                self._deps.mockup_model.load_from_index(src)
            except Exception as e:
                self._safe_emit_status(f"Failed to load mockup data for {src}: {str(e)[:30]}")
                
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

        except Exception as e:
            self._safe_emit_status(f"Error activating missing files: {str(e)[:40]}")


    def _on_print_jobs_activated(self) -> None:
        """Handle print jobs activation."""
        try:
            self._deps.print_log_state.load()
        except Exception as e:
            self._safe_emit_status(f"Failed to reload print log: {str(e)[:40]}")
    
    def _on_index_log_activated(self) -> None:
        """Handle index log activation."""
        self._deps.index_log_model.load()
    
    def _on_replace_paper_requested(self, name: str, total_ft: float) -> None:
        """Handle replace paper request."""
        self._deps.paper_ledger.replace_paper(name, total_ft)
        message = f"Paper replaced: {name} ({total_ft} ft)"
        self._safe_emit_status(message)
        # This will trigger a success notification with the paper replaced message
    
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
        
        message = f"Index ready in {duration_ms}ms"
        self.set_status(message, timestamp=True, 
                       decay_ms=UIConstants.STATUS_DECAY_MS)
        
        # This will trigger a success notification via _filter_status_for_notification
        self._safe_emit_status(f"Index finished - {duration_ms}ms")
    
    def _on_index_error(self, message: str) -> None:
        """Handle index error."""
        self._sidebar.set_refresh_enabled(True)
        self._dash_loading.clear()
        self._safe_emit_status(f"Index failed: {message[:50]}", decay_ms=5000)
        
        # This will be caught by _filter_status_for_notification and become a notification
        # with Retry button
    
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
        """Start the media worker in a background thread."""
        try:
            self._media_runner = start_media_worker(self.config_manager, self)
            self._media_runner.status_message.connect(self._safe_emit_status)
            # The "Media worker thread started" message will trigger a success notification
        except Exception as e:
            self._safe_emit_status(f"Media service unavailable: {str(e)[:30]}")
        
    # --------------------------------------------------
    # Event Handlers
    # --------------------------------------------------
    
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Handle window resize."""
        super().resizeEvent(event)
        
        # Reposition notifications if open
        if hasattr(self, '_notifications_drawer') and self._notifications_drawer and self._notifications_drawer.is_open:
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
            hasattr(self, '_notifications_drawer') and 
            self._notifications_drawer and 
            self._notifications_drawer.is_open):
            self._toggle_notifications()
            event.accept()
            return
        
        super().keyPressEvent(event)