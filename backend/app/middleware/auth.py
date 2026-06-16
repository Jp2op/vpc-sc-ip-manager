import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/", "/health", "/readiness"}


class APIKeyMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        if not settings.api_key:
            return await call_next(request)

        path = request.url.path.rstrip("/")
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        api_key = (
            request.headers.get("X-API-Key")
            or request.query_params.get("api_key")
        )

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key. Provide via X-API-Key header."},
            )

        if api_key != settings.api_key:
            logger.warning(f"Invalid API key from {request.client.host}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key."},
            )

        return await call_next(request)
