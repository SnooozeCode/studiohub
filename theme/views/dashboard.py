from studiohub.theme.styles.utils import with_alpha

def build(tokens):
    return f"""
    /* ============================
       Dashboard Typography
       ============================ */
    QLabel#DashboardCardTitle {{
        font-weight: 700;
        letter-spacing: 1.2px;
        color: {tokens.text_primary};
    }}

    QLabel#KPIValue {{
        color: {tokens.text_primary};
    }}

    QLabel#DashboardEmphasisValue {{
        color: {tokens.text_primary};
    }}

    QLabel#KPIValueXL {{
        color: {tokens.text_primary};
    }}

    QLabel#KPISubtext {{
        opacity: 0.75;
        color: {tokens.text_muted};
    }}

    QLabel#KPIUnit {{
        opacity: 0.75;
        color: {tokens.text_muted};
    }}

    QFrame#DashboardCard {{
        background-color: {tokens.bg_surface};
        border-radius: 7px;
    }}

    QFrame[role="stat-card"] {{
        background-color: {tokens.bg_surface};
        border-radius: 7px;
    }}

    #KPIDivider {{
        background-color: rgba(255,255,255,0.08);
        margin-top: 4px;
        margin-bottom: 6px;
    }}
    
    QWidget#DashboardListHost {{
        background: transparent;
    }}

    QScrollArea {{
        background: transparent;
        border: none;
    }}

    QScrollArea > QWidget {{
        background: transparent;
    }}

    QLabel#KPIMetaMuted {{
        color: {{with_alpha(tokens.text_primary, 0.55)}};
    }}

    QScrollArea::viewport {{
        background: transparent;
    }}

    QLabel#DashboardRow {{
        background: transparent;
    }}

    /* --- Recent Print Logs --- */
    QLabel[role="dashboard-size-badge"] {{
        padding: 2px 10px;
    }}

    /* Purple accent badge (single) */
    QLabel[role="dashboard-size-badge"][variant="single"] {{
        background: {tokens.accent};
        color: {tokens.text_primary};
    }}

    /* Purple accent badge (2-UP, spans two rows) */
    QLabel[role="dashboard-size-badge"][variant="two-up"] {{
        background: {tokens.accent};
        color: {tokens.text_primary};
    }}

    QListWidget#DashboardQueueList::item {{
        margin: 0px;
        padding: 0px;
    }}

    QListWidget#DashboardQueueList {{
        outline: none;
        border: none;
    }}

    QListWidget#DashboardQueueList::item:selected {{
        background: transparent;
    }}

    /* Compact dashboard card headers (print job / index only) */
    DashboardCard[header="compact"] QLabel#DashboardCardTitle {{
        padding-top: 0px;
        padding-bottom: 0px;
    }}
        
    QChartView {{
        background: transparent;
    }}

    /* Bar fill colors */
    QBarSet[label="Patent"] {{
        background-color: {tokens.accent};
    }}

    QBarSet[label="Studio"] {{
        background-color: {tokens.accent};
    }}

    /* ============================
    Ledger Panels (Shared)
    ============================ */

    QFrame#MonthlyCostLedgerPanel,
    QFrame#PatentsVsStudioPanel {{
        background-color: {tokens.bg_surface};
        border-radius: 7px;
    }}

    /* --- Subtitle --- */

    QLabel#DashboardCardSubtitle {{
        color: {with_alpha(tokens.text_primary, 0.55)};
    }}

    /* --- Rows --- */

    QWidget#CostRow {{
        min-height: 24px;
    }}

    QFrame#CostMarker {{
        border-radius: 2px;
        background-color: {with_alpha(tokens.text_muted, 0.6)};
    }}

    QFrame#CostMarker[markerColor="paper"] {{
        background-color: {tokens.accent};
    }}

    QFrame#CostMarker[markerColor="ink"] {{
        background-color: {tokens.accent_secondary};
    }}

    QFrame#CostMarker[markerColor="shipping"] {{
        background-color: {tokens.accent_tertiary};
    }}

    QLabel#CostLabel {{
        color: {with_alpha(tokens.text_primary, 0.80)};
    }}

    QLabel#CostAmount {{
        color: {with_alpha(tokens.text_primary, 0.95)};
    }}

    /* --- Divider --- */

    QFrame#LedgerDivider {{
        background-color: {with_alpha(tokens.text_primary, 0.10)};
        max-width: 70%;
    }}

    /* --- Totals --- */

    QLabel#LedgerTotalLabel {{
        letter-spacing: 0.8px;
        color: {with_alpha(tokens.text_primary, 0.70)};
    }}

    QLabel#LedgerTotalAmount {{
        color: {tokens.text_primary};
    }}

    /* --- Footer --- */

    QLabel#LedgerFooter {{
        letter-spacing: 0.4px;
        color: {with_alpha(tokens.text_primary, 0.55)};
    }}


    /* ============================
       Patents vs Studio Panel
       ============================ */

    /* Track behind each row */
    QFrame#PVSTrack {{
        background-color: {with_alpha(tokens.bg_app, 0.18)};
        border-radius: 4px;
    }}

    /* Fill bar (color depends on row barRole) */
    QWidget#PVSRow[barRole="archive"] QFrame#PVSFill {{
        background-color: {with_alpha(tokens.accent, 0.22)};
        border-radius: 4px;
    }}

    QWidget#PVSRow[barRole="studio"] QFrame#PVSFill {{
        background-color: {with_alpha(tokens.accent_secondary, 0.22)};
        border-radius: 4px;
    }}

    /* Zero marker (only visible when value == 0) */
    QFrame#CostMarker {{
        background-color: {with_alpha(tokens.text_muted, 0.60)};
        border-radius: 2px;
    }}

    QLabel#LedgerDelta[delta="up"] {{
        color: {tokens.accent_tertiary};
    }}

    QLabel#LedgerDelta[delta="down"] {{
        color: {tokens.danger};
    }}

    QLabel#LedgerDelta[delta="neutral"] {{
        color: {with_alpha(tokens.accent_tertiary, 0.55)};
    }}
    /* ============================
    Patents vs Studio Bars
    ============================ */

    QFrame#PVSBar {{
        border-radius: 4px;
    }}

    /* Archive bar */
    QWidget[barRole="archive"] QFrame#PVSBar {{
        background-color: {with_alpha(tokens.accent, 1)};
    }}

    /* Studio bar */
    QWidget[barRole="studio"] QFrame#PVSBar {{
        background-color: {with_alpha(tokens.accent_secondary, 1)};
    }}
    
    /* =========================================
    Ledger-style left indicators
    ========================================= */

    QFrame#LedgerIndicator {{
        background-color: rgba(255, 255, 255, 0.18);
        border-radius: 2px;
    }}

    QFrame#LedgerIndicator[role="print-job"] {{
        background-color: rgba(189, 147, 249, 0.85); /* Dracula accent */
    }}

    /* ============================
    Ledger Bars
    ============================ */

    QFrame#LedgerBarTrack {{
        background-color: {tokens.bg_surface};
        border-radius: 4px;
    }}

    QFrame#LedgerBarFill {{
        background-color: {tokens.accent};
        border-radius: 4px;
    }}

    QFrame#LedgerBarTrack {{
        min-height: 14px;
        max-height: 14px;
    }}

    QFrame#LedgerBarFill {{
        min-height: 14px;
        max-height: 14px;
    }}


    /* ============================
    Archive Status Panel
    ============================ */

    QFrame#ArchiveStatusPanel {{
        background-color: {tokens.bg_surface};
        border-radius: 7px;
    }}

    QWidget[barRole="archive"] QFrame#PVSBar {{
        background-color: {{with_alpha(tokens.accent, 1)}};
    }}

    /* ============================
    Notes Panel
    ============================ */

    QPlainTextEdit#DashboardNotes {{
        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};
        border-radius: 8px;
        padding: 10px;
        font-weight: 400;
     line-height: 1.4;

    }}
    /* --- Dashboard Notes (Dracula) --- */

    QTextEdit#DashboardNotes {{
        background-color: {tokens.bg_surface};
        border: none;
        color: {tokens.text_primary};
        line-height: 1.45;
    }}


    /* ============================
    Replace Paper Dialog
    ============================ */

    QDialog#ReplacePaperDialog {{
    background-color: {tokens.bg_surface};
    }}

    /* Labels */
    QDialog#ReplacePaperDialog QLabel {{
        color: {tokens.text_primary};
    }}

    /* Inputs */
    QDialog#ReplacePaperDialog QLineEdit,
    QDialog#ReplacePaperDialog QDoubleSpinBox {{
        background-color: {tokens.bg_surface};
        color: {tokens.text_primary};
        border: 1px solid {tokens.border};
        border-radius: 6px;
        padding: 6px 8px;
    }}

    /* Buttons */
    QDialog#ReplacePaperDialog QPushButton {{
        padding: 6px 14px;
    }}

    QDialog#ReplacePaperDialog QLineEdit,
    QDialog#ReplacePaperDialog QDoubleSpinBox {{
        min-height: 22px;
        max-height: 22px;
        padding: 3px 5px;
    }}

    #StudioMoodDivider {{
        background-color: rgba(255, 255, 255, 0.08);
        height: 1px;
        margin: 4px 0 8px 0;
    }}

    QToolButton#MediaPrev,
    QToolButton#MediaPlayPause,
    QToolButton#MediaNext {{
        background: transparent;
        border: none;
        padding: 4px;
    }}

    QToolButton#MediaPrev:hover,
    QToolButton#MediaPlayPause:hover,
    QToolButton#MediaNext:hover {{
        background-color: rgba(255, 255, 255, 0.06);
        border-radius: 6px;
    }}

    /* ============================
   Print Economics View
   ============================ */

/* --- View Title --- */
#ViewTitle {{
    font-weight: 600;
    color: {{tokens.text_primary}};
}}

/* --- Filters --- */
#FilterLabel {{
    color: {{tokens.text_muted}};
}}

#FilterCombo {{
    min-width: 110px;
}}

/* --- KPI Strip --- */
#KpiStrip {{
    background-color: {{tokens.bg_surface}};
    border-radius: 12px;
}}

#KpiLabel {{
    color: {{tokens.text_muted}};
}}

#KpiValue {{
    font-weight: 600;
    color: {{tokens.text_primary}};
}}

/* --- Section Titles --- */
#SectionTitle {{
    font-weight: 600;
    color: {{tokens.text_primary}};
    margin-top: 8px;
}}

/* --- Cost Breakdown --- */
#CostBar {{
    background-color: {{tokens.bg_surface_alt}};
    border-radius: 8px;
}}

#CostLegend {{
    color: {{tokens.text_muted}};
}}

/* --- Economics Table --- */
#EconomicsTable {{
    background: transparent;
    gridline-color: {{tokens.border_subtle}};
}}

#EconomicsTable::item {{
    padding: 6px 8px;
    color: {{tokens.text_primary}};
}}

#EconomicsTable::item:selected {{
    background-color: {{tokens.accent_primary_muted}};
}}

#EconomicsTable QHeaderView::section {{
    background: transparent;
    color: {{tokens.text_muted}};
    font-weight: 500;
    padding: 6px 8px;
    border: none;
}}


    """