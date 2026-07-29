---
created: 2026-07-23
last_updated: 2026-07-28
candidate_revision: 83a7a5184a59fe2fc14c84035fde089e769edefa
status: APPROVED
---
# STD-028 contract review — whatsapp-mcp

## Decision

**APPROVED — independent evidence-only review found no blocking architecture
contract defect at exact record-bound revision `83a7a51`.**

The source and contract were first approved at corrective revision
`b40403ae45cfc401619e477479e0a9989c602c69`. Final rebind approved
`83a7a5184a59fe2fc14c84035fde089e769edefa`, whose only delta is the
architecture approval line and durable adoption records.

## Approved contract

- Twenty named owners govern the Go bridge, Python MCP surface, tests, build,
  service control, project knowledge, and agent controls.
- Twenty-two allowed edges form an acyclic graph.
- The Go composition root calls only `bridge.Run`; connection lifecycle
  dispatches to history, messaging, REST, and store capabilities without a
  return dependency.
- History ingestion and message handling both depend inward on independent
  chat-name resolution; naming depends only on the store.
- Store APIs exclusively own SQL and the database handle.
- `whatsapp-bridge/main.go` and `whatsapp-mcp-server/main.py` are the only
  composition roots.
- The architecture baseline is empty.
- Same-package Go calls are checked against `may_depend_on`, the declared graph
  is checked for cycles, and all Go capability owners are capped at 500 lines.

## Review history

Independent review rejected exact revision `55d6bf4` because the real Go graph
contained a hidden messaging-to-session edge and cycles, raw SQL lived outside
the store owner, lifecycle/history/naming were still mixed, and no check
verified same-package calls.

Corrective revision `b40403a` resolved every blocking finding. The reviewer
manually reconstructed the actual call graph from the supplied complete Go
surface, matched each observed dependency to `appcheck.toml`, confirmed a
topological ordering, confirmed SQL confinement, and confirmed that
`requestHistorySync` was removed.

## Evidence boundary

- `make check` passed Go tests, eight architecture contract tests, and the
  checkout-local Appcheck gate.
- Static Appcheck passed 37 checks, skipped 28 non-applicable checks, warned
  only on the known standard-library unittest marker, and failed none.
- Both generated hook stages and the candidate-bound generator check passed.

This approval covers source architecture and non-live characterization. It does
not cover WhatsApp connectivity, authenticated sessions, local stores, QR
interaction, message/media mutation, LaunchAgent behavior, or operator
acceptance.
