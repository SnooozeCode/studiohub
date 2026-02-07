def build(tokens) -> str:
    return f"""
    /* ============================
    Queue Rows
    ============================ */

    QFrame[role="queue-indicator"] {{
        background-color: {tokens.accent};
        border-radius: 2px;
    }}

    QFrame[role="queue-row"][selected="true"] QFrame[role="queue-indicator"] {{
        background-color: {tokens.accent};
    }}

    QLabel[role="queue-badge"] {{
        background-color: {tokens.accent};
        color: {tokens.text_primary};
    }}
    """
