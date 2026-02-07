from __future__ import annotations

from dataclasses import dataclass
from studiohub.theme.styles.utils import with_alpha


@dataclass(frozen=True)
class ThemeTokens:
    """
    Fully tokenized theme surface.

    """

    name: str

    # =================================================
    # Surfaces
    # =================================================
    bg_app: str
    bg_surface: str
    bg_sidebar: str
    bg_header: str
    bg_status: str

    # =================================================
    # Text
    # =================================================
    text_primary: str
    text_muted: str
    text_disabled: str

    # =================================================
    # Borders
    # =================================================
    border: str
    border_strong: str

    # =================================================
    # Danger
    # =================================================
    danger: str
    success: str
    warning: str

    # =================================================
    # Accents
    # =================================================
    accent: str
    accent_secondary: str
    accent_tertiary: str

    # =================================================
    # Interaction / State
    # =================================================
    surface_hover: str
    surface_active: str

    accent_hover: str
    accent_active: str

    border_hover: str
    border_focus: str

    scrollbar_handle: str
    
    # 🔹 Derived (computed, not from JSON)
    default_hover: str
    danger_hover: str
    danger_active: str


def build_tokens(theme: dict) -> ThemeTokens:
    """
    Build ThemeTokens from a validated theme dictionary.

    This function assumes the theme was loaded via the theme loader
    and has already been parsed from JSON.
    """

    if "colors" not in theme or "interaction" not in theme:
        raise ValueError("Theme must be loaded via theme.loader.load_theme()")

    c = theme["colors"]
    i = theme["interaction"]

    return ThemeTokens(
        name=theme.get("meta", {}).get("name", "unknown").lower(),

        # -------------------------------
        # Surfaces
        # -------------------------------
        bg_app=c["bg_app"],
        bg_surface=c["bg_surface"],
        bg_sidebar=c["bg_sidebar"],
        bg_header=c["bg_header"],
        bg_status=c["bg_status"],

        # -------------------------------
        # Text
        # -------------------------------
        text_primary=c["fg_primary"],
        text_muted=c["fg_muted"],
        text_disabled=c["fg_disabled"],

        # -------------------------------
        # Borders
        # -------------------------------
        border=c["border_subtle"],
        border_strong=c["border_strong"],

        # -------------------------------
        # Danger
        # -------------------------------
        danger=c["danger"],
        success=c["success"],
        warning=c["warning"],

        # -------------------------------
        # Accents
        # -------------------------------
        accent=c["accent_primary"],
        accent_secondary=c["accent_secondary"],
        accent_tertiary=c["accent_tertiary"],

        # -------------------------------
        # Interaction / State
        # -------------------------------
        surface_hover=i["surface_hover"],
        surface_active=i["surface_active"],

        accent_hover=i["accent_hover"],
        accent_active=i["accent_active"],

        border_hover=i["border_hover"],
        border_focus=i["border_focus"],

        scrollbar_handle=i["scrollbar_handle"],

        # 🔹 Derived here
        default_hover=with_alpha(c["bg_app"], 0.25),
        danger_hover=with_alpha(c["danger"], 0.20),
        danger_active=with_alpha(c["danger"], 0.30),
    )