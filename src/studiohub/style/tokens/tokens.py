from __future__ import annotations

from dataclasses import dataclass
from studiohub.style.utils.colors import with_alpha


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
    Build ThemeTokens from a validated theme dictionary (new schema).

    Expected theme format:
      - surface: app, surface, sidebar, header, status
      - text: primary, muted, disabled
      - border: subtle, strong
      - accent: primary, secondary, tertiary
      - semantic: danger, success, warning
      - state: surface_hover, surface_active, accent_hover, accent_active,
               border_hover, border_focus, scrollbar_handle
    """
    for section in ("surface","text","border","accent","semantic","state"):
        if section not in theme:
            raise ValueError("Theme must be loaded via tokens.loader.load_theme() and match the new schema")

    s = theme["surface"]
    t = theme["text"]
    b = theme["border"]
    a = theme["accent"]
    sem = theme["semantic"]
    st = theme["state"]

    name = (theme.get("meta", {}).get("name") or theme.get("name") or "unknown").lower()

    return ThemeTokens(
        name=name,

        # Surfaces
        bg_app=s["app"],
        bg_surface=s["surface"],
        bg_sidebar=s["sidebar"],
        bg_header=s["header"],
        bg_status=s["status"],

        # Text
        text_primary=t["primary"],
        text_muted=t["muted"],
        text_disabled=t["disabled"],

        # Borders
        border=b["subtle"],
        border_strong=b["strong"],

        # Semantic
        danger=sem["danger"],
        success=sem["success"],
        warning=sem["warning"],

        # Accents
        accent=a["primary"],
        accent_secondary=a["secondary"],
        accent_tertiary=a["tertiary"],

        # Interaction / State
        surface_hover=st["surface_hover"],
        surface_active=st["surface_active"],
        accent_hover=st["accent_hover"],
        accent_active=st["accent_active"],
        border_hover=st["border_hover"],
        border_focus=st["border_focus"],
        scrollbar_handle=st["scrollbar_handle"],

        # Derived
        default_hover=with_alpha(s["app"], 0.25),
        danger_hover=with_alpha(sem["danger"], 0.20),
        danger_active=with_alpha(sem["danger"], 0.30),
    )
