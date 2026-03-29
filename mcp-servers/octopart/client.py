"""Nexar API client with OAuth2 auth, token caching, and part consumption tracking."""

import base64
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

NEXAR_URL = "https://api.nexar.com/graphql/"
TOKEN_URL = "https://identity.nexar.com/connect/token"
COUNTER_FILE = Path(__file__).parent / ".parts_counter.json"

LIFECYCLE_FREE_LIMIT = 100  # Evaluation tier lifetime limit


def _decode_jwt_exp(token: str) -> float:
    """Extract expiry timestamp from a JWT without verification."""
    payload = token.split(".")[1]
    payload += "=" * (4 - len(payload) % 4)
    decoded = json.loads(base64.urlsafe_b64decode(payload))
    return float(decoded["exp"])


class NexarClient:
    def __init__(self, client_id: str, client_secret: str):
        if not client_id or not client_secret:
            raise ValueError(
                "NEXAR_CLIENT_ID and NEXAR_CLIENT_SECRET must be set. "
                "See README.md for how to get credentials."
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._http: Optional[httpx.AsyncClient] = None
        self._parts_consumed = self._load_counter()

    def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=90.0)
        return self._http

    # --- Part consumption counter ---

    def _load_counter(self) -> int:
        if COUNTER_FILE.exists():
            try:
                data = json.loads(COUNTER_FILE.read_text())
                return data.get("parts_consumed", 0)
            except (json.JSONDecodeError, KeyError):
                return 0
        return 0

    def _save_counter(self):
        COUNTER_FILE.write_text(json.dumps({
            "parts_consumed": self._parts_consumed,
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, indent=2))

    def _log_consumption(self, new_parts: int, query_type: str):
        self._parts_consumed += new_parts
        self._save_counter()
        remaining = LIFECYCLE_FREE_LIMIT - self._parts_consumed
        print(
            f"[NEXAR] +{new_parts} parts ({query_type}) | "
            f"Total: {self._parts_consumed}/{LIFECYCLE_FREE_LIMIT} | "
            f"Remaining: {remaining}",
            file=sys.stderr,
        )
        if self._parts_consumed >= 95:
            print(
                f"[NEXAR] CRITICAL: Only {remaining} matched parts remaining!",
                file=sys.stderr,
            )
        elif self._parts_consumed >= 75:
            print(
                f"[NEXAR] WARNING: {remaining} matched parts remaining.",
                file=sys.stderr,
            )
        elif self._parts_consumed >= 50:
            print(
                f"[NEXAR] INFO: {remaining} matched parts remaining.",
                file=sys.stderr,
            )

    @property
    def parts_consumed(self) -> int:
        return self._parts_consumed

    @property
    def parts_remaining(self) -> int:
        return max(0, LIFECYCLE_FREE_LIMIT - self._parts_consumed)

    # --- Authentication ---

    async def _ensure_token(self):
        """Acquire or refresh the OAuth2 token if needed."""
        if self._token and time.time() < self._token_expiry - 300:
            return

        http = self._get_http()
        response = await http.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "supply.domain",
            },
        )
        if response.status_code != 200:
            raise Exception(
                f"Token request failed ({response.status_code}): {response.text}"
            )

        token_data = response.json()
        if "access_token" not in token_data:
            raise Exception(f"No access_token in response: {token_data}")

        self._token = token_data["access_token"]
        self._token_expiry = _decode_jwt_exp(self._token)
        print(
            f"[NEXAR] Token acquired, expires {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._token_expiry))}",
            file=sys.stderr,
        )

    # --- GraphQL query ---

    async def query(self, graphql: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GraphQL query and return the data payload."""
        await self._ensure_token()

        http = self._get_http()
        response = await http.post(
            NEXAR_URL,
            json={"query": graphql, "variables": variables},
            headers={"token": self._token},
        )

        if response.status_code != 200:
            raise Exception(
                f"GraphQL request failed ({response.status_code}): {response.text}"
            )

        body = response.json()

        if "errors" in body:
            msgs = [e.get("message", str(e)) for e in body["errors"]]
            raise Exception(f"GraphQL errors: {'; '.join(msgs)}")

        return body.get("data", {})

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()
