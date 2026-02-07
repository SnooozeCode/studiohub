def with_alpha(hex_color: str, alpha: float) -> str:
    """
    Convert hex (#RRGGBB) to rgba(r,g,b,a)
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
