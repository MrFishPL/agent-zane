"""Response validation and compression for Nexar API responses."""

from typing import Any, Dict, List, Optional


# Specs worth keeping — everything else is noise for the agent
_KEY_SPEC_SHORTNAMES = {
    "lifecyclestatus", "case_package", "packagecase",
    "operatingtemperature", "temperaturerange",
    "tolerance", "resistance", "capacitance",
    "voltage", "outputvoltage", "ratedvoltage", "voltagerated",
    "current", "outputcurrent", "ratedcurrent",
    "power", "ratedpower", "inductance", "frequency",
}

# Target qty tiers for price break selection
_PRICE_BREAK_TARGETS = [1, 100, 1000]
_MAX_SELLERS = 5
_MAX_PRICE_BREAKS = 3


def validate_search_response(data: Dict[str, Any], query_key: str) -> Dict[str, Any]:
    """Validate a supSearch or supSearchMpn response structure.

    Returns the validated data (passthrough) or raises ValueError.
    """
    if query_key not in data:
        raise ValueError(f"Missing '{query_key}' in response data")

    result_set = data[query_key]

    if "results" not in result_set and "parts" not in result_set:
        raise ValueError(f"Missing 'results' or 'parts' in {query_key} response")

    return result_set


def validate_multi_match_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validate a supMultiMatch response. Returns list of match result sets."""
    if "supMultiMatch" not in data:
        raise ValueError("Missing 'supMultiMatch' in response data")

    return data["supMultiMatch"]


def count_parts_in_response(data: Dict[str, Any], query_key: str) -> int:
    """Count the number of matched parts in a response for quota tracking."""
    result_set = data.get(query_key, {})

    # supSearch / supSearchMpn use results[].part
    results = result_set.get("results", [])
    if results:
        return len(results)

    # supMultiMatch uses parts[]
    parts = result_set.get("parts", [])
    if parts:
        return len(parts)

    return 0


def count_parts_in_multi_match(data: Dict[str, Any]) -> int:
    """Count total parts across all supMultiMatch result sets."""
    match_sets = data.get("supMultiMatch", [])
    total = 0
    for match_set in match_sets:
        parts = match_set.get("parts", [])
        total += len(parts)
    return total


def extract_lifecycle(specs: Optional[List[Dict[str, Any]]]) -> str:
    """Extract lifecycle status from a part's specs list.

    Returns one of: 'active', 'nrnd', 'obsolete', 'unknown'.
    """
    if not specs:
        return "unknown"

    for spec in specs:
        attr = spec.get("attribute", {})
        if attr.get("shortname") == "lifecyclestatus":
            raw = (spec.get("displayValue") or "").strip().lower()
            # Nexar sometimes appends annotations like "(last updated: 20 hours ago)"
            # Strip parenthetical suffixes before matching
            core = raw.split("(")[0].strip() if "(" in raw else raw
            if core in ("production", "active", "new product"):
                return "active"
            elif core in (
                "not recommended for new designs",
                "nrnd",
                "not recommended",
            ):
                return "nrnd"
            elif core in ("obsolete", "end of life", "eol", "discontinued"):
                return "obsolete"
            elif core:
                return core  # return the cleaned value if we can't categorize it
            return "unknown"

    return "unknown"


def _pick_best_price_breaks(prices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Select up to 3 price breaks closest to qty 1, 100, 1000."""
    if not prices:
        return []
    if len(prices) <= _MAX_PRICE_BREAKS:
        return [_slim_price(p) for p in prices]

    selected = []
    used_indices = set()
    for target in _PRICE_BREAK_TARGETS:
        best_idx = min(
            range(len(prices)),
            key=lambda i: abs(prices[i].get("quantity", 0) - target),
        )
        if best_idx not in used_indices:
            used_indices.add(best_idx)
            selected.append(_slim_price(prices[best_idx]))
    return selected


def _slim_price(p: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only quantity + price from a price break."""
    return {"quantity": p["quantity"], "price": p["price"]}


def _compress_offer(offer: Dict[str, Any]) -> Dict[str, Any]:
    """Compress a single seller offer."""
    result = {
        "sku": offer.get("sku"),
        "stock": offer.get("inventoryLevel"),
        "moq": offer.get("moq"),
        "prices": _pick_best_price_breaks(offer.get("prices") or []),
    }
    url = offer.get("clickUrl")
    if url:
        result["url"] = url
    return _strip_empty(result)


def _compress_sellers(sellers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep top 5 sellers by lowest unit price, compress their offers."""
    if not sellers:
        return []

    # Score each seller by lowest price across all offers
    def _min_price(seller):
        best = float("inf")
        for offer in seller.get("offers") or []:
            for p in offer.get("prices") or []:
                price = p.get("price")
                if price is not None and price < best:
                    best = price
        return best

    sorted_sellers = sorted(sellers, key=_min_price)[:_MAX_SELLERS]

    result = []
    for seller in sorted_sellers:
        compressed = {
            "seller": seller.get("company", {}).get("name", ""),
            "offers": [_compress_offer(o) for o in (seller.get("offers") or [])],
        }
        result.append(_strip_empty(compressed))
    return result


def _compress_specs(specs: List[Dict[str, Any]]) -> Dict[str, str]:
    """Extract key specs into a flat dict, skip the rest."""
    if not specs:
        return {}
    result = {}
    for spec in specs:
        attr = spec.get("attribute", {})
        shortname = attr.get("shortname", "")
        if shortname in _KEY_SPEC_SHORTNAMES:
            val = spec.get("displayValue")
            if val:
                result[shortname] = val
    return result


def _strip_empty(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None, empty string, empty list, or empty dict values."""
    return {k: v for k, v in d.items() if v is not None and v != "" and v != [] and v != {}}


def compress_part(part: Dict[str, Any]) -> Dict[str, Any]:
    """Compress a raw Nexar part into a compact representation."""
    lifecycle = extract_lifecycle(part.get("specs"))
    specs = _compress_specs(part.get("specs") or [])
    sellers = _compress_sellers(part.get("sellers") or [])

    result = {
        "mpn": part.get("mpn"),
        "manufacturer": part.get("manufacturer", {}).get("name"),
        "description": part.get("shortDescription"),
        "totalAvail": part.get("totalAvail"),
        "lifecycle": lifecycle,
        "specs": specs,
        "sellers": sellers,
        "octopartUrl": part.get("octopartUrl"),
    }

    datasheet = part.get("bestDatasheet", {})
    if datasheet and datasheet.get("url"):
        result["datasheetUrl"] = datasheet["url"]

    median = part.get("medianPrice1000", {})
    if median and median.get("price") is not None:
        result["medianPrice1000"] = median["price"]

    return _strip_empty(result)


def compress_result_set(result_set: Dict[str, Any]) -> Dict[str, Any]:
    """Compress an entire supSearch/supSearchMpn result set."""
    compressed = {"hits": result_set.get("hits", 0)}

    results = result_set.get("results")
    if results is not None:
        compressed["results"] = [
            {"part": compress_part(r.get("part", {}))} for r in results
        ]

    parts = result_set.get("parts")
    if parts is not None:
        compressed["parts"] = [compress_part(p) for p in parts]

    return compressed


def compress_multi_match(match_sets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compress supMultiMatch result sets."""
    return [compress_result_set(ms) for ms in match_sets]
