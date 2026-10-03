from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
import pytest
from doc_cheap import Client
from langchain_core.tools import ToolException
from pydantic import SecretStr, ValidationError

from langchain_doccheap import (
    DocCheapDeleteScan,
    DocCheapGetScan,
    DocCheapGetUsage,
    DocCheapListScans,
    DocCheapScanDocument,
    DocCheapToolkit,
    ScanDocumentInput,
    __version__,
)

from .conftest import Recorder

SCAN = {"id": "scn_1", "meta": {"status": "unsupported_document", "billed": False}}
ERROR = {"error": {"code": "scan_not_found", "message": "No such scan.", "request_id": "req_1"}}


def test_scan_from_base64_sends_the_image_and_returns_json(
    client: Client, recorder: Recorder
) -> None:
    recorder.queue(201, SCAN)
    tool = DocCheapScanDocument(client=client)
    out = tool.invoke({"image_base64": "aGVsbG8=", "reference": "case-7", "expect_country": "GBR"})
    assert json.loads(out) == SCAN
    request = recorder.requests[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/scans"
    assert recorder.body() == {
        "image": "aGVsbG8=",
        "reference": "case-7",
        "options": {"expect_country": "GBR"},
    }


def test_scan_from_path_reads_the_file(client: Client, recorder: Recorder, tmp_path: Path) -> None:
    image = tmp_path / "doc.png"
    image.write_bytes(b"\x89PNG-bytes")
    recorder.queue(201, SCAN)
    DocCheapScanDocument(client=client).invoke({"image_path": str(image)})
    assert recorder.body() == {"image": base64.b64encode(b"\x89PNG-bytes").decode()}


@pytest.mark.parametrize(
    "args",
    [{}, {"image_path": "a.png", "image_base64": "aGVsbG8="}],
)
def test_scan_needs_exactly_one_image(args: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="exactly one of image_path or image_base64"):
        ScanDocumentInput(**args)


def test_scan_input_refuses_a_bad_country() -> None:
    with pytest.raises(ValidationError):
        ScanDocumentInput(image_base64="aGVsbG8=", expect_country="gb")


def test_get_scan(client: Client, recorder: Recorder) -> None:
    recorder.queue(200, SCAN)
    out = DocCheapGetScan(client=client).invoke({"scan_id": "scn_1"})
    assert json.loads(out) == SCAN
    assert recorder.requests[0].url.path == "/v1/scans/scn_1"


def test_list_scans_passes_limit_and_cursor(client: Client, recorder: Recorder) -> None:
    page: dict[str, object] = {"scans": [], "next_cursor": None}
    recorder.queue(200, page)
    out = DocCheapListScans(client=client).invoke({"limit": 5, "cursor": "c1"})
    assert json.loads(out) == page
    params = recorder.requests[0].url.params
    assert params["limit"] == "5"
    assert params["cursor"] == "c1"


def test_list_scans_without_arguments(client: Client, recorder: Recorder) -> None:
    recorder.queue(200, {"scans": [], "next_cursor": None})
    DocCheapListScans(client=client).invoke({})
    assert str(recorder.requests[0].url) == "https://api.test/v1/scans"


def test_delete_scan(client: Client, recorder: Recorder) -> None:
    recorder.queue(200, {"id": "scn_1", "deleted": True})
    out = DocCheapDeleteScan(client=client).invoke({"scan_id": "scn_1"})
    assert json.loads(out) == {"id": "scn_1", "deleted": True}
    assert recorder.requests[0].method == "DELETE"


def test_usage(client: Client, recorder: Recorder) -> None:
    usage = {"free_allowance": {"remaining": 100}}
    recorder.queue(200, usage)
    out = DocCheapGetUsage(client=client).invoke({})
    assert json.loads(out) == usage
    assert recorder.requests[0].url.path == "/v1/usage"


def test_api_error_is_returned_to_the_model_as_text(client: Client, recorder: Recorder) -> None:
    recorder.queue(404, ERROR)
    out = DocCheapGetScan(client=client).invoke({"scan_id": "scn_x"})
    assert out == "doc.cheap error: 404 scan_not_found: No such scan."


def test_api_error_is_raised_when_handling_is_off(client: Client, recorder: Recorder) -> None:
    recorder.queue(404, ERROR)
    tool = DocCheapGetScan(client=client, handle_tool_error=False)
    with pytest.raises(ToolException, match="scan_not_found"):
        tool.invoke({"scan_id": "scn_x"})


def test_missing_key_is_reported_not_raised() -> None:
    out = DocCheapGetUsage().invoke({})
    assert "no API key" in out
    assert "sk_sandbox_public" in out


def test_tool_creates_its_own_client_once(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    original = httpx.Client.__init__

    def patched(self: httpx.Client, *args: object, **kwargs: object) -> None:
        kwargs["transport"] = transport
        original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx.Client, "__init__", patched)
    monkeypatch.setenv("DOC_CHEAP_API_KEY", "sk_env_key")
    tool = DocCheapGetUsage(base_url="https://api.example")
    tool.invoke({})
    tool.invoke({})
    assert len(seen) == 2
    assert seen[0].headers["authorization"] == "Bearer sk_env_key"
    assert str(seen[0].url) == "https://api.example/v1/usage"
    assert seen[0].headers["user-agent"].startswith(f"langchain-doccheap/{__version__} ")


def test_toolkit_shares_the_given_client(client: Client) -> None:
    tools = DocCheapToolkit(client=client).get_tools()
    assert [t.name for t in tools] == [
        "doc_cheap_scan_document",
        "doc_cheap_get_scan",
        "doc_cheap_list_scans",
        "doc_cheap_get_usage",
        "doc_cheap_delete_scan",
    ]
    assert all(getattr(t, "client", None) is client for t in tools)


def test_toolkit_can_leave_out_delete() -> None:
    tools = DocCheapToolkit(api_key=SecretStr("sk_test_key"), include_delete=False).get_tools()
    assert "doc_cheap_delete_scan" not in [t.name for t in tools]
    clients = {id(getattr(t, "client", None)) for t in tools}
    assert len(clients) == 1


def test_toolkit_creates_its_client_once() -> None:
    toolkit = DocCheapToolkit(api_key=SecretStr("sk_test_key"), base_url="https://api.example")
    first = toolkit.get_tools()[0]
    second = toolkit.get_tools()[0]
    assert getattr(first, "client", None) is getattr(second, "client", None)
    assert getattr(first, "client").base_url == "https://api.example"  # noqa: B009
