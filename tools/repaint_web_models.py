#!/usr/bin/env python3
"""Puts the paint schemes of the real aircraft (tools/make_roblox_models.LIVERIES: the photographs of the Hungarian MiG-29 and Gripen, the MiG-31,
Su-57, Su-35, Typhoon, Rafale, F-35, F/A-18 and J-20) into the paint textures of the browser game's own models (web/assets/<jet>.glb).
The shapes are not touched, only the base colour image of each model is replaced (JPEG, the same size).   python3 tools/repaint_web_models.py [jets]"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import make_roblox_models as M


def patch(path, spec):
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    off = 20 + n
    binlen = struct.unpack("<I", b[off:off + 4])[0]
    binc = b[off + 8:off + 8 + binlen]
    idx = None
    for i, im in enumerate(j["images"]):
        if "basecolor" in im.get("name", ""):
            idx = i
    if idx is None:
        return False
    bv = j["bufferViews"][j["images"][idx]["bufferView"]]
    old = Image.open(io.BytesIO(binc[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]])).convert("RGB")
    new = M.repaint(old, spec)
    buf = io.BytesIO()
    new.save(buf, "JPEG", quality=88)
    newbytes = buf.getvalue()
    # the binary chunk again, every buffer view in its place (the repainted image has its own length)
    order = sorted(range(len(j["bufferViews"])), key=lambda i: j["bufferViews"][i].get("byteOffset", 0))
    out = bytearray()
    for i in order:
        v = j["bufferViews"][i]
        data = newbytes if i == j["images"][idx]["bufferView"] else binc[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]]
        while len(out) % 4:
            out.append(0)
        v["byteOffset"] = len(out)
        v["byteLength"] = len(data)
        out += data
    while len(out) % 4:
        out.append(0)
    j["buffers"][0]["byteLength"] = len(out)
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(out)
    data = struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<I4s", len(js), b"JSON") + js + struct.pack("<I4s", len(out), b"BIN\0") + bytes(out)
    open(path, "wb").write(data)
    return True


def main(keys):
    for k in keys:
        p = os.path.join(M.SRC, k + ".glb")
        if k in M.LIVERIES and os.path.exists(p):
            before = os.path.getsize(p)
            patch(p, M.LIVERIES[k])
            print("%-8s %5d KB -> %5d KB" % (k, before // 1024, os.path.getsize(p) // 1024))


if __name__ == "__main__":
    main(sys.argv[1:] or list(M.LIVERIES))
