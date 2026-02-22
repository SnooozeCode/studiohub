from __future__ import annotations

from pathlib import Path
import json


def load_poster_index(path: str | Path) -> dict:
    """Load the cached poster index from an explicit path."""
    p = Path(path)
    
    if not p.exists() or p.is_dir():
        return {"posters": {"archive": {}, "studio": {}}}
    
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception as e:
        print(f"[WARN] Failed to load poster index from {path}: {e}")
        # Could emit to status bar if we had a reference
    
    return {"posters": {"archive": {}, "studio": {}}}