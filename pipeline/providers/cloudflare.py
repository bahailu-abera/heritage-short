
import base64
import io

from pathlib import Path

import httpx
from PIL import Image

from pipeline.core.config import settings, require_env
from pipeline.core.cache import hash_file
from pipeline.core.logger import logger
from pipeline.core.retry import run_with_retry


class CloudflareProvider:
    VERSION = "1.0"

    MODEL = settings.image_model

    MAX_REFERENCES = 4
    REFERENCE_SIZE = 512

    def __init__(self):
        self.account_id = require_env(
            "CLOUDFLARE_ACCOUNT_ID"
        )

        self.api_token = require_env(
            "CLOUDFLARE_API_TOKEN"
        )

        self.url = (
            "https://api.cloudflare.com/client/v4/"
            f"accounts/{self.account_id}/ai/run/"
            f"{self.MODEL}"
        )

        self.headers = {
            "Authorization": f"Bearer {self.api_token}"
        }

    def prepare_reference(self, path: Path) -> bytes:
        with Image.open(path) as image:
            image = image.convert("RGB")

            image.thumbnail(
                (
                    self.REFERENCE_SIZE,
                    self.REFERENCE_SIZE,
                ),
                Image.Resampling.LANCZOS,
            )

            buffer = io.BytesIO()
            image.save(buffer, format="PNG")

            return buffer.getvalue()

    def generate_image(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_path: Path,
        seed: int | None = None,
        references: list[Path] | None = None,
        stage: str = "keyframes",
        artifact_id: str | None = None,
    ) -> Path:

        references = references or []

        if len(references) > self.MAX_REFERENCES:
            raise ValueError(
                "FLUX.2 supports at most four references"
            )

        if not 256 <= width <= 1920:
            raise ValueError("Unsupported image width")

        if not 256 <= height <= 1920:
            raise ValueError("Unsupported image height")

        fields = {
            "prompt": prompt,
            "width": str(width),
            "height": str(height),
        }

        if seed is not None:
            fields["seed"] = str(seed)

        # Using files for all fields forces multipart encoding,
        # even for text-to-image requests without references.
        parts = {
            name: (None, value)
            for name, value in fields.items()
        }

        reference_metadata = []

        for index, reference in enumerate(references):
            field_name = f"input_image_{index}"

            parts[field_name] = (
                f"reference_{index}.png",
                self.prepare_reference(reference),
                "image/png",
            )

            reference_metadata.append({
                "index": index,
                "path": str(reference),
                "sha256": hash_file(reference),
            })

        parameters = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "references": reference_metadata,
            "reference_max_size": self.REFERENCE_SIZE,
            "inference_steps": 4,
            "provider_version": self.VERSION,
        }

        def generate(attempt: int) -> Path:
            with logger.model_call(
                stage=stage,
                provider="cloudflare",
                model=self.MODEL,
                parameters=parameters,
                seed=seed,
                shot_id=artifact_id,
                attempt=attempt,
            ) as record:

                response = httpx.post(
                    self.url,
                    headers=self.headers,
                    files=parts,
                    timeout=settings.request_timeout,
                )

                response.raise_for_status()

                payload = response.json()

                if not payload.get("success", False):
                    raise RuntimeError(
                        f"Cloudflare generation failed: "
                        f"{payload.get('errors')}"
                    )

                encoded = payload.get(
                    "result", {}
                ).get("image")

                if not encoded:
                    raise RuntimeError(
                        "Cloudflare returned no image"
                    )

                image_data = base64.b64decode(
                    encoded
                )

                output_path.parent.mkdir(
                    parents=True, exist_ok=True
                )

                temporary_path = output_path.with_suffix(
                    ".tmp"
                )

                try:
                    with Image.open(
                        io.BytesIO(image_data)
                    ) as image:

                        image.load()

                        if image.size != (width, height):
                            raise RuntimeError(
                                f"Unexpected image size: "
                                f"{image.size}"
                            )

                        image = image.convert("RGB")

                        image.save(
                            temporary_path,
                            format="PNG",
                        )

                    temporary_path.replace(output_path)

                finally:
                    temporary_path.unlink(
                        missing_ok=True
                    )

                record["output_path"] = str(
                    output_path
                )

                record["output_width"] = width
                record["output_height"] = height

                record["output_bytes"] = (
                    output_path.stat().st_size
                )

                return output_path

        return run_with_retry(generate)
