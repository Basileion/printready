#!/usr/bin/env python3
"""Publish rubric v0.2 scores: archive v0.1 CSV/JSON as history, write v0.2 scores.csv/json and per-prompt JSON.
Input: scores/hunyuan3d2/v0.2/T0*.json (from pipeline/score_v02.py). No numbers are typed by hand."""
import csv, json, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "site" / "data"
for ext in ("csv", "json"):
    arc = D / f"scores_v0.1.{ext}"
    if not arc.exists():
        shutil.copy(D / f"scores.{ext}", arc)
v01 = {r["prompt_id"]: r for r in csv.DictReader(open(D / "scores_v0.1.csv"))}
(D / "hunyuan3d2" / "v0.2").mkdir(exist_ok=True)
rows = []
for pid in sorted(v01):
    j = json.load(open(ROOT / "scores" / "hunyuan3d2" / "v0.2" / f"{pid}.json"))
    j["source"] = f"meshes/hunyuan3d2/{pid}.glb.gz (gunzip; sha256 in SHA256SUMS)"
    (D / "hunyuan3d2" / "v0.2" / f"{pid}.json").write_text(json.dumps(j, indent=1))
    c, s, o = j["checks"], j["score"], v01[pid]
    rows.append({
        "generator": o["generator"], "prompt_id": pid, "prompt": o["prompt"], "rubric": "0.2",
        "score": s["score"], "score_v0.1": float(o["score"]), "hard_fail": s["hard_fail"],
        "up_axis": c["up_axis_declared"], "watertight": c["watertight"], "is_manifold": c["is_manifold"],
        "nonmanifold_edges": c["nonmanifold_edge_count"], "self_intersections": c["self_intersection_count"],
        "body_count": c["body_count"], "wall_p5_mm": c["wall_thickness_p5_mm"], "hull_fill_pct": c["hull_fill_pct"],
        "bed_contact_mm2": c["bed_contact_mm2"], "overhang_pct": c["overhang_pct"],
        "support_volume_mm3": c["support_volume_mm3"], "support_share_pct": c["support_share_pct"],
        "slice_success": c["slice_success"], "print_time_s": c["print_time_s"], "print_time_points": "n/a",
        "faces": j["faces"], "export_padding_faces": j["export_padding_faces"], "scored_at": j["scored_at"],
        "mesh": o["mesh"], "mesh_sha256": o["mesh_sha256"],
    })
with open(D / "scores.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
w0 = json.load(open(ROOT / "scores" / "hunyuan3d2" / "v0.2" / "T01.json"))["score"]["weights"]
old = json.load(open(D / "scores_v0.1.json"))
out = {
    "dataset": old["dataset"], "version": "2026-10-31", "rubric": "0.2", "weights": w0,
    "rubric_history": [{"rubric": "0.1", "file": "scores_v0.1.csv", "json": "scores_v0.1.json", "scored": "2026-10-30"}],
    "license": old["license"],
    "slicer": old["slicer"].replace("0.20mm Standard @BBL A1", "0.20mm Standard @BBL A1 + tree(auto) supports at 45 deg (pipeline/profiles)"),
    "pose": "glTF declared Y-up rotated to Z-up, slicer auto-orient off",
    "normalize_longest_mm": old["normalize_longest_mm"], "rows": rows,
}
(D / "scores.json").write_text(json.dumps(out, indent=1))
print("\n".join(f'{r["prompt_id"]} v0.1={r["score_v0.1"]} v0.2={r["score"]}' for r in rows))
