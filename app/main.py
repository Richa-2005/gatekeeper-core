from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.config import settings
from app.middleware.guard_middleware import GatekeeperMiddleware
from app.core.hash_ring import ConsistentHashRing
from app.core.rate_limiter import SlidingWindowRateLimiter

hash_ring = ConsistentHashRing()
for node_url in settings.node_list:
    hash_ring.add_node(node_url)

rate_limiter = SlidingWindowRateLimiter(
    max_limit_per_minute=settings.DEFAULT_RATE_LIMIT,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Booting up GateKeeper-Core Infrastructure Gateway.")
    print(f"Registered Backend Nodes: {settings.node_list}")
    yield
    print("Shutting down GateKeeper-Core.")

app = FastAPI(
    title="GateKeeper-Core: Distributed Rate-Limiting API Gateway",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(
    GatekeeperMiddleware,
    hash_ring=hash_ring,
    rate_limiter=rate_limiter,
)

@app.get("/healthz", include_in_schema=False)
def healthcheck():
    """Confirm the gateway proxy core is running."""
    return {"status": "gateway_healthy", "nodes_configured": len(settings.node_list)}

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def gateway_proxy_handler(request: Request, full_path: str):
    """Catch all non-gateway routes so the middleware can proxy them."""
    return {"detail": f"Gateway route accepted: /{full_path}"}
