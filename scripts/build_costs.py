#!/usr/bin/env python3
"""Build site/costs/ + site/data/costs.json/.csv from the vendor pricing table below.
Every number is copied from the vendor's own pricing page on CHECKED (ET). Re-check before editing."""
import csv, json, html, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
CHECKED = "2026-10-31"
ROWS = [
 dict(tool="Hunyuan3D-2 (Tencent, open weights)", status="Scored: 5 of 6 watertight", scored=True,
      entry="$0 (public Hugging Face Space or self-hosted GPU)", free="Free; the public Space is rate-limited",
      per_model="$0 on the public Space (what we used)", basis="Our own run: 6 locked prompts, 0 credits spent",
      license="Tencent Hunyuan 3D 2.0 Community License: royalty-free, but not licensed in the EU, UK or South Korea",
      source="https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE"),
 dict(tool="Meshy", status="Queued, not scored yet", scored=False,
      entry="Pro $20/mo ($10 first month for new users); 1,000 credits, up to 100 assets", free="100 credits/month, low queue priority",
      per_model="About $0.20 per asset at $20 ($0.10 in the $10 first month)", basis="Vendor's 'up to 100 assets' ÷ price; not print success",
      license="Free: CC BY 4.0 (sell with credit to Meshy). Paid: you own the assets", source="https://www.meshy.ai/pricing"),
 dict(tool="Tripo", status="Queued, not scored yet", scored=False,
      entry="Pro $20/mo billed annually ($240/yr); 3,000 credits ≈ 200 models", free="200 credits/month ≈ 13 models, limited exports",
      per_model="$0.16 per model (vendor's own figure, annual Pro)", basis="Vendor-stated; not print success",
      license="Free: public models, non-commercial use. Pro: private, commercial use", source="https://www.tripo3d.ai/pricing"),
 dict(tool="Rodin (Hyper3D)", status="Queued, not scored yet", scored=False,
      entry="Creator $30/mo, or $24/mo billed yearly ($288); about 60 models", free="Generate and preview free; pay by result when you confirm; 10 private assets",
      per_model="About $0.50 per model at $30/mo ($0.40 yearly)", basis="Vendor's 'about 60 models' ÷ price; not print success",
      license="Paid plans: unlimited export and any use. Free: no 'any use' grant listed", source="https://hyper3d.ai/pricing"),
 dict(tool="Hitem3D (Hi3D)", status="Queued, not scored yet", scored=False,
      entry="Pro 1,000 credits/month (dollar price not shown in the page's static HTML; check the page)", free="100 credits, lifetime (up to 10 v2.1 geometry models)",
      per_model="Not computed (no dollar price we could read)", basis="v2.1 geometry = 10 credits; v3.0 Quality = 30 credits",
      license="Not stated on the pricing page", source="https://www.hitem3d.ai/pricing"),
 dict(tool="PrintPal", status="Not queued yet (added to the watch list 2026-10-31)", scored=False,
      entry="Pro $10/mo ($8/mo billed annually); 200 generations/month", free="10 photo-to-3D generations/month, Draft quality, STL + OBJ export",
      per_model="About $0.05 per generation at $10", basis="Vendor's 200 generations ÷ price; not print success",
      license="Free: personal, non-commercial. Pro/Studio: sell prints and files", source="https://printpal.io/3dgenerator"),
]
FIELDS = ["tool","status","entry","free","per_model","basis","license","source"]
(SITE/"data"/"costs.json").write_text(json.dumps({"checked_et": CHECKED, "note": "Plan prices copied from each vendor's pricing page. Cost per model = vendor allowance ÷ price, NOT cost per printable model; only Hunyuan3D-2 is scored so far.", "license": "CC BY 4.0", "rows": [{k: r[k] for k in FIELDS+["scored"]} for r in ROWS]}, indent=1, ensure_ascii=False)+"\n")
with open(SITE/"data"/"costs.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(FIELDS+["checked_et"])
    for r in ROWS: w.writerow([r[k] for k in FIELDS]+[CHECKED])
e=html.escape
rows="\n".join(f"""          <tr>
            <th scope="row">{e(r['tool'])}</th>
            <td>{'<span class="score score-ok">'+e(r['status'])+'</span>' if r['scored'] else e(r['status'])}</td>
            <td>{e(r['entry'])}</td>
            <td>{e(r['free'])}</td>
            <td>{e(r['per_model'])}<br><small>{e(r['basis'])}</small></td>
            <td>{e(r['license'])}</td>
            <td><a href="{e(r['source'])}" rel="nofollow noopener">{"license" if "LICENSE" in r["source"] else "pricing page"}</a></td>
          </tr>""" for r in ROWS)
title="What it costs to get a printable AI 3D model (2026 prices) — PrintReady AI"
desc=f"Plan prices, free-tier limits, cost per model and commercial-use terms for AI 3D generators, copied from each vendor's pricing page on {CHECKED}. Only Hunyuan3D-2 is scored for printability so far; the paid tools are queued."
ld={"@context":"https://schema.org","@type":"Dataset","name":"AI 3D generator plan prices and licenses for 3D printing","url":"https://basileion.github.io/printready/costs/","description":desc,"dateModified":CHECKED,"license":"https://creativecommons.org/licenses/by/4.0/","creator":{"@type":"Organization","name":"PrintReady AI","url":"https://basileion.github.io/printready/"},"distribution":[{"@type":"DataDownload","encodingFormat":"text/csv","contentUrl":"https://basileion.github.io/printready/data/costs.csv"},{"@type":"DataDownload","encodingFormat":"application/json","contentUrl":"https://basileion.github.io/printready/data/costs.json"}]}
page=f"""<!doctype html>
<html lang="en" data-product="printready" data-theme="light">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}" />
  <meta name="robots" content="index,follow" />
  <link rel="stylesheet" href="../css/site.css" />
  <link rel="alternate" type="application/atom+xml" title="PrintReady AI scorecard updates" href="https://basileion.github.io/printready/feed.xml" />
  <link rel="canonical" href="https://basileion.github.io/printready/costs/" />
  <meta property="og:url" content="https://basileion.github.io/printready/costs/" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="PrintReady AI" />
  <meta property="og:title" content="{e(title)}" />
  <meta property="og:description" content="{e(desc)}" />
  <meta property="og:image" content="https://basileion.github.io/printready/img/og.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{e(title)}" />
  <meta name="twitter:description" content="{e(desc)}" />
  <meta name="twitter:image" content="https://basileion.github.io/printready/img/og.png" />
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
  <script src="../js/grow.js" defer></script>
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="wrap nav">
      <a class="brand" href="../">Print<span>Ready</span> AI</a>
      <nav aria-label="Primary">
        <ul class="nav-links">
          <li><a href="../">Home</a></li>
          <li><a href="../scorecard/">Sample scorecard</a></li>
          <li><a href="./" aria-current="page">Costs</a></li>
          <li><a href="../methodology/">Methodology</a></li>
          <li><a href="../newsletter/">Newsletter</a></li>
        </ul>
      </nav>
    </div>
  </header>
  <main id="main" class="wrap section">
    <p class="eyebrow">Prices checked {CHECKED} (ET) on each vendor's own pricing page</p>
    <h1>What it costs to get a printable AI 3D model</h1>
    <ul class="lede" style="margin:8px 0 16px">
      <li>Is it worth paying for credits? Here is what each plan costs, what the free tier gives you, and whether you can sell prints.</li>
      <li><strong>Cost per model below is the vendor's allowance divided by the price.</strong> It is not cost per <em>printable</em> model. We only have printability scores for Hunyuan3D-2 so far (<a href="../scorecard/" data-grow="scorecard">5 of 6 watertight</a>); the paid tools are queued for the same locked prompts.</li>
      <li>Selling on Etsy or MakerWorld? Free tiers of Tripo and PrintPal are non-commercial; Meshy's free tier is CC BY 4.0 (credit Meshy). Read the license link before you sell.</li>
    </ul>
    <div class="table-wrap" role="region" aria-label="AI 3D generator costs and licenses" tabindex="0">
      <table>
        <thead>
          <tr><th scope="col">Tool</th><th scope="col">PrintReady status</th><th scope="col">Entry paid plan</th><th scope="col">Free tier</th><th scope="col">Cost per model (not per printable model)</th><th scope="col">Commercial use / license</th><th scope="col">Source</th></tr>
        </thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </div>
    <p style="margin-top:16px">Download this table: <a href="../data/costs.csv" data-grow="data_download">CSV</a> · <a href="../data/costs.json" data-grow="data_download">JSON</a> (CC BY 4.0). Prices change often; we re-check before each scorecard update and date every change.</p>
    <p>Want to know when the queued tools get printability scores? <a href="../feed.xml" data-grow="rss">Follow the scorecard feed (RSS, no email)</a>.</p>
    <p><small>No affiliate links on this page. Not affiliated with any vendor listed. Spot an outdated price? Open an issue on <a href="https://github.com/Basileion/printready/issues" data-grow="github">GitHub</a>.</small></p>
  </main>
  <footer class="site-footer">
    <div class="wrap legal">Prices checked {CHECKED} ET from vendor pricing pages · <a href="../data/">Open data (CSV/JSON, CC BY 4.0)</a> · Privacy: cookieless page-view and link-click counts only, no cookies or personal data</div>
  </footer>
</body>
</html>
"""
(SITE/"costs"/"index.html").write_text(page)
print("ok", len(ROWS))
