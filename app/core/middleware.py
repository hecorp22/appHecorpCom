import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from app.core.context import ctx_trace_id, bind_context
from app.core.security import decode_token


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = str(uuid.uuid4())

        # Contexto global
        ctx_trace_id.set(trace_id)
        request.state.trace_id = trace_id

        # --- Usuario global en request.state.user (no crashea si no hay cookie) ---
        request.state.user = None
        try:
            token = request.cookies.get("access_token")
            payload = decode_token(token, expected_type="access") if token else None
            if payload and payload.get("sub"):
                # Carga perezosa del usuario desde DB
                try:
                    from app.database import SessionLocal
                    from app.models.user_model import User
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.email == payload["sub"]).first()
                        request.state.user = user
                    finally:
                        db.close()
                except Exception as e:
                    logger.debug(f"user_load_skip: {e}")
                    request.state.user = None
        except Exception as e:
            logger.debug(f"auth_middleware_skip: {e}")
            request.state.user = None
        # -------------------------------------------------------------------------

        start = time.perf_counter()
        log = bind_context(logger)

        log.info(
            "request_in",
            method=request.method,
            path=request.url.path,
            client=str(request.client)
        )

        response = None

        try:
            response = await call_next(request)

            # Header SIEMPRE presente
            response.headers["X-Trace-Id"] = trace_id

            return response

        except Exception as e:
            log.exception(
                "request_error",
                method=request.method,
                path=request.url.path,
                error=str(e)
            )
            raise

        finally:
            dur_ms = round((time.perf_counter() - start) * 1000, 2)

            log.info(
                "request_out",
                method=request.method,
                path=request.url.path,
                status=getattr(response, "status_code", 500),
                duration_ms=dur_ms
            )
