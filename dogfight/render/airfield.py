"""Visual air base: runway with ICAO markings, taxiway, apron, hardened aircraft
shelters, control tower, parked F-16s and runway / approach lights."""

import math

from panda3d.core import CardMaker, ColorBlendAttrib, TextNode, TransparencyAttrib, Vec3

from ..sim.airfield import APRON, RUNWAY_LENGTH, RUNWAY_WIDTH, TAXIWAY_OFFSET, TAXIWAY_WIDTH
from .effects import soft_texture
from .meshbuilder import MeshBuilder, ellipse_ring
from .models import box

ASPHALT = (0.20, 0.205, 0.215, 1.0)
CONCRETE = (0.52, 0.52, 0.50, 1.0)
WHITE = (0.92, 0.92, 0.90, 1.0)
YELLOW = (0.88, 0.72, 0.18, 1.0)
SHELTER = (0.55, 0.54, 0.50, 1.0)
UP = Vec3(0, 0, 1)


def _rect(mb, x0, y0, x1, y1, z, color):
    mb.quad(Vec3(x0, y0, z), Vec3(x1, y0, z), Vec3(x1, y1, z), Vec3(x0, y1, z), color, outward=UP)


def _layer(root, mb, name, offset):
    np = mb.build(name)
    np.reparentTo(root)
    np.setDepthOffset(offset)
    return np


def build_airfield(base, airfield, models=None):
    root = base.render.attachNewNode("airfield")
    root.setPos(airfield.x, airfield.y, airfield.elevation)
    half_l = RUNWAY_LENGTH * 0.5
    half_w = RUNWAY_WIDTH * 0.5
    z = 0.05

    # ---- pavement (asphalt runway, concrete taxiway / apron)
    pave = MeshBuilder()
    step = 250.0                      # split long strips (big polygons light badly)
    y = -half_l - 60.0
    while y < half_l + 60.0:
        y1 = min(y + step, half_l + 60.0)
        _rect(pave, -half_w - 3.0, y, half_w + 3.0, y1, z, ASPHALT)
        y = y1
    tx = TAXIWAY_OFFSET
    y = -half_l
    while y < half_l:
        y1 = min(y + step, half_l)
        _rect(pave, tx - TAXIWAY_WIDTH * 0.5, y, tx + TAXIWAY_WIDTH * 0.5, y1, z, CONCRETE)
        y = y1
    for cy in (-half_l + 60.0, 0.0, half_l - 60.0):
        _rect(pave, half_w + 3.0, cy - TAXIWAY_WIDTH * 0.5, tx - TAXIWAY_WIDTH * 0.5, cy + TAXIWAY_WIDTH * 0.5, z,
              CONCRETE)
    ax0, ax1, ay0, ay1 = APRON
    _rect(pave, tx + TAXIWAY_WIDTH * 0.5, ay0, ax1, ay1, z, CONCRETE)
    _layer(root, pave, "pavement", 1)

    # ---- markings
    mk = MeshBuilder()
    zm = z + 0.02
    # edge lines and dashed centre line
    _rect(mk, -half_w, -half_l, -half_w + 0.9, half_l, zm, WHITE)
    _rect(mk, half_w - 0.9, -half_l, half_w, half_l, zm, WHITE)
    y = -half_l + 120.0
    while y < half_l - 120.0:
        _rect(mk, -0.45, y, 0.45, y + 30.0, zm, WHITE)
        y += 50.0
    for sign in (1.0, -1.0):          # both runway ends
        end = -half_l * sign
        inward = sign
        # threshold "piano keys"
        for k in range(8):
            off = 3.0 + k * 2.6
            for side in (-1.0, 1.0):
                x0 = side * off
                _rect(mk, min(x0, x0 + side * 1.8), end + inward * 6.0, max(x0, x0 + side * 1.8),
                      end + inward * 36.0, zm, WHITE)
        # aiming point markers (400 m) and touchdown zone bars
        for side in (-1.0, 1.0):
            x0 = side * 5.5
            _rect(mk, min(x0, x0 + side * 9.0), end + inward * 400.0, max(x0, x0 + side * 9.0),
                  end + inward * 445.0, zm, WHITE)
            for dist, bars in ((150.0, 3), (300.0, 2), (600.0, 2), (750.0, 1)):
                for b in range(bars):
                    xb = side * (6.0 + b * 3.0)
                    _rect(mk, min(xb, xb + side * 1.8), end + inward * dist, max(xb, xb + side * 1.8),
                          end + inward * (dist + 22.0), zm, WHITE)
    # taxiway centre line (yellow)
    _rect(mk, tx - 0.25, -half_l, tx + 0.25, half_l, zm, YELLOW)
    _layer(root, mk, "markings", 2)

    # runway numbers (36 at the south end, 18 at the north end)
    for text, y_pos, heading in (("36", -half_l + 75.0, 0.0), ("18", half_l - 75.0, 180.0)):
        tn = TextNode("rwy" + text)
        tn.setText(text)
        tn.setAlign(TextNode.ACenter)
        tn.setTextColor(*WHITE)
        num = root.attachNewNode(tn)
        num.setScale(16.0)
        num.setPos(0, y_pos, zm + 0.01)
        num.setHpr(heading, -90, 0)
        num.setDepthOffset(3)
        num.setLightOff(1)

    # ---- buildings: hardened aircraft shelters, tower, hangar
    bld = MeshBuilder()
    for k in range(6):
        cx = ax1 - 40.0
        cy = ay0 + 60.0 + k * 115.0
        _shelter(bld, cx, cy, 26.0, 36.0, 11.0)
    tower_x, tower_y = tx + 80.0, ay0 - 60.0
    box(bld, (tower_x, tower_y, 12.0), (5.0, 5.0, 12.0), CONCRETE)
    box(bld, (tower_x, tower_y, 26.0), (7.0, 7.0, 2.5), (0.18, 0.26, 0.30, 1.0))       # glass cab
    box(bld, (tower_x, tower_y, 29.0), (7.5, 7.5, 0.5), CONCRETE)
    box(bld, (tx + 120.0, ay1 + 80.0, 9.0), (40.0, 30.0, 9.0), (0.45, 0.47, 0.44, 1.0))  # maintenance hangar
    for k in range(4):                                                             # fuel tanks
        _tank(bld, ax1 + 60.0, ay0 + 40.0 + k * 22.0, 8.0, 9.0)
    _layer(root, bld, "buildings", 0)

    # ---- parked F-16s on the apron
    if models is not None:
        for k in range(3):
            ac = models.aircraft("viper")
            ac.reparentTo(root)
            ac.setPos(tx + TAXIWAY_WIDTH + 45.0, ay0 + 90.0 + k * 45.0, 2.05)
            ac.setH(90.0)
            gear = models.gear()
            gear.reparentTo(ac)

    # ---- runway edge lights + approach lights
    _lights(root, half_l, half_w)
    return root


def _shelter(mb, cx, cy, width, length, height):
    """Hardened aircraft shelter: a concrete half-barrel facing the taxiway (west)."""
    rings = []
    for x in (cx - length * 0.5, cx + length * 0.5):
        ring = ellipse_ring(0.0, width * 0.5, 0.0, height, segments=10, start=0.0, end=math.pi)
        rings.append([Vec3(x, cy + p.x, p.z) for p in ring])
    mb.loft(rings, SHELTER, smooth=True)
    back = rings[1]
    mb.poly([Vec3(cx + length * 0.5, cy, 0.0)] + back, SHELTER, outward=Vec3(1, 0, 0))
    door = rings[0]
    mb.poly([Vec3(cx - length * 0.5, cy, 0.0)] + door[::-1], (0.30, 0.31, 0.30, 1.0), outward=Vec3(-1, 0, 0))


def _tank(mb, cx, cy, radius, height):
    rings = [[Vec3(cx + p.x, cy + p.z, z) for p in ellipse_ring(0.0, radius, 0.0, radius, segments=12)]
             for z in (0.0, height)]
    mb.loft(rings, (0.70, 0.70, 0.66, 1.0), smooth=True, cap_front=(0.65, 0.65, 0.62, 1.0))


def _lights(root, half_l, half_w):
    lights = root.attachNewNode("lights")
    lights.setLightOff(1)
    lights.setFogOff(1)
    lights.setDepthWrite(False)
    lights.setTransparency(TransparencyAttrib.MAlpha)
    lights.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha,
                                           ColorBlendAttrib.OOne))
    lights.setTexture(soft_texture(32, 2.0, "light"))
    lights.setBin("fixed", 15)
    cm = CardMaker("light")
    cm.setFrame(-0.5, 0.5, -0.5, 0.5)
    card = cm.generate()

    def lamp(x, y, color, size=3.0):
        n = lights.attachNewNode(card.copySubgraph())
        n.setPos(x, y, 0.6)
        n.setScale(size)
        n.setBillboardPointEye()
        n.setColor(*color)

    y = -half_l
    while y <= half_l:
        for side in (-1.0, 1.0):
            lamp(side * (half_w + 2.0), y, (1.0, 0.95, 0.8, 0.9))
        y += 60.0
    for side in (-1.0, 1.0):                  # threshold (green) and runway end (red)
        for k in range(6):
            x = side * (3.0 + k * 3.5)
            lamp(x, -half_l - 2.0, (0.3, 1.0, 0.4, 1.0))
            lamp(x, half_l + 2.0, (0.3, 1.0, 0.4, 1.0))
    for d in range(1, 11):                    # approach light bars south of runway 36
        y = -half_l - d * 60.0
        for k in range(-3, 4):
            lamp(k * 3.0, y, (1.0, 1.0, 0.9, 1.0), 2.5)
    return lights
