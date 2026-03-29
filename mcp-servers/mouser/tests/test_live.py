"""Live smoke tests against the real Mouser API.

These tests consume API requests from the daily quota.
Budget: MAX 3 requests total across all tests.

Skip gracefully if credentials are missing.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env for credentials
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

MOUSER_API_KEY = os.environ.get("MOUSER_API_KEY", "")

skip_no_creds = pytest.mark.skipif(
    not MOUSER_API_KEY,
    reason="MOUSER_API_KEY not set",
)


@skip_no_creds
class TestLiveAPI:
    """Live tests — consume real API requests. Keep minimal."""

    @pytest.mark.asyncio
    async def test_keyword_search_potentiometer(self, tmp_path):
        """Keyword search for a specific potentiometer.

        Expected consumption: 1 API request.
        """
        import client as client_mod

        original_counter = client_mod.COUNTER_FILE
        client_mod.COUNTER_FILE = tmp_path / "live_counter.json"

        try:
            from client import MouserClient
            from schemas import validate_search_response, normalize_part

            c = MouserClient(MOUSER_API_KEY)

            data = await c.search_keyword(
                "1M logarithmic potentiometer D-shaft sealed",
                records=5,
            )

            # Validate response structure
            search_results = validate_search_response(data)
            assert isinstance(search_results["NumberOfResult"], int)

            parts = search_results.get("Parts", [])
            print(f"\n  Keyword search: {search_results['NumberOfResult']} total results")
            print(f"  Returned: {len(parts)} parts")

            for i, part in enumerate(parts[:3]):
                normalized = normalize_part(part)
                print(f"\n  Part {i+1}: {normalized['mpn']}")
                print(f"    Manufacturer: {normalized['manufacturer']}")
                print(f"    Description: {normalized['description']}")
                print(f"    Availability: {normalized['availability']}")
                print(f"    Unit price: {normalized['unit_price']}")
                print(f"    URL: {normalized['product_detail_url']}")

            await c.close()
        finally:
            client_mod.COUNTER_FILE = original_counter

    @pytest.mark.asyncio
    async def test_part_number_search(self, tmp_path):
        """MPN search for a known part.

        Expected consumption: 1 API request.
        """
        import client as client_mod

        original_counter = client_mod.COUNTER_FILE
        client_mod.COUNTER_FILE = tmp_path / "live_counter.json"

        try:
            from client import MouserClient
            from schemas import validate_search_response, normalize_part

            c = MouserClient(MOUSER_API_KEY)

            data = await c.search_part_number("LM7805CT", part_search_options="None")

            search_results = validate_search_response(data)
            assert search_results["NumberOfResult"] >= 1, "Expected at least 1 result for LM7805CT"

            parts = search_results.get("Parts", [])
            assert len(parts) >= 1

            normalized = normalize_part(parts[0])
            assert normalized["mpn"], "MPN should not be empty"
            assert normalized["manufacturer"], "Manufacturer should not be empty"

            print(f"\n  MPN search result: {normalized['mpn']}")
            print(f"    Manufacturer: {normalized['manufacturer']}")
            print(f"    Availability: {normalized['availability']}")
            print(f"    Unit price: {normalized['unit_price']}")

            await c.close()
        finally:
            client_mod.COUNTER_FILE = original_counter
