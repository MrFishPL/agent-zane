# agent-zane

AI agent that sources electronic components from real distributor APIs. Give it a schematic (PDF, image, or text description), get back a verified BOM with pricing, stock levels, and direct purchase links.

## What it does

1. You upload a schematic or describe what you need
2. The agent analyzes the circuit, identifies components, and asks clarifying questions if needed
3. It queries real distributor APIs (Mouser, Octopart, more coming) in parallel
4. You get a structured JSON response with MPNs, prices, stock, datasheet links, and a BOM summary

No invented part numbers. Every MPN comes from a real API query or verified web search.

## Quick start

```bash
# Clone
git clone https://github.com/MrFishPL/agent-zane.git
cd agent-zane

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Install MCP server dependencies
cd mcp-servers/mouser && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && deactivate && cd ../..
cd mcp-servers/octopart && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && deactivate && cd ../..

# Run with Claude Code
claude
```

## How to use

Everything starts with `/ask`. Attach a file or type a description — the agent handles the rest.

After getting results, use `/feedback` to teach the agent your preferences (it saves them as lessons for future sessions).

## Example prompts

### Test 1: Audio mixer from academic paper

Download the PDF: [4-Channel Audio Mixer](https://www.scholarsresearchlibrary.com/articles/design-and-simulation-of-four-channel-audio-mixer.pdf)

```
/ask [attach mixer PDF]

Hi, I need to produce 200 units of this mixer.
Potentiometers must be panel-mount with D-shaft,
logarithmic 1M, dust-sealed.
Inputs and output on 6.35mm PCB-mount jacks.
All through-hole. Looking for the cheapest option.
```

This tests whether the agent can:
- Parse a multi-page academic PDF and extract schematics
- Handle specific mechanical requirements (D-shaft, dust-sealed, panel-mount)
- Source through-hole components at production volume pricing

### Test 2: Regulated power supply from a kit manual

Download the PDF: [LM317 Kit Instructions](http://myosuploads3.banggood.com/products/20220111/20220111234413LM317.pdf)

```
/ask [attach LM317 PDF]

I'm building this regulated power supply, single unit
for my workshop. I already have the transformer and
bridge rectifier — don't source those. I want quality
components, not the cheapest. I'll order everything
from one distributor.
```

This tests whether the agent can:
- Read a simple single-page schematic from a kit manual
- Respect exclusions ("already have transformer and bridge rectifier")
- Understand "single unit" means volume = 1
- Consolidate to one distributor when asked
- Prioritize quality over price when instructed

## Architecture

The agent runs inside [Claude Code](https://claude.ai/claude-code) and uses a subagent-first architecture:

- **schematic-analyzer** — reads one functional block from a schematic (one per block, parallel)
- **component-sourcer** — searches one distributor API (one per distributor, parallel)
- **result-merger** — combines multi-distributor results into ranked recommendations
- **cad-model-checker** — checks SnapMagic for CAD models after selection
- **lessons-reader** — loads learned preferences at session start

MCP servers in `mcp-servers/` provide the API integrations:

| Server | Status | Quota |
|--------|--------|-------|
| Mouser | Working | 1000 req/day |
| Octopart/Nexar | Working | 100 matched parts lifetime (use sparingly) |
| DigiKey | Planned | — |
| LCSC | Planned | — |

## API keys

Copy `.env.example` to `.env` and fill in your keys:

| Variable | Source |
|----------|--------|
| `MOUSER_API_KEY` | [Mouser API Hub](https://www.mouser.com/api-hub/) |
| `NEXAR_CLIENT_ID` | [Nexar Portal](https://portal.nexar.com/) |
| `NEXAR_CLIENT_SECRET` | [Nexar Portal](https://portal.nexar.com/) |

## Output format

Every response is a JSON envelope:

```json
{
  "status": "recommendation | analysis | needs_clarification",
  "message": "Human-readable explanation and reasoning",
  "data": { "components": [...], "bom_summary": {...} }
}
```

See `.claude/rules/output-format.md` for the full schema.

## License

MIT
