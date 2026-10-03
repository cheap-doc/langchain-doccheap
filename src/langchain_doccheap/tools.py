"""LangChain tools that call the doc.cheap document-recognition API."""

from __future__ import annotations

import json
from typing import Any

from doc_cheap import API_KEY_ENV, Client, DocCheapError
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from langchain_core.utils import secret_from_env
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, SecretStr, model_validator

from ._version import __version__

_USER_AGENT = f"langchain-doccheap/{__version__}"


def _to_json(value: Any) -> str:
    # Tool output goes back to a chat model as text, so the API's JSON answer
    # is passed through as JSON rather than as a Python repr.
    return json.dumps(value, ensure_ascii=False)


class _DocCheapTool(BaseTool):
    """Shared configuration of the doc.cheap tools.

    The API key is the ``api_key`` argument, else the ``DOC_CHEAP_API_KEY``
    environment variable. A ``client`` passed in is used as given and stays
    the caller's to close; otherwise the tool creates one on first use.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    api_key: SecretStr | None = Field(default_factory=secret_from_env(API_KEY_ENV, default=None))
    """The doc.cheap API key; ``sk_sandbox_public`` works without an account."""

    base_url: str | None = None
    """The API address; the client's default when omitted."""

    client: Client | None = Field(default=None, exclude=True)
    """A ready ``doc_cheap.Client`` to send the requests through."""

    _owned_client: Client | None = PrivateAttr(default=None)

    def __init__(self, **kwargs: Any) -> None:
        # An API error goes back to the model as the tool's answer, so an
        # agent can react to it, unless the caller chose otherwise.
        kwargs.setdefault("handle_tool_error", True)
        super().__init__(**kwargs)

    def _client(self) -> Client:
        if self.client is not None:
            return self.client
        if self._owned_client is None:
            key = self.api_key.get_secret_value() if self.api_key is not None else None
            self._owned_client = Client(key, base_url=self.base_url, user_agent=_USER_AGENT)
        return self._owned_client

    def _call(self, operation: str, **kwargs: Any) -> str:
        try:
            result = getattr(self._client(), operation)(**kwargs)
        except DocCheapError as err:
            raise ToolException(f"doc.cheap error: {err}") from err
        return _to_json(result)


class ScanDocumentInput(BaseModel):
    """Arguments of :class:`DocCheapScanDocument`."""

    image_path: str | None = Field(
        default=None,
        description="Path of a local JPEG or PNG file holding the document.",
    )
    image_base64: str | None = Field(
        default=None,
        description="The JPEG or PNG image as base64 text, with or without a data: prefix.",
    )
    reference: str | None = Field(
        default=None,
        max_length=128,
        description="An optional label of your own, stored with the result.",
    )
    expect_country: str | None = Field(
        default=None,
        pattern=r"^[A-Z]{3}$",
        description="Optional ISO 3166-1 alpha-3 code of the issuing country, e.g. GBR.",
    )

    @model_validator(mode="after")
    def _one_image(self) -> ScanDocumentInput:
        if (self.image_path is None) == (self.image_base64 is None):
            raise ValueError("give exactly one of image_path or image_base64")
        return self


class DocCheapScanDocument(_DocCheapTool):
    """Reads a passport, national ID card or driving licence into JSON."""

    name: str = "doc_cheap_scan_document"
    description: str = (
        "Reads a photo or scan of a passport, national ID card or driving licence "
        "and returns the printed fields (name, date of birth, document number, "
        "expiry, machine-readable zone) as JSON. Give image_path or image_base64. "
        "One recognised document costs one credit; an image with no readable "
        "document costs nothing and comes back with billed set to false."
    )
    args_schema: type[BaseModel] = ScanDocumentInput

    def _run(
        self,
        image_path: str | None = None,
        image_base64: str | None = None,
        reference: str | None = None,
        expect_country: str | None = None,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        return self._call(
            "recognize",
            path=image_path,
            image_base64=image_base64,
            reference=reference,
            expect_country=expect_country,
        )


class ScanIdInput(BaseModel):
    """Arguments of the tools that act on one stored scan."""

    scan_id: str = Field(min_length=1, description="The id of a scan, as returned by a scan.")


class DocCheapGetScan(_DocCheapTool):
    """Returns a stored scan result."""

    name: str = "doc_cheap_get_scan"
    description: str = (
        "Returns a stored doc.cheap scan result by its id, as JSON. Results are "
        "stored only for live keys with a retention window. Costs nothing."
    )
    args_schema: type[BaseModel] = ScanIdInput

    def _run(self, scan_id: str, run_manager: CallbackManagerForToolRun | None = None) -> str:
        return self._call("get_scan", scan_id=scan_id)


class ListScansInput(BaseModel):
    """Arguments of :class:`DocCheapListScans`."""

    limit: int | None = Field(
        default=None, ge=1, le=100, description="How many results to return, 1 to 100."
    )
    cursor: str | None = Field(
        default=None,
        max_length=256,
        description="The next_cursor value of the previous page, for the next page.",
    )


class DocCheapListScans(_DocCheapTool):
    """Lists stored scan results, newest first."""

    name: str = "doc_cheap_list_scans"
    description: str = (
        "Lists stored doc.cheap scan results, newest first, as JSON with a "
        "next_cursor for the next page. Costs nothing."
    )
    args_schema: type[BaseModel] = ListScansInput

    def _run(
        self,
        limit: int | None = None,
        cursor: str | None = None,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        return self._call("list_scans", limit=limit, cursor=cursor)


class DocCheapDeleteScan(_DocCheapTool):
    """Deletes a stored scan result."""

    name: str = "doc_cheap_delete_scan"
    description: str = (
        "Deletes a stored doc.cheap scan result by its id. It cannot be undone. Costs nothing."
    )
    args_schema: type[BaseModel] = ScanIdInput

    def _run(self, scan_id: str, run_manager: CallbackManagerForToolRun | None = None) -> str:
        return self._call("delete_scan", scan_id=scan_id)


class UsageInput(BaseModel):
    """The usage tool takes no arguments."""


class DocCheapGetUsage(_DocCheapTool):
    """Returns the account's credits and scan counters."""

    name: str = "doc_cheap_get_usage"
    description: str = (
        "Returns this month's free doc.cheap credits, the paid credits, the "
        "credits spent and the scan counters, as JSON. Costs nothing."
    )
    args_schema: type[BaseModel] = UsageInput

    def _run(self, run_manager: CallbackManagerForToolRun | None = None) -> str:
        return self._call("usage")
