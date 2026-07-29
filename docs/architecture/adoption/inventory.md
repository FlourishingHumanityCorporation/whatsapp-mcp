---
created: 2026-07-23
last_updated: 2026-07-28
standard: STD-028 v1.37
---
# whatsapp-mcp STD-028 adoption inventory

Status: `IN_REVIEW` at exact implementation revision
`517578954a257e27d711d228d32401c85f124d8b`.

## Identity

- Registry key and project path: `whatsapp-mcp` at `tools/whatsapp-mcp`.
- Candidate base and original `origin/main`:
  `5f6597f951a12c14025e4f46d53ff19224ed60e5`.
- Exact implementation tree:
  `92f07e99468ec24981dda318eb08bd5908a2f0a9`.
- Classification: substantial hybrid operator service.
- Canonical branch: `main`.
- The implementation revision is three commits ahead of its exact base and has
  no upstream divergence.

## Pre-adoption surface

- One 1,351-line Go bridge composition root.
- Three direct Python runtime files: a 247-line FastMCP root, a 767-line local
  access module, and a 110-line audio conversion module.
- One persisted LaunchAgent invoking non-executable `main.py` through an
  explicit interpreter and working directory.
- One Go module and one nested Python source-launched project/lock.
- No repository tests and no architecture enforcement.

The pre-adoption native gate compiled Python source and the Go package without
starting either runtime. The first architecture contract failed as expected
because the project was unadopted.

## Adopted architecture

- Eleven named owners govern all 33 scanned project entries.
- Seven allowed first-party edges form an acyclic graph.
- `whatsapp-bridge/main.go` and `whatsapp-mcp-server/main.py` are the only
  composition roots.
- The Go root is seven lines and delegates to the importable `bridge/` runtime
  package. This preserves both `go run main.go` and package compilation.
- The Python root is 19 lines and imports the existing FastMCP registration from
  `tools.py`.
- The interpreter-invoked Python path remains non-executable and is not
  misdeclared as a standalone entry point.
- The direct Python root cap is eight: four explicitly owned source
  capabilities and four build/control files.
- `.appcheck/architecture-baseline.json` is empty. No invalid configuration,
  flat-root, ownership, dependency, cycle, composition-size, or other
  architecture debt is baselined.
- `make check` includes four focused contract tests and checkout-local
  architecture enforcement.
- Generated pre-commit and pre-push configuration includes the registered
  architecture gate.
- Repository agent guidance names the ownership document, exact architecture
  command, placement rules, and private/live boundary.

## Compatibility and safety

The documented Go and Python launch paths, MCP tool names, environment
variables, Go module identity, Python project identity, LaunchAgent source, and
network defaults remain unchanged.

No bridge, MCP server, LaunchAgent, browser, consumer, or provider process was
launched, restarted, signalled, or exercised. Proof did not connect WhatsApp,
display or scan a QR code, inspect message/session stores, read private logs,
send messages or media, download media, or call the bridge REST API.

Green source and architecture evidence is not live WhatsApp acceptance.

## Exact-revision proof

- `make check`: Python syntax compilation, both Go packages, test policy, four
  architecture contract tests, and architecture enforcement passed.
- Architecture run `fc524b23-6a6c-4200-a2dc-0de753b0559f`: 33 files scanned,
  33 governed, zero outside governance, zero baseline entries, and no new,
  grown, stale, or historical regression.
- Static Appcheck: 36 passes, 29 non-applicable skips, one known standard-
  library unittest marker warning, and no failure.
- `pre-commit run --all-files`: every generated pre-commit hook passed.
- `pre-commit run --hook-stage pre-push --all-files`: every generated pre-push
  hook passed.
- Central hook generator equivalence passed at generator candidate revision
  `337fddbd6b58aa7beb1efbf4a19baa5841bd33ca`.
- The installed pre-commit dispatcher is present. The installed pre-push
  composite resolves through control-plane revision
  `812fdd7951c0b18c2070c939d6bfe83c829928b1`.

## Review and promotion

The implementation-owner contract and quality assessments are complete for the
exact implementation revision. Independent approval is pending, so the rollout
ledger must remain `IN_REVIEW` rather than `CONFORMANT`.

Live WhatsApp acceptance is deliberately excluded from this architecture
rollout and would require separate, exact authorization.
