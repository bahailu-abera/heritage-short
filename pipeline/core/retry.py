from collections.abc import Callable
from typing import TypeVar

import httpx

from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)


from pipeline.core.config import settings
from pipeline.core.logger import logger


T = TypeVar("T")


def get_status_code(error: Exception) -> int | None:
    candidates = [
        getattr(error, "status_code", None),
        getattr(error, "code", None),
    ]

    response = getattr(error, "response", None)

    if response is not None:
        candidates.append(
            getattr(response, "status_code", None)
        )

    for value in candidates:
        if isinstance(value, int):
            return value

    return None


def is_retryable(error: Exception) -> bool:
    if isinstance(
        error,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
            TimeoutError,
            ConnectionError,
        ),
    ):
        return True

    status = get_status_code(error)

    return status in {
        408,
        429,
        500,
        502,
        503,
        504,
    }


def log_retry(retry_state) -> None:
    error = retry_state.outcome.exception()

    logger.write({
        "event": "retry_scheduled",
        "attempt": retry_state.attempt_number,
        "error_type": type(error).__name__,
        "http_status": get_status_code(error),
        "wait_seconds": (
            retry_state.next_action.sleep
        ),
    })


def run_with_retry(
    operation: Callable[[int], T],
    max_attempts: int = settings.max_attempts,
) -> T:
    if max_attempts < 1:
        raise ValueError(
            "max_attempts must be at least 1"
        )

    retrying = Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(
            multiplier=2,
            max=30,
        ),
        retry=retry_if_exception(is_retryable),
        before_sleep=log_retry,
        reraise=True,
    )

    for attempt in retrying:
        with attempt:
            return operation(
                attempt.retry_state.attempt_number
            )

    raise RuntimeError(
        "Retry execution ended unexpectedly"
    )
