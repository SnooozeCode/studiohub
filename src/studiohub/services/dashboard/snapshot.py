from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from typing import List, Dict

# ============================
# Core panel slices
# ============================

@dataclass(frozen=True)
class CompletenessSlice:
    """Used by ArchiveStatusPanel / StudioPanel."""
    issues: int                  # posters with any missing required files
    missing_files: int           # total missing file count
    complete_fraction: float     # fraction of posters without issues (0..1)


@dataclass(frozen=True)
class MonthlyPrintCountSlice:
    """Used by ArchiveVsStudioChart (print_count_panel)."""
    archive_this_month: int
    studio_this_month: int
    archive_last_month: int
    studio_last_month: int
    delta_archive: int
    delta_studio: int
    delta_total: int


@dataclass(frozen=True)
class PaperSlice:
    """Used by PaperPanel."""
    paper_name: str
    total_length_ft: float
    remaining_ft: float
    remaining_percent: int
    estimated_prints_left: Optional[int] 
    last_replaced: Optional[datetime]


@dataclass(frozen=True)
class InkSlice:
    """Used by InkPanel."""
    remaining_percent: int
    last_replaced: Optional[datetime]


@dataclass(frozen=True)
class MonthlyCostBreakdown:
    """Used by MonthlyCostLedgerPanel."""
    ink: float
    paper: float
    shipping_supplies: float
    prints: int

    @property
    def total(self) -> float:
        return float(self.ink + self.paper + self.shipping_supplies)


@dataclass(frozen=True)
class StudioMoodSlice:
    mood: str          # "stressed" | "productive" | "idle" | etc
    label: str         # Human-facing summary

@dataclass(frozen=True)
class IndexSlice:
    title: str
    subtitle: str | None
    status: str
    timestamp: str | None



# ============================
# Root snapshot
# ============================


@dataclass
class DashboardSnapshot:
    archive: CompletenessSlice
    studio: CompletenessSlice
    studio_mood: StudioMoodSlice

    monthly_print_count: MonthlyPrintCountSlice
    recent_prints: list[dict]

    monthly_costs: MonthlyCostBreakdown

    # NEW (safe placeholders)
    revenue: float | None = None
    notes: str | None = None

