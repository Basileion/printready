#!/usr/bin/env python3
"""Append (or replace) one generator's rubric v0.2 rows in site/data/scores.csv/json.
Usage: python3 scripts/add_generator_v02.py <gen_key> "<Generator label>"
Input: scores/<gen_key>/v0.2/T0*.json (pipeline/score_v02.py) + gens/<gen_key>/T0*.glb. No numbers typed by hand.
Copies per-prompt JSON to site/data/<gen_key>/v0.2/, gzips meshes to site/data/meshes/<gen_key>/, updates SHA256SUMS."""
import csv, gzip, hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "site" / "data"
key, label = sys.argv[1], sys.argv[2]
prompts = dict(re.findall(r"^\| (T\d\d) \| `([^`]+)`", (ROOT / "PROMPTS.md").read_text(), re.M))
(D / key / "v0.2").mkdir(parents=True, exist_ok=True); (D / "meshes" / key).mkdir(parents=True, exist_ok=True)
old = list(csv.DictReader(open(D / "scores.csv")))
fields = list(old[0].keys())
rows = [r for r in old if r["generator"] != label]
sums = [l for l in (D / "SHA256SUMS").read_text().splitlines() if l.strip() and not l.split()[-1].startswith(f"{key}/")]
new = []
for jf in sorted((ROOT / "scores" / key / "v0.2").glob("T0*.json")):
    pid = jf.stem; glb = ROOT / "gens" / key / f"{pid}.glb"; raw = glb.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    (D / "meshes" / key / f"{pid}.glb.gz").write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    sums.append(f"{sha}  {key}/{pid}.glb")
    j = json.loads(jf.read_text()); j["source"] = f"meshes/{key}/{pid}.glb.gz (gunzip; sha256 in SHA256SUMS)"
    (D / key / "v0.2" / f"{pid}.json").write_text(json.dumps(j, indent=1))
    c, s = j["checks"], j["score"]
    new.append({
        "generator": label, "prompt_id": pid, "prompt": prompts[pid], "rubric": "0.2",
        "score": s["score"], "score_v0.1": "", "hard_fail": s["hard_fail"],
        "up_axis": c["up_axis_declared"], "watertight": c["watertight"], "is_manifold": c["is_manifold"],
        "nonmanifold_edges": c["nonmanifold_edge_count"], "self_intersections": c["self_intersection_count"],
        "body_count": c["body_count"], "wall_p5_mm": c["wall_thickness_p5_mm"], "hull_fill_pct": c["hull_fill_pct"],
        "bed_contact_mm2": c["bed_contact_mm2"], "overhang_pct": c["overhang_pct"],
        "support_volume_mm3": c["support_volume_mm3"], "support_share_pct": c["support_share_pct"],
        "slice_success": c["slice_success"], "print_time_s": c["print_time_s"], "print_time_points": "n/a",
        "faces": j["faces"], "export_padding_faces": j["export_padding_faces"], "scored_at": j["scored_at"],
        "mesh": f"meshes/{key}/{pid}.glb.gz", "mesh_sha256": sha,
    })
# Preserve Matches prompt? columns if present; new generators start blank until human review.
# Re-scoring keeps the human review (RT-20261107-68 re-score must not wipe Matches prompt?).
prev = {r["prompt_id"]: r for r in old if r["generator"] == label}
for r in new:
    for c in ("matches_prompt", "matches_prompt_note", "matches_prompt_reviewed_et"):
        if c in fields:
            r.setdefault(c, prev.get(r["prompt_id"], {}).get(c, ""))
rows += new
with open(D / "scores.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
js = json.loads((D / "scores.json").read_text())
js["rows"] = [r for r in js["rows"] if r["generator"] != label] + [
    {**r, "score_v0.1": None} for r in new]
js["version"] = "2026-10-31"
(D / "scores.json").write_text(json.dumps(js, indent=1))
(D / "SHA256SUMS").write_text("\n".join(sums) + "\n")
print("\n".join(f'{r["generator"]} {r["prompt_id"]} {r["score"]}' for r in new))
