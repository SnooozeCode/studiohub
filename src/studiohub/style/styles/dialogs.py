
def build(tokens) -> str:
    return f"""
    /* ============================
    Dialogs (Global)
    ============================ */

    QDialog {{
        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};
        border-radius: 12px;
    }}

    QDialog > QWidget {{
        background: transparent;
    }}

    QDialog QLabel[emphasis="strong"] {{
        font-weight: 600;
        color: {tokens.text_primary};
    }}

    QDialog QLineEdit,
    QDialog QTextEdit,
    QDialog QComboBox {{
        background-color: {tokens.bg_app};
        border: 1px solid {tokens.border};
        border-radius: 6px;
        padding: 6px 8px;
        color: {tokens.text_primary};
    }}

    QDialog QLineEdit:focus,
    QDialog QTextEdit:focus {{
        border-color: {tokens.accent};
    }}

    QDialog QRadioButton,
    QDialog QCheckBox {{
        spacing: 8px;
        color: {tokens.text_primary};
    }}

    QDialog QRadioButton::indicator,
    QDialog QCheckBox::indicator {{
        width: 14px;
        height: 14px;
    }}

    QDialog QDialogButtonBox QPushButton {{
        min-height: 32px;
        padding: 6px 14px;
        border-radius: 6px;
        font-weight: 500;
    }}

    QDialog QDialogButtonBox QPushButton:default {{
        background-color: {tokens.accent};
        color: white;
    }}

    QDialog QDialogButtonBox QPushButton:!default {{
        background-color: transparent;
        border: 1px solid {tokens.border};
    }}

    QDialog QDialogButtonBox QPushButton:hover {{
        background-color: rgba(255,255,255,0.06);
    }}
"""