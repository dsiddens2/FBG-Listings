# Discover FBG listings snapshot

Shared Reata Ranch Realty FOR_SALE snapshot for Discover FBG finders. Driving Roads, Winery Finder, Restaurant Finder, and later tools all fetch this JSON. Do not copy it into the finder repos.

## Public feed

https://dsiddens2.github.io/FBG-Listings/listings.json

Fields: `title`, `priceLabel`, `photo`, `url`, `meta`, `city`. Hide a listings row if the fetch is empty.

See-all search (not the agent bio):

https://reataranchrealty.com/home-search/listings?sortBy=LIST_PRICE&regions=%5B%7B%22regionId%22%3A%22d2b75ba0-dc7d-48d4-8cb5-1e5a823eda96%22%2C%22address%22%3A%22Fredericksburg%2C+TX%2C+USA%22%7D%5D&center=%7B%22lat%22%3A30.2544044893871%2C%22lng%22%3A-98.889515%7D&boundary=%5B%5B%5B30.58599013173766%2C-99.20846183837891%5D%2C%5B30.58599013173766%2C-98.5705681616211%5D%2C%5B29.921695749509272%2C-98.5705681616211%5D%2C%5B29.921695749509272%2C-99.20846183837891%5D%2C%5B30.58599013173766%2C-99.20846183837891%5D%5D%5D&cityName=Fredericksburg&stateName=TX

## Standalone embed

Paste `squarespace-embed.html` into a Squarespace Code Block on any page. It loads `embed.css` / `embed.js` from this repo, shuffles listings on each visit, and hides itself if the feed is empty. See-all still goes to the Fredericksburg home-search URL above, not the agent bio.

Optional attributes on `.fbg-listings-embed`:

- `data-theme="light"` or `dark`
- `data-heading="Browse local listings"` (`off` hides the heading)
- `data-sub="Optional line under the heading"`
- `data-align="center"` for a homepage-style centered heading
- `data-columns="3"` or `4`
- `data-limit="3"` to show fewer shuffled cards

Preview: `docs/embed.html`.

## Refresh

```
python3 bake_listings.py
```

A GitHub Action runs that daily. Put MLS corrections in `listings_overrides.json` so the next refresh keeps them.
