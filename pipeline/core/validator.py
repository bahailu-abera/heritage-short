
import argparse
import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCHEMA_PATH = PROJECT_ROOT / "schema" / "storyboard.schema.json"

STORYBOARD_PATH = PROJECT_ROOT / "storyboard.json"


class StoryboardValidationError(ValueError):
    """Raised when a storyboard violates the film contract."""


def read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except OSError as error:
        raise StoryboardValidationError(
            f"Cannot read {path}: {error}"
        ) from error
    except json.JSONDecodeError as error:
        raise StoryboardValidationError(
            f"Invalid JSON in {path}: "
            f"line {error.lineno}, column {error.colno}: "
            f"{error.msg}"
        ) from error


def validate_structure(storyboard: dict) -> None:
    schema = read_json(SCHEMA_PATH)

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise StoryboardValidationError(
            f"Invalid storyboard schema: {error.message}"
        ) from error

    validator = Draft202012Validator(schema)

    errors = []

    for error in validator.iter_errors(storyboard):
        path = ".".join(
            str(part) for part in error.absolute_path
        ) or "root"

        errors.append(f"{path}: {error.message}")

    if errors:
        raise StoryboardValidationError(
            "\n".join(errors)
        )


def get_film_duration(storyboard: dict) -> float:
    shot_duration = sum(
        shot["duration_seconds"]
        for shot in storyboard["shots"]
    )

    end_card_duration = storyboard["export"]["end_card"][
        "duration_seconds"
    ]

    return shot_duration + end_card_duration


def get_duplicates(values: list[str]) -> list[str]:
    return [
        value
        for value, count in Counter(values).items()
        if count > 1
    ]


def resolve_reference_path(
    relative_path: str,
    project_root: Path = PROJECT_ROOT,
) -> Path:
    path = Path(relative_path)
    root = project_root.resolve()

    if path.is_absolute():
        raise StoryboardValidationError(
            f"Reference must be a relative path: {relative_path}"
        )

    resolved = (root / path).resolve()

    if not resolved.is_relative_to(root):
        raise StoryboardValidationError(
            f"Reference escapes project directory: {relative_path}"
        )

    return resolved


def validate_business_rules(storyboard: dict) -> None:
    errors = []

    shots = storyboard["shots"]
    characters = storyboard["characters"]

    shot_ids = [shot["id"] for shot in shots]

    character_ids = [
        character["id"]
        for character in characters
    ]

    duplicate_shots = get_duplicates(shot_ids)

    if duplicate_shots:
        errors.append(
            f"Duplicate shot IDs: {duplicate_shots}"
        )

    duplicate_characters = get_duplicates(character_ids)

    if duplicate_characters:
        errors.append(
            f"Duplicate character IDs: {duplicate_characters}"
        )

    duration = get_film_duration(storyboard)

    if not 60 <= duration <= 90:
        errors.append(
            f"Film duration must be between 60 and 90 seconds. "
            f"Actual duration: {duration} seconds."
        )

    valid_characters = set(character_ids)

    for shot in shots:
        shot_id = shot["id"]

        unknown_characters = (
            set(shot["character_ids"]) - valid_characters
        )

        if unknown_characters:
            errors.append(
                f"{shot_id}: unknown character IDs: "
                f"{sorted(unknown_characters)}"
            )

        if (
            shot["generation_duration_seconds"]
            > shot["duration_seconds"]
        ):
            errors.append(
                f"{shot_id}: generation duration exceeds "
                "the planned shot duration"
            )

        if (
            shot["narration_text"].strip()
            and not shot["subtitle_en"].strip()
        ):
            errors.append(
                f"{shot_id}: narration requires English subtitles"
            )

    reference_paths = []

    for character in characters:
        try:
            reference_path = resolve_reference_path(
                character["reference_image"]
            )

            reference_paths.append(str(reference_path))

        except StoryboardValidationError as error:
            errors.append(
                f"{character['id']}: {error}"
            )

    duplicate_paths = get_duplicates(reference_paths)

    if duplicate_paths:
        errors.append(
            f"Characters share reference output paths: "
            f"{duplicate_paths}"
        )

    shot_positions = {
        shot_id: index
        for index, shot_id in enumerate(shot_ids)
    }

    for index, cue in enumerate(storyboard["music"]["cues"]):
        start = cue["start_shot"]
        end = cue["end_shot"]

        if start not in shot_positions:
            errors.append(
                f"Music cue {index}: unknown start shot {start}"
            )

        if end not in shot_positions:
            errors.append(
                f"Music cue {index}: unknown end shot {end}"
            )

        if start in shot_positions and end in shot_positions:
            if shot_positions[start] > shot_positions[end]:
                errors.append(
                    f"Music cue {index}: start shot follows end shot"
                )

    if errors:
        raise StoryboardValidationError(
            "\n".join(errors)
        )


def validate_reference_files(
    storyboard: dict,
    shot_id: str | None = None,
) -> None:
    """Check required references after the reference generation stage."""

    required_characters = set()

    selected_shots = [
        shot
        for shot in storyboard["shots"]
        if shot_id is None or shot["id"] == shot_id
    ]

    if shot_id is not None and not selected_shots:
        raise StoryboardValidationError(
            f"Unknown shot ID: {shot_id}"
        )

    for shot in selected_shots:
        required_characters.update(shot["character_ids"])

    errors = []

    for character in storyboard["characters"]:
        if character["id"] not in required_characters:
            continue

        path = resolve_reference_path(
            character["reference_image"]
        )

        if not path.is_file():
            errors.append(
                f"{character['id']}: reference image missing: "
                f"{path}"
            )
        elif path.stat().st_size == 0:
            errors.append(
                f"{character['id']}: reference image is empty: "
                f"{path}"
            )

    if errors:
        raise StoryboardValidationError(
            "\n".join(errors)
        )


def load_storyboard(
    path: str | Path = STORYBOARD_PATH,
) -> dict:
    storyboard = read_json(Path(path))

    validate_structure(storyboard)
    validate_business_rules(storyboard)

    return storyboard


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Heritage Short storyboard"
    )

    parser.add_argument(
        "storyboard",
        nargs="?",
        default=str(STORYBOARD_PATH),
    )

    parser.add_argument(
        "--check-references",
        action="store_true",
        help="Verify generated character reference files",
    )

    args = parser.parse_args()

    try:
        storyboard = load_storyboard(args.storyboard)

        if args.check_references:
            validate_reference_files(storyboard)

    except StoryboardValidationError as error:
        print(f"Storyboard validation failed:\n{error}")
        return 1

    print("Storyboard validation passed.")
    print(f"Title: {storyboard['film']['title']}")
    print(f"Characters: {len(storyboard['characters'])}")
    print(f"Shots: {len(storyboard['shots'])}")
    print(f"Duration: {get_film_duration(storyboard)} seconds")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
