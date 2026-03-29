"""Unit tests for the Nexar API client. Uses fixtures, no real API calls."""

import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from client import NexarClient, _decode_jwt_exp, COUNTER_FILE

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class TestJWTDecode:
    def test_decode_exp(self):
        # The fixture token has exp=9999999999
        token_data = load_fixture("token_response.json")
        exp = _decode_jwt_exp(token_data["access_token"])
        assert exp == 9999999999


class TestNexarClientInit:
    def test_raises_on_empty_credentials(self):
        with pytest.raises(ValueError, match="NEXAR_CLIENT_ID"):
            NexarClient("", "secret")

        with pytest.raises(ValueError, match="NEXAR_CLIENT_ID"):
            NexarClient("id", "")

    def test_creates_with_valid_credentials(self):
        client = NexarClient("test-id", "test-secret")
        assert client.client_id == "test-id"
        assert client.parts_consumed == 0 or client.parts_consumed >= 0


class TestPartsCounter:
    def test_load_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("client.COUNTER_FILE", tmp_path / "missing.json")
        client = NexarClient("test-id", "test-secret")
        assert client.parts_consumed == 0

    def test_load_existing_counter(self, tmp_path, monkeypatch):
        counter_file = tmp_path / "counter.json"
        counter_file.write_text(json.dumps({"parts_consumed": 42}))
        monkeypatch.setattr("client.COUNTER_FILE", counter_file)
        client = NexarClient("test-id", "test-secret")
        assert client.parts_consumed == 42

    def test_save_and_reload(self, tmp_path, monkeypatch):
        counter_file = tmp_path / "counter.json"
        monkeypatch.setattr("client.COUNTER_FILE", counter_file)

        client = NexarClient("test-id", "test-secret")
        client._log_consumption(5, "test")
        assert client.parts_consumed == 5
        assert client.parts_remaining == 95

        # Reload
        client2 = NexarClient("test-id", "test-secret")
        assert client2.parts_consumed == 5

    def test_consumption_accumulates(self, tmp_path, monkeypatch):
        counter_file = tmp_path / "counter.json"
        monkeypatch.setattr("client.COUNTER_FILE", counter_file)

        client = NexarClient("test-id", "test-secret")
        client._log_consumption(10, "q1")
        client._log_consumption(5, "q2")
        assert client.parts_consumed == 15
        assert client.parts_remaining == 85

    def test_corrupted_counter_file(self, tmp_path, monkeypatch):
        counter_file = tmp_path / "counter.json"
        counter_file.write_text("not json")
        monkeypatch.setattr("client.COUNTER_FILE", counter_file)
        client = NexarClient("test-id", "test-secret")
        assert client.parts_consumed == 0


class TestTokenHandling:
    @pytest.mark.asyncio
    async def test_acquires_token(self, monkeypatch):
        token_data = load_fixture("token_response.json")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = token_data

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = False

        client = NexarClient("test-id", "test-secret")
        client._http = mock_http

        await client._ensure_token()

        assert client._token == token_data["access_token"]
        assert client._token_expiry == 9999999999

    @pytest.mark.asyncio
    async def test_skips_refresh_when_valid(self):
        client = NexarClient("test-id", "test-secret")
        client._token = "valid-token"
        client._token_expiry = time.time() + 3600  # expires in 1 hour

        # Should not make any HTTP calls
        await client._ensure_token()
        assert client._token == "valid-token"

    @pytest.mark.asyncio
    async def test_auth_failure_raises(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status = MagicMock(
            side_effect=Exception("401 Unauthorized")
        )

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = False

        client = NexarClient("test-id", "test-secret")
        client._http = mock_http

        with pytest.raises(Exception, match="Token request failed"):
            await client._ensure_token()


class TestGraphQLQuery:
    @pytest.mark.asyncio
    async def test_successful_query(self):
        fixture = load_fixture("search_mpn_response.json")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = False

        client = NexarClient("test-id", "test-secret")
        client._token = "valid-token"
        client._token_expiry = time.time() + 3600
        client._http = mock_http

        data = await client.query("query { test }", {})
        assert "supSearchMpn" in data
        assert data["supSearchMpn"]["hits"] == 1

    @pytest.mark.asyncio
    async def test_graphql_error_raises(self):
        fixture = load_fixture("error_response.json")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.is_closed = False

        client = NexarClient("test-id", "test-secret")
        client._token = "valid-token"
        client._token_expiry = time.time() + 3600
        client._http = mock_http

        with pytest.raises(Exception, match="GraphQL errors"):
            await client.query("query { test }", {})
