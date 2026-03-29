"""Mouser REST API client with rate limiting."""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

BASE_URL = "https://api.mouser.com/api/v1"
BASE_URL_V2 = "https://api.mouser.com/api/v2"

# Rate limits: 30 req/min, 1000 req/day
RATE_LIMIT_PER_MINUTE = 30
RATE_LIMIT_PER_DAY = 1000

COUNTER_FILE = Path(__file__).parent / ".request_counter.json"


class MouserClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError(
                "MOUSER_API_KEY must be set. "
                "See README.md for how to get credentials."
            )
        self.api_key = api_key
        self._http: Optional[httpx.AsyncClient] = None
        self._request_timestamps: List[float] = []
        self._daily_count, self._daily_date = self._load_counter()

    def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    # --- Rate limiting ---

    def _load_counter(self):
        """Load daily request counter from disk."""
        today = time.strftime("%Y-%m-%d")
        if COUNTER_FILE.exists():
            try:
                data = json.loads(COUNTER_FILE.read_text())
                if data.get("date") == today:
                    return data.get("count", 0), today
            except (json.JSONDecodeError, KeyError):
                pass
        return 0, today

    def _save_counter(self):
        COUNTER_FILE.write_text(json.dumps({
            "date": self._daily_date,
            "count": self._daily_count,
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, indent=2))

    def _check_rate_limits(self):
        """Check and enforce rate limits. Raises if daily limit exceeded."""
        today = time.strftime("%Y-%m-%d")
        if today != self._daily_date:
            self._daily_count = 0
            self._daily_date = today

        if self._daily_count >= RATE_LIMIT_PER_DAY:
            raise Exception(
                f"Mouser daily rate limit reached ({RATE_LIMIT_PER_DAY} requests/day). "
                "Try again tomorrow."
            )

        # Clean up timestamps older than 60 seconds
        now = time.time()
        self._request_timestamps = [
            t for t in self._request_timestamps if now - t < 60
        ]

        if len(self._request_timestamps) >= RATE_LIMIT_PER_MINUTE:
            wait_time = 60 - (now - self._request_timestamps[0])
            raise Exception(
                f"Mouser per-minute rate limit reached ({RATE_LIMIT_PER_MINUTE}/min). "
                f"Wait {wait_time:.0f}s before retrying."
            )

    def _log_request(self, endpoint: str):
        """Record a request for rate limit tracking."""
        self._request_timestamps.append(time.time())
        self._daily_count += 1
        self._save_counter()
        print(
            f"[MOUSER] Request: {endpoint} | "
            f"Today: {self._daily_count}/{RATE_LIMIT_PER_DAY}",
            file=sys.stderr,
        )

    @property
    def daily_requests_remaining(self) -> int:
        today = time.strftime("%Y-%m-%d")
        if today != self._daily_date:
            return RATE_LIMIT_PER_DAY
        return max(0, RATE_LIMIT_PER_DAY - self._daily_count)

    # --- API methods ---

    async def search_keyword(
        self,
        keyword: str,
        records: int = 10,
        starting_record: int = 0,
        search_options: str = "None",
    ) -> Dict[str, Any]:
        """Search parts by keyword.

        Args:
            keyword: Search term
            records: Max results (max 50)
            starting_record: Pagination offset
            search_options: "None", "Rohs", "InStock", "RohsAndInStock"
        """
        self._check_rate_limits()

        body = {
            "SearchByKeywordRequest": {
                "keyword": keyword,
                "records": min(records, 50),
                "startingRecord": starting_record,
                "searchOptions": search_options,
                "searchWithYourSignUpLanguage": "en",
            }
        }

        url = f"{BASE_URL}/search/keyword?apiKey={self.api_key}"
        result = await self._post(url, body)
        self._log_request(f"search/keyword({keyword!r})")
        return result

    async def search_part_number(
        self,
        part_number: str,
        part_search_options: str = "None",
    ) -> Dict[str, Any]:
        """Search by Mouser part number or MPN.

        Args:
            part_number: MPN or Mouser part number. Pipe-separated for multiple (max 10).
            part_search_options: "None", "Exact", "BeginsWith", "Contains"
        """
        self._check_rate_limits()

        body = {
            "SearchByPartRequest": {
                "mouserPartNumber": part_number,
                "partSearchOptions": part_search_options,
            }
        }

        url = f"{BASE_URL}/search/partnumber?apiKey={self.api_key}"
        result = await self._post(url, body)
        self._log_request(f"search/partnumber({part_number!r})")
        return result

    async def search_keyword_and_manufacturer(
        self,
        keyword: str,
        manufacturer_name: str,
        records: int = 10,
        page_number: int = 1,
        search_options: str = "None",
    ) -> Dict[str, Any]:
        """Search by keyword filtered by manufacturer.

        Args:
            keyword: Search term
            manufacturer_name: Manufacturer name filter
            records: Max results (max 50)
            page_number: Page number (1-based)
            search_options: "None", "Rohs", "InStock", "RohsAndInStock"
        """
        self._check_rate_limits()

        body = {
            "SearchByKeywordMfrNameRequest": {
                "keyword": keyword,
                "manufacturerName": manufacturer_name,
                "records": min(records, 50),
                "pageNumber": page_number,
                "searchOptions": search_options,
                "searchWithYourSignUpLanguage": False,
                "mouserPaysCustomsAndDuties": False,
            }
        }

        url = f"{BASE_URL_V2}/search/keywordandmanufacturer?apiKey={self.api_key}"
        result = await self._post(url, body)
        self._log_request(f"search/keywordandmanufacturer({keyword!r}, {manufacturer_name!r})")
        return result

    async def _post(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a POST request and return JSON response."""
        http = self._get_http()
        response = await http.post(
            url,
            json=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        if response.status_code != 200:
            raise Exception(
                f"Mouser API request failed ({response.status_code}): {response.text}"
            )

        return response.json()

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()
