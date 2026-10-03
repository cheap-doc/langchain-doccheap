"""LangChain's own standard checks for a tool package."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from langchain_tests.unit_tests import ToolsUnitTests

from langchain_doccheap import (
    DocCheapDeleteScan,
    DocCheapGetScan,
    DocCheapGetUsage,
    DocCheapListScans,
    DocCheapScanDocument,
)

_ENV: tuple[dict[str, str], dict[str, Any], dict[str, Any]] = (
    {"DOC_CHEAP_API_KEY": "sk_env_key"},
    {},
    {"api_key": "sk_env_key"},
)


class _Base(ToolsUnitTests):
    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {"api_key": "sk_test_key"}

    @property
    def init_from_env_params(self) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
        return _ENV


class TestScanDocument(_Base):
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return DocCheapScanDocument

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"image_base64": "aGVsbG8=", "expect_country": "GBR"}


class TestGetScan(_Base):
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return DocCheapGetScan

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"scan_id": "scn_1"}


class TestListScans(_Base):
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return DocCheapListScans

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"limit": 10}


class TestDeleteScan(_Base):
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return DocCheapDeleteScan

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"scan_id": "scn_1"}


class TestGetUsage(_Base):
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return DocCheapGetUsage
