"""Builds the F/A-18E Super Hornet in Blender and exports it (models/fa18/fa18.glb, web/assets/fa18.glb).

    python tools/blender/build_fa18.py            (with the bpy module)

The shape: fa18_shape.py (measured off the three-view), the meshes: fa18_mesh.py (jk_mesh), the paint: fa18_paint.py,
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
import fa18_mesh as M  # noqa: E402
import fa18_paint  # noqa: E402
import fa18_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, fa18_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "fa18")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.50, 0.53, 0.57)), \
        Part("matte", None, color=C_DARK)
    Y0 = S.Y0
    # the retractable refuelling probe fairing on the right of the nose, the M61 port on top of the nose
    tube(grey, [(0.36, Y0 - 3.20, 0.62), (0.36, Y0 - 4.60, 0.70)], [0.05, 0.07], 10, (0.50, 0.53, 0.57))
    tube(dark, [(0.0, Y0 - 1.95, 0.62), (0.0, Y0 - 2.10, 0.66)], 0.04, 8, C_BLACK)
    for s in (-1, 1):                                               # the LEX fences, the angle of attack probes
        prism(grey, (s * 1.20, Y0 - 8.60, 0.36), (0, 1, 0), (0, 0, 1), [(0, 0), (-0.55, 0), (-0.55, 0.22), (-0.20, 0.22)], 0.012)
        prism(grey, (s * 0.40, Y0 - 1.80, 0.10), (0, 1, 0), (s, 0, 0), [(0, 0), (-0.10, 0), (-0.10, 0.10), (-0.02, 0.10)], 0.006)
    prism(grey, (0, Y0 - 10.80, float(S.SPINE(Y0 - 10.80))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.35, 0.0), (-0.40, 0.16), (-0.24, 0.16)], 0.012)
    build_object("details", [metal, grey, dark])


def stores():
    B.wing_stores(S, ((8, 5.30), (7, 4.10), (6, 2.90)), fus=(0.70, S.Y0 - 10.0, float(S.KEEL(S.Y0 - 10.0))), depth=0.34)


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.40,
                   nose_doors=[((0.22, gn["y"] + 0.90, zk - 0.02), (0.22, gn["y"] - 0.45, zk - 0.02),
                                (0.25, gn["y"] + 0.22, zk - 0.42), 86.0)],
                   main_hinge=(gm["x"] - 0.30, gm["y"] + 0.30, -0.45),
                   main_doors=[((1.05, gm["y"] + 0.85, -0.66), (1.05, gm["y"] - 0.70, -0.66), (1.18, gm["y"] + 0.05, -1.20), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, S.Y0 - 17.40, 0.10), vapor=(1.90, S.Y0 - 8.70, 0.36), gun=(0.0, S.Y0 - 1.95, 0.62))


B.build_jet(S, M, fa18_paint.painter, "fa18", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.42))
