
import argparse
import json
import subprocess
import textwrap
import time

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from pipeline.core.config import settings
from pipeline.core.cache import cache
from pipeline.core.logger import logger
from pipeline.core.validator import load_storyboard


ROOT = settings.storyboard_path.parent

SHOTS_DIR = ROOT / "outputs/shots"
NARRATION_DIR = ROOT / "outputs/narration"
MUSIC_PATH = ROOT / "outputs/music/selected.wav"

FINAL_DIR = ROOT / "outputs/final"
WORK_DIR = ROOT / "outputs/assembly"
SUBTITLES_DIR = ROOT / "outputs/subtitles"

VERSION = "1.0"


EXPORT_PRESETS = {
    "16:9": {
        "width": 1920,
        "height": 1080,
        "filename": "landscape.mp4",
        "subtitle_width": 85,
        "font_size": 14,
        "margin_v": 20,
    },
    "9:16": {
        "width": 1080,
        "height": 1920,
        "filename": "portrait.mp4",
        "subtitle_width": 55,
        "font_size": 12,
        "margin_v": 60,
    },
}

def ffmpeg(arguments, cwd=None):

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            *arguments,
        ],
        cwd=cwd,
        check=True,
    )


def get_duration(path):

    result = subprocess.check_output(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(path),
        ],
        text=True,
    )

    return float(result.strip())


def total_duration(storyboard):

    return (
        sum(
            shot["duration_seconds"]
            for shot in storyboard["shots"]
        )
        + storyboard["export"]["end_card"]["duration_seconds"]
    )


def format_timestamp(seconds):

    milliseconds = round(seconds * 1000)

    hours, remainder = divmod(
        milliseconds, 3600000
    )

    minutes, remainder = divmod(
        remainder, 60000
    )

    seconds, milliseconds = divmod(
        remainder, 1000
    )

    return (
        f"{hours:02d}:{minutes:02d}:"
        f"{seconds:02d},{milliseconds:03d}"
    )


def create_subtitles(
    storyboard,
    output,
    line_width,
):

    current_time = 0
    entries = []

    for shot in storyboard["shots"]:

        duration = shot["duration_seconds"]

        subtitle = shot["subtitle_en"].strip()

        if subtitle:

            wrapped = textwrap.fill(
                subtitle,
                width=line_width,
                break_long_words=False,
                break_on_hyphens=False,
            )

            start = format_timestamp(
                current_time + 0.1
            )

            end = format_timestamp(
                current_time + duration - 0.1
            )

            entries.append(
                f"{len(entries) + 1}\n"
                f"{start} --> {end}\n"
                f"{wrapped}\n"
            )

        current_time += duration

    output.write_text(
        "\n".join(entries),
        encoding="utf-8",
    )

    print(f"[SUBTITLES] {output.name}")


def create_end_card(
    storyboard,
    output,
    width,
    height,
):

    image = Image.new(
        "RGB",
        (width, height),
        "#101410",
    )

    draw = ImageDraw.Draw(image)

    font_path = (
        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans.ttf"
    )

    bold_path = (
        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans-Bold.ttf"
    )

    title_font = ImageFont.truetype(
        bold_path,
        int(width * 0.040),
    )

    disclosure_font = ImageFont.truetype(
        font_path,
        int(width * 0.030),
    )

    caption_font = ImageFont.truetype(
        font_path,
        int(width * 0.017),
    )

    draw.text(
        (width / 2, height * 0.38),
        storyboard["film"]["title"],
        font=title_font,
        fill="#F5F1E6",
        anchor="mm",
    )

    draw.line(
        [
            (width * 0.37, height * 0.46),
            (width * 0.63, height * 0.46),
        ],
        fill="#A7B98B",
        width=max(2, int(width * 0.002)),
    )

    draw.text(
        (width / 2, height * 0.54),
        storyboard["export"]["end_card"]["text"],
        font=disclosure_font,
        fill="#FFFFFF",
        anchor="mm",
    )

    draw.text(
        (width / 2, height * 0.62),
        "AI-generated visuals, narration and music",
        font=caption_font,
        fill="#B9C3B2",
        anchor="mm",
    )

    image.save(output)


def prepare_audio(storyboard):

    audio_dir = WORK_DIR / "audio"

    audio_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    narration_segments = []

    for shot in storyboard["shots"]:

        shot_id = shot["id"]

        duration = float(
            shot["duration_seconds"]
        )

        source = (
            NARRATION_DIR / f"{shot_id}.wav"
        )

        output = (
            audio_dir / f"{shot_id}.wav"
        )

        if not source.is_file():

            raise FileNotFoundError(source)

        actual_duration = get_duration(source)

        if actual_duration > duration + 0.05:

            raise RuntimeError(
                f"Narration exceeds shot duration: "
                f"{shot_id}"
            )

        ffmpeg([
            "-i", str(source),
            "-af",
            (
                "aresample=48000,"
                "aformat=channel_layouts=mono,"
                f"apad=whole_dur={duration},"
                f"atrim=duration={duration},"
                "asetpts=PTS-STARTPTS"
            ),
            "-ar", "48000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(output),
        ])

        narration_segments.append(output)

    end_duration = storyboard[
        "export"
    ]["end_card"]["duration_seconds"]

    silence = audio_dir / "end_silence.wav"

    ffmpeg([
        "-f", "lavfi",
        "-i", "anullsrc=r=48000:cl=mono",
        "-t", str(end_duration),
        "-c:a", "pcm_s16le",
        str(silence),
    ])

    narration_segments.append(silence)

    concat_file = audio_dir / "narration.txt"

    concat_file.write_text(
        "\n".join(
            f"file '{path.name}'"
            for path in narration_segments
        ) + "\n",
        encoding="utf-8",
    )

    narration_output = (
        audio_dir / "narration.wav"
    )

    ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:a", "pcm_s16le",
        str(narration_output),
    ])

    duration = total_duration(storyboard)

    target_lufs = storyboard[
        "export"
    ]["target_lufs"]

    true_peak = storyboard[
        "export"
    ]["true_peak_db"]

    fade_start = max(0, duration - 3)

    mix_output = audio_dir / "final_mix.wav"

    audio_filter = (
        "[0:a]"
        "aformat=sample_fmts=dbl:"
        "sample_rates=48000:"
        "channel_layouts=stereo,"
        "asplit=2[voice][sidechain];"

        "[1:a]"
        "aformat=sample_fmts=dbl:"
        "sample_rates=48000:"
        "channel_layouts=stereo,"
        f"atrim=duration={duration},"
        "asetpts=PTS-STARTPTS,"
        "volume=0.22,"
        "afade=t=in:st=0:d=1.5,"
        f"afade=t=out:st={fade_start}:d=3"
        "[music];"

        "[music][sidechain]"
        "sidechaincompress="
        "threshold=0.02:"
        "ratio=6:"
        "attack=100:"
        "release=1000"
        "[ducked];"

        "[voice][ducked]"
        "amix=inputs=2:"
        "duration=first:"
        "normalize=0,"
        f"loudnorm=I={target_lufs}:"
        f"TP={true_peak}:LRA=7,"
        "aresample=48000"
        "[audio]"
    )

    ffmpeg([
        "-i", str(narration_output),
        "-stream_loop", "-1",
        "-i", str(MUSIC_PATH),
        "-filter_complex", audio_filter,
        "-map", "[audio]",
        "-t", str(duration),
        "-ar", "48000",
        "-ac", "2",
        "-c:a", "pcm_s16le",
        str(mix_output),
    ])

    print(
        "[AUDIO] Final narration and music mix:",
        mix_output,
    )

    return mix_output


def create_video_segments(
    storyboard,
    aspect_ratio,
    preset,
    directory,
):

    width = preset["width"]
    height = preset["height"]

    fps = storyboard["export"]["fps"]

    segments = []

    for shot in storyboard["shots"]:

        shot_id = shot["id"]

        source = SHOTS_DIR / f"{shot_id}.mp4"

        output = directory / f"{shot_id}.mp4"

        frames = round(
            shot["duration_seconds"] * fps
        )

        print(
            f"[VIDEO] {aspect_ratio} | {shot_id}",
            flush=True,
        )

        if aspect_ratio == "16:9":

            video_filter = (
                f"scale={width}:{height}:"
                "flags=lanczos,"
                "setsar=1,"
                "format=yuv420p"
            )

        else:

            # Preserve the full cinematic frame.
            # Fill the portrait background with a
            # darkened, blurred version of the scene.

            video_filter = (
                "[0:v]split=2[bg][fg];"

                "[bg]"
                f"scale={width}:{height}:"
                "force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                "boxblur=30:2,"
                "eq=brightness=-0.12"
                "[background];"

                "[fg]"
                f"scale={width}:-2:"
                "flags=lanczos"
                "[foreground];"

                "[background][foreground]"
                "overlay=(W-w)/2:(H-h)/2,"
                "setsar=1,"
                "format=yuv420p"
                "[video]"
            )

        arguments = [
            "-i", str(source),
        ]

        if aspect_ratio == "16:9":

            arguments += [
                "-vf", video_filter,
            ]

        else:

            arguments += [
                "-filter_complex", video_filter,
                "-map", "[video]",
            ]

        arguments += [
            "-frames:v", str(frames),
            "-r", str(fps),
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            str(output),
        ]

        ffmpeg(arguments)

        segments.append(output)

    card_image = directory / "end_card.png"

    card_video = directory / "end_card.mp4"

    create_end_card(
        storyboard,
        card_image,
        width,
        height,
    )

    end_frames = round(
        storyboard["export"]["end_card"][
            "duration_seconds"
        ] * fps
    )

    ffmpeg([
        "-loop", "1",
        "-framerate", str(fps),
        "-i", str(card_image),
        "-frames:v", str(end_frames),
        "-an",
        "-vf", "setsar=1,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        str(card_video),
    ])

    segments.append(card_video)

    return segments


def assemble_export(
    storyboard,
    aspect_ratio,
    audio_path,
):

    preset = EXPORT_PRESETS[aspect_ratio]

    width = preset["width"]
    height = preset["height"]

    fps = storyboard["export"]["fps"]

    duration = total_duration(storyboard)

    directory = (
        WORK_DIR / aspect_ratio.replace(":", "x")
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = FINAL_DIR / preset["filename"]

    temporary = output.with_suffix(".tmp.mp4")

    segments = create_video_segments(
        storyboard,
        aspect_ratio,
        preset,
        directory,
    )

    concat_file = directory / "video.txt"

    concat_file.write_text(
        "\n".join(
            f"file '{path.name}'"
            for path in segments
        ) + "\n",
        encoding="utf-8",
    )

    visual_output = directory / "visuals.mp4"

    ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "copy",
        str(visual_output),
    ])

    subtitle_path = directory / "subtitles.srt"

    create_subtitles(
        storyboard,
        subtitle_path,
        preset["subtitle_width"],
    )

    # Retain standalone subtitles alongside
    # the burned-in versions.

    subtitle_name = (
        "landscape.srt"
        if aspect_ratio == "16:9"
        else "portrait.srt"
    )

    (
        SUBTITLES_DIR / subtitle_name
    ).write_text(
        subtitle_path.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    subtitle_style = (
        "FontName=DejaVu Sans,"
        f"FontSize={preset['font_size']},"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H80000000,"
        "BorderStyle=1,"
        "Outline=0.8,"
        "Shadow=0.3,"
        "Alignment=2,"
        "MarginL=20,"
        "MarginR=20,"
        f"MarginV={preset['margin_v']}"
    )

    subtitle_filter = (
        "subtitles=subtitles.srt:"
        f"original_size={width}x{height}:"
        f"force_style='{subtitle_style}'"
    )

    print(
        f"[EXPORTING] {aspect_ratio}",
        flush=True,
    )

    ffmpeg([
        "-i", str(visual_output),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-vf", subtitle_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-r", str(fps),
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-t", str(duration),
        "-movflags", "+faststart",
        str(temporary),
    ], cwd=directory)

    actual_duration = get_duration(temporary)

    if abs(actual_duration - duration) > 0.1:

        raise RuntimeError(
            f"Expected {duration}s, "
            f"received {actual_duration}s"
        )

    temporary.replace(output)

    print(f"[COMPLETED] {output}")

    return output


def validate_inputs(storyboard):

    required = [MUSIC_PATH]

    for shot in storyboard["shots"]:

        shot_id = shot["id"]

        required.extend([
            SHOTS_DIR / f"{shot_id}.mp4",
            NARRATION_DIR / f"{shot_id}.wav",
        ])

    for path in required:

        if not path.is_file():

            raise FileNotFoundError(path)

    for shot in storyboard["shots"]:

        shot_id = shot["id"]

        path = SHOTS_DIR / f"{shot_id}.mp4"

        expected = shot["duration_seconds"]

        actual = get_duration(path)

        if abs(actual - expected) > 0.05:

            raise RuntimeError(
                f"Incorrect shot duration: "
                f"{shot_id}: {actual}s"
            )

    return required


def run(
    storyboard,
    aspect_ratio=None,
    force=False,
):

    for directory in [
        FINAL_DIR,
        WORK_DIR,
        SUBTITLES_DIR,
    ]:

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    required = validate_inputs(storyboard)

    dependencies = {
        str(path.relative_to(ROOT)): path
        for path in required
    }

    selected_ratios = (
        [aspect_ratio]
        if aspect_ratio
        else storyboard["export"]["aspect_ratios"]
    )

    audio_path = None

    results = []

    for ratio in selected_ratios:

        preset = EXPORT_PRESETS[ratio]

        artifact_id = ratio.replace(":", "x")

        output = FINAL_DIR / preset["filename"]

        parameters = {
            "version": VERSION,
            "aspect_ratio": ratio,
            "preset": preset,
            "storyboard": storyboard,
            "music_volume": 0.22,
        }

        cache_key = cache.key(
            stage="assemble",
            model="ffmpeg",
            parameters=parameters,
            dependencies=dependencies,
        )

        if not force and cache.is_valid(
            stage="assemble",
            artifact_id=artifact_id,
            key=cache_key,
            output_path=output,
        ):

            print(f"[CACHE HIT] {ratio}")

            logger.cache_hit(
                stage="assemble",
                artifact_id=artifact_id,
                cache_key=cache_key,
                output_path=output,
            )

            results.append(output)

            continue

        start = time.perf_counter()

        record = {
            "event": "film_assembly",
            "stage": "assemble",
            "provider": "local",
            "model": "ffmpeg",
            "aspect_ratio": ratio,
            "parameters": parameters,
            "status": "running",
            "cost_usd": 0,
            "gpu_minutes": 0,
        }

        try:

            if audio_path is None:

                audio_path = prepare_audio(
                    storyboard
                )

            output = assemble_export(
                storyboard,
                ratio,
                audio_path,
            )

            cache.save(
                stage="assemble",
                artifact_id=artifact_id,
                key=cache_key,
                output_path=output,
            )

            record["status"] = "success"

            record["output_path"] = str(output)

            record["duration_seconds"] = (
                get_duration(output)
            )

            results.append(output)

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

            output.with_suffix(
                ".tmp.mp4"
            ).unlink(missing_ok=True)

    print("\nFinal exports:")

    for path in results:

        print(path)

    return results


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Assemble final heritage film"
    )

    parser.add_argument(
        "--aspect",
        choices=["16:9", "9:16"],
        default=None,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    storyboard = load_storyboard()

    run(
        storyboard,
        aspect_ratio=args.aspect,
        force=args.force,
    )
