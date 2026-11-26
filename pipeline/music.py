import json
import argparse
import subprocess
import hashlib
from pathlib import Path

from pipeline.core.config import settings
from pipeline.core.validator import load_storyboard

ROOT = settings.storyboard_path.parent

MUSIC_DIR = ROOT / "outputs/music"
SELECTED_MUSIC = MUSIC_DIR / "selected.wav"


def run(storyboard: dict) -> Path:

    if not SELECTED_MUSIC.is_file():
        raise FileNotFoundError(
            "Missing selected soundtrack. "
            "Generate candidates using the ACE-Step notebook "
            "and copy the approved candidate to "
            "outputs/music/selected.wav."
        )

    duration = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(SELECTED_MUSIC),
            ],
            text=True,
        ).strip()
    )

    if duration <= 0:
        raise ValueError("Invalid soundtrack duration")

    report = {
        "model": "ACE-Step 1.5",
        "backend": "imported",
        "path": str(
            SELECTED_MUSIC.relative_to(ROOT)
        ),
        "duration_seconds": duration,
        "sha256": hashlib.sha256(
            SELECTED_MUSIC.read_bytes()
        ).hexdigest(),
    }

    (MUSIC_DIR / "selection_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("[MUSIC] Using approved ACE-Step soundtrack")
    print(f"Duration: {duration:.2f}s")

    return SELECTED_MUSIC


if __name__ == "__main__":
    run(load_storyboard())
