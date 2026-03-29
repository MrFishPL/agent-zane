# Octopart/Nexar MCP Server

MCP server for searching electronic components via the Nexar API (formerly Octopart). Provides pricing, stock, and specifications from 70M+ parts across DigiKey, Mouser, LCSC, Farnell, and other distributors in a single query.

## Getting API Credentials

1. Go to [nexar.com](https://nexar.com/api) and create a free account
2. In the [Nexar Portal](https://portal.nexar.com), create a new application
3. Note the **Client ID** and **Client Secret** from the app settings
4. The free Evaluation tier provides **100 matched parts lifetime** — use sparingly

## Setup

```bash
cd mcp-servers/octopart/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in this directory:
```
NEXAR_CLIENT_ID=your-client-id-here
NEXAR_CLIENT_SECRET=your-client-secret-here
```

## Tools

| Tool | Description | Quota Cost |
|------|-------------|------------|
| `search_parts(query)` | General search by description (e.g. "3 ohm resistor 0603") | N parts |
| `search_mpn(mpn)` | Search by MPN, supports partial match | N parts |
| `get_part_details(mpn)` | Full details for one MPN (limit=1) | 1 part |
| `multi_match(mpns)` | Batch lookup of multiple MPNs | N parts |
| `check_lifecycle(mpn)` | Returns active/nrnd/obsolete/unknown | 1 part |
| `get_quota_status()` | Check remaining quota | 0 parts |

All search tools accept optional `currency` (default "USD") and `country` (default "US") parameters.

## Quota Tracking

The Evaluation tier has a **100 matched parts lifetime limit**. The server tracks consumption in `.parts_counter.json` and logs to stderr on every query with warnings at 50%, 75%, and 95% usage.

Use `get_quota_status()` to check remaining quota without consuming any parts.

## Running

```bash
source venv/bin/activate
python server.py
```

Or via MCP config (registered in `.claude/settings.json`):
```json
{
  "mcpServers": {
    "octopart": {
      "command": "mcp-servers/octopart/venv/bin/python",
      "args": ["mcp-servers/octopart/server.py"],
      "cwd": "mcp-servers/octopart"
    }
  }
}
```

## Testing

```bash
source venv/bin/activate

# Unit + integration tests (no API calls, no quota cost)
python -m pytest tests/test_client.py tests/test_tools.py -v

# Live smoke test (costs ~1 matched part)
python -m pytest tests/test_live.py -v
```

## API Details

- **Endpoint**: `https://api.nexar.com/graphql/` (GraphQL)
- **Auth**: OAuth2 Client Credentials → `https://identity.nexar.com/connect/token`
- **Token lifetime**: 24 hours
- **Scope**: `supply.domain`
- **Timeout**: 90 seconds
- **Rate limits (tokens)**: 2/sec, 200/15min, 3000/12hr, 40000/week
