#!/usr/bin/env python3
"""RT-20261031-105 re-test: alpha-matte the locked FLUX refs locally (rembg, isnet-general-use) -> RGBA PNG.
Hunyuan3D-2.1 Space skips its own background removal for RGBA input when check_box_rembg=False."""
import sys
from pathlib import Path
from PIL import Image
from rembg import remove, new_session
ROOT = Path(__file__).resolve().parents[1]
s = new_session("isnet-general-use")
for pid in sys.argv[1:]:
    im = Image.open(ROOT/"samples"/"images"/f"{pid}.webp").convert("RGB")
    out = remove(im, session=s, post_process_mask=True)
    a = out.getchannel("A"); bbox = a.getbbox()
    out.save(ROOT/"samples"/"images_rgba"/f"{pid}.png")
    print(pid, out.mode, out.size, "alpha bbox", bbox, "opaque frac", round(sum(1 for v in a.getdata() if v>128)/(a.size[0]*a.size[1]),3))
