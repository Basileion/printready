#!/usr/bin/env python3
"""Generate locked core text prompts via free public HF Space tencent/Hunyuan3D-2 (shape only, fixed seed)."""
import json, re, shutil, sys, time
from pathlib import Path
from gradio_client import Client
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "gens" / "hunyuan3d2"; OUT.mkdir(parents=True, exist_ok=True)
rows = re.findall(r"^\| (T\d\d) \| `([^`]+)`", (ROOT/"PROMPTS.md").read_text(), re.M)
ids = sys.argv[1:] or [r[0] for r in rows[:10]]
c = Client("tencent/Hunyuan3D-2", verbose=False)
log = OUT / "runs.jsonl"
for pid, prompt in rows:
    if pid not in ids or (OUT / f"{pid}.glb").exists(): continue
    t = time.time()
    try:
        r = c.predict(caption=prompt, image=None, mv_image_front=None, mv_image_back=None, mv_image_left=None, mv_image_right=None,
                      steps=30, guidance_scale=5.0, seed=1234, octree_resolution=256, check_box_rembg=True, num_chunks=8000,
                      randomize_seed=False, api_name="/shape_generation")
        shutil.copy(r[0], OUT / f"{pid}{Path(r[0]).suffix or '.glb'}")
        rec = {"id": pid, "ok": True, "secs": round(time.time()-t), "stats": r[2], "seed": r[3]}
    except Exception as e:
        rec = {"id": pid, "ok": False, "secs": round(time.time()-t), "err": repr(e)[:300]}
    rec.update(prompt=prompt, generator="Hunyuan3D-2 (HF Space tencent/Hunyuan3D-2, shape-only)", ts=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    print(json.dumps(rec)[:400], flush=True)
    with log.open("a") as f: f.write(json.dumps(rec)+"\n")
