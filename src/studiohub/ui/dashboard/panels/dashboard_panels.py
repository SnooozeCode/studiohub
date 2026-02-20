# studiohub/ui/dashboard/dashboard_panels.py

from __future__ import annotations

from PySide6.QtGui import QTextCursor, QTextCharFormat, QFont, QAction, QPainter, QColor
from PySide6.QtCore import QSettings, QTimer, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QFrame,
    QTextEdit,
    QToolBar,
    QPlainTextEdit,
    QProgressBar,
)

from studiohub.ui.dashboard.dashboard_container import DashboardSurface
from studiohub.services.dashboard.snapshot import (
    CompletenessSlice,
    MonthlyPrintCountSlice,
    MonthlyCostBreakdown,
    StudioMoodSlice,
    PaperSlice,
    InkSlice,
)

from studiohub.style.typography.rules import apply_typography


# ==================================================
# Base Dashboard Panel
# ==================================================

class BaseDashboardPanel(QWidget):
    """
    Base class providing standardized typography roles
    for dashboard panels.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)  # NO PADDING - container provides it

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

        surface_layout = self._surface.layout()
        surface_layout.setSpacing(6)

        self._title = QLabel(title)
        self._title.setObjectName("ActionTitle")
        apply_typography(self._title, "h2")
        self._title.setAlignment(Qt.AlignCenter)

        surface_layout.addStretch()
        surface_layout.addWidget(self._title)

        if subtitle:
            self._subtitle = QLabel(subtitle)
            self._subtitle.setObjectName("ActionSubtitle")
            apply_typography(self._subtitle, "h6")
            self._subtitle.setAlignment(Qt.AlignCenter)
            surface_layout.addWidget(self._subtitle)

        surface_layout.addStretch()

        outer.addWidget(self._surface)

    def mousePressEvent(self, event):
        """Handle mouse press to emit triggered signal."""
        self.triggered.emit()
        super().mousePressEvent(event)
    # ===================================

# ==================================================
# Content Health Panel
# ==================================================
class ContentHealthPanel(QWidget):
    """
    Panel showing Archive and Studio poster counts and completion progress.
    - Shows total poster count for each source
    - Progress bar shows % of posters with no missing files
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ContentHealthPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Archive section
        archive_header = QHBoxLayout()
        archive_header.setContentsMargins(0, 0, 0, 0)
        
        archive_label = QLabel("Archive:")
        apply_typography(archive_label, "body")
        archive_label.setObjectName("HealthLabel")
        
        self.archive_count = QLabel("0 posters")
        self.archive_count.setObjectName("HealthCount")
        self.archive_count.setAlignment(Qt.AlignRight)
        
        archive_header.addWidget(archive_label)
        archive_header.addStretch()
        archive_header.addWidget(self.archive_count)
        apply_typography(self.archive_count, "body")
        layout.addLayout(archive_header)

        # Archive progress bar
        self.archive_progress = QProgressBar()
        self.archive_progress.setObjectName("ArchiveHealthProgress")
        self.archive_progress.setRange(0, 100)
        self.archive_progress.setValue(0)
        self.archive_progress.setTextVisible(False)
        self.archive_progress.setFixedHeight(20)
        layout.addWidget(self.archive_progress)

        # Archive details (issues/missing)
        self.archive_details = QLabel("0 issues · 0 missing")
        self.archive_details.setObjectName("HealthDetails")
        apply_typography(self.archive_details, "small")
        layout.addWidget(self.archive_details)

        layout.addSpacing(8)  # Space between sections

        # Studio section
        studio_header = QHBoxLayout()
        studio_header.setContentsMargins(0, 0, 0, 0)
        
        studio_label = QLabel("Studio:")
        studio_label.setObjectName("HealthLabel")
        apply_typography(studio_label, "body")
        
        self.studio_count = QLabel("0 posters")
        self.studio_count.setObjectName("HealthCount")
        self.studio_count.setAlignment(Qt.AlignRight)
        
        studio_header.addWidget(studio_label)
        studio_header.addStretch()
        studio_header.addWidget(self.studio_count)
        apply_typography(self.studio_count, "body")
        layout.addLayout(studio_header)

        # Studio progress bar
        self.studio_progress = QProgressBar()
        self.studio_progress.setObjectName("StudioHealthProgress")
        self.studio_progress.setRange(0, 100)
        self.studio_progress.setValue(0)
        self.studio_progress.setTextVisible(False)
        self.studio_progress.setFixedHeight(20)
        layout.addWidget(self.studio_progress)

        # Studio details (issues/missing)
        self.studio_details = QLabel("0 issues · 0 missing")
        self.studio_details.setObjectName("HealthDetails")
        apply_typography(self.studio_details, "small")
        layout.addWidget(self.studio_details)

    def set_data(self, archive: CompletenessSlice, studio: CompletenessSlice) -> None:
        """
        Update panel with archive and studio data.
        Now using total_posters from the slice.
        """
        
        # Archive
        archive_pct = int(archive.complete_fraction * 100)
        self.archive_count.setText(f"{archive.total_posters}")
        self.archive_progress.setValue(archive_pct)
        self.archive_details.setText(f"{archive.issues} issues · {archive.missing_files} missing")
        
        # Studio
        studio_pct = int(studio.complete_fraction * 100)
        self.studio_count.setText(f"{studio.total_posters}")
        self.studio_progress.setValue(studio_pct)
        self.studio_details.setText(f"{studio.issues} issues · {studio.missing_files} missing")

# ==================================================
# Print Readiness Panel
# ==================================================
class PrintReadinessPanel(QWidget):
    """
    Panel showing print readiness based on Paper and Ink levels.
    Each shows its own last replaced date.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PrintReadinessPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Paper section
        paper_label_row = QHBoxLayout()
        paper_label_row.setContentsMargins(0, 0, 0, 0)
        paper_label = QLabel("Paper:")
        apply_typography(paper_label, "body")
        paper_label.setObjectName("ReadinessLabel")

        self.paper_value = QLabel("56%")
        apply_typography(self.paper_value, "body")
        self.paper_value.setObjectName("ReadinessValue")
        self.paper_value.setAlignment(Qt.AlignRight)

        paper_label_row.addWidget(paper_label)
        paper_label_row.addStretch()
        paper_label_row.addWidget(self.paper_value)
        layout.addLayout(paper_label_row)

        # Paper progress bar
        self.paper_progress = QProgressBar()
        self.paper_progress.setObjectName("PaperProgress")
        self.paper_progress.setRange(0, 100)
        self.paper_progress.setValue(56)
        self.paper_progress.setTextVisible(False)
        self.paper_progress.setFixedHeight(20)
        layout.addWidget(self.paper_progress)

        # Paper last replaced
        self.paper_last = QLabel("Last replaced: Feb 03, 2026 · 12:09 PM")
        self.paper_last.setObjectName("ReadinessLast")
        apply_typography(self.paper_last, "small")
        layout.addWidget(self.paper_last)

        layout.addSpacing(8)  # Space between paper and ink

        # Ink section
        ink_label_row = QHBoxLayout()
        ink_label_row.setContentsMargins(0, 0, 0, 0)
        ink_label = QLabel("Ink:")
        ink_label.setObjectName("ReadinessLabel")
        apply_typography(ink_label, "body")

        self.ink_value = QLabel("86%")
        apply_typography(self.ink_value, "body")
        self.ink_value.setObjectName("ReadinessValue")
        self.ink_value.setAlignment(Qt.AlignRight)

        ink_label_row.addWidget(ink_label)
        ink_label_row.addStretch()
        ink_label_row.addWidget(self.ink_value)
        layout.addLayout(ink_label_row)

        # Ink progress bar
        self.ink_progress = QProgressBar()
        self.ink_progress.setObjectName("InkProgress")
        self.ink_progress.setRange(0, 100)
        self.ink_progress.setValue(86)
        self.ink_progress.setTextVisible(False)
        self.ink_progress.setFixedHeight(20)
        layout.addWidget(self.ink_progress)

        # Ink last replaced
        self.ink_last = QLabel("Last replaced: Feb 01, 2026 · 3:30 PM")
        self.ink_last.setObjectName("ReadinessLast")
        apply_typography(self.ink_last, "small")
        layout.addWidget(self.ink_last)

    def set_data(self, paper_data: PaperSlice, ink_data: InkSlice) -> None:
        """Update with paper and ink data."""
        # Paper
        paper_pct = paper_data.remaining_percent
        self.paper_value.setText(f"{paper_pct}%")
        self.paper_progress.setValue(paper_pct)
        
        if paper_data.last_replaced:
            self.paper_last.setText(
                f"Last replaced: {paper_data.last_replaced.strftime('%b %d, %Y · %I:%M %p')}"
            )
        else:
            self.paper_last.setText("Last replaced: Never")
        
        # Ink
        ink_pct = ink_data.remaining_percent
        self.ink_value.setText(f"{ink_pct}%")
        self.ink_progress.setValue(ink_pct)
        
        if ink_data.last_replaced:
            self.ink_last.setText(
                f"Last replaced: {ink_data.last_replaced.strftime('%b %d, %Y · %I:%M %p')}"
            )
        else:
            self.ink_last.setText("Last replaced: Never")


# ==================================================
# Studio Mood Panel
# ui/dashboard/panels/studio_mood.py
# ==================================================

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
# Monthly Print Counts Panel
# ==================================================
class MonthlyPrintCountsPanel(QWidget):
    """
    Archive vs Studio panel with colored progress bars and deltas.
    Consistent spacing throughout.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MonthlyPrintCountsPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Subtitle
        subtitle = QLabel("How many prints from each source.")
        subtitle.setObjectName("DashboardSubtitle")
        apply_typography(subtitle, "caption")
        subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        subtitle.setFixedHeight(14)
        layout.addWidget(subtitle)

        # Spacing below subtitle
        layout.addSpacing(8)

        # Archive row
        self.archive_bar = PrintCountBar("ARCHIVE", "archive")
        layout.addWidget(self.archive_bar)

        # Spacing between progress bars
        layout.addSpacing(4)

        # Studio row
        self.studio_bar = PrintCountBar("STUDIO", "studio")
        layout.addWidget(self.studio_bar)

        # Spacing above divider
        layout.addSpacing(8)

        # Divider
        divider = QFrame()
        divider.setObjectName("DashboardDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # Spacing below divider
        layout.addSpacing(8)

        # Total row
        total_row = QWidget()
        total_row.setObjectName("TotalRow")
        total_row.setFixedHeight(24)  # Slightly shorter than progress bars
        total_layout = QHBoxLayout(total_row)
        total_layout.setContentsMargins(8, 0, 8, 0)
        total_layout.setSpacing(4)

        self.total_label = QLabel("TOTAL PRINTS")
        apply_typography(self.total_label, "body")
        self.total_label.setObjectName("TotalLabel")
        self.total_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.total_label.setFixedHeight(24)

        total_layout.addWidget(self.total_label)
        total_layout.addStretch()

        self.total_value = QLabel("0")
        apply_typography(self.total_value, "body")
        self.total_value.setObjectName("TotalValue")
        self.total_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_value.setFixedHeight(24)
        total_layout.addWidget(self.total_value)

        layout.addWidget(total_row)

        # Spacing above footer
        layout.addSpacing(4)

        # Footer - aligned right
        self.footer = QLabel("vs last month")
        self.footer.setObjectName("CountsFooter")
        self.footer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        apply_typography(self.footer, "small")
        self.footer.setFixedHeight(16)
        layout.addWidget(self.footer)

        # No stretch at the bottom - let it be natural

    def set_data(self, data: MonthlyPrintCountSlice) -> None:
        total = data.archive_this_month + data.studio_this_month
        
        self.archive_bar.set_values(
            data.archive_this_month, 
            data.delta_archive,
            total
        )
        self.studio_bar.set_values(
            data.studio_this_month, 
            data.delta_studio,
            total
        )
        
        # Format total with delta
        if data.delta_total != 0:
            delta_sign = "+" if data.delta_total > 0 else ""
            self.total_value.setText(f"{total} ({delta_sign}{data.delta_total})")
        else:
            self.total_value.setText(str(total))

class PrintCountBar(QWidget):
    """
    Progress bar with integrated label and delta.
    Uses QProgressBar with stacked labels on top.
    """

    def __init__(self, label: str, bar_type: str, parent=None):
        super().__init__(parent)
        self.setObjectName(f"PrintCountBar_{bar_type}")
        self.setFixedHeight(32)
        
        self._bar_type = bar_type
        self._percentage = 0
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Progress bar - ensure it fills the entire height
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName(f"PrintCountProgress_{bar_type}")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(32)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Create a container for labels that sits on top
        self.label_container = QWidget(self.progress_bar)
        self.label_container.setGeometry(0, 0, self.progress_bar.width(), 32)
        self.label_container.setAttribute(Qt.WA_TranslucentBackground)
        
        # Use QVBoxLayout with center alignment
        container_layout = QVBoxLayout(self.label_container)
        container_layout.setContentsMargins(8, 0, 8, 0)
        container_layout.setAlignment(Qt.AlignCenter)
        
        # Horizontal layout for the actual content
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        # Label (left side)
        self.label = QLabel(label)
        apply_typography(self.label, "body")
        self.label.setObjectName("PrintCountBarLabel")
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        content_layout.addWidget(self.label)

        content_layout.addStretch()

        # Value
        self.value_label = QLabel("0")
        apply_typography(self.value_label, "body")
        self.value_label.setObjectName("PrintCountBarValue")
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        content_layout.addWidget(self.value_label)

        # Delta
        self.delta_label = QLabel("")
        apply_typography(self.delta_label, "body")
        self.delta_label.setObjectName("PrintCountBarDelta")
        self.delta_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        content_layout.addWidget(self.delta_label)

        container_layout.addLayout(content_layout)
        layout.addWidget(self.progress_bar)

    def resizeEvent(self, event):
        """Update label container geometry when widget is resized."""
        super().resizeEvent(event)
        self.label_container.setGeometry(0, 0, self.progress_bar.width(), 32)

    def set_values(self, value: int, delta: int, total: int):
        """Set the current value, delta, and total for scaling."""
        self._percentage = int((value / max(total, 1)) * 100)
        self.progress_bar.setValue(self._percentage)
        
        # Update text
        self.value_label.setText(str(value))
        
        if delta != 0:
            delta_sign = "+" if delta > 0 else ""
            self.delta_label.setText(f"({delta_sign}{delta})")
        else:
            self.delta_label.setText("")

# ==================================================
# Monthly Cost Panel - WITH COLORED INDICATORS
# ==================================================
class MonthlyCostPanel(QWidget):
    """
    Monthly Production Cost panel with colored indicators.
    Matches the screenshot with colored markers for each row.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MonthlyCostPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Subtitle
        subtitle = QLabel("Production cost across all prints.")
        subtitle.setObjectName("DashboardSubtitle")
        apply_typography(subtitle, "caption")
        subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        subtitle.setFixedHeight(14)
        layout.addWidget(subtitle)

        # Paper row with colored indicator
        paper_row = QHBoxLayout()
        paper_row.setContentsMargins(0, 0, 0, 0)
        paper_row.setSpacing(8)

        # Colored indicator for Paper
        paper_indicator = QFrame()
        paper_indicator.setObjectName("CostIndicator")
        paper_indicator.setProperty("costType", "paper")
        paper_indicator.setFixedSize(12, 12)
        paper_indicator.setFrameShape(QFrame.NoFrame)

        paper_label = QLabel("Paper")
        apply_typography(paper_label, "body")
        paper_label.setObjectName("CostLabel")
        paper_label.setAlignment(Qt.AlignVCenter)

        self.paper_value = QLabel("$0.00")
        apply_typography(self.paper_value, "body")
        self.paper_value.setObjectName("CostValue")
        self.paper_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        paper_row.addWidget(paper_indicator)
        paper_row.addWidget(paper_label)
        paper_row.addStretch()
        paper_row.addWidget(self.paper_value)
        layout.addLayout(paper_row)

        # Ink row with colored indicator
        ink_row = QHBoxLayout()
        ink_row.setContentsMargins(0, 0, 0, 0)
        ink_row.setSpacing(8)

        # Colored indicator for Ink
        ink_indicator = QFrame()
        ink_indicator.setObjectName("CostIndicator")
        ink_indicator.setProperty("costType", "ink")
        ink_indicator.setFixedSize(12, 12)
        ink_indicator.setFrameShape(QFrame.NoFrame)

        ink_label = QLabel("Ink")
        apply_typography(ink_label, "body")
        ink_label.setObjectName("CostLabel")
        ink_label.setAlignment(Qt.AlignVCenter)

        self.ink_value = QLabel("$0.00")
        apply_typography(self.ink_value, "body")
        self.ink_value.setObjectName("CostValue")
        self.ink_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        ink_row.addWidget(ink_indicator)
        ink_row.addWidget(ink_label)
        ink_row.addStretch()
        ink_row.addWidget(self.ink_value)
        layout.addLayout(ink_row)

        # Shipping row with colored indicator
        shipping_row = QHBoxLayout()
        shipping_row.setContentsMargins(0, 0, 0, 0)
        shipping_row.setSpacing(8)

        # Colored indicator for Shipping
        shipping_indicator = QFrame()
        shipping_indicator.setObjectName("CostIndicator")
        shipping_indicator.setProperty("costType", "shipping")
        shipping_indicator.setFixedSize(12, 12)
        shipping_indicator.setFrameShape(QFrame.NoFrame)

        shipping_label = QLabel("Shipping Supplies")
        apply_typography(shipping_label, "body")
        shipping_label.setObjectName("CostLabel")
        shipping_label.setAlignment(Qt.AlignVCenter)

        self.shipping_value = QLabel("$0.00")
        apply_typography(self.shipping_value, "body")
        self.shipping_value.setObjectName("CostValue")
        self.shipping_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        shipping_row.addWidget(shipping_indicator)
        shipping_row.addWidget(shipping_label)
        shipping_row.addStretch()
        shipping_row.addWidget(self.shipping_value)
        layout.addLayout(shipping_row)

        # Divider
        divider = QFrame()
        divider.setObjectName("DashboardDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # Total row
        total_row = QHBoxLayout()
        total_row.setContentsMargins(0, 0, 0, 0)

        total_label = QLabel("TOTAL")
        apply_typography(total_label, "body")
        total_label.setObjectName("TotalLabel")
        total_label.setAlignment(Qt.AlignVCenter)
        total_label.setStyleSheet("font-weight: bold;")

        self.total_value = QLabel("$0.00")
        apply_typography(self.total_value, "body")
        self.total_value.setObjectName("TotalValue")
        self.total_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_value.setStyleSheet("font-weight: bold;")

        total_row.addWidget(total_label)
        total_row.addStretch()
        total_row.addWidget(self.total_value)
        layout.addLayout(total_row)

    def set_data(self, data: MonthlyCostBreakdown) -> None:
        self.paper_value.setText(f"${data.paper:.2f}")
        self.ink_value.setText(f"${data.ink:.2f}")
        self.shipping_value.setText(f"${data.shipping_supplies:.2f}")
        self.total_value.setText(f"${data.total:.2f}")

# ==================================================
# Revenue Panel
# ==================================================
class RevenuePanel(QWidget):
    """
    Revenue panel for dashboard.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RevenuePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # NO PADDING

        self.value_label = QLabel("—")
        self.value_label.setObjectName("RevenueValue")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.value_label)

    def set_data(self, revenue: float | None) -> None:
        if revenue is not None:
            self.value_label.setText(f"${revenue:,.2f}")
        else:
            self.value_label.setText("—")


# ==================================================
# Notes Panel 
# ==================================================
class NotesPanel(QWidget):
    """
    Notes panel - plain text only, no HTML or rich text formatting.
    Completely clears all default styling.
    """

    NOTES_SAVE_DEBOUNCE_MS = 800

    def __init__(self, notes_store, parent=None):
        super().__init__(parent)
        self.setObjectName("NotesPanel")

        self._store = notes_store
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setObjectName("NotesEdit")
        self.notes_edit.setPlaceholderText("Write your notes here...")
        apply_typography(self.notes_edit, "body")
        self.notes_edit.setFrameStyle(QFrame.NoFrame)
        self.notes_edit.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        doc = self.notes_edit.document()
        doc.setDefaultStyleSheet("")  # Remove any default CSS
        
        # Set a completely empty stylesheet for the widget itself
        self.notes_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: transparent;
                border: none;
                padding: 0px;
                font-family: inherit;
                font-size: inherit;
            }
        """)
        
        # Reset to plain text mode explicitly
        self.notes_edit.setPlainText("")

        layout.addWidget(self.notes_edit)

        # Load saved text
        self._load()

        # Debounced autosave
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self.NOTES_SAVE_DEBOUNCE_MS)
        self._timer.timeout.connect(self._save)

        self.notes_edit.textChanged.connect(self._on_text_changed)

    def _load(self):
        """Load plain text from store, stripping any HTML if necessary"""
        text = ""
        
        # Try to get plain text first
        if hasattr(self._store, 'load_plain_text'):
            text = self._store.load_plain_text()
        elif hasattr(self._store, 'load_html'):
            # If store only has HTML, extract plain text
            html = self._store.load_html()
            if html:
                text = self._strip_html(html)
        
        if text:
            self._loading = True
            self.notes_edit.blockSignals(True)
            self.notes_edit.setPlainText(text)
            self.notes_edit.blockSignals(False)
            self._loading = False

    def _save(self):
        """Save as plain text only"""
        text = self.notes_edit.toPlainText()
        if hasattr(self._store, 'save_plain_text'):
            self._store.save_plain_text(text)
        elif hasattr(self._store, 'save_html'):
            # If store expects HTML, save as plain text in a simple paragraph
            self._store.save_html(f"<p>{text}</p>")

    def _on_text_changed(self):
        if not self._loading:
            self._timer.start()

    def _strip_html(self, html: str) -> str:
        """Remove all HTML tags and return plain text."""
        import re
        
        # First, extract just the text content between body tags if present
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        if body_match:
            html = body_match.group(1)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Remove CSS blocks
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
        
        # Remove script blocks
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL)
        
        # Remove meta tags and other head content
        text = re.sub(r'<meta[^>]*>', ' ', text)
        text = re.sub(r'<head[^>]*>.*?</head>', ' ', text, flags=re.DOTALL)
        
        # Decode HTML entities
        import html
        text = html.unescape(text)
        
        # Remove extra whitespace (including newlines)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def set_data(self, text: str | None) -> None:
        """Set notes content, ensuring it's plain text only."""
        self._loading = True
        self.notes_edit.blockSignals(True)
        
        # If text contains HTML/CSS, strip it thoroughly
        if text:
            # Check if it looks like HTML (contains tags)
            if '<' in text and '>' in text:
                text = self._strip_html(text)
            # Also check for CSS blocks
            if '{' in text and '}' in text and ':' in text:
                # This might be CSS, strip anything that looks like CSS
                text = re.sub(r'[a-zA-Z-]+\s*:\s*[^;]+;', ' ', text)
        
        self.notes_edit.setPlainText(text or "")
        self.notes_edit.blockSignals(False)
        self._loading = False

    def get_data(self) -> str:
        """Return notes content as plain text."""
        return self.notes_edit.toPlainText()