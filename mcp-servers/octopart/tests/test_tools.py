"""Integration tests for MCP tools with mocked HTTP responses."""

import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from client import NexarClient
from schemas import (
    compress_multi_match,
    compress_part,
    compress_result_set,
    count_parts_in_multi_match,
    count_parts_in_response,
    extract_lifecycle,
    validate_multi_match_response,
    validate_search_response,
    _compress_sellers,
    _compress_specs,
    _pick_best_price_breaks,
    _strip_empty,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# --- Schema validation tests ---


class TestValidateSearchResponse:
    def test_valid_supSearch(self):
        fixture = load_fixture("search_parts_response.json")
        result = validate_search_response(fixture["data"], "supSearch")
        assert result["hits"] == 42
        assert len(result["results"]) == 1

    def test_valid_supSearchMpn(self):
        fixture = load_fixture("search_mpn_response.json")
        result = validate_search_response(fixture["data"], "supSearchMpn")
        assert result["hits"] == 1

    def test_missing_key_raises(self):
        with pytest.raises(ValueError, match="Missing"):
            validate_search_response({}, "supSearch")


class TestValidateMultiMatch:
    def test_valid_response(self):
        fixture = load_fixture("multi_match_response.json")
        result = validate_multi_match_response(fixture["data"])
        assert len(result) == 2

    def test_missing_key_raises(self):
        with pytest.raises(ValueError, match="Missing"):
            validate_multi_match_response({})


class TestCountParts:
    def test_count_search_results(self):
        fixture = load_fixture("search_mpn_response.json")
        count = count_parts_in_response(fixture["data"], "supSearchMpn")
        assert count == 1

    def test_count_search_parts(self):
        fixture = load_fixture("search_parts_response.json")
        count = count_parts_in_response(fixture["data"], "supSearch")
        assert count == 1

    def test_count_multi_match(self):
        fixture = load_fixture("multi_match_response.json")
        count = count_parts_in_multi_match(fixture["data"])
        assert count == 2

    def test_count_empty_response(self):
        count = count_parts_in_response({}, "supSearch")
        assert count == 0


class TestExtractLifecycle:
    def test_production(self):
        specs = [
            {"attribute": {"shortname": "lifecyclestatus"}, "displayValue": "Production"}
        ]
        assert extract_lifecycle(specs) == "active"

    def test_active(self):
        specs = [
            {"attribute": {"shortname": "lifecyclestatus"}, "displayValue": "Active"}
        ]
        assert extract_lifecycle(specs) == "active"

    def test_nrnd(self):
        specs = [
            {
                "attribute": {"shortname": "lifecyclestatus"},
                "displayValue": "Not Recommended for New Designs",
            }
        ]
        assert extract_lifecycle(specs) == "nrnd"

    def test_nrnd_short(self):
        specs = [
            {"attribute": {"shortname": "lifecyclestatus"}, "displayValue": "NRND"}
        ]
        assert extract_lifecycle(specs) == "nrnd"

    def test_obsolete(self):
        specs = [
            {"attribute": {"shortname": "lifecyclestatus"}, "displayValue": "Obsolete"}
        ]
        assert extract_lifecycle(specs) == "obsolete"

    def test_eol(self):
        specs = [
            {
                "attribute": {"shortname": "lifecyclestatus"},
                "displayValue": "End of Life",
            }
        ]
        assert extract_lifecycle(specs) == "obsolete"

    def test_unknown_when_missing(self):
        specs = [
            {"attribute": {"shortname": "resistance"}, "displayValue": "10k"}
        ]
        assert extract_lifecycle(specs) == "unknown"

    def test_unknown_when_none(self):
        assert extract_lifecycle(None) == "unknown"

    def test_unknown_when_empty(self):
        assert extract_lifecycle([]) == "unknown"

    def test_new_product(self):
        specs = [
            {
                "attribute": {"shortname": "lifecyclestatus"},
                "displayValue": "New Product",
            }
        ]
        assert extract_lifecycle(specs) == "active"

    def test_passes_through_unknown_value(self):
        specs = [
            {
                "attribute": {"shortname": "lifecyclestatus"},
                "displayValue": "Limited Availability",
            }
        ]
        assert extract_lifecycle(specs) == "limited availability"

    def test_strips_parenthetical_annotation(self):
        specs = [
            {
                "attribute": {"shortname": "lifecyclestatus"},
                "displayValue": "Production (last updated: 20 hours ago)",
            }
        ]
        assert extract_lifecycle(specs) == "active"

    def test_obsolete_with_annotation(self):
        specs = [
            {
                "attribute": {"shortname": "lifecyclestatus"},
                "displayValue": "Obsolete (last updated: 3 days ago)",
            }
        ]
        assert extract_lifecycle(specs) == "obsolete"


# --- Compression tests ---


class TestStripEmpty:
    def test_removes_none(self):
        assert _strip_empty({"a": 1, "b": None}) == {"a": 1}

    def test_removes_empty_string(self):
        assert _strip_empty({"a": "val", "b": ""}) == {"a": "val"}

    def test_removes_empty_list(self):
        assert _strip_empty({"a": [1], "b": []}) == {"a": [1]}

    def test_removes_empty_dict(self):
        assert _strip_empty({"a": {"x": 1}, "b": {}}) == {"a": {"x": 1}}

    def test_keeps_zero(self):
        # 0 is a valid value (e.g., stock=0)
        result = _strip_empty({"stock": 0, "name": "x"})
        assert "stock" in result


class TestPickBestPriceBreaks:
    def test_three_or_fewer_returned_as_is(self):
        prices = [
            {"quantity": 1, "price": 0.59},
            {"quantity": 10, "price": 0.49},
        ]
        result = _pick_best_price_breaks(prices)
        assert len(result) == 2

    def test_picks_closest_to_targets(self):
        prices = [
            {"quantity": 1, "price": 1.00},
            {"quantity": 5, "price": 0.90},
            {"quantity": 25, "price": 0.80},
            {"quantity": 50, "price": 0.70},
            {"quantity": 100, "price": 0.60},
            {"quantity": 500, "price": 0.50},
            {"quantity": 1000, "price": 0.40},
            {"quantity": 5000, "price": 0.30},
        ]
        result = _pick_best_price_breaks(prices)
        assert len(result) == 3
        qtys = [r["quantity"] for r in result]
        assert 1 in qtys
        assert 100 in qtys
        assert 1000 in qtys

    def test_empty_input(self):
        assert _pick_best_price_breaks([]) == []

    def test_slim_drops_extra_fields(self):
        prices = [
            {"quantity": 1, "price": 0.59, "currency": "USD", "convertedPrice": 0.59},
        ]
        result = _pick_best_price_breaks(prices)
        assert result == [{"quantity": 1, "price": 0.59}]


class TestCompressSpecs:
    def test_keeps_key_specs(self):
        specs = [
            {"attribute": {"shortname": "lifecyclestatus"}, "displayValue": "Production"},
            {"attribute": {"shortname": "case_package"}, "displayValue": "TO-220"},
            {"attribute": {"shortname": "outputvoltage"}, "displayValue": "5V"},
            {"attribute": {"shortname": "outputcurrent"}, "displayValue": "1.5A"},
        ]
        result = _compress_specs(specs)
        assert result["lifecyclestatus"] == "Production"
        assert result["case_package"] == "TO-220"
        assert result["outputvoltage"] == "5V"
        assert len(result) == 4

    def test_drops_non_key_specs(self):
        specs = [
            {"attribute": {"shortname": "lifecyclestatus"}, "displayValue": "Production"},
            {"attribute": {"shortname": "numberofpins"}, "displayValue": "3"},
            {"attribute": {"shortname": "mountingtype"}, "displayValue": "Through Hole"},
            {"attribute": {"shortname": "weight"}, "displayValue": "2g"},
        ]
        result = _compress_specs(specs)
        assert "lifecyclestatus" in result
        assert "numberofpins" not in result
        assert "mountingtype" not in result
        assert "weight" not in result

    def test_empty_specs(self):
        assert _compress_specs([]) == {}
        assert _compress_specs(None) == {}


class TestCompressSellers:
    def test_limits_to_5_sellers(self):
        sellers = []
        for i in range(8):
            sellers.append({
                "company": {"name": f"Seller{i}"},
                "offers": [{
                    "sku": f"SKU-{i}",
                    "inventoryLevel": 100,
                    "moq": 1,
                    "prices": [{"quantity": 1, "price": 0.50 + i * 0.1}],
                }],
            })
        result = _compress_sellers(sellers)
        assert len(result) == 5

    def test_sorts_by_lowest_price(self):
        sellers = [
            {"company": {"name": "Expensive"}, "offers": [{"sku": "A", "inventoryLevel": 100, "moq": 1, "prices": [{"quantity": 1, "price": 5.00}]}]},
            {"company": {"name": "Cheap"}, "offers": [{"sku": "B", "inventoryLevel": 100, "moq": 1, "prices": [{"quantity": 1, "price": 0.10}]}]},
        ]
        result = _compress_sellers(sellers)
        assert result[0]["seller"] == "Cheap"
        assert result[1]["seller"] == "Expensive"

    def test_empty_sellers(self):
        assert _compress_sellers([]) == []


class TestCompressPart:
    def test_compress_mpn_fixture(self):
        fixture = load_fixture("search_mpn_response.json")
        raw_part = fixture["data"]["supSearchMpn"]["results"][0]["part"]
        compressed = compress_part(raw_part)

        assert compressed["mpn"] == "LM7805CT"
        assert compressed["manufacturer"] == "Texas Instruments"
        assert compressed["lifecycle"] == "active"
        assert compressed["totalAvail"] == 50000
        assert "datasheetUrl" in compressed
        assert "medianPrice1000" in compressed

        # Specs should be flat dict with only key specs
        assert isinstance(compressed["specs"], dict)
        assert "lifecyclestatus" in compressed["specs"]
        assert "case_package" in compressed["specs"]

        # Sellers compressed
        assert len(compressed["sellers"]) == 2
        for seller in compressed["sellers"]:
            assert "seller" in seller
            assert "offers" in seller
            for offer in seller["offers"]:
                assert "sku" in offer
                # price breaks should be slim (no currency/convertedPrice)
                for pb in offer["prices"]:
                    assert set(pb.keys()) == {"quantity", "price"}

        # Raw verbose fields should NOT be present
        assert "name" not in compressed
        assert "category" not in compressed
        assert "homepageUrl" not in compressed

    def test_compress_part_strips_empty(self):
        part = {
            "mpn": "TEST",
            "manufacturer": {"name": "Acme"},
            "shortDescription": "Test part",
            "totalAvail": 0,
            "specs": [],
            "sellers": [],
            "octopartUrl": "",
            "bestDatasheet": {},
            "medianPrice1000": None,
        }
        compressed = compress_part(part)
        assert "specs" not in compressed  # empty dict stripped
        assert "sellers" not in compressed  # empty list stripped
        assert "octopartUrl" not in compressed  # empty string stripped
        assert "datasheetUrl" not in compressed
        assert "medianPrice1000" not in compressed


class TestCompressResultSet:
    def test_compress_search_result(self):
        fixture = load_fixture("search_mpn_response.json")
        raw = fixture["data"]["supSearchMpn"]
        compressed = compress_result_set(raw)

        assert compressed["hits"] == 1
        assert len(compressed["results"]) == 1
        part = compressed["results"][0]["part"]
        assert part["mpn"] == "LM7805CT"

    def test_compress_multi_match(self):
        fixture = load_fixture("multi_match_response.json")
        raw = fixture["data"]["supMultiMatch"]
        compressed = compress_multi_match(raw)

        assert len(compressed) == 2
        assert compressed[0]["parts"][0]["mpn"] == "LM7805CT"
        assert compressed[1]["parts"][0]["mpn"] == "LM317T"


# --- Tool integration tests (mocked HTTP) ---


def make_mocked_client(fixture_name: str, tmp_path) -> NexarClient:
    """Create a NexarClient with mocked HTTP that returns fixture data."""
    import client as client_mod

    # Patch counter file to tmp
    original_counter = client_mod.COUNTER_FILE
    client_mod.COUNTER_FILE = tmp_path / "counter.json"

    c = NexarClient("test-id", "test-secret")
    c._token = "valid-token"
    c._token_expiry = time.time() + 3600

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


class TestToolSearchMPN:
    @pytest.mark.asyncio
    async def test_search_mpn_returns_results(self, tmp_path):
        import client as client_mod
        original = client_mod.COUNTER_FILE
        client_mod.COUNTER_FILE = tmp_path / "counter.json"
        try:
            c = make_mocked_client("search_mpn_response.json", tmp_path)
            from tools import register_tools
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("test")
            register_tools(mcp, c)

            # Call the tool directly via the client's query
            from queries import SEARCH_MPN
            data = await c.query(SEARCH_MPN, {"q": "LM7805", "limit": 1, "currency": "USD", "country": "US"})
            result = data["supSearchMpn"]

            assert result["hits"] == 1
            part = result["results"][0]["part"]
            assert part["mpn"] == "LM7805CT"
            assert part["manufacturer"]["name"] == "Texas Instruments"
            assert len(part["sellers"]) == 2

            # Verify compression works on this data
            compressed = compress_part(part)
            assert compressed["mpn"] == "LM7805CT"
            assert compressed["manufacturer"] == "Texas Instruments"
            assert len(compressed["sellers"]) == 2
        finally:
            client_mod.COUNTER_FILE = original

    @pytest.mark.asyncio
    async def test_lifecycle_extraction_from_fixture(self):
        fixture = load_fixture("search_mpn_response.json")
        part = fixture["data"]["supSearchMpn"]["results"][0]["part"]
        lifecycle = extract_lifecycle(part["specs"])
        assert lifecycle == "active"


class TestToolSearchParts:
    @pytest.mark.asyncio
    async def test_search_parts_returns_results(self, tmp_path):
        import client as client_mod
        original = client_mod.COUNTER_FILE
        client_mod.COUNTER_FILE = tmp_path / "counter.json"
        try:
            c = make_mocked_client("search_parts_response.json", tmp_path)

            from queries import SEARCH_PARTS
            data = await c.query(SEARCH_PARTS, {"q": "3 ohm resistor", "limit": 1, "currency": "USD", "country": "US"})
            result = data["supSearch"]

            assert result["hits"] == 42
            part = result["results"][0]["part"]
            assert "CRCW0603" in part["mpn"]

            # Verify compression
            compressed = compress_result_set(result)
            assert compressed["hits"] == 42
            assert compressed["results"][0]["part"]["mpn"] == part["mpn"]
        finally:
            client_mod.COUNTER_FILE = original


class TestToolMultiMatch:
    @pytest.mark.asyncio
    async def test_multi_match_returns_both(self, tmp_path):
        import client as client_mod
        original = client_mod.COUNTER_FILE
        client_mod.COUNTER_FILE = tmp_path / "counter.json"
        try:
            c = make_mocked_client("multi_match_response.json", tmp_path)

            from queries import MULTI_MATCH
            data = await c.query(
                MULTI_MATCH,
                {"queries": [{"mpn": "LM7805CT"}, {"mpn": "LM317T"}], "currency": "USD", "country": "US"},
            )
            matches = data["supMultiMatch"]

            assert len(matches) == 2
            assert matches[0]["parts"][0]["mpn"] == "LM7805CT"
            assert matches[1]["parts"][0]["mpn"] == "LM317T"

            # Verify compression
            compressed = compress_multi_match(matches)
            assert len(compressed) == 2
            assert compressed[0]["parts"][0]["mpn"] == "LM7805CT"
        finally:
            client_mod.COUNTER_FILE = original
