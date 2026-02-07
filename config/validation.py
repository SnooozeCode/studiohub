from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def assert_runtime_not_in_studio(cfg: Dict[str, Any]) -> None:
    runtime_raw = cfg.get("paths", {}).get("runtime_root", "").strip()
    if not runtime_raw:
        return

    runtime = Path(runtime_raw).expanduser()

    studio_raw = cfg.get("paths", {}).get("studio_root", "").strip()
    if not studio_raw:
        return

    studio = Path(studio_raw).expanduser()
    if not studio.exists():
        return

    try:
        runtime.resolve().relative_to(studio.resolve())
        raise RuntimeError(
            f"Invalid configuration: runtime_root is inside studio_root\n"
            f"runtime_root: {runtime}\n"
            f"studio_root:  {studio}"
        )
    except ValueError:
        pass
