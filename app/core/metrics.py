from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_client import Histogram
import time
from starlette.middleware.base import BaseHTTPMiddleware

# Histograma propio opcional (por path)
REQUEST_TIME = Histogram(
    "http_request_duration_seconds_custom",
    "Tiempo de respuesta por endpoint",
    ["path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

def instrument(app):
    """
    Instrumenta FastAPI y expone /metrics.
    Compatible con prometheus-fastapi-instrumentator >= 6.x/7.x
    """
    inst = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers={"/metrics", "/healthz"},
    )

    # ⚠️ En 7.1.0 NO existe request_counter(); usar requests()
    inst.add(metrics.requests())
    inst.add(metrics.latency())
    inst.add(metrics.response_size())
    inst.add(metrics.default())
    # Si quieres tamaño de request: inst.add(metrics.request_size())

    inst.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    return inst

class CustomLatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path in ("/metrics", "/healthz"):
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        REQUEST_TIME.labels(request.url.path).observe(time.perf_counter() - start)
        return response
