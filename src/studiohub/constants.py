"""Application-wide constants and configuration values."""
from __future__ import annotations

from typing import TypedDict

# Application metadata
APP_VERSION = "v0.12.5-beta"
APP_VENDOR = "SnooozeCo"
APP_NAME = "StudioHub"

# =====================================================
# Print Sizes (Single Source of Truth)
# =====================================================
PRINT_SIZES = ("12x18", "18x24", "24x36")
PRINT_SIZES_DISPLAY = {  # For UI display with proper multiplication sign
    "12x18": "12×18",
    "18x24": "18×24",
    "24x36": "24×36",
}

class UIConstants:
    """UI sizing and timing constants."""

    # Fonts
    BASE_FONT_FAMILY = "Inter"
    BASE_FONT_PX = 14       # Global dial (change once, affects everything)

    # Window
    DEFAULT_WIDTH = 1440
    DEFAULT_HEIGHT = 900
    
    # Sidebar
    SIDEBAR_WIDTH = 260
    
    # Status bar
    STATUS_BAR_HEIGHT = 38
    STATUS_DECAY_MS = 6000
    SETTINGS_SAVED_DECAY_MS = 2500
    
    # Notifications drawer
    NOTIFICATION_DRAWER_WIDTH = 360
    NOTIFICATION_HEADER_HEIGHT = 56
    NOTIFICATION_ANIMATION_DURATION = 420
    
    # Margins and spacing
    VIEW_MARGIN = 24
    VIEW_SPACING = 12


class PathRequirement(TypedDict):
    """Type definition for required path configuration."""
    label: str
    must_exist: bool
    type: str  # "file" or "dir"


# Required paths for application startup
REQUIRED_PATHS: dict[str, PathRequirement] = {
    "paths.photoshop_exe": {
        "label": "Photoshop Executable",
        "must_exist": False,
        "type": "file",
    },
    "paths.archive_root": {
        "label": "Archive Root",
        "must_exist": True,
        "type": "dir",
    },
    "paths.studio_root": {
        "label": "Studio Root",
        "must_exist": True,
        "type": "dir",
    },
    "paths.runtime_root": {
        "label": "Runtime Root",
        "must_exist": True,
        "type": "dir",
    },
    "paths.print_jobs_root": {
        "label": "Print Jobs Folder",
        "must_exist": True,
        "type": "dir",
    },
    "paths.jsx_root": {
        "label": "JSX Scripts Folder",
        "must_exist": True,
        "type": "dir",
    },
}