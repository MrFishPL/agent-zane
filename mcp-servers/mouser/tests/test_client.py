"""Unit tests for the Mouser API client. Uses fixtures, no real API calls."""

import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from client import MouserClient, COUNTER_FILE

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class TestMouserClientInit:
    def test_raises_on_empty_key(self):
        with pytest.raises(ValueError, match="MOUSER_API_KEY"):
            MouserClient("")

    def test_creates_with_valid_key(self):
        client = MouserClient("test-key")
        assert client.api_key == "test-key"
        assert client.daily_requests_remaining <= 1000


class TestRateLimiting:
    def test_daily_counter_load_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("client.COUNTER_FILE", tmp_path / "missing.json")
        client = MouserClient("test-key")
        assert client.daily_requests_remaining == 1000

    def test_daily_counter_load_existing(self, tmp_path, monkeypatch):
        counter_file = tmp_path / "counter.json"
        today = time.strftime("%Y-%m-%d")
        counter_file.write_text(json.dumps({"date": today, "count": 42}))
        monkeypatch.setattr("client.COUNTER_FILE", counter_file)
        client = MouserClient("test-key")
        assert client.daily_requests_remaining == 958

    def test_daily_counter_resets_on_new_day(self, tmp_path, monkeypatch):
        counter_file = tmp_path / "counter.json"
        counter_file.write_text(json.dumps({"date": "1999-01-01", "count": 999}))
        monkeypatch.setattr("client.COUNTER_FILE", counter_file)
        client = MouserClient("test-key")
        assert client.daily_requests_remaining == 1000

    def test_corrupted_counter_file(self, tmp_path, monkeypatch):
        counter_file = tmp_path / "counter.json"
        counter_file.write_text("not json")
        monkeypatch.setattr("client.COUNTER_FILE", counter_file)
        client = MouserClient("test-key")
        assert client.daily_requests_remaining == 1000

    def test_daily_limit_enforcement(self, tmp_path, monkeypatch):
        counter_file = tmp_path / "counter.json"
        today = time.strftime("%Y-%m-%d")
        counter_file.write_text(json.dumps({"date": today, "count": 1000}))
        monkeypatch.setattr("client.COUNTER_FILE", counter_file)
        client = MouserClient("test-key")

        with pytest.raises(Exception, match="daily rate limit"):
            client._check_rate_limits()

    def test_per_minute_limit_enforcement(self, tmp_path, monkeypatch):
        monkeypatch.setattr("client.COUNTER_FILE", tmp_path / "counter.json")
        client = MouserClient("test-key")

        now = time.time()
        client._request_timestamps = [now - i for i in range(30)]

        with pytest.raises(Exception, match="per-minute rate limit"):
            client._check_rate_limits()

    def test_save_and_reload_counter(self, tmp_path, monkeypatch):
        counter_file = tmp_path / "counter.json"
        monkeypatch.setattr("client.COUNTER_FILE", counter_file)

        client = MouserClient("test-key")
        client._log_request("test_endpoint")
        assert client.daily_requests_remaining == 999

        # Reload
        client2 = MouserClient("test-key")
        assert client2.daily_requests_remaining == 999


class TestHTTPPost:
    @pytest.mark.asyncio
    async def test_successful_post(self, tmp_path, monkeypatch):
        monkeypatch.setattr("client.COUNTER_FILE", tmp_path / "counter.json")
        fixture = load_fixture("keyword_search_response.json")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = False

        client = MouserClient("test-key")
        client._http = mock_http

        result = await client._post("https://api.mouser.com/test", {"test": True})
        assert "SearchResults" in result
        assert result["SearchResults"]["NumberOfResult"] == 3

    @pytest.mark.asyncio
    async def test_http_error_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr("client.COUNTER_FILE", tmp_path / "counter.json")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = False

        client = MouserClient("test-key")
        client._http = mock_http

        with pytest.raises(Exception, match="request failed"):
            await client._post("https://api.mouser.com/test", {})

    @pytest.mark.asyncio
    async def test_search_keyword_builds_correct_body(self, tmp_path, monkeypatch):
        monkeypatch.setattr("client.COUNTER_FILE", tmp_path / "counter.json")
        fixture = load_fixture("keyword_search_response.json")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = False

        client = MouserClient("test-key")
        client._http = mock_http

        await client.search_keyword("op amp", records=5, search_options="InStock")

        call_args = mock_http.post.call_args
        body = call_args.kwargs.get("json") or call_args[1].get("json")
        req = body["SearchByKeywordRequest"]
        assert req["keyword"] == "op amp"
        assert req["records"] == 5
        assert req["searchOptions"] == "InStock"

    @pytest.mark.asyncio
    async def test_search_part_number_builds_correct_body(self, tmp_path, monkeypatch):
        monkeypatch.setattr("client.COUNTER_FILE", tmp_path / "counter.json")
        fixture = load_fixture("part_number_response.json")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = False

        client = MouserClient("test-key")
        client._http = mock_http

        await client.search_part_number("LM7805CT/NOPB", part_search_options="Exact")

        call_args = mock_http.post.call_args
        body = call_args.kwargs.get("json") or call_args[1].get("json")
        req = body["SearchByPartRequest"]
        assert req["mouserPartNumber"] == "LM7805CT/NOPB"
        assert req["partSearchOptions"] == "Exact"

    @pytest.mark.asyncio
    async def test_records_capped_at_50(self, tmp_path, monkeypatch):
        monkeypatch.setattr("client.COUNTER_FILE", tmp_path / "counter.json")
        fixture = load_fixture("keyword_search_response.json")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = False

        client = MouserClient("test-key")
        client._http = mock_http

        await client.search_keyword("test", records=100)

        call_args = mock_http.post.call_args
        body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert body["SearchByKeywordRequest"]["records"] == 50
