# studiohub/ui/dashboard/dashboard_panels.py

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QFrame,
)

from studiohub.ui.dashboard.dashboard_container import DashboardSurface
from studiohub.services.dashboard.snapshot import (
    CompletenessSlice,
    MonthlyPrintCountSlice,
    MonthlyCostBreakdown,
    StudioMoodSlice,
)

# ==================================================
# Base Dashboard Panel
# ==================================================

class BaseDashboardPanel(QWidget):
    """
    Base class providing standardized typography roles
    for dashboard panels.

    Panels should:
    - set text on these labels
    - hide labels they don't need
    - never style fonts directly
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        self.primary = QLabel()
        self.primary.setObjectName("PanelPrimary")

        self.secondary = QLabel()
        self.secondary.setObjectName("PanelSecondary")
        self.secondary.setWordWrap(True)

        self.meta = QLabel()
        self.meta.setObjectName("PanelMeta")

        self.placeholder = QLabel("—")
        self.placeholder.setObjectName("PanelPlaceholder")
        self.placeholder.hide()

        layout.addWidget(self.primary)
        layout.addWidget(self.secondary)
        layout.addWidget(self.meta)
        layout.addWidget(self.placeholder)
        layout.addStretch()

# ==================================================
# Action Base Dashboard Panel
# ==================================================

class BaseActionPanel(QWidget):
    triggered = Signal()

    def __init__(self, title: str, subtitle: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("ActionPanel")
        self.setCursor(Qt.PointingHandCursor)

        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._surface = DashboardSurface(self)
        self._surface.setProperty("role", "panel")

        self._surface.style().unpolish(self._surface)
        self._surface.style().polish(self._surface)

        surface_layout = QVBoxLayout()
        surface_layout.setContentsMargins(16, 16, 16, 16)
        surface_layout.setSpacing(6)

        self._surface.setLayout(surface_layout)

        self._title = QLabel(title)
        self._title.setObjectName("ActionTitle")
        self._title.setAlignment(Qt.AlignCenter)

        surface_layout.addStretch()
        surface_layout.addWidget(self._title)

        if subtitle:
            self._subtitle = QLabel(subtitle)
            self._subtitle.setObjectName("ActionSubtitle")
            self._subtitle.setAlignment(Qt.AlignCenter)
            surface_layout.addWidget(self._subtitle)

        surface_layout.addStretch()

        outer.addWidget(self._surface)


    def mousePressEvent(self, event):
        self.triggered.emit()
        super().mousePressEvent(event)


# ==================================================
# Content Health
# ==================================================

class ContentHealthPanel(BaseDashboardPanel):
    """
    Combined health view for Archive + Studio content.
    """
    def set_data(
        self,
        archive: CompletenessSlice,
        studio: CompletenessSlice,
    ) -> None:
        # Compute combined view (simple, explicit)
        archive_pct = int(archive.complete_fraction * 100)
        studio_pct = int(studio.complete_fraction * 100)

        # Primary: worst-case health (for now)
        overall_pct = min(archive_pct, studio_pct)
        self.primary.setText(f"{overall_pct}% healthy")

        # Secondary: explicit breakdown
        self.secondary.setText(
            f"Archive: {archive_pct}% · "
            f"{archive.issues} issues · "
            f"{archive.missing_files} missing\n"
            f"Studio: {studio_pct}% · "
            f"{studio.issues} issues · "
            f"{studio.missing_files} missing"
        )

        self.meta.setText("")
        self.placeholder.hide()

# ==================================================
# Print Readiness Panel
# ==================================================

class PrintReadinessPanel(BaseDashboardPanel):
    def set_data(self, data: CompletenessSlice) -> None:
        percent = int(data.complete_fraction * 100)

        self.primary.setText(f"{percent}%")

        self.secondary.setText(
            f"{data.issues} issues · {data.missing_files} missing files"
        )

        self.meta.setText("Print readiness")

# ==================================================
# New Print Job Panel
# ==================================================

class NewPrintJobPanel(BaseActionPanel):
    def __init__(self, parent=None):
        super().__init__(
            title="New Print Job",
            subtitle="Create a new print job",
            parent=parent,
        )

# ==================================================
# Open Print Log Panel
# ==================================================

class OpenPrintLogPanel(BaseActionPanel):
    def __init__(self, parent=None):
        super().__init__(
            title="Open Print Log",
            subtitle="View all print jobs",
            parent=parent,
        )

# ==================================================
# Monthly Print Counts
# ==================================================

class MonthlyPrintCountsPanel(BaseDashboardPanel):
    def set_data(self, data: MonthlyPrintCountSlice) -> None:
        total = data.archive_this_month + data.studio_this_month

        self.primary.setText(f"{total} prints")

        self.secondary.setText(
            f"Archive: {data.archive_this_month} · "
            f"Studio: {data.studio_this_month}"
        )

        self.meta.setText(f"This month · Δ {data.delta_total:+d}")
        self.placeholder.hide()

# ==================================================
# Monthly Cost Panel
# ==================================================

class MonthlyCostPanel(BaseDashboardPanel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def set_data(self, data: MonthlyCostBreakdown) -> None:
        self.primary.setText(f"${data.total:.2f}")

        self.secondary.setText(
            f"Prints: {data.prints}\n"
            f"Ink: ${data.ink:.2f}\n"
            f"Paper: ${data.paper:.2f}\n"
            f"Shipping: ${data.shipping_supplies:.2f}"
        )

        self.meta.setText("This month")
        self.placeholder.hide()

# ==================================================
# Recent Activity Panels
# ==================================================

class RecentPrintJobsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._list = QListWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self._list)

    def set_data(self, jobs: list[dict]) -> None:
        self._list.clear()
        for job in jobs:
            ts = job.get("timestamp", "")
            label = job.get("label", "Print job")
            self._list.addItem(f"{ts} · {label}")


class RecentIndexEventsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._list = QListWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self._list)

    def set_data(self, events: list[dict]) -> None:
        self._list.clear()
        for evt in events:
            ts = evt.get("timestamp", "")
            status = evt.get("status", "")
            self._list.addItem(QListWidgetItem(f"{ts} · {status}"))


# ==================================================
# KPI / Last Index Panel
# ==================================================

class StudioMoodPanel(BaseDashboardPanel):
    def set_data(self, data: StudioMoodSlice) -> None:
        self.primary.setText(data.label)
        self.secondary.hide()
        self.meta.hide()

        # semantic hook for QSS
        self.primary.setProperty("mood", data.mood)
        self.primary.style().polish(self.primary)


class RevenuePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._label = QLabel("Revenue: —")
        layout = QVBoxLayout(self)
        layout.addWidget(self._label)

    def set_data(self, data) -> None:
        # placeholder until snapshot.revenue exists
        self._label.setText(str(data))


class NotesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._label = QLabel("Notes")
        self._label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._label)

    def set_data(self, data) -> None:
        self._label.setText(data or "")
