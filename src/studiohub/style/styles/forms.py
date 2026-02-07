def build(tokens) -> str:
    return f"""
    /* ============================
    Forms & Fields
    ============================ */

    QRadioButton,
    QCheckBox {{
        font-weight: 500;
    }}

    QLabel[role="field-label"] {{
        font-weight: 600;
    }}

    QLabel[role="muted"] {{
        color: rgba(255,255,255,0.48);
    }}
    /* ============================
    Spin Boxes
    ============================ */

    QSpinBox,
    QDoubleSpinBox {{
        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};
        border: 1px solid {tokens.border};
        border-radius: 6px;
        padding: 4px 8px;
        min-height: 34px;
    }}

    QSpinBox:hover,
    QDoubleSpinBox:hover {{
        border-color: {tokens.border_hover};
    }}

    QSpinBox:focus,
    QDoubleSpinBox:focus {{
        border-color: {tokens.accent};
    }}

    /* --- Embedded line edit --- */
    QSpinBox::lineEdit,
    QDoubleSpinBox::lineEdit {{
        background: transparent;
        border: none;
        padding: 0;
        color: {tokens.text_primary};
    }}

    /* --- Up / Down buttons --- */
    QSpinBox::up-button,
    QSpinBox::down-button,
    QDoubleSpinBox::up-button,
    QDoubleSpinBox::down-button {{
        background: transparent;
        border: none;
        width: 14px;
    }}

    QSpinBox::up-button:hover,
    QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover,
    QDoubleSpinBox::down-button:hover {{
        background-color: {tokens.surface_hover};
    }}

    /* ============================
    Checkboxes & Radio Buttons
    ============================ */

    /* --- Base text --- */
    QCheckBox,
    QRadioButton {{
        color: {tokens.text_primary};
        spacing: 10px;
    }}

    /* ============================
    Checkbox
    ============================ */

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {tokens.border};
        background-color: {tokens.bg_surface};
    }}

    QCheckBox::indicator:hover {{
        border-color: {tokens.border_hover};
    }}

    QCheckBox::indicator:checked {{
        background-color: {tokens.accent};
        border-color: {tokens.accent};
    }}

    QCheckBox::indicator:checked:hover {{
        background-color: {tokens.accent_hover};
        border-color: {tokens.accent_hover};
    }}

    QCheckBox::indicator:disabled {{
        background-color: {tokens.bg_surface};
        border-color: {tokens.border};
    }}

    QCheckBox:disabled {{
        color: {tokens.text_disabled};
    }}

    /* ============================
    Radio Buttons (Refined)
    ============================ */

    QRadioButton {{
        color: {tokens.text_primary};
        spacing: 10px;
    }}

    QRadioButton::indicator {{
        width: 14px;
        height: 14px;
        border-radius: 7px;
        border: 1px solid {tokens.border};
        background-color: {tokens.bg_surface};
    }}

    QRadioButton::indicator:hover {{
        border-color: {tokens.border_hover};
    }}

    QRadioButton::indicator:checked {{
        border: 1px solid {tokens.accent};
        background-color: {tokens.accent};
    }}

    QRadioButton::indicator:checked:disabled {{
        background-color: {tokens.border};
        border-color: {tokens.border};
    }}

    QRadioButton:disabled {{
        color: {tokens.text_disabled};
    }}


    """
