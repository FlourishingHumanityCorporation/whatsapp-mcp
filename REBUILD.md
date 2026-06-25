# whatsapp-mcp Rebuild Log

## Purpose

`whatsapp-mcp` contains a Go WhatsApp bridge and a Python MCP server for local WhatsApp search, read, send, and media workflows.

## Non-Live Validation

Run routine CodeProjects validation from the repository root:

```bash
make check
```

This check compiles Python source and the Go package only. It does not start the bridge, start the MCP server, connect to WhatsApp, read the local message store, send messages, or download media.

## Live Setup Boundary

Live setup is opt-in only:

```bash
cd whatsapp-bridge
go run main.go
```

This may connect to the user's personal WhatsApp account, require QR pairing, write to `whatsapp-bridge/store/`, and start the bridge REST API on port 8080. Do not run it as part of appcheck, pre-commit, or routine repository cleanup.
