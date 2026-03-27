import os
from pathlib import Path


BASE_DIR = Path(os.getenv("APP_BASE_DIR", Path(__file__).resolve().parent.parent.parent))


def get_path(*parts: str) -> Path:
    return BASE_DIR.joinpath(*parts)
