"""MCP tool definitions for the Octopart/Nexar server."""

import json
from typing import Optional

from client import NexarClient
from queries import CHECK_LIFECYCLE, MULTI_MATCH, SEARCH_MPN, SEARCH_PARTS
from schemas import (
    compress_multi_match,
    compress_part,
    compress_result_set,
    count_parts_in_multi_match,
    count_parts_in_response,
    extract_lifecycle,
    validate_multi_match_response,
    validate_search_response,
)


def register_tools(mcp, client: NexarClient):
    """Register all Octopart tools on the given FastMCP server."""

    @mcp.tool()
    async def search_parts(
        query: str,
        limit: int = 3,
        currency: str = "USD",
        country: str = "US",
    ) -> str:
        """Search for electronic parts by description (e.g. '3 ohm resistor', '100uF capacitor').

        Uses Octopart's general search. Returns compressed pricing, stock, and key specs.
        Each result consumes 1 matched part from the Nexar quota.

        Args:
            query: Descriptive search query
            limit: Max results to return (default 3, keep low to conserve quota)
            currency: ISO currency code (default USD)
            country: ISO country code (default US)
        """
        variables = {"q": query, "start": 0, "limit": limit}
        if currency:
            variables["currency"] = currency
        if country:
            variables["country"] = country

        data = await client.query(SEARCH_PARTS, variables)
        result_set = validate_search_response(data, "supSearch")
        parts_count = count_parts_in_response(data, "supSearch")
        client._log_consumption(parts_count, f"search_parts({query!r})")

        return json.dumps(compress_result_set(result_set))

    @mcp.tool()
    async def search_mpn(
        mpn: str,
        limit: int = 3,
        currency: str = "USD",
        country: str = "US",
    ) -> str:
        """Search for parts by Manufacturer Part Number (MPN). Supports partial matches.

        Use this when you know the exact or partial MPN. Returns compressed pricing, stock,
        and key specs. Each result consumes 1 matched part from the Nexar quota.

        Args:
            mpn: Manufacturer part number (exact or partial)
            limit: Max results (default 3, keep low to conserve quota)
            currency: ISO currency code (default USD)
            country: ISO country code (default US)
        """
        variables = {"q": mpn, "limit": limit}
        if currency:
            variables["currency"] = currency
        if country:
            variables["country"] = country

        data = await client.query(SEARCH_MPN, variables)
        result_set = validate_search_response(data, "supSearchMpn")
        parts_count = count_parts_in_response(data, "supSearchMpn")
        client._log_consumption(parts_count, f"search_mpn({mpn!r})")

        return json.dumps(compress_result_set(result_set))

    @mcp.tool()
    async def get_part_details(
        mpn: str,
        currency: str = "USD",
        country: str = "US",
    ) -> str:
        """Get detailed information for a specific MPN including top sellers, pricing, and key specs.

        Returns the single best match. Consumes 1 matched part from the Nexar quota.

        Args:
            mpn: Exact manufacturer part number
            currency: ISO currency code (default USD)
            country: ISO country code (default US)
        """
        variables = {"q": mpn, "limit": 1}
        if currency:
            variables["currency"] = currency
        if country:
            variables["country"] = country

        data = await client.query(SEARCH_MPN, variables)
        result_set = validate_search_response(data, "supSearchMpn")
        parts_count = count_parts_in_response(data, "supSearchMpn")
        client._log_consumption(parts_count, f"get_part_details({mpn!r})")

        results = result_set.get("results", [])
        if not results:
            return json.dumps({"error": f"No part found for MPN: {mpn}"})

        part = compress_part(results[0].get("part", {}))

        return json.dumps({"hits": result_set.get("hits", 0), "part": part})

    @mcp.tool()
    async def multi_match(
        mpns: list[str],
        currency: str = "USD",
        country: str = "US",
    ) -> str:
        """Look up multiple MPNs in a single query. More efficient than individual searches.

        Each MPN that returns results consumes matched parts from the Nexar quota.

        Args:
            mpns: List of manufacturer part numbers to look up
            currency: ISO currency code (default USD)
            country: ISO country code (default US)
        """
        queries = [{"mpn": mpn, "limit": 1} for mpn in mpns]
        variables: dict = {"queries": queries}
        if currency:
            variables["currency"] = currency
        if country:
            variables["country"] = country

        data = await client.query(MULTI_MATCH, variables)
        validate_multi_match_response(data)
        parts_count = count_parts_in_multi_match(data)
        client._log_consumption(parts_count, f"multi_match({len(mpns)} MPNs)")

        return json.dumps(compress_multi_match(data["supMultiMatch"]))

    @mcp.tool()
    async def check_lifecycle(mpn: str) -> str:
        """Check the lifecycle status of a component by MPN.

        Returns a simple status: 'active', 'nrnd', 'obsolete', or 'unknown'.
        Consumes 1 matched part from the Nexar quota.

        Args:
            mpn: Exact manufacturer part number
        """
        variables = {"q": mpn}

        data = await client.query(CHECK_LIFECYCLE, variables)
        result_set = validate_search_response(data, "supSearchMpn")
        parts_count = count_parts_in_response(data, "supSearchMpn")
        client._log_consumption(parts_count, f"check_lifecycle({mpn!r})")

        results = result_set.get("results", [])
        if not results:
            return json.dumps({
                "mpn": mpn,
                "lifecycle": "unknown",
                "note": "No part found for this MPN",
            })

        part = results[0].get("part", {})
        lifecycle = extract_lifecycle(part.get("specs"))

        return json.dumps({
            "mpn": part.get("mpn", mpn),
            "manufacturer": part.get("manufacturer", {}).get("name", "unknown"),
            "description": part.get("shortDescription", ""),
            "lifecycle": lifecycle,
        })

    @mcp.tool()
    async def get_quota_status() -> str:
        """Check how many matched parts have been consumed from the Nexar quota.

        Does NOT consume any matched parts.
        """
        return json.dumps({
            "parts_consumed": client.parts_consumed,
            "parts_remaining": client.parts_remaining,
            "lifetime_limit": 100,
            "note": "Nexar Evaluation tier: 100 matched parts lifetime",
        })
