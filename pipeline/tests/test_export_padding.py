"""Regression: Space GLB export-padding must not flip watertight to false."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from score_mesh import load_mesh, drop_export_padding

ROOT = Path(__file__).resolve().parents[2]
GLBS = ROOT / "gens" / "hunyuan3d2"

def test_hunyuan_padding_cleanup():
    assert GLBS.exists(), "gens/hunyuan3d2 missing (local-only fixtures)"
    results = {}
    for tid in ["T01", "T02", "T03", "T04", "T05", "T06"]:
        mesh = load_mesh(GLBS / f"{tid}.glb")
        cleaned, info = drop_export_padding(mesh)
        results[tid] = (cleaned.is_watertight, info["export_padding_faces"])
    # 5 of 6 watertight after padding drop; T05 remains open
    wt = [tid for tid, (w, _) in results.items() if w]
    assert len(wt) == 5, results
    assert results["T05"][0] is False
    for tid in ["T01", "T02", "T03", "T04", "T06"]:
        assert results[tid][1] > 0

if __name__ == "__main__":
    test_hunyuan_padding_cleanup()
    print("ok")
