#!/usr/bin/env python3
"""Build site/costs/ + site/data/costs.json/.csv from the vendor pricing table below.
Every number is copied from the vendor's own pricing page on checked_et. Re-check before editing."""
import csv, json, html, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PAGE_CHECKED = "2026-11-07"  # page last rebuilt; per-row checked_et below
ROWS = [
 dict(tool="Hunyuan3D-2 (Tencent, open weights)", status="Scored: 5 of 6 watertight", scored=True,
      entry="$0 (public Hugging Face Space or self-hosted GPU)", free="Free; the public Space is rate-limited",
      free_dl="Yes — free mesh download on the public Space (rate-limited); self-host $0",
      per_model="$0 on the public Space (what we used)", basis="Our own run: 6 locked prompts, 0 credits spent",
      license="Tencent Hunyuan 3D 2.0 Community License: royalty-free, but not licensed in the EU, UK or South Korea",
      source="https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE", checked="2026-10-31"),
 dict(tool="Hunyuan3D-2.1 (Tencent, open weights)", status="Scored: 6 of 6 watertight (plate was input artifact)", scored=True,
      entry="$0 (public Hugging Face Space or self-hosted GPU)", free="Free; the public Space is rate-limited (ZeroGPU)",
      free_dl="Yes — free mesh download on the public Space (rate-limited); self-host $0",
      per_model="$0 on the public Space (what we used)", basis="Our own run: 6 locked prompts, 0 credits spent; matted re-test T01/T04/T05/T06",
      license="Tencent Hunyuan 3D 2.1 Community License: royalty-free, but not licensed in the EU, UK or South Korea",
      source="https://huggingface.co/tencent/Hunyuan3D-2.1", checked="2026-10-31"),
 dict(tool="Hunyuan 3D 3.1 (Tencent hosted / MakerLab engine)", status="Not scored yet (watch list; MakerLab + Tencent Cloud API)", scored=False,
     entry="Tencent Cloud API: prepaid from $15 / 1,000 credits ($0.015/cr; 1-year packs); postpaid $0.02/cr. Also via MakerLab Image to 3D (28 credits/gen)",
     free="API: one-time 200 trial credits/user (1 year, deducted first). MakerLab: 2 free Image to 3D gens/account shared across engines (no monthly refill). Consumer-web free daily gens not re-verified this run (login wall).",
     free_dl="MakerLab: Yes, 2 free gens/account then credits. Tencent API: after trial, prepaid/postpaid — download via console (not a free Space like 2.x)",
     per_model="API prepaid ≈ $0.375 Normal textured (25 cr) / $0.225 Geometry (15 cr); postpaid ≈ $0.50 / $0.30. MakerLab ≈ $0.24 on $3/350 pack (28 cr)",
     basis="Tencent Cloud billing doc (Professional Normal 25 / Geometry 15 / +10 multi-view|PBR|face-count) + MakerWorld credit guide; not print success",
     license="Hosted: Tencent Cloud / platform ToS (open-weights 2.x community license does not cover hosted 3.1)",
     source="https://www.tencentcloud.com/document/product/1281/74121", checked="2026-11-07"),
 dict(tool="Meshy", status="Scored: Meshy 6 Lite free plan (not flagship 7.1); T01 99.5 … T05 39", scored=True,
      entry="Pro $20/mo ($10 first month for new users); 1,000 credits, up to 100 assets", free="100 credits/month (20 per Meshy 7.1 image-to-3D, the default), low queue priority. Free plan: 10 untextured Meshy 6 Lite downloads/month (help.meshy.ai). Meshy 6/7/7.1 (the default) and textured models need Pro to download — our 2026-10-31 free-account test used Meshy 7.1 and hit that Pro paywall. Pro: unlimited",
      free_dl="Yes, limited — 10 untextured Meshy 6 Lite downloads/mo; 7.x/textured need Pro",
      per_model="About $0.20 per asset at $20 ($0.10 in the $10 first month)", basis="Vendor's 'up to 100 assets' ÷ price; not print success",
      license="Free: CC BY 4.0 (sell with credit to Meshy). Paid: you own the assets", source="https://www.meshy.ai/pricing", checked="2026-11-07"),
 dict(tool="Tripo", status="Scored: Tripo H2.5 free export (not newer paid models); mean ~26.2; 0/6 watertight; 6/6 hard-fail", scored=True,
      entry="Pro $20/mo billed annually ($240/yr); 3,000 credits ≈ 200 models", free="200 credits/month ≈ 13 models; free exports capped at 15 (H2.5 only)",
      free_dl="Yes, limited — 15 exports, H2.5 only (not newer models)",
      per_model="$0.16 per model (vendor's own figure, annual Pro)", basis="Vendor-stated; not print success",
      license="Free: public models, non-commercial use. Pro: private, commercial use", source="https://www.tripo3d.ai/pricing", checked="2026-11-07"),
 dict(tool="Rodin (Hyper3D)", status="Queued, not scored yet", scored=False,
      entry="Creator $30/mo, or $24/mo billed yearly ($288); about 60 models", free="Generate and preview free; pay by result when you confirm; 10 private assets",
      free_dl="Preview free; pay on confirm / limited private assets",
      per_model="About $0.50 per model at $30/mo ($0.40 yearly)", basis="Vendor's 'about 60 models' ÷ price; not print success",
      license="Paid plans: unlimited export and any use. Free: no 'any use' grant listed", source="https://hyper3d.ai/pricing", checked="2026-11-07"),
 dict(tool="Hitem3D (Hi3D)", status="Queued, not scored yet", scored=False,
      entry="Pro $19.90/mo, 1,000 credits/month (new users: $9.95/mo for the first year, $119.40 billed annually)", free="100 trial credits, lifetime; vendor says 'try up to 7 models'",
      free_dl="Yes, trial — ~7 models (100 trial credits)",
      per_model="About $0.20 per v2.1 geometry model at $19.90 (about $0.10 on the first-year offer)", basis="1,000 credits ÷ 10 credits per v2.1 geometry model; v3.0 Quality = 30 credits; not print success",
      license="Not stated on the pricing page", source="https://www.hitem3d.ai/pricing", checked="2026-10-31"),
 dict(tool="Bambu MakerLab Image to 3D (MakerWorld)", status="Route to the engines above, not scored separately", scored=False,
      entry="No plan: credit packs from $3 for 350 credits (1,000 for $8); credits never expire", free="2 free Image to 3D generations per account, shared across engines; they don't refill",
      free_dl="Yes, 2 free gens/account (no refill), then credits",
      per_model="About $0.21 (Tripo 3.1 or Hitem3D 2.1, 24 credits), $0.24 (Hunyuan 3D 3.1, 28) or $0.39 (Meshy 6 or Rodin Gen-2, 45) per generation on the $3 pack", basis="Credits per generation from MakerWorld's credit guide × $3/350; charged at generation start, system failures refunded; not print success",
      license="MakerWorld: the engine provider's terms decide for Image to 3D output; check the engine you pick", source="https://makerworld.com/en/makerlab-credit-full-guide", checked="2026-11-07"),
 dict(tool="PrintPal", status="Not queued yet (added to the watch list 2026-10-31)", scored=False,
      entry="Pro $10/mo ($8/mo billed annually); 200 generations/month", free="10 photo-to-3D generations/month, Draft quality, STL + OBJ export",
      free_dl="Yes — 10 Draft/mo with STL+OBJ export",
      per_model="About $0.05 per generation at $10", basis="Vendor's 200 generations ÷ price; not print success",
      license="Free: personal, non-commercial. Pro/Studio: sell prints and files", source="https://printpal.io/3dgenerator", checked="2026-10-31"),
 dict(tool="MakeIt3D", status="Not queued yet (added 2026-11-06)", scored=False,
      entry="Light ~$20/mo (30 credits ≈ 30 Quick or 10 Precise); Heavy $50/mo (300 credits). One-time credit packs from $8", free="Free plan exists; free & credit-pack gens go to a community gallery under CC BY-NC 4.0. Light/Heavy: private models + commercial license. Refund-if-not-good (vendor: every refund requested granted)",
      free_dl="Yes — free/packs download STL/3MF/OBJ/GLB (gallery, CC BY-NC); Light/Heavy private + commercial",
      per_model="About $0.66/credit on Light; $0.17 on Heavy; packs $0.50–$0.80/credit. Quick=1 credit (~80s); Precise=3 credits (~2 min)", basis="Vendor pricing page ÷ credits; not print success",
      license="Free & credit packs: personal/CC BY-NC (gallery). Light/Heavy: commercial license included", source="https://makeit3d.app/pricing", checked="2026-11-07"),
]
FIELDS = ["tool","status","entry","free","free_dl","per_model","basis","license","source"]
(SITE/"data"/"costs.json").write_text(json.dumps({
    "checked_et": PAGE_CHECKED,
    "note": "Plan prices copied from each vendor's pricing page. Cost per model = vendor allowance ÷ price, NOT cost per printable model; scored so far: Hunyuan3D-2, Hunyuan3D-2.1, Meshy 6 Lite (free plan, not flagship 7.1) and Tripo H2.5 (free export). free_dl answers 'can I download on free?'. 2026-11-07: added Hunyuan 3D 3.1 hosted/MakerLab row (Tencent Cloud billing + MakerWorld credit guide); re-checked Meshy Pro $20, Tripo, Rodin Creator $30/$24, MakerLab packs, MakeIt3D Light/Heavy. Hitem3D and PrintPal left at 2026-10-31 (pricing pages JS-heavy / not re-verified this run).",
    "license": "CC BY 4.0",
    "rows": [{k: r[k] for k in FIELDS+["scored","checked"]} for r in ROWS]
}, indent=1, ensure_ascii=False)+"\n")
with open(SITE/"data"/"costs.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["tool","status","entry","free","free_downloads","per_model","basis","license","source","checked_et"])
    for r in ROWS: w.writerow([r["tool"],r["status"],r["entry"],r["free"],r["free_dl"],r["per_model"],r["basis"],r["license"],r["source"],r["checked"]])
e=html.escape
rows="\n".join(f"""          <tr>
            <th scope="row">{e(r['tool'])}</th>
            <td>{'<span class="score score-ok">'+e(r['status'])+'</span>' if r['scored'] else e(r['status'])}</td>
            <td>{e(r['entry'])}</td>
            <td>{e(r['free'])}</td>
            <td><strong>{e(r['free_dl'])}</strong><br><small>checked {e(r['checked'])}</small></td>
            <td>{e(r['per_model'])}<br><small>{e(r['basis'])}</small></td>
            <td>{e(r['license'])}</td>
            <td><a href="{e(r['source'])}" rel="nofollow noopener">{"license" if "LICENSE" in r["source"] or "Hunyuan3D-2.1" in r["source"] else ("credit guide" if "makerworld" in r["source"] else ("billing doc" if "tencentcloud.com" in r["source"] else "pricing page"))}</a></td>
          </tr>""" for r in ROWS)
title="What it costs to get a printable AI 3D model (2026 prices) — PrintReady AI"
desc=f"Plan prices, free-tier limits, free downloads, cost per model and commercial-use terms for AI 3D generators, copied from each vendor's pricing page (page rebuilt {PAGE_CHECKED}). Scored for printability so far: Hunyuan3D-2, Hunyuan3D-2.1 and Meshy 6 Lite (Meshy free plan; not flagship 7.1). Queued/watch (not scored yet): Hunyuan 3D 3.1 hosted/MakerLab, Rodin, Hitem3D, MakeIt3D, Meshy 7.1. Tripo H2.5 free export is scored (mean ~26.2; 0/6 watertight)."
ld={"@context":"https://schema.org","@type":"Dataset","name":"AI 3D generator plan prices and licenses for 3D printing","url":"https://basileion.github.io/printready/costs/","description":desc,"dateModified":PAGE_CHECKED,"license":"https://creativecommons.org/licenses/by/4.0/","creator":{"@type":"Organization","name":"PrintReady AI","url":"https://basileion.github.io/printready/"},"distribution":[{"@type":"DataDownload","encodingFormat":"text/csv","contentUrl":"https://basileion.github.io/printready/data/costs.csv"},{"@type":"DataDownload","encodingFormat":"application/json","contentUrl":"https://basileion.github.io/printready/data/costs.json"}]}
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
          <li><a href="../scorecard/">Scorecard</a></li>
          <li><a href="../check/">Check a file</a></li>
          <li><a href="./" aria-current="page">Costs</a></li>
          <li><a href="../data/">Data</a></li>
          <li><a href="../methodology/">Method</a></li>
          <li><a href="../newsletter/">Newsletter</a></li>
        </ul>
      </nav>
    </div>
  </header>
  <main id="main" class="wrap section">
    <p class="eyebrow">Prices checked per row (page rebuilt {PAGE_CHECKED} ET). Free-downloads column answers: can I download on free?</p>
    <h1>What it costs to get a printable AI 3D model</h1>
    <ul class="lede" style="margin:8px 0 16px">
      <li>Is it worth paying for credits? Here is what each plan costs, what the free tier gives you, <strong>whether you can download on free</strong>, and whether you can sell prints.</li>
      <li><strong>Cost per model below is the vendor's allowance divided by the price.</strong> It is not cost per <em>printable</em> model. Printability scores so far: Hunyuan3D-2, Hunyuan3D-2.1, <a href="../scorecard/#m6l-h" data-grow="scorecard">Meshy 6 Lite</a> (free plan, not flagship 7.1; 6 of 6 watertight, T05 slice hard-fail) and <a href="../scorecard/#th25-h" data-grow="scorecard">Tripo H2.5</a> (free export; mean ~26.2; 0 of 6 watertight; 6 of 6 hard-fail). Head-to-head: <a href="../compare/meshy-vs-tripo/">Meshy vs Tripo</a> · <a href="../compare/hunyuan3d-2-vs-2-1/">Hunyuan3D-2 vs 2.1</a>. Hunyuan 3D 3.1 (hosted/MakerLab), Rodin, Hitem3D, MakeIt3D and Meshy 7.1 are queued/watch (not scored) for the same locked prompts.</li>
      <li>Free downloads (short version): Hunyuan Space yes; Meshy 10 Lite/mo; Tripo <strong>15 exports, H2.5 only</strong>; Hitem3D ~7 trial; MakerLab 2 free; PrintPal 10 Draft STL; MakeIt3D free/packs yes (CC BY-NC gallery).</li>
      <li>Selling on Etsy or MakerWorld? Free tiers of Tripo and PrintPal are non-commercial; Meshy's free tier is CC BY 4.0 (credit Meshy); MakeIt3D free/packs are CC BY-NC. Read the license link before you sell.</li>
      <li>Own a Bambu printer? MakerWorld's MakerLab Image to 3D runs Tripo, Hitem3D, Hunyuan 3D, Meshy and Rodin with 2 free generations per account, then roughly $0.21 to $0.39 per generation on the $3 credit pack, with no subscription.</li>
    </ul>
    <div class="table-wrap" role="region" aria-label="AI 3D generator costs and licenses" tabindex="0">
      <table>
        <thead>
          <tr><th scope="col">Tool</th><th scope="col">PrintReady status</th><th scope="col">Entry paid plan</th><th scope="col">Free tier</th><th scope="col">Free downloads?</th><th scope="col">Cost per model (not per printable model)</th><th scope="col">Commercial use / license</th><th scope="col">Source</th></tr>
        </thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </div>
    <p style="margin-top:16px">Download this table: <a href="../data/costs.csv" data-grow="data_download">CSV</a> · <a href="../data/costs.json" data-grow="data_download">JSON</a> (CC BY 4.0). Prices change often; we re-check before each scorecard update and date every change.</p>
    <div class="band" style="margin-top:32px" id="get-scores">
      <div>
        <h2>Before you buy credits: get the scores first</h2>
        <p>We email you when Meshy 7.1, Hitem3D, Rodin, MakeIt3D or TRELLIS printability scores land, so you can see which generator gives printable files before you pay.</p>
      </div>
      <div style="display:grid;gap:10px;min-width:min(100%,18rem)">
        <form class="form" style="max-width:none;display:flex;flex-wrap:wrap;gap:8px;align-items:stretch" action="https://app.kit.com/forms/10124123/subscriptions" method="post" aria-label="Get an email when new printability scores land">
          <label class="skip" for="costs-email">Email</label>
          <input id="costs-email" type="email" name="email_address" required placeholder="you@example.com" autocomplete="email" style="flex:1 1 10rem;min-width:10rem" />
          <button class="btn btn-primary" type="submit" data-grow="newsletter_submit">Email me the scores</button>
        </form>
        <p class="form-note" style="margin:0">Confirmation email required (double opt-in). Free; unsubscribe anytime. Sent via Kit. <a href="/printready/privacy/">Privacy</a>. No email? <a href="../feed.xml" data-grow="rss">Follow the RSS feed</a>.</p>
      </div>
    </div>
    <p><small>No affiliate links on this page. Not affiliated with any vendor listed. Spot an outdated price? Open an issue on <a href="https://github.com/Basileion/printready/issues" data-grow="github">GitHub</a>.</small></p>
  </main>
  <footer class="site-footer">
    <div class="wrap legal">Prices checked per row (page {PAGE_CHECKED} ET) from vendor pricing pages · <a href="../data/">Open data (CSV/JSON, CC BY 4.0)</a> · Privacy: cookieless page-view and link-click counts only, no cookies or personal data · <a href="/printready/privacy/">Privacy</a> · <a href="/printready/terms/">Terms</a> · <a href="mailto:basileion.ops@gmail.com">Contact</a></div>
  </footer>
</body>
</html>
"""
(SITE/"costs"/"index.html").write_text(page)
print("ok", len(ROWS), "free_dl column + MakeIt3D + HY2.1 row")
