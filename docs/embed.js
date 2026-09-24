(function () {
  if (window.__fbgListingsEmbedLoaded) return;
  window.__fbgListingsEmbedLoaded = true;

  var LISTINGS_JSON = "https://dsiddens2.github.io/FBG-Listings/listings.json";
  var LISTINGS_SEARCH =
    "https://reataranchrealty.com/home-search/listings?sortBy=LIST_PRICE&regions=%5B%7B%22regionId%22%3A%22d2b75ba0-dc7d-48d4-8cb5-1e5a823eda96%22%2C%22address%22%3A%22Fredericksburg%2C+TX%2C+USA%22%7D%5D&center=%7B%22lat%22%3A30.2544044893871%2C%22lng%22%3A-98.889515%7D&boundary=%5B%5B%5B30.58599013173766%2C-99.20846183837891%5D%2C%5B30.58599013173766%2C-98.5705681616211%5D%2C%5B29.921695749509272%2C-98.5705681616211%5D%2C%5B29.921695749509272%2C-99.20846183837891%5D%2C%5B30.58599013173766%2C-99.20846183837891%5D%5D%5D&cityName=Fredericksburg&stateName=TX";
  var DISCLAIMER =
    "Listings courtesy of Reata Ranch Realty. Information believed reliable, not guaranteed — verify independently. Doug Siddens, REALTOR®, TREC #840460.";

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function shuffleListings(items) {
    var shuffled = items.slice();
    for (var i = shuffled.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var swap = shuffled[i];
      shuffled[i] = shuffled[j];
      shuffled[j] = swap;
    }
    return shuffled;
  }

  function listingCardHtml(item) {
    var photo = item.photo
      ? '<img src="' +
        escapeHtml(item.photo) +
        '" alt="" loading="lazy" decoding="async">'
      : '<span class="listings-card-ph" aria-hidden="true"></span>';
    var price = escapeHtml(item.priceLabel || "");
    var title = escapeHtml(item.title || "Hill Country listing");
    var meta = escapeHtml(item.meta || item.city || "");
    return (
      '<a class="listings-card" href="' +
      escapeHtml(item.url) +
      '" target="_blank" rel="noopener noreferrer">' +
      '<span class="listings-card-photo">' +
      photo +
      "</span>" +
      '<span class="listings-card-body">' +
      (price ? '<span class="listings-card-price">' + price + "</span>" : "") +
      '<span class="listings-card-name">' +
      title +
      "</span>" +
      (meta ? '<span class="listings-card-meta">' + meta + "</span>" : "") +
      '<span class="listings-card-more">See more</span>' +
      "</span></a>"
    );
  }

  function attr(root, name, fallback) {
    var value = (root.getAttribute(name) || "").trim();
    return value || fallback;
  }

  function headingText(root) {
    var value = (root.getAttribute("data-heading") || "").trim();
    if (!value) return "Browse local listings";
    if (/^(off|none|false)$/i.test(value)) return "";
    return value;
  }

  function initRoot(root) {
    if (root.getAttribute("data-fbg-ready") === "1") return;
    root.setAttribute("data-fbg-ready", "1");
    var columns = parseInt(attr(root, "data-columns", "4"), 10);
    if (columns !== 3) columns = 4;
    root.setAttribute("data-columns", String(columns));
    root.style.setProperty("--fbg-l-cols", String(columns));
    if (!root.getAttribute("data-theme")) root.setAttribute("data-theme", "light");

    var heading = headingText(root);
    var sub = (root.getAttribute("data-sub") || "").trim();
    var jsonUrl = attr(root, "data-listings-url", LISTINGS_JSON);
    root.innerHTML =
      '<div class="listings-head">' +
      "<div>" +
      (heading ? "<h2>" + escapeHtml(heading) + "</h2>" : "") +
      (sub ? '<p class="listings-sub">' + escapeHtml(sub) + "</p>" : "") +
      "</div>" +
      '<a class="listings-all" href="' +
      escapeHtml(LISTINGS_SEARCH) +
      '" target="_blank" rel="noopener noreferrer">See all listings</a>' +
      "</div>" +
      '<div class="listings-scroller"></div>' +
      '<p class="listings-disclaimer">' +
      escapeHtml(DISCLAIMER) +
      "</p>";
    root.hidden = true;

    var scroller = root.querySelector(".listings-scroller");
    fetch(jsonUrl, { credentials: "omit" })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (data) {
        var items = shuffleListings(
          data && Array.isArray(data.listings)
            ? data.listings.filter(function (item) {
                return item && item.url;
              })
            : []
        );
        var limit = parseInt(root.getAttribute("data-limit") || "", 10);
        if (limit > 0) items = items.slice(0, limit);
        if (!items.length) {
          root.hidden = true;
          scroller.innerHTML = "";
          return;
        }
        scroller.innerHTML = items.map(listingCardHtml).join("");
        root.hidden = false;
      })
      .catch(function () {
        root.hidden = true;
      });
  }

  function boot() {
    document.querySelectorAll(".fbg-listings-embed").forEach(initRoot);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
