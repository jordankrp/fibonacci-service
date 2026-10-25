FROM python:3.14.5-slim-bookworm AS base

RUN useradd --user-group --system --create-home --no-log-init application
USER application

WORKDIR /api

FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff /uv /bin/uv

ENV UV_LINK_MODE=copy

COPY ["./pyproject.toml", "./uv.lock", "/api/"]

RUN uv sync --python-preference only-system --locked --no-dev --compile-bytecode

FROM base

ENV VIRTUAL_ENV=/api/.venv \
    PATH=/api/.venv/bin:$PATH \
    PYTHONPATH=/api/

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY ./service ./service

CMD ["uvicorn", "service.http_server_main:app", "--host", "0.0.0.0", "--port", "8070"]
