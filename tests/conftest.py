from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from doc_cheap import Client


class Recorder:
    """Answers every request with a queued response and remembers the requests."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.responses: list[httpx.Response] = []

    def queue(self, status: int, body: Any) -> None:
        self.responses.append(httpx.Response(status, json=body))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responses.pop(0)

    def body(self, index: int = -1) -> Any:
        return json.loads(self.requests[index].content)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOC_CHEAP_API_KEY", raising=False)
    monkeypatch.delenv("DOC_CHEAP_API_BASE", raising=False)


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


@pytest.fixture
def client(recorder: Recorder) -> Iterator[Client]:
    http = httpx.Client(transport=httpx.MockTransport(recorder))
    with Client("sk_test_key", base_url="https://api.test", http_client=http) as c:
        yield c
    http.close()
