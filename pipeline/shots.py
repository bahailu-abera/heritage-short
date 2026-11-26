
import argparse
import json
import subprocess
import time

from pathlib import Path

from pipeline.core.config import settings
from pipeline.core.cache import cache
from pipeline.core.logger import logger
from pipeline.core.validator import load_storyboard

from pipeline.providers.wan import WanProvider


PROJECT_ROOT = settings.storyboard_path.parent

KEYFRAMES_DIR = PROJECT_ROOT / "outputs/keyframes"
SHOTS_DIR = PROJECT_ROOT / "outputs/shots"

WIDTH = 1280
HEIGHT = 720

PROVIDER_VERSION = "1.1"

wan = WanProvider(PROJECT_ROOT)


MOTION_PRESETS = {
    "shot_001": "pan_right",
    "shot_002": "push_in",
    "shot_003": "push_in",
    "shot_004": "push_in",
    "shot_005": "push_in",
    "shot_006": "pull_out",
    "shot_007": "pan_left",
    "shot_008": "push_in",
    "shot_009": "pan_right",
    "shot_010": "pull_out",
}


def run_ffmpeg(arguments: list[str]) -> None:

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        *arguments,
    ]

    subprocess.run(command, check=True)


def get_motion_filter(
    preset: str,
    total_frames: int,
    fps: int,
) -> str:

    denominator = max(total_frames - 1, 1)

    progress = f"on/{denominator}"

    center_x = "iw/2-iw/zoom/2"
    center_y = "ih/2-ih/zoom/2"

    if preset == "push_in":

        zoom = f"1.0+0.12*({progress})"

        x = center_x
        y = center_y

    elif preset == "pull_out":

        zoom = f"1.12-0.12*({progress})"

        x = center_x
        y = center_y

    elif preset == "pan_right":

        zoom = "1.12"

        x = f"(iw-iw/zoom)*({progress})"
        y = center_y

    elif preset == "pan_left":

        zoom = "1.12"

        x = f"(iw-iw/zoom)*(1-({progress}))"
        y = center_y

    else:

        zoom = f"1.0+0.08*({progress})"

        x = center_x
        y = center_y

    return (
        "scale=3840:2160:"
        "force_original_aspect_ratio=increase,"
        "crop=3840:2160,"
        f"zoompan=z='{zoom}':"
        f"x='{x}':"
        f"y='{y}':"
        f"d={total_frames}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={fps},"
        "setsar=1,"
        "format=yuv420p"
    )


def generate_ffmpeg_shot(
    keyframe: Path,
    output: Path,
    duration: float,
    fps: int,
    preset: str,
) -> None:

    total_frames = round(duration * fps)

    video_filter = get_motion_filter(
        preset,
        total_frames,
        fps,
    )

    run_ffmpeg([
        "-i", str(keyframe),

        "-vf", video_filter,

        "-frames:v", str(total_frames),

        "-an",

        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",

        "-pix_fmt", "yuv420p",

        "-movflags", "+faststart",

        str(output),
    ])


def normalize_wan_shot(
    source: Path,
    output: Path,
    duration: float,
    fps: int,
) -> None:

    source_duration = wan.get_duration(source)

    if source_duration <= 0:
        raise ValueError(
            f"Invalid source duration: {source}"
        )

    total_frames = round(duration * fps)

    speed_factor = duration / source_duration

    video_filter = (
        "setpts=PTS-STARTPTS,"
        f"setpts={speed_factor:.10f}*PTS,"
        f"fps={fps},"
        f"scale={WIDTH}:{HEIGHT}:"
        "force_original_aspect_ratio=increase:"
        "flags=lanczos,"
        f"crop={WIDTH}:{HEIGHT},"
        "setsar=1,"
        "tpad=stop_mode=clone:"
        f"stop={total_frames},"
        f"trim=end_frame={total_frames},"
        f"setpts=N/({fps}*TB),"
        "format=yuv420p"
    )

    run_ffmpeg([
        "-i", str(source),

        "-vf", video_filter,

        "-frames:v", str(total_frames),

        "-r", str(fps),

        "-an",

        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",

        "-pix_fmt", "yuv420p",

        "-movflags", "+faststart",

        str(output),
    ])


def generate_shot(
    shot: dict,
    fps: int,
    force: bool = False,
    backend: str = "ffmpeg",
) -> dict:

    shot_id = shot["id"]

    duration = float(shot["duration_seconds"])

    keyframe = KEYFRAMES_DIR / f"{shot_id}.png"

    if not keyframe.is_file():
        raise FileNotFoundError(
            f"Missing keyframe: {keyframe}"
        )

    output = SHOTS_DIR / f"{shot_id}.mp4"

    temporary_output = (
        SHOTS_DIR / f"{shot_id}.tmp.mp4"
    )

    motion_preset = MOTION_PRESETS.get(
        shot_id,
        "push_in",
    )

    source = None

    if backend != "ffmpeg":

        source = wan.get_clip(
            shot_id,
            keyframe,
            shot,
        )

    if backend == "wan" and source is None:

        raise RuntimeError(
            f"No valid Wan clip for {shot_id}"
        )

    selected_backend = (
        "wan" if source else "ffmpeg"
    )

    model = (
        wan.MODEL if source else "ffmpeg-zoompan"
    )

    dependencies = {
        "keyframe": keyframe,
    }

    if source is not None:

        dependencies["wan_video"] = source

    parameters = {
        "provider_version": PROVIDER_VERSION,
        "backend": selected_backend,
        "duration_seconds": duration,
        "fps": fps,
        "width": WIDTH,
        "height": HEIGHT,
        "motion_preset": motion_preset,
        "image_prompt": shot["image_prompt"],
        "motion_prompt": shot["motion_prompt"],
        "seed": shot["seed"],
    }

    cache_key = cache.key(
        stage="shots",
        model=model,
        parameters=parameters,
        dependencies=dependencies,
    )

    if not force and cache.is_valid(
        stage="shots",
        artifact_id=shot_id,
        key=cache_key,
        output_path=output,
    ):

        print(
            f"[CACHE HIT] {shot_id} ({selected_backend})"
        )

        logger.cache_hit(
            stage="shots",
            artifact_id=shot_id,
            cache_key=cache_key,
            output_path=output,
        )

        return {
            "shot_id": shot_id,
            "backend": selected_backend,
            "duration_seconds": wan.get_duration(output),
            "output_path": str(output),
            "cached": True,
        }

    print(
        f"[GENERATING] {shot_id}"
        f" | Backend: {selected_backend}"
        f" | Duration: {duration}s",
        flush=True,
    )

    start = time.perf_counter()

    record = {
        "event": "video_processing",
        "stage": "shots",
        "shot_id": shot_id,
        "provider": selected_backend,
        "model": model,
        "parameters": parameters,
        "seed": shot["seed"],
        "cost_usd": 0,
        "gpu_minutes": 0,
        "status": "running",
    }

    try:

        if source is not None:

            normalize_wan_shot(
                source,
                temporary_output,
                duration,
                fps,
            )

        else:

            generate_ffmpeg_shot(
                keyframe,
                temporary_output,
                duration,
                fps,
                motion_preset,
            )

        actual_duration = wan.get_duration(
            temporary_output
        )

        tolerance = 1 / fps + 0.02

        if abs(actual_duration - duration) > tolerance:

            raise RuntimeError(
                f"{shot_id}: expected {duration}s, "
                f"received {actual_duration}s"
            )

        temporary_output.replace(output)

        cache.save(
            stage="shots",
            artifact_id=shot_id,
            key=cache_key,
            output_path=output,
        )

        record["status"] = "success"
        record["output_path"] = str(output)

        record["duration_seconds"] = actual_duration

    except BaseException as error:

        record["status"] = "failed"
        record["error_type"] = type(error).__name__
        record["error"] = str(error)

        raise

    finally:

        record["latency_seconds"] = round(
            time.perf_counter() - start,
            3,
        )

        logger.write(record)

        temporary_output.unlink(missing_ok=True)

    print(f"  Output: {output}")

    return {
        "shot_id": shot_id,
        "backend": selected_backend,
        "duration_seconds": actual_duration,
        "output_path": str(output),
        "cached": False,
    }


def run(
    storyboard: dict,
    shot_id: str | None = None,
    force: bool = False,
    backend: str = "auto",
) -> list[dict]:

    SHOTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fps = storyboard["export"]["fps"]

    selected_shots = [
        shot
        for shot in storyboard["shots"]
        if shot_id is None or shot["id"] == shot_id
    ]

    if not selected_shots:

        raise ValueError(
            f"Unknown shot: {shot_id}"
        )

    results = []

    for shot in selected_shots:

        result = generate_shot(
            shot,
            fps,
            force=force,
            backend=backend,
        )

        results.append(result)

    report_path = SHOTS_DIR / "generation_report.json"

    existing = {}

    if shot_id and report_path.is_file():

        for item in json.loads(
            report_path.read_text(encoding="utf-8")
        ):
            existing[item["shot_id"]] = item

    for item in results:

        existing[item["shot_id"]] = item

    report_path.write_text(
        json.dumps(
            list(existing.values()),
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"\nProcessed {len(results)} shot(s)"
    )

    return results


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate film shot videos"
    )

    parser.add_argument(
        "--shot",
        default=None,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    parser.add_argument(
        "--backend",
        choices=["auto", "wan", "ffmpeg"],
        default="ffmpeg",
    )

    args = parser.parse_args()

    storyboard = load_storyboard()

    run(
        storyboard,
        shot_id=args.shot,
        force=args.force,
        backend=args.backend,
    )
