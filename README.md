# PrintReady AI

Weekly AI text/image-to-3D **printability** benchmark (not looks).

**Live:** https://basileion.github.io/printready/

## Layout

| Path | Contents |
| --- | --- |
| `PROMPTS.md` | 20 text prompts + 12 image-to-3D reference ideas + negative controls |
| `pipeline/score_mesh.py` | trimesh + OrcaSlicer 2.4.2 scorer → JSON + PNG |
| `samples/` | Generated STLs + deliberate broken meshes |
| `scores/` | Per-mesh JSON + `summary.json` |
| `renders/` | Preview PNGs |
| `site/` | Static site (GitHub Pages) |

## Score a mesh

```bash
python pipeline/score_mesh.py samples/n01_closed_cube.stl
```

Slicer profile: Bambu Lab A1 0.4 nozzle, 0.20 mm Standard, Generic PLA @BBL A1.  
Meshes normalized to 50 mm longest edge before thin-wall + slice.  
Index-degenerate export-padding faces are dropped before watertight checks.

## Notes

The scorer reports Space-GLB zero-area filler triangles as **export padding**, not holes.
