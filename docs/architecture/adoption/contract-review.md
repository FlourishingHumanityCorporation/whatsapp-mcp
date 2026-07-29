---
created: 2026-07-23
last_updated: 2026-07-28
candidate_revision: 517578954a257e27d711d228d32401c85f124d8b
status: PENDING_INDEPENDENT_REVIEW
---
# STD-028 contract review — whatsapp-mcp

## Decision

**PENDING — no independent reviewer has approved this candidate.**

This implementation-owner self-audit is review input, not independent
approval.

## Scope

- Exact implementation revision:
  `517578954a257e27d711d228d32401c85f124d8b`.
- Architecture scope and Git root: `tools/whatsapp-mcp`.
- Live bridge or MCP execution, WhatsApp connectivity, message/session stores,
  QR interaction, media, private logs, and service restarts are excluded.

## Owner self-audit

- Eleven named owners govern all 33 scanned project entries with no overlap or
  gap.
- The Go root is a seven-line composition root over the importable `bridge/`
  runtime package; the documented `go run main.go` command remains valid.
- The Python root is a 19-line transport selector over the existing tool
  registration in `tools.py`.
- The seven declared dependency edges are explicit and acyclic.
- The two composition roots remain the established Go and Python executable
  paths, and the interpreter-invoked Python root remains non-executable.
- The architecture baseline is empty and baseline-history verification passes.
- The intentional Python root cap is eight: four owned source capabilities and
  four build/control files.
- Checkout-local native and generated-hook gates do not start either runtime or
  inspect private state.

## Required reviewer checks

1. Confirm the eleven owners represent real reasons to change.
2. Confirm all seven allowed edges are necessary and no valid edge is omitted.
3. Confirm the Go package extraction preserves its public launch seam.
4. Confirm the Python tool extraction preserves tool registration and transport
   selection.
5. Confirm the empty baseline hides no root, size, composition, cycle,
   ownership, or documentation debt.
6. Confirm the eight-file Python root cap is a truthful boundary rather than an
   exception disguised as configuration.

## Current evidence

- `make check` passes Python compilation, both Go packages, test policy, four
  architecture contract tests, and checkout-local architecture enforcement.
- Static Appcheck has 36 passes, 29 non-applicable skips, one known unittest
  marker warning, and no failure.
- The complete generated pre-commit and pre-push suites pass.
- Central generator equivalence passes.

The rollout ledger must remain `IN_REVIEW`.
