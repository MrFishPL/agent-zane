"""Live smoke tests against the real Nexar API.

These tests consume matched parts from the quota.
Budget: MAX 2 parts total across all tests.

Skip gracefully if credentials are missing.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Check for credentials before importing
NEXAR_CLIENT_ID = os.environ.get("NEXAR_CLIENT_ID", "")
NEXAR_CLIENT_SECRET = os.environ.get("NEXAR_CLIENT_SECRET", "")

skip_no_creds = pytest.mark.skipif(
    not NEXAR_CLIENT_ID or not NEXAR_CLIENT_SECRET,
    reason="NEXAR_CLIENT_ID and NEXAR_CLIENT_SECRET not set",
)


@skip_no_creds
class TestLiveAPI:
    """Live tests — consume real quota. Keep minimal."""

    @pytest.mark.asyncio
    async def test_auth_and_search_mpn(self, tmp_path):
        """Single MPN search: verifies auth + query + response parsing.

        Expected consumption: 1 matched part.
        """
        import client as client_mod

        original_counter = client_mod.COUNTER_FILE
        client_mod.COUNTER_FILE = tmp_path / "live_counter.json"

        try:
            from client import NexarClient
            from queries import SEARCH_MPN
            from schemas import extract_lifecycle, validate_search_response

            c = NexarClient(NEXAR_CLIENT_ID, NEXAR_CLIENT_SECRET)

            data = await c.query(SEARCH_MPN, {"q": "LM7805", "limit": 1, "currency": "USD", "country": "US"})

            # Validate structure
            result_set = validate_search_response(data, "supSearchMpn")
            assert result_set["hits"] >= 1, "Expected at least 1 hit for LM7805"

            results = result_set["results"]
            assert len(results) >= 1

            part = results[0]["part"]
            assert part["mpn"], "MPN should not be empty"
            assert part["manufacturer"]["name"], "Manufacturer should not be empty"

            # Lifecycle extraction
            lifecycle = extract_lifecycle(part.get("specs"))
            assert lifecycle in ("active", "nrnd", "obsolete", "unknown")

            # Sellers/pricing (may be empty on eval tier, but structure should exist)
            assert "sellers" in part

            print(f"\n  Live result: {part['mpn']} by {part['manufacturer']['name']}")
            print(f"  Lifecycle: {lifecycle}")
            print(f"  Total availability: {part.get('totalAvail', 'N/A')}")
            if part.get("sellers"):
                seller = part["sellers"][0]
                print(f"  First seller: {seller['company']['name']}")

            await c.close()
        finally:
            client_mod.COUNTER_FILE = original_counter
