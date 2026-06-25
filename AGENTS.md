# whatsapp-mcp

Codex guidance for this repository.

## What This Is

Repository in the CodeProjects workspace.

## Workspace Context

- Workspace path: `tools/whatsapp-mcp`
- Repository name: `whatsapp-mcp`
- Kind: developer/operator tool
- Registry entry: `whatsapp-mcp` in `.meta/projects.json`.

## Tech Stack Signals

- Go bridge in `whatsapp-bridge/`
- Python MCP server in `whatsapp-mcp-server/`
- Local SQLite message/session data under `whatsapp-bridge/store/`

## Start Here

- Read `/Users/paulrohde/CodeProjects/AGENTS.md` before making cross-project changes.
- Keep changes scoped to this repo unless the user asks for a workspace-wide change.
- Check `.meta/projects.json` before changing ports, dependency relationships, project names, or automation ownership.
- Prefer existing local conventions, scripts, and docs over new machinery.
- Never print secrets from `.env`, local credentials, browser profiles, keychains, or private data stores.

## Local Orientation

- `README.md` is the first local product/usage orientation surface.
- `SYMBOLS.md` is available for code navigation; regenerate only when local conventions require it.
- The Go bridge connects to the user's personal WhatsApp account, stores local message history, and exposes a live REST API on port 8080 when started.
- The Python MCP server exposes read/search/send/download tools over that bridge and local SQLite store.

## Safety Boundary

- Routine validation must be non-live. Do not start `go run main.go`, `uv run main.py`, the MCP server, or the bridge REST API unless the user explicitly approves a live WhatsApp session.
- Do not scan a QR code, reconnect the WhatsApp device, read or print message-store contents, send messages/files/audio, download media, or inspect `whatsapp-bridge/store/` data without explicit user approval for that exact action.
- Treat `whatsapp-bridge/store/`, local database files, logs, media downloads, and generated bridge binaries as private/generated operator artifacts.
- The bridge default REST port is 8080, which is not registered as an owned CodeProjects port because it is an opt-in live service and conflicts with existing workspace port ownership.

## Commands

- `make check` - Run non-live Python syntax compilation and Go package compilation. This must not start the bridge, start the MCP server, connect to WhatsApp, read message data, or send/download media.
- `cd whatsapp-bridge && go test ./...` - Compile the Go bridge package without invoking `main`.
- `python3 -c 'from pathlib import Path; [compile(p.read_text(), str(p), "exec") for p in sorted(Path("whatsapp-mcp-server").glob("*.py"))]'` - Compile Python source without importing or starting the MCP server.

## Important Files

- `README.md`
- `SYMBOLS.md`
- `SYMBOLS-full.md`
- `Makefile`
- `appcheck.toml`
- `whatsapp-bridge/main.go`
- `whatsapp-mcp-server/main.py`
- `whatsapp-mcp-server/whatsapp.py`

## Verification

- Run the narrowest relevant local check after edits.
- For user-visible behavior, prefer the real UI, CLI, appcheck, logs, or documented proof surface over a shallow green check.
- If verification cannot run, report the exact blocker and residual risk.
