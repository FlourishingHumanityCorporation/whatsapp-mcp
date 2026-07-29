"""WhatsApp MCP transport composition root."""

import os

from tools import mcp


def main() -> None:
    """Run the configured MCP transport."""
    if os.environ.get("WHATSAPP_MCP_TRANSPORT") == "streamable-http":
        mcp.settings.host = os.environ.get("WHATSAPP_MCP_HOST", "127.0.0.1")
        mcp.settings.port = int(os.environ.get("WHATSAPP_MCP_PORT", "9106"))
        mcp.run(transport="streamable-http")
        return
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
