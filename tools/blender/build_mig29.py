"""Builds the MiG-29 (9.12, Hungarian Air Force) in Blender and exports it (models/mig29/mig29.glb, web/assets/mig29.glb).

    python tools/blender/build_mig29.py            (with the bpy module)

The shape: mig29_shape.py (measured off the three-view), the meshes: mig29_mesh.py, the paint: mig29_paint.py,
the game's objects and reference points: jk_blend.py.
"""

import importlib
import math
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
import jk_paint  # noqa: E402
import mig29_mesh as M  # noqa: E402
import mig29_paint  # noqa: E402
import mig29_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, B, S, M, mig29_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_GREY, C_LIGHT, C_STEEL, Part, box, build_object, empty, prism, tube  # noqa

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "mig29")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.52, 0.55, 0.58)), \
        Part("matte", None, color=C_DARK)
    B.pitot(metal, S.Y_NOSE - 0.02, S.Y_PITOT, 0.045)
    ball = Part("glass", None)
    B.ball(ball, (0.16, 6.08, float(S.SPINE(6.08)) - 0.01), 0.13)          # IRST, right of the windscreen
    for s in (-1, 1):                                                       # angle of attack vanes
        prism(grey, (s * 0.33, 7.30, 0.10), (0, 1, 0), (s, 0, 0), [(0, 0), (-0.10, 0), (-0.10, 0.10), (-0.02, 0.10)], 0.006)
    prism(grey, (0, 1.60, float(S.SPINE(1.60))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.35, 0.0), (-0.40, 0.17), (-0.25, 0.17)], 0.012)
    prism(grey, (0, 3.70, float(S.KEEL(3.70))), (0, 1, 0), (0, 0, -1), [(0.0, 0.0), (-0.30, 0.0), (-0.35, 0.13), (-0.2, 0.13)], 0.012)
    tube(dark, [(-0.95, 2.70, 0.16), (-0.95, 2.35, 0.16)], 0.05, 10, C_BLACK)   # gun muzzle, left LERX root
    build_object("details", [metal, grey, dark, ball])


def stores():
    B.wing_stores(S, ((8, 4.65), (7, 3.60), (6, 2.55)), fus=(1.0, -0.85, float(S.NACELLE[3](-0.85))))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_doors=[((0.20, gn["y"] + 0.85, zk - 0.02), (0.20, gn["y"] - 0.45, zk - 0.02),
                                   (0.22, gn["y"] + 0.2, zk - 0.42), 86.0)],
                   main_doors=[((1.50, gm["y"] + 0.75, -0.30), (1.50, gm["y"] - 0.65, -0.30), (1.62, gm["y"] + 0.05, -0.95), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, -5.40, -0.12), vapor=(1.20, 3.30, 0.07), gun=(-0.95, 2.40, 0.16), strobe_y=-5.55)


B.build_jet(S, M, mig29_paint.painter, "mig29", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(floor_z=float(S.CANOPY_SILL_Z(4.0)) - 0.62, sill_z=float(S.CANOPY_SILL_Z(4.0)),
                         panel_z=float(S.CANOPY_SILL_Z(5.0)) + 0.05, russian=True))
