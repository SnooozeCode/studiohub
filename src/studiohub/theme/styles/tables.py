def build(tokens) -> str:
    return f"""
    /* ============================
    Tables & Lists
    ============================ */

    QTreeView,
    QTableView,
    QListView {{
        background-color: {tokens.bg_surface};
        font-weight: 600;
        gridline-color: {tokens.text_muted};
        selection-background-color: {tokens.accent};
        selection-color: {tokens.text_primary};
        border: none;
        outline: none;
        alternate-background-color: rgba(0,0,0,0.08);
    }}

    QTreeView::item,
    QTableView::item,
    QListView::item {{
        padding-left: 10px;
        padding-right: 10px;
        color: {tokens.text_primary};
    }}

    QTreeView::viewport {{
        background-color: {tokens.bg_surface};
    }}


    QHeaderView {{
        background-color: {tokens.bg_surface};
    }}

    QHeaderView::section {{
        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};
        font-weight: 800;
        padding: 8px 10px;
        border-bottom: 1px solid rgba(255,255,255,0.12);
        qproperty-alignment: AlignVCenter;
    }}


    QTreeView[role="posters-tree"] {{
        alternate-background-color: rgba(0,0,0,0.08);
    }}

    /* =========================================================
    Missing Files – Table Header (QHeaderView)
    ========================================================= */

    QTreeWidget[role="missing-tree"]::header {{
        background: transparent;
    }}

    /* All header sections */
    QTreeWidget[role="missing-tree"] QHeaderView::section {{
        background-color: {tokens.bg_header};
        color: {tokens.text_primary};
        padding: 0 10px;
        min-height: 45px;
        border-bottom: 1px solid {tokens.border};
        font-weight: 600;
    }}

    /* Horizontal header sections */
    QTreeWidget[role="missing-tree"] QHeaderView::section:horizontal {{
        padding-left: 12px;
        border-right: none;
    }}

    /* Hover (optional, subtle) */
    QTreeWidget[role="missing-tree"] QHeaderView::section:hover {{
        background-color: {tokens.surface_hover};
    }}

    #MissingFilesView QTreeView::item:selected {{
        background: {tokens.surface_active};
    }}

    /* ============================
    Log Tables (Print Jobs, Logs)
    ============================ */

    QTableView[role="log-table"] {{
        gridline-color: rgba(255, 255, 255, 0.06);
        background: transparent;
    }}

    QTableView[role="log-table"]::item {{
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }}

    QTableView[role="log-table"]::item:selected {{
        background: transparent;
    }}

    QHeaderView::section {{
        border: none;
        padding: 6px 8px;
        font-weight: 500;
    }}

    QTableView[row_profile="standard"] {{
        gridline-color: rgba(255, 255, 255, 18);
    }}
    """
