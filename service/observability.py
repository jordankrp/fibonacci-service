import json
import logging
import logging.config
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import Request, Response
from prometheus_client import Histogram

CORRELATION_ID_HEADER = "X-Correlation-ID"


correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

logger = logging.getLogger(__name__)

request_duration_histogram = Histogram(
    "http_request_duration_seconds",
    "Time spent handling HTTP requests.",
    ["method", "route", "status"],
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Extra fields go in extra={"fields": {...}}."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get(),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def setup_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": JsonFormatter}},
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "json",
                }
            },
            "root": {"level": "INFO", "handlers": ["stdout"]},
            "loggers": {
                "uvicorn": {"handlers": [], "propagate": True},
                "uvicorn.access": {"level": "WARNING"},
            },
        }
    )


async def observe_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get(CORRELATION_ID_HEADER) or uuid4().hex
    correlation_id.set(request_id)

    start = time.perf_counter()
    # If the app raises, the exception reaches handle_generic which responds with a 500
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers[CORRELATION_ID_HEADER] = request_id
        return response
    finally:
        duration = time.perf_counter() - start
        route = getattr(request.scope.get("route"), "path", "unmatched")
        request_duration_histogram.labels(request.method, route, str(status)).observe(duration)
        logger.info(
            "request",
            extra={
                "fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "route": route,
                    "status": status,
                    "duration_ms": round(duration * 1000, 2),
                }
            },
        )
