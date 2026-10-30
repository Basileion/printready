# PrintReady AI — Phase 1 Plan

**Owner:** Kurt Waibel  
**Working dir:** `/workspace/printready`  
**Status:** Phase 1 (plan + prompts + domains + approvals + scoring pipeline)  
**Rules this phase:** no spending, no account signups, no outreach, no publishing.

---

## 1. Positioning

**One-liner:** The weekly benchmark that scores AI 3D generators on whether their meshes actually print — not how pretty the renders look.

**Problem:** top3d.ai and taxon3d.org rank aesthetics. Meshy’s blog grades itself. Makers who paste a prompt into Meshy / Tripo / Rodin / Hunyuan3D / Trellis / Hitem3D (Hi3D) get glamorous GLBs that fail manifold checks, grow paper-thin walls, or explode in the slicer. Nobody publishes a recurring, vendor-neutral printability leaderboard.

**Audience:** FDM / Bambu / Prusa hobbyists, makerspace leads, and product designers who want AI mesh → plate without hours of repair.

**Moat:** (1) Same locked prompt set every week. (2) Automated mesh + slice scores, not vibes. (3) Programmatic comparison SEO (“Meshy vs Tripo for 3D printing”). (4) Affiliate + sponsor + newsletter revenue aligned with “what actually prints.”

**Not competing on:** visual fidelity leaderboards, game-asset retopo, or paid “AI 3D art” galleries.

---

## 2. Site structure

```
/                     Weekly leaderboard (text-to-3D + image-to-3D tabs)
/methodology          Scoring rubric, slicer profile, hardware assumptions
/prompts              Current + archived prompt packs (versioned)
/models/{vendor}      Per-generator history + sample failures
/compare/{a}-vs-{b}   Programmatic “X vs Y for 3D printing” pages
/week/{YYYY-Www}      Immutable weekly run archive (JSON + PNG previews)
/newsletter           Archive + signup
/affiliates           Disclosure + printer / filament / Bambu / Prusa links
/about                Who runs it, conflict policy, how to reproduce
```

Tech sketch (later phases): static site or Next.js; scores as JSON in git or object storage; preview PNGs from the pipeline; no user accounts required to read.

---

## 3. Scoring method

Each output mesh (STL/OBJ/GLB → triangulated) gets a **PrintReady Score (0–100)** composed of:

| Check | Weight | How | Pass bar |
| --- | --- | --- | --- |
| Watertight | 20 | `trimesh.Trimesh.is_watertight` | True |
| Manifold (edge valence) | 15 | Every edge shared by exactly 2 faces | 0 non-manifold edges |
| Non-manifold edges count | 10 | Count of edges with ≠2 faces; soft penalty | 0 ideal |
| Self-intersections | 10 | `trimesh.intermediate.convex` / collision or face-pair AABB | 0 intersections |
| Thin walls (if feasible) | 10 | Ray / thickness sampling; flag walls &lt; 0.8 mm at 100% scale | ≥0.8 mm (FDM 0.4 mm nozzle) |
| Slice success | 20 | CLI slicer (OrcaSlicer / PrusaSlicer) exits 0 and emits G-code | Success |
| Print time | 5 | Parsed from slicer estimate; normalized vs median of week | Soft — outliers flagged |
| Support volume | 10 | Support filament/volume from slicer; lower is better | Soft — vs week median |

**Hard fail (score capped at 39):** not watertight **or** slice failure.  
**Scale:** meshes normalized to a 50 mm bounding-box longest edge before thin-wall and slice (documented in methodology).  
**Slicer profile (phase 1 default):** 0.4 mm nozzle, 0.2 mm layer, 15% gyroid, generic PLA, auto supports on build plate only, 3 mm brim. Exact profile JSON saved next to scores.

Implementation lives in `pipeline/score_mesh.py` → JSON under `scores/` + preview PNG under `renders/`.

---

## 4. Weekly cadence

| Day (America/New_York) | Action |
| --- | --- |
| Mon AM | Freeze prompt pack version; pull generator versions/changelog notes |
| Mon–Tue | Run text-to-3D + image-to-3D jobs (manual free tiers first; APIs after approvals) |
| Wed | Score all meshes; regenerate leaderboard JSON |
| Thu | Draft newsletter + r/ posts; update compare pages |
| Fri | Publish week archive (when publishing is approved); schedule social |
| Sat–Sun | Buffer / re-runs for vendor outages |

Prompt pack rotates quarterly; a fixed “core 10” never change so YoY charts stay valid.

---

## 5. Newsletter format

**Name working title:** *PrintReady Weekly*  
**Cadence:** Friday morning ET  
**Length:** ~600–900 words  

Sections:
1. **This week’s #1** — generator + score + one failure screenshot of the runner-up.
2. **Leaderboard table** — top models on core prompts (text + image tabs).
3. **Failure of the week** — one non-manifold / thin-wall / slice-crash case study.
4. **X vs Y** — teaser link to one programmatic compare page.
5. **Tooling / affiliate** — one printer or filament pick with disclosure.
6. **Reproducibility** — link to prompt pack version + score JSON.

No paywall on the weekly; paid tier later for CSV exports and alert webhooks (phase 3+).

---

## 6. Distribution (built in from day one)

### Programmatic SEO
- Template: `/{a}-vs-{b}-for-3d-printing` for every unordered pair of generators.
- Also: `/{generator}-printability-score`, `/best-ai-for-3d-printing-{month}-{year}`.
- Each page embeds the latest head-to-head table + methodology blurb + affiliate CTA.

### Communities (draft only this phase — no posting until Kurt approves)
- **r/3Dprinting** — weekly “AI mesh printability benchmark” stickied-style self-post with charts; follow sub rules (no pure affiliate spam).
- **r/BambuLab** — Bambu-oriented slice of results (0.4 / 0.2 profile matching X1C defaults).
- **r/TopologyAI** — technical write-up of manifold / non-manifold findings.
- **Show HN** — launch post: “PrintReady AI – open weekly printability benchmark for text/image-to-3D”.
- **Product Hunt** — launch day after 4 consecutive weekly runs so the gallery isn’t empty.

### Other channels (phase 2+)
- X/Twitter threads with before/after repair GIFs.
- YouTube short: “This Meshy dragon will not slice”.
- Cross-link from Printables / MakerWorld guides (no ToS-violating scraping).

---

## 7. Phase map

| Phase | Deliverable | This box |
| --- | --- | --- |
| **1 (now)** | PLAN, PROMPTS, domain shortlist, APPROVALS, scoring pipeline tested | ✅ |
| 2 | Kurt signups + free-tier runs; first private week JSON | Needs approvals |
| 3 | Static site + compare pages + newsletter tool | Needs domain + publish OK |
| 4 | Public launch (HN / PH / reddit) | Needs Kurt go-ahead |

---

## 8. Risks

- Free tiers throttle / watermark / ban automation → prefer official APIs once paid.
- Vendor self-preference accusations → publish full prompt pack + raw meshes.
- Thin-wall heuristic false positives → label as “experimental” until calibrated on known-good Printables STLs.
- Box has **no GPU** → local open-weight inference not viable here; use HF Spaces or cloud APIs.
