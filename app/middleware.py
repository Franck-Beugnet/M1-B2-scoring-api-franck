"""Logging middleware with request_id and latency tracking.

Adds X-Request-ID to every response and logs structured JSON to file.

Standard schema (FastIA 7 keys):
  - timestamp: added by loguru
  - level: INFO/WARNING/ERROR (based on status code)
  - method: HTTP verb
  - path: URI path
  - status: HTTP status code
  - latency__ms: request duration
  - request__id: unique request ID

Enrichment:
  - endpoint: normalized path (e.g. "/predict", "/health")
  - model_version: from app.state.metadata (if available)
"""
from __future__ import annotations

import time
import uuid

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log each request: method, path, status, latency, request_id."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract endpoint name for normalized logging
        # e.g. "/health" from path, or "/predict" from "/predict"
        path_parts = request.url.path.strip("/").split("/")
        endpoint = f"/{path_parts[0]}" if path_parts[0] else "/"

        start = time.perf_counter()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            logger.bind(request_id=request_id, endpoint=endpoint).exception(
                "Unhandled exception in request"
            )
            raise

        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        # Select log level based on HTTP status code
        if status_code < 400:
            log_level = "INFO"
        elif status_code < 500:
            log_level = "WARNING"
        else:
            log_level = "ERROR"

        # Build context dict with FastIA 7 keys + enrichment
        log_context = {
            "method": request.method,
            "path": request.url.path,
            "status": status_code,
            "latency__ms": latency_ms,
            "request__id": request_id,
            "endpoint": endpoint,
        }

        # Add model_version if available (for /predict and all endpoints)
        if hasattr(request.app.state, "metadata") and request.app.state.metadata:
            log_context["model_version"] = request.app.state.metadata.get("model_version")

        # Bind context to logger and interpolate message with explicit parameters
        logger.bind(**log_context).log(
            log_level,
            "{method} {endpoint} {status} {latency__ms}ms",
            method=request.method,
            endpoint=endpoint,
            status=status_code,
            latency__ms=latency_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
