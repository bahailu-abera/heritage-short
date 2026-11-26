
import json
import time
import uuid

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from pipeline.core.config import settings


class RunLogger:
    def __init__(
        self,
        path: Path = settings.log_path,
    ):
        self.path = path
        self._lock = Lock()

    def write(self, record: dict) -> None:
        entry = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            **record,
        }

        self.path.parent.mkdir(
            parents=True, exist_ok=True
        )

        with self._lock:
            with self.path.open(
                "a", encoding="utf-8"
            ) as file:
                file.write(
                    json.dumps(
                        entry,
                        ensure_ascii=False,
                    ) + "\n"
                )

    @contextmanager
    def model_call(
        self,
        *,
        stage: str,
        provider: str,
        model: str,
        parameters: dict,
        seed: int | None = None,
        shot_id: str | None = None,
        attempt: int = 1,
    ):
        start = time.perf_counter()

        record = {
            "event": "model_call",
            "stage": stage,
            "provider": provider,
            "model": model,
            "shot_id": shot_id,
            "parameters": parameters,
            "seed": seed,
            "attempt": attempt,
            "status": "running",
            "cost_usd": None,
            "estimated_cost_usd": None,
            "gpu_minutes": None,
            "output_path": None,
        }

        try:
            yield record
            record["status"] = "success"

        except Exception as error:
            record["status"] = "failed"
            record["error_type"] = type(error).__name__

            status = getattr(
                error, "status_code", None
            )

            response = getattr(
                error, "response", None
            )

            if status is None and response is not None:
                status = getattr(
                    response, "status_code", None
                )

            record["http_status"] = status
            raise

        finally:
            record["latency_seconds"] = round(
                time.perf_counter() - start, 4
            )

            self.write(record)

    def cache_hit(
        self,
        *,
        stage: str,
        artifact_id: str,
        cache_key: str,
        output_path: Path,
    ) -> None:
        self.write({
            "event": "cache_hit",
            "stage": stage,
            "artifact_id": artifact_id,
            "cache_key": cache_key,
            "output_path": str(output_path),
            "status": "reused",
            "cost_usd": 0,
        })


logger = RunLogger()
