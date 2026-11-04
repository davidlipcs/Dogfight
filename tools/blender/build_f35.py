"""Builds the F-35A Lightning II in Blender and exports it (models/f35/f35.glb, web/assets/f35.glb).

    python tools/blender/build_f35.py            (with the bpy module)

The shape: f35_shape.py (measured off the three-view), the meshes: f35_mesh.py (jk_mesh), the paint: f35_paint.py,
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
import f35_mesh as M  # noqa: E402
import f35_paint  # noqa: E402
import f35_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, f35_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, box, build_object, empty, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "f35")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.45, 0.46, 0.46)), \
        Part("matte", None, color=C_DARK)
    # the EOTS window under the nose (the faceted sapphire)
    box(dark, (0.0, 6.55, float(S.KEEL(6.55)) - 0.01), (0.12, 0.20, 0.03), color=(0.15, 0.13, 0.10))
    prism(grey, (0, -1.00, float(S.SPINE(-1.00))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.30, 0.0), (-0.34, 0.12), (-0.20, 0.12)], 0.012)
    # the GAU-22 gun fairing on the left shoulder
    tube(grey, [(-0.72, 2.40, 0.98), (-0.72, 0.60, 0.98)], [0.07, 0.09], 10, (0.45, 0.46, 0.46))
    tube(dark, [(-0.72, 2.42, 0.98), (-0.72, 2.36, 0.98)], 0.035, 8, C_BLACK)
    build_object("details", [metal, grey, dark])


def stores():
    B.wing_stores(S, ((8, 4.40), (7, 3.40)), fus=None, depth=0.24)
    for stn, p in ((5, (0.45, -0.80, -0.70)), (6, (0.80, -0.80, -0.65))):     # the weapon bays (internal)
        empty("store_%d" % stn, p)
        empty("store_%d" % (9 - stn), (-p[0], p[1], p[2]))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.30,
                   nose_doors=[((0.18, gn["y"] + 0.80, zk - 0.02), (0.18, gn["y"] - 0.40, zk - 0.02),
                                (0.20, gn["y"] + 0.20, zk - 0.40), 86.0)],
                   main_hinge=(gm["x"] - 0.35, gm["y"] + 0.20, -0.45),
                   main_doors=[((0.95, gm["y"] + 0.75, -0.75), (0.95, gm["y"] - 0.65, -0.75), (1.08, gm["y"] + 0.05, -1.30), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, -7.50, 0.55), vapor=(1.80, 0.20, 0.30), gun=(-0.72, 2.42, 0.98))


B.build_jet(S, M, f35_paint.painter, "f35", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.40))
