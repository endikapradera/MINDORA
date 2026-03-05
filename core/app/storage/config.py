from pathlib import Path
import os


def get_base_dir() -> Path:
    env_dir = os.getenv("IA_OFFLINE_BASE_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return (Path(__file__).resolve().parents[3] / "data").resolve()
