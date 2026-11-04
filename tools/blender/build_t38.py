"""Builds the T-38C Talon in Blender and exports it (models/t38/t38.glb, web/assets/t38.glb).

    python tools/blender/build_t38.py            (with the bpy module)

The shape: t38_shape.py (measured off the three-view), the meshes: t38_mesh.py (jk_mesh), the paint: t38_paint.py,
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
import t38_mesh as M  # noqa: E402
import t38_paint  # noqa: E402
import t38_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, t38_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, empty, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "t38")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.70, 0.71, 0.72)), \
        Part("matte", None, color=C_DARK)
    B.pitot(metal, S.Y_NOSE - 0.02, S.Y_PITOT, 0.0, r=0.022)
    prism(grey, (0, S.Y0 - 7.20, float(S.SPINE(S.Y0 - 7.20))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.25, 0.0), (-0.28, 0.12), (-0.18, 0.12)], 0.010)
    build_object("details", [metal, grey, dark])


def stores():
    for stn, p in ((8, (3.0, S.Y0 - 9.4, -0.40)), (7, (2.2, S.Y0 - 9.2, -0.40)), (6, (1.4, S.Y0 - 9.0, -0.42)),
                   (5, (0.0, S.Y0 - 8.5, -0.55))):          # (the trainer carries nothing; the game wants the points)
        empty("store_%d" % stn, p)
        empty("store_%d" % (9 - stn), (-p[0], p[1], p[2]))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.25,
                   nose_doors=[((0.14, gn["y"] + 0.55, zk - 0.02), (0.14, gn["y"] - 0.30, zk - 0.02),
                                (0.16, gn["y"] + 0.12, zk - 0.28), 86.0)],
                   main_hinge=(0.70, gm["y"] + 0.10, -0.30),
                   main_doors=[((0.62, gm["y"] + 0.55, -0.38), (0.62, gm["y"] - 0.45, -0.38), (0.72, gm["y"] + 0.05, -0.78), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, S.Y0 - 13.75, 0.10), vapor=(1.00, S.Y0 - 7.60, -0.15), gun=(0.0, S.Y0 - 1.0, 0.0))


B.build_jet(S, M, t38_paint.painter, "t38", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.34, seat_y=S.Y0 - 4.05, rear_seats=(S.Y0 - 5.50,)))
