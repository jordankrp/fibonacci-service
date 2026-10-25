import json
import logging
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from service import http_server_main
from service.observability import CORRELATION_ID_HEADER, JsonFormatter


def access_log(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    entries = [json.loads(line) for line in caplog.text.splitlines()]
    return [entry for entry in entries if entry["logger"] == "service.observability"]


@pytest.fixture(autouse=True)
def json_caplog(caplog: pytest.LogCaptureFixture) -> None:
    caplog.handler.setFormatter(JsonFormatter())
    caplog.set_level(logging.INFO)


def test_correlation_id_matches_request(client: TestClient) -> None:
    response = client.get("/v1/fibonacci/1", headers={CORRELATION_ID_HEADER: "abc-123"})

    assert response.headers[CORRELATION_ID_HEADER] == "abc-123"


def test_correlation_id_generated_when_missing(client: TestClient) -> None:
    response = client.get("/v1/fibonacci/1")

    assert re.fullmatch(r"[0-9a-f]{32}", response.headers[CORRELATION_ID_HEADER])


def test_log(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    client.get("/v1/fibonacci/5", headers={CORRELATION_ID_HEADER: "abc-123"})

    [entry] = access_log(caplog)
    assert entry.pop("timestamp")
    assert entry.pop("duration_ms") >= 0
    assert entry == {
        "level": "INFO",
        "logger": "service.observability",
        "message": "request",
        "correlation_id": "abc-123",
        "method": "GET",
        "path": "/v1/fibonacci/5",
        "route": "/v1/fibonacci/{n}",
        "status": 200,
    }


def test_unhandled_error_logged_and_keeps_correlation_id(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def runtime_error(_: int) -> list[int]:
        raise RuntimeError("This is a runtime error!")

    monkeypatch.setattr(http_server_main, "fibonacci_sequence", runtime_error)

    with TestClient(http_server_main.app, raise_server_exceptions=False) as client:
        response = client.get("/v1/fibonacci/1", headers={CORRELATION_ID_HEADER: "abc-123"})

    assert response.status_code == 500
    assert response.headers[CORRELATION_ID_HEADER] == "abc-123"
    [entry] = access_log(caplog)
    assert entry["correlation_id"] == "abc-123"
    assert entry["status"] == 500


def test_metrics(client: TestClient) -> None:
    client.get("/v1/fibonacci/5")
    client.get("/v1/does-not-exist")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert (
        'http_request_duration_seconds_count{method="GET",route="/v1/fibonacci/{n}",status="200"}'
        in body
    )
    assert (
        'http_request_duration_seconds_count{method="GET",route="unmatched",status="404"}' in body
    )
    assert "/v1/does-not-exist" not in body
