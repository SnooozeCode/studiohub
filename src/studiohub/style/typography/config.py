# studiohub/style/typography/config.py
"""
Single source of truth for all typography settings.
"""

from dataclasses import dataclass
from typing import Dict, Tuple
from PySide6.QtGui import QFont

@dataclass(frozen=True)
class TypographyStyle:
    """Complete typography style definition."""
    size_px: int
    weight: QFont.Weight
    letter_spacing: float = 0.0
    line_height: float = 1.4  # For multi-line text

class TypographyConfig:
    """Central typography configuration."""
    
    # Base settings
    BASE_FONT_FAMILY = "Inter"
    BASE_FONT_PX = 14
    
    # Semantic scale - ALL fonts defined here
    STYLES: Dict[str, TypographyStyle] = {
        # Headings
        "h1-xl": TypographyStyle(size_px=26, weight=QFont.Weight.Bold),
        "h1":    TypographyStyle(size_px=22, weight=QFont.Weight.Bold),
        "h2":    TypographyStyle(size_px=19, weight=QFont.Weight.DemiBold),
        "h3":    TypographyStyle(size_px=17, weight=QFont.Weight.DemiBold),
        "h4":    TypographyStyle(size_px=15, weight=QFont.Weight.Medium),
        "h5":    TypographyStyle(size_px=14, weight=QFont.Weight.Medium),
        "h6":    TypographyStyle(size_px=13, weight=QFont.Weight.Medium, letter_spacing=1.0),
        
        # Body text
        "body":         TypographyStyle(size_px=14, weight=QFont.Weight.Normal),
        "body-strong":  TypographyStyle(size_px=14, weight=QFont.Weight.Medium),
        "body-small":   TypographyStyle(size_px=12, weight=QFont.Weight.Normal),
        
        # Supporting text
        "caption":      TypographyStyle(size_px=12, weight=QFont.Weight.Normal),
        "small":        TypographyStyle(size_px=11, weight=QFont.Weight.Normal),
        "nav":          TypographyStyle(size_px=13, weight=QFont.Weight.Normal, letter_spacing=0.5),
        
        # Special
        "tree":         TypographyStyle(size_px=12, weight=QFont.Weight.Normal),
        "mono":         TypographyStyle(size_px=12, weight=QFont.Weight.Normal),
    }
    
    # Widget type to style mapping
    WIDGET_STYLES = {
        # Widget object names
        "DashboardCardTitle": "h3",
        "ActionTitle": "h2",
        "ActionSubtitle": "h6",
        "StatusText": "body-small",
        "StatusVersion": "body-small",
        "PanelPrimary": "h2",
        "PanelSecondary": "body",
        "PanelMeta": "small",
        "PanelPlaceholder": "body",
        "SidebarButtonLabel": "nav",
        
        # Role-based
        "section-title": "h3",
        "field-label": "body-strong",
        "muted": "caption",
        "notification-title": "h5",
        
        # Default fallbacks
        "default": "body",
        "default-button": "body",
    }