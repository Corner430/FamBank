"""Request logging middleware: logs method, path, status, duration, request_id, client_ip."""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import request_id_ctx

logger = structlog.get_logger("http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("x-request-id", uuid.uuid4().hex[:16])
        request_id_ctx.set(rid)

        client_ip = request.client.host if request.client else ""
        method = request.method
        path = request.url.path

        logger.info(
            "request_started",
            method=method,
            path=path,
            client_ip=client_ip,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "request_failed",
                method=method,
                path=path,
                client_ip=client_ip,
                duration_ms=duration_ms,
                exc_info=True,
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_finished",
            method=method,
            path=path,
            status=response.status_code,
            client_ip=client_ip,
            duration_ms=duration_ms,
        )

        response.headers["x-request-id"] = rid
        return response
