import time
import logging
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.hash_ring import ConsistentHashRing
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.core.proxy import forward_request

logger = logging.getLogger("gatekeeper")

class GatekeeperMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, hash_ring: ConsistentHashRing, rate_limiter: SlidingWindowRateLimiter):
        super().__init__(app)
        self.hash_ring = hash_ring
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Skip middleware checks for health checks or admin routes
        if request.url.path.startswith("/health") or request.url.path.startswith("/cluster"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"

        # Enforce Rate Limiting 
        limit_check = await self.rate_limiter.request_validation(client_ip)
        if not limit_check["request_allowed"]:
            return Response(
                content=f'{{"error": "Rate limit exceeded. Try again in {limit_check["retry_after"]}s"}}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(limit_check["retry_after"])
                }
            )

        #Consistent Hash Ring for Backend Node 
        target_node = self.hash_ring.get_node(client_ip)
        if not target_node:
            raise HTTPException(status_code=503, detail="No active backend nodes available in hash ring.")

        #Proxy the Request and Measure Latency 
        start_time = time.time()
        try:
            response = await forward_request(request, target_node)
        except HTTPException as he:
            # If proxy throws an error (e.g. 502/504), return it directly
            return Response(content=f'{{"error": "{he.detail}"}}', status_code=he.status_code, media_type="application/json")
        
        latency_ms = (time.time() - start_time) * 1000
        
        response.headers["X-RateLimit-Remaining"] = str(limit_check["remaining_requests"])
        response.headers["X-Target-Node"] = target_node
        response.headers["X-Proxy-Latency-Ms"] = f"{latency_ms:.2f}"

        return response