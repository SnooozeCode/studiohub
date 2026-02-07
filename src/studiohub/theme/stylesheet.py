from studiohub.ui.rows.layout import build_row_density_qss

from .styles import (
    base,
    typography,
    buttons,
    forms,
    panels,
    tables,
    sidebar,
    dialogs,
    queue,
)

from .views import (
    dashboard,
    settings,
)

def build_stylesheet(tokens) -> str:
    return (
        # ---- global styles ----
        base.build(tokens)
        + typography.build_qss(tokens)
        + buttons.build(tokens)
        + forms.build(tokens)
        + panels.build(tokens)
        + tables.build(tokens)
        + sidebar.build(tokens)
        + dialogs.build(tokens)
        + queue.build(tokens)

        # ---- feature styles ----
        + dashboard.build(tokens)
        + settings.build(tokens)

        + build_row_density_qss()
    )
