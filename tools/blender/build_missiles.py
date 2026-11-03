"""Builds the AIM-120C and AIM-9M missiles in Blender and exports them (models/missiles/*.glb, web/assets/*.glb).

Run it inside Blender (or with the bpy module):

    python -c "import bpy; exec(open('tools/blender/build_missiles.py').read())"

Nose towards +Y, origin in the middle of the missile; the game hangs them on the store_N points of the jets.
"""

import importlib
import math
import os
import sys

import bpy  # noqa: F401  (Blender context)
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "tools", "blender")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import aircraft_lib as L  # noqa: E402

importlib.reload(L)
from aircraft_lib import Part, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "missiles")
WEB = os.path.join(ROOT, "web", "assets")


def missile(body, fins, thick=0.012):
    """body: (y, radius, colour) stations nose first; fins: (outline in the (y, r) plane, colour), four of each."""
    part = Part("matte", None)
    for (ya, ra, col), (yb, rb, _c) in zip(body, body[1:]):
        tube(part, [(0, ya, 0), (0, yb, 0)], [ra, rb], 20, col, caps=False)
    part.ngon(tube(part, [(0, body[-1][0], 0), (0, body[-1][0] + 0.03, 0)], [body[-1][1], body[-1][1] * 0.7], 20,
                   (0.08, 0.08, 0.08), caps=False)[-1], (0.03, 0.03, 0.03))
    for outline, col in fins:
        for k in range(4):
            a = math.radians(45.0 + 90.0 * k)
            prism(part, (0, 0, 0), (0, 1, 0), (math.cos(a), 0.0, math.sin(a)), outline, thick, col)
    return part


def build_missiles():
    white, grey, dark = (0.80, 0.81, 0.80), (0.60, 0.62, 0.64), (0.22, 0.23, 0.25)
    amraam = missile(
        [(1.825, 0.004, white), (1.76, 0.030, white), (1.62, 0.058, white), (1.42, 0.080, white), (1.22, 0.089, grey),
         (0.98, 0.089, (0.72, 0.58, 0.10)), (0.93, 0.089, grey), (-0.52, 0.089, (0.42, 0.28, 0.14)), (-0.57, 0.089, grey),
         (-1.825, 0.089, grey)],
        [([(0.22, 0.08), (-0.12, 0.08), (-0.12, 0.225), (-0.02, 0.225)], grey),
         ([(-1.40, 0.08), (-1.80, 0.08), (-1.80, 0.225), (-1.66, 0.225)], grey)])
    sidewinder = missile(
        [(1.425, 0.012, (0.05, 0.05, 0.06)), (1.405, 0.034, (0.05, 0.05, 0.06)), (1.36, 0.052, dark), (1.28, 0.0635, dark),
         (1.02, 0.0635, white), (0.62, 0.0635, (0.72, 0.58, 0.10)), (0.58, 0.0635, white), (-1.425, 0.0635, white)],
        [([(1.27, 0.055), (1.03, 0.055), (1.03, 0.19), (1.09, 0.19)], dark),
         ([(-0.86, 0.055), (-1.41, 0.055), (-1.41, 0.315), (-1.13, 0.315)], white)], 0.010)
    return {"AIM-120C": amraam, "AIM-9M": sidewinder}


def main():
    L.begin("missiles", OUT, lambda pos, nrm, mode: np.zeros((len(pos), 2)), "MISSILES")
    for name, part in build_missiles().items():
        obj = build_object(name, [part])
        obj.parent = None
        obj["part"] = 2
    os.makedirs(OUT, exist_ok=True)
    for obj in list(bpy.context.scene.objects):
        obj.select_set(False)
    for obj in [o for o in bpy.context.scene.objects if o.get("part") == 2]:
        obj.location = (0.0, 0.0, 0.0)
        for folder in (OUT, WEB):
            for o in bpy.context.scene.objects:
                o.select_set(o == obj)
            path = os.path.join(folder, obj.name.lower().replace("-", "") + ".glb")
            bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                                      export_extras=True, export_cameras=False, export_lights=False,
                                      export_animations=False, export_vertex_color="MATERIAL")
            print("exported", path)


main()
