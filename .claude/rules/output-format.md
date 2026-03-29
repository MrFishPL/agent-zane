# Output Format Rules

## Unified Response Envelope

Every response uses the same core structure:

```json
{
  "status": "recommendation | analysis | needs_clarification",
  "message": "Natural language explanation, reasoning, notes",
  "data": { ... }
}
```

### Fields

- `status` — always present. One of:
  - `"recommendation"` — sourcing results with components and BOM
  - `"analysis"` — schematic analysis, component identification, general answers
  - `"needs_clarification"` — questions the agent needs answered before proceeding
- `message` — always present. Plain text only — no markdown formatting (no **bold**, *italic*, `code`, or other markup). Use CAPS or dashes for emphasis if needed. The text commentary: reasoning, warnings, strategic advice, everything the engineer needs to understand the result. This replaces any natural language before/after the JSON block — all commentary goes inside `message`.
- `data` — present only when there's structured output to deliver. When there's nothing structured to return, omit `data` entirely.

### Optional Field Policy

Within a given response, every component must have the same set of fields. Optional fields are always included — use `null` for unavailable strings and `[]` for unavailable arrays. Never omit an optional field from some components while including it in others. This ensures every response is structurally identical for its status type.

## Examples

### Recommendation (sourcing results)

```json
{
  "status": "recommendation",
  "message": "Consolidated at Mouser. All parts active and in stock. Total BOM cost $12.50/unit at qty 200. Prices and stock are UNVERIFIED -- no MCP API servers are connected yet.",
  "data": {
    "components": [
      {
        "ref": "IC1",
        "mpn": "LM3900N/NOPB",
        "manufacturer": "Texas Instruments",
        "description": "Quad Norton op-amp, DIP-14",
        "package": "DIP-14",
        "qty_per_unit": 1,
        "qty_total": 200,
        "justification": "Matches schematic, lowest price option",
        "unit_price": 0.85,
        "price_break": {"qty": 200, "unit_price": 0.62},
        "stock": 4500,
        "lifecycle": "Active",
        "distributor": "DigiKey",
        "distributor_url": "URL not verified — search DigiKey for LM3900N/NOPB",
        "datasheet_url": "https://www.ti.com/lit/ds/symlink/lm3900.pdf",
        "snapmagic_url": null,
        "mpn_confidence": "searched",
        "mpn_source": "https://www.digikey.com/...",
        "verified": false,
        "warnings": [],
        "alternatives": [
          {
            "mpn": "LM324N",
            "manufacturer": "Texas Instruments",
            "unit_price": 0.45,
            "note": "Standard op-amp, not pin-compatible -- requires circuit changes"
          }
        ]
      }
    ],
    "bom_summary": {
      "unique_parts": 8,
      "total_components_per_unit": 24,
      "cost_per_unit": 12.50,
      "cost_total": 2500.00,
      "volume": 200,
      "currency": "USD"
    },
    "sources_queried": ["DigiKey", "Mouser", "LCSC"]
  }
}
```

### Analysis (schematic parsing, component identification)

```json
{
  "status": "analysis",
  "message": "Found 7 ICs across 3 pages. Pages 4-6 are legal text. Used crop-zoom at 600 DPI to resolve unreadable values on pages 1 and 3.",
  "data": {
    "pages": [
      {
        "page": 1,
        "title": "BlueNRG-LP Application Circuit",
        "components": [
          {"ref": "U1", "type": "BLE SoC", "value": "BlueNRG-LP", "package": "QFN-48"}
        ]
      }
    ],
    "summary": {
      "total_ics": 7,
      "total_passives": 42,
      "total_connectors": 8
    }
  }
}
```

### Clarification needed

```json
{
  "status": "needs_clarification",
  "message": "I can read the schematic but need a few answers before sourcing.",
  "data": {
    "questions": [
      {"id": 1, "question": "What supply voltage will be used?", "default": "12V", "reason": "Affects capacitor voltage rating selection"},
      {"id": 2, "question": "Output connector type?", "default": "6.35mm jack", "reason": "Need to source the correct connector"}
    ]
  }
}
```

### Simple answer (no structured data)

```json
{
  "status": "analysis",
  "message": "The LM3900 is a quad Norton op-amp. It's not pin-compatible with standard op-amps like LM324 — the inputs are current-mode, not voltage-mode."
}
```

## Clarification Question Fields (within `data.questions`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | integer | yes | Sequential question number (1, 2, 3...) |
| `question` | string | yes | The question to ask the user |
| `default` | string | yes | Suggested default answer, or `null` if no reasonable default |
| `reason` | string | yes | Why this information is needed for sourcing |

## Component Fields (within `data.components`)

| Field | Type | Required | Description |
|---|---|---|---|
| `ref` | string | yes | Reference designator (IC1, R1, C1, etc.) |
| `mpn` | string | yes | Manufacturer Part Number — never invented |
| `manufacturer` | string | yes | Component manufacturer |
| `description` | string | yes | Brief component description |
| `package` | string | yes | Package type (DIP-14, 0805, etc.) |
| `qty_per_unit` | integer | yes | Quantity needed per single board |
| `qty_total` | integer | yes | qty_per_unit × production volume |
| `justification` | string | yes | Why this part was selected |
| `unit_price` | number | yes | Price per unit at qty 1 (USD) |
| `price_break` | object | no | Best price break: `{qty, unit_price}` |
| `stock` | integer | yes | Current stock at distributor |
| `lifecycle` | string | yes | Active, NRND, or Obsolete |
| `distributor` | string | yes | Source distributor name |
| `distributor_url` | string | yes | Full clickable URL or "URL not verified — search [source] for [MPN]" |
| `datasheet_url` | string | yes | Full URL to datasheet, or `null` if not available |
| `snapmagic_url` | string | yes | Full URL, `"not available"`, or `null` if not checked |
| `mpn_confidence` | string | yes | One of: `"verified"`, `"searched"`, `"uncertain"`, `"fabricated"` |
| `mpn_source` | string | yes | URL or source where the MPN was found, or `null` if `mpn_confidence` is `"verified"` (API) |
| `verified` | boolean | yes | `true` only if data came from MCP API query |
| `warnings` | array | yes | Per-component warnings (NRND, derating, etc.). Empty `[]` if none. |
| `alternatives` | array | yes | Alternative components considered. Empty `[]` if none. |

## BOM Summary Fields (within `data.bom_summary`)

| Field | Type | Description |
|---|---|---|
| `unique_parts` | integer | Number of distinct part numbers |
| `total_components_per_unit` | integer | Total component count per board |
| `cost_per_unit` | number | Estimated cost for one board (USD) |
| `cost_total` | number | cost_per_unit × volume |
| `volume` | integer | Production volume |
| `currency` | string | Always "USD" unless user specifies otherwise |

## URL Rules

- Every URL field must contain a full, clickable URL
- Never truncate URLs with "..." or show partial paths
- If exact URL is unknown: `"URL not verified — search [source] for [MPN]"`
- Distributor URLs should link directly to the product page for that MPN
- SnapMagic URLs should link to the part's model page

## MPN Confidence Levels

Every component must include `mpn_confidence` indicating how the MPN was obtained:

- `"verified"` — MPN returned by a working MCP server querying a real distributor API. Highest trust.
- `"searched"` — MPN found via WebSearch/WebFetch on a distributor website. Include `mpn_source` URL. Trustworthy but may be stale.
- `"uncertain"` — MPN assembled from a manufacturer naming convention pattern. May not exist as listed. Must say so in warnings.
- `"fabricated"` — MPN generated from training data with no search performed. **Must be discarded. Never merge fabricated MPNs into final recommendations.**

If a sourcer subagent returns results with 0 tool calls, ALL its MPNs are `"fabricated"` regardless of how plausible they look.

## Verification Flag

- `"verified": false` — data is best-knowledge, not from API. User must confirm.
- `"verified": true` — data came from a working MCP server querying a real API. Can be trusted.
