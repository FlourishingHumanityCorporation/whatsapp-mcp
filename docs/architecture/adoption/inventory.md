---
created: 2026-07-23
last_updated: 2026-07-23
---
# STD-028 adoption inventory

Status: candidate evidence, not publication or live WhatsApp acceptance.

## Identity

- Registry key: `whatsapp-mcp`
- Architecture scope and Git root: `tools/whatsapp-mcp`
- Candidate base: `3eeea999f76cea66472b939dfaa3ac2906ad4417`
- Candidate tree excluding adoption records:
  `c449bc6d828c8ce8d959c4eac67154a3bb58a18d`
- Candidate patch digest excluding adoption records:
  `d7fb80b7dcd501d81732ed55d8307aa1b80460653d8f52641c6ae40b4560d141`
- Classification: substantial hybrid operator service
- Canonical workspace upstream: `fhc/main`, exact at identity capture
- Primary checkout: preserved with its existing generated
  `.pre-commit-config.yaml` edit
- Existing live state: preserved without process signals, restarts, store
  access, QR interaction, or transport calls

The isolated candidate was created from the exact `fhc/main` revision. No
source, index, commit, branch, installed hook, live service, or private store
in the primary checkout was changed.

## Pre-adoption surface

- 22 tracked files
- One 1,351-line Go bridge composition root
- Three direct Python runtime files: a 247-line FastMCP root, a 767-line local
  access module, and a 110-line audio conversion module
- One persisted LaunchAgent invoking non-executable `main.py` through an
  explicit Python interpreter and working directory
- One Go module and one nested Python lock/project definition
- No repository tests
- Native gate: syntax-compile the three Python files without importing them,
  compile the Go package through `go test`, and run changed-file policy

The baseline native gate passed without starting either runtime. The focused
contract then failed as expected because architecture was not required and
the custom Appcheck command jumped to the protected primary checkout.

## Consumers and compatibility

No runtime source moved. The LaunchAgent path, working directory, Go module,
Python filenames, imports, FastMCP tool names, environment variables, and
network defaults are unchanged.

The declared capability direction is:

- `whatsapp-mcp-server/audio.py` owns audio conversion;
- `whatsapp-mcp-server/whatsapp.py` owns local store and bridge access and may
  depend on audio conversion;
- `whatsapp-mcp-server/main.py` owns FastMCP registration and runtime
  selection and may depend on local access;
- `whatsapp-bridge/main.go` owns the separately built Go bridge runtime; and
- `infra/launchd/` plus `automations.toml` own persisted service control.

The service project is source-launched and has no Python build backend or
console-script metadata. Its correct non-live build proof is Python syntax
compilation, `uv lock --check`, Go package compilation, and LaunchAgent plist
validation rather than inventing a wheel contract.

## Candidate architecture

- Every source, build, test, service-control, documentation, agent-control,
  and exact root resource has one declared owner.
- `whatsapp-bridge/main.go` and `whatsapp-mcp-server/main.py` are the only
  composition roots.
- The persisted interpreter-invoked Python path remains non-executable and is
  not misdeclared as a standalone entry point.
- The seven-file source-root ceiling prevents new flat growth without
  multiplying the established three-file Python surface into one-file
  folders.
- The declared first-party dependency graph is acyclic.
- The baseline contains exactly the pre-adoption 1,351-line Go and 247-line
  Python composition roots. It contains no invalid-configuration, flat-root,
  ownership, dependency, or cycle exemptions.
- `make check` now includes a pure four-test contract and checkout-local
  architecture ratchet.
- The central registry declares the architecture command.
- Agent guidance makes the private/live boundary and capability placement
  rules explicit.

## Proof

- Native candidate gate: Python syntax compile, Go package compile,
  changed-file policy, four contract tests, and architecture all pass.
- Full checkout-local Appcheck:
  `6753f487-8d58-475a-a689-4606630a7cf8`, zero failures.
- Full Appcheck has one non-blocking static marker warning because the pure
  standard-library `unittest` file does not use pytest markers; boundary and
  semantic classification still pass.
- `uv lock --check` resolves the existing 47-package lock under Python 3.11
  without changing it.
- `plutil -lint` accepts the canonical LaunchAgent plist.
- Generated `.pre-commit-config.yaml` is byte-for-byte equal to the current
  central generator output; its SHA-256 is
  `23b87bd7040161aef189e273a17c0fa8cf4404fbac3c04b2398afd54bb2e8101`.
- The architecture hook passes through pre-commit at both pre-commit and
  pre-push stages.

The first full Appcheck attempt exposed a proof-integration bug:
`unittest -v` writes successful progress to stderr, while the custom check
correctly fails on any stderr. A focused RED regression drove the narrow
`2>&1` routing on that test command; the succeeding full run has empty
stderr.

## Live and private-data boundary

No WhatsApp bridge, MCP server, LaunchAgent, browser, Figma, consumer
application, or provider process was launched, restarted, signalled, or
exercised.

Proof did not connect WhatsApp, display or scan a QR code, inspect message or
session database contents, read private logs, send messages or media,
download media, or call the bridge REST API. The protected primary processes
continued running throughout.

Green source and metadata evidence is not live WhatsApp acceptance.

## Promotion blockers

- Independent contract and quality reviews are pending.
- The Git root has no installed pre-commit hook.
- Its installed pre-push hook is the existing shared control-plane symlink
  and has not been exercised against this candidate.
- The primary generated-hook edit overlaps the candidate-generated file and
  must be reconciled deliberately.
- Live acceptance would require separate explicit authorization and cannot be
  inferred from these non-live checks.
- The candidate has no immutable tested commit. No commit or push was made.
