"""Startup validation and initialization."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6 import QtWidgets

from studiohub.config_manager import ConfigManager
from studiohub.constants import REQUIRED_PATHS


class StartupManager:
    """
    Manages application startup validation and configuration.
    
    Validates required paths and guides user through setup if needed.
    """
    
    def __init__(
        self,
        config_manager: ConfigManager,
        parent_window: QtWidgets.QWidget,
    ):
        """
        Initialize startup manager.
        
        Args:
            config_manager: Configuration manager
            parent_window: Parent window for dialogs
        """
        self._config = config_manager
        self._parent = parent_window
    
    def validate_required_paths(
        self,
        on_incomplete: Callable[[list[str]], None] | None = None,
    ) -> bool:
        """
        Validate all required paths are configured.
        
        Args:
            on_incomplete: Callback for handling missing paths
            
        Returns:
            True if all paths valid, False if setup incomplete
        """
        missing = self._find_missing_paths()
        
        if not missing:
            return True
        
        # Prompt user
        should_configure = self._prompt_configuration(missing)
        
        if should_configure and on_incomplete:
            on_incomplete(missing)
        
        return False
    
    def _find_missing_paths(self) -> list[str]:
        """
        Find all missing or invalid required paths.
        
        Returns:
            List of missing path keys
        """
        missing: list[str] = []
        
        for key, meta in REQUIRED_PATHS.items():
            section, name = key.split(".", 1)
            value = self._config.get(section, name)
            
            if not value:
                missing.append(key)
                continue
            
            path = Path(value)
            
            if meta["type"] == "dir" and not path.is_dir():
                missing.append(key)
            elif meta["type"] == "file" and not path.is_file():
                missing.append(key)
        
        return missing
    
    def _prompt_configuration(self, missing: list[str]) -> bool:
        """
        Show configuration prompt to user.
        
        Args:
            missing: List of missing path keys
            
        Returns:
            True if user wants to configure, False if cancelled
        """
        msg = QtWidgets.QMessageBox(self._parent)
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setWindowTitle("Setup Required")
        msg.setText(
            "Some required paths are missing or invalid.\n\n"
            "You must configure them before using SnooozeCo Studio Hub."
        )
        msg.setDetailedText("\n".join(missing))
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Open | QtWidgets.QMessageBox.Cancel
        )
        msg.setDefaultButton(QtWidgets.QMessageBox.Open)
        
        result = msg.exec()
        return result == QtWidgets.QMessageBox.Open
