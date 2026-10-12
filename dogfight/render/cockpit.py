"""F-16C cockpit interior: ACES II seat, side consoles, instrument panel with MFDs, glareshield and HUD.

The panels are textured from a painted atlas (cockpit.png, made by tools/make_cockpit_texture.py);
the 3D parts (seat, stick, throttle, frames) are vertex coloured.  There is deliberately no pilot.
Coordinates are model space: x right, y forward, z up (metres).
"""

import math
import os

from panda3d.core import (Filename, Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
                          GeomVertexWriter, NodePath, SamplerState, Texture, Vec3)

SIZE = 1024
ATLAS = {                                   # pixel rectangles (x0, y0, x1, y1), image rows top-down
    "panel": (0, 0, 1024, 640),
    "mfd_l": (83, 309, 333, 559),
    "mfd_r": (691, 309, 941, 559),
    "rwr": (178, 38, 302, 162),
    "icp": (334, 14, 690, 222),
    "ded": (712, 22, 942, 102),
    "console_l": (0, 640, 1024, 768),
    "console_r": (0, 768, 1024, 896),
    "stripes": (0, 896, 256, 960),
    "cushion": (0, 960, 256, 1024),
    "tub": (256, 896, 512, 1024),
    "placard": (512, 896, 768, 1024),
}
TEXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cockpit.png")

# geometry anchors
EYE = Vec3(0.0, 2.40, 1.10)                  # design eye point (camera position in cockpit view)
HIP = Vec3(0.0, 2.62, 0.42)                  # seat reference point
BACK_ANGLE = math.radians(30.0)              # ACES II seat back recline
PANEL_CENTER = Vec3(0.0, 3.30, 0.60)
PANEL_HALF = (0.37, 0.231)                   # matches the 1024 x 640 px panel region
PANEL_NORMAL = Vec3(0.0, -0.944, 0.33)
CONSOLE_Y = (2.30, 3.15)
CONSOLE_TOP = 0.55
CONSOLE_X = (0.255, 0.41)


def region_uv(name, fx, fy):
    """(fx, fy) in 0..1 across a named atlas rectangle (fy = 0 at its top row) -> texture UV."""
    x0, y0, x1, y1 = ATLAS[name]
    px = x0 + (x1 - x0) * fx
    py = y0 + (y1 - y0) * fy
    return px / SIZE, 1.0 - py / SIZE


class TexMesh:
    """Triangles with position, normal and atlas UV."""

    def __init__(self):
        self.tris = []

    def quad(self, a, b, c, d, uvs, normal):
        """a..d counter-clockwise seen from the front (``normal`` side); uvs for a..d."""
        n = Vec3(normal)
        n.normalize()
        if ((b - a).cross(c - a)).dot(n) < 0:
            a, b, c, d = a, d, c, b
            uvs = (uvs[0], uvs[3], uvs[2], uvs[1])
        self.tris.append(((a, n, uvs[0]), (b, n, uvs[1]), (c, n, uvs[2])))
        self.tris.append(((a, n, uvs[0]), (c, n, uvs[2]), (d, n, uvs[3])))

    def rect(self, center, u_axis, v_axis, hu, hv, region, sub=(0.0, 0.0, 1.0, 1.0)):
        """Flat rectangle facing u x v; ``sub`` = (fx0, fy0, fx1, fy1) part of the atlas region."""
        u = Vec3(u_axis) * hu
        v = Vec3(v_axis) * hv
        fx0, fy0, fx1, fy1 = sub
        pts = (center - u - v, center + u - v, center + u + v, center - u + v)
        uvs = (region_uv(region, fx0, fy1), region_uv(region, fx1, fy1), region_uv(region, fx1, fy0),
               region_uv(region, fx0, fy0))
        self.quad(*pts, uvs, Vec3(u_axis).cross(Vec3(v_axis)))

    def box(self, center, axes, half, region):
        """Oriented box, every face mapped to the whole region."""
        ax = [Vec3(a) for a in axes]
        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            for s in (-1, 1):
                c = center + ax[i] * (half[i] * s)
                self.rect(c, ax[j] * s, ax[k], half[j], half[k], region)

    def build(self, name):
        vdata = GeomVertexData(name, GeomVertexFormat.getV3n3t2(), Geom.UHStatic)
        vdata.setNumRows(len(self.tris) * 3)
        vw = GeomVertexWriter(vdata, "vertex")
        nw = GeomVertexWriter(vdata, "normal")
        tw = GeomVertexWriter(vdata, "texcoord")
        for tri in self.tris:
            for p, n, (u, v) in tri:
                vw.addData3(p)
                nw.addData3(n)
                tw.addData2(u, v)
        prim = GeomTriangles(Geom.UHStatic)
        for i in range(len(self.tris)):
            prim.addVertices(3 * i, 3 * i + 1, 3 * i + 2)
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode(name)
        node.addGeom(geom)
        return NodePath(node)


def _axes_pitch(angle):
    """Orthonormal axes (x, forward, up) pitched by ``angle`` (rad, nose up positive)."""
    c, s = math.cos(angle), math.sin(angle)
    return Vec3(1, 0, 0), Vec3(0, c, s), Vec3(0, -s, c)


def obox(mb, center, axes, half, color):
    """Oriented, flat shaded box into a MeshBuilder."""
    ax = [Vec3(a) for a in axes]
    corners = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                corners[(sx, sy, sz)] = center + ax[0] * (half[0] * sx) + ax[1] * (half[1] * sy) + ax[2] * (half[2] * sz)
    for i in range(3):
        for s in (-1, 1):
            face = []
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                key = [0, 0, 0]
                key[i] = s
                key[(i + 1) % 3] = a
                key[(i + 2) % 3] = b
                face.append(corners[tuple(key)])
            mb.quad(*face, color, outward=ax[i] * s)


def cylinder(mb, a, b, r, color, segments=10, caps=True):
    d = b - a
    d.normalize()
    side = d.cross(Vec3(0, 0, 1))
    if side.length() < 1e-3:
        side = d.cross(Vec3(1, 0, 0))
    side.normalize()
    up = side.cross(d)
    rings = [[p + side * (math.cos(t) * r) + up * (math.sin(t) * r)
              for t in (2 * math.pi * k / segments for k in range(segments + 1))] for p in (a, b)]
    mb.loft(rings, color, cap_front=color if caps else None, cap_back=color if caps else None)


def panel_point(px, py):
    """Atlas pixel inside the panel region -> point on the instrument panel."""
    x0, y0, x1, y1 = ATLAS["panel"]
    n = Vec3(PANEL_NORMAL)
    n.normalize()
    v = Vec3(0, n.z, -n.y)
    fu = (px - (x0 + x1) / 2) / (x1 - x0) * 2 * PANEL_HALF[0]
    fv = ((y0 + y1) / 2 - py) / (y1 - y0) * 2 * PANEL_HALF[1]
    return PANEL_CENTER + Vec3(1, 0, 0) * fu + v * fv


def build_cockpit(plain, glass, rim):
    """Adds the cockpit to ``plain`` (vertex coloured) / ``glass`` and returns (panels, screens) TexMeshes.

    ``rim(y)`` -> (half width, z) of the cockpit opening edge at station y.
    """
    panels = TexMesh()
    screens = TexMesh()
    black = (0.035, 0.035, 0.04, 1.0)
    dark = (0.11, 0.115, 0.12, 1.0)
    grey = (0.20, 0.21, 0.22, 1.0)
    metal = (0.42, 0.43, 0.44, 1.0)
    olive = (0.27, 0.29, 0.21, 1.0)

    # --- instrument panel (textured) with a dark backing box
    n = Vec3(PANEL_NORMAL)
    n.normalize()
    v = Vec3(0, n.z, -n.y)
    panels.rect(PANEL_CENTER, Vec3(1, 0, 0), v, PANEL_HALF[0], PANEL_HALF[1], "panel")
    obox(plain, PANEL_CENTER - n * 0.04, (Vec3(1, 0, 0), -n, v), (PANEL_HALF[0] + 0.01, 0.035, PANEL_HALF[1] + 0.01),
         black)
    # glowing screens just in front of the panel face
    for name in ("mfd_l", "mfd_r", "ded", "rwr"):
        x0, y0, x1, y1 = ATLAS[name]
        c = (panel_point(x0, y0) + panel_point(x1, y1)) * 0.5 + n * 0.002
        hu = (x1 - x0) / (ATLAS["panel"][2] - ATLAS["panel"][0]) * PANEL_HALF[0]
        hv = (y1 - y0) / (ATLAS["panel"][3] - ATLAS["panel"][1]) * PANEL_HALF[1]
        screens.rect(c, Vec3(1, 0, 0), v, hu, hv, name)
    # MFD bezels and the up-front control panel stand out of the panel face
    for name in ("mfd_l", "mfd_r"):
        x0, y0, x1, y1 = ATLAS[name]
        c = (panel_point(x0, y0) + panel_point(x1, y1)) * 0.5
        hu = (x1 - x0 + 92) / 1024 * PANEL_HALF[0]
        hv = (y1 - y0 + 92) / 640 * PANEL_HALF[1]
        for s in (-1, 1):                         # side rails of the bezel
            obox(plain, c + Vec3(s * hu, 0, 0) - n * 0.0, (Vec3(1, 0, 0), -n, v), (0.006, 0.012, hv), black)
    x0, y0, x1, y1 = ATLAS["icp"]
    c = (panel_point(x0, y0) + panel_point(x1, y1)) * 0.5 + n * 0.025
    hu = (x1 - x0) / 1024 * PANEL_HALF[0]
    hv = (y1 - y0) / 640 * PANEL_HALF[1]
    panels.rect(c, Vec3(1, 0, 0), v, hu, hv, "icp")
    obox(plain, c - n * 0.014, (Vec3(1, 0, 0), -n, v), (hu, 0.012, hv), dark)
    # gear handle
    gp = panel_point(22, 250)
    cylinder(plain, gp, gp + n * 0.07, 0.008, metal, 6)
    cylinder(plain, gp + n * 0.07 - Vec3(0.02, 0, 0), gp + n * 0.07 + Vec3(0.02, 0, 0), 0.016, (0.86, 0.86, 0.82, 1.0), 8)

    # --- glareshield: flat topped hood over the panel, HUD on top
    top_z = PANEL_CENTER.z + PANEL_HALF[1] * v.z + 0.05
    rings = []
    for y, hw, drop in ((3.30, 0.30, 0.03), (3.34, 0.34, 0.0), (3.55, 0.35, 0.0), (3.78, 0.30, 0.0), (3.90, 0.18, 0.03)):
        ring = []
        for k in range(17):
            t = math.pi * k / 16
            c, s = math.cos(t), math.sin(t)
            ring.append(Vec3(hw * math.copysign(abs(c) ** 0.4, c), y, top_z - 0.07 - drop + 0.07 * abs(s) ** 0.4))
        rings.append(ring)
    plain.loft(rings, (0.075, 0.077, 0.08, 1.0), cap_back=(0.075, 0.077, 0.08, 1.0))
    # HUD: base, side posts, top bar and two combiner glasses
    hy = 3.55
    obox(plain, Vec3(0, hy - 0.02, top_z + 0.015), _axes_pitch(0.0), (0.11, 0.09, 0.02), dark)
    for s in (-1, 1):
        cylinder(plain, Vec3(s * 0.088, hy - 0.04, top_z + 0.02), Vec3(s * 0.088, hy + 0.01, top_z + 0.19), 0.009,
                 black, 6)
    cylinder(plain, Vec3(-0.09, hy + 0.012, top_z + 0.19), Vec3(0.09, hy + 0.012, top_z + 0.19), 0.008, black, 6)
    tint = (0.30, 0.55, 0.42, 0.22)
    for dy in (0.0, 0.035):
        a = Vec3(-0.08, hy - 0.035 + dy, top_z + 0.03)
        b = Vec3(0.08, hy - 0.035 + dy, top_z + 0.03)
        glass.quad(a, b, b + Vec3(0, 0.045, 0.15), a + Vec3(0, 0.045, 0.15), tint, outward=Vec3(0, -1, 0.3))

    # --- side consoles (textured tops)
    for side, region in ((-1, "console_l"), (1, "console_r")):
        xa, xb = CONSOLE_X
        y0, y1 = CONSOLE_Y
        cx = side * (xa + xb) / 2
        hy_ = (y1 - y0) / 2
        hx = (xb - xa) / 2
        cy = (y0 + y1) / 2
        # the atlas strip runs along the console with its top row on the outboard edge, so the labels
        # read like a page on a table seen from the seat
        panels.rect(Vec3(cx, cy, CONSOLE_TOP + 0.001), Vec3(0, -side, 0), Vec3(side, 0, 0), hy_, hx, region)
        obox(plain, Vec3(cx, cy, (CONSOLE_TOP + 0.08) / 2 - 0.004), _axes_pitch(0.0),
             (hx, hy_, (CONSOLE_TOP - 0.08) / 2), dark)
        # aft part of the console wall up to the sill
        obox(plain, Vec3(side * (rim(2.2)[0] - 0.02), 2.25, CONSOLE_TOP + 0.04), _axes_pitch(0.0), (0.02, 0.15, 0.06),
             grey)

    # --- side stick (right console) and throttle (left console)
    sb = Vec3(0.33, 3.02, CONSOLE_TOP)
    cylinder(plain, sb, sb + Vec3(0, 0, 0.03), 0.04, black, 12)                   # rubber boot
    grip_a = sb + Vec3(0, 0, 0.025)
    grip_b = sb + Vec3(-0.01, 0.02, 0.13)
    cylinder(plain, grip_a, grip_b, 0.021, (0.16, 0.16, 0.17, 1.0), 10)
    obox(plain, grip_b + Vec3(0, 0.004, 0.012), _axes_pitch(0.15), (0.024, 0.03, 0.02), (0.16, 0.16, 0.17, 1.0))
    obox(plain, grip_b + Vec3(0, 0.03, -0.03), _axes_pitch(0.4), (0.008, 0.008, 0.016), (0.55, 0.08, 0.06, 1.0))  # trigger
    for dx, col in ((-0.01, (0.75, 0.75, 0.7, 1.0)), (0.01, (0.05, 0.05, 0.05, 1.0))):
        obox(plain, grip_b + Vec3(dx, 0.0, 0.034), _axes_pitch(0.0), (0.006, 0.006, 0.004), col)   # hat switches
    obox(plain, Vec3(0.34, 3.09, CONSOLE_TOP + 0.045), _axes_pitch(0.0), (0.035, 0.012, 0.045), dark)   # wrist rest
    tb = Vec3(-0.33, 2.80, CONSOLE_TOP)
    obox(plain, tb + Vec3(0, 0.08, 0.008), _axes_pitch(0.0), (0.012, 0.14, 0.008), black)                # quadrant slot
    obox(plain, tb + Vec3(0, 0.14, 0.06), _axes_pitch(0.25), (0.032, 0.05, 0.035), (0.17, 0.17, 0.18, 1.0))  # grip
    obox(plain, tb + Vec3(0.018, 0.17, 0.085), _axes_pitch(0.25), (0.006, 0.008, 0.006), (0.7, 0.7, 0.65, 1.0))
    cylinder(plain, tb + Vec3(0, 0.12, 0.0), tb + Vec3(0, 0.13, 0.04), 0.009, metal, 6)

    # --- ACES II ejection seat (reclined 30 degrees)
    ax, fwd, up = _axes_pitch(BACK_ANGLE)          # pitched back: "up" leans aft
    back_up = Vec3(0, -math.sin(BACK_ANGLE), math.cos(BACK_ANGLE))
    back_n = Vec3(0, math.cos(BACK_ANGLE), math.sin(BACK_ANGLE))
    seat_ax = (Vec3(1, 0, 0), back_n, back_up)
    pan_ax = _axes_pitch(math.radians(8))
    # bucket and survival kit
    obox(plain, HIP + Vec3(0, 0.17, -0.10), pan_ax, (0.22, 0.20, 0.07), dark)
    panels.box(HIP + Vec3(0, 0.17, -0.02), pan_ax, (0.19, 0.18, 0.025), "cushion")
    for s in (-1, 1):                                            # bucket side walls
        obox(plain, HIP + Vec3(s * 0.225, 0.08, 0.06), seat_ax, (0.012, 0.16, 0.20), grey)
    # back cushion, frame and headbox
    panels.box(HIP + back_up * 0.36 + back_n * 0.0, seat_ax, (0.19, 0.03, 0.30), "cushion")
    obox(plain, HIP + back_up * 0.40 - back_n * 0.06, seat_ax, (0.21, 0.04, 0.40), dark)
    head = HIP + back_up * 0.86 - back_n * 0.02
    obox(plain, head, seat_ax, (0.15, 0.09, 0.12), (0.21, 0.22, 0.20, 1.0))
    obox(plain, head + back_n * 0.092, seat_ax, (0.10, 0.004, 0.07), (0.12, 0.12, 0.11, 1.0))      # head pad
    panels.rect(head + Vec3(0.152, 0, 0), Vec3(0, 1, 0), back_up, 0.06, 0.04, "placard")
    panels.rect(head - Vec3(0.152, 0, 0), Vec3(0, -1, 0), back_up, 0.06, 0.04, "placard")
    for s in (-1, 1):                                            # catapult rails behind the seat
        cylinder(plain, HIP - back_n * 0.12 + Vec3(s * 0.17, 0, -0.12),
                 HIP + back_up * 1.0 - back_n * 0.12 + Vec3(s * 0.17, 0, 0), 0.018, metal, 6)
    # shoulder harness and lap belt (olive webbing)
    for s in (-1, 1):
        obox(plain, HIP + back_up * 0.45 + back_n * 0.036 + Vec3(s * 0.08, 0, 0), seat_ax, (0.022, 0.004, 0.20), olive)
        obox(plain, HIP + Vec3(s * 0.12, 0.10, 0.012), pan_ax, (0.022, 0.08, 0.004), olive)
    obox(plain, HIP + Vec3(0, 0.15, 0.02), pan_ax, (0.05, 0.03, 0.006), metal)                     # buckle
    # yellow and black ejection handle on the front of the seat
    panels.box(HIP + Vec3(0, 0.37, -0.03), _axes_pitch(0.0), (0.075, 0.012, 0.03), "stripes")
    # rudder pedals
    for s in (-1, 1):
        obox(plain, Vec3(s * 0.12, 3.45, 0.22), _axes_pitch(math.radians(-60)), (0.05, 0.015, 0.09), grey)

    # --- tub details: floor, rear bulkhead with avionics boxes
    obox(plain, Vec3(0, 2.07, 0.75), _axes_pitch(0.0), (rim(2.1)[0] - 0.03, 0.05, 0.12), dark)
    for k, (x, z) in enumerate(((-0.2, 0.84), (0.0, 0.86), (0.2, 0.84))):
        obox(plain, Vec3(x, 2.04, z), _axes_pitch(0.0), (0.08, 0.03, 0.04), (0.16, 0.17, 0.18, 1.0))
    # canopy sill padding (both sides)
    for s in (-1, 1):
        for y0, y1 in ((2.2, 2.7), (2.7, 3.2)):
            w0, z0 = rim(y0)
            w1, z1 = rim(y1)
            a = Vec3(s * (w0 - 0.015), y0, z0 - 0.025)
            b = Vec3(s * (w1 - 0.015), y1, z1 - 0.025)
            obox(plain, (a + b) * 0.5, (Vec3(1, 0, 0), _unit(b - a), Vec3(0, 0, 1)), (0.02, (b - a).length() / 2, 0.025),
                 grey)
    return panels, screens


def _unit(v):
    v = Vec3(v)
    v.normalize()
    return v


_TEXTURE = {}


def cockpit_texture():
    if "tex" not in _TEXTURE:
        tex = Texture("cockpit")
        if not tex.read(Filename.fromOsSpecific(TEXTURE_PATH)):
            return None
        tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        tex.setMagfilter(SamplerState.FT_linear)
        tex.setAnisotropicDegree(8)
        _TEXTURE["tex"] = tex
    return _TEXTURE["tex"]
