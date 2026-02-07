from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCharFormat, QTextCursor

from studiohub.ui.dashboard.cards.base import DashboardCard
from studiohub.ui.dashboard.panels.archive_status import ArchiveStatusPanel
from studiohub.ui.dashboard.panels.print_count_panel import PatentsVsStudioChart
from studiohub.ui.dashboard.panels.monthly_cost_ledger import MonthlyCostLedgerPanel, MonthlyCostBreakdown
from studiohub.ui.dashboard.panels.recent_print_jobs import RecentPrintJobs
from studiohub.ui.dashboard.panels.recent_index_events import RecentIndexEvents
from studiohub.ui.dashboard.panels.studio_mood import StudioMoodPanel

from studiohub.ui.dashboard.panels.studio_panel import StudioPanel
from studiohub.ui.dashboard.panels.paper_panel import PaperPanel
from studiohub.ui.dashboard.panels.ink_panel import InkPanel

from studiohub.services.dashboard_metrics import DashboardMetrics
from studiohub.services.media_session_service import MediaSessionService
from studiohub.style.typography.rules import apply_typography


from studiohub.services.dashboard_metrics_adapter import DashboardMetricsSnapshot


class DashboardViewQt(QtWidgets.QWidget):

    queue_readd_requested = QtCore.Signal(list)
    send_requested = QtCore.Signal()
    send_reprint_requested = QtCore.Signal(dict)
    replace_paper_requested = QtCore.Signal(str, float)
    
    OUTER_MARGINS = 16
    ROW_GUTTER = 16
    ROW_COUNT = 3

    def __init__(
        self,
        *,
        dashboard_metrics_adapter,
        print_count_adapter,
        parent=None,
    ):

        super().__init__(parent)

        self.dashboard_metrics_adapter = dashboard_metrics_adapter
        self.print_count_adapter = print_count_adapter
        self._loading_notes = False

        cfg = self._get_config()

        # IMPORTANT: media_service and StudioMoodPanel are initialized lazily
        # to avoid native (0xC0000005) crashes at startup.
        self.media_service: MediaSessionService | None = None

        self._patents_cache: dict = {}
        self._studio_cache: dict = {}
        self._last_index: dict = {}

        self._build_ui()
        self._relax_minimum_sizes()

        # Notes autosave (debounced)
        self._notes_save_timer = QtCore.QTimer(self)
        self._notes_save_timer.setSingleShot(True)
        self._notes_save_timer.timeout.connect(self._save_notes_to_disk)

        self.notes_edit.textChanged.connect(
            lambda: (
                not self._loading_notes
                and self._notes_save_timer.start(self.NOTES_SAVE_DEBOUNCE_MS)
            )
        )


        QtGui.QShortcut(QtGui.QKeySequence.Bold, self.notes_edit, activated=self._toggle_bold)
        QtGui.QShortcut(QtGui.QKeySequence.Italic, self.notes_edit, activated=self._toggle_italic)
        QtGui.QShortcut(QtGui.QKeySequence.Underline, self.notes_edit, activated=self._toggle_underline)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+L"), self.notes_edit, activated=self._toggle_bullet_list)


        # Load shared notes once UI is ready
        QtCore.QTimer.singleShot(0, self._load_notes_from_disk)

    def set_metrics(self, metrics: DashboardMetrics) -> None:
        self.metrics = metrics
        QtCore.QTimer.singleShot(0, self._init_media_and_studio_mood_panel)
        
    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(
            self.OUTER_MARGINS,
            self.OUTER_MARGINS,
            self.OUTER_MARGINS,
            self.OUTER_MARGINS,
        )
        root.setSpacing(0)

        self.grid_host = QtWidgets.QWidget()
        self.grid_host.setObjectName("DashboardGridHost")
        self.grid = QtWidgets.QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(self.ROW_GUTTER)

        # Columns
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(2, 1)

        # -------------------------------------------------
        # TOP ROW — column containers (stacked cards)
        # -------------------------------------------------

        # Column 0: Archive + Studio
        col0 = QtWidgets.QWidget()
        col0_l = QtWidgets.QVBoxLayout(col0)
        col0_l.setContentsMargins(0, 0, 0, 0)
        col0_l.setSpacing(12)

        self.archive_card = DashboardCard("ARCHIVE")
        self.archive_panel = ArchiveStatusPanel()
        self.archive_card.add_widget(self.archive_panel, 1)

        self.studio_card = DashboardCard("STUDIO")
        self.studio_panel = StudioPanel()
        self.studio_card.add_widget(self.studio_panel, 1)

        col0_l.addWidget(self.archive_card, 1)
        col0_l.addWidget(self.studio_card, 1)

        # Column 1: Paper + Ink
        col1 = QtWidgets.QWidget()
        col1_l = QtWidgets.QVBoxLayout(col1)
        col1_l.setContentsMargins(0, 0, 0, 0)
        col1_l.setSpacing(12)

        self.paper_card = DashboardCard("PAPER STOCK")
        self.paper_panel = PaperPanel()
        self.paper_panel.replace_requested.connect(self._on_replace_paper_requested)
        self.paper_card.add_widget(self.paper_panel, 1)

        self.ink_card = DashboardCard("INK LEVELS")
        self.ink_panel = InkPanel()
        self.ink_panel.replace_requested.connect(self._on_replace_ink)
        self.ink_card.add_widget(self.ink_panel, 1)

        col1_l.addWidget(self.paper_card, 1)
        col1_l.addWidget(self.ink_card, 1)

        # Column 2: Studio Mood card (panel will be injected lazily)
        self.studio_mood_card = DashboardCard("STUDIO MOOD")

        self.studio_mood_active_lbl = QtWidgets.QLabel("Active · 0m")
        apply_typography(self.studio_mood_active_lbl, "body-small")
        self.studio_mood_active_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.studio_mood_active_lbl.setProperty("role", "header-muted")
        self.studio_mood_card.set_header_widget(self.studio_mood_active_lbl)


        self._studio_mood_placeholder = QtWidgets.QLabel("Loading…")
        self._studio_mood_placeholder.setAlignment(Qt.AlignCenter)
        self._studio_mood_placeholder.setObjectName("DashboardPlaceholder")
        self.studio_mood_card.add_widget(self._studio_mood_placeholder, 1)

        self.grid.addWidget(col0, 0, 0)
        self.grid.addWidget(col1, 0, 1)
        self.grid.addWidget(self.studio_mood_card, 0, 2)

        # -------------------------------------------------
        # MIDDLE ROW
        # -------------------------------------------------

        self.print_volume = DashboardCard("Print Volume (Last 30 Days)")
        self.print_volume.add_widget(self._placeholder("Chart placeholder"), 1)

        self.patents_vs = DashboardCard("PATENTS VS STUDIO")
        self.patents_vs_studio_chart = PatentsVsStudioChart()
        self.patents_vs.add_widget(self.patents_vs_studio_chart, 1)

        self.grid.addWidget(self.print_volume, 1, 0, 1, 2)
        self.grid.addWidget(self.patents_vs, 1, 2)

        # -------------------------------------------------
        # BOTTOM ROW
        # -------------------------------------------------

        self.notes_card = DashboardCard("NOTES")
        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setAcceptRichText(True)
        self.notes_edit.setPlaceholderText("Notes")
        self.notes_edit.setObjectName("DashboardNotes")
        self.notes_edit.setProperty("typography", "mono")
        apply_typography(self.notes_edit, "mono")
        self.notes_edit.setWordWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.notes_card.add_widget(self.notes_edit, 1)

        # Center stack: Recent print jobs + recent indexes (restores last_index_card)
        center_stack = QtWidgets.QWidget()
        center_l = QtWidgets.QVBoxLayout(center_stack)
        center_l.setContentsMargins(0, 0, 0, 0)
        center_l.setSpacing(16)

        self.last_job_card = DashboardCard("RECENT PRINT JOBS")
        self.recent_print_jobs = RecentPrintJobs()
        self.recent_print_jobs.reprint_requested.connect(self._on_recent_reprint)
        self.last_job_card.add_widget(self.recent_print_jobs, 1)

        self.last_index_card = DashboardCard("RECENT POSTER INDEXES")
        self.recent_index_events = RecentIndexEvents()
        self.last_index_card.add_widget(self.recent_index_events, 1)

        center_l.addWidget(self.last_job_card, 1)
        center_l.addWidget(self.last_index_card, 1)

        self.monthly_cost = DashboardCard("MONTHLY PRODUCTION COST")
        self.panel_monthly_cost = MonthlyCostLedgerPanel(parent=self)
        self.monthly_cost.add_widget(self.panel_monthly_cost, 1)

        self.grid.addWidget(self.notes_card, 2, 0)
        self.grid.addWidget(center_stack, 2, 1)
        self.grid.addWidget(self.monthly_cost, 2, 2)

        root.addWidget(self.grid_host, 1)

        self.grid.setRowStretch(0, 1)
        self.grid.setRowStretch(1, 1)
        self.grid.setRowStretch(2, 1)


    def _on_replace_paper_requested(self, name: str, length: float) -> None:
        # Forward intent upward ONLY
        self.replace_paper_requested.emit(name, length)



    # =========================================================
    # Lazy init: media + StudioMoodPanel (avoids 0xC0000005)
    # =========================================================

    def _init_media_and_studio_mood_panel(self) -> None:
        try:
            self.media_service = MediaSessionService(
                root_path=Path(__file__).resolve().parents[1]
            )
        except Exception as e:
            print("[Dashboard] MediaSessionService init failed:", e)
            self.media_service = None

        try:
            # Remove placeholder and inject the real panel
            if hasattr(self, "_studio_mood_placeholder") and self._studio_mood_placeholder:
                self._studio_mood_placeholder.setParent(None)
                self._studio_mood_placeholder.deleteLater()
                self._studio_mood_placeholder = None

            if getattr(self, "metrics", None) is None:
                print("[Dashboard] StudioMoodPanel skipped (metrics not set)")
                return

            self.studio_mood_panel = StudioMoodPanel(
                metrics=self.metrics,
                media_service=self.media_service,
                parent=self.studio_mood_card,
            )

            # 🔹 NEW: wire Active Time → header right
            self.studio_mood_panel.active_time_changed.connect(
                self.studio_mood_active_lbl.setText
            )

            self.studio_mood_card.add_widget(self.studio_mood_panel, 1)

        except Exception as e:
            print("[Dashboard] StudioMoodPanel init failed:", e)


    # =========================================================
    # Helpers / callbacks
    # =========================================================

    def _placeholder(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setObjectName("DashboardPlaceholder")
        return lbl

    # =========================================================
    # Notes persistence (shared, autosave)
    # =========================================================

    NOTES_SAVE_DEBOUNCE_MS = 750

    def _notes_path(self) -> Path:
        cfg = self._get_config()
        runtime_root = cfg.get_runtime_root()
        return runtime_root / "notes" / "dashboard_notes.json"


    def _load_notes_from_disk(self) -> None:
        path = self._notes_path()
        if not path.exists():
            return

        try:
            self._loading_notes = True

            data = json.loads(path.read_text(encoding="utf-8"))
            html = data.get("content", "")

            self.notes_edit.blockSignals(True)
            self.notes_edit.setHtml(html)
            self.notes_edit.blockSignals(False)

        except Exception as e:
            print("[Dashboard] Failed to load shared notes:", e)
        finally:
            self._loading_notes = False


    def _save_notes_to_disk(self) -> None:
        path = self._notes_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": 1,
            "updated_at": datetime.utcnow().isoformat(),
            "content": self.notes_edit.toHtml(),
        }

        try:
            path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print("[Dashboard] Failed to save shared notes:", e)

    def _toggle_bold(self):
        self._merge_format(bold=True)

    def _toggle_italic(self):
        self._merge_format(italic=True)

    def _toggle_underline(self):
        self._merge_format(underline=True)

    def _merge_format(self, *, bold=False, italic=False, underline=False):
        cursor = self.notes_edit.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.WordUnderCursor)

        current = cursor.charFormat()
        fmt = QTextCharFormat()

        if bold:
            fmt.setFontWeight(
                QtGui.QFont.Normal
                if current.fontWeight() == QtGui.QFont.Bold
                else QtGui.QFont.Bold
            )
        if italic:
            fmt.setFontItalic(not current.fontItalic())
        if underline:
            fmt.setFontUnderline(not current.fontUnderline())

        cursor.mergeCharFormat(fmt)

    def _toggle_bullet_list(self):
        cursor = self.notes_edit.textCursor()
        cursor.beginEditBlock()

        current_list = cursor.currentList()
        if current_list:
            block_fmt = cursor.blockFormat()
            block_fmt.setObjectIndex(-1)
            block_fmt.setTopMargin(0)
            cursor.setBlockFormat(block_fmt)
        else:
            list_fmt = QtGui.QTextListFormat()
            list_fmt.setStyle(QtGui.QTextListFormat.ListDisc)
            cursor.createList(list_fmt)

            block_fmt = cursor.blockFormat()
            block_fmt.setTopMargin(8)
            cursor.setBlockFormat(block_fmt)

        cursor.endEditBlock()

    def _refresh_dashboard(self) -> None:
        self._render_dashboard(
            metrics=self.dashboard_metrics_adapter.snapshot,
            prints=self.print_count_adapter.snapshot,
        )

    def _render_dashboard(
        self,
        *,
        metrics: DashboardMetricsSnapshot,
        prints,
    ) -> None:
        """
        Render dashboard from adapter snapshots.

        Pure UI wiring.
        No computation outside basic ratios.
        """

        # =================================================
        # Archive
        # =================================================
        archive_total = metrics.by_source_total.get("archive", 0)
        archive_missing_files = metrics.by_source_missing_files.get("archive", 0)
        archive_issues = metrics.by_source_issues.get("archive", 0)
        archive_missing_master = metrics.by_source_missing_master.get("archive", 0)

        archive_complete = archive_total - archive_missing_master
        archive_fraction = (
            archive_complete / archive_total if archive_total else 0.0
        )

        self.archive_card.set_header_value(
            archive_total,
            style="kpi",
        )

        self.archive_panel.set_values(
            issues=archive_issues,
            missing=archive_missing_files,
            complete_fraction=archive_fraction,
        )

        # =================================================
        # Studio
        # =================================================
        studio_total = metrics.by_source_total.get("studio", 0)
        studio_missing_files = metrics.by_source_missing_files.get("studio", 0)
        studio_issues = metrics.by_source_issues.get("studio", 0)
        studio_missing_master = metrics.by_source_missing_master.get("studio", 0)

        studio_complete = studio_total - studio_missing_master
        studio_fraction = (
            studio_complete / studio_total if studio_total else 0.0
        )

        self.studio_card.set_header_value(
            studio_total,
            style="kpi",
        )

        self.studio_panel.set_values(
            issues=studio_issues,
            missing=studio_missing_files,
            fraction=studio_fraction,
        )

        # =================================================
        # Archive vs Studio (PRINT COUNTS)
        # =================================================
        self.patents_vs_studio_chart.set_values(
            patents=prints.archive_this_month,
            studio=prints.studio_this_month,
            delta_patents=prints.delta_archive,
            delta_studio=prints.delta_studio,
            delta_total=prints.delta_total,
        )




    # =========================================================
    # Data binding (hub compatibility)
    # =========================================================

    def update_from_cache(self, index: dict, patents_cache=None, studio_cache=None, **__):
        cfg = self._get_config()

        # Ensure metrics exists even if set_metrics() was never called
        if getattr(self, "metrics", None) is None:
            try:
                self.metrics = DashboardMetrics(print_log_path=cfg.get_print_log_path())
            except Exception:
                # last-resort fallback (keeps dashboard alive)
                self.metrics = DashboardMetrics(print_log_path="")

        # Keep metrics on the correct, current print log path
        try:
            p = cfg.get_print_log_path()
            if getattr(self.metrics, "print_log_path", None) != p:
                self.metrics.print_log_path = p
                # Reload rows when path changes so panels don't show stale/zero data
                self.metrics.reload()
        except Exception as e:
            print("[Dashboard] Could not resolve print log path:", e)


        self._last_index = index or {}

        try:
            self.metrics.set_index(self._last_index)
        except Exception as e:
            print("[Dashboard] DashboardMetrics.set_index error:", e)

        self._patents_cache = patents_cache or {}
        self._studio_cache = studio_cache or {}

        posters = self._last_index.get("posters", {}) if isinstance(self._last_index, dict) else {}
        patents = posters.get("patents", {}) if isinstance(posters, dict) else {}
        studio = posters.get("studio", {}) if isinstance(posters, dict) else {}

        total_patents = len(patents)
        total_studio = len(studio)

        self.archive_card.set_header_value(str(total_patents), style="title")
        self.studio_card.set_header_value(str(total_studio), style="title")

        # -----------------------------
        # PATENTS / ARCHIVE PANEL
        # -----------------------------
        patents_issues, patents_missing = self._calculate_missing_stats(self._patents_cache)

        complete_fraction = 1.0
        if total_patents > 0:
            complete_fraction = max(
                0.0,
                min(1.0, (total_patents - patents_missing) / total_patents),
            )

        try:
            self.archive_panel.set_values(
                issues=patents_issues,
                missing=patents_missing,
                complete_fraction=complete_fraction,
            )
        except TypeError:
            self.archive_panel.set_values(
                total=total_patents,
                issues=patents_issues,
                missing=patents_missing,
                complete_fraction=complete_fraction,
            )

        # -----------------------------
        # STUDIO PANEL
        # -----------------------------
        studio_issues, studio_missing = self._calculate_missing_stats(self._studio_cache)

        studio_complete_fraction = 1.0
        if total_studio > 0:
            studio_complete_fraction = max(
                0.0,
                min(1.0, (total_studio - studio_issues) / total_studio),
            )

        self.studio_panel.set_values(
            issues=studio_issues,
            missing=studio_missing,
            fraction=studio_complete_fraction,
        )

        # -----------------------------
        # Ink
        # -----------------------------
        try:
            ink_percent = int(self.metrics.get_ink_percent())
            self.ink_card.set_header_value(str(ink_percent), style="title")
            self.ink_panel.set_progress(ink_percent)
            self.ink_panel.set_last_replaced(cfg.get("consumables", "ink_reset_at", ""))
        except Exception as e:
            print("Ink panel error:", e)

        # -----------------------------
        # Patents vs Studio chart
        # -----------------------------
        try:
            if hasattr(self.metrics, "get_monthly_print_counts_with_delta"):
                counts = self.metrics.get_monthly_print_counts_with_delta()
                self.patents_vs_studio_chart.set_values(
                    patents=counts.get("patents", 0),
                    studio=counts.get("studio", 0),
                    delta_patents=counts.get("delta_patents", 0),
                    delta_studio=counts.get("delta_studio", 0),
                    delta_total=counts.get("delta_total", 0),
                )
            else:
                counts = self.metrics.get_print_counts_last_30_days()
                self.patents_vs_studio_chart.set_values(
                    patents=counts.get("patents", 0),
                    studio=counts.get("studio", 0),
                    delta_patents=0,
                    delta_studio=0,
                    delta_total=0,
                )
        except Exception as e:
            print("Patents vs Studio chart error:", e)

        # -----------------------------
        # Recent panels
        # -----------------------------
        try:
            jobs = self.metrics.get_recent_print_jobs(limit=2)
            self.recent_print_jobs.update_jobs(jobs)
        except Exception as e:
            print("Refresh print jobs error:", e)

        try:
            events = self.metrics.get_recent_index_events(limit=2)
            self.recent_index_events.update_events(events)
        except Exception as e:
            print("Refresh index events error:", e)

        def format_compact_timestamp(ts: str | datetime | None) -> str:
            if not ts:
                return "—"
            try:
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts)
                elif isinstance(ts, datetime):
                    dt = ts
                else:
                    return "—"
                time_str = dt.strftime("%I:%M %p").lstrip("0")
                return f"{dt.month}.{dt.day} · {time_str}"
            except Exception:
                return "—"

        # Recent print jobs subtitle
        try:
            jobs = self.metrics.get_recent_print_jobs(limit=1)
            if jobs:
                ts = jobs[0].get("timestamp") or jobs[0].get("datetime")
                subtitle = f"Last Print: {format_compact_timestamp(ts)}"
            else:
                subtitle = "Last: —"
            self.last_job_card.set_subtitle(subtitle)
        except Exception as e:
            print("Print log subtitle error:", e)

        # Recent poster index subtitle
        try:
            events = self.metrics.get_recent_index_events(limit=1)
            if not events and not self._last_index:
                self.last_index_card.set_subtitle(None)
            else:
                if events:
                    evt = events[0]
                    status_val = (evt.get("status") or "").lower()
                    failed_states = {"fail", "failed", "error", "exception"}
                    ok = status_val not in failed_states
                    subtitle = "Up to Date" if ok else "Out of Date"
                else:
                    subtitle = "Out of Date"
                self.last_index_card.set_subtitle(subtitle)
        except Exception as e:
            print("Poster index subtitle error:", e)

        # Monthly cost ledger
        try:
            monthly = self.metrics.get_monthly_costs()
            shipping_per_print = cfg.get("consumables", "shipping_cost_per_print", 0.0)

            breakdown = MonthlyCostBreakdown(
                ink=monthly["ink"],
                paper=monthly["paper"],
                shipping_supplies=monthly["prints"] * shipping_per_print,
                prints=monthly["prints"],
            )

            self.panel_monthly_cost.update_costs(breakdown)
        except Exception as e:
            print("Monthly cost panel error:", e)

    @staticmethod
    def _calculate_missing_stats(cache: dict) -> tuple[int, int]:
        if not isinstance(cache, dict):
            return 0, 0

        issues = 0
        missing = 0

        for _poster_id, entry in cache.items():
            files = None

            if isinstance(entry, list):
                files = entry
            elif isinstance(entry, dict):
                missing_block = entry.get("missing")
                if isinstance(missing_block, dict):
                    files = missing_block.get("sizes")

            if files:
                issues += 1
                try:
                    missing += len(files)
                except Exception:
                    missing += 1

        return issues, missing

    def set_loading(self, source: str, loading: bool) -> None:
        pass

    def _relax_minimum_sizes(self):
        for w in self.findChildren(QtWidgets.QWidget):
            w.setMinimumSize(0, 0)


    # =========================================================
    # Replace buttons
    # =========================================================

    def _on_replace_paper(self, name: str, total_length: float) -> None:
        # Forward intent upward — dashboard is NOT authoritative
        if hasattr(self.parent(), "paper_replace_requested"):
            self.parent().paper_replace_requested.emit(name, total_length)


    def _on_replace_ink(self) -> None:
        try:
            self.metrics.replace_ink()
        except Exception as e:
            print("Ink replace error:", e)

    # =========================================================
    # Recent print jobs -> re-add to queue
    # =========================================================

    def _on_recent_reprint(self, jobs: list[dict]):
        if not jobs:
            return
        job = jobs[0]
        self.send_reprint_requested.emit(job)

    def set_paper_info(
        self,
        *,
        name: str | None,
        total_ft: float | None,
        remaining_ft: float | None,
        last_replaced_ts: str | None,
    ) -> None:
        """
        Update the PaperPanel from authoritative paper ledger data.
        This view does NOT read the ledger directly.
        """

        # Paper name
        self.paper_panel.set_paper_name(name or "")

        # Store total length for dialog defaults (optional but safe)
        self.paper_panel.set_total_length(total_ft or 0.0)

        # Progress bar
        if total_ft and remaining_ft is not None and total_ft > 0:
            percent = int((remaining_ft / total_ft) * 100)
        else:
            percent = 0

        self.paper_panel.set_progress(percent)

        # Last replaced timestamp (UTC string → localized in PaperPanel)
        self.paper_panel.set_last_replaced(last_replaced_ts)


    # =========================================================
    # Config access
    # =========================================================

    def _get_config(self):
        w = self
        while w:
            if hasattr(w, "config_manager"):
                return w.config_manager
            w = w.parent()
        raise RuntimeError("ConfigManager not found")
