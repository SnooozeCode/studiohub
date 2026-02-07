def build(tokens) -> str:
    return f"""
    /* ============================
    Panels & Headers
    ============================ */

    QFrame[role="panel"] {{
        background-color: {tokens.bg_surface};
        border: 1px solid rgba(255,255,255,0.12);
        border-top-left-radius: 10px;
        border-bottom-left-radius: 10px;
    }}

    QFrame[role="panel"][active="true"] {{
        box-shadow: inset 0 0 0 1px rgba(189,147,249,0.35);
    }}

    QFrame[role="table-header"] {{
        border-bottom: 1px solid rgba(255,255,255,0.18);
    }}

    QFrame[role="divider"] {{
        background-color: {tokens.text_muted};
        min-height: 1px;
    }}

    QFrame[role="section-divider"] {{
        background-color: rgba(255,255,255,0.08);
    }}
    
    /* ============================
   Panel Surfaces
   ============================ */

    QFrame#DashboardCard {{
        background-color: palette(base);
        border-radius: 7px;
    }}

    QFrame[role="stat-card"] {{
        background-color: palette(base);
        border-radius: 7px;
    }}

    QFrame[role="panel"][variant="missing-table"] {{
        border: none;
        border-radius: 0;
    }}

    """
