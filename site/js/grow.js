/* PrintReady AI: tiny cookieless event beacon (page views + key clicks).
 * No cookies, no personal data. Sends site, event, path, link label, UTM tags and referrer host.
 * Endpoint: https://growth-ingest.basileion-ops.workers.dev */
(function () {
  var ENDPOINT = "https://growth-ingest.basileion-ops.workers.dev";
  var SITE = "printready";
  var L = null;
  try { L = window.localStorage; } catch (e) {}
  function qs(k) { try { return new URLSearchParams(location.search).get(k) || ""; } catch (e) { return ""; } }
  function utm() {
    var keys = ["utm_source", "utm_medium", "utm_campaign"], out = {}, found = false;
    keys.forEach(function (k) { var v = qs(k); if (v) { out[k] = v; found = true; } });
    if (found && L) { try { L.setItem("grow:utm", JSON.stringify({ t: Date.now(), s: out })); } catch (e) {} return out; }
    if (L) { try { var o = JSON.parse(L.getItem("grow:utm") || "null"); if (o && Date.now() - o.t < 7 * 864e5) return o.s || {}; } catch (e) {} }
    return {};
  }
  var isTest = qs("grow_test") === "1" || /^(localhost|127\.|0\.0\.0\.0)/.test(location.hostname);
  function send(event, cta) {
    var u = utm();
    var body = JSON.stringify({
      site: SITE, event: event, path: location.pathname + location.hash, cta: cta || "",
      utm_source: u.utm_source || "", utm_medium: u.utm_medium || "", utm_campaign: u.utm_campaign || "",
      referrer: document.referrer || "", test: isTest
    });
    try { if (navigator.sendBeacon && navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }))) return; } catch (e) {}
    try { fetch(ENDPOINT, { method: "POST", body: body, headers: { "Content-Type": "application/json" }, keepalive: true, credentials: "omit" }); } catch (e) {}
  }
  function label(a) {
    var g = a.getAttribute("data-grow"); if (g) return g;
    var h = a.getAttribute("href") || "";
    if (/feed\.xml/.test(h)) return "rss";
    if (/github\.com\/Basileion\/printready/i.test(h)) return "github";
    if (/\.(csv|json|glb|gz|txt)$|SHA256SUMS/i.test(h) && /data\//.test(h)) return "data_download";
    if (/(^|\/)data\/?$/.test(h)) return "data_page";
    if (/scorecard\/?$/.test(h)) return "scorecard";
    if (/costs\/?$/.test(h)) return "costs";
    if (/methodology/.test(h)) return "methodology";
    if (/newsletter/.test(h)) return "newsletter";
    if (/^https?:/.test(h) && h.indexOf(location.host) < 0) { try { return "out:" + new URL(h).hostname; } catch (e) { return "out"; } }
    return "";
  }
  send("page_view");
  document.addEventListener("click", function (ev) {
    var el = ev.target && ev.target.closest && ev.target.closest("a[href], button[type=submit][data-grow], input[type=submit][data-grow]");
    if (!el) return;
    if (el.tagName === "A") {
      var c = label(el);
      if (c) send("cta_click", c);
      return;
    }
    var g = el.getAttribute("data-grow");
    if (g) send("cta_click", g);
  }, true);
  window.grow = { track: send };
})();
