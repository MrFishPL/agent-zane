"""Integration tests for MCP tools with mocked HTTP responses."""

import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from client import MouserClient
from schemas import (
    extract_lifecycle,
    extract_price_breaks,
    normalize_part,
    parse_availability,
    parse_price,
    validate_search_response,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# --- Schema validation tests ---


class TestValidateSearchResponse:
    def test_valid_keyword_response(self):
        fixture = load_fixture("keyword_search_response.json")
        result = validate_search_response(fixture)
        assert result["NumberOfResult"] == 3
        assert len(result["Parts"]) == 3

    def test_valid_part_number_response(self):
        fixture = load_fixture("part_number_response.json")
        result = validate_search_response(fixture)
        assert result["NumberOfResult"] == 1

    def test_empty_response(self):
        fixture = load_fixture("empty_response.json")
        result = validate_search_response(fixture)
        assert result["NumberOfResult"] == 0
        assert result["Parts"] == []

    def test_error_response_raises(self):
        fixture = load_fixture("error_response.json")
        with pytest.raises(ValueError, match="InvalidApiKey"):
            validate_search_response(fixture)

    def test_missing_search_results_raises(self):
        with pytest.raises(ValueError, match="Missing 'SearchResults'"):
            validate_search_response({})

    def test_null_search_results_raises(self):
        with pytest.raises(ValueError, match="null"):
            validate_search_response({"SearchResults": None})


class TestParseAvailability:
    def test_standard_format(self):
        assert parse_availability("4500 In Stock") == 4500

    def test_with_commas(self):
        assert parse_availability("12,500 In Stock") == 12500

    def test_zero(self):
        assert parse_availability("0") == 0

    def test_empty_string(self):
        assert parse_availability("") == 0

    def test_no_number(self):
        assert parse_availability("In Stock") == 0

    def test_none_string(self):
        assert parse_availability("None") == 0

    def test_large_number(self):
        assert parse_availability("1,234,567 In Stock") == 1234567


class TestParsePrice:
    def test_usd(self):
        assert parse_price("$0.85") == 0.85

    def test_euro(self):
        assert parse_price("€1.20") == 1.20

    def test_no_symbol(self):
        assert parse_price("1.50") == 1.50

    def test_empty(self):
        assert parse_price("") is None

    def test_none(self):
        assert parse_price(None) is None

    def test_european_comma(self):
        assert parse_price("€1,20") == 1.20

    def test_thousands_separator(self):
        assert parse_price("$1,234.56") == 1234.56

    def test_small_price(self):
        assert parse_price("$0.005") == 0.005


class TestExtractPriceBreaks:
    def test_standard_breaks_under_limit(self):
        breaks = [
            {"Quantity": 1, "Price": "$0.85", "Currency": "USD"},
            {"Quantity": 100, "Price": "$0.54", "Currency": "USD"},
        ]
        result = extract_price_breaks(breaks)
        assert len(result) == 2
        assert result[0] == {"quantity": 1, "price": 0.85}
        assert result[1] == {"quantity": 100, "price": 0.54}

    def test_limits_to_3_breaks(self):
        breaks = [
            {"Quantity": 1, "Price": "$1.00", "Currency": "USD"},
            {"Quantity": 5, "Price": "$0.90", "Currency": "USD"},
            {"Quantity": 25, "Price": "$0.80", "Currency": "USD"},
            {"Quantity": 100, "Price": "$0.60", "Currency": "USD"},
            {"Quantity": 500, "Price": "$0.50", "Currency": "USD"},
            {"Quantity": 1000, "Price": "$0.40", "Currency": "USD"},
        ]
        result = extract_price_breaks(breaks)
        assert len(result) == 3
        qtys = [r["quantity"] for r in result]
        assert 1 in qtys
        assert 100 in qtys
        assert 1000 in qtys

    def test_empty(self):
        assert extract_price_breaks([]) == []

    def test_none(self):
        assert extract_price_breaks(None) == []


class TestExtractLifecycle:
    def test_active(self):
        assert extract_lifecycle("Active") == "active"

    def test_production(self):
        assert extract_lifecycle("Production") == "active"

    def test_nrnd(self):
        assert extract_lifecycle("NRND") == "nrnd"

    def test_not_recommended(self):
        assert extract_lifecycle("Not Recommended for New Designs") == "nrnd"

    def test_obsolete(self):
        assert extract_lifecycle("Obsolete") == "obsolete"

    def test_eol(self):
        assert extract_lifecycle("End of Life") == "obsolete"

    def test_discontinued(self):
        assert extract_lifecycle("Discontinued") == "obsolete"

    def test_empty(self):
        assert extract_lifecycle("") == "unknown"

    def test_none(self):
        assert extract_lifecycle(None) == "unknown"

    def test_unknown_value_passthrough(self):
        assert extract_lifecycle("Limited Availability") == "limited availability"


class TestNormalizePart:
    def test_full_part(self):
        fixture = load_fixture("keyword_search_response.json")
        raw_part = fixture["SearchResults"]["Parts"][0]
        normalized = normalize_part(raw_part)

        assert normalized["mpn"] == "LM3900N/NOPB"
        assert normalized["manufacturer"] == "Texas Instruments"
        assert normalized["availability"] == 4500
        assert normalized["unit_price"] == 0.85
        assert len(normalized["price_breaks"]) == 3
        assert normalized["rohs_status"] == "RoHS Compliant"
        # Removed fields should not be present
        assert "mouser_part_number" not in normalized
        assert "category" not in normalized
        assert "attributes" not in normalized
        assert "image_url" not in normalized

    def test_part_strips_empty_fields(self):
        fixture = load_fixture("keyword_search_response.json")
        raw_part = fixture["SearchResults"]["Parts"][2]  # Obsolete part, no prices
        normalized = normalize_part(raw_part)

        assert normalized["mpn"] == "LM3900N"
        assert normalized["lifecycle"] == "obsolete"
        # Empty fields should be stripped
        assert "unit_price" not in normalized  # None stripped
        assert "price_breaks" not in normalized  # empty list stripped
        assert "datasheet_url" not in normalized  # empty string stripped
        assert "rohs_status" not in normalized  # empty string stripped

    def test_part_with_commas_in_availability(self):
        fixture = load_fixture("keyword_search_response.json")
        raw_part = fixture["SearchResults"]["Parts"][1]  # "12,500 In Stock"
        normalized = normalize_part(raw_part)

        assert normalized["availability"] == 12500
        assert normalized["lifecycle"] == "active"


# --- Tool integration tests (mocked HTTP) ---


def make_mocked_client(fixture_name: str, tmp_path) -> MouserClient:
    """Create a MouserClient with mocked HTTP that returns fixture data."""
    import client as client_mod

    original_counter = client_mod.COUNTER_FILE
    client_mod.COUNTER_FILE = tmp_path / "counter.json"

    c = MouserClient("test-key")

    fixture = load_fixture(fixture_name)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.is_closed = False
    c._http = mock_http

    client_mod.COUNTER_FILE = original_counter
    return c


class TestToolSearchParts:
    @pytest.mark.asyncio
    async def test_keyword_search_returns_results(self, tmp_path):
        import client as client_mod
        original = client_mod.COUNTER_FILE
        client_mod.COUNTER_FILE = tmp_path / "counter.json"
        try:
            c = make_mocked_client("keyword_search_response.json", tmp_path)

            data = await c.search_keyword("op amp", records=10)
            search_results = validate_search_response(data)

            assert search_results["NumberOfResult"] == 3
            assert len(search_results["Parts"]) == 3

            part = search_results["Parts"][0]
            assert part["ManufacturerPartNumber"] == "LM3900N/NOPB"
            assert part["Manufacturer"] == "Texas Instruments"
        finally:
            client_mod.COUNTER_FILE = original


class TestToolSearchMPN:
    @pytest.mark.asyncio
    async def test_mpn_search_returns_results(self, tmp_path):
        import client as client_mod
        original = client_mod.COUNTER_FILE
        client_mod.COUNTER_FILE = tmp_path / "counter.json"
        try:
            c = make_mocked_client("part_number_response.json", tmp_path)

            data = await c.search_part_number("LM7805CT/NOPB", part_search_options="Exact")
            search_results = validate_search_response(data)

            assert search_results["NumberOfResult"] == 1
            part = search_results["Parts"][0]
            assert part["ManufacturerPartNumber"] == "LM7805CT/NOPB"
            assert part["Manufacturer"] == "Texas Instruments"

            normalized = normalize_part(part)
            assert normalized["availability"] == 8234
            assert normalized["unit_price"] == 0.59
        finally:
            client_mod.COUNTER_FILE = original


class TestToolSearchManufacturer:
    @pytest.mark.asyncio
    async def test_manufacturer_search_returns_results(self, tmp_path):
        import client as client_mod
        original = client_mod.COUNTER_FILE
        client_mod.COUNTER_FILE = tmp_path / "counter.json"
        try:
            c = make_mocked_client("manufacturer_search_response.json", tmp_path)

            data = await c.search_keyword_and_manufacturer(
                "capacitor", "Murata", records=10
            )
            search_results = validate_search_response(data)

            assert search_results["NumberOfResult"] == 2
            for part in search_results["Parts"]:
                assert part["Manufacturer"] == "Murata"
        finally:
            client_mod.COUNTER_FILE = original
