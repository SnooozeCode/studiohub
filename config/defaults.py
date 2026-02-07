# config/defaults.py
from typing import Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    "meta": {
        "version": 1
    },
    "paths": {
        # Asset roots
        "patents_root": "",
        "studio_root": "",

        # Mockups / tooling
        "mockup_templates_root": "",
        "mockup_output_root": "",
        "print_jobs_root": "",
        "jsx_root": "",
        "photoshop_exe": "",

        # Shared business runtime (Google Drive)
        "runtime_root": "",
        "print_log": "",
    },
    "appearance": {
        "theme": "dracula",  # "dracula" | "alucard"
    },
    "startup": {
        "scan_patents_on_launch": True,
        "scan_studio_on_launch": True,
    },
    "print_manager": {
        "confirm_clear": True,
        "confirm_send": True,
    },
    "printing": {
        "is_primary_printer": True,

        # Print behavior (NEW)
        "default_size": "12x18",
        "allow_pairing_12x18": True,
        "render_dpi": 300,
        "color_profile": "sRGB",
        "auto_commit_paper": True,
        "auto_log_prints": True,
    },
    "consumables": {
        "paper_name": "Red River Polar Matte 60",
        "paper_roll_start_feet": 60,
        "paper_roll_reset_at": "15",
        "ink_reset_percent": 100,
        "ink_reset_at": "25"
    },
}

