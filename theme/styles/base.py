def build(tokens) -> str:
    return f"""
    /* ============================
    Root / App Surfaces
    ============================ */
    #Root {{
        background-color: {tokens.bg_app};
    }}

    #bgApp {{
        background-color: {tokens.bg_app};
        border: none;
    }}

    QWidget {{
        color: {tokens.text_primary};
    }}

    /* ============================
    Status Bar
    ============================ */
    QFrame#ViewStatusBar {{
        background-color: {tokens.bg_app};
        border-top: 1px solid {tokens.text_muted};
    }}

    QLabel#StatusText,
    QLabel#StatusVersion {{
        color: {tokens.text_muted};
    }}

    /* ============================
    Scrollbars (Token-Based)
    ============================ */
    QScrollBar:vertical {{
        background: {tokens.bg_surface};
        width: 10px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: {tokens.scrollbar_handle};
        min-height: 24px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {tokens.border_hover};
    }}

    QScrollBar::handle:vertical:pressed {{
        background: {tokens.accent_active};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: none;
    }}
    QScrollBar:horizontal {{
        background: {tokens.bg_surface};
        height: 10px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background: {tokens.border};
        min-width: 24px;
        border-radius: 5px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {tokens.border_hover};
    }}

    QScrollBar::handle:horizontal:pressed {{
        background: {tokens.accent_active};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: none;
    }}
    /* ============================
    Progress Bars (Global)
    ============================ */

    QProgressBar {{
        background-color: {tokens.bg_surface};
        border: 1px solid {tokens.border};
        border-radius: 4px;
        height: 10px;
        text-align: center;
        color: transparent; /* hide % text */
    }}

    QProgressBar::chunk {{
        background-color: {tokens.accent};
        border-radius: 3px;
    }}

    /* --- Hover / emphasis variants (optional) --- */
    QProgressBar[variant="warning"]::chunk {{
        background-color: {tokens.warning};
    }}

    QProgressBar[variant="danger"]::chunk {{
        background-color: {tokens.danger};
    }}

    QProgressBar[variant="success"]::chunk {{
        background-color: {tokens.success};
    }}

    /* ============================
    Context Menus (QMenu)
    ============================ */

    QMenu {{
        background-color: {tokens.bg_surface};
        border: 1px solid {tokens.border};
        padding: 0px;
    }}

    QMenu::item {{
        color: {tokens.text_primary};
        padding: 6px 24px 6px 18px;
    }}

    QMenu::item:selected {{
        background-color: {tokens.accent_hover};
        color: {tokens.text_primary};
    }}

    QMenu::separator {{
        height: 1px;
        margin: 6px 8px;
        background-color: {tokens.border};
    }}
    QDialog#HubDialog {{
        background-color: {tokens.bg_surface};
        border-radius: 14px;
    }}

    QDialog#HubDialog QLabel {{
        color: {tokens.text_primary};
    }}

    QDialog#HubDialog QCheckBox {{
        color: {tokens.text_primary};
        spacing: 8px;
        padding-top: 6px;
    }}

    QDialog#HubDialog QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {tokens.border};
        background-color: {tokens.bg_surface};
    }}

    QDialog#HubDialog QCheckBox::indicator:checked {{
        background-color: {tokens.accent};
        border-color: {tokens.accent};
    }}

    QDialog#HubDialog QDialogButtonBox {{
        margin-top: 10px;
    }}

    QDialog#HubDialog QPushButton {{
        min-height: 32px;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 500;
    }}

    QDialog#HubDialog QPushButton:default {{
        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};
    }}

    QDialog#HubDialog QPushButton:default:hover {{
        background-color: {tokens.surface_hover};
    }}

    QDialog#HubDialog QPushButton:default {{
        background-color: {tokens.accent};
        color: {tokens.text_primary};
    }}

    QDialog#HubDialog QPushButton:default:hover {{
        background-color: {tokens.accent};
    }}
    QLabel[emphasis="strong"] {{
        font-weight: 600;
    }}

    QMessageBox {{
        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};
        font-family: "Inter";
    }}

    QMessageBox QLabel {{
        color: {tokens.text_primary};
    }}

    QMessageBox QLabel#qt_msgbox_label {{
        font-size: 13px;
        line-height: 1.4;
    }}

    QMessageBox QLabel#qt_msgboxex_icon_label {{
        padding-right: 12px;
    }}
    QMessageBox QPushButton {{
        min-width: 80px;
        min-height: 10px;

        padding: 6px 14px;
        border-radius: 6px;

        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};

        border: 1px solid {tokens.border};
    }}

    QMessageBox QPushButton:hover {{
        background-color: {tokens.bg_header};
    }}

    QMessageBox QPushButton:pressed {{
        background-color: {tokens.bg_surface};
    }}

    QMessageBox QPushButton:default {{
        border: 1px solid {tokens.accent};
    }}

    """