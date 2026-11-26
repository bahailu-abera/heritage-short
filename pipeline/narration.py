
import argparse
import json
import subprocess

from pathlib import Path

from pipeline.core.config import settings
from pipeline.core.cache import cache
from pipeline.core.logger import logger
from pipeline.core.validator import load_storyboard
from pipeline.providers.gemini import GeminiProvider


STAGE = "narration"

OUTPUT_DIR = settings.outputs_dir / "narration"


def get_audio_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    duration = float(result.stdout.strip())

    if duration <= 0:
        raise ValueError(
            f"Invalid audio duration: {path}"
        )

    return duration


def generate_silence(
    duration: float,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v", "error",
            "-f", "lavfi",
            "-i", "anullsrc=r=24000:cl=mono",
            "-t", str(duration),
            "-c:a", "pcm_s16le",
            str(output_path),
        ],
        check=True,
    )


def narration_parameters(
    storyboard: dict,
    shot: dict,
) -> dict:
    language = storyboard["film"]["language"]

    style = (
        f"Narration language: {language}. "
        f"{storyboard['narration']['style']}"
    )

    return {
        "text": shot["narration_text"],
        "voice": storyboard["narration"]["voice"],
        "style": style,
        "api_version": settings.gemini_api_version,
        "provider_version": GeminiProvider.VERSION,
        "response_format": "audio/wav",
    }


def run(
    storyboard: dict,
    shot_id: str | None = None,
    force: bool = False,
) -> list[dict]:

    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )

    provider = None
    results = []

    shots = [
        shot
        for shot in storyboard["shots"]
        if shot_id is None or shot["id"] == shot_id
    ]

    if not shots:
        raise ValueError(
            f"Unknown shot ID: {shot_id}"
        )

    for shot in shots:
        current_id = shot["id"]
        planned = shot["duration_seconds"]

        output_path = OUTPUT_DIR / f"{current_id}.wav"

        silent = not shot["narration_text"].strip()

        if silent:
            model = "ffmpeg-silence"

            parameters = {
                "duration_seconds": planned,
                "sample_rate": 24000,
            }
        else:
            model = settings.gemini_tts_model

            parameters = narration_parameters(
                storyboard, shot
            )

        key = cache.key(
            stage=STAGE,
            model=model,
            parameters=parameters,
        )

        cached = not force and cache.is_valid(
            stage=STAGE,
            artifact_id=current_id,
            key=key,
            output_path=output_path,
        )

        if cached:
            print(f"[CACHE HIT] {current_id}")

            logger.cache_hit(
                stage=STAGE,
                artifact_id=current_id,
                cache_key=key,
                output_path=output_path,
            )

        else:
            print(f"[GENERATING] {current_id}")

            if silent:
                generate_silence(
                    planned, output_path
                )

            else:
                if provider is None:
                    provider = GeminiProvider()

                provider.generate_speech(
                    text=parameters["text"],
                    voice=parameters["voice"],
                    style=parameters["style"],
                    output_path=output_path,
                    shot_id=current_id,
                )

            # Validate before registering the cache entry.
            get_audio_duration(output_path)

            cache.save(
                stage=STAGE,
                artifact_id=current_id,
                key=key,
                output_path=output_path,
            )

        actual = get_audio_duration(output_path)

        difference = planned - actual

        result = {
            "shot_id": current_id,
            "path": str(
                output_path.relative_to(settings.root)
            ),
            "planned_seconds": planned,
            "actual_seconds": round(actual, 3),
            "remaining_seconds": round(difference, 3),
            "status": (
                "overflow" if actual > planned + 0.01
                else "fits"
            ),
            "cached": cached,
        }

        results.append(result)

        print(
            f"  Planned: {planned:.2f}s | "
            f"Actual: {actual:.2f}s | "
            f"Status: {result['status']}"
        )

    report_name = (
        f"timing_{shot_id}.json"
        if shot_id
        else "timing_report.json"
    )

    report_path = OUTPUT_DIR / report_name

    report_path.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\nTiming report: {report_path}")

    overflows = [
        result for result in results
        if result["status"] == "overflow"
    ]

    if overflows:
        print("\nWARNING: Narration exceeds shot duration:")

        for result in overflows:
            print(
                f"  {result['shot_id']}: "
                f"{abs(result['remaining_seconds']):.2f}s "
                "over allocated time"
            )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate shot-level narration"
    )

    parser.add_argument(
        "--storyboard",
        default=str(settings.storyboard_path),
    )

    parser.add_argument("--shot")

    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate selected narration artifacts",
    )

    args = parser.parse_args()

    storyboard = load_storyboard(args.storyboard)

    run(
        storyboard,
        shot_id=args.shot,
        force=args.force,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
