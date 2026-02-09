from __future__ import annotations

from pathlib import Path
from typing import Mapping

from studiohub.ui.layout.row_layout import build_row_density_qss  # keeps existing density behavior



_QSS_ROOT = Path(__file__).resolve().parents[1] / "qss"
_CORE = _QSS_ROOT / "core.qss"

def _read_qss(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _resolve_imports(qss: str, *, base_dir: Path) -> str:
    # Qt supports @import in QSS, but we compile to a single string for token substitution.
    out_lines: list[str] = []
    for line in qss.splitlines():
        m = line.strip().startswith("@import")
        if m:
            # @import "file.qss";
            import_match = __import_re.match(line.strip())
            if import_match:
                rel = import_match.group(1)
                imported = _read_qss(base_dir / rel)
                out_lines.append(f"/* --- begin import: {rel} --- */")
                out_lines.append(_resolve_imports(imported, base_dir=(base_dir / rel).parent))
                out_lines.append(f"/* --- end import: {rel} --- */")
                continue
        out_lines.append(line)
    return "\n".join(out_lines) + "\n"

import re as _re
__import_re = _re.compile(r'@import\s+"([^"]+)"\s*;?')

def build_stylesheet(tokens) -> str:
    """
    Build the full application stylesheet from QSS sources.

    - Loads qss/core.qss (and its @imports) from studiohub.style.qss/
    - Replaces __TOKEN__ placeholders with values from ThemeTokens
    - Appends row density QSS (existing behavior)
    """
    if not _CORE.exists():
        raise FileNotFoundError(f"Missing core QSS at {_CORE}")

    compiled = _resolve_imports(_read_qss(_CORE), base_dir=_CORE.parent)

    # Map ThemeTokens attributes to placeholder names: __BG_APP__, etc.
    # Any ThemeTokens field can be used as __FIELDNAME__ in QSS (uppercased).
    mapping: Mapping[str, str] = {k.upper(): str(v) for k, v in getattr(tokens, "__dict__", {}).items()}

    def repl(match):
        key = match.group(1)
        if key not in mapping:
            # fail loud: no fallbacks
            raise KeyError(f"Unknown stylesheet token placeholder __{key}__")
        return mapping[key]

    compiled = _re.sub(r"__([A-Z0-9_]+)__", repl, compiled)

    Path("compiled.qss").write_text(compiled, encoding="utf-8")

    # Keep existing density behavior (not theme-related)
    compiled += "\n/* --- row density --- */\n" + build_row_density_qss() + "\n"
    return compiled
