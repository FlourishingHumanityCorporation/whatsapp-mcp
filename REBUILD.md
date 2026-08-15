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

This may connect to the user's personal WhatsApp account, require QR pairing, write to `whatsapp-bridge/store/`, and start the bridge REST API. Do not run it as part of appcheck, pre-commit, or routine repository cleanup.

## Bridge REST Port

The bridge REST API defaults to port 8080, which this repository does **not** own
in the workspace port registry (`.meta/PORTS.md` allocates only 9106, for the MCP
HTTP service). On this machine 8080 is held by ProjectPulse's backend, so the
bridge must be pointed elsewhere. Both sides read it from the environment and
must agree:

```bash
# bridge
WHATSAPP_BRIDGE_PORT=9114 go run main.go

# MCP server (whatsapp-mcp-server, incl. the com.paulrohde.mcp.whatsapp LaunchAgent)
WHATSAPP_BRIDGE_URL=http://localhost:9114/api
```

The bridge refuses to start when something already answers on its port, and
reports the conflict before any WhatsApp pairing. It checks by connecting rather
than by test-binding: on macOS a bind cannot detect this. A bare `:8080` takes
the IPv6 wildcard, which does not collide with an IPv4-only listener, and BSD
`SO_REUSEADDR` allows `127.0.0.1:8080` beside a bound `0.0.0.0:8080` — both
observed on 2026-08-15. The API binds loopback only, so it is not exposed to the
LAN.
