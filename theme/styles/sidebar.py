def build(tokens) -> str:
    return f"""
    /* ============================
    Sidebar
    ============================ */

    #leftMenuBg {{
        background-color: {tokens.bg_surface};
    }}

    QFrame#SidebarHeader {{
        background-color: {tokens.bg_header};
        border-bottom: 2px solid {tokens.text_muted};
    }}

    QWidget#SidebarButton {{
        background: transparent;
    }}

    QWidget#SidebarButton:hover {{
        background-color: {tokens.surface_hover};
    }}

    QWidget#SidebarButton:pressed {{
        background-color: {tokens.surface_active};
    }}

    QPushButton#SidebarButtonText:pressed {{
        background-color: {tokens.surface_active};
    }}

    /* Child row hover surface */
    QWidget#SidebarChildRow:hover {{
        background-color: {tokens.surface_hover};
    }}

    QWidget#SidebarChildRow[active="true"] {{
        background-color: transparent;
    }}

    /* Child active indicator */
    QWidget#SidebarChildRow[active="true"] QFrame#SidebarIndicator {{
        background-color: {tokens.accent};
    }}


    /* ============================
    Sidebar inner button (kill native press)
    ============================ */

    QPushButton#SidebarButtonText {{
        background-color: transparent;
        border: none;
        padding: 0px;
    }}

    QPushButton#SidebarButtonText:hover {{
        background-color: transparent;
    }}

    QPushButton#SidebarButtonText:pressed {{
        background-color: transparent;
    }}

    QPushButton#SidebarButtonText:checked {{
        background-color: transparent;
    }}

    QPushButton#SidebarButtonText:focus {{
        outline: none;
    }}


    QPushButton#SidebarUtility:checked {{
    background-color: {tokens.surface_active};
    }}

    QPushButton#SidebarUtility:checked:pressed {{
        background-color: {tokens.surface_active};
    }}

    QPushButton#SidebarUtility:focus {{
        outline: none;
    }}

    QWidget#SidebarButton[active="true"] {{
        background: transparent;
    }}

    QFrame#SidebarIndicator {{
        background: transparent;
    }}

    QWidget#SidebarButton[active="true"] QFrame#SidebarIndicator {{
        background-color: {tokens.accent};
    }}

    QLabel#SidebarButtonLabel {{
        color: {tokens.text_muted};
        font-weight: 600;
    }}

    QWidget#SidebarButton[active="true"] QLabel#SidebarButtonLabel {{
        color: {tokens.text_primary};
        font-weight: 700;
    }}
    /* --- Sidebar footer --- */
    QFrame#SidebarFooter {{
        background-color: {tokens.bg_surface};
        border-top: 1px solid {tokens.border};
    }}

    QFrame#SidebarFooterDivider {{
        background-color: {tokens.border};
        height: 1px;
    }}

    /* --- Sidebar footer --- */
    QFrame#SidebarFooter {{
        background-color: {tokens.bg_surface};
        border-top: 1px solid {tokens.border};
    }}

    QFrame#SidebarDivider {{
        background-color: {tokens.border};
        height: 1px;
    }}

    /* --- Footer Buttons --- */
    QPushButton#SidebarUtility {{
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 0px;
    }}

    QPushButton#SidebarUtility:hover {{
        background-color: {tokens.surface_hover};
    }}

    QPushButton#SidebarUtility:pressed {{
        background-color: {tokens.surface_active};
    }}

    SidebarButton[role="sidebar-item"][active="false"] #SidebarIndicator {{
        background: transparent;
    }}

    #SidebarDivider {{
        border: {tokens.border};
    }}
    
    /* Drawer */
    QFrame#NotificationsDrawer {{
        background: {tokens.bg_surface};
    }}

    /* Scroll area */
    QScrollArea,
    QScrollArea > QWidget {{
        background: transparent;
    }}

    /* Notification row */
    QWidget#NotificationRow {{
        background: {tokens.bg_surface};
    }}

    /* Divider between notifications */
    QFrame#NotificationDivider {{
        background: {tokens.border};
        margin-left: 16px;
        margin-right: 16px;
    }}

    QScrollArea {{
        background: transparent;
        border: none;
    }}

    QScrollArea::viewport {{
        background: transparent;
        border: none;
    }}
    QLabel[role="notification-title"] {{
        font-weight: 600;
    }}

    QFrame#NotificationsDrawer {{
        background: {tokens.bg_surface};
    }}

    QFrame#NotificationsHeader {{
        background: {tokens.bg_header};
        border-bottom: 1px solid {tokens.border};
    }}

    QLabel[role="notification-title"] {{
        font-weight: 600;
    }}

    QFrame#NotificationDivider {{
        background: {tokens.border};
    }}
    NotificationBadge {{
        border-radius: 9px;
        background: {{danger}};
        color: white;
        font-size: 7px;
        font-weight: 600;
    }}

    QLabel#SidebarNotificationBadge {{
        border-radius: 9px;
        background: {{danger}};
        color: white;
        font-size: 7px;
        font-weight: 600;
    }}
    QLabel#SidebarNotificationBadge[variant="inline"] {{
        background: {{accent}};
        font-size: 8px;
    }}

    /* ==================================================
    Notification Badge (base)
    ================================================== */

    /* Base badge */
    QLabel#SidebarNotificationBadge {{
        background: {tokens.accent};
        color: {tokens.text_primary};

        min-height: 14px;
        padding-left: 4px;
        padding-right: 4px;

        border-radius: 7px; /* half of min-height */

        font-size: 7px;
        font-weight: 600;

        qproperty-alignment: AlignCenter;
    }}

    /* Collapsed (icon overlay) */
    QLabel#SidebarNotificationBadge[variant="compact"] {{
        min-height: 14px;
        border-radius: 7px;
        font-size: 7px;
        padding-left: 3px;
        padding-right: 3px;
    }}

    /* Expanded (inline) */
    QLabel#SidebarNotificationBadge[variant="inline"] {{
        min-height: 16px;
        border-radius: 8px;
        font-size: 8px;
        padding-left: 5px;
        padding-right: 5px;
    }}


    """