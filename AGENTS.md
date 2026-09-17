# Discover FBG listings snapshot

Canonical Reata FOR_SALE JSON for every Discover FBG finder. GitHub Pages publishes **`docs/listings.json`**.

Public URL: `https://dsiddens2.github.io/FBG-Listings/listings.json`

## Refresh
1. Edit `listings_overrides.json` for MLS corrections (sq ft, etc.)
2. `python3 bake_listings.py`
3. That writes `docs/listings.json`. A daily GitHub Action does the same.

Do not copy this JSON into finder repos. Finders fetch the public URL. Hide the listings row if the fetch is empty.
