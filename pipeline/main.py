import argparse
import time

from pipeline.core.validator import (
    load_storyboard,
    get_film_duration,
)

from pipeline import (
    references,
    narration,
    keyframes,
    shots,
    music,
    assemble,
)


def run_pipeline(
    force=False,
    backend="ffmpeg",
):

    start = time.perf_counter()

    storyboard = load_storyboard()

    print("=" * 60)
    print(storyboard["film"]["title"])
    print(
        "Film duration:",
        get_film_duration(storyboard),
        "seconds",
    )
    print("=" * 60)

    stages = [
        (
            "Character references",
            lambda: references.run(
                storyboard,
                force=force,
            ),
        ),
        (
            "Narration",
            lambda: narration.run(
                storyboard,
                force=force,
            ),
        ),
        (
            "Keyframes",
            lambda: keyframes.run(
                storyboard,
                force=force,
            ),
        ),
        (
            "Moving shots",
            lambda: shots.run(
                storyboard,
                force=force,
                backend=backend,
            ),
        ),
        (
            "Music",
            lambda: music.run(storyboard),
        ),
        (
            "Final assembly",
            lambda: assemble.run(
                storyboard,
                force=force,
            ),
        ),
    ]

    for name, operation in stages:

        print(f"\n{'=' * 60}")
        print(f"STAGE: {name}")
        print("=" * 60)

        stage_start = time.perf_counter()

        operation()

        elapsed = time.perf_counter() - stage_start

        print(
            f"[DONE] {name}: "
            f"{elapsed:.2f} seconds"
        )

    print("\nPipeline completed successfully")

    print(
        "Total elapsed:",
        round(time.perf_counter() - start, 2),
        "seconds",
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Heritage Short film pipeline"
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    parser.add_argument(
        "--backend",
        choices=["ffmpeg", "wan", "auto"],
        default="ffmpeg",
    )

    args = parser.parse_args()

    run_pipeline(
        force=args.force,
        backend=args.backend,
    )
