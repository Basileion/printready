"""Regression (RT-20261107-68): raw is_watertight True must never become False after cleanup.

Runs on every local GLB under gens/<generator>/T*.glb. Also a synthetic check: a closed
cube with a zero-area sliver triangle split must stay watertight.
"""
from pathlib import Path
import sys
import numpy as np
import trimesh
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from score_mesh import load_mesh, drop_export_padding

ROOT = Path(__file__).resolve().parents[2]


def sliver_cube():
    """Closed cube where one edge a-b is split by collinear k and closed by a zero-area sliver (k,a,b)."""
    m = trimesh.creation.box()
    v = m.vertices.tolist(); f = m.faces.tolist()
    a, b, c = f[0]
    v.append(((np.array(v[a]) + np.array(v[b])) / 2).tolist()); k = len(v) - 1
    f[0] = [a, k, c]; f.append([k, b, c]); f.append([k, a, b])
    return trimesh.Trimesh(v, f, process=False)


def test_synthetic_sliver():
    mesh = sliver_cube()
    assert mesh.is_watertight
    assert (~mesh.nondegenerate_faces()).sum() == 1  # one zero-area face, distinct indices
    cleaned, info = drop_export_padding(mesh)
    assert cleaned.is_watertight, "zero-area sliver drop tore a hole"
    assert info["export_padding_faces"] == 0


def test_real_glbs():
    n = 0
    for p in sorted((ROOT / "gens").glob("*/T*.glb")):
        mesh = load_mesh(p)
        if mesh.is_watertight:
            cleaned, _ = drop_export_padding(mesh)
            assert cleaned.is_watertight, f"cleanup broke watertight: {p}"
            n += 1
    return n


if __name__ == "__main__":
    test_synthetic_sliver()
    print("ok", test_real_glbs(), "watertight meshes stayed watertight")
