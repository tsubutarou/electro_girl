#!/usr/bin/env python
"""validate_atlas.py
atlas.png + atlas_map.json の必須スロットが揃っているかチェックします。

Usage:
  python tools/validate_atlas.py assets/sprite/atlas.png assets/sprite/atlas_map.json
"""
import json, sys, os
from PIL import Image

REQUIRED_SLOTS = [
  "body_idle","body_walk_0","body_walk_1","body_walk_2","body_sleep","body_drowsy",
  "clothes_idle","clothes_walk_0","clothes_walk_1","clothes_walk_2","clothes_sleep",
  "face_normal","face_blink","face_mouth"
]

def main():
    if len(sys.argv) < 3:
        print("Usage: python tools/validate_atlas.py atlas.png atlas_map.json")
        return 2
    atlas_png, atlas_map = sys.argv[1], sys.argv[2]
    if not os.path.exists(atlas_png) or not os.path.exists(atlas_map):
        print("Missing input files.")
        return 2
    with open(atlas_map, "r", encoding="utf-8") as f:
        m=json.load(f)
    slots=m.get("slots",{})
    missing=[s for s in REQUIRED_SLOTS if s not in slots]
    if missing:
        print("Missing slots:", ", ".join(missing))
    im=Image.open(atlas_png)
    print("Atlas size:", im.size, "tile_size:", m.get("tile_size"))
    print("OK" if not missing else "NG")
    return 0 if not missing else 1

if __name__=="__main__":
    raise SystemExit(main())
