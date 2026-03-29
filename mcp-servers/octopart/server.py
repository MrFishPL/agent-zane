"""Octopart/Nexar MCP server entry point."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load .env from the server directory
load_dotenv(Path(__file__).parent / ".env")

from client import NexarClient
from tools import register_tools

mcp = FastMCP(
    "octopart",
    instructions=(
        "Octopart/Nexar component search server. Provides pricing, stock, and specs "
        "from 70M+ electronic parts across DigiKey, Mouser, LCSC, Farnell, and more. "
        "WARNING: Evaluation tier has 100 matched parts LIFETIME. Use get_quota_status() "
        "to check remaining quota before running queries."
    ),
)

client_id = os.environ.get("NEXAR_CLIENT_ID", "")
client_secret = os.environ.get("NEXAR_CLIENT_SECRET", "")

if not client_id or not client_secret:
    print(
        "[NEXAR] ERROR: NEXAR_CLIENT_ID and NEXAR_CLIENT_SECRET not set. "
        "Tools will fail. See README.md for setup.",
        file=sys.stderr,
    )

client = NexarClient(client_id, client_secret) if (client_id and client_secret) else None


def _get_client() -> NexarClient:
    if client is None:
        raise RuntimeError(
            "Nexar client not initialized. Set NEXAR_CLIENT_ID and "
            "NEXAR_CLIENT_SECRET environment variables."
        )
    return client


register_tools(mcp, _get_client())

if __name__ == "__main__":
    print(f"[NEXAR] Starting Octopart MCP server...", file=sys.stderr)
    if client:
        print(
            f"[NEXAR] Quota: {client.parts_consumed}/100 parts consumed, "
            f"{client.parts_remaining} remaining",
            file=sys.stderr,
        )
    mcp.run()
