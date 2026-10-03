# langchain-doccheap

[![PyPI](https://img.shields.io/pypi/v/langchain-doccheap.svg)](https://pypi.org/project/langchain-doccheap/)

[LangChain](https://python.langchain.com/) tools for
[doc.cheap](https://doc.cheap): an agent gives them a photo or scan of a
passport, national ID card or driving licence and gets back the printed fields –
name, date of birth, document number, expiry, the machine-readable zone – as
JSON.

One recognised document costs one credit, $0.01. Registering gives 100 free
documents every month. An unreadable image, an empty frame or an unsupported
document type costs nothing, and every answer says whether it was billed.

The package needs Python 3.10 or later. It is built on the
[doc-cheap](https://pypi.org/project/doc-cheap/) client and `langchain-core` 1.x.

## Installation

```sh
pip install langchain-doccheap
```

## The tools

| Tool | Name the model sees | What it does |
| --- | --- | --- |
| `DocCheapScanDocument` | `doc_cheap_scan_document` | Reads one JPEG or PNG image, from `image_path` or `image_base64`, with an optional `reference` label and `expect_country` (ISO 3166-1 alpha-3). |
| `DocCheapGetScan` | `doc_cheap_get_scan` | Returns a stored result by `scan_id`. |
| `DocCheapListScans` | `doc_cheap_list_scans` | Returns one page of stored results (`limit`, `cursor`). |
| `DocCheapDeleteScan` | `doc_cheap_delete_scan` | Deletes a stored result by `scan_id`. |
| `DocCheapGetUsage` | `doc_cheap_get_usage` | Returns this month's free credits, the paid credits, the credits spent and the scan counters. |

Every tool returns the API's answer as a JSON string. An API error – an unknown
scan, a used-up rate limit, a wrong key – comes back to the model as a short
text such as `doc.cheap error: 404 scan_not_found: …` instead of stopping the
agent; pass `handle_tool_error=False` to have it raised as a `ToolException`.

## Quick start

```python
from langchain_doccheap import DocCheapScanDocument

scan = DocCheapScanDocument(api_key="sk_sandbox_public")
print(scan.invoke({"image_path": "passport.jpg"}))
```

With an agent, take all five tools from the toolkit. They share one client and
its connections:

```python
from langchain.agents import create_agent
from langchain_doccheap import DocCheapToolkit

tools = DocCheapToolkit().get_tools()  # reads DOC_CHEAP_API_KEY
agent = create_agent("openai:gpt-4.1-mini", tools)
agent.invoke({"messages": [{"role": "user", "content": "Read the passport in ./passport.jpg"}]})
```

`DocCheapToolkit(include_delete=False)` leaves out the tool that deletes stored
results.

## API keys

- **Live key** – `sk_live_…`, created in the
  [doc.cheap cabinet](https://doc.cheap/docs/concepts/api-keys-and-sessions).
- **Sandbox key** – `sk_sandbox_public` works without an account. It gives 10
  free recognised documents per address in all, and at most 10 requests per
  address an hour, whatever their answer.

Without `api_key` the tools read the key from the `DOC_CHEAP_API_KEY`
environment variable. `base_url` (or `DOC_CHEAP_API_BASE`) points them at
another address. To control timeouts, proxies or connection pooling, build a
`doc_cheap.Client` yourself and pass it as `client=`; the tools leave it open.

**Stored results.** A result is stored only when the scan was made with a live
key under a non-zero retention window. Under the sandbox key nothing is stored,
so getting or deleting a scan answers `scan_not_found`.

## Resources

- [doc.cheap documentation](https://doc.cheap/docs)
- [Your first recognition](https://doc.cheap/docs/start/first-recognition)
- [API reference](https://doc.cheap/docs/reference)
- [The doc-cheap Python client](https://pypi.org/project/doc-cheap/)

## License

[MIT](LICENSE)
