# style/tokens/schema.py

# New, semantic theme schema (no fallbacks).

REQUIRED_SURFACE_KEYS = {
    "app",
    "surface",
    "sidebar",
    "header",
    "status",
}

REQUIRED_TEXT_KEYS = {
    "primary",
    "muted",
    "disabled",
}

REQUIRED_BORDER_KEYS = {
    "subtle",
    "strong",
}

REQUIRED_ACCENT_KEYS = {
    "primary",
    "secondary",
    "tertiary",
}

REQUIRED_SEMANTIC_KEYS = {
    "danger",
    "success",
    "warning",
}

REQUIRED_STATE_KEYS = {
    "surface_hover",
    "surface_active",
    "accent_hover",
    "accent_active",
    "border_hover",
    "border_focus",
    "scrollbar_handle",
}
