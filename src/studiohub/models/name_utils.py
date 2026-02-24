
import re

def normalize_name(raw: str) -> str:
    """
    Convert filesystem-safe names into human-readable titles.

    Examples:
      Anatomical_Body -> Anatomical Body
      antique-parchment -> Antique Parchment
    """
    if not raw:
        return ""

    s = raw.replace("_", " ").replace("-", " ")
    s = " ".join(s.split())  # collapse double spaces
    return s.title()


# =====================================================
# Franchise aliases (filesystem-safe → display name)
# =====================================================


ACRONYMS = {"nasa", "cs", "fps"}

FRANCHISE_ALIASES = {
    "ram": "Rick and Morty",
    "rickandmorty": "Rick and Morty",
    "cs": "Counter-Strike",
    "counterstrike": "Counter-Strike",
    "callofduty": "Call of Duty",
}


def _split_words(text: str) -> list[str]:
    """
    Splits CamelCase, numbers, and glued words.
    """
    return re.findall(
        r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[0-9]+",
        text,
    )


def _normalize_words(text: str) -> str:
    words = _split_words(text.replace("_", " "))
    out = []
    for w in words:
        if w.lower() in ACRONYMS:
            out.append(w.upper())
        else:
            out.append(w.capitalize())
    return " ".join(out)


def normalize_patent_name(raw: str) -> str:
    """
    Normalize patent filenames with background separator preserved.

    Examples:
      AnatomicalBody-Blueprint
        -> Anatomical Body - Blueprint

      AnatomicalBody-AntiqueParchment
        -> Anatomical Body - Antique Parchment
    """
    if not raw:
        return ""

    # Split patent vs background ON FIRST HYPHEN ONLY
    if "-" in raw:
        left, right = raw.split("-", 1)
    else:
        left, right = raw, ""

    # Normalize patent title
    left_words = _split_words(left.replace("_", " "))
    left_norm = " ".join(
        w.upper() if w.lower() in ACRONYMS else w.capitalize()
        for w in left_words
    )

    if not right:
        return left_norm

    # Normalize background
    right_words = _split_words(right.replace("_", " "))
    right_norm = " ".join(
        w.upper() if w.lower() in ACRONYMS else w.capitalize()
        for w in right_words
    )

    return f"{left_norm} - {right_norm}"


def normalize_studio_name(raw: str) -> str:
    """
    Normalize studio poster names.

    Examples:
      RAM_GetYourShit_Alt
        -> Rick and Morty - Get Your Shit Alt

      CS_Mirage
        -> CS - Mirage

      CallOfDuty_ModernWarfare
        -> Call of Duty - Modern Warfare
    """
    if not raw:
        return ""

    s = raw.strip()

    # Filesystem-normalized key for alias matching
    fs = s.lower().replace("_", "").replace("-", "").replace(" ", "")

    # Alias-based franchise detection
    for key, display in FRANCHISE_ALIASES.items():
        if fs.startswith(key):
            remainder = s[len(key):].lstrip("_- ")
            subject = _normalize_words(remainder)
            return f"{display} - {subject}" if subject else display

    # Fallback: split on first underscore
    if "_" in s:
        left, right = s.split("_", 1)
        left_norm = _normalize_words(left)
        right_norm = _normalize_words(right)
        return f"{left_norm} - {right_norm}"

    # Final fallback
    return _normalize_words(s)

