
import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

WAN_DIR = PROJECT_ROOT / "outputs/wan"

LOG_PATH = PROJECT_ROOT / "runs.jsonl"


def hash_file(path: Path) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def import_bundle(bundle: Path) -> None:

    WAN_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    storyboard = json.loads(
        (PROJECT_ROOT / "storyboard.json").read_text(
            encoding="utf-8"
        )
    )

    valid_ids = {
        shot["id"] for shot in storyboard["shots"]
    }

    with tempfile.TemporaryDirectory() as directory:

        temporary = Path(directory)

        imported = 0

        with zipfile.ZipFile(bundle) as archive:

            names = set(archive.namelist())

            for shot_id in sorted(valid_ids):

                video_name = (
                    f"outputs/shots/{shot_id}.mp4"
                )

                manifest_name = (
                    f"outputs/shots/{shot_id}.json"
                )

                if video_name not in names:

                    continue

                if manifest_name not in names:

                    print(
                        f"[SKIPPED] {shot_id}: "
                        "missing manifest"
                    )

                    continue

                video_path = temporary / f"{shot_id}.mp4"

                manifest_path = (
                    temporary / f"{shot_id}.json"
                )

                video_path.write_bytes(
                    archive.read(video_name)
                )

                manifest_path.write_bytes(
                    archive.read(manifest_name)
                )

                manifest = json.loads(
                    manifest_path.read_text()
                )

                if manifest["shot_id"] != shot_id:

                    raise ValueError(
                        f"Incorrect manifest: {shot_id}"
                    )

                if hash_file(video_path) != manifest[
                    "output_sha256"
                ]:

                    raise ValueError(
                        f"Video hash mismatch: {shot_id}"
                    )

                shutil.copy2(
                    video_path,
                    WAN_DIR / video_path.name,
                )

                shutil.copy2(
                    manifest_path,
                    WAN_DIR / manifest_path.name,
                )

                imported += 1

                print(f"[IMPORTED] {shot_id}")

            # Merge remote inference logs without duplication.

            if "wan_runs.jsonl" in names:

                remote_lines = archive.read(
                    "wan_runs.jsonl"
                ).decode("utf-8").splitlines()

                existing = set()

                if LOG_PATH.is_file():

                    for line in LOG_PATH.read_text(
                        encoding="utf-8"
                    ).splitlines():

                        try:

                            existing.add(
                                json.dumps(
                                    json.loads(line),
                                    sort_keys=True,
                                )
                            )

                        except ValueError:

                            continue

                with LOG_PATH.open(
                    "a",
                    encoding="utf-8",
                ) as logfile:

                    for line in remote_lines:

                        if not line.strip():

                            continue

                        record = json.loads(line)

                        canonical = json.dumps(
                            record,
                            sort_keys=True,
                        )

                        if canonical in existing:

                            continue

                        logfile.write(
                            json.dumps(record) + "\n"
                        )

                        existing.add(canonical)

    print(f"\nImported {imported} Wan video(s)")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "bundle",
        type=Path,
    )

    args = parser.parse_args()

    import_bundle(args.bundle)
    