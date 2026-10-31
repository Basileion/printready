#!/usr/bin/env python3
"""PrintReady rubric v2 diagnostics (RT-30): hull fill %, orientation, first-layer area, ray wall thickness.
Measurement only; does not change v1 scores."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, trimesh
sys.path.insert(0, str(Path(__file__).parent))
from score_mesh import load_mesh, drop_export_padding, TARGET_LONGEST_MM

FIRST_LAYER_MM = 0.2

def first_layer_area(m: trimesh.Trimesh, axis: int) -> float:
    """Area (mm^2) of downward-facing faces within 0.2 mm of the bed when `axis` is up."""
    lo = m.bounds[0][axis]
    tri = m.triangles
    near = (tri[:, :, axis].max(axis=1) - lo) <= FIRST_LAYER_MM
    down = m.face_normals[:, axis] < -0.7
    sel = near & down
    a = m.area_faces[sel].copy()
    n = np.abs(m.face_normals[sel, axis])
    return float((a * n).sum())

def ray_wall(m: trimesh.Trimesh, n=400) -> dict:
    if not m.is_watertight:
        return {"p5_mm": None, "median_mm": None}
    rng = np.random.default_rng(0)
    pts, fi = trimesh.sample.sample_surface(m, n, seed=0)
    nr = m.face_normals[fi]
    loc, ir, _ = m.ray.intersects_location(pts - nr * 1e-3, -nr, multiple_hits=False)
    if len(loc) == 0:
        return {"p5_mm": None, "median_mm": None}
    d = np.linalg.norm(loc - pts[ir], axis=1)
    return {"p5_mm": round(float(np.percentile(d, 5)), 3), "median_mm": round(float(np.median(d)), 3)}

def diag(path: Path) -> dict:
    m = load_mesh(path); m, _ = drop_export_padding(m)
    m.apply_scale(TARGET_LONGEST_MM / float(max(m.extents)))
    m.apply_translation(-m.bounds[0])
    hull = m.convex_hull
    vol = float(m.volume) if m.is_volume else None
    fill = round(100 * vol / float(hull.volume), 1) if vol and hull.volume > 0 else None
    # Scorer v1 slices with mesh Z as up; glTF convention is Y-up.
    fl_z = first_layer_area(m, 2)
    fl_y = first_layer_area(m, 1)
    return {
        "id": path.stem,
        "extents_mm": [round(float(x), 2) for x in m.extents],
        "volume_mm3": round(vol, 1) if vol else None,
        "hull_volume_mm3": round(float(hull.volume), 1),
        "hull_fill_pct": fill,
        "first_layer_mm2_as_sliced_z_up": round(fl_z, 1),
        "first_layer_mm2_gltf_y_up": round(fl_y, 1),
        "gltf_up_axis": "Y",
        "sliced_up_axis": "Z",
        "ray_wall": ray_wall(m),
    }

if __name__ == "__main__":
    out = [diag(Path(p)) for p in sys.argv[1:]]
    print(json.dumps(out, indent=1))
