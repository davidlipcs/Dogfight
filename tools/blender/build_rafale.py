"""Builds the Dassault Rafale C in Blender and exports it (models/rafale/rafale.glb, web/assets/rafale.glb).

    python tools/blender/build_rafale.py            (with the bpy module)

The shape: rafale_shape.py (measured off the three-view), the meshes: rafale_mesh.py (jk_mesh), the paint: rafale_paint.py,
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
import rafale_mesh as M  # noqa: E402
import rafale_paint  # noqa: E402
import rafale_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, rafale_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "rafale")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.30, 0.31, 0.34)), \
        Part("matte", None, color=C_DARK)
    B.pitot(metal, S.Y_NOSE - 0.02, S.Y_PITOT, -0.18, r=0.02, vanes=False)
    # the fixed refuelling probe on the right of the windscreen
    tube(grey, [(0.42, 4.20, 0.55), (0.42, 5.40, 0.62), (0.32, 5.85, 0.66)], [0.045, 0.040, 0.030], 10, (0.30, 0.31, 0.34))
    # the OSF sensors ahead of the windscreen
    ball = Part("glass", None)
    B.ball(ball, (0.0, 5.25, float(S.SPINE(5.25)) - 0.04), 0.09)
    prism(grey, (0, -0.80, float(S.SPINE(-0.80))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.28, 0.0), (-0.32, 0.14), (-0.20, 0.14)], 0.012)
    tube(dark, [(0.60, 1.40, -0.30), (0.60, 1.15, -0.30)], 0.035, 8, C_BLACK)      # GIAT 30 port, right intake
    build_object("details", [metal, grey, dark, ball])


def stores():
    B.wing_stores(S, ((8, 4.10), (7, 3.10), (6, 2.10)), fus=(0.55, -2.00, float(S.KEEL(-2.00))), depth=0.26)


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.30,
                   nose_doors=[((0.17, gn["y"] + 0.70, zk - 0.02), (0.17, gn["y"] - 0.35, zk - 0.02),
                                (0.19, gn["y"] + 0.18, zk - 0.35), 86.0)],
                   main_hinge=(gm["x"] - 0.40, gm["y"] + 0.20, -0.15),
                   main_doors=[((0.90, gm["y"] + 0.70, -0.32), (0.90, gm["y"] - 0.55, -0.32), (1.02, gm["y"] + 0.05, -0.85), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, -7.10, 3.40), vapor=(1.50, 0.40, 0.42), gun=(0.60, 1.15, -0.30))


B.build_jet(S, M, rafale_paint.painter, "rafale", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.36))
