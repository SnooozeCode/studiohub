from __future__ import annotations

import json
import socket
from pathlib import Path
from datetime import datetime
from typing import Optional, Iterable

# =====================================================
# Schema Constants
# =====================================================

PRINT_LOG_SCHEMA_V1 = "print_log_v1"
PRINT_LOG_SCHEMA_V2 = "print_log_v2"


# =====================================================
# Public API
# =====================================================

def append_print_log(
    *,
    log_path: Path,
    mode: str,
    size: str,
    print_cost_usd: float,

    # --- v2 inputs (preferred)
    files: Optional[Iterable[dict]] = None,

    # --- v2 analytics flags
    is_reprint: bool = False,
    waste_incurred: Optional[bool] = None,

    # --- v1 legacy inputs (fallback)
    file_1: Optional[str] = None,
    file_2: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """
    Append a print log entry.

    - Uses print_log_v2 when `files` is provided
    - Falls back to print_log_v1 for legacy callers
    - Never mutates or migrates existing log entries
    """

    try:
        timestamp = datetime.now().isoformat(timespec="seconds")
        machine = socket.gethostname()

        # =================================================
        # v2 Path (authoritative, deterministic reprint)
        # =================================================

        if files is not None:
            record = {
                "schema": PRINT_LOG_SCHEMA_V2,
                "timestamp": timestamp,
                "machine": machine,
                "mode": mode,
                "size": size,
                "files": list(files),
                "print_cost_usd": float(print_cost_usd),
                "is_reprint": bool(is_reprint),
                "waste_incurred": bool(waste_incurred if waste_incurred is not None else is_reprint),
            }

        # =================================================
        # v1 Legacy Path (unchanged behavior)
        # =================================================

        else:
            record = {
                "schema": PRINT_LOG_SCHEMA_V1,
                "timestamp": timestamp,
                "machine": machine,
                "source": source,
                "mode": mode,
                "size": size,
                "file_1": file_1,
                "file_2": file_2,
                "print_cost_usd": float(print_cost_usd),
                "is_reprint": bool(is_reprint),
                "waste_incurred": bool(waste_incurred if waste_incurred is not None else is_reprint),
            }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    except Exception as e:
        print(f"[PrintLog] Failed to write log: {e}")
        return {}
