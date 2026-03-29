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
git clone https://github.com/MrFishPL/agent-zane.git
cd agent-zane
claude
```

Then run:

```
/install
```

This creates all virtual environments, installs dependencies, checks your API keys, and runs tests. It will tell you exactly what's missing.

## How to use

| Command | What it does |
|---------|-------------|
| `/install` | Set up the environment (run once after cloning) |
| `/ask` | Start a sourcing request (text, image, or PDF) |
| `/feedback` | Teach the agent your preferences for future sessions |

## Example prompts

### 1. Audio mixer — production run from academic paper

Download the PDF: [4-Channel Audio Mixer](https://www.scholarsresearchlibrary.com/articles/design-and-simulation-of-four-channel-audio-mixer.pdf)

```
/ask [attach mixer PDF]

Hi, I need to produce 200 units of this mixer.
Potentiometers must be panel-mount with D-shaft,
logarithmic 1M, dust-sealed.
Inputs and output on 6.35mm PCB-mount jacks.
All through-hole. Looking for the cheapest option.
```

Tests: multi-page academic PDF parsing, specific mechanical requirements (D-shaft, dust-sealed, panel-mount), through-hole sourcing at production volume.

### 2. Lab power supply — specific figure from a datasheet

Download the PDF: [LM317 Datasheet (TI)](https://www.ti.com/lit/ds/symlink/lm317.pdf)

```
/ask [attach LM317 datasheet PDF]

I have the LM317 datasheet here. I'm interested in the
schematic from Figure 22 — "Laboratory Power Supply".
Building a single unit for my workshop, I want quality
components. I already have the transformer and bridge
rectifier — don't source those. I'll order everything
from one distributor.
```

Tests: finding a specific figure in a multi-page datasheet, skipping irrelevant pages (specs, package drawings), understanding volume = 1, respecting component exclusions, single-distributor consolidation, quality over price.

### 3. Simple text request — no schematic

```
/ask

I need a 5V 2A buck converter for a Raspberry Pi project.
Input is 12V from a wall adapter. I want something easy
to solder by hand — no QFN or tiny packages. Just the
converter IC and its support components (inductor, caps,
diode, resistors). 50 units.
```

Tests: text-only input (no PDF/image), designing a BOM from a description, package constraints (hand-solderable), complete support component list, mid-volume pricing.

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

Copy `.env.example` to `.env` and fill in your keys (or run `/install` and it will guide you):

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
