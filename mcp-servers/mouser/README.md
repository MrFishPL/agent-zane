# Mouser MCP Server

MCP server for searching electronic components via the Mouser Search API. Provides pricing, stock, and specifications from Mouser's catalog.

## Getting API Credentials

1. Go to [mouser.com/api-hub](https://www.mouser.com/api-hub/) and create an account
2. Register for the Search API and get your API key
3. Mouser issues separate keys for Search and Cart/Order — you need the **Search API key**

## Setup

```bash
cd mcp-servers/mouser/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in this directory:
```
MOUSER_API_KEY=your-api-key-here
```

## Tools

| Tool | Description |
|------|-------------|
| `search_parts(query)` | Keyword search (e.g. "100uF capacitor", "STM32F4") |
| `search_mpn(mpn)` | MPN lookup, supports exact/begins-with/contains |
| `get_part_details(mpn)` | Full details for one exact MPN |
| `search_manufacturer(keyword, manufacturer)` | Keyword search filtered by manufacturer |
| `get_rate_limit_status()` | Check remaining daily API requests |

## Rate Limits

- **30 requests per minute**
- **1,000 requests per day**

The server tracks daily usage in `.request_counter.json` and enforces both limits.

## Running

```bash
source venv/bin/activate
python server.py
```

Or via MCP config (registered in `.mcp.json`):
```json
{
  "mcpServers": {
    "mouser": {
      "command": "mcp-servers/mouser/venv/bin/python",
      "args": ["mcp-servers/mouser/server.py"],
      "cwd": "mcp-servers/mouser"
    }
  }
}
```

## Testing

```bash
source venv/bin/activate

# Unit + integration tests (no API calls)
python -m pytest tests/test_client.py tests/test_tools.py -v

# Live smoke test (uses real API key)
python -m pytest tests/test_live.py -v
```

## API Details

- **Base URL**: `https://api.mouser.com/api/v1` (V1), `https://api.mouser.com/api/v2` (V2)
- **Auth**: API key as query parameter (`?apiKey=...`)
- **Format**: JSON POST requests
- **Rate limits**: 30/min, 1000/day

## Response Quirks

- `Availability` is a string like `"1234 In Stock"` — parsed to integer
- `Price` is a string like `"$0.85"` — parsed to float
- `LifeCycle` field is often empty — do not rely on it exclusively
- `ProductAttributes` is limited — typically only packaging/pack qty, not full parametrics
- Max 50 results per keyword search; max 10 MPNs per part number search
