
import argparse
import subprocess
import tempfile
import wave
import textwrap

from pathlib import Path

import numpy as np

from pipeline.core.config import settings
from pipeline.core.validator import (
    load_storyboard,
    get_film_duration,
)
from pipeline.narration import get_audio_duration


OUTPUT_DIR = settings.outputs_dir / "drafts"
NARRATION_DIR = settings.outputs_dir / "narration"

SAMPLE_RATE = 48000


def run_ffmpeg(arguments: list[str]) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", *arguments],
        check=True,
    )


def format_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)

    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)

    return (
        f"{hours:02d}:{minutes:02d}:"
        f"{seconds:02d},{milliseconds:03d}"
    )


def create_subtitles(
    storyboard: dict,
    output_path: Path,
) -> None:
    entries = []
    position = 0.0
    subtitle_index = 1

    for shot in storyboard["shots"]:
        duration = shot["duration_seconds"]
        text = shot["subtitle_en"].strip()

        if text:
            audio_path = (
                NARRATION_DIR / f"{shot['id']}.wav"
            )

            speech_duration = get_audio_duration(
                audio_path
            )

            subtitle_duration = min(
                duration,
                speech_duration + 0.3,
            )

            wrapped = textwrap.fill(
                text, width=42
            )

            entries.append(
                f"{subtitle_index}\n"
                f"{format_timestamp(position)} --> "
                f"{format_timestamp(position + subtitle_duration)}\n"
                f"{wrapped}\n"
            )

            subtitle_index += 1

        position += duration

    end_card = storyboard["export"]["end_card"]

    entries.append(
        f"{subtitle_index}\n"
        f"{format_timestamp(position)} --> "
        f"{format_timestamp(position + end_card['duration_seconds'])}\n"
        f"{end_card['text']}\n"
    )

    output_path.write_text(
        "\n".join(entries),
        encoding="utf-8",
    )


def prepare_narration(
    storyboard: dict,
    working_dir: Path,
) -> Path:
    segments = []

    for shot in storyboard["shots"]:
        shot_id = shot["id"]

        source = NARRATION_DIR / f"{shot_id}.wav"

        if not source.is_file():
            raise FileNotFoundError(
                f"Missing narration: {source}"
            )

        planned = shot["duration_seconds"]
        actual = get_audio_duration(source)

        if actual > planned + 0.01:
            raise ValueError(
                f"{shot_id}: narration lasts "
                f"{actual:.2f}s but only "
                f"{planned:.2f}s is allocated. "
                "Adjust the narration or storyboard."
            )

        segment = working_dir / f"{shot_id}.wav"

        run_ffmpeg([
            "-i", str(source),
            "-af",
            f"apad,atrim=duration={planned}",
            "-ar", str(SAMPLE_RATE),
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(segment),
        ])

        segments.append(segment)

    end_duration = storyboard["export"]["end_card"][
        "duration_seconds"
    ]

    end_silence = working_dir / "end_card.wav"

    run_ffmpeg([
        "-f", "lavfi",
        "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
        "-t", str(end_duration),
        "-c:a", "pcm_s16le",
        str(end_silence),
    ])

    segments.append(end_silence)

    concat_file = working_dir / "concat.txt"

    concat_file.write_text(
        "\n".join(
            f"file '{path.name}'"
            for path in segments
        ),
        encoding="utf-8",
    )

    narration_path = OUTPUT_DIR / "radio_narration.wav"

    run_ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:a", "pcm_s16le",
        str(narration_path),
    ])

    return narration_path


def create_placeholder_music(
    duration: float,
    output_path: Path,
) -> None:
    samples = int(duration * SAMPLE_RATE)

    audio = np.zeros(
        samples, dtype=np.float32
    )

    # A simple original ambient progression:
    # A minor, F major, C major, G major.
    chords = [
        [110.00, 130.81, 164.81],
        [87.31, 110.00, 130.81],
        [130.81, 164.81, 196.00],
        [98.00, 123.47, 146.83],
    ]

    chord_duration = 4.0

    for index, start in enumerate(
        np.arange(0, duration, chord_duration)
    ):
        end = min(
            start + chord_duration,
            duration,
        )

        start_sample = int(start * SAMPLE_RATE)
        end_sample = int(end * SAMPLE_RATE)

        length = end_sample - start_sample

        if length <= 0:
            continue

        t = np.arange(length) / SAMPLE_RATE

        chord = chords[index % len(chords)]

        signal = np.zeros(length)

        for frequency in chord:
            signal += (
                np.sin(2 * np.pi * frequency * t)
                + 0.15 * np.sin(
                    4 * np.pi * frequency * t
                )
            )

        signal /= len(chord)

        envelope = np.sin(
            np.linspace(0, np.pi, length)
        ) ** 0.5

        audio[start_sample:end_sample] = (
            signal * envelope * 0.15
        )

    pcm = np.clip(
        audio * 32767,
        -32768,
        32767,
    ).astype("<i2")

    with wave.open(str(output_path), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(SAMPLE_RATE)
        file.writeframes(pcm.tobytes())


def run(storyboard: dict) -> Path:
    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )

    duration = get_film_duration(storyboard)

    with tempfile.TemporaryDirectory(
        prefix="radio-cut-"
    ) as temporary_directory:

        working_dir = Path(temporary_directory)

        narration = prepare_narration(
            storyboard, working_dir
        )

        subtitles = working_dir / "radio.srt"

        create_subtitles(
            storyboard, subtitles
        )

        # Preserve a readable copy for inspection.
        (OUTPUT_DIR / "radio.srt").write_bytes(
            subtitles.read_bytes()
        )

        music = (
            OUTPUT_DIR / "placeholder_music.wav"
        )

        create_placeholder_music(
            duration, music
        )

        output = OUTPUT_DIR / "radio_cut.mp4"

        audio_filter = (
            "[1:a]"
            "aformat=sample_fmts=dbl:"
            "sample_rates=48000:"
            "channel_layouts=mono,"
            "asplit=2[voice][sidechain];"

            "[2:a]"
            "aformat=sample_fmts=dbl:"
            "sample_rates=48000:"
            "channel_layouts=mono,"
            "volume=0.25[music];"

            "[music][sidechain]"
            "sidechaincompress="
            "threshold=0.02:"
            "ratio=6:"
            "attack=100:"
            "release=1000[ducked];"

            "[voice][ducked]"
            "amix=inputs=2:"
            "duration=first:"
            "normalize=0,"
            "loudnorm=I=-14:TP=-1:LRA=7[audio]"
        )

        command = [
            "ffmpeg",
            "-y",
            "-v", "error",
            "-f", "lavfi",
            "-i",
            f"color=c=black:s=1280x720:r=24:d={duration}",
            "-i", str(narration),
            "-i", str(music),
            "-filter_complex", audio_filter,
            "-vf",
            (
                "subtitles=radio.srt:"
                "force_style='FontSize=20,Alignment=2,"
                "MarginV=30,Outline=1'"
            ),
            "-map", "0:v",
            "-map", "[audio]",
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", str(SAMPLE_RATE),
            "-movflags", "+faststart",
            str(output),
        ]

        subprocess.run(
            command,
            cwd=working_dir,
            check=True,
        )

    print(f"Radio cut created: {output}")
    print(f"Planned duration: {duration:.2f}s")

    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create the narration-only radio cut"
    )

    parser.add_argument(
        "--storyboard",
        default=str(settings.storyboard_path),
    )

    args = parser.parse_args()

    storyboard = load_storyboard(args.storyboard)

    run(storyboard)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
