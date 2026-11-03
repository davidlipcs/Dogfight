"""Quick check of a jet's airframe without Blender: <jet>_mesh.airframe() -> a plain .glb (flat colours), and an
overlay of its outline on the three-view drawing the shape was measured from.

    python tools/blender/preview.py mig29 out.glb
    python tools/blender/preview.py mig29 out.glb --overlay ref.json out_overlay.png

ref.json (kept with the drawings, outside the repository):
    {"image": "...drawing.jpg",
     "top":  {"box": [x0, y0, x1, y1], "X0": 598, "y0": 0.90, "Yc": 927, "ppm": 55.3},
     "side": {"box": [...], "X0": 604, "y0": 0.90, "Z0": 1405, "ppm": 55.3}}
(top: y = y0 + (X0 - X) / ppm, x = (Y - Yc) / ppm;  side: y = y0 + (X0 - X) / ppm, z = (Z0 - Y) / ppm;
"nose_right": true for a drawing with the nose to the right, "right_wing_up": true when the right wing is drawn
above the centre line in the top view)
"""

import importlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

COLOURS = {"paint": (170, 176, 182, 255), "glass": (60, 70, 60, 120), "dark": (25, 25, 28, 255), "metal": (120, 110, 100, 255)}


def triangles(piece):
    tris = []
    for f in piece.faces:
        for k in range(1, len(f) - 1):
            tris.append((f[0], f[k], f[k + 1]))
    return np.array(tris, int)


def to_glb(parts, path):
    import trimesh
    scene = trimesh.Scene()
    for name, p in parts.items():
        t = triangles(p)
        if not len(t):
            continue
        v = p.verts
        v_gl = np.stack([v[:, 0], v[:, 2], -v[:, 1]], axis=1)       # +Y up, -Z forward
        m = trimesh.Trimesh(v_gl, t, process=False)
        m.visual = trimesh.visual.ColorVisuals(m, face_colors=np.tile(COLOURS.get(p.mat, COLOURS["paint"]), (len(t), 1)))
        scene.add_geometry(m, node_name=name, geom_name=name)
    scene.export(path)
    return path


def overlay(parts, ref, out, skip=("duct", "nozzle_in")):
    from PIL import Image, ImageDraw
    img = Image.open(ref["image"]).convert("RGB")
    tris = []
    for name, p in parts.items():
        if any(name.startswith(s) for s in skip):
            continue
        t = triangles(p)
        if len(t):
            tris.append(p.verts[t])
    T = np.concatenate(tris)
    panels = []
    for view in ("top", "side"):
        r = ref.get(view)
        if not r:
            continue
        x0, y0, x1, y1 = r["box"]
        base = img.crop((x0, y0, x1, y1)).convert("RGBA")
        lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        sgn = 1.0 if r.get("nose_right") else -1.0         # the drawing's nose to the right: X grows with y
        X = r["X0"] + sgn * (T[..., 1] - r["y0"]) * r["ppm"] - x0
        if view == "top":
            Y = r["Yc"] + T[..., 0] * r["ppm"] * (-1.0 if r.get("right_wing_up") else 1.0) - y0
        else:
            Y = r["Z0"] - T[..., 2] * r["ppm"] - y0
        for k in range(len(T)):
            d.polygon([(X[k, 0], Y[k, 0]), (X[k, 1], Y[k, 1]), (X[k, 2], Y[k, 2])], fill=(255, 40, 40, 255))
        a = np.array(lay)
        a[..., 3] = (a[..., 3] > 0) * 95
        comp = Image.alpha_composite(base, Image.fromarray(a)).convert("RGB")
        panels.append(comp.resize((comp.width * 2, comp.height * 2)))
    W = max(p.width for p in panels)
    H = sum(p.height for p in panels)
    sheet = Image.new("RGB", (W, H), "white")
    yy = 0
    for p in panels:
        sheet.paste(p, (0, yy))
        yy += p.height
    sheet.save(out)
    return out


def main():
    jet, out = sys.argv[1], sys.argv[2]
    mesh = importlib.import_module(jet + "_mesh")
    parts = mesh.airframe()
    to_glb(parts, out)
    print("wrote", out, sum(len(triangles(p)) for p in parts.values()), "triangles")
    if "--overlay" in sys.argv:
        i = sys.argv.index("--overlay")
        ref = json.load(open(sys.argv[i + 1]))
        print("wrote", overlay(parts, ref, sys.argv[i + 2]))


if __name__ == "__main__":
    main()
