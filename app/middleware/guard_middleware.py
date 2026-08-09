import time
import logging
import uuid
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.hash_ring import ConsistentHashRing
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.core.proxy import forward_request
from app.core.telemetry import RATE_LIMIT_REJECTIONS, PROXY_REQUESTS, PROXY_LATENCY, log_event

logger = logging.getLogger("gatekeeper")

class GatekeeperMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, hash_ring: ConsistentHashRing, rate_limiter: SlidingWindowRateLimiter):
        super().__init__(app)
        self.hash_ring = hash_ring
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Skip middleware checks for health checks or admin routes
        if (
            request.url.path.startswith("/health")
            or request.url.path.startswith("/cluster")
            or request.url.path == "/metrics"
        ):
            return await call_next(request)

        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        client_ip = request.client.host if request.client else "127.0.0.1"
        log_event(
            logger,
            "info",
            "request_started",
            request_id=request_id,
            client_ip=client_ip,
            method=request.method,
            path=request.url.path,
        )

        # Enforce Rate Limiting 
        limit_check = await self.rate_limiter.request_validation(client_ip)
        if not limit_check["request_allowed"]:
            RATE_LIMIT_REJECTIONS.inc()
            log_event(
                logger,
                "warning",
                "rate_limited",
                request_id=request_id,
                client_ip=client_ip,
                retry_after=limit_check["retry_after"],
            )
            return Response(
                content=f'{{"error": "Rate limit exceeded. Try again in {limit_check["retry_after"]}s"}}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(limit_check["retry_after"]),
                    "X-Request-ID": request_id,
                }
            )

        #Consistent Hash Ring for Backend Node 
        target_node = self.hash_ring.get_node(client_ip)
        if not target_node:
            raise HTTPException(status_code=503, detail="No active backend nodes available in hash ring.")

        #Proxy the Request and Measure Latency 
        start_time = time.time()
        try:
            response = await forward_request(
                request,
                target_node,
                extra_headers={"X-Request-ID": request_id},
            )
        except HTTPException as he:
            # If proxy throws an error (e.g. 502/504), return it directly
            log_event(
                logger,
                "error",
                "proxy_failed",
                request_id=request_id,
                client_ip=client_ip,
                target_node=target_node,
                status_code=he.status_code,
                error=he.detail,
            )
            return Response(
                content=f'{{"error": "{he.detail}"}}',
                status_code=he.status_code,
                media_type="application/json",
                headers={"X-Request-ID": request_id},
            )
        
        latency_seconds = time.time() - start_time
        latency_ms = latency_seconds * 1000
        PROXY_REQUESTS.labels(target_node=target_node, status_code=str(response.status_code)).inc()
        PROXY_LATENCY.labels(target_node=target_node).observe(latency_seconds)
        log_event(
            logger,
            "info",
            "request_proxied",
            request_id=request_id,
            client_ip=client_ip,
            method=request.method,
            path=request.url.path,
            target_node=target_node,
            status_code=response.status_code,
            latency_ms=f"{latency_ms:.2f}",
        )
        
        response.headers["X-RateLimit-Remaining"] = str(limit_check["remaining_requests"])
        response.headers["X-Target-Node"] = target_node
        response.headers["X-Proxy-Latency-Ms"] = f"{latency_ms:.2f}"
        response.headers["X-Request-ID"] = request_id

        return response
