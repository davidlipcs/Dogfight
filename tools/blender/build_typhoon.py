"""Builds the Eurofighter Typhoon in Blender and exports it (models/typhoon/typhoon.glb, web/assets/typhoon.glb).

    python tools/blender/build_typhoon.py            (with the bpy module)

The shape: typhoon_shape.py (measured off the three-view), the meshes: typhoon_mesh.py (jk_mesh), the paint: typhoon_paint.py,
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
import typhoon_mesh as M  # noqa: E402
import typhoon_paint  # noqa: E402
import typhoon_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, typhoon_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, box, build_object, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "typhoon")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.55, 0.57, 0.59)), \
        Part("matte", None, color=C_DARK)
    for s in (-1, 1):                                                       # the pitot probes on the nose sides
        tube(metal, [(s * 0.22, 6.90, 0.12), (s * 0.24, 7.40, 0.12)], [0.018, 0.010], 8)
    ball = Part("glass", None)
    B.ball(ball, (-0.22, 6.05, float(S.SPINE(6.05)) - 0.06), 0.10)        # PIRATE IRST, left of the windscreen
    prism(grey, (0, -0.50, float(S.SPINE(-0.50))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.28, 0.0), (-0.32, 0.15), (-0.20, 0.15)], 0.012)
    # the dorsal air intake at the fin root
    box(grey, (0.0, -3.45, float(S.SPINE(-3.45)) + 0.10), (0.18, 0.22, 0.10), color=(0.55, 0.57, 0.59))
    tube(dark, [(0.80, 1.80, 0.25), (0.80, 1.55, 0.25)], 0.035, 8, C_BLACK)        # Mauser BK 27, right wing root
    build_object("details", [metal, grey, dark, ball])


def stores():
    B.wing_stores(S, ((8, 4.20), (7, 3.20), (6, 2.20)), fus=(0.55, -1.50, float(S.KEEL(-1.50))), depth=0.26)


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.NACELLE[3](gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.30,
                   nose_doors=[((0.17, gn["y"] + 0.70, zk - 0.02), (0.17, gn["y"] - 0.35, zk - 0.02),
                                (0.19, gn["y"] + 0.18, zk - 0.35), 86.0)],
                   main_hinge=(gm["x"] - 0.45, gm["y"] + 0.20, -0.25),
                   main_doors=[((0.85, gm["y"] + 0.70, -0.55), (0.85, gm["y"] - 0.55, -0.55), (0.98, gm["y"] + 0.05, -1.05), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, -7.95, 3.20), vapor=(1.40, 1.30, 0.38), gun=(0.80, 1.55, 0.25))


B.build_jet(S, M, typhoon_paint.painter, "typhoon", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.38))
