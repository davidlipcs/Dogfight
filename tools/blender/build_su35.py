"""Builds the Su-35S Flanker-E in Blender and exports it (models/su35/su35.glb, web/assets/su35.glb).

    python tools/blender/build_su35.py            (with the bpy module)

The shape: su35_shape.py (measured off the three-view), the meshes: su35_mesh.py (jk_mesh), the paint: su35_paint.py,
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
import su35_mesh as M  # noqa: E402
import su35_paint  # noqa: E402
import su35_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, su35_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "su35")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.50, 0.56, 0.62)), \
        Part("matte", None, color=C_DARK)
    B.pitot(metal, S.Y_NOSE - 0.02, S.Y_PITOT, -0.42, r=0.03, vanes=False)
    ball = Part("glass", None)
    B.ball(ball, (0.22, 5.25, float(S.SPINE(5.25)) - 0.06), 0.15)          # OLS-35 ahead of the windscreen
    for s in (-1, 1):                                                        # pitot tubes on the nose sides
        tube(metal, [(s * 0.40, 8.40, -0.30), (s * 0.40, 8.85, -0.30)], [0.018, 0.012], 8)
    prism(grey, (0, -0.80, float(S.SPINE(-0.80))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.40, 0.0), (-0.45, 0.20), (-0.28, 0.20)], 0.014)
    prism(grey, (0, 1.80, float(S.KEEL(1.80))), (0, 1, 0), (0, 0, -1), [(0.0, 0.0), (-0.32, 0.0), (-0.36, 0.14), (-0.2, 0.14)], 0.012)
    tube(dark, [(0.98, 2.25, 0.20), (0.98, 1.95, 0.20)], 0.05, 10, C_BLACK)       # GSh-30-1, right LERX root
    build_object("details", [metal, grey, dark, ball])


def stores():
    B.wing_stores(S, ((8, 6.20), (7, 4.70), (6, 3.40)), fus=(1.05, -0.80, float(S.NACELLE[3](-0.80))))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.35,
                   nose_doors=[((0.24, gn["y"] + 0.95, zk - 0.02), (0.24, gn["y"] - 0.45, zk - 0.02),
                                (0.27, gn["y"] + 0.25, zk - 0.45), 86.0)],
                   main_hinge=(gm["x"] - 0.06, gm["y"] - 0.25, -0.05),
                   main_doors=[((1.80, gm["y"] + 0.85, -0.25), (1.80, gm["y"] - 0.75, -0.25), (1.94, gm["y"] + 0.05, -0.95), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, -11.08, 0.0), vapor=(1.70, 1.60, 0.03), gun=(0.98, 1.95, 0.20))


B.build_jet(S, M, su35_paint.painter, "su35", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.44))
