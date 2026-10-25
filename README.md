# Fibonacci Service

An HTTP API service for calculating Fibonacci numbers.

## API

### `GET /v1/fibonacci/{n}`

Returns the first `n` Fibonacci numbers starting from 0.

```console
$ curl localhost:8070/v1/fibonacci/5
[0,1,1,2,3]
```

| Input                       | Status | Body                                       |
|-----------------------------|--------|--------------------------------------------|
| `0 <= n <= 1000`            | 200    | `[0, 1, 1, ...]` (`n = 0` gives `[]`)      |
| `n < 0`, `n > 1000`, non-int | 422    | `{"message", "code": "ValidationError", "detail": [...]}` |
| Unknown path                | 404    | `{"message", "code": "EndpointNotFound", "detail": null}` |
| Method other than `GET`     | 405    | `{"message", "code": "MethodNotAllowed", "detail": null}` |

All errors share the format `{"message": str, "code": str, "detail": any}`.

`n` is capped at 1000 (defined by `MAX_N` in `service/fibonacci.py`) to keep response size and CPU time per
request bounded.

Numbers are returned as exact JSON integers. Note that values from `n=79` onwards exceed 2^53, so JavaScript's `JSON.parse` will round them as it stores every number as a 64-bit float by default. (Front-end) clients that need them exactly should use a BigInt JSON parser.

### `GET /health`

Liveness probe, returns `200 {"status": "ok"}`. It is not versioned since it is meant for infrastructure rather than API clients.

### `GET /metrics`

Prometheus metrics (see [Observability](#observability)). Like `/health` it is for infrastructure:
don't expose it publicly, block it at the ingress or load balancer.

## Observability

### Logs

Everything is logged as one JSON object per line on stdout. Each request produces one access log line:

```json
{"timestamp": "2026-10-25T13:52:21.170825+00:00", "level": "INFO", "logger": "service.observability", "message": "request", "correlation_id": "trace-me-1", "method": "GET", "path": "/v1/fibonacci/5", "route": "/v1/fibonacci/{n}", "status": 200, "duration_ms": 0.31}
```

Unhandled exceptions are logged by uvicorn with the full traceback with the same `correlation_id`.

### Correlation IDs

Every response has an `X-Correlation-ID` header, including error responses. If the request sends
one it is reused, otherwise a new ID is generated. Every log line written while handling the
request carries it, so searching for it returns everything about that request.

### Metrics

`GET /metrics` exposes `http_request_duration_seconds`, a histogram labelled by `method`, `route`
and `status`. It gives request rate, error rate and latency percentiles. The standard `process_*`
and `python_*` metrics (CPU, memory, garbage collection) are included automatically.

`route` is the route template (e.g. `/v1/fibonacci/{n}`); requests to unknown paths are grouped as
`unmatched`. Labelling by raw path would create a separate time series for every URL.

## Development

Requires [uv](https://docs.astral.sh/uv/), which installs the right Python version (3.14).

```sh
uv sync                        # create/ update .venv with all dependencies
uv run pre-commit install      # run once to format/ lint/ type-check on every commit
uv run pytest                  # unit tests
uv run ruff format .           # format
uv run ruff check .            # lint
uv run mypy service tests      # type-check

uv run uvicorn service.http_server_main:app --port 8070 --reload   # dev server
```

Testing:

- `tests/test_fibonacci.py`: unit tests for the Fibonacci logic in `service/fibonacci.py`
- `tests/test_api.py`: integration tests for the full HTTP app in `service/http_server_main.py` through FastAPI's `TestClient`
- `tests/test_observability.py`: correlation IDs, access log and metrics from `service/observability.py`

## Build and run in production

The service ships as a Docker image. It runs as a non-root user and listens on port 8070.

```sh
docker build -t fibonacci-service .
docker run -d -p 8070:8070 --name fibonacci-service fibonacci-service

curl localhost:8070/health
curl localhost:8070/v1/fibonacci/10
```

For an orchestrator or load balancer use the health checks at `GET /health` on port 8070.

### Published images

CI pushes every commit on `main` that passes all checks to Docker Hub as
[`jordankrp93/fibonacci-service`](https://hub.docker.com/r/jordankrp93/fibonacci-service), with
two tags:

- `<full git commit SHA>`: immutable. Deploy this tag, so production runs exactly the image CI
  tested and a rollback is just deploying the previous SHA.
- `latest`: changes with every push to `main`.

```sh
docker run -d -p 8070:8070 jordankrp93/fibonacci-service:<commit-sha>
```

Pushing requires a Docker Hub access token with read & write scope, stored as the GitHub Actions
repository secret `DOCKERHUB_TOKEN`.

## CI

`.github/workflows/ci.yml` runs on every push to `main` and on every pull request:

1. Format, lint, type-check, and run the tests.
2. Build the Docker image and smoke-test the running container.
3. On `main` only: push that image to Docker Hub.

## Maintenance

- Dependency updates are automated with [Renovate](https://docs.renovatebot.com/) (`renovate.json`).
  It opens PRs for Python packages (`uv.lock`), the Docker base image, uv and GitHub Actions. Pending updates are listed in the Dependency Dashboard issue on GitHub,
  and run logs are in the [Mend developer portal](https://developer.mend.io/github/jordankrp/fibonacci-service).
- Two upgrades need a manual step:
  - **New Python minor version** (e.g. 3.15): approve it on the Dependency Dashboard. On the PR's
    branch, update `requires-python` in `pyproject.toml`, run `uv lock`, and push.
  - **New Debian release**: Renovate never changes the `-slim-bookworm` suffix in the Dockerfile's
    `FROM` tag. Switch it by hand before the old release loses security support.
- Breaking API changes go under a new `/v2` path. Keep `/v1` until clients have migrated.
