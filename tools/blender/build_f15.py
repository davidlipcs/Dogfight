"""Builds the F-15EX Eagle II in Blender and exports it (models/f15/f15.glb, web/assets/f15.glb).

    python tools/blender/build_f15.py            (with the bpy module)

The shape: f15_shape.py (measured off the three-view), the meshes: f15_mesh.py (jk_mesh), the paint: f15_paint.py,
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
import f15_mesh as M  # noqa: E402
import f15_paint  # noqa: E402
import f15_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, f15_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "f15")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.50, 0.52, 0.55)), \
        Part("matte", None, color=C_DARK)
    Y0 = S.Y0
    for s in (-1, 1):                                       # angle of attack probes; the intake ramps' hinges
        prism(grey, (s * 0.40, Y0 - 2.20, 0.20), (0, 1, 0), (s, 0, 0), [(0, 0), (-0.10, 0), (-0.10, 0.10), (-0.02, 0.10)], 0.006)
    prism(grey, (0, Y0 - 9.00, float(S.SPINE(Y0 - 9.00))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.35, 0.0), (-0.40, 0.15), (-0.24, 0.15)], 0.012)
    # the M61 port in the right wing root
    tube(dark, [(1.55, Y0 - 8.10, 0.70), (1.55, Y0 - 8.35, 0.70)], 0.04, 8, C_BLACK)
    build_object("details", [metal, grey, dark])


def stores():
    B.wing_stores(S, ((8, 4.55), (7, 2.55)), fus=(1.70, S.Y0 - 10.5, -0.40), depth=0.40)


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.35,
                   nose_doors=[((0.20, gn["y"] + 0.80, zk - 0.02), (0.20, gn["y"] - 0.45, zk - 0.02),
                                (0.22, gn["y"] + 0.20, zk - 0.42), 86.0)],
                   main_hinge=(gm["x"] - 0.30, gm["y"] + 0.30, -0.50),
                   main_doors=[((1.10, gm["y"] + 0.85, -0.70), (1.10, gm["y"] - 0.70, -0.70), (1.22, gm["y"] + 0.05, -1.25), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, S.Y0 - 17.40, 0.30), vapor=(1.90, S.Y0 - 9.20, 0.62), gun=(1.55, S.Y0 - 8.10, 0.70))


B.build_jet(S, M, f15_paint.painter, "f15", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.44, seat_y=S.Y0 - 5.00, rear_seats=(S.Y0 - 6.75,)))
