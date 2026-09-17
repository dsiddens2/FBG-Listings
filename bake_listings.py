#!/usr/bin/env python3
"""Refresh the shared Discover FBG Reata listings snapshot."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
LISTINGS_OUT = DOCS / "listings.json"
LISTINGS_OVERRIDES = ROOT / "listings_overrides.json"
LISTINGS_PAGE = "https://reataranchrealty.com/agents/doug-siddens"
LISTINGS_ENDPOINT = "https://reataranchrealty.com/api-gw/graphql"
LP_COMPANY_ID = "d35b0af8-248c-413b-b5f9-d720b12d0bc1"
LP_AGENT_ID = "b459b58a-06e5-4f6a-8e91-dcdca5fb0dc9"
LISTINGS_QUERY = """
query Properties($agentIds: [ID!], $companyId: String, $archived: Boolean, $offset: Int, $limit: Int) {
  properties(agentIds: $agentIds, companyId: $companyId, archived: $archived, offset: $offset, limit: $limit) {
    id
    name
    status
    salesPrice
    fullAddress
    addressCity
    bedroomCount
    bathCount
    livingSpaceSize
    lotAreaSize
    lotAreaUnits
    slug
    media { mediumUrl largeUrl }
  }
}
""".strip()


def format_price(value) -> str:
    if value in (None, ""):
        return "Price on request"
    number = int(round(float(value)))
    return f"${number:,}"


def load_listing_overrides() -> dict:
    if not LISTINGS_OVERRIDES.exists():
        return {}
    try:
        data = json.loads(LISTINGS_OVERRIDES.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def listing_override_for(keys: list) -> dict:
    overrides = load_listing_overrides()
    extra = {}
    for key in keys:
        value = (key or "").strip()
        if value and isinstance(overrides.get(value), dict):
            extra.update(overrides[value])
    return extra


def apply_raw_listing_overrides(raw: dict) -> dict:
    merged = dict(raw)
    slug = (raw.get("slug") or "").strip()
    extra = listing_override_for([raw.get("id"), slug, raw.get("name")])
    if extra:
        merged.update(extra)
    return merged


def listing_meta(raw: dict) -> str:
    parts = []
    beds = raw.get("bedroomCount") or 0
    baths = raw.get("bathCount")
    sqft = raw.get("livingSpaceSize")
    acres = raw.get("lotAreaSize")
    city = (raw.get("addressCity") or "").strip()
    if beds:
        parts.append(f"{int(beds)} bd")
    if baths:
        count = float(baths)
        parts.append(f"{int(count) if count == int(count) else count:g} ba")
    if sqft:
        parts.append(f"{int(float(sqft)):,} sq ft")
    if acres:
        size = float(acres)
        parts.append("1 acre" if size == 1 else f"{size:g} acres")
    if city:
        parts.append(city)
    return " · ".join(parts)


def normalize_listing(raw: dict) -> dict:
    media = raw.get("media") or []
    photo = ""
    if media:
        photo = media[0].get("mediumUrl") or media[0].get("largeUrl") or ""
    slug = (raw.get("slug") or "").strip()
    return {
        "id": raw.get("id") or "",
        "title": (raw.get("name") or "").strip(),
        "price": raw.get("salesPrice"),
        "priceLabel": format_price(raw.get("salesPrice")),
        "address": (raw.get("fullAddress") or "").strip(),
        "city": (raw.get("addressCity") or "").strip(),
        "photo": photo,
        "url": f"https://reataranchrealty.com/properties/{slug}" if slug else LISTINGS_PAGE,
        "meta": listing_meta(raw),
    }


def fetch_listings() -> dict:
    payload = {
        "operationName": "Properties",
        "query": LISTINGS_QUERY,
        "variables": {
            "companyId": LP_COMPANY_ID,
            "agentIds": [LP_AGENT_ID],
            "archived": False,
            "offset": 0,
            "limit": 24,
        },
    }
    request = urllib.request.Request(
        LISTINGS_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": "DiscoverFBG-Listings/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    errors = body.get("errors") or []
    if errors:
        raise RuntimeError(errors[0].get("message") or "listings GraphQL error")
    props = body.get("data", {}).get("properties") or []
    active = [item for item in props if item.get("status") == "FOR_SALE"]
    active.sort(key=lambda item: float(item.get("salesPrice") or 0), reverse=True)
    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": LISTINGS_PAGE,
        "listings": [normalize_listing(apply_raw_listing_overrides(item)) for item in active],
    }


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    data = fetch_listings()
    LISTINGS_OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Wrote {len(data['listings'])} listings → {LISTINGS_OUT}")


if __name__ == "__main__":
    main()
