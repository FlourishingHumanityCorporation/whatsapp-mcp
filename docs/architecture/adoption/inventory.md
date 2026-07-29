---
created: 2026-07-23
last_updated: 2026-07-28
standard: STD-028 v1.37
status: approved
---
# whatsapp-mcp STD-028 adoption inventory

Status: `CONFORMANT` at exact record-bound revision
`83a7a5184a59fe2fc14c84035fde089e769edefa`.

## Identity and classification

- Registry key and project path: `whatsapp-mcp` at `tools/whatsapp-mcp`.
- Frozen pre-adoption base:
  `5f6597f951a12c14025e4f46d53ff19224ed60e5`.
- Canonical branch and remote: `main` on `origin`.
- Classification: **SUBSTANTIAL** hybrid operator service.

The project owns a Go WhatsApp bridge, Python MCP delivery, local database and
audio access, persisted service control, two runtime composition roots, and
explicit private/live-data boundaries. It is not eligible for the small-project
exemption.

## Pre-adoption pain

- One 1,351-line Go file combined connection lifecycle, QR pairing, history
  ingestion, chat naming, SQLite persistence, message send/receive, REST
  delivery, media download, and Ogg/Opus analysis.
- A 247-line Python root combined FastMCP registration and transport selection.
- There were no repository tests or architecture enforcement.

The first corrective split compiled but was independently rejected because
message handling called naming logic in the session owner, creating an
undeclared cycle, and two non-store owners executed raw SQL.

## Approved architecture

- Twenty named owners and 22 allowed edges govern the full project graph.
- `whatsapp-bridge/main.go` and `whatsapp-mcp-server/main.py` are the only
  composition roots.
- The Go composition root depends only on connection lifecycle.
- Connection lifecycle, history ingestion, chat-name resolution, persistence,
  messaging, media, REST delivery, and audio analysis each have one file-level
  owner. No Go owner exceeds 500 lines.
- The declared Go graph is acyclic. A source-level symbol ratchet detects
  same-package calls that Appcheck's import analysis cannot observe and rejects
  undeclared edges or cycles.
- All SQLite statements and direct database-handle access are confined to
  `bridge_store`; non-store files call store methods.
- Non-live Go tests characterize URL path parsing, text extraction, invalid
  Ogg rejection, valid OpusHead/granule duration parsing, and deterministic
  bounded waveform generation.
- The Python root is 19 lines and imports the existing FastMCP registration
  from `tools.py`.
- `.appcheck/architecture-baseline.json` is empty.
- `make check`, generated pre-commit and pre-push hooks, and candidate-bound
  generator equivalence enforce the contract from the active checkout.

## Independent review history

The initial exact candidate `55d6bf4` was rejected for a real cycle, leaked SQL
ownership, mixed lifecycle/history/naming responsibility, and an enforcement
gap for same-package calls.

Corrective revision `b40403a` separated lifecycle, history, and naming; routed
all SQL through store APIs; deleted unreachable history-sync code; narrowed the
composition edge; added same-package dependency, cycle, and SQL-encapsulation
ratchets; and fixed an OpusHead offset bug exposed by new characterization.
Independent evidence-only review approved both the architecture contract and
implementation quality with no blocking findings.

Final evidence-only rebind approved exact record-bound revision
`83a7a5184a59fe2fc14c84035fde089e769edefa`. Its only delta from the approved
corrective implementation is the architecture approval status and durable
adoption records; no source, contract, test, hook, or baseline bytes changed.

Accepted residuals are recorded in the quality review. They include heuristic
limits in the symbol and SQL ratchets, pre-existing unused exported store
surface, duplicated filesystem-path knowledge, duplicated history text
extraction, and the absence of live WhatsApp proof. None creates an unowned
path, forbidden edge, cycle, or baseline exception.

## Current exact proof

- `make check`: Go packages, eight Python architecture contract tests, and
  checkout-local architecture enforcement passed.
- Static Appcheck: 37 checks passed, 28 non-applicable checks skipped, one
  known standard-library unittest marker warning, and no failure.
- Architecture: 42 scanned, 42 governed, zero outside governance, empty
  baseline, and no findings.
- Both generated hook stages passed.
- Candidate-bound generator equivalence and surface-complete adoption status
  passed at control candidate `3c9c188bf9d7074c70eb83839590bab48fe8abc1`.
- The installed composite pre-push hook passed the exact record-bound revision
  with its Tier 0 focused commit check.

## Safety boundary

No bridge, MCP server, LaunchAgent, browser, consumer, or provider process was
launched, restarted, signalled, or exercised. Proof did not connect WhatsApp,
display or scan a QR code, inspect message/session stores, read private logs,
send messages or media, download media, or call the bridge REST API.

Green source and architecture evidence is not live WhatsApp acceptance.
