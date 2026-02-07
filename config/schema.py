from __future__ import annotations

from typing import TypedDict, Dict


# ============================
# Section schemas
# ============================

class MetaConfig(TypedDict):
    version: int


class PathsConfig(TypedDict):
    patents_root: str
    studio_root: str
    mockup_templates_root: str
    mockup_output_root: str
    print_jobs_root: str
    jsx_root: str
    photoshop_exe: str
    runtime_root: str
    print_log: str


class AppearanceConfig(TypedDict):
    theme: str


class StartupConfig(TypedDict):
    scan_patents_on_launch: bool
    scan_studio_on_launch: bool


class PrintManagerConfig(TypedDict):
    confirm_clear: bool
    confirm_send: bool


class PrintingConfig(TypedDict):
    is_primary_printer: bool
    default_size: str
    allow_pairing_12x18: bool
    render_dpi: int
    color_profile: str
    auto_commit_paper: bool
    auto_log_prints: bool


class ConsumablesConfig(TypedDict):
    paper_name: str
    paper_roll_start_feet: int
    paper_roll_reset_at: str
    ink_reset_percent: int
    ink_reset_at: str


# ============================
# Root schema
# ============================

class AppConfig(TypedDict):
    meta: MetaConfig
    paths: PathsConfig
    appearance: AppearanceConfig
    startup: StartupConfig
    print_manager: PrintManagerConfig
    printing: PrintingConfig
    consumables: ConsumablesConfig
