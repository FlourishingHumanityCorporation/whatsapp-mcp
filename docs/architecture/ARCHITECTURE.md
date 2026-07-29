---
created: 2026-07-23
last_updated: 2026-07-23
---
# Architecture: whatsapp-mcp

**Status:** STD-028 candidate

whatsapp-mcp joins a Go WhatsApp bridge to a Python MCP delivery surface. It
owns versioned source and service declarations; it does not own the operator's
WhatsApp account, authenticated device session, local message stores, media,
or currently running processes.

The machine-readable ownership and dependency contract in
[`appcheck.toml`](../../appcheck.toml) is normative.

## Dependency direction

```mermaid
flowchart LR
    audio["Audio conversion"] --> access["Local access and bridge client"]
    access --> delivery["MCP delivery"]
    delivery -. persisted invocation .-> service["Service control"]
    bridge["Go bridge runtime"]
```

The Python delivery root depends inward on local access functions, which
depend on audio conversion. The Go bridge is a separately built runtime
component. Service declarations invoke the Python delivery root but contain
no product behavior.

## Physical layout

```text
whatsapp-bridge/
├── main.go                  # Go bridge composition root
├── go.mod
└── go.sum

whatsapp-mcp-server/
├── main.py                  # FastMCP composition root
├── whatsapp.py              # local store and bridge access
├── audio.py                 # ffmpeg conversion boundary
├── pyproject.toml
└── uv.lock

infra/launchd/               # persisted service declaration
tests/architecture/          # non-live contract tests
docs/architecture/           # ownership and adoption evidence
```

The two runtime roots remain separate because they have different languages,
processes, and responsibilities. The three Python files are established
capabilities, not an undifferentiated script pile; creating one-file folders
would add navigation without clearer ownership.

## Named owner map

The human names below match the exact machine-owner names in
`appcheck.toml`:

| Machine owner | Responsibility |
|---|---|
| `bridge_runtime` | Go bridge composition and runtime behavior |
| `bridge_build` | Go module and dependency lock |
| `server_audio` | Audio conversion boundary |
| `server_access` | Local store access and bridge client |
| `server_delivery` | FastMCP registration and transport selection |
| `server_build` | Nested Python environment and dependency lock |
| `test_consumers` | Non-live architecture and behavior regressions |
| `service_control` | Persisted LaunchAgent and automation declaration |
| `project_knowledge` | Architecture and adoption documentation |
| `agent_control` | Repository-local coding-agent placement rules |
| `build_control` | Root metadata, baseline, hook, and native gate |

## Live and private-data boundary

Routine architecture proof must not start the Go bridge or Python MCP server,
connect or reconnect WhatsApp, display a QR code, inspect the message stores,
send messages or media, download media, or read private runtime logs.

The protected primary paths include:

- `whatsapp-bridge/store/`;
- the built `whatsapp-bridge/whatsapp-bridge` binary;
- local virtual environments and caches; and
- all live service processes and authenticated session state.

`make check` is deliberately non-live: it compiles Python source without
importing it, compiles the Go package through `go test`, runs the pure
architecture contract tests, and invokes checkout-local Appcheck. Green
source checks are not live WhatsApp acceptance.

## Ratcheted debt

The pre-adoption Go composition root is 1,351 lines and the Python MCP
composition root is 247 lines. The architecture baseline may contain only
their exact non-growing composition-size keys.

Remove the Go key by extracting storage, event handling, HTTP delivery, media,
and WhatsApp client coordination behind explicit packages while retaining one
thin `main`. Remove the Python key by moving tool implementations and runtime
selection behind a thin FastMCP registration root. These extractions require
focused non-live behavior tests before moves and separate authorized live
acceptance afterward.

Do not add invalid-configuration, flat-root, ownership, dependency, or cycle
exceptions. Do not treat a live service as permission to defer enforcement.

## Enforcement

`make architecture-check` runs checkout-local Appcheck. `make check` includes
the focused contract test and the architecture ratchet alongside the existing
Python and Go compilation checks.

When a boundary changes, update this document and `appcheck.toml`, add a
failing non-live test first, and run the focused architecture, native,
generated-hook, and package/build proof appropriate to the changed component.
