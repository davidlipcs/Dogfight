"""Builds the Su-57 Felon in Blender and exports it (models/su57/su57.glb, web/assets/su57.glb).

    python tools/blender/build_su57.py            (with the bpy module)

The shape: su57_shape.py (measured off the three-view), the meshes: su57_mesh.py (jk_mesh), the paint: su57_paint.py,
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
import su57_mesh as M  # noqa: E402
import su57_paint  # noqa: E402
import su57_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, su57_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "su57")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.45, 0.52, 0.60)), \
        Part("matte", None, color=C_DARK)
    ball = Part("glass", None)
    B.ball(ball, (0.22, 7.95, float(S.SPINE(7.95)) - 0.05), 0.13)         # 101KS-V IRST ahead of the windscreen
    for s in (-1, 1):                                                       # air data probes on the nose sides
        tube(metal, [(s * 0.36, 8.80, 0.27), (s * 0.36, 9.10, 0.27)], [0.016, 0.010], 8)
    prism(grey, (0, 2.00, float(S.SPINE(2.00))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.30, 0.0), (-0.34, 0.14), (-0.20, 0.14)], 0.012)
    tube(dark, [(0.85, 3.30, 0.75), (0.85, 3.00, 0.75)], 0.045, 10, C_BLACK)      # GSh-30-1 port, right of the canopy
    build_object("details", [metal, grey, dark, ball])


def stores():
    B.wing_stores(S, ((8, 6.00), (7, 4.90), (6, 3.70)), fus=(0.55, -1.20, float(S.KEEL(-1.20))))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.35,
                   nose_doors=[((0.24, gn["y"] + 0.95, zk - 0.02), (0.24, gn["y"] - 0.45, zk - 0.02),
                                (0.27, gn["y"] + 0.25, zk - 0.45), 86.0)],
                   main_hinge=(gm["x"] - 0.06, gm["y"] - 0.25, 0.10),
                   main_doors=[((2.04, gm["y"] + 0.85, -0.10), (2.04, gm["y"] - 0.75, -0.10), (2.18, gm["y"] + 0.05, -0.80), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, -10.02, 0.62), vapor=(2.30, 1.50, 0.44), gun=(0.85, 3.00, 0.75))


B.build_jet(S, M, su57_paint.painter, "su57", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.44))
