
import hashlib
import json
import subprocess

from pathlib import Path


class WanProvider:

    VERSION = "1.0"

    MODEL = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"

    def __init__(self, project_root: Path):
        self.project_root = project_root

        self.wan_dir = (
            project_root / "outputs" / "wan"
        )

    @staticmethod
    def hash_file(path: Path) -> str:
        return hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

    @staticmethod
    def get_duration(path: Path) -> float:
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

        return float(result.stdout.strip())

    def get_clip(
        self,
        shot_id: str,
        keyframe_path: Path,
        shot: dict,
    ) -> Path | None:

        video_path = self.wan_dir / f"{shot_id}.mp4"

        manifest_path = self.wan_dir / f"{shot_id}.json"

        if not video_path.is_file():
            return None

        if not manifest_path.is_file():
            return None

        try:
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            parameters = manifest["parameters"]

            expected_keyframe_hash = parameters[
                "keyframe_sha256"
            ]

            if manifest["shot_id"] != shot_id:
                return None

            if parameters.get("model") != self.MODEL:
                return None

            if parameters.get("seed") != shot["seed"]:
                return None

            expected_prompt = (
                f"{shot['image_prompt']}. "
                f"{shot['motion_prompt']}. "
                "Preserve the original characters' ages, "
                "facial features, body proportions and clothing. "
                "Natural cinematic movement, consistent lighting, "
                "stable environment and realistic human motion."
            )

            if parameters.get("prompt") != expected_prompt:
                print(
                    f"[STALE WAN] {shot_id}: prompt changed"
                )
                return None

            actual_keyframe_hash = self.hash_file(
                keyframe_path
            )

            if expected_keyframe_hash != actual_keyframe_hash:
                print(
                    f"[STALE WAN] {shot_id}: keyframe changed"
                )
                return None

            if manifest["output_sha256"] != self.hash_file(
                video_path
            ):
                print(
                    f"[INVALID WAN] {shot_id}: hash mismatch"
                )
                return None

            duration = self.get_duration(video_path)

            if duration <= 0:
                return None

            return video_path

        except (
            KeyError,
            ValueError,
            OSError,
            subprocess.SubprocessError,
        ) as error:

            print(
                f"[INVALID WAN] {shot_id}: {error}"
            )

            return None
