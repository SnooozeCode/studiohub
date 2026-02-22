from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import socket


SCHEMA = "index_log_v1"


def append_index_log(
    *,
    log_path: Path,
    source: str,
    archive: int,
    studio: int,
    duration_ms: int,
    status: str,
) -> None:
    """
    Append a single index operation entry to a JSONL index log.

    This log is:
    - local to the machine
    - append-only
    - not shared across devices
    """

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "schema": SCHEMA,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "machine": socket.gethostname(),
            "source": source,              # startup | refresh_all | manual | etc
            "archive_count": archive,
            "studio_count": studio,
            "duration_ms": duration_ms,
            "status": status,              # OK | ERROR
        }

        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    except Exception as e:
        print(f"[WARN] Failed to write index log: {e}")
        # Non-critical, continue
