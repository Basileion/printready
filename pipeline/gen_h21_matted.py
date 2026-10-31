#!/usr/bin/env python3
"""RT-20261031-105 re-test: Hunyuan3D-2.1 Space, same settings as gen_free.hunyuan21 (seed 1234, 30 steps, gs 5.0,
octree 256) but input = locally alpha-matted RGBA PNG and check_box_rembg=False."""
import json, shutil, sys, time
from pathlib import Path
from gradio_client import Client, handle_file
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT/"gens"/"hunyuan3d21_matted"; LOG = ROOT/"gens"/"runs.jsonl"
c = Client("tencent/Hunyuan3D-2.1", verbose=False)
for pid in sys.argv[1:]:
    out = OUT/f"{pid}.glb"
    if out.exists(): continue
    for attempt in range(3):
        t = time.time()
        try:
            r = c.predict(image=handle_file(str(ROOT/"samples"/"images_rgba"/f"{pid}.png")), mv_image_front=None, mv_image_back=None,
                mv_image_left=None, mv_image_right=None, steps=30, guidance_scale=5.0, seed=1234, octree_resolution=256,
                check_box_rembg=False, num_chunks=8000, randomize_seed=False, api_name="/shape_generation")
            f = r[0]; p = (f.get('value') or f.get('path')) if isinstance(f, dict) else f
            shutil.copy(p, out); rec = {"id": pid, "gen": "hunyuan3d21_matted", "ok": True, "secs": round(time.time()-t), "input": "rgba_rembg_isnet", "rembg_in_space": False}
        except Exception as e:
            rec = {"id": pid, "gen": "hunyuan3d21_matted", "ok": False, "secs": round(time.time()-t), "err": repr(e)[:300]}
        rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z"); print(json.dumps(rec)[:300], flush=True)
        with LOG.open("a") as fh: fh.write(json.dumps(rec)+"\n")
        if rec["ok"]: break
        time.sleep(60)
