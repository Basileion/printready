#!/usr/bin/env python3
"""PrintReady Score rubric v0.2 (2026-10-31). Closes RT-20261031-23 and RT-20261030-30.

Changes vs v0.1 (score_mesh.py, kept for history):
  * Geometry is scored in the file's declared up-axis. glTF/GLB is Y-up, so the mesh is
    rotated Y-up -> Z-up before any bed/overhang check and before slicing (v0.1 used raw Z as up).
  * Slice success 20 -> 5 (every mesh sliced in public benchmarks and here).
  * Support volume (10) is now real: v0.1 sliced with enable_support=0, so it was always 10/10.
    v0.2 slices with tree(auto) supports at 45 deg (pipeline/profiles/) and scores the support
    share of extruded volume. Geometric overhang % (> 45 deg, off the bed) is reported as a cross-check.
  * Print time (5) removed -> reported, scored n/a until a weekly median exists.
  * New: hull fill % (hollow-skin check), first-layer bed contact (flat base).
  * Thin walls now use ray wall thickness p5 (400 seeded surface samples).
Weights sum to 100. Hard fail (not watertight or slice failed) caps the score at 39, as in v0.1.
"""
from __future__ import annotations
import argparse, json, math, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, trimesh

sys.path.insert(0, str(Path(__file__).parent))
from score_mesh import (load_mesh, drop_export_padding, count_nonmanifold_edges,
                        self_intersection_count, slice_with_orca, TARGET_LONGEST_MM)
from diagnostics_v2 import ray_wall, first_layer_area

RUBRIC_VERSION = "0.2"
WEIGHTS = {
    "watertight": 20, "manifold": 15, "nonmanifold_edges": 10, "self_intersections": 10,
    "wall_thickness_p5": 10, "slice_success": 5, "tree_support": 10, "hull_fill": 10,
    "bed_contact": 10, "print_time": 0,
}
assert sum(WEIGHTS.values()) == 100
OVERHANG_DEG = 45.0
BED_BAND_MM = 0.2
WALL_FULL_MM, WALL_PART_MM = 0.8, 0.4
SUPPORT_FULL_PCT, SUPPORT_ZERO_PCT = 5.0, 35.0
SUPPORT_PROFILE = Path(__file__).resolve().parent / "profiles" / "0.20mm Standard @BBL A1 - tree supports.json"
FILL_FULL_PCT, FILL_ZERO_PCT = 20.0, 5.0
CONTACT_ZERO_MM2, CONTACT_FULL_MM2 = 10.0, 100.0
UP_AXIS = {".glb": "Y", ".gltf": "Y"}  # STL/OBJ/3MF: Z-up


def to_z_up(mesh: trimesh.Trimesh, up: str) -> trimesh.Trimesh:
    m = mesh.copy()
    if up == "Y":  # +Y -> +Z (rotate +90 deg about X)
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation(-m.bounds[0])
    return m


def overhang(m: trimesh.Trimesh, axis: int = 2, sign: float = 1.0) -> dict:
    """Area of faces whose normal points down more than 45 deg past vertical, excluding faces in the bed band."""
    nz = m.face_normals[:, axis] * sign
    coord = m.triangles[:, :, axis] * sign
    lo = coord.min()
    on_bed = (coord.max(axis=1) - lo) <= BED_BAND_MM
    sel = (nz < -math.cos(math.radians(OVERHANG_DEG))) & ~on_bed
    a = float(m.area_faces[sel].sum())
    return {"area_mm2": round(a, 1), "pct": round(100 * a / float(m.area), 2)}


def lin(x, zero, full):
    """0..1 linear ramp; works for ascending or descending bars."""
    t = (x - zero) / (full - zero)
    return max(0.0, min(1.0, t))


def score(checks: dict) -> dict:
    w, p = WEIGHTS, {}
    p["watertight"] = w["watertight"] if checks["watertight"] else 0.0
    p["manifold"] = w["manifold"] if checks["is_manifold"] else 0.0
    nm = checks["nonmanifold_edge_count"]
    p["nonmanifold_edges"] = w["nonmanifold_edges"] * (1.0 if nm == 0 else 0.5 if nm <= 5 else 0.0)
    si = checks["self_intersection_count"]
    p["self_intersections"] = w["self_intersections"] * (0.5 if si is None else 1.0 if si == 0 else 0.0)
    t = checks["wall_thickness_p5_mm"]
    p["wall_thickness_p5"] = 0.0 if t is None else w["wall_thickness_p5"] * (
        1.0 if t >= WALL_FULL_MM else 0.4 if t >= WALL_PART_MM else 0.0)
    p["slice_success"] = w["slice_success"] if checks["slice_success"] else 0.0
    sp = checks["support_share_pct"]
    p["tree_support"] = 0.0 if sp is None else w["tree_support"] * lin(sp, SUPPORT_ZERO_PCT, SUPPORT_FULL_PCT)
    f = checks["hull_fill_pct"]
    p["hull_fill"] = 0.0 if f is None else w["hull_fill"] * lin(f, FILL_ZERO_PCT, FILL_FULL_PCT)
    c = checks["bed_contact_mm2"]
    p["bed_contact"] = w["bed_contact"] * lin(math.log10(max(c, 1e-6)), math.log10(CONTACT_ZERO_MM2),
                                              math.log10(CONTACT_FULL_MM2))
    p["print_time"] = 0.0  # n/a until a weekly median exists
    total = float(sum(p.values()))
    hard_fail = (not checks["watertight"]) or (not checks["slice_success"])
    if hard_fail:
        total = min(total, 39.0)
    return {"rubric": RUBRIC_VERSION, "score": round(total, 1), "hard_fail": hard_fail,
            "partial": {k: round(v, 2) for k, v in p.items()}, "weights": WEIGHTS}


def score_file(path: Path, rel_source: str, skip_slice=False, slice_dir: Path | None = None) -> dict:
    up = UP_AXIS.get(path.suffix.lower(), "Z")
    raw = load_mesh(path)
    raw, pad = drop_export_padding(raw)
    raw.apply_scale(TARGET_LONGEST_MM / float(max(raw.extents)))
    m = to_z_up(raw, up)
    nm = count_nonmanifold_edges(m)
    wt = bool(m.is_watertight)
    si = self_intersection_count(m)
    vol = float(m.volume) if m.is_volume else None
    hull = float(m.convex_hull.volume)
    fill = round(100 * vol / hull, 1) if vol and hull > 0 else None
    rw = ray_wall(m)
    oh = overhang(m)
    contact = first_layer_area(m, 2)
    # info only: v0.1 pose (raw Z up) and best of 6 axis-aligned poses
    raw0 = raw.copy(); raw0.apply_translation(-raw0.bounds[0])
    poses = {}
    for ax, name in enumerate("XYZ"):
        for sgn, s in ((1.0, "+"), (-1.0, "-")):
            poses[s + name] = overhang(raw0, ax, sgn)["pct"]
    slice_info = {"attempted": False, "success": False}
    if not skip_slice:
        with tempfile.TemporaryDirectory(prefix="pr02_") as td:
            stl = Path(td) / f"{path.stem}_v02_zup.stl"
            m.export(stl)
            slice_info = slice_with_orca(stl, Path(td) / "out", orient=False, process=SUPPORT_PROFILE)
            slice_info.pop("gcode_path", None)
    checks = {
        "up_axis_declared": up, "scored_pose": f"{up}-up (declared)",
        "watertight": wt, "is_manifold": bool(nm == 0 and wt), "nonmanifold_edge_count": int(nm),
        "self_intersection_count": si, "body_count": int(m.body_count),
        "wall_thickness_p5_mm": rw["p5_mm"], "wall_thickness_median_mm": rw["median_mm"],
        "volume_mm3": round(vol, 1) if vol else None, "hull_volume_mm3": round(hull, 1),
        "hull_fill_pct": fill, "overhang_area_mm2": oh["area_mm2"], "overhang_pct": oh["pct"],
        "bed_contact_mm2": round(contact, 1),
        "overhang_pct_by_axis_pose_info": poses,
        "bed_contact_mm2_v01_raw_z_up_info": round(first_layer_area(raw0, 2), 1),
        "slice_success": bool(slice_info.get("success")),
        "print_time_s": slice_info.get("print_time_s"),
        "support_volume_mm3": slice_info.get("support_volume_mm3"),
        "extruded_volume_mm3": slice_info.get("extruded_volume_mm3"),
        "support_share_pct": (round(100 * slice_info["support_volume_mm3"] / slice_info["extruded_volume_mm3"], 1)
                              if slice_info.get("support_volume_mm3") is not None and slice_info.get("extruded_volume_mm3") else None),
    }
    return {
        "id": path.stem, "source": rel_source, "rubric": RUBRIC_VERSION,
        "scored_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "normalize_longest_mm": TARGET_LONGEST_MM, "extents_mm_z_up": [round(float(x), 2) for x in m.extents],
        "faces": int(len(m.faces)), "export_padding_faces": pad["export_padding_faces"],
        "checks": checks, "score": score(checks),
        "slice": {"orient": "off (declared pose)", "supports": "tree(auto), 45 deg", "process": SUPPORT_PROFILE.name, "returncode": slice_info.get("returncode"),
                  "stderr_tail": (slice_info.get("stderr_tail") or "")[-300:]},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meshes", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-slice", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    for p in a.meshes:
        rel = str(p.resolve().relative_to(root)) if p.resolve().is_relative_to(root) else p.name
        r = score_file(p, rel, a.skip_slice)
        (a.out / f"{p.stem}.json").write_text(json.dumps(r, indent=1))
        print(p.stem, r["score"]["score"], json.dumps(r["score"]["partial"]), flush=True)


if __name__ == "__main__":
    main()
