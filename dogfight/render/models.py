"""Procedural low-poly models: F-16C, AIM-9M, AIM-120A, afterburner flame.

All dimensions are real-world metres (F-16C: 15.06 m long, 9.96 m span
including wingtip missiles).  +Y is forward, +Z up, +X right.
"""

import math

from panda3d.core import ColorBlendAttrib, LODNode, NodePath, TransparencyAttrib, Vec3

from ..mathutil import interp_table
from .f16_model import build_f16_detailed
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
    "AIM-9M": dict(length=2.87, radius=0.0635, body=(0.80, 0.81, 0.80, 1)),
    "AIM-120A": dict(length=3.65, radius=0.089, body=(0.90, 0.90, 0.88, 1)),
}
_YELLOW = (0.86, 0.70, 0.12, 1.0)
_BROWN = (0.42, 0.30, 0.18, 1.0)
_DARK = (0.08, 0.08, 0.09, 1.0)


def _fin_set(mb, r, y_center, root_chord, span, tip_chord, sweep, color, rolleron=False, angle0=math.pi / 4):
    for k in range(4):
        a = angle0 + k * math.pi / 2
        d = Vec3(math.cos(a), 0, math.sin(a))
        thick = Vec3(-math.sin(a), 0, math.cos(a))
        root_le = d * r + Vec3(0, y_center + root_chord * 0.5, 0)
        root_te = d * r + Vec3(0, y_center - root_chord * 0.5, 0)
        tip_le = d * (r + span) + Vec3(0, y_center + root_chord * 0.5 - sweep, 0)
        tip_te = tip_le - Vec3(0, tip_chord, 0)
        mb.surface(root_le, root_te, tip_le, tip_te, 0.014, 0.006, thick, color)
        if rolleron:   # small gyro wheel at the trailing tip corner
            c = d * (r + span - 0.025) + Vec3(0, y_center - root_chord * 0.5 + 0.035, 0)
            ring0 = [c + thick * 0.008 + (d * math.cos(t) + Vec3(0, math.sin(t), 0)) * 0.035
                     for t in (2 * math.pi * j / 10 for j in range(11))]
            ring1 = [p - thick * 0.016 for p in ring0]
            mb.loft([ring0, ring1], _DARK, cap_front=(0.5, 0.5, 0.5, 1.0), cap_back=(0.5, 0.5, 0.5, 1.0))


def build_missile(key):
    s = MISSILE_SHAPES[key]
    mb = MeshBuilder()
    length = s["length"]
    r = s["radius"]
    body = s["body"]
    tail = -length * 0.5
    front = length * 0.5
    seg = 16

    def ring(y, rr):
        return ellipse_ring(y, rr, 0.0, rr, segments=seg)
    if key == "AIM-9M":
        nose_y = front - 0.11
        bands = ((nose_y - 0.62, nose_y - 0.56, _YELLOW), (tail + 1.15, tail + 1.09, _BROWN))
    else:
        nose_y = front - 0.55
        bands = ((nose_y - 0.32, nose_y - 0.26, _YELLOW), (tail + 1.40, tail + 1.34, _BROWN))

    def body_color(p, n):
        for y0, y1, col in bands:
            if y1 <= p.y <= y0:
                return col
        if p.y < tail + 0.12:
            return (0.55, 0.56, 0.56, 1.0)
        return body
    ys = sorted({tail, tail + 0.12, nose_y} | {b[0] for b in bands} | {b[1] for b in bands})
    for y0, y1 in zip(ys, ys[1:]):          # one loft per segment: crisp paint bands
        col = body_color(Vec3(0, (y0 + y1) * 0.5, 0), None)
        mb.loft([ring(y0, r), ring(y1, r)], col)
    # recessed nozzle
    nozzle = [ring(tail, r), ring(tail + 0.02, r * 0.75), ring(tail + 0.15, r * 0.6)]
    inner = MeshBuilder()
    inner.loft(nozzle, _DARK)
    inner.tris = [(a, c, b) for a, b, c in inner.tris]
    mb.extend(inner)
    mb._cap(nozzle[-1], Vec3(0, tail + 0.15, 0), Vec3(0, -1, 0), _DARK)

    if key == "AIM-9M":
        # glass seeker dome + guidance section with double delta canards
        dome = [ring(nose_y, r)]
        for k in range(1, 7):
            a = k / 6 * math.pi / 2
            dome.append(ring(nose_y + math.sin(a) * 0.11, r * math.cos(a) + 0.0005))
        mb.loft(dome, (0.14, 0.17, 0.22, 1.0))
        _fin_set(mb, r, front - 0.40, 0.30, 0.20, 0.06, 0.20, body)
        _fin_set(mb, r, front - 0.40, 0.12, 0.27, 0.03, 0.08, body)
        _fin_set(mb, r, tail + 0.24, 0.34, 0.26, 0.20, 0.14, body, rolleron=True)
    else:
        # ogive radome, mid-body wings, clipped tail fins
        ogive = []
        for k in range(9):
            t = k / 8
            ogive.append(ring(nose_y + t * 0.55, r * math.sqrt(max(1 - t * t, 0.0)) * (1 - 0.12 * t) + 0.0005))
        mb.loft(ogive, lambda p, n: (0.78, 0.78, 0.76, 1.0))
        _fin_set(mb, r, 0.15, 0.55, 0.11, 0.30, 0.25, body)
        _fin_set(mb, r, tail + 0.20, 0.32, 0.21, 0.14, 0.18, body)
    return mb.build("missile_" + key)


def _wheel(mb, x, y, z, radius, width, color=(0.10, 0.10, 0.11, 1.0)):
    rings = []
    for dx in (-width * 0.5, width * 0.5):
        ring = ellipse_ring(0.0, radius, 0.0, radius, segments=12)
        rings.append([Vec3(x + dx, y + p.x, z + p.z) for p in ring])
    mb.loft(rings, color, cap_front=(0.35, 0.35, 0.36, 1.0), cap_back=(0.35, 0.35, 0.36, 1.0))


def build_gear():
    """Landing gear (main gear + nose gear), wheels touching z = -2.05."""
    mb = MeshBuilder()
    leg = (0.78, 0.79, 0.80, 1.0)
    for side in (-1.0, 1.0):
        box(mb, (side * 1.05, -1.0, -1.12), (0.07, 0.07, 0.58), leg)          # strut
        box(mb, (side * 0.8, -1.25, -0.95), (0.25, 0.04, 0.03), leg)          # drag brace
        box(mb, (side * 1.25, -0.95, -0.95), (0.03, 0.5, 0.4), (0.60, 0.63, 0.66, 1.0))  # gear door
        _wheel(mb, side * 1.12, -1.0, -1.70, 0.35, 0.22)
    box(mb, (0.0, 3.3, -1.52), (0.05, 0.05, 0.28), leg)                       # nose strut
    _wheel(mb, 0.0, 3.3, -1.80, 0.25, 0.14)
    box(mb, (0.0, 3.3, -1.75), (0.13, 0.1, 0.02), leg)                        # landing light / fork
    return mb.build("gear")


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

    def aircraft(self, livery, detail_range=2500.0):
        """F-16 with two levels of detail: the full model up close, the light one far away."""
        key = ("f16_lod", livery)
        if key not in self._cache:
            lod = LODNode("f16_lod")
            root = NodePath(lod)
            build_f16_detailed(livery).reparentTo(root)
            lod.addSwitch(detail_range, 0.0)
            self._get(("f16", livery), lambda: build_f16(livery)).copyTo(root)
            lod.addSwitch(1.0e7, detail_range)
            self._cache[key] = root
        return self._cache[key].copyTo(NodePath("ac"))

    def missile(self, key):
        return self._get(("missile", key), lambda: build_missile(key)).copyTo(NodePath("m"))

    def gear(self):
        return self._get(("gear",), build_gear).copyTo(NodePath("gear"))

    def flame(self):
        return self._get(("flame",), build_flame).copyTo(NodePath("flame"))
