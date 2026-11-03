"""Builds the MiG-31 Foxhound in Blender and exports it (models/mig31/mig31.glb, web/assets/mig31.glb).

    python tools/blender/build_mig31.py            (with the bpy module)

The shape: mig31_shape.py (measured off the three-view), the meshes: mig31_mesh.py (jk_mesh), the paint: mig31_paint.py,
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
import mig31_mesh as M  # noqa: E402
import mig31_paint  # noqa: E402
import mig31_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, mig31_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "mig31")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.55, 0.57, 0.59)), \
        Part("matte", None, color=C_DARK)
    B.pitot(metal, S.Y_NOSE - 0.02, S.Y_PITOT, -0.45, r=0.035)
    for s in (-1, 1):                                                       # angle of attack vanes
        prism(grey, (s * 0.52, 8.70, -0.30), (0, 1, 0), (s, 0, 0), [(0, 0), (-0.10, 0), (-0.10, 0.10), (-0.02, 0.10)], 0.006)
    prism(grey, (0, 1.00, float(S.SPINE(1.00))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.40, 0.0), (-0.48, 0.30), (-0.30, 0.30)], 0.014)
    # the GSh-6-23 fairing low on the right side
    tube(grey, [(1.02, 0.60, -0.92), (1.02, -1.40, -0.92)], [0.10, 0.12], 10, (0.55, 0.57, 0.59))
    tube(dark, [(1.02, 0.62, -0.92), (1.02, 0.55, -0.92)], 0.05, 8, C_BLACK)
    build_object("details", [metal, grey, dark])


def stores():
    B.wing_stores(S, ((8, 5.60), (7, 4.40), (6, 3.20)), fus=(0.65, -2.20, float(S.KEEL(-2.20))))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.40,
                   nose_doors=[((0.26, gn["y"] + 1.00, zk - 0.02), (0.26, gn["y"] - 0.50, zk - 0.02),
                                (0.30, gn["y"] + 0.25, zk - 0.50), 86.0)],
                   main_hinge=(gm["x"] - 0.08, gm["y"] + 0.10, -0.40),
                   main_doors=[((1.88, gm["y"] + 0.95, -0.55), (1.88, gm["y"] - 0.85, -0.55), (2.02, gm["y"] + 0.05, -1.25), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, -10.88, 0.25), vapor=(2.20, 0.20, 0.62), gun=(1.02, 0.60, -0.92))


B.build_jet(S, M, mig31_paint.painter, "mig31", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.40, russian=True, seat_y=5.55))
