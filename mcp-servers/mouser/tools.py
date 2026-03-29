"""MCP tool definitions for the Mouser server."""

import json

from client import MouserClient
from schemas import normalize_part, validate_search_response


def register_tools(mcp, client: MouserClient):
    """Register all Mouser tools on the given FastMCP server."""

    @mcp.tool()
    async def search_parts(
        query: str,
        limit: int = 10,
        search_options: str = "None",
    ) -> str:
        """Search for electronic parts by keyword on Mouser.

        Returns pricing, stock, and basic specs. Good for general searches like
        '100uF capacitor', 'STM32F4', 'logarithmic potentiometer'.

        Args:
            query: Search keyword(s)
            limit: Max results to return (max 50, default 10)
            search_options: Filter: "None", "Rohs", "InStock", "RohsAndInStock"
        """
        data = await client.search_keyword(
            keyword=query,
            records=limit,
            search_options=search_options,
        )
        search_results = validate_search_response(data)
        parts = search_results.get("Parts") or []
        normalized = [normalize_part(p) for p in parts]

        return json.dumps({
            "total_results": search_results.get("NumberOfResult", 0),
            "returned": len(normalized),
            "parts": normalized,
        }, indent=2)

    @mcp.tool()
    async def search_mpn(
        mpn: str,
        match_type: str = "None",
    ) -> str:
        """Search for parts by Manufacturer Part Number (MPN) on Mouser.

        Use this when you know the exact or partial MPN. Supports exact match,
        begins-with, and contains matching.

        Args:
            mpn: Manufacturer part number. Use pipe '|' to search multiple (max 10).
            match_type: "None" (auto), "Exact", "BeginsWith", "Contains"
        """
        data = await client.search_part_number(
            part_number=mpn,
            part_search_options=match_type,
        )
        search_results = validate_search_response(data)
        parts = search_results.get("Parts") or []
        normalized = [normalize_part(p) for p in parts]

        return json.dumps({
            "total_results": search_results.get("NumberOfResult", 0),
            "returned": len(normalized),
            "parts": normalized,
        }, indent=2)

    @mcp.tool()
    async def get_part_details(mpn: str) -> str:
        """Get detailed information for a specific MPN from Mouser.

        Returns the exact match with full pricing, stock, and attributes.

        Args:
            mpn: Exact manufacturer part number
        """
        data = await client.search_part_number(
            part_number=mpn,
            part_search_options="Exact",
        )
        search_results = validate_search_response(data)
        parts = search_results.get("Parts") or []

        if not parts:
            return json.dumps({"error": f"No part found for MPN: {mpn}"})

        normalized = normalize_part(parts[0])
        return json.dumps({"part": normalized}, indent=2)

    @mcp.tool()
    async def search_manufacturer(
        keyword: str,
        manufacturer: str,
        limit: int = 10,
        search_options: str = "None",
    ) -> str:
        """Search for parts by keyword filtered by manufacturer on Mouser.

        Useful when you need parts from a specific manufacturer.

        Args:
            keyword: Search keyword(s)
            manufacturer: Manufacturer name (e.g. "Texas Instruments", "Murata")
            limit: Max results to return (max 50, default 10)
            search_options: Filter: "None", "Rohs", "InStock", "RohsAndInStock"
        """
        data = await client.search_keyword_and_manufacturer(
            keyword=keyword,
            manufacturer_name=manufacturer,
            records=limit,
            search_options=search_options,
        )
        search_results = validate_search_response(data)
        parts = search_results.get("Parts") or []
        normalized = [normalize_part(p) for p in parts]

        return json.dumps({
            "total_results": search_results.get("NumberOfResult", 0),
            "returned": len(normalized),
            "parts": normalized,
        }, indent=2)

    @mcp.tool()
    async def get_rate_limit_status() -> str:
        """Check remaining daily API requests for Mouser.

        Does NOT consume any API requests.
        """
        return json.dumps({
            "daily_requests_remaining": client.daily_requests_remaining,
            "daily_limit": 1000,
            "per_minute_limit": 30,
            "note": "Mouser API: 30 req/min, 1000 req/day",
        })
