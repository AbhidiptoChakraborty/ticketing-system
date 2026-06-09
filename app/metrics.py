import time
import logging
from typing import Callable

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    HAS_PROM = True
except Exception:  # pragma: no cover - optional dependency
    HAS_PROM = False


if HAS_PROM:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )

    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
    )


    async def metrics_middleware(request, call_next: Callable):
        start = time.time()
        response = await call_next(request)
        resp_time = time.time() - start
        try:
            REQUEST_LATENCY.labels(request.method, request.url.path).observe(resp_time)
            REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
        except Exception:
            logger.exception("Failed to record metrics")
        return response


    # simple metrics router
    from fastapi import APIRouter, Response

    router = APIRouter()


    @router.get("/metrics")
    async def metrics():
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

else:  # no-op middleware and router when prometheus_client isn't installed
    async def metrics_middleware(request, call_next: Callable):
        return await call_next(request)

    from fastapi import APIRouter, Response

    router = APIRouter()


    @router.get("/metrics")
    async def metrics():
        return Response(status_code=501, content=b"metrics not configured")
