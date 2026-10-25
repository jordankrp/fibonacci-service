from typing import Annotated

from fastapi import FastAPI, Path, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from service.error_handler import handlers as error_handlers
from service.fibonacci import MAX_N, fibonacci_sequence
from service.observability import observe_requests, setup_logging

setup_logging()

app = FastAPI(exception_handlers=error_handlers)
app.middleware("http")(observe_requests)


@app.get("/v1/fibonacci/{n}")
def get_fibonacci_sequence(n: Annotated[int, Path(ge=0, le=MAX_N)]) -> list[int]:
    return fibonacci_sequence(n)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    # Prometheus metrics not meant to be public: block at ingress / load balancer.
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
