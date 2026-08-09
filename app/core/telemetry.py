import json
import logging

from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator


RATE_LIMIT_REJECTIONS = Counter(
    "gatekeeper_rate_limit_rejections_total",
    "Total requests rejected by the gateway rate limiter.",
)

PROXY_REQUESTS = Counter(
    "gatekeeper_proxy_requests_total",
    "Total requests proxied by the gateway.",
    ["target_node", "status_code"],
)

PROXY_LATENCY = Histogram(
    "gatekeeper_proxy_latency_seconds",
    "Latency spent proxying requests to upstream backend nodes.",
    ["target_node"],
)


def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def setup_metrics(app):
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


def log_event(logger, level: str, event: str, **fields):
    payload = {"event": event, **fields}
    log_method = getattr(logger, level)
    log_method(json.dumps(payload, default=str))
