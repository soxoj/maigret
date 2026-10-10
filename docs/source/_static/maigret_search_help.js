// Show a helper when a docs search returns zero results.
//
// A large share of searches on these docs are usernames, emails or phone
// numbers typed by people who think this page *is* Maigret. Those always return
// nothing, so the empty-results state is the moment to point them at how to run
// a real search.
//
// There are two search UIs to cover:
//   1. Read the Docs Addons modal (production hosting) — a <readthedocs-search>
//      web component with an OPEN shadow root; on zero hits it renders a
//      `.no-results` panel.
//   2. Plain Sphinx search.html (local builds, non-RTD hosting) — results go in
//      #search-results.
// Both are keyed off DOM structure only, and every lookup is null-guarded, so a
// markup change upstream just means the helper stops appearing — never an error.

(function () {
  "use strict";

  var HELPER_HTML =
    "<strong>Looking for a person, not documentation?</strong><br>" +
    "This searches Maigret’s docs — not social networks. To check a " +
    "username, run <code>maigret &lt;username&gt;</code> in a terminal, use the " +
    '<a href="https://maigret.app/docs">Telegram bot</a>, ' +
    "or run <code>maigret --web 5000</code>.";

  // The RTD modal lives in a shadow root, so the theme's .admonition CSS can't
  // reach it — style inline there. On the light-DOM Sphinx page, reuse the theme.
  function makeBox(inShadow) {
    var box = document.createElement("div");
    box.id = "maigret-search-help";
    box.innerHTML = HELPER_HTML;
    if (inShadow) {
      box.style.cssText =
        "margin:16px auto;max-width:88%;padding:12px 16px;border:1px solid " +
        "#cfe3c9;background:#e8f5e2;border-radius:6px;font-size:14px;" +
        "line-height:1.55;text-align:left;color:#1a1a1a";
    } else {
      box.className = "admonition tip";
    }
    return box;
  }

  // Surface 1 — Read the Docs Addons search modal.
  function hookRtdSearch() {
    if (!window.customElements || !customElements.whenDefined) return;
    customElements.whenDefined("readthedocs-search").then(function () {
      var tries = 0;
      (function attach() {
        var el = document.querySelector("readthedocs-search");
        var root = el && el.shadowRoot;
        if (!root) {
          if (tries++ < 20) setTimeout(attach, 250);
          return;
        }
        // .no-results is re-rendered on each keystroke; re-inject when missing.
        new MutationObserver(function () {
          var nr = root.querySelector(".no-results");
          if (nr && !nr.querySelector("#maigret-search-help")) {
            nr.insertBefore(makeBox(true), nr.querySelector(".tips") || null);
          }
        }).observe(root, { childList: true, subtree: true });
      })();
    });
  }

  // Surface 2 — plain Sphinx search.html.
  function hookSphinxSearch() {
    var out = document.getElementById("search-results");
    if (!out) return;
    function maybeShow() {
      if (document.getElementById("maigret-search-help")) return; // once
      if (!new URLSearchParams(window.location.search).get("q")) return; // no query
      if (out.querySelector("li")) return; // has results
      if (!out.textContent.trim()) return; // search not finished yet
      out.insertBefore(makeBox(false), out.firstChild);
    }
    // ponytail: debounce settles the async result stream; 250ms is ample since
    // 0-result runs finish in one tick. Bump if a slow render ever false-fires.
    var settle;
    new MutationObserver(function () {
      clearTimeout(settle);
      settle = setTimeout(maybeShow, 250);
    }).observe(out, { childList: true, subtree: true, characterData: true });
  }

  document.addEventListener("DOMContentLoaded", function () {
    hookRtdSearch();
    hookSphinxSearch();
  });
})();
