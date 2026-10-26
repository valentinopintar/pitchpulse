from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"


def match_dir(match_id: str) -> Path:
    return DATA_DIR / "matches" / match_id


def storybeat_path(match_id: str) -> Path:
    return DATA_DIR / "storybeats" / f"{match_id}.yaml"


def roster_path() -> Path:
    return DATA_DIR / "roster" / "catalog.csv"
