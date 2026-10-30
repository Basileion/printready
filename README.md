# PrintReady AI — Phase 1

Weekly AI text/image-to-3D **printability** benchmark (not looks).

## Layout

| Path | Contents |
| --- | --- |
| `PLAN.md` | Positioning, site map, scoring rubric, cadence, newsletter, distribution |
| `PROMPTS.md` | 20 text prompts + 12 image-to-3D reference ideas + negative controls |
| `DOMAINS.md` | RDAP shortlist (2026-10-30) + typical prices |
| `APPROVALS.md` | Free tiers, signup needs, GPU status, $ approvals Kurt must give |
| `pipeline/score_mesh.py` | trimesh + OrcaSlicer 2.4.2 scorer → JSON + PNG |
| `samples/` | Public-domain-style generated STLs + deliberate broken meshes |
| `scores/` | Per-mesh JSON + `summary.json` |
| `renders/` | Preview PNGs |
| `tools/orca_root/` | Extracted OrcaSlicer (CLI via xvfb + stubbed WebKit) |

## Score a mesh

```bash
cd /workspace/printready
.venv/bin/python pipeline/score_mesh.py samples/n01_closed_cube.stl
```

Slicer profile: Bambu Lab A1 0.4 nozzle, 0.20 mm Standard, Generic PLA @BBL A1.  
Meshes normalized to 50 mm longest edge before thin-wall + slice.

## Phase-1 rules honored

No spending, no account signups, no outreach, no publishing.
