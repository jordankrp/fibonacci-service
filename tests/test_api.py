import pytest
from fastapi.testclient import TestClient

from service import http_server_main
from service.fibonacci import MAX_N, fibonacci_sequence


def test_success(client: TestClient) -> None:
    response = client.get("/v1/fibonacci/5")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == [0, 1, 1, 2, 3]


def test_zero(client: TestClient) -> None:
    response = client.get("/v1/fibonacci/0")

    assert response.status_code == 200
    assert response.json() == []


def test_max_n(client: TestClient) -> None:
    response = client.get(f"/v1/fibonacci/{MAX_N}")

    assert response.status_code == 200
    assert response.json() == fibonacci_sequence(MAX_N)


def test_large_number_serialized(client: TestClient) -> None:
    response = client.get("/v1/fibonacci/101")

    assert response.json()[100] == 354224848179261915075
    assert "354224848179261915075" in response.text


def test_negative(client: TestClient) -> None:
    response = client.get("/v1/fibonacci/-1")

    assert response.status_code == 422
    assert response.json() == {
        "message": "Request validation failed",
        "code": "ValidationError",
        "detail": [
            {
                "type": "greater_than_equal",
                "loc": ["path", "n"],
                "msg": "Input should be greater than or equal to 0",
                "input": "-1",
                "ctx": {"ge": 0},
            }
        ],
    }


def test_above_max(client: TestClient) -> None:
    response = client.get(f"/v1/fibonacci/{MAX_N + 1}")

    assert response.status_code == 422
    assert response.json() == {
        "message": "Request validation failed",
        "code": "ValidationError",
        "detail": [
            {
                "type": "less_than_equal",
                "loc": ["path", "n"],
                "msg": f"Input should be less than or equal to {MAX_N}",
                "input": str(MAX_N + 1),
                "ctx": {"le": MAX_N},
            }
        ],
    }


@pytest.mark.parametrize(
    ("n", "received"),
    [("abc", "abc"), ("1.5", "1.5"), ("1e3", "1e3")],
)
def test_non_integer(client: TestClient, n: str, received: str) -> None:
    response = client.get(f"/v1/fibonacci/{n}")

    assert response.status_code == 422
    assert response.json() == {
        "message": "Request validation failed",
        "code": "ValidationError",
        "detail": [
            {
                "type": "int_parsing",
                "loc": ["path", "n"],
                "msg": "Input should be a valid integer, unable to parse string as an integer",
                "input": received,
            }
        ],
    }


def test_unknown_endpoint(client: TestClient) -> None:
    response = client.get("/v1/non-existent")

    assert response.status_code == 404
    assert response.json() == {
        "message": "Endpoint 'GET /v1/non-existent' does not exist",
        "code": "EndpointNotFound",
        "detail": None,
    }


def test_wrong_method(client: TestClient) -> None:
    response = client.post("/v1/fibonacci/5")

    assert response.status_code == 405
    assert response.json() == {
        "message": "Method not allowed on 'POST /v1/fibonacci/5'",
        "code": "MethodNotAllowed",
        "detail": None,
    }
    assert response.headers["allow"] == "GET"


def test_unhandled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(n: int) -> list[int]:
        raise RuntimeError("boom")

    monkeypatch.setattr(http_server_main, "fibonacci_sequence", boom)

    with TestClient(http_server_main.app, raise_server_exceptions=False) as client:
        response = client.get("/v1/fibonacci/1")

    assert response.status_code == 500
    assert response.json() == {
        "message": "Internal server error",
        "code": "InternalServerError",
        "detail": None,
    }
