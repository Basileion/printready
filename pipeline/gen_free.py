#!/usr/bin/env python3
"""Free $0 benchmark generation: locked text prompt -> FLUX.1-schnell reference image (seed 1234)
-> image-to-3D on public HF Spaces (Hunyuan3D-2 / Hunyuan3D-2.1 shape-only, TRELLIS). Same image for every generator."""
import json, re, shutil, sys, time
from pathlib import Path
from gradio_client import Client, handle_file
ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT/"samples"/"images"; IMG.mkdir(parents=True, exist_ok=True)
GENS = ROOT/"gens"; LOG = GENS/"runs.jsonl"; GENS.mkdir(exist_ok=True)
SUFFIX = ", single object centered on plain white background, product photo, soft diffuse light"
rows = dict(re.findall(r"^\| (T\d\d) \| `([^`]+)`", (ROOT/"PROMPTS.md").read_text(), re.M))
ids = sys.argv[1:] or list(rows)[:10]
_c = {}
def cl(s):
    if s not in _c: _c[s] = Client(s, verbose=False)
    return _c[s]
def log(rec):
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z"); print(json.dumps(rec)[:300], flush=True)
    with LOG.open("a") as f: f.write(json.dumps(rec)+"\n")
def hunyuan(img):
    r = cl("tencent/Hunyuan3D-2").predict(caption=None, image=handle_file(str(img)), mv_image_front=None, mv_image_back=None,
        mv_image_left=None, mv_image_right=None, steps=30, guidance_scale=5.0, seed=1234, octree_resolution=256,
        check_box_rembg=True, num_chunks=8000, randomize_seed=False, api_name="/shape_generation")
    f=r[0]
    return f.get('value') or f.get('path') if isinstance(f,dict) else f
def hunyuan21(img):
    r = cl("tencent/Hunyuan3D-2.1").predict(image=handle_file(str(img)), mv_image_front=None, mv_image_back=None,
        mv_image_left=None, mv_image_right=None, steps=30, guidance_scale=5.0, seed=1234, octree_resolution=256,
        check_box_rembg=True, num_chunks=8000, randomize_seed=False, api_name="/shape_generation")
    f=r[0]
    return f.get('value') or f.get('path') if isinstance(f,dict) else f
def trellis(img):
    c = cl("trellis-community/TRELLIS")
    try: c.predict(api_name="/start_session")
    except Exception: pass
    pre = c.predict(image=handle_file(str(img)), api_name="/preprocess_image")
    r = c.predict(image=handle_file(pre if isinstance(pre,str) else pre["path"]), multiimages=[], seed=1234, ss_guidance_strength=7.5,
        ss_sampling_steps=12, slat_guidance_strength=3.0, slat_sampling_steps=12, multiimage_algo="stochastic",
        mesh_simplify=0.95, texture_size=1024, api_name="/generate_and_extract_glb")
    return r[2] if isinstance(r[2], str) else r[1]
import os
GEN = {k:v for k,v in {"hunyuan3d2": hunyuan, "hunyuan3d21": hunyuan21, "trellis": trellis}.items() if k in os.environ.get("GENS","hunyuan3d2,trellis").split(",")}
for pid in ids:
    img = IMG/f"{pid}.webp"
    if not img.exists():
        r = cl("black-forest-labs/FLUX.1-schnell").predict(prompt=rows[pid]+SUFFIX, seed=1234, randomize_seed=False,
            width=1024, height=1024, num_inference_steps=4, api_name="/infer")
        shutil.copy(r[0], img)
    for g, fn in GEN.items():
        out = GENS/g/f"{pid}.glb"; out.parent.mkdir(exist_ok=True)
        if out.exists(): continue
        t = time.time()
        try:
            shutil.copy(fn(img), out); log({"id": pid, "gen": g, "ok": True, "secs": round(time.time()-t), "prompt": rows[pid]})
        except Exception as e:
            log({"id": pid, "gen": g, "ok": False, "secs": round(time.time()-t), "err": repr(e)[:300]})
