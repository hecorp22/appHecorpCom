"""
Middlewares de seguridad:
  - SecurityHeadersMiddleware: HSTS, X-Frame-Options, X-Content-Type-Options,
    Referrer-Policy, Permissions-Policy, CSP básica
  - RateLimitMiddleware: rate-limit en memoria por IP+path; bloquea abuso
  - SecurityMonitorMiddleware: detecta patrones sospechosos (paths típicos de
    bots/scanners, SQLi/XSS naive, 401/403 repetidos) y los anota.

Sin dependencias externas para no inflar requirements.txt.
"""
import os
import re
import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple, List
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from loguru import logger


# =========================================================================== #
# 1. Security headers
# =========================================================================== #
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp: Response = await call_next(request)
        h = resp.headers
        # mantenemos los que ya pone otra capa; añadimos faltantes
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "SAMEORIGIN")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy",
                     "geolocation=(self), camera=(self), microphone=(self), "
                     "payment=(self), usb=()")
        # HSTS solo en HTTPS
        if request.url.scheme == "https":
            h.setdefault("Strict-Transport-Security",
                         "max-age=31536000; includeSubDomains")
        # CSP suave (no rompe Tailwind CDN/Leaflet OSRM/OSM)
        h.setdefault("Content-Security-Policy",
                     "default-src 'self'; "
                     "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                     "https://cdn.tailwindcss.com https://unpkg.com "
                     "https://*.openstreetmap.org; "
                     "style-src 'self' 'unsafe-inline' https://unpkg.com; "
                     "img-src 'self' data: blob: https:; "
                     "connect-src 'self' https://*.openstreetmap.org "
                     "https://router.project-osrm.org "
                     "https://nominatim.openstreetmap.org; "
                     "frame-ancestors 'self'; "
                     "object-src 'none'; "
                     "base-uri 'self'")
        return resp


# =========================================================================== #
# 2. Rate limit + monitor en una sola pieza para compartir el store
# =========================================================================== #
SUSPICIOUS_PATH_RX = re.compile(
    r"(?ix)"
    r"(/wp-(login|admin|content|includes)|/xmlrpc\.php|/phpmyadmin|/\.env"
    r"|/\.git|/eval|/owa|/cgi-bin|/etc/passwd|/console|/jenkins|/manager/html"
    r"|/actuator|/_ignition|/server-status|/struts2|/solr/|/druid/|/api/jsonws"
    r"|/HNAP1|/cnxe?|\.php($|\?))"
)
SUSPICIOUS_QS_RX = re.compile(
    r"(?ix)"
    r"(\bUNION\s+SELECT\b|<script\b|onerror=|javascript:|"
    r"\bSELECT\b.*\bFROM\b|/etc/passwd|\.\./\.\./|;\s*(rm|wget|curl)\s)"
)

# Reglas (path-prefix, max_requests, ventana_seg) — orden importa
RATE_RULES: List[Tuple[str, int, int]] = [
    ("/login", 10, 60),                       # login: 10/min/IP
    ("/api/auth", 10, 60),
    ("/api/delivery/track/", 240, 60),        # pings GPS legítimos pueden ser muchos
    ("/api/", 120, 60),                       # API general 120/min/IP
    ("/", 240, 60),                           # global por IP
]

# Rutas que NO se cuentan como "abuso" aunque sean 401 (público sin auth a propósito)
NO_AUTH_PUBLIC_PREFIXES = ("/track/", "/driver/", "/static/", "/healthz",
                            "/login", "/sw.js", "/favicon")

# Stores en memoria (un proceso) — suficiente; en multiproceso preferiríamos Redis
_lock = Lock()
_buckets: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)   # (ip, key) -> timestamps
_blocks: Dict[str, float] = {}                                       # ip -> unblock_at
_events: Deque[dict] = deque(maxlen=500)                             # anillo de eventos
_counters = defaultdict(int)
_first_seen = {}                                                     # ip -> first_ts
_last_seen = {}                                                      # ip -> last_ts


def _client_ip(request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _record_event(kind: str, ip: str, detail: str, severity: str = "warn"):
    ev = {
        "ts": time.time(), "kind": kind, "ip": ip,
        "detail": detail[:300], "severity": severity,
    }
    _events.appendleft(ev)
    _counters[kind] += 1
    if severity in ("warn", "high"):
        logger.warning(f"sec.{kind} ip={ip} {detail[:200]}")


def _rule_for(path: str) -> Tuple[str, int, int]:
    for prefix, lim, win in RATE_RULES:
        if path.startswith(prefix):
            return prefix, lim, win
    return "/", 240, 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ip = _client_ip(request)
        now = time.time()

        # IP bloqueada?
        unblock_at = _blocks.get(ip)
        if unblock_at and unblock_at > now:
            return JSONResponse(
                {"detail": "Too many requests. Try later."},
                status_code=429,
                headers={"Retry-After": str(int(unblock_at - now))},
            )

        path = request.url.path
        rule_key, limit, window = _rule_for(path)

        # update bucket
        with _lock:
            bucket = _buckets[(ip, rule_key)]
            cutoff = now - window
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            bucket.append(now)
            count = len(bucket)
            _first_seen.setdefault(ip, now)
            _last_seen[ip] = now

        if count > limit:
            # bloquear ip 5 min
            _blocks[ip] = now + 300
            _record_event("rate_limit", ip,
                          f"path={path} count={count}/{limit} window={window}s",
                          severity="high")
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "300"},
            )

        return await call_next(request)


class SecurityMonitorMiddleware(BaseHTTPMiddleware):
    """Anota patrones sospechosos sin bloquear (deja al rate limiter eso)."""
    async def dispatch(self, request, call_next):
        ip = _client_ip(request)
        path = request.url.path
        qs = request.url.query or ""

        # Patrones obvios de scanner
        if SUSPICIOUS_PATH_RX.search(path):
            _record_event("scan_path", ip, f"{request.method} {path}", severity="warn")
        if qs and SUSPICIOUS_QS_RX.search(qs):
            _record_event("injection_attempt", ip,
                          f"{request.method} {path}?{qs[:200]}", severity="high")

        # body suspicious (solo POST/PUT/PATCH, sin consumir streams grandes)
        ctype = (request.headers.get("content-type") or "").lower()
        if request.method in ("POST", "PUT", "PATCH") and "application/json" in ctype:
            try:
                body_bytes = await request.body()
                if body_bytes and len(body_bytes) < 8000:
                    body_text = body_bytes.decode("utf-8", "ignore")
                    if SUSPICIOUS_QS_RX.search(body_text):
                        _record_event("injection_attempt", ip,
                                      f"{request.method} {path} body~"
                                      f"{body_text[:160]}", severity="high")
                    # re-inject body
                    async def receive():
                        return {"type": "http.request", "body": body_bytes,
                                "more_body": False}
                    request._receive = receive
            except Exception:
                pass

        resp: Response = await call_next(request)

        # 401/403 desde rutas no públicas → posible fuerza bruta
        if resp.status_code in (401, 403) and not any(path.startswith(p) for p in NO_AUTH_PUBLIC_PREFIXES):
            _record_event("auth_fail", ip,
                          f"{request.method} {path} → {resp.status_code}",
                          severity="warn")

        # 5xx → registramos también
        if resp.status_code >= 500:
            _record_event("server_error", ip,
                          f"{request.method} {path} → {resp.status_code}",
                          severity="warn")

        return resp


# =========================================================================== #
# 3. API pública del módulo (consumida por el panel)
# =========================================================================== #
def get_security_snapshot() -> dict:
    now = time.time()
    blocks_active = {ip: int(unblock - now)
                     for ip, unblock in _blocks.items() if unblock > now}
    by_kind = dict(_counters)
    last = list(_events)[:50]
    # top IPs por # eventos en la ventana actual
    ip_count = defaultdict(int)
    for e in _events:
        ip_count[e["ip"]] += 1
    top_ips = sorted(ip_count.items(), key=lambda x: -x[1])[:15]
    return {
        "now": now,
        "blocks_active": blocks_active,
        "events_total": sum(by_kind.values()),
        "by_kind": by_kind,
        "top_ips": [{"ip": ip, "count": c,
                     "first_seen": _first_seen.get(ip),
                     "last_seen": _last_seen.get(ip)} for ip, c in top_ips],
        "events": last,
    }


def unblock_ip(ip: str) -> bool:
    if ip in _blocks:
        _blocks.pop(ip, None)
        _record_event("unblock", ip, "manual", severity="info")
        return True
    return False
