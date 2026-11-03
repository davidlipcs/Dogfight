"""Builds the MiG-29 (9.12, Hungarian Air Force) in Blender and exports it (models/mig29/mig29.glb, web/assets/mig29.glb).

    python tools/blender/build_mig29.py            (with the bpy module)

The shape: mig29_shape.py (measured off the three-view), the meshes: mig29_mesh.py, the paint: mig29_paint.py,
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
import jk_paint  # noqa: E402
import mig29_mesh as M  # noqa: E402
import mig29_paint  # noqa: E402
import mig29_shape as S  # noqa: E402

for mod in (L, jk, jk_paint, B, S, M, mig29_paint):
    importlib.reload(mod)
from aircraft_lib import C_BLACK, C_DARK, C_GREY, C_LIGHT, C_STEEL, Part, box, build_object, empty, prism, tube  # noqa

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "models", "mig29")
WEB = os.path.join(ROOT, "web", "assets")


def canopy_z(y, x):
    """Height of the glass at (x, y) (the cockpit is kept under it); the skin elsewhere."""
    if S.Y_CAN1 < y < S.Y_WS0:
        h = S.canopy_half(y)
        if abs(x) <= h[-1, 0]:
            return float(np.interp(abs(x), h[::-1, 0], h[::-1, 1]))
    return float(S.SPINE(y))


def details():
    metal, grey, dark = Part("metal", None, color=C_STEEL), Part("matte", None, color=(0.52, 0.55, 0.58)), \
        Part("matte", None, color=C_DARK)
    # pitot boom with its vanes, the radome tip
    tube(metal, [(0, S.Y_NOSE - 0.02, 0.045), (0, S.Y_NOSE + 0.35, 0.045), (0, S.Y_PITOT, 0.045)], [0.035, 0.022, 0.012], 10)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        prism(metal, (0, S.Y_NOSE + 0.55, 0.045), (0, 1, 0), (math.cos(a), 0, math.sin(a)),
              [(0.0, 0.015), (-0.10, 0.015), (-0.10, 0.07), (-0.04, 0.07)], 0.004)
    # IRST ball ahead of the windscreen (right of the centre line)
    ball = Part("glass", None)
    c = np.array([0.16, 6.08, float(S.SPINE(6.08)) - 0.01])
    for i in range(6):
        a0, a1 = 0.5 * math.pi * i / 6, 0.5 * math.pi * (i + 1) / 6
        r0, r1 = 0.13 * math.cos(a0), 0.13 * math.cos(a1)
        z0, z1 = 0.13 * math.sin(a0), 0.13 * math.sin(a1)
        ring0 = [c + np.array([r0 * math.cos(t), r0 * math.sin(t), z0]) for t in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
        ring1 = [c + np.array([r1 * math.cos(t), r1 * math.sin(t), z1]) for t in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
        ball.grid([ring0, ring1], close=True)
    # angle of attack vanes on the nose sides, the blade aerials
    for s in (-1, 1):
        prism(grey, (s * 0.33, 7.30, 0.10), (0, 1, 0), (s, 0, 0), [(0, 0), (-0.10, 0), (-0.10, 0.10), (-0.02, 0.10)], 0.006)
    prism(grey, (0, 1.60, float(S.SPINE(1.60))), (0, 1, 0), (0, 0, 1), [(0.0, 0.0), (-0.35, 0.0), (-0.40, 0.17), (-0.25, 0.17)], 0.012)
    prism(grey, (0, 3.70, float(S.KEEL(3.70))), (0, 1, 0), (0, 0, -1), [(0.0, 0.0), (-0.30, 0.0), (-0.35, 0.13), (-0.2, 0.13)], 0.012)
    # gun muzzle in the left LERX root
    tube(dark, [(-0.95, 2.70, 0.16), (-0.95, 2.35, 0.16)], 0.05, 10, C_BLACK)
    build_object("details", [metal, grey, dark, ball])


def canopy_frame():
    p = Part("paint", "auto")
    for y, r in ((S.Y_WS1, 0.028), (S.Y_CAN1 + 0.05, 0.035)):
        h = S.canopy_half(y)
        pts = [(-hx, y, hz + 0.004) for hx, hz in h[::-1]] + [(hx, y, hz + 0.004) for hx, hz in h[1:]]
        tube(p, pts, r, 8, caps=True)
    # the sill rails
    for s in (-1, 1):
        ys = np.linspace(S.Y_WS0 - 0.02, S.Y_CAN1 + 0.02, 14)
        pts = [(s * float(S.CANOPY_SILL_X(y)), y, float(S.CANOPY_SILL_Z(y)) + 0.01) for y in ys]
        tube(p, pts, 0.022, 6, caps=True)
    build_object("canopy_frame", [p])


def stores():
    part = Part("paint", "auto")
    pts = {}
    for stn, x in ((8, 4.65), (7, 3.60), (6, 2.55)):
        le, te = float(S.wing_le(x)), float(S.wing_te(x))
        c = le - te
        zl = float(S.wing_z(x)) - float(S.WING.t(x)) * c * 0.55
        pts[stn] = B.pylon(part, x, le - 0.35 * c + 0.95, le - 0.35 * c - 1.15, zl, 0.30)
    # under the nacelles (the fuselage stations of the game)
    zb = float(S.NACELLE[3](-0.85))
    box(part, (1.0, -0.85, zb - 0.04), (0.04, 0.80, 0.04))
    pts[5] = (1.0, -0.90, zb - 0.20)
    build_object("pylons", [part])
    for stn, p in pts.items():
        empty("store_%d" % stn, p)
        empty("store_%d" % (9 - stn), (-p[0], p[1], p[2]))


def gear():
    zg = S.Z_GROUND
    gn, gm = S.GEAR_NOSE, S.GEAR_MAIN
    root = empty("gear", (0.0, 0.0, 0.0))
    # nose leg: in the bay between the intakes, folds aft
    hinge = (0.0, gn["y"] + 0.30, float(S.KEEL(gn["y"])) + 0.05)
    axle = (0.0, gn["y"], zg + gn["r"])
    B.gear_leg("gear_nose", hinge, axle, gn["r"], gn["w"], True, (-1.0, 0.0, 0.0), 95.0, zg)
    # its mudguard rides on the leg: a small separate piece under the same hinge would need its own extras; keep
    # it on the leg mesh instead (added as a box just above the wheels)
    leg = bpy.data.objects["gear_nose"]
    guard = Part("matte", None, color=(0.55, 0.58, 0.60))
    box(guard, (0.0, gn["y"], zg + 2 * gn["r"] + 0.05), (0.26, 0.20, 0.015))
    g = build_object("gear_nose_guard", [guard], frame=(np.array(hinge), np.array([-1.0, 0.0, 0.0])))
    g["retract"] = 95.0
    for s in (-1, 1):
        zk = float(S.KEEL(gn["y"]))
        o = B.gear_door("door_nose_%s" % ("R" if s > 0 else "L"), (s * 0.20, gn["y"] + 0.85, zk - 0.02),
                        (s * 0.20, gn["y"] - 0.45, zk - 0.02), (s * 0.22, gn["y"] + 0.2, zk - 0.42), 86.0 * s * -1)
    # main legs: from the wing root outboard of the nacelles, fold forwards
    for s, sfx in ((1, "R"), (-1, "L")):
        x = s * gm["x"]
        hinge = (x - s * 0.05, gm["y"] - 0.20, -0.18)
        axle = (x, gm["y"], zg + gm["r"])
        B.gear_leg("gear_main_" + sfx, hinge, axle, gm["r"], gm["w"], False, (1.0, 0.0, 0.0), 92.0, zg, x_side=s)
        zb = float(S.NACELLE[3](gm["y"]))
        B.gear_door("door_main_" + sfx, (s * 1.50, gm["y"] + 0.75, -0.30), (s * 1.50, gm["y"] - 0.65, -0.30),
                    (s * 1.62, gm["y"] + 0.05, -0.95), 80.0 * -s)
    empty("ref_gear_nose", (0.0, gn["y"], zg))
    for s, sfx in ((1, "R"), (-1, "L")):
        empty("ref_gear_main_" + sfx, (s * gm["x"], gm["y"], zg))


def lights_and_refs():
    xt = S.X_WTIP
    zt = float(S.wing_z(xt))
    yl = float(S.wing_le(xt - 0.1)) - 0.45
    B.lamp("light_nav_L", (-xt + 0.02, yl, zt), "light_red")
    B.lamp("light_nav_R", (xt - 0.02, yl, zt), "light_green")
    B.lamp("light_tail", (0.0, -5.38, -0.12), "light_white", r=0.03)
    for s, sfx in ((1, "R"), (-1, "L")):
        empty("ref_nav_" + sfx, (s * (xt - 0.02), yl, zt))
        empty("ref_wingtip_" + sfx, (s * xt, float(S.wing_te(xt)) + 0.4, zt))
        empty("ref_nozzle_" + sfx, (s * S.NOZZLE["x"], S.NOZZLE["y1"], S.NOZZLE["z"]))
        tipz = S.FIN_Z + S.FIN[-1][0] * math.cos(math.radians(S.FIN_CANT))
        tipx = S.FIN_X + S.FIN[-1][0] * math.sin(math.radians(S.FIN_CANT))
        empty("ref_strobe_" + sfx, (s * tipx, -5.55, tipz + 0.02))
        empty("ref_vapor_" + sfx, (s * 1.20, 3.30, 0.07))
    empty("ref_tail", (0.0, -5.42, -0.12))
    empty("ref_gun", (-0.95, 2.40, 0.16))


def build():
    root, tex = B.begin("mig29", OUT)
    parts = M.airframe()
    painted = []
    painted.append(B.obj("fuselage", [parts["fuselage"]]))
    for sfx in ("L", "R"):
        for k in ("wing", "fin", "boom", "nacelle"):
            painted.append(B.obj("%s_%s" % (k, sfx), [parts["%s_%s" % (k, sfx)]]))
        for k in ("lef", "flap", "ail", "stab", "rudder"):
            pc = parts["%s_%s" % (k, sfx)]
            painted.append(B.obj("%s_%s" % (k, sfx), [pc], hinge=pc.hinge))
    B.obj("canopy", [parts["canopy"]])
    B.obj("nozzle", [parts[k] for k in ("nozzle_R", "nozzle_L", "nozzle_in_R", "nozzle_in_L", "duct_R", "duct_L")])
    canopy_frame()
    details()
    stores()
    gear()
    B.cockpit(dict(seat_y=S.Y_CAN1 + 0.75, floor_z=float(S.CANOPY_SILL_Z(4.0)) - 0.62, sill_z=float(S.CANOPY_SILL_Z(4.0)),
                   panel_y=S.Y_WS1 - 0.10, panel_z=float(S.CANOPY_SILL_Z(5.0)) + 0.05, width=0.40, russian=True,
                   canopy_z=canopy_z))
    lights_and_refs()
    painted += [o for o in bpy.data.objects if o.type == "MESH" and (o.name.startswith("door_") or o.name in
                                                                         ("canopy_frame", "pylons"))]
    B.paint(painted, mig29_paint.painter, tex, "mig29", size=2048)
    B.finish(OUT, WEB, "mig29")


build()
