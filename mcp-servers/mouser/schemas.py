"""Response validation and parsing for Mouser API responses."""

import re
from typing import Any, Dict, List, Optional


def validate_search_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a Mouser search response structure.

    Returns the SearchResults dict or raises ValueError.
    """
    errors = data.get("Errors", [])
    if errors:
        error_msgs = [
            f"{e.get('Code', 'Unknown')}: {e.get('Message', str(e))}"
            for e in errors
        ]
        raise ValueError(f"Mouser API errors: {'; '.join(error_msgs)}")

    if "SearchResults" not in data:
        raise ValueError("Missing 'SearchResults' in response")

    search_results = data["SearchResults"]

    if search_results is None:
        raise ValueError("SearchResults is null — likely an auth or request error")

    return search_results


def parse_availability(availability_str: str) -> int:
    """Parse stock count from Mouser availability string.

    Examples:
        "1234 In Stock" -> 1234
        "0" -> 0
        "In Stock" -> 0  (no number found)
        "" -> 0
        "None" -> 0
    """
    if not availability_str:
        return 0

    match = re.search(r"(\d[\d,]*)", availability_str)
    if match:
        return int(match.group(1).replace(",", ""))

    return 0


def parse_price(price_str: str) -> Optional[float]:
    """Parse price from Mouser price string.

    Examples:
        "$0.85" -> 0.85
        "€1.20" -> 1.20
        "1.50" -> 1.50
        "" -> None
    """
    if not price_str:
        return None

    # Strip any non-numeric characters except . and ,
    cleaned = re.sub(r"[^\d.,]", "", price_str)
    if not cleaned:
        return None

    # Handle European comma-as-decimal if no period present
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    else:
        # Remove thousand separators
        cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


_PRICE_BREAK_TARGETS = [1, 100, 1000]
_MAX_PRICE_BREAKS = 3


def extract_price_breaks(price_breaks: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Parse price breaks into structured data, keeping max 3 closest to qty 1, 100, 1000.

    Input: [{"Quantity": 1, "Price": "$0.85", "Currency": "USD"}, ...]
    Output: [{"quantity": 1, "price": 0.85}, ...]
    """
    if not price_breaks:
        return []

    parsed = []
    for pb in price_breaks:
        price = parse_price(pb.get("Price", ""))
        if price is not None:
            parsed.append({
                "quantity": pb.get("Quantity", 0),
                "price": price,
            })

    if len(parsed) <= _MAX_PRICE_BREAKS:
        return parsed

    # Pick breaks closest to target quantities
    selected = []
    used_indices = set()
    for target in _PRICE_BREAK_TARGETS:
        best_idx = min(
            range(len(parsed)),
            key=lambda i: abs(parsed[i]["quantity"] - target),
        )
        if best_idx not in used_indices:
            used_indices.add(best_idx)
            selected.append(parsed[best_idx])
    return selected


def extract_lifecycle(lifecycle_str: Optional[str]) -> str:
    """Categorize lifecycle status string.

    Returns one of: 'active', 'nrnd', 'obsolete', 'unknown'.
    Note: Mouser's LifeCycle field is often empty.
    """
    if not lifecycle_str:
        return "unknown"

    raw = lifecycle_str.strip().lower()

    if not raw:
        return "unknown"

    if raw in ("active", "production", "new product"):
        return "active"
    elif raw in ("nrnd", "not recommended for new designs", "not recommended"):
        return "nrnd"
    elif raw in ("obsolete", "end of life", "eol", "discontinued"):
        return "obsolete"
    elif raw:
        return raw  # pass through unrecognized values

    return "unknown"


def _strip_empty(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None, empty string, empty list, empty dict, or 0 values."""
    return {
        k: v for k, v in d.items()
        if v is not None and v != "" and v != [] and v != {}
    }


def normalize_part(part: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Mouser part response into a compact structure.

    Strips empty fields to reduce response size.
    """
    price_breaks = extract_price_breaks(part.get("PriceBreaks"))

    result = {
        "mpn": part.get("ManufacturerPartNumber", ""),
        "manufacturer": part.get("Manufacturer", ""),
        "description": part.get("Description", ""),
        "availability": parse_availability(part.get("Availability", "")),
        "lifecycle": extract_lifecycle(part.get("LifeCycle")),
        "rohs_status": part.get("ROHSStatus", ""),
        "lead_time": part.get("LeadTime", ""),
        "datasheet_url": part.get("DataSheetUrl", ""),
        "product_detail_url": part.get("ProductDetailUrl", ""),
        "price_breaks": price_breaks,
        "unit_price": price_breaks[0]["price"] if price_breaks else None,
    }

    return _strip_empty(result)
