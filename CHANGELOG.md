# Changelog

## 0.1.1

- The README said nothing is stored under the sandbox key. In fact the public
  sandbox key `sk_sandbox_public` keeps a record of every scan for one year,
  with a reduced thumbnail and the address it came from, and cannot read it
  back; an account's own sandbox key stores nothing. The text now says so, and
  asks for test images only, never a real document.

## 0.1.0

First release: five LangChain tools for the doc.cheap API – scan a document,
get, list and delete stored results, and read the account's usage – and a
toolkit that returns them sharing one client.
