from studiohub.style.styles.utils import with_alpha


def build(tokens):
    return f"""
    /* ============================================================
       Root background ownership
       ============================================================ */
    #SettingsView {{
        background-color: {tokens.bg_app};
    }}

    #SettingsView QScrollArea {{
        background: transparent;
        border: none;
    }}

    #SettingsView QScrollArea::viewport {{
        background: transparent;
    }}

    #SettingsView QWidget#SettingsContent {{
        background-color: {tokens.bg_app};
    }}

    /* ============================================================
       Button Base (canonical interaction model)
       ============================================================ */
    #SettingsView QPushButton {{
        background-color: {tokens.surface_hover};
        color: {tokens.text_muted};
        border: none;
    }}

    /* Hover = text only */
    #SettingsView QPushButton:hover {{
        background-color: {tokens.surface_hover};
        color: {tokens.text_primary};
    }}

    /* ============================================================
       Top Navigation
       ============================================================ */
    #SettingsView QPushButton[role="NavToggle"] {{
        min-width: 110px;
        padding: 6px 14px;
        border-radius: 8px;
        background-color: {tokens.surface_hover};
        color: {tokens.text_muted};
    }}

    #SettingsView QPushButton[role="NavToggle"]:checked {{
        background-color: {tokens.accent};
        color: {tokens.text_primary};
        font-weight: 700;
    }}

    /* ============================================================
       Section Structure
       ============================================================ */
    #SettingsView QFrame[role="section-separator"] {{
        background-color: {with_alpha(tokens.border, 0.50)};
        min-height: 1px;
        max-height: 1px;
        border: none;
    }}

    #SettingsView QLabel[role="section-title"] {{
        color: {tokens.text_primary};
    }}

    #SettingsView QLabel[role="subsection-title"] {{
        color: {tokens.text_primary};
    }}

    #SettingsView QFrame[role="section-divider"] {{
        background-color: {with_alpha(tokens.border, 0.50)};
        min-height: 1px;
        max-height: 1px;
        border: none;
    }}

    /* ============================================================
       Settings Rows
       ============================================================ */
    #SettingsView QWidget[role="settings-row"] {{
        border-bottom: 1px solid {with_alpha(tokens.border, 0.50)};
    }}

    #SettingsView QWidget[role="settings-row"][isLast="true"] {{
        border-bottom: none;
    }}

    /* ============================================================
       Field Labels & Inputs
       ============================================================ */
    #SettingsView QLabel[role="field-label"] {{
        color: {tokens.text_primary};
    }}

    #SettingsView QLabel[role="muted"] {{
        color: {tokens.text_muted};
    }}

    #SettingsView QLineEdit {{
        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};
        border: 1px solid {tokens.border};
        border-radius: 3px;
        padding: 6px 10px;
    }}

    /* ============================================================
       Segmented Buttons (canonical)
       ============================================================ */
    #SettingsView QPushButton#SegmentedButton {{
        min-width: 65px;
        padding-left: 14px;
        padding-right: 14px;
        padding-top: 0px;
        padding-bottom: 0px;
        background-color: {tokens.surface_hover};
        color: {tokens.text_muted};
        border: none;
    }}

    #SettingsView QPushButton#SegmentedButton:hover:!checked {{
        background-color: {tokens.surface_hover};
        color: {tokens.text_primary};
    }}

    #SettingsView QPushButton#SegmentedButton:checked {{
        background-color: {tokens.accent};
        color: {tokens.text_primary};
        font-weight: 700;
    }}

    #SettingsView QPushButton#SegmentedButton[segment="first"] {{
        border-top-left-radius: 8px;
        border-bottom-left-radius: 8px;
    }}

    #SettingsView QPushButton#SegmentedButton[segment="last"] {{
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
    }}

    /* ============================
    Icon Buttons (SVG / currentColor)
    ============================ */

    #SettingsView QToolButton#IconButton {{
        background-color: transparent;
        border: none;
        color: {with_alpha(tokens.text_primary, 0.55)};

    }}

    #SettingsView QToolButton#IconButton:hover {{
        color: {tokens.text_primary};
    }}

    /* ============================
    Replace Paper Button spacing
    ============================ */

    #SettingsView QPushButton#SegmentedButton {{
        padding: 6px 18px;          /* vertical | horizontal */
        min-height: 32px;
    }}
    #SettingsView QPushButton#SegmentedButton:hover {{
        font-weight: 700;
    }}

    /* ============================================================
       Footer Buttons
       ============================================================ */
    #SettingsView QPushButton:default {{
        background-color: {tokens.surface_hover};
        color: {tokens.text_muted};
        font-weight: 600;
    }}
    #SettingsView QPushButton#IconButton {{
        background-color: {tokens.surface_hover};
        border-radius: 6px;
    }}

    #SettingsView QPushButton#IconButton:hover {{
        color: {tokens.text_primary};
    }}

    """
