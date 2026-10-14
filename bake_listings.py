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
LISTINGS_PINS = ROOT / "listings_pins.json"
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


def graphql_properties(**variables) -> list:
    payload = {
        "operationName": "Properties",
        "query": LISTINGS_QUERY,
        "variables": {
            "companyId": LP_COMPANY_ID,
            "archived": False,
            "offset": 0,
            "limit": 24,
            **variables,
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
    return body.get("data", {}).get("properties") or []


def load_listing_pins() -> list:
    if not LISTINGS_PINS.exists():
        return []
    try:
        data = json.loads(LISTINGS_PINS.read_text())
    except json.JSONDecodeError:
        return []
    listings = data.get("listings") if isinstance(data, dict) else data
    if not isinstance(listings, list):
        return []
    return [item for item in listings if isinstance(item, dict) and item.get("url")]


def pin_from_home_search(url: str) -> dict | None:
    request = urllib.request.Request(
        url,
        headers={
            "accept": "text/html",
            "user-agent": "DiscoverFBG-Listings/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, UnicodeError):
        return None
    marker = '<script id="__NEXT_DATA__" type="application/json">'
    start = html.find(marker)
    if start < 0:
        return None
    start += len(marker)
    end = html.find("</script>", start)
    if end < 0:
        return None
    try:
        payload = json.loads(html[start:end])
    except json.JSONDecodeError:
        return None
    listing = (payload.get("props") or {}).get("pageProps", {}).get("listing") or {}
    status = (listing.get("standardStatus") or listing.get("mlsStatus") or "").upper()
    if status not in {"ACTIVE", "FOR_SALE"}:
        return None
    photos = listing.get("photos") or []
    photo = ""
    if photos:
        photo = photos[0].get("photoUrl") or photos[0].get("thumbnailUrl") or ""
    city = (listing.get("city") or "").strip()
    state = (listing.get("state") or "").strip()
    postal = (listing.get("postalCode") or "").strip()
    name = (listing.get("unparsedAddress") or "").strip()
    place = " ".join(
        part for part in [", ".join(part for part in [city, state] if part), postal] if part
    )
    address = ", ".join(part for part in [name, place] if part)
    acres = listing.get("acreage")
    if acres not in (None, ""):
        acres = round(float(acres), 2)
    return {
        "id": listing.get("displayId") or listing.get("listingId") or "",
        "name": name,
        "status": "FOR_SALE",
        "salesPrice": listing.get("listPrice"),
        "fullAddress": address,
        "addressCity": city,
        "bedroomCount": listing.get("bedroomsTotal") or 0,
        "bathCount": listing.get("bathroomsTotal"),
        "livingSpaceSize": listing.get("livingArea"),
        "lotAreaSize": acres,
        "url": url.split("?")[0],
        "media": [{"mediumUrl": photo}] if photo else [],
    }


def pin_from_company_property(url: str) -> dict | None:
    slug = url.split("?")[0].rstrip("/").split("/")[-1]
    if not slug:
        return None
    terms = [slug]
    tail = slug.rsplit("-", 1)[-1]
    if tail and tail not in terms:
        terms.append(tail)
    for term in terms:
        try:
            props = graphql_properties(search=term)
        except (urllib.error.URLError, TimeoutError, RuntimeError):
            continue
        for item in props:
            if (item.get("slug") or "").strip() != slug:
                continue
            if item.get("status") != "FOR_SALE":
                return None
            live = dict(item)
            live["url"] = url.split("?")[0]
            return live
    return None


def resolve_pin(pin: dict) -> dict | None:
    url = (pin.get("url") or "").strip()
    live = None
    if "/home-search/listings/" in url:
        live = pin_from_home_search(url)
    elif "/properties/" in url:
        live = pin_from_company_property(url)
    else:
        live = pin_from_home_search(url) or pin_from_company_property(url)
    if live:
        merged = dict(pin)
        merged.update({key: value for key, value in live.items() if value not in (None, "", [])})
        merged["status"] = "FOR_SALE"
        return merged
    if (pin.get("status") or "FOR_SALE").upper() in {"ACTIVE", "FOR_SALE"}:
        return dict(pin)
    return None


def listing_keys(raw: dict) -> set[str]:
    keys = set()
    for value in (raw.get("id"), raw.get("slug"), raw.get("url"), raw.get("name")):
        text = str(value or "").strip().lower()
        if text:
            keys.add(text)
    return keys


def merge_pinned_listings(active: list) -> list:
    seen = set()
    for item in active:
        seen |= listing_keys(item)
    merged = list(active)
    for pin in load_listing_pins():
        resolved = resolve_pin(pin)
        if not resolved:
            print(f"Skipping pin (unavailable): {pin.get('url')}")
            continue
        keys = listing_keys(resolved)
        if keys & seen:
            continue
        seen |= keys
        merged.append(resolved)
        print(f"Pinned listing: {resolved.get('name') or resolved.get('url')}")
    return merged


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
        units = (raw.get("lotAreaUnits") or "").upper()
        if units in {"SQUARE_FEET", "SQFT", "SQ_FT"}:
            size = round(size / 43560, 2)
        if size >= 0.01:
            parts.append("1 acre" if round(size, 2) == 1 else f"{size:g} acres")
    if city:
        parts.append(city)
    return " · ".join(parts)


def normalize_listing(raw: dict) -> dict:
    media = raw.get("media") or []
    photo = ""
    if media:
        photo = media[0].get("mediumUrl") or media[0].get("largeUrl") or ""
    slug = (raw.get("slug") or "").strip()
    url = (raw.get("url") or "").strip()
    if not url:
        url = f"https://reataranchrealty.com/properties/{slug}" if slug else LISTINGS_PAGE
    return {
        "id": raw.get("id") or "",
        "title": (raw.get("name") or "").strip(),
        "price": raw.get("salesPrice"),
        "priceLabel": format_price(raw.get("salesPrice")),
        "address": (raw.get("fullAddress") or "").strip(),
        "city": (raw.get("addressCity") or "").strip(),
        "photo": photo,
        "url": url,
        "meta": listing_meta(raw),
    }


def fetch_listings() -> dict:
    props = graphql_properties(agentIds=[LP_AGENT_ID])
    active = [item for item in props if item.get("status") == "FOR_SALE"]
    active = merge_pinned_listings(active)
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
