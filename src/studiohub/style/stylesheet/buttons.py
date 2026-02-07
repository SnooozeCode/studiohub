def build(tokens) -> str:
    return f"""
    /* ============================
    Buttons (Global)
    ============================ */

    QPushButton {{
        padding: 6px 12px;
        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};
        letter-spacing: 1px;
    }}

    QPushButton:hover {{
        background-color: {tokens.surface_hover};
    }}

    QPushButton:pressed {{
        background-color: {tokens.surface_active};
    }}

    QPushButton:disabled {{
        color: {tokens.text_disabled};
        background-color: {tokens.bg_app};
        border-color: {tokens.border};
    }}

    /* Primary action */
    QPushButton[primary="true"] {{
        background-color: {tokens.accent};
        color: {tokens.text_primary};
        border: none;
    }}

    QPushButton[primary="true"]:hover {{
        background-color: {tokens.accent_hover};
    }}

    QPushButton[primary="true"]:pressed {{
        background-color: {tokens.accent_active};
    }}

    /* ============================
    Source / Mode Toggle Buttons
    ============================ */

    QPushButton#SourceToggle {{
        min-height: 20px;
        padding: 6px 14px;
        background-color: {tokens.bg_surface};
        color: {tokens.text_muted};
        font-weight: 600;
        border-radius: 6px;
    }}

    QPushButton#SourceToggle:hover {{
        background-color: {tokens.surface_hover};
        color: {tokens.text_primary};
    }}

    QPushButton#SourceToggle:checked {{
        background-color: {tokens.accent};
        color: {tokens.text_primary};
        font-weight: 700;
    }}

    QPushButton#SourceToggle:checked:hover {{
        background-color: {tokens.accent_hover};
    }}

    QPushButton#SourceToggle:pressed {{
        background-color: {tokens.surface_active};
    }}

    QPushButton#SourceToggle:disabled {{
        color: {tokens.text_disabled};
        background-color: {tokens.bg_surface};
    }}

    /* --- Danger variant --- */

    QPushButton#SourceToggle[danger="true"] {{
        background-color: {tokens.danger_hover};
        color: {tokens.text_primary};
    }}

    QPushButton#SourceToggle[danger="true"]:hover {{
        background-color: {tokens.danger};
    }}

    QPushButton#SourceToggle[danger="true"]:pressed {{
        background-color: {tokens.danger_active};
    }}

    /* ============================
    Drawer Handle
    ============================ */

    QToolButton[role="drawer-handle"] {{
        background: {tokens.surface_hover};
        border: none;
        border-radius: 0;
        padding: 0;
        letter-spacing: 2px;
        color: {tokens.text_muted};
    }}

    QToolButton[role="drawer-handle"]:hover {{
        background: {tokens.surface_active};
    }}

    QToolButton[role="drawer-handle"]:checked {{
        background-color: {tokens.accent};
        color: {tokens.bg_app};
    }}
    """
