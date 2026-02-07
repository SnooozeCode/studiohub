from pathlib import Path
import subprocess


def run_jsx(jsx_path: Path, config_manager) -> None:
    photoshop_exe = config_manager.get("paths", "photoshop_exe", "")

    if not photoshop_exe:
        raise FileNotFoundError("Photoshop executable not set in Settings.")

    exe = Path(photoshop_exe)
    if not exe.exists():
        raise FileNotFoundError(f"Photoshop executable not found: {exe}")

    if not jsx_path.exists():
        raise FileNotFoundError(f"JSX worker not found: {jsx_path}")

    # 🔑 CRITICAL: Photoshop requires forward slashes
    jsx_arg = str(jsx_path).replace("\\", "/")

    subprocess.Popen(
        [str(exe), "-r", jsx_arg],
        shell=False,
    )
