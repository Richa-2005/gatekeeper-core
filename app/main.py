from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings

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

@app.get("/healthz", include_in_schema=False)
def healthcheck():
    """Confirm the gateway proxy core is running."""
    return {"status": "gateway_healthy", "nodes_configured": len(settings.node_list)}