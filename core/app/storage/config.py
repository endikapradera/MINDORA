from pathlib import Path
import os
import sys


def _user_data_dir() -> Path:
    """Return the OS-appropriate user data directory for MINDORA."""
    home = Path.home()
    if sys.platform == "win32":
        # Windows: use APPDATA or ~/Documents/MINDORA
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "MINDORA" / "data"
        return home / "Documents" / "MINDORA" / "data"
    elif sys.platform == "darwin":
        # macOS: use ~/Documents/MINDORA
        return home / "Documents" / "MINDORA" / "data"
    else:
        # Linux: follow XDG Base Directory spec
        xdg = os.getenv("XDG_DATA_HOME")
        if xdg:
            return Path(xdg) / "MINDORA" / "data"
        return home / ".local" / "share" / "MINDORA" / "data"


def get_base_dir() -> Path:
    env_dir = os.getenv("IA_OFFLINE_BASE_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    # When running as frozen PyInstaller bundle, use OS user data dir
    if getattr(sys, "frozen", False):
        p = _user_data_dir()
        p.mkdir(parents=True, exist_ok=True)
        return p
    # Development mode: use project-relative data/
    return (Path(__file__).resolve().parents[3] / "data").resolve()
