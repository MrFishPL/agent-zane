# MCP Server Development Standards

## Directory Structure

Each MCP server lives in its own directory under `mcp-servers/`:

```
mcp-servers/
├── digikey/
│   ├── venv/                  # Isolated Python virtual environment
│   ├── requirements.txt       # Pinned dependencies
│   ├── server.py              # MCP server entry point
│   ├── client.py              # API client (auth, requests, response parsing)
│   ├── tools.py               # Tool definitions exposed via MCP
│   ├── schemas.py             # Response validation schemas
│   ├── tests/
│   │   ├── test_client.py     # Unit tests for API client
│   │   ├── test_tools.py      # Integration tests for MCP tools
│   │   └── test_live.py       # Live API smoke tests (requires credentials)
│   └── README.md              # API notes: auth method, rate limits, gotchas
├── mouser/
│   └── ...
├── lcsc/
│   └── ...
├── octopart/
│   └── ...
└── snapmagic/
    └── ...
```

## Server Implementation

### Entry Point (`server.py`)
- Uses the MCP Python SDK (`mcp` package)
- Registers all tools from `tools.py`
- Handles graceful startup and shutdown
- Logs errors to stderr, never to stdout (stdout is the MCP transport)

### API Client (`client.py`)
- Handles authentication (API keys from environment variables, never hardcoded)
- Manages rate limiting (respect distributor limits, implement backoff)
- Parses responses into validated Python objects
- Handles common errors: auth failure, rate limit hit, timeout, malformed response

### Tools (`tools.py`)
Each distributor server should expose at minimum:
- `search_parts(query, filters)` — parametric search by keyword, category, specs
- `get_part_details(mpn)` — full details for a specific MPN
- `get_stock(mpn)` — current stock level and lead time
- `get_pricing(mpn, quantities)` — price breaks at specified quantities

SnapMagic server exposes:
- `check_model_availability(mpn)` — symbol, footprint, 3D model status
- `get_model_links(mpn)` — download/page links for available models

### Response Validation (`schemas.py`)
- Define expected response shapes (dataclass or Pydantic)
- Validate every API response before returning to the agent
- If response doesn't match schema, return a structured error — never pass through garbage data

## Virtual Environment

Each server gets its own venv. No shared environments.

```bash
cd mcp-servers/digikey/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Common Dependencies
- `mcp` — MCP Python SDK
- `httpx` — async HTTP client (preferred over requests)
- `pydantic` — response validation (optional but recommended)

Pin all dependency versions in `requirements.txt`.

## Environment Variables

API credentials are stored in `.env` files (gitignored) and loaded by the server:
- `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET`
- `MOUSER_API_KEY`
- `LCSC_API_KEY`
- `OCTOPART_API_KEY`
- `SNAPMAGIC_API_KEY`

Never hardcode credentials. If credentials are missing, the server should start but return clear error messages when tools are called.

## Testing Requirements

### Three test levels (all required before declaring a server "working"):

**1. Unit tests (`test_client.py`)**
- Test response parsing with recorded fixtures (saved JSON responses)
- Test error handling: auth failure, rate limit, timeout, empty results, malformed JSON
- Run without API credentials — uses fixtures only

**2. Integration tests (`test_tools.py`)**
- Test each MCP tool end-to-end with mocked HTTP responses
- Verify tool output matches expected schema
- Test edge cases: query with zero results, special characters in search, very long part numbers

**3. Live smoke tests (`test_live.py`)**
- Require real API credentials (skip gracefully if missing)
- Run a small set of known queries and verify results make sense
- Check a known MPN returns expected manufacturer and category
- These are re-run periodically to catch API changes or token expiration

### Test Script
Each server must have a runnable test script:
```bash
cd mcp-servers/digikey/
source venv/bin/activate
python -m pytest tests/ -v
```

## Registration

After building and testing, register the server in `.claude/settings.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "digikey": {
      "command": "mcp-servers/digikey/venv/bin/python",
      "args": ["mcp-servers/digikey/server.py"],
      "env": {
        "DIGIKEY_CLIENT_ID": "${DIGIKEY_CLIENT_ID}",
        "DIGIKEY_CLIENT_SECRET": "${DIGIKEY_CLIENT_SECRET}"
      }
    }
  }
}
```

## Quality Gates

An MCP server is NOT ready for use until:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] At least one live smoke test passes with real credentials
- [ ] The server starts without errors
- [ ] A known MPN query returns correct, verified data
- [ ] Rate limiting is implemented and tested
- [ ] Auth failure produces a clear error message, not a crash
