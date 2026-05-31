# whatsapp-mcp

Codex guidance for this repository.

## What This Is

Repository in the CodeProjects workspace.

## Workspace Context

- Workspace path: `tools/whatsapp-mcp`
- Repository name: `whatsapp-mcp`
- Kind: developer/operator tool
- Registry entry: not listed in `.meta/projects.json`; treat local docs as authoritative.

## Tech Stack Signals

- Inspect local README and build files

## Start Here

- Read `/Users/paulrohde/CodeProjects/AGENTS.md` before making cross-project changes.
- Keep changes scoped to this repo unless the user asks for a workspace-wide change.
- Check `.meta/projects.json` before changing ports, dependency relationships, project names, or automation ownership.
- Prefer existing local conventions, scripts, and docs over new machinery.
- Never print secrets from `.env`, local credentials, browser profiles, keychains, or private data stores.

## Local Orientation

- `README.md` is the first local product/usage orientation surface.
- `SYMBOLS.md` is available for code navigation; regenerate only when local conventions require it.

## Commands

- No standard command was detected; inspect local docs and run the narrowest relevant verification.

## Important Files

- `README.md`
- `SYMBOLS.md`
- `SYMBOLS-full.md`

## Verification

- Run the narrowest relevant local check after edits.
- For user-visible behavior, prefer the real UI, CLI, appcheck, logs, or documented proof surface over a shallow green check.
- If verification cannot run, report the exact blocker and residual risk.
