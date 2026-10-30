# PrintReady AI — Approvals Kurt Needs

Nothing below has been signed up or purchased. Phase 1 rule: **NO spending, NO account signups**.

## Box hardware

| Item | Finding |
| --- | --- |
| GPU | **None** (`nvidia-smi` → NO_GPU). Local Hunyuan3D / Trellis weights are **not** runnable on this box. |
| CPU / RAM | 8 cores, ~16 GiB RAM |
| Slicer on box | OrcaSlicer **v2.4.2** AppImage downloaded + extracted under `tools/orca_root/`. Needs extra system libs (WebKitGTK / libsoup) for full GUI; CLI slice path wired with graceful fallback if binary cannot load. |

---

## Per-generator free tiers (research snapshot 2026-10-30)

### 1. Meshy (meshy.ai)

| | |
| --- | --- |
| Free | **100 credits / month**, no credit card. Web app only. ~10 downloads/mo of Meshy 6 Lite **untextured**. CC BY 4.0. |
| API | **Not on Free.** Needs Pro+ |
| Signup needs | Email (Google/Discord/etc. common). No card for Free. |
| Paid (if Kurt approves later) | Pro **$20/mo** list (often **$10** first month promo) = 1,000 credits. API mesh-only ≈ 5–20 credits/gen depending on model. |
| Phase-2 use | Manual web gens on Free for a few prompts; API only after Pro. |

### 2. Tripo (tripo3d.ai)

| | |
| --- | --- |
| Free web | **~200 credits / month**, no card (Studio free plan). Outputs often public / non-commercial on free. |
| API | Prepaid credits; **$1 = 100 credits**. Historical new-API-key bonus (2,000 credits) may still appear — **verify at key creation**, do not assume. Text-to-3D mesh-only ≈ **10 credits ($0.10)**. |
| Signup needs | Email / account. Card only when buying credits. |

### 3. Rodin / Hyper3D (hyper3d.ai) via site or fal

| | |
| --- | --- |
| Hyper3D Free | Preview/generate free; credits charged on **confirm/download**. Starter credits reported (~10); direct credit ≈ **$1.50** each. Creator plan ~**$24/mo**. |
| fal.ai Rodin | **~$0.40 / generation** (HighPack +$0.80). fal signup often wants card; third-party reports ~**$20** trial credits (unofficial — verify). |
| Signup needs | Email; fal may require payment method to activate. |

### 4. Hunyuan3D

| | |
| --- | --- |
| HF Spaces | `tencent/Hunyuan3D-2` and `Hunyuan3D-2.1` on **ZeroGPU** — usable in browser **without account** (queue). License: Tencent community, **non-commercial** caveats — OK for benchmark research; check before selling assets. |
| fal | Hunyuan endpoints ~**$0.015 / unit** (see fal model page). |
| Box local | **Blocked** — no GPU. |

### 5. Trellis (Microsoft)

| | |
| --- | --- |
| HF Spaces | `microsoft/TRELLIS.2` and community TRELLIS Spaces on ZeroGPU — **no account** for public demo (queue). Weights MIT. |
| fal | Trellis ~**$0.02**/gen; Trellis 2 ~**$0.05**/unit. |
| Replicate | Pay-per-second after any free trial runs; needs billing for sustained use. |
| Box local | **Blocked** — needs ≥16–24 GB VRAM. |

### 6. Hitem3D / Hi3D (hi3d.ai)

| | |
| --- | --- |
| Free | **100 lifetime credits**; attribution; limited commercial use on free. |
| Paid | From ~**$19.90/mo** for 1,000 credits (verify at signup). Geometry 10–130 credits depending on quality tier. |
| Signup needs | Email account. |

### 7. Open-weight / no-account options (preferred for $0 phase)

| Model | Where | Account? |
| --- | --- | --- |
| Hunyuan3D-2 / 2.1 | Hugging Face Spaces (ZeroGPU) | No (browser) |
| TRELLIS / TRELLIS.2 | Hugging Face Spaces (ZeroGPU) | No (browser) |
| TripoSR | `stabilityai/TripoSR` Space | No (browser) |
| Local weights | Needs GPU — **not on this box** | — |

---

## Exact approvals to request from Kurt

### A. Free signups (no spend) — approve account creation

1. **Meshy Free** — email signup, 100 credits/mo, web-only downloads.  
2. **Tripo Free** — email signup, ~200 credits/mo.  
3. **Hi3D / Hitem3D Free** — email signup, 100 lifetime credits.  
4. **Hyper3D Free** — email signup; download only if free starter credits cover it.  
5. Optional: **Hugging Face account** (free) — higher ZeroGPU priority; Spaces work without it.

### B. Spend approvals (dollar amounts) — do **not** buy until Kurt says yes

| Item | Amount | Why |
| --- | --- | --- |
| Domain: printbench.ai (or alt from DOMAINS.md) | **~$70–100** year-1 | Site home |
| Fallback domain printready.co | **~$10–15**/yr | If .ai deferred |
| Meshy Pro (API + downloads) | **$10** first month promo / **$20**/mo after | Automated weekly runs |
| fal.ai top-up | **$20–50** prepaid | Rodin + Trellis + Hunyuan API |
| Tripo API credits | **$20** (= 2,000 credits) | ~200 text mesh gens |
| Hi3D starter paid (optional) | **~$20**/mo | If free 100 credits exhaust |
| Replicate billing (optional) | **$20** prepaid | Backup Trellis path |

### C. Estimated monthly cost at **full scale**

Assumptions: **20 text + 12 image prompts × 6 generators = 192 gens/week ≈ 768 gens/month**, mesh-only where possible.

| Path | Est. monthly |
| --- | --- |
| Free tiers + HF Spaces only | **$0** (slow, incomplete coverage, ToS/queue limits) |
| Lean paid (Meshy Pro + $40 fal/Tripo mix) | **~$60–80**/mo |
| Full-scale API parity all six vendors | **~$150–350**/mo | (Meshy Pro/Premium + Tripo + fal Rodin@$0.40 + Hunyuan/Trellis cheap + Hi3D) |
| Domain + newsletter tooling | **+$6–10**/mo amortized |

**Recommendation:** Approve **A** (free signups) + **one .ai domain (~$80)** + **$50** prepaid API budget for a first private week. Revisit full-scale after week 1 cost actuals.

---

## Not requesting (blocked by phase-1 rules)

- Publishing the site, Show HN, Product Hunt, or subreddit posts  
- Contacting vendors for sponsorship  
- Any purchase without Kurt’s explicit dollar approval  
