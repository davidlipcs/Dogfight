"""Builds the F-22A Raptor in Blender and exports it (models/f22/f22.glb, web/assets/f22.glb).

    python tools/blender/build_f22.py            (with the bpy module)

The shape: f22_shape.py (measured off the three-view), the meshes: f22_mesh.py (jk_mesh), the paint: f22_paint.py,
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
import jk_mesh  # noqa: E402
import jk_paint  # noqa: E402
import f22_mesh as M  # noqa: E402
import f22_paint  # noqa: E402
import f22_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, f22_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, box, build_object, empty, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "f22")
WEB = os.path.join(ROOT, "web", "assets")


MAIN_STATIONS = {2: (-0.66, -0.75), 3: (-0.43, -0.35), 4: (-0.20, -0.75), 5: (0.20, -0.75), 6: (0.43, -0.35),
                 7: (0.66, -0.75)}            # AIM-120 in the main bay: (x, y in the earlier F-22's frame - the same here)
SIDE_STATIONS = {1: -1.0, 8: 1.0}               # AIM-9 in the side bays
TRAPEZE_L, TRAPEZE_PHI0, TRAPEZE_PHI1 = 0.75, 8.0, 90.0
SIDE_SLIDE = np.array([0.10, 0.0, -0.44])      # the AIM-9 rail pushes the missile out of the trunk


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.44, 0.45, 0.46)), \
        Part("matte", None, color=C_DARK)
    Y0 = S.Y0
    prism(grey, (0, Y0 - 9.20, float(S.SPINE(Y0 - 9.20))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.30, 0.0), (-0.34, 0.10), (-0.20, 0.10)], 0.012)
    # the M61 port over the right intake (closed door: a dark slit)
    box(dark, (1.20, Y0 - 7.30, 0.55), (0.04, 0.20, 0.015), color=(0.12, 0.12, 0.13))
    build_object("details", [metal, grey, dark])


def bays():
    """The weapons bays: dark boxes behind the cut-outs, the doors (extras.bay / group), the launchers (rack_N), the
    missiles' places (store_N)."""
    x0, x1, y0, y1 = S.MAIN_BAY
    belly = -0.735
    build_object("bay_wells", [B.bay_well(x0, x1, y0, y1, belly, S.BAY_ROOF, mirror=True),
                               B.bay_well(S.SIDE_BAY[0], S.SIDE_BAY[1], S.SIDE_BAY[2], S.SIDE_BAY[3], -0.80, -0.32, mirror=True)])
    # main bay doors: hinged at the outer edges, hanging down open; they close inwards
    B.bay_door("bay_main_R", (x1, y0, belly), (x1, y1, belly), (x1 + 0.02, 0.5 * (y0 + y1), belly - 0.80), 90.0, "main")
    B.bay_door("bay_main_L", (-x1, y1, belly), (-x1, y0, belly), (-x1 - 0.02, 0.5 * (y0 + y1), belly - 0.80), 90.0, "main")
    sx0, sx1, sy0, sy1 = S.SIDE_BAY
    B.bay_door("bay_side_R", (sx1, sy0, -0.80), (sx1, sy1, -0.80), (sx1 + 0.02, 0.5 * (sy0 + sy1), -1.14), 90.0, "side_R")
    B.bay_door("bay_side_L", (-sx1, sy1, -0.80), (-sx1, sy0, -0.80), (-sx1 - 0.02, 0.5 * (sy0 + sy1), -1.14), 90.0, "side_L")
    # AIM-120 trapeze launchers: two parallel links from the bay roof; the missile hangs level below them
    phi0 = math.radians(TRAPEZE_PHI0)
    hz = S.BAY_ROOF - 0.03
    for st, (x, yc) in MAIN_STATIONS.items():
        hinge = np.array([x, yc + TRAPEZE_L * math.cos(phi0), hz])
        attach = hinge + TRAPEZE_L * np.array([0.0, -math.cos(phi0), -math.sin(phi0)])
        part = Part("metal", None, color=(0.42, 0.43, 0.45))
        for dx in (-0.045, 0.045):
            tube(part, [hinge + (dx, 0, 0), attach + (dx, 0, 0)], 0.016, 8)
        tube(part, [hinge + (-0.06, 0, 0), hinge + (0.06, 0, 0)], 0.022, 8, (0.25, 0.26, 0.27))
        box(part, attach + (0.0, 0.0, -0.015), (0.03, 0.42, 0.012), color=(0.30, 0.31, 0.32))
        o = build_object("rack_%d" % st, [part], frame=(hinge, np.array([1.0, 0.0, 0.0])))
        o["rack"] = TRAPEZE_PHI1 - TRAPEZE_PHI0
        empty("store_%d" % st, (x, yc, float(attach[2]) - 0.12))
    # AIM-9 rails in the side bays: they slide down and out of the trunk
    for st, side in SIDE_STATIONS.items():
        x, yc, z = side * 1.23, 1.15, -0.60
        part = Part("metal", None, color=(0.42, 0.43, 0.45))
        box(part, (x, yc, z + 0.085), (0.025, 0.95, 0.018))
        for dy in (-0.55, 0.55):
            box(part, (x, yc + dy, z + 0.20), (0.02, 0.03, 0.10))
        o = build_object("rack_%d" % st, [part], frame=(np.array([x, yc, z + 0.085]), np.array([1.0, 0.0, 0.0])))
        o["slide_x"], o["slide_y"], o["slide_z"] = float(side * SIDE_SLIDE[0]), 0.0, float(SIDE_SLIDE[2])
        empty("store_%d" % st, (x, yc, z))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.35,
                   nose_doors=[((0.20, gn["y"] + 0.80, zk - 0.02), (0.20, gn["y"] - 0.45, zk - 0.02),
                                (0.22, gn["y"] + 0.20, zk - 0.42), 86.0)],
                   main_hinge=(gm["x"] - 0.25, gm["y"] + 0.30, -0.45),
                   main_doors=[((1.20, gm["y"] + 0.80, -0.62), (1.20, gm["y"] - 0.70, -0.62), (1.32, gm["y"] + 0.05, -1.15), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, S.Y0 - 17.70, 0.20), vapor=(2.30, S.Y0 - 8.60, 0.35), gun=(1.20, S.Y0 - 7.30, 0.55))


B.build_jet(S, M, f22_paint.painter, "f22", OUT, WEB, details=lambda: (details(), bays()), gear=gear, refs=refs,
            cockpit=dict(width=0.44))
