from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any
from copy import deepcopy

from .defaults import DEFAULT_CONFIG
from studiohub.utils.logging import get_logger

logger = get_logger(__name__)



def load_or_create(path: Path) -> Dict[str, Any]:
    if not path.exists():
        logger.info(f"Config not found, creating default at {path}")
        write_config(path, DEFAULT_CONFIG)
        return deepcopy(DEFAULT_CONFIG)

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"[Config] Failed to load config: {e}")
        logger.warning("[Config] Using in-memory defaults ONLY")
        return deepcopy(DEFAULT_CONFIG)

    merged = merge_defaults(data)
    write_config(path, merged)
    return merged


def write_config(path: Path, data: Dict[str, Any]) -> None:
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Config written to {path}")
    except Exception as e:
        logger.error(f"Failed to write config: {e}", exc_info=True)


def merge_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(DEFAULT_CONFIG)

    for section, values in data.items():
        if isinstance(values, dict):
            merged.setdefault(section, {}).update(values)
        else:
            merged[section] = values

    return merged
