"""Retry utility for LeadFinder AI crawlers.

Provides a configurable retry decorator with exponential back-off and
selective exception filtering.

Usage::

    from leadfinder.utils.retry import with_retry

    @with_retry(max_retries=3, base_delay=1.0)
    def fetch_page(url: str) -> str:
        ...

    # Async variant
    @with_retry(max_retries=3, base_delay=1.0)
    async def fetch_async(url: str) -> str:
        ...
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger("leadfinder.retry")

F = TypeVar("F", bound=Callable)


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator that retries a function on failure with exponential back-off.

    Works for both sync and async functions.

    Args:
        max_retries:    Maximum number of *retry* attempts (not counting the first call).
        base_delay:     Initial wait time in seconds before the first retry.
        backoff_factor: Multiplier applied to the delay after each failure.
                        e.g. 2.0 → delays of 1s, 2s, 4s …
        exceptions:     Tuple of exception types that trigger a retry.
                        Any other exception type is raised immediately.

    Returns:
        A decorated callable that retries on the specified exceptions.

    Raises:
        The last encountered exception if all retries are exhausted.
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                delay = base_delay
                last_exc: Exception | None = None
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as exc:
                        last_exc = exc
                        if attempt == max_retries:
                            logger.error(
                                "All %d retries exhausted for %s: %s",
                                max_retries,
                                func.__name__,
                                exc,
                            )
                            raise
                        logger.warning(
                            "Attempt %d/%d failed for %s (%s). Retrying in %.1fs…",
                            attempt + 1,
                            max_retries + 1,
                            func.__name__,
                            exc,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor

            return async_wrapper  # type: ignore[return-value]

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                delay = base_delay
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as exc:
                        if attempt == max_retries:
                            logger.error(
                                "All %d retries exhausted for %s: %s",
                                max_retries,
                                func.__name__,
                                exc,
                            )
                            raise
                        logger.warning(
                            "Attempt %d/%d failed for %s (%s). Retrying in %.1fs…",
                            attempt + 1,
                            max_retries + 1,
                            func.__name__,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                        delay *= backoff_factor

            return sync_wrapper  # type: ignore[return-value]

    return decorator
