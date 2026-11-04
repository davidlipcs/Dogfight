"""Builds the F-16C Fighting Falcon in Blender and exports it (models/f16/f16.glb, web/assets/f16.glb).

    python tools/blender/build_f16.py            (with the bpy module)

The shape: f16_shape.py (measured off the three-view), the meshes: f16_mesh.py (jk_mesh), the paint: f16_paint.py,
the game's objects and reference points: jk_blend.py.
"""

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "tools", "blender")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402,F401
import numpy as np  # noqa: E402

import aircraft_lib as L  # noqa: E402
import jk  # noqa: E402
import jk_blend as B  # noqa: E402
import jk_mesh  # noqa: E402
import jk_paint  # noqa: E402
import f16_mesh as M  # noqa: E402
import f16_paint  # noqa: E402
import f16_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, f16_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, empty, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "f16")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.50, 0.52, 0.54)), \
        Part("matte", None, color=C_DARK)
    Y0 = S.Y0
    B.pitot(metal, S.Y_NOSE - 0.02, S.Y_PITOT, 0.02, r=0.025)
    for s in (-1, 1):                                       # angle of attack probes, the strake light fairings
        prism(grey, (s * 0.30, Y0 - 1.60, 0.20), (0, 1, 0), (s, 0, 0), [(0, 0), (-0.08, 0), (-0.08, 0.08), (-0.02, 0.08)], 0.005)
    prism(grey, (0, Y0 - 7.40, float(S.SPINE(Y0 - 7.40))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.30, 0.0), (-0.34, 0.12), (-0.20, 0.12)], 0.012)
    # the drag chute housing at the fin root, the M61 port in the left strake
    tube(grey, [(0.0, Y0 - 13.90, 1.55), (0.0, Y0 - 14.75, 1.58)], [0.12, 0.13], 12, (0.50, 0.52, 0.54))
    tube(dark, [(-0.62, Y0 - 5.60, 0.62), (-0.62, Y0 - 5.85, 0.62)], 0.035, 8, C_BLACK)
    build_object("details", [metal, grey, dark])


def stores():
    B.wing_stores(S, ((7, 3.40), (6, 2.40)), fus=(0.0, S.Y0 - 8.60, float(S.NACELLE[3](S.Y0 - 8.60))), depth=0.30)
    xt = S.TIP_POD["x"]
    for stn, p in ((8, (xt, (S.TIP_POD["y0"] + S.TIP_POD["y1"]) * 0.5, 0.60 - 0.13)),):
        empty("store_%d" % stn, p)
        empty("store_%d" % (9 - stn), (-p[0], p[1], p[2]))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.NACELLE[3](gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.30,
                   nose_doors=[((0.16, gn["y"] + 0.70, zk - 0.02), (0.16, gn["y"] - 0.35, zk - 0.02),
                                (0.18, gn["y"] + 0.18, zk - 0.35), 86.0)],
                   main_hinge=(gm["x"] - 0.40, gm["y"] + 0.20, -0.10),
                   main_doors=[((0.70, gm["y"] + 0.70, -0.35), (0.70, gm["y"] - 0.55, -0.35), (0.82, gm["y"] + 0.05, -0.85), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, S.Y0 - 14.80, 1.58), vapor=(1.30, S.Y0 - 7.40, 0.60), gun=(-0.62, S.Y0 - 5.60, 0.62))


B.build_jet(S, M, f16_paint.painter, "f16", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.38))
