from __future__ import annotations

from pathlib import Path
from importlib import resources


def asset_path(*parts: str) -> str:
    """
    Return an absolute filesystem path to a bundled asset.
    Works for editable installs, namespace packages, and packaging.
    """
    base = resources.files("studiohub")

    path = base.joinpath("assets")
    for part in parts:
        path = path.joinpath(part)

    return str(Path(path))
