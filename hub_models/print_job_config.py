from dataclasses import dataclass
from pathlib import Path

from studiohub.config_manager import ConfigManager


@dataclass(frozen=True)
class PrintJobConfig:
    runtime_root: Path
    print_log_path: Path

    default_size: str
    allow_pairing_12x18: bool
    render_dpi: int
    color_profile: str

    auto_commit_paper: bool
    auto_log_prints: bool

    @classmethod
    def from_config(cls, cfg: ConfigManager) -> "PrintJobConfig":
        return cls(
            runtime_root=cfg.get_runtime_root(),
            print_log_path=cfg.get_print_log_path(),

            default_size=cfg.get("printing", "default_size", "12x18"),
            allow_pairing_12x18=cfg.get("printing", "allow_pairing_12x18", True),
            render_dpi=cfg.get("printing", "render_dpi", 300),
            color_profile=cfg.get("printing", "color_profile", "sRGB"),

            auto_commit_paper=cfg.get("printing", "auto_commit_paper", True),
            auto_log_prints=cfg.get("printing", "auto_log_prints", True),
        )
