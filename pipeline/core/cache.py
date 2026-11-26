
import hashlib
import json
import os
import tempfile

from pathlib import Path

from pipeline.core.config import settings


CACHE_VERSION = 1


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024), b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def hash_data(data: dict) -> str:
    serialized = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


class ArtifactCache:
    def __init__(
        self,
        directory: Path = settings.cache_dir,
    ):
        self.directory = directory

    def key(
        self,
        *,
        stage: str,
        model: str,
        parameters: dict,
        dependencies: dict[str, Path] | None = None,
    ) -> str:
        dependency_hashes = {
            name: hash_file(path)
            for name, path in (
                dependencies or {}
            ).items()
        }

        return hash_data({
            "cache_version": CACHE_VERSION,
            "stage": stage,
            "model": model,
            "parameters": parameters,
            "dependencies": dependency_hashes,
        })

    def manifest_path(
        self,
        stage: str,
        artifact_id: str,
    ) -> Path:
        identifier = hash_data({
            "stage": stage,
            "artifact_id": artifact_id,
        })

        return self.directory / f"{identifier}.json"

    def is_valid(
        self,
        *,
        stage: str,
        artifact_id: str,
        key: str,
        output_path: Path,
    ) -> bool:
        manifest_path = self.manifest_path(
            stage, artifact_id
        )

        if not manifest_path.is_file():
            return False

        if not output_path.is_file():
            return False

        if output_path.stat().st_size == 0:
            return False

        try:
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            return (
                manifest["cache_key"] == key
                and manifest["output_sha256"]
                == hash_file(output_path)
            )

        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ):
            return False

    def save(
        self,
        *,
        stage: str,
        artifact_id: str,
        key: str,
        output_path: Path,
    ) -> None:
        if (
            not output_path.is_file()
            or output_path.stat().st_size == 0
        ):
            raise ValueError(
                f"Invalid artifact: {output_path}"
            )

        manifest_path = self.manifest_path(
            stage, artifact_id
        )

        manifest_path.parent.mkdir(
            parents=True, exist_ok=True
        )

        manifest = {
            "stage": stage,
            "artifact_id": artifact_id,
            "cache_key": key,
            "output_path": str(output_path),
            "output_sha256": hash_file(output_path),
        }

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=manifest_path.parent,
                delete=False,
            ) as file:
                temporary_path = Path(file.name)

                json.dump(
                    manifest,
                    file,
                    indent=2,
                )

            os.replace(
                temporary_path, manifest_path
            )

        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def invalidate(
        self,
        stage: str,
        artifact_id: str,
    ) -> None:
        self.manifest_path(
            stage, artifact_id
        ).unlink(missing_ok=True)


cache = ArtifactCache()

import hashlib
import json
import os
import tempfile

from pathlib import Path

from pipeline.core.config import settings


CACHE_VERSION = 1


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024), b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def hash_data(data: dict) -> str:
    serialized = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


class ArtifactCache:
    def __init__(
        self,
        directory: Path = settings.cache_dir,
    ):
        self.directory = directory

    def key(
        self,
        *,
        stage: str,
        model: str,
        parameters: dict,
        dependencies: dict[str, Path] | None = None,
    ) -> str:
        dependency_hashes = {
            name: hash_file(path)
            for name, path in (
                dependencies or {}
            ).items()
        }

        return hash_data({
            "cache_version": CACHE_VERSION,
            "stage": stage,
            "model": model,
            "parameters": parameters,
            "dependencies": dependency_hashes,
        })

    def manifest_path(
        self,
        stage: str,
        artifact_id: str,
    ) -> Path:
        identifier = hash_data({
            "stage": stage,
            "artifact_id": artifact_id,
        })

        return self.directory / f"{identifier}.json"

    def is_valid(
        self,
        *,
        stage: str,
        artifact_id: str,
        key: str,
        output_path: Path,
    ) -> bool:
        manifest_path = self.manifest_path(
            stage, artifact_id
        )

        if not manifest_path.is_file():
            return False

        if not output_path.is_file():
            return False

        if output_path.stat().st_size == 0:
            return False

        try:
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            return (
                manifest["cache_key"] == key
                and manifest["output_sha256"]
                == hash_file(output_path)
            )

        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ):
            return False

    def save(
        self,
        *,
        stage: str,
        artifact_id: str,
        key: str,
        output_path: Path,
    ) -> None:
        if (
            not output_path.is_file()
            or output_path.stat().st_size == 0
        ):
            raise ValueError(
                f"Invalid artifact: {output_path}"
            )

        manifest_path = self.manifest_path(
            stage, artifact_id
        )

        manifest_path.parent.mkdir(
            parents=True, exist_ok=True
        )

        manifest = {
            "stage": stage,
            "artifact_id": artifact_id,
            "cache_key": key,
            "output_path": str(output_path),
            "output_sha256": hash_file(output_path),
        }

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=manifest_path.parent,
                delete=False,
            ) as file:
                temporary_path = Path(file.name)

                json.dump(
                    manifest,
                    file,
                    indent=2,
                )

            os.replace(
                temporary_path, manifest_path
            )

        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def invalidate(
        self,
        stage: str,
        artifact_id: str,
    ) -> None:
        self.manifest_path(
            stage, artifact_id
        ).unlink(missing_ok=True)


cache = ArtifactCache()
