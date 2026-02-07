from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from PySide6 import QtCore


class IndexLogModelQt(QtCore.QObject):
    data_loaded = QtCore.Signal(list)
    error = QtCore.Signal(str)

    def __init__(self, *, logs_root: Path, parent=None):
        super().__init__(parent)
        self.log_path = logs_root / "index_log.jsonl"

    def load(self) -> None:
        rows: List[Dict[str, Any]] = []

        try:
            if not self.log_path.exists():
                self.data_loaded.emit([])
                return

            with self.log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    rows.append({
                        "Time": rec.get("timestamp", ""),
                        "Source": rec.get("source", ""),
                        "Patents": rec.get("patents_count", 0),
                        "Studio": rec.get("studio_count", 0),
                        "Duration (ms)": rec.get("duration_ms", 0),
                        "Status": rec.get("status", ""),
                    })



            # newest first
            rows.reverse()

            self.data_loaded.emit(rows)

        except Exception as e:
            self.error.emit(str(e))
