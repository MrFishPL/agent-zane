"""Mouser MCP server entry point."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load .env from the server directory
load_dotenv(Path(__file__).parent / ".env")

from client import MouserClient
from tools import register_tools

mcp = FastMCP(
    "mouser",
    instructions=(
        "Mouser electronic component search server. Provides pricing, stock, and specs "
        "via the Mouser Search API. Supports keyword search, MPN lookup, and "
        "manufacturer-filtered search. Rate limits: 30 req/min, 1000 req/day."
    ),
)

api_key = os.environ.get("MOUSER_API_KEY", "")

if not api_key:
    print(
        "[MOUSER] ERROR: MOUSER_API_KEY not set. "
        "Tools will fail. See README.md for setup.",
        file=sys.stderr,
    )

client = MouserClient(api_key) if api_key else None


def _get_client() -> MouserClient:
    if client is None:
        raise RuntimeError(
            "Mouser client not initialized. Set MOUSER_API_KEY environment variable."
        )
    return client


register_tools(mcp, _get_client())

if __name__ == "__main__":
    print("[MOUSER] Starting Mouser MCP server...", file=sys.stderr)
    if client:
        print(
            f"[MOUSER] Daily requests remaining: {client.daily_requests_remaining}/1000",
            file=sys.stderr,
        )
    mcp.run()
