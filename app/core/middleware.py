import time, uuid
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from app.core.context import ctx_trace_id, bind_context

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = str(uuid.uuid4())
        ctx_trace_id.set(trace_id)      # guarda en contextvars
        request.state.trace_id = trace_id

        start = time.perf_counter()
        log = bind_context(logger)      # logger con contexto

        log.info("request_in", method=request.method, path=request.url.path)

        try:
            response = await call_next(request)
        except Exception:
            bind_context(logger).exception("request_error")
            raise
        finally:
            dur_ms = round((time.perf_counter() - start) * 1000, 2)
            bind_context(logger).info("request_out", path=request.url.path, status=getattr(response, "status_code", 0), duration_ms=dur_ms)

        response.headers["X-Trace-Id"] = trace_id
        return response
