"""Builds the Chengdu J-20 in Blender and exports it (models/j20/j20.glb, web/assets/j20.glb).

    python tools/blender/build_j20.py            (with the bpy module)

The shape: j20_shape.py (measured off the three-view), the meshes: j20_mesh.py (jk_mesh), the paint: j20_paint.py,
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
import j20_mesh as M  # noqa: E402
import j20_paint  # noqa: E402
import j20_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, j20_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, box, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "j20")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.48, 0.50, 0.53)), \
        Part("matte", None, color=C_DARK)
    B.pitot(metal, S.Y_NOSE - 0.02, S.Y_PITOT, -0.22, r=0.025, vanes=True)
    prism(grey, (0, -2.00, float(S.SPINE(-2.00))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.30, 0.0), (-0.34, 0.14), (-0.20, 0.14)], 0.012)
    # the EOTS window under the nose
    box(dark, (0.0, 7.60, float(S.KEEL(7.60)) - 0.02), (0.14, 0.22, 0.03), color=(0.12, 0.13, 0.15))
    build_object("details", [metal, grey, dark])


def stores():
    B.wing_stores(S, ((8, 5.40), (7, 4.30)), fus=(0.55, -2.50, float(S.KEEL(-2.50))), depth=0.26)


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.35,
                   nose_doors=[((0.22, gn["y"] + 0.85, zk - 0.02), (0.22, gn["y"] - 0.45, zk - 0.02),
                                (0.25, gn["y"] + 0.20, zk - 0.42), 86.0)],
                   main_hinge=(gm["x"] - 0.40, gm["y"] + 0.20, -0.60),
                   main_doors=[((1.00, gm["y"] + 0.80, -1.00), (1.00, gm["y"] - 0.70, -1.00), (1.14, gm["y"] + 0.05, -1.55), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, -9.95, 0.05), vapor=(2.20, -0.50, 0.15), gun=(0.0, 3.0, -0.90))


B.build_jet(S, M, j20_paint.painter, "j20", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.40))
