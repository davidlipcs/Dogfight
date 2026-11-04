"""Builds the T-6A Texan II in Blender and exports it (models/t6/t6.glb, web/assets/t6.glb).

    python tools/blender/build_t6.py            (with the bpy module)

The shape: t6_shape.py (measured off the three-view), the meshes: t6_mesh.py (jk_mesh), the paint: t6_paint.py,
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
import t6_mesh as M  # noqa: E402
import t6_paint  # noqa: E402
import t6_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, jk_mesh, B, S, M, t6_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_STEEL, Part, build_object, empty, prism, tube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "t6")
WEB = os.path.join(ROOT, "web", "assets")


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.70, 0.71, 0.72)), \
        Part("matte", None, color=C_DARK)
    ex = S.EXHAUST
    for s in (-1, 1):                                       # the exhaust stacks either side of the cowling
        tube(dark, [(s * (ex[0] - 0.04), ex[1] + 0.12, ex[2]), (s * (ex[0] + 0.07), ex[1] - 0.10, ex[2] - 0.02)],
             [0.085, 0.10], 10, (0.22, 0.20, 0.18))
    prism(grey, (0, S.Y0 - 6.80, float(S.SPINE(S.Y0 - 6.80))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.22, 0.0), (-0.25, 0.10), (-0.16, 0.10)], 0.010)
    build_object("details", [metal, grey, dark])
    # the propeller: four blades and the hub, turning about the aircraft's long axis (the game spins "prop" about
    # its local X)
    pr = S.PROP
    prop = Part("matte", None, color=(0.08, 0.08, 0.09))
    tips = Part("matte", None, color=(0.85, 0.70, 0.12))
    for k in range(pr["blades"]):
        a = math.radians(45.0 + 360.0 * k / pr["blades"])
        d = np.array([math.cos(a), 0.0, math.sin(a)])
        side = np.array([-math.sin(a), 0.0, math.cos(a)])
        for r0, r1, part in ((0.16, pr["r"] - 0.12, prop), (pr["r"] - 0.12, pr["r"], tips)):
            c0 = np.array([0.0, pr["y"], 0.0]) + d * r0
            c1 = np.array([0.0, pr["y"], 0.0]) + d * r1
            w0, w1 = pr["chord"] * (1.0 if r0 < 0.2 else 0.85), pr["chord"] * 0.7
            quad = [c0 + side * w0 / 2, c1 + side * w1 / 2, c1 - side * w1 / 2, c0 - side * w0 / 2]
            q = np.array(quad)
            twist = np.array([0.0, 0.02, 0.0])
            part.add(np.vstack([q + twist, q - twist]), [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
                                                          (2, 6, 7, 3), (3, 7, 4, 0)])
    o = build_object("prop", [prop, tips], frame=(np.array([0.0, pr["y"], 0.0]), np.array([0.0, 1.0, 0.0])))


def stores():
    for stn, p in ((8, (3.6, S.Y0 - 4.3, -0.40)), (7, (2.6, S.Y0 - 4.2, -0.48)), (6, (1.6, S.Y0 - 4.1, -0.56)),
                   (5, (0.0, S.Y0 - 4.5, -0.90))):          # (the trainer carries nothing; the game wants the points)
        empty("store_%d" % stn, p)
        empty("store_%d" % (9 - stn), (-p[0], p[1], p[2]))


def gear():
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    zk = float(S.KEEL(gn["y"]))
    B.landing_gear(S, nose_hinge_dy=0.20,
                   nose_doors=[((0.13, gn["y"] + 0.45, zk - 0.02), (0.13, gn["y"] - 0.25, zk - 0.02),
                                (0.15, gn["y"] + 0.10, zk - 0.25), 86.0)],
                   main_hinge=(1.30, gm["y"] + 0.15, -0.45), main_retract=((0.0, 1.0, 0.0), 88.0),
                   main_doors=[((1.05, gm["y"] + 0.45, -0.50), (1.05, gm["y"] - 0.35, -0.50), (1.12, gm["y"] + 0.05, -0.85), 80.0)])


def refs():
    B.lights_and_refs(S, tail_light=(0.0, S.Y0 - 10.16, 0.05), vapor=(1.00, S.Y0 - 3.50, -0.50), gun=(0.0, S.Y0 - 0.3, 0.0))
    ex = S.EXHAUST
    for s, sfx in ((1, "R"), (-1, "L")):
        empty("ref_nozzle_" + sfx, (s * (ex[0] + 0.08), ex[1] - 0.12, ex[2]))


B.build_jet(S, M, t6_paint.painter, "t6", OUT, WEB, details=details, stores=stores, gear=gear, refs=refs,
            cockpit=dict(width=0.36, seat_y=S.Y0 - 3.95, rear_seats=(S.Y0 - 5.35,)))
