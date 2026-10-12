"""Procedural low-poly models: F-16C, AIM-9M, AIM-120A, afterburner flame.

All dimensions are real-world metres (F-16C: 15.06 m long, 9.96 m span
including wingtip missiles).  +Y is forward, +Z up, +X right.
"""

import math

from panda3d.core import (ColorBlendAttrib, NodePath, TransparencyAttrib, Vec3)

from ..mathutil import interp_table
from .meshbuilder import MeshBuilder, ellipse_ring

LIVERIES = {
    # USAF two tone gray
    "viper": dict(top=(0.47, 0.50, 0.54, 1), side=(0.60, 0.63, 0.66, 1), bottom=(0.69, 0.71, 0.73, 1),
                  radome=(0.38, 0.40, 0.43, 1), camo=False),
    # Aggressor squadron desert splinter
    "aggressor": dict(top=(0.76, 0.64, 0.45, 1), side=(0.52, 0.40, 0.28, 1), bottom=(0.72, 0.73, 0.74, 1),
                      radome=(0.30, 0.28, 0.26, 1), camo=True),
}
METAL = (0.36, 0.34, 0.32, 1)
DARK = (0.05, 0.05, 0.06, 1)
CANOPY = (0.30, 0.25, 0.10, 1)
FRAME = (0.20, 0.21, 0.22, 1)

# Fuselage stations: (y, half width, top z, bottom z), rear -> front
FUSELAGE = (
    (-6.50, 0.58, 0.56, -0.42),
    (-5.80, 0.66, 0.62, -0.46),
    (-4.60, 0.78, 0.72, -0.52),
    (-3.20, 0.86, 0.80, -0.58),
    (-1.60, 0.90, 0.86, -0.60),
    (0.00, 0.88, 0.88, -0.60),
    (1.40, 0.80, 0.90, -0.58),
    (2.60, 0.68, 0.86, -0.54),
    (3.60, 0.62, 0.78, -0.50),
    (4.60, 0.56, 0.68, -0.44),
    (5.60, 0.48, 0.55, -0.34),
    (6.60, 0.33, 0.42, -0.20),
    (7.40, 0.16, 0.30, -0.06),
)
NOSE_TIP = Vec3(0.0, 8.05, 0.12)

CANOPY_RINGS = (   # y, half width, height above the fuselage top
    (1.0, 0.08, 0.05),
    (1.6, 0.25, 0.22),
    (2.4, 0.38, 0.42),
    (3.2, 0.42, 0.52),
    (4.0, 0.40, 0.48),
    (4.8, 0.28, 0.28),
    (5.35, 0.05, 0.03),
)

INTAKE = (   # y, half width, top z, bottom z  (chin intake, rear -> mouth)
    (-2.4, 0.40, -0.50, -0.62),
    (-1.0, 0.50, -0.48, -0.86),
    (0.5, 0.56, -0.44, -1.10),
    (2.2, 0.58, -0.36, -1.25),
    (3.4, 0.56, -0.30, -1.30),
)

TOP_Z = tuple((y, top) for y, _, top, _ in FUSELAGE)


def body_color(livery):
    def color(p, n):
        if n.z < -0.35:
            return livery["bottom"]
        if livery["camo"]:
            v = math.sin(p.x * 1.15 + p.y * 0.55) + math.sin(p.y * 0.8 - p.x * 0.35 + 1.7)
            return livery["top"] if v > 0.15 else livery["side"]
        return livery["top"] if n.z > 0.5 else livery["side"]
    return color


def box(mb, center, half, color):
    cx, cy, cz = center
    hx, hy, hz = half
    c = [Vec3(cx + sx * hx, cy + sy * hy, cz + sz * hz)
         for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    # index = (sx>0)*4 + (sy>0)*2 + (sz>0)
    faces = (((0, 1, 3, 2), Vec3(-1, 0, 0)), ((4, 6, 7, 5), Vec3(1, 0, 0)),
             ((0, 4, 5, 1), Vec3(0, -1, 0)), ((2, 3, 7, 6), Vec3(0, 1, 0)),
             ((0, 2, 6, 4), Vec3(0, 0, -1)), ((1, 5, 7, 3), Vec3(0, 0, 1)))
    for (a, b, cc, d), out in faces:
        mb.quad(c[a], c[b], c[cc], c[d], color, outward=out)


def build_f16(livery_name="viper"):
    livery = LIVERIES[livery_name]
    paint = body_color(livery)
    mb = MeshBuilder()

    # --- fuselage (rear -> nose tip)
    rings = []
    for y, hw, top, bot in FUSELAGE:
        rings.append(ellipse_ring(y, hw, (top + bot) * 0.5, (top - bot) * 0.5, segments=18, exponent=2.4))
    rings.append([Vec3(NOSE_TIP) for _ in range(19)])

    def fuselage_color(p, n):
        if p.y > 5.9:
            return livery["radome"]
        return paint(p, n)
    mb.loft(rings, fuselage_color)

    # --- engine nozzle
    nozzle = [ellipse_ring(y, r, 0.07, r, segments=16) for y, r in ((-7.45, 0.45), (-7.0, 0.49), (-6.45, 0.55))]
    mb.loft(nozzle, METAL, cap_back=DARK)

    # --- canopy bubble
    canopy = []
    for y, w, h in CANOPY_RINGS:
        base = interp_table(TOP_Z, y) - 0.08
        canopy.append(ellipse_ring(y, w, base, h + 0.08, segments=10, start=0.0, end=math.pi))
    mb.loft(canopy, CANOPY)
    # canopy frame bow
    box(mb, (0.0, 2.15, interp_table(TOP_Z, 2.15) + 0.36), (0.36, 0.05, 0.05), FRAME)

    # --- chin intake
    intake = [ellipse_ring(y, hw, (top + bot) * 0.5, (top - bot) * 0.5, segments=14, exponent=4.0)
              for y, hw, top, bot in INTAKE]
    mb.loft(intake, paint, cap_front=DARK)

    # --- vertical fin + dorsal fillet
    mb.surface((0, -3.5, 0.80), (0, -6.9, 0.70), (0, -5.75, 3.65), (0, -6.75, 3.65), 0.16, 0.05, (1, 0, 0), paint)
    mb.surface((0, -2.0, 0.86), (0, -3.7, 0.84), (0, -3.6, 1.35), (0, -3.95, 1.35), 0.12, 0.08, (1, 0, 0), paint)
    box(mb, (0.0, -6.55, 3.62), (0.06, 0.3, 0.07), FRAME)          # fin tip antenna

    # --- one side (mirrored below)
    half = MeshBuilder()
    # wing
    half.surface((0.80, 1.30, 0.12), (0.80, -3.10, 0.12), (4.72, -1.95, 0.12), (4.72, -3.05, 0.12),
                 0.22, 0.07, (0, 0, 1), paint)
    # leading edge root extension (strake)
    half.surface((0.50, 4.60, 0.16), (0.50, 1.00, 0.16), (0.95, 1.50, 0.15), (0.95, 1.00, 0.15),
                 0.08, 0.06, (0, 0, 1), paint)
    # horizontal stabiliser (anhedral)
    half.surface((0.70, -4.55, 0.10), (0.70, -7.00, 0.10), (2.75, -6.25, -0.24), (2.75, -7.05, -0.24),
                 0.12, 0.04, (0, 0.0, 1), paint)
    # ventral fin
    half.surface((0.50, -3.70, -0.52), (0.50, -4.90, -0.50), (0.78, -4.30, -1.05), (0.78, -5.00, -1.05),
                 0.06, 0.04, (1, 0, 0.3), livery["bottom"])
    # wingtip launch rail
    box(half, (4.80, -0.75, 0.12), (0.06, 1.25, 0.05), FRAME)
    # pylons for stations 2/8 and 3/7
    box(half, (3.75, -0.95, -0.10), (0.05, 0.75, 0.16), livery["bottom"])
    box(half, (2.60, -0.55, -0.12), (0.05, 0.85, 0.20), livery["bottom"])
    mb.extend(half)
    mb.extend(half.mirrored_x())

    node = mb.build("f16_" + livery_name)
    return node


MISSILE_SHAPES = {
    "AIM-9M": dict(length=2.87, radius=0.0635, nose=0.22, body=(0.80, 0.81, 0.80, 1), nose_col=(0.25, 0.30, 0.36, 1),
                   band=(0.85, 0.75, 0.25, 1), front=(0.95, 0.24, 0.20), rear=(-1.05, 0.32, 0.30), mid=None),
    "AIM-120A": dict(length=3.65, radius=0.089, nose=0.55, body=(0.88, 0.88, 0.86, 1), nose_col=(0.70, 0.70, 0.68, 1),
                     band=(0.80, 0.70, 0.25, 1), front=None, rear=(-1.45, 0.21, 0.32), mid=(0.15, 0.17, 0.55)),
}


def build_missile(key):
    s = MISSILE_SHAPES[key]
    mb = MeshBuilder()
    length = s["length"]
    r = s["radius"]
    tail = -length * 0.5
    nose_start = length * 0.5 - s["nose"]
    rings = [ellipse_ring(tail, r, 0.0, r, segments=10),
             ellipse_ring(nose_start - 0.35, r, 0.0, r, segments=10),
             ellipse_ring(nose_start - 0.3, r * 1.001, 0.0, r * 1.001, segments=10),
             ellipse_ring(nose_start, r, 0.0, r, segments=10)]
    mb.loft(rings, lambda p, n: s["band"] if nose_start - 0.35 < p.y < nose_start - 0.29 else s["body"],
            cap_back=DARK)
    nose = [ellipse_ring(nose_start, r, 0.0, r, segments=10),
            ellipse_ring(nose_start + s["nose"] * 0.5, r * 0.75, 0.0, r * 0.75, segments=10),
            [Vec3(0, length * 0.5, 0) for _ in range(11)]]
    mb.loft(nose, s["nose_col"])

    def fins(y_center, span, chord):
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            d = Vec3(math.cos(a), 0, math.sin(a))
            thick = Vec3(-math.sin(a), 0, math.cos(a))
            root_le = d * r + Vec3(0, y_center + chord * 0.5, 0)
            root_te = d * r + Vec3(0, y_center - chord * 0.5, 0)
            tip_le = d * (r + span) + Vec3(0, y_center - chord * 0.1, 0)
            tip_te = d * (r + span) + Vec3(0, y_center - chord * 0.5, 0)
            mb.surface(root_le, root_te, tip_le, tip_te, 0.012, 0.006, thick, s["body"])

    for key2 in ("front", "mid", "rear"):
        f = s[key2]
        if f is not None:
            fins(f[0], f[1], f[2])
    return mb.build("missile_" + key)


def build_flame():
    """Afterburner plume along -Y, unit length (scaled at runtime)."""
    mb = MeshBuilder()
    for radius, length, base_col, tip_col in ((0.46, 1.0, (1.0, 0.55, 0.25, 0.75), (0.6, 0.2, 0.5, 0.0)),
                                              (0.30, 0.55, (1.0, 0.95, 0.8, 0.95), (1.0, 0.6, 0.3, 0.0))):
        base = ellipse_ring(0.0, radius, 0.0, radius, segments=14)
        mid = ellipse_ring(-length * 0.35, radius * 0.75, 0.0, radius * 0.75, segments=14)
        tip = [Vec3(0, -length, 0) for _ in range(15)]

        def col(p, n, length=length, base_col=base_col, tip_col=tip_col):
            t = min(1.0, -p.y / length)
            return tuple(base_col[i] + (tip_col[i] - base_col[i]) * t for i in range(4))
        mb.loft([tip, mid, base], col)
    node = mb.build("flame")
    node.setTwoSided(True)
    node.setLightOff(1)
    node.setDepthWrite(False)
    node.setTransparency(TransparencyAttrib.MAlpha)
    node.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha,
                                         ColorBlendAttrib.OOne))
    node.setBin("fixed", 20)
    return node


class ModelLibrary:
    """Builds every model once and hands out instances."""

    def __init__(self):
        self._cache = {}

    def _get(self, key, factory):
        if key not in self._cache:
            node = factory()
            node.flattenStrong()
            self._cache[key] = node
        return self._cache[key]

    def aircraft(self, livery):
        return self._get(("f16", livery), lambda: build_f16(livery)).copyTo(NodePath("ac"))

    def missile(self, key):
        return self._get(("missile", key), lambda: build_missile(key)).copyTo(NodePath("m"))

    def flame(self):
        return self._get(("flame",), build_flame).copyTo(NodePath("flame"))
