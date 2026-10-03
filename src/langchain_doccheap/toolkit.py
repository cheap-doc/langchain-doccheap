"""All doc.cheap tools behind one client."""

from __future__ import annotations

from doc_cheap import API_KEY_ENV, Client
from langchain_core.tools import BaseTool, BaseToolkit
from langchain_core.utils import secret_from_env
from pydantic import ConfigDict, Field, PrivateAttr, SecretStr

from .tools import (
    _USER_AGENT,
    DocCheapDeleteScan,
    DocCheapGetScan,
    DocCheapGetUsage,
    DocCheapListScans,
    DocCheapScanDocument,
)


class DocCheapToolkit(BaseToolkit):
    """The five doc.cheap tools, sharing one client and its connections.

    The API key is the ``api_key`` argument, else the ``DOC_CHEAP_API_KEY``
    environment variable. Pass ``include_delete=False`` to leave out the tool
    that deletes stored results.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    api_key: SecretStr | None = Field(default_factory=secret_from_env(API_KEY_ENV, default=None))
    base_url: str | None = None
    client: Client | None = Field(default=None, exclude=True)
    include_delete: bool = True

    _owned_client: Client | None = PrivateAttr(default=None)

    def _shared_client(self) -> Client:
        if self.client is not None:
            return self.client
        if self._owned_client is None:
            key = self.api_key.get_secret_value() if self.api_key is not None else None
            self._owned_client = Client(key, base_url=self.base_url, user_agent=_USER_AGENT)
        return self._owned_client

    def get_tools(self) -> list[BaseTool]:
        """Returns the tools, all sending their requests through one client."""
        client = self._shared_client()
        tools: list[BaseTool] = [
            DocCheapScanDocument(client=client),
            DocCheapGetScan(client=client),
            DocCheapListScans(client=client),
            DocCheapGetUsage(client=client),
        ]
        if self.include_delete:
            tools.append(DocCheapDeleteScan(client=client))
        return tools
