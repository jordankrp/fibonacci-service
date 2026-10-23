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

## Development

Requires [uv](https://docs.astral.sh/uv/), which installs the right Python version (3.14).

```sh
uv sync                        # create .venv with all dependencies
uv run pre-commit install      # optional: run format/lint/type checks on commit
uv run pytest                  # unit tests
uv run ruff format .           # format
uv run ruff check .            # lint
uv run mypy service tests      # type-check

uv run uvicorn service.http_server_main:app --port 8070 --reload   # dev server
```

Testing:

- `tests/test_fibonacci.py`: unit tests for the Fibonacci logic in `service/fibonacci.py`
- `tests/test_api.py`: integration tests for the full HTTP app in `service/http_server_main.py` through FastAPI's `TestClient`

## Build and run in production

The service ships as a Docker image. It runs as a non-root user and listens on port 8070.

```sh
docker build -t fibonacci-service .
docker run -d -p 8070:8070 --name fibonacci-service fibonacci-service

curl localhost:8070/v1/fibonacci/10
```


## CI

`.github/workflows/ci.yml` runs on every push to `main` and on every pull request:

1. Format, lint, type-check, and run the tests.
2. Build the Docker image and smoke-test the running container.

## Maintenance

- Dependencies are locked in `uv.lock`. To upgrade, run `uv lock --upgrade`, then run the tests.
- To increase the Python version, change `.python-version`, `requires-python` inside `pyproject.toml`, and the `FROM` line in the `Dockerfile` together. `uv sync` to create a new `uv.lock` file.
- Breaking API changes go under a new `/v2` path. Keep `/v1` until clients have migrated.
