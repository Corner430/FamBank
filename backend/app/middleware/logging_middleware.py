"""Request logging middleware.

Logs method, path, status, duration, request_id, client_ip, family_id, user_id.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.auth import decode_token
from app.logging_config import request_id_ctx

logger = structlog.get_logger("http")


def _extract_jwt_context(request: Request) -> dict:
    """Extract family_id and user_id from JWT Authorization header if present."""
    ctx: dict = {}
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        if payload:
            ctx["user_id"] = int(payload.get("sub", 0))
            if payload.get("family_id"):
                ctx["family_id"] = payload["family_id"]
    return ctx


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("x-request-id", uuid.uuid4().hex[:16])
        request_id_ctx.set(rid)

        client_ip = request.client.host if request.client else ""
        method = request.method
        path = request.url.path

        jwt_ctx = _extract_jwt_context(request)

        logger.info(
            "request_started",
            method=method,
            path=path,
            client_ip=client_ip,
            **jwt_ctx,
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
                **jwt_ctx,
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
            **jwt_ctx,
        )

        response.headers["x-request-id"] = rid
        return response
