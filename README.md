# GateKeeper-Core

![GateKeeper-Core request flow](assets/gatekeeper-flow.svg)

GateKeeper-Core is a lightweight FastAPI-based API gateway that forwards client traffic to a pool of backend nodes while applying per-client rate limiting and consistent-hash routing.

The project is designed as a small, readable gateway core: requests enter through one public gateway, pass through middleware for traffic control, and are then proxied to a stable backend node selected from a consistent hash ring.

## Features

- Reverse proxy for forwarding HTTP requests to backend services
- Consistent hashing for stable client-to-node routing
- Sliding-window rate limiting per client IP
- Configurable backend node list through environment variables
- Response metadata headers for observability
- Docker and Docker Compose support for local multi-service testing
- Mock backend service for gateway verification

## Architecture

```text
Client
  |
  v
Gateway FastAPI app :8000
  |
  v
GatekeeperMiddleware
  |
  |-- health/admin route bypass
  |-- client IP extraction
  |-- sliding-window rate limit check
  |-- consistent hash node selection
  |-- proxy latency measurement
  |
  v
Selected backend node
  |
  v
Backend response returned to client
```

The gateway exposes a catch-all route so application traffic can enter FastAPI, but the actual gateway behavior lives in middleware. The middleware decides whether a request is allowed, selects a backend node, forwards the request, and appends gateway metadata headers to the response.

## Project Structure

```text
.
├── app
│   ├── config.py                    # Environment-backed gateway settings
│   ├── main.py                      # FastAPI app, health route, middleware registration
│   ├── core
│   │   ├── hash_ring.py             # Consistent hash ring implementation
│   │   ├── proxy.py                 # Async HTTP forwarding with httpx
│   │   └── rate_limiter.py          # Sliding-window rate limiter
│   └── middleware
│       └── guard_middleware.py      # Gateway request-control middleware
├── tests
│   ├── mock_backend.py              # Simple backend worker used for local testing
│   ├── test_hash_ring.py            # Hash ring behavior tests
│   └── test_rate_limiter.py         # Rate limiter behavior tests
├── Dockerfile                       # Container image definition
├── docker-compose.yml               # Gateway + backend worker stack
├── requirements.txt                 # Python dependencies
└── .env.example                     # Example runtime configuration
```

## Request Flow

1. A client sends a request to the gateway, for example `GET /api/v1/test`.
2. `GatekeeperMiddleware` ignores internal routes such as `/healthz`.
3. The middleware identifies the client by IP address.
4. The sliding-window rate limiter checks whether the client is still within its request budget.
5. The consistent hash ring maps the client IP to one backend node.
6. `app.core.proxy.forward_request()` forwards the original method, path, query string, headers, cookies, and body to the selected backend.
7. The gateway returns the backend response with gateway headers attached.

Example response headers:

```text
X-RateLimit-Remaining: 99
X-Target-Node: http://localhost:8001
X-Proxy-Latency-Ms: 12.34
```

## Configuration

Runtime configuration is managed by `pydantic-settings` in `app/config.py`.

| Variable | Default | Description |
| --- | --- | --- |
| `GATEWAY_PORT` | `8000` | Intended gateway port |
| `DEFAULT_RATE_LIMIT` | `100` | Maximum requests allowed per client window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding-window duration in seconds |
| `BACKEND_NODES` | `http://localhost:8001,http://localhost:8002,http://localhost:8003` | Comma-separated backend node URLs |

Create a local `.env` from the example if you want to override defaults:

```bash
cp .env.example .env
```

## Local Development

Install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start three mock backend workers in separate terminals:

```bash
uvicorn tests.mock_backend:app --host 127.0.0.1 --port 8001
uvicorn tests.mock_backend:app --host 127.0.0.1 --port 8002
uvicorn tests.mock_backend:app --host 127.0.0.1 --port 8003
```

Start the gateway:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Send traffic through the gateway:

```bash
curl -i http://127.0.0.1:8000/api/v1/test
```

Check gateway health:

```bash
curl http://127.0.0.1:8000/healthz
```

## Docker

Build and run the full local stack with Docker Compose:

```bash
docker compose up --build
```

This starts:

- `gateway` on host port `8000`
- `backend1` on host port `8001`
- `backend2` on host port `8002`
- `backend3` on host port `8003`

Inside Docker Compose, the gateway uses service names instead of `localhost`:

```text
http://backend1:8001,http://backend2:8002,http://backend3:8003
```

That distinction matters because `localhost` inside a container points to the container itself, not another service.

## Testing

Run the hash ring test:

```bash
pytest -q tests/test_hash_ring.py
```

Run the rate limiter test module directly:

```bash
python3 tests/test_rate_limiter.py
```

The rate limiter tests are async. To run them through `pytest`, add an async pytest plugin such as `pytest-asyncio` and mark/configure the async tests accordingly.

## Core Components

### `ConsistentHashRing`

`app/core/hash_ring.py` maps client keys to backend nodes using virtual nodes. This keeps routing stable: the same client usually lands on the same backend, and removing a backend only remaps the keys that belonged to that backend.

### `SlidingWindowRateLimiter`

`app/core/rate_limiter.py` tracks request timestamps per client and rejects requests once the configured limit is exceeded within the active time window. An async lock protects the in-memory counters during concurrent access.

### `GatekeeperMiddleware`

`app/middleware/guard_middleware.py` is the main gateway control point. It applies rate limiting, selects a target backend, forwards traffic, handles proxy errors, and attaches gateway metadata headers.

### `forward_request`

`app/core/proxy.py` performs async HTTP forwarding with `httpx`. It reconstructs the target URL, preserves the incoming request method and body, removes the original `Host` header, and returns the backend response to the client.

## Current Limitations

- Rate-limit state is in memory, so it is not shared across multiple gateway replicas.
- Backend health checking is not implemented yet.
- Node membership is loaded at startup and is not dynamically rebalanced at runtime.
- The proxy currently buffers request and response bodies instead of streaming them.
- Client identity is based on `request.client.host`; deployments behind another reverse proxy may need trusted forwarded-header handling.

## Roadmap Ideas

- Add active backend health checks and automatic node removal
- Add Redis-backed distributed rate limiting
- Add request/response streaming for large payloads
- Add structured logging and metrics export
- Add pytest async support and end-to-end proxy tests
- Add admin APIs for inspecting nodes and rate-limit state

---

<p align="center">
  Built by <strong>Richa Gupta</strong>
</p>

