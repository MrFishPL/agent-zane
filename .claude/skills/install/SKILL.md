---
name: install
description: Set up the agent environment — creates virtual environments, installs dependencies, verifies API keys, and runs alive tests for all MCP servers. Run this after cloning the repo.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
user-invocable: true
---

Run the full installation and verification sequence for the agent. Print a status line for each step. At the end, print a summary table.

## Step 1: Check Python 3

```bash
python3 --version
```

If python3 is not found, stop and tell the user to install Python 3.8+.

## Step 2: Create root virtual environment

Create `.venv/` at project root and install root dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Verify by importing the key package:

```bash
.venv/bin/python3 -c "import fitz; print(f'PyMuPDF {fitz.version[0]} OK')"
```

Print: `[OK] Root venv — PyMuPDF installed` or `[FAIL] Root venv — ...`

## Step 3: Create MCP server virtual environments

Auto-discover all MCP servers: find every directory under `mcp-servers/` that contains a `requirements.txt` file.

For each server found:

```bash
cd mcp-servers/<server>/
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

Verify by importing the MCP package:

```bash
mcp-servers/<server>/venv/bin/python3 -c "import mcp; print('MCP SDK OK')"
```

Print: `[OK] <server> venv — dependencies installed` or `[FAIL] <server> venv — ...`

## Step 4: Check .env file and API keys

Check if `.env` exists at project root.

**If `.env` does NOT exist:**
- Copy `.env.example` to `.env`
- Tell the user: "Created .env from .env.example — please fill in your API keys."

**If `.env` exists:**
- Read `.env.example` to get the list of required variable names (parse lines matching `^[A-Z_]+=`)
- For each required variable, check if it is set in `.env` AND is not still the placeholder value (e.g., not "your-api-key-here", "your-client-id-here", "your-client-secret-here")
- Print per-key status:
  - `[OK] MOUSER_API_KEY — configured`
  - `[MISSING] NEXAR_CLIENT_ID — still placeholder or empty`

IMPORTANT: Do NOT read or print the actual key values. Only check presence and that they are not placeholders. Use grep or pattern matching, never display secrets.

To check without exposing values, use this approach:
```bash
grep '^MOUSER_API_KEY=' .env | grep -qv 'your-.*-here' && echo "OK" || echo "MISSING"
```

## Step 5: Alive test for MCP servers

For each MCP server that has a working venv, run a quick startup test. The server should start and respond to an MCP initialization, then exit cleanly.

Test by running the server's unit tests (skip live tests which need real API calls):

```bash
mcp-servers/<server>/venv/bin/python3 -m pytest mcp-servers/<server>/tests/test_client.py mcp-servers/<server>/tests/test_tools.py -v --timeout=30 -x
```

Print: `[OK] <server> — tests pass (X passed)` or `[FAIL] <server> — tests failed (see above)`

If pytest is not installed or tests don't exist, fall back to a simple import check:

```bash
mcp-servers/<server>/venv/bin/python3 -c "import server; print('Server module loads OK')"
```

## Step 6: Summary

Print a summary table:

```
=== Installation Summary ===

Python:          [OK] 3.x.x
Root venv:       [OK] PyMuPDF installed
Mouser venv:     [OK] dependencies installed
Octopart venv:   [OK] dependencies installed
MOUSER_API_KEY:  [OK] configured
NEXAR_CLIENT_ID: [MISSING] placeholder
NEXAR_SECRET:    [MISSING] placeholder
Mouser tests:    [OK] 12 passed
Octopart tests:  [OK] 15 passed

Ready to use: /ask
```

If any keys are missing, add a note:
```
NOTE: Some API keys are not configured. Edit .env to add them.
The agent can still work with the configured sources.
```

If everything passes:
```
All systems go. Run /ask to start sourcing components.
```
