"""Builds the JAS 39C Gripen in Blender and exports it (models/gripen/gripen.glb, web/assets/gripen.glb).

    python tools/blender/build_gripen.py            (with the bpy module)

The shape: gripen_shape.py (measured off the three-view), the meshes: gripen_mesh.py (jk_mesh), the paint: gripen_paint.py,
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
import gripen_mesh as M  # noqa: E402
import gripen_paint  # noqa: E402
import gripen_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, gripen_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "gripen")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.45, 0.50, 0.57)), \
        Part("matte", None, color=C_DARK)
    B.pitot(metal, S.Y_NOSE - 0.02, S.Y_PITOT, -0.05, r=0.025)
    for s in (-1, 1):                                                       # angle of attack vanes
        prism(grey, (s * 0.30, 4.80, 0.05), (0, 1, 0), (s, 0, 0), [(0, 0), (-0.08, 0), (-0.08, 0.07), (-0.02, 0.07)], 0.005)
    prism(grey, (0, -0.60, float(S.SPINE(-0.60))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.30, 0.0), (-0.36, 0.16), (-0.22, 0.16)], 0.012)
    tube(dark, [(-0.62, 1.20, -0.10), (-0.62, 0.95, -0.10)], 0.035, 8, C_BLACK)   # BK 27 port, left side
    build_object("details", [metal, grey, dark])


def stores():
    B.wing_stores(S, ((8, 3.40), (7, 2.50), (6, 1.55)), fus=(0.0, -1.00, float(S.KEEL(-1.00))), depth=0.24)


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.30,
                   nose_doors=[((0.17, gn["y"] + 0.70, zk - 0.02), (0.17, gn["y"] - 0.35, zk - 0.02),
                                (0.19, gn["y"] + 0.18, zk - 0.35), 86.0)],
                   main_hinge=(gm["x"] - 0.30, gm["y"] + 0.25, -0.20),
                   main_doors=[((0.72, gm["y"] + 0.70, -0.32), (0.72, gm["y"] - 0.55, -0.32), (0.85, gm["y"] + 0.05, -0.85), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, -6.10, 2.20), vapor=(1.60, 0.90, 0.55), gun=(-0.62, 0.95, -0.10))


B.build_jet(S, M, gripen_paint.painter, "gripen", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.36))
