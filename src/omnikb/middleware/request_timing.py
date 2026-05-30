from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from omnikb.config.settings import get_settings
from omnikb.infra.file_log_writer import append_jsonl


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Log each HTTP request duration and optional client correlation header."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        if not settings.request_logging_enabled:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        correlation_id = request.headers.get("x-correlation-id")

        append_jsonl(
            "api-requests",
            {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_correlation_id": correlation_id,
                "query": str(request.url.query) if request.url.query else None,
            },
        )
        response.headers["X-Request-Duration-Ms"] = str(duration_ms)
        if correlation_id:
            response.headers["X-Correlation-Id"] = correlation_id
        return response
