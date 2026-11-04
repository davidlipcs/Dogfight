"""Builds the T-45C Goshawk in Blender and exports it (models/t45/t45.glb, web/assets/t45.glb).

    python tools/blender/build_t45.py            (with the bpy module)

The shape: t45_shape.py (measured off the three-view), the meshes: t45_mesh.py (jk_mesh), the paint: t45_paint.py,
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
import t45_mesh as M  # noqa: E402
import t45_paint  # noqa: E402
import t45_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, t45_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, empty, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "t45")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.70, 0.71, 0.72)), \
        Part("matte", None, color=C_DARK)
    B.pitot(metal, S.Y_NOSE - 0.02, S.Y_PITOT, 0.02, r=0.020)
    prism(grey, (0, S.Y0 - 6.40, float(S.SPINE(S.Y0 - 6.40))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.25, 0.0), (-0.28, 0.12), (-0.18, 0.12)], 0.010)
    # the arrester hook under the tail
    tube(dark, [(0.0, S.Y0 - 9.6, -0.02), (0.0, S.Y0 - 11.2, -0.12)], [0.035, 0.03], 8, C_BLACK)
    build_object("details", [metal, grey, dark])


def stores():
    for stn, p in ((8, (3.3, S.Y0 - 7.3, -0.05)), (7, (2.4, S.Y0 - 7.1, -0.08)), (6, (1.5, S.Y0 - 6.9, -0.10)),
                   (5, (0.0, S.Y0 - 6.5, -0.30))):          # (the trainer carries nothing; the game wants the points)
        empty("store_%d" % stn, p)
        empty("store_%d" % (9 - stn), (-p[0], p[1], p[2]))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.25,
                   nose_doors=[((0.14, gn["y"] + 0.55, zk - 0.02), (0.14, gn["y"] - 0.30, zk - 0.02),
                                (0.16, gn["y"] + 0.12, zk - 0.28), 86.0)],
                   main_hinge=(1.30, gm["y"] + 0.10, 0.05),
                   main_doors=[((1.25, gm["y"] + 0.50, 0.08), (1.25, gm["y"] - 0.40, 0.08), (1.35, gm["y"] + 0.05, -0.32), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, S.Y0 - 11.95, 0.70), vapor=(1.00, S.Y0 - 6.00, 0.15), gun=(0.0, S.Y0 - 1.0, 0.1))


B.build_jet(S, M, t45_paint.painter, "t45", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.36, seat_y=S.Y0 - 3.70, rear_seats=(S.Y0 - 5.00,)))
