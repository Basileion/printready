#!/usr/bin/env python3
"""PrintReady AI — mesh printability scorer (trimesh + OrcaSlicer CLI)."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
ORCA_ROOT = ROOT / "tools" / "orca_root"
ORCA_BIN = ORCA_ROOT / "bin" / "orca-slicer"
STUBS = ROOT / "tools" / "stubs"
LOCAL_LIB = ROOT / "tools" / "local" / "usr" / "lib" / "x86_64-linux-gnu"
BBL = ORCA_ROOT / "resources" / "profiles" / "BBL"
MACHINE = BBL / "machine" / "Bambu Lab A1 0.4 nozzle.json"
PROCESS = BBL / "process" / "0.20mm Standard @BBL A1.json"
FILAMENT = BBL / "filament" / "Generic PLA @BBL A1.json"
if not FILAMENT.exists():
    cands = sorted((BBL / "filament").glob("*PLA*@BBL A1.json"))
    FILAMENT = cands[0] if cands else BBL / "filament" / "Bambu PLA Aero @BBL A1.json"

TARGET_LONGEST_MM = 50.0
THIN_WALL_MM = 0.8


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def load_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="mesh")
    if isinstance(loaded, trimesh.Scene):
        geoms = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not geoms:
            raise ValueError(f"No triangle mesh in {path}")
        loaded = trimesh.util.concatenate(geoms)
    if not isinstance(loaded, trimesh.Trimesh):
        raise ValueError(f"Unsupported mesh type for {path}: {type(loaded)}")
    return loaded


def normalize_scale(mesh: trimesh.Trimesh, longest: float = TARGET_LONGEST_MM) -> float:
    extents = mesh.extents
    cur = float(max(extents)) if max(extents) > 0 else 1.0
    scale = longest / cur
    mesh.apply_scale(scale)
    # Sit on bed (z=0)
    mesh.apply_translation(-mesh.bounds[0])
    return scale


def count_nonmanifold_edges(mesh: trimesh.Trimesh) -> int:
    # edges_unique_length == 2 is manifold; else non-manifold
    try:
        group = mesh.edges_unique_length  # not right
    except Exception:
        pass
    # Prefer trimesh helper
    if hasattr(mesh, "facets_boundary"):
        pass
    # Count edges with valence != 2
    edges = mesh.edges_sorted
    if len(edges) == 0:
        return 0
    # unique edges + counts
    uniq, counts = np.unique(edges, axis=0, return_counts=True)
    return int(np.sum(counts != 2))


MAX_OVERLAP_PARTS = 40


def self_intersection_count(mesh: trimesh.Trimesh) -> int | None:
    """Return 0/1-ish intersection signal; None if undetermined."""
    try:
        if hasattr(mesh, "is_self_intersecting"):
            val = mesh.is_self_intersecting
            if callable(val):
                val = val()
            if val:
                return 1
    except Exception:
        pass
    # Multi-body overlap: split and check pairwise bounding-box + volume overlap
    try:
        parts = mesh.split(only_watertight=False)
        # Raw AI meshes can have 100k+ loose fragments; pairwise checks are O(n^2).
        # Cap overlap test to the largest MAX_OVERLAP_PARTS bodies (by face count).
        if len(parts) > MAX_OVERLAP_PARTS:
            parts = sorted(parts, key=lambda q: len(q.faces), reverse=True)[:MAX_OVERLAP_PARTS]
        if len(parts) >= 2:
            hits = 0
            for i in range(len(parts)):
                for j in range(i + 1, len(parts)):
                    a, b = parts[i], parts[j]
                    # AABB overlap?
                    if (a.bounds[0] <= b.bounds[1]).all() and (b.bounds[0] <= a.bounds[1]).all():
                        # Sample points from A inside B
                        try:
                            pts = a.sample(50)
                            inside = b.contains(pts)
                            if bool(np.any(inside)):
                                hits += 1
                        except Exception:
                            # If contains fails, treat overlapping AABB of two volumes as suspect
                            if a.is_watertight and b.is_watertight:
                                hits += 1
            if hits:
                return hits
            return 0
    except Exception:
        pass
    return 0 if mesh.is_watertight else None


def thin_wall_min_mm(mesh: trimesh.Trimesh, samples: int = 200) -> float | None:
    """Estimate minimum thickness via inward ray samples along face normals."""
    if not mesh.is_watertight or len(mesh.faces) == 0:
        return None
    try:
        # Sample random face centroids
        idx = np.linspace(0, len(mesh.faces) - 1, num=min(samples, len(mesh.faces)), dtype=int)
        origins = mesh.triangles_center[idx]
        normals = mesh.face_normals[idx]
        # Ray inward
        locations, index_ray, _ = mesh.ray.intersects_location(
            origins - normals * 1e-4,
            -normals,
            multiple_hits=False,
        )
        if len(locations) == 0:
            return None
        # Distance from corresponding origins
        dists = np.linalg.norm(locations - origins[index_ray], axis=1)
        # Thickness ≈ 2 * distance to opposite surface for centered rays; for inward from surface ≈ distance
        return float(np.percentile(dists, 5))
    except Exception:
        return None


def preview_png(mesh: trimesh.Trimesh, out_path: Path) -> bool:
    """Render a simple preview PNG (matplotlib fallback; no GPU)."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        fig = plt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111, projection="3d")
        # Downsample faces for huge meshes
        faces = mesh.faces
        if len(faces) > 8000:
            sel = np.linspace(0, len(faces) - 1, 8000, dtype=int)
            faces = faces[sel]
        tris = mesh.vertices[faces]
        coll = Poly3DCollection(tris, alpha=0.85, linewidths=0.05, edgecolor="k")
        coll.set_facecolor((0.3, 0.65, 0.95, 0.9))
        ax.add_collection3d(coll)
        bounds = mesh.bounds
        center = bounds.mean(axis=0)
        span = (bounds[1] - bounds[0]).max() / 2 * 1.1
        ax.set_xlim(center[0] - span, center[0] + span)
        ax.set_ylim(center[1] - span, center[1] + span)
        ax.set_zlim(center[2] - span, center[2] + span)
        ax.set_axis_off()
        ax.view_init(elev=25, azim=45)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=120, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:
        print(f"preview failed: {e}")
        return False


def _orca_env() -> dict[str, str]:
    env = os.environ.copy()
    libs = [
        str(STUBS),
        str(LOCAL_LIB),
        str(ORCA_ROOT / "usr" / "lib"),
        str(ORCA_ROOT / "lib"),
    ]
    env["LD_LIBRARY_PATH"] = ":".join(libs + [env.get("LD_LIBRARY_PATH", "")])
    return env


def slice_with_orca(stl_path: Path, out_dir: Path) -> dict[str, Any]:
    """Run OrcaSlicer CLI; return slice metrics."""
    result: dict[str, Any] = {
        "attempted": False,
        "success": False,
        "print_time_s": None,
        "support_volume_mm3": None,
        "filament_mm3": None,
        "gcode_path": None,
        "stderr_tail": "",
        "returncode": None,
    }
    if not ORCA_BIN.exists():
        result["stderr_tail"] = "orca-slicer binary missing"
        return result
    if not MACHINE.exists() or not PROCESS.exists():
        result["stderr_tail"] = f"profiles missing: {MACHINE} / {PROCESS}"
        return result

    out_dir.mkdir(parents=True, exist_ok=True)
    filament = FILAMENT if FILAMENT.exists() else None
    cmd = [
        "xvfb-run",
        "-a",
        str(ORCA_BIN),
        "--orient",
        "1",
        "--arrange",
        "1",
        "--ensure-on-bed",
        "--load-settings",
        f"{MACHINE};{PROCESS}",
        "--slice",
        "0",
        "--outputdir",
        str(out_dir),
        str(stl_path),
    ]
    if filament:
        cmd[cmd.index("--load-settings") : cmd.index("--load-settings")]  # noop keep order
        # insert filaments after load-settings pair
        idx = cmd.index("--load-settings")
        cmd.insert(idx + 2, "--load-filaments")
        cmd.insert(idx + 3, str(filament))

    result["attempted"] = True
    try:
        proc = subprocess.run(
            cmd,
            env=_orca_env(),
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(out_dir),
        )
        result["returncode"] = proc.returncode
        result["stderr_tail"] = (proc.stderr or proc.stdout or "")[-2000:]
        # Find gcode
        gcodes = list(out_dir.glob("*.gcode")) + list(out_dir.rglob("*.gcode"))
        if gcodes:
            gcode = gcodes[0]
            result["gcode_path"] = str(gcode)
            result["success"] = True
            metrics = parse_gcode_metrics(gcode)
            result.update(metrics)
        elif proc.returncode == 0:
            # Some builds write .bgcode or 3mf only
            alts = list(out_dir.glob("*.bgcode")) + list(out_dir.glob("*.3mf"))
            if alts:
                result["gcode_path"] = str(alts[0])
                result["success"] = True
                result["stderr_tail"] += f"\nnote: no .gcode, found {alts[0].name}"
    except subprocess.TimeoutExpired:
        result["stderr_tail"] = "slice timeout (180s)"
    except Exception as e:
        result["stderr_tail"] = str(e)
    return result


def _parse_time_to_s(fragment: str) -> int | None:
    m = re.search(
        r"(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?",
        fragment,
        re.I,
    )
    if not m or not any(m.groups()):
        return None
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def parse_gcode_metrics(gcode_path: Path) -> dict[str, Any]:
    text = gcode_path.read_text(errors="ignore")
    out: dict[str, Any] = {
        "print_time_s": None,
        "support_volume_mm3": None,
        "filament_mm3": None,
    }
    # Orca/BBL: ; model printing time: 5h 14m 33s; total estimated time: 5h 21m 28s
    m = re.search(r"total estimated time:\s*([^;\n]+)", text, re.I)
    if m:
        out["print_time_s"] = _parse_time_to_s(m.group(1))
    if out["print_time_s"] is None:
        m = re.search(r"model printing time:\s*([^;\n]+)", text, re.I)
        if m:
            out["print_time_s"] = _parse_time_to_s(m.group(1))
    if out["print_time_s"] is None:
        m = re.search(
            r"estimated printing time.*?=\s*(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?",
            text,
            re.I,
        )
        if m and any(m.groups()):
            d, h, mi, s = (int(x) if x else 0 for x in m.groups())
            out["print_time_s"] = d * 86400 + h * 3600 + mi * 60 + s
    m = re.search(r"filament used \[mm3\]\s*=\s*([\d.]+)", text, re.I)
    if m:
        out["filament_mm3"] = float(m.group(1))
    else:
        m = re.search(r"filament used \[cm3\]\s*=\s*([\d.]+)", text, re.I)
        if m:
            out["filament_mm3"] = float(m.group(1)) * 1000.0
    # support volume soft signals
    m = re.search(r";\s*enable_support\s*=\s*(\d+)", text, re.I)
    enable = int(m.group(1)) if m else None
    m = re.search(r"support filament used \[mm3\]\s*=\s*([\d.]+)", text, re.I)
    if m:
        out["support_volume_mm3"] = float(m.group(1))
    elif enable == 0:
        out["support_volume_mm3"] = 0.0
    return out


def score_components(checks: dict[str, Any]) -> dict[str, Any]:
    """Weighted PrintReady Score 0–100."""
    weights = {
        "watertight": 20,
        "manifold": 15,
        "nonmanifold_edges": 10,
        "self_intersections": 10,
        "thin_walls": 10,
        "slice_success": 20,
        "print_time": 5,
        "support_volume": 10,
    }
    partial: dict[str, float] = {}

    partial["watertight"] = weights["watertight"] if checks["watertight"] else 0.0
    partial["manifold"] = weights["manifold"] if checks["is_manifold"] else 0.0

    nm = checks["nonmanifold_edge_count"]
    if nm == 0:
        partial["nonmanifold_edges"] = weights["nonmanifold_edges"]
    elif nm <= 5:
        partial["nonmanifold_edges"] = weights["nonmanifold_edges"] * 0.5
    else:
        partial["nonmanifold_edges"] = 0.0

    si = checks.get("self_intersection_count")
    if si is None:
        partial["self_intersections"] = weights["self_intersections"] * 0.5  # unknown → half
    elif si == 0 or si is False:
        partial["self_intersections"] = weights["self_intersections"]
    else:
        partial["self_intersections"] = 0.0

    tmin = checks.get("thin_wall_min_mm")
    if tmin is None:
        partial["thin_walls"] = weights["thin_walls"] * 0.5
    elif tmin >= THIN_WALL_MM:
        partial["thin_walls"] = weights["thin_walls"]
    elif tmin >= 0.4:
        partial["thin_walls"] = weights["thin_walls"] * 0.4
    else:
        partial["thin_walls"] = 0.0

    partial["slice_success"] = weights["slice_success"] if checks.get("slice_success") else 0.0

    # Soft metrics: full points if sliced; else 0
    if checks.get("slice_success"):
        partial["print_time"] = weights["print_time"]
        # Support: if None, half; if 0, full; else scale soft
        sv = checks.get("support_volume_mm3")
        if sv is None:
            partial["support_volume"] = weights["support_volume"] * 0.5
        elif sv <= 0:
            partial["support_volume"] = weights["support_volume"]
        else:
            # soft: more support → lower; cap at weight
            partial["support_volume"] = max(
                0.0, weights["support_volume"] * (1.0 - min(sv / 5000.0, 1.0))
            )
    else:
        partial["print_time"] = 0.0
        partial["support_volume"] = 0.0

    total = float(sum(partial.values()))
    hard_fail = (not checks["watertight"]) or (not checks.get("slice_success"))
    if hard_fail:
        total = min(total, 39.0)

    return {
        "score": round(total, 2),
        "partial": {k: round(v, 2) for k, v in partial.items()},
        "hard_fail": hard_fail,
        "weights": weights,
    }


def score_file(path: Path, out_scores: Path, out_renders: Path, skip_slice: bool = False) -> dict:
    mesh = load_mesh(path)
    scale = normalize_scale(mesh)
    # Export normalized STL for slicer
    with tempfile.TemporaryDirectory(prefix="pr_slice_") as td:
        td_path = Path(td)
        norm_stl = td_path / f"{path.stem}_norm50.stl"
        mesh.export(norm_stl)

        nm_count = count_nonmanifold_edges(mesh)
        is_manifold = nm_count == 0 and bool(mesh.is_watertight)
        # trimesh also has is_volume / is_watertight
        si = self_intersection_count(mesh)
        # Attempt trimesh broken check
        try:
            broken = int(len(trimesh.repair.broken_faces(mesh))) if hasattr(trimesh, "repair") else 0
        except Exception:
            broken = 0

        tmin = thin_wall_min_mm(mesh)
        # Plate/rod heuristic: smallest bbox extent is an upper bound on thickness
        min_extent = float(np.min(mesh.extents))
        if tmin is None or min_extent < tmin:
            # For near-planar solids, bbox min is the wall thickness
            if min_extent < THIN_WALL_MM * 2:
                tmin = min_extent if tmin is None else min(tmin, min_extent)

        if skip_slice:
            slice_info = {"attempted": False, "success": False, "stderr_tail": "skipped"}
        else:
            slice_out = td_path / "slice_out"
            slice_info = slice_with_orca(norm_stl, slice_out)

        checks = {
            "watertight": bool(mesh.is_watertight),
            "is_volume": bool(getattr(mesh, "is_volume", False)),
            "is_manifold": bool(is_manifold),
            "nonmanifold_edge_count": int(nm_count),
            "self_intersection_count": si,
            "broken_faces": broken,
            "body_count": int(mesh.body_count) if hasattr(mesh, "body_count") else None,
            "thin_wall_min_mm": tmin,
            "slice_success": bool(slice_info.get("success")),
            "print_time_s": slice_info.get("print_time_s"),
            "support_volume_mm3": slice_info.get("support_volume_mm3"),
            "filament_mm3": slice_info.get("filament_mm3"),
        }
        scored = score_components(checks)

        render_path = out_renders / f"{path.stem}.png"
        preview_ok = preview_png(mesh, render_path)

        payload = {
            "id": path.stem,
            "source": str(path),
            "scored_at": _now(),
            "timezone_note": "America/New_York (box-local)",
            "normalize_longest_mm": TARGET_LONGEST_MM,
            "applied_scale": scale,
            "extents_mm": mesh.extents.tolist(),
            "faces": int(len(mesh.faces)),
            "vertices": int(len(mesh.vertices)),
            "checks": checks,
            "slice": {
                "attempted": slice_info.get("attempted"),
                "success": slice_info.get("success"),
                "returncode": slice_info.get("returncode"),
                "gcode_path": slice_info.get("gcode_path"),
                "stderr_tail": slice_info.get("stderr_tail", "")[-500:],
            },
            "score": scored,
            "preview_png": str(render_path) if preview_ok else None,
            "slicer": {
                "name": "OrcaSlicer",
                "version": "2.4.2",
                "machine": str(MACHINE.name),
                "process": str(PROCESS.name),
                "filament": str(FILAMENT.name) if FILAMENT.exists() else None,
            },
        }

        out_scores.mkdir(parents=True, exist_ok=True)
        out_path = out_scores / f"{path.stem}.json"
        out_path.write_text(json.dumps(payload, indent=2))
        return payload


def main():
    ap = argparse.ArgumentParser(description="PrintReady AI mesh scorer")
    ap.add_argument("meshes", nargs="+", type=Path, help="STL/OBJ/GLB paths")
    ap.add_argument("--scores-dir", type=Path, default=ROOT / "scores")
    ap.add_argument("--renders-dir", type=Path, default=ROOT / "renders")
    ap.add_argument("--skip-slice", action="store_true")
    args = ap.parse_args()

    summaries = []
    for m in args.meshes:
        print(f"=== Scoring {m} ===")
        try:
            payload = score_file(m, args.scores_dir, args.renders_dir, skip_slice=args.skip_slice)
            s = payload["score"]["score"]
            print(
                f"  score={s} watertight={payload['checks']['watertight']} "
                f"nm_edges={payload['checks']['nonmanifold_edge_count']} "
                f"slice={payload['checks']['slice_success']} "
                f"preview={payload['preview_png']}"
            )
            summaries.append(
                {
                    "id": payload["id"],
                    "score": s,
                    "hard_fail": payload["score"]["hard_fail"],
                    "watertight": payload["checks"]["watertight"],
                    "slice": payload["checks"]["slice_success"],
                }
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            summaries.append({"id": m.stem, "error": str(e)})

    summary_path = args.scores_dir / "summary.json"
    summary_path.write_text(
        json.dumps({"scored_at": _now(), "results": summaries}, indent=2)
    )
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
