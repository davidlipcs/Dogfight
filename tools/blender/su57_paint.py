"""Su-57 of the Russian Aerospace Forces: the digital ("pixel") camouflage, from photographs and the three-view.

A dark blue centre body that breaks up into square blocks of dark blue and blue-grey towards the very light bluish
grey outer wings, tailplanes and fins; light grey radome, blue-grey wing tip panels, red stars with a white rim on the
wings (top and bottom) and the fins, the side number on the forward fuselage.
"""

import numpy as np

import jk_paint as P

SIDE_NUMBER = "51"
LIGHT = (0.765, 0.820, 0.890)
MID = (0.440, 0.505, 0.580)
DARK = (0.200, 0.305, 0.440)
RADOME = (0.760, 0.785, 0.800)
TIP = (0.420, 0.520, 0.640)
RED, WHITE = (0.80, 0.10, 0.10), (0.94, 0.94, 0.93)
Y_RADOME = 8.40
BLOCK = 0.32                  # the size of the camouflage squares


def star(u, v, c, r, inner=0.40):
    pts = []
    for k in range(10):
        a = np.pi / 2 + k * np.pi / 5
        rr = r if k % 2 == 0 else r * inner
        pts.append((c[0] + rr * np.cos(a), c[1] + rr * np.sin(a)))
    return P.in_polygon(u, v, pts)


def roundel(rgb, sel, u, v, c, r):
    for rad, col in ((r * 1.18, RED), (r * 1.10, WHITE), (r, RED)):
        m = np.zeros(len(rgb), bool)
        m[sel] = star(u[sel], v[sel], c, rad)
        rgb[m] = col


def block_noise(a, b, seed):
    """One random number per BLOCK x BLOCK square of the (a, b) plane."""
    ia, ib = np.floor(a / BLOCK).astype(np.int64), np.floor(b / BLOCK).astype(np.int64)
    return P._hash(ia, ib, np.zeros_like(ia), seed)


def painter(pos, nrm, oid, names, mask):
    H, W = mask.shape
    p, n = pos[mask].astype(np.float64), nrm[mask].astype(np.float64)
    name = np.array(names)[oid[mask]]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    starts = lambda *k: np.logical_or.reduce([np.char.startswith(name, s) for s in k])
    is_fin = starts("fin", "rudder")
    is_wing = starts("wing", "ail", "flap", "lef")
    is_fus = name == "fuselage"
    is_nac = starts("nacelle")
    is_stab = starts("stab")

    # how dark: dark along the centre body, light out on the wings; vertical faces use their own plane
    vertical = np.abs(n[:, 2]) < 0.45
    d = 1.0 - P.smooth(1.3, 6.0, ax)                       # 1 on the spine, 0 out on the wings
    d = np.where(is_fin | is_stab, 0.25, d)
    d = d - 0.25 * P.smooth(7.0, 9.6, y)                    # the nose is lighter
    d = d + 0.18 * (P.fbm(np.stack([x, y, z], 1), 2.2, 2, seed=4) - 0.5)
    a = np.where(vertical, y, y)
    b = np.where(vertical, z * 1.0 + 50.0 * np.sign(x), ax)
    r1 = block_noise(a, b, 11)
    r2 = block_noise(a + 0.5 * BLOCK, b, 23)
    dark = d + 0.60 * (r1 - 0.5) > 0.47
    mid = (~dark) & (d + 0.70 * (r2 - 0.5) > 0.24)
    speck = dark & (block_noise(a + 0.25 * BLOCK, b + 0.5 * BLOCK, 37) > 0.88) & (d < 0.95)
    dark &= ~speck
    mid |= speck
    up = n[:, 2] > -0.30
    rgb = np.tile(np.asarray(LIGHT), (len(p), 1))
    rgb[mid] = MID
    rgb[dark] = DARK
    # underneath: light, with a few mid blocks
    under = ~up
    ub = (block_noise(y, ax, 41) > 0.80) & under & (ax < 3.5)
    rgb[under] = LIGHT
    rgb[ub] = MID
    rgb = rgb * (0.98 + 0.04 * P.fbm(p, 1.4, 2, seed=3))[:, None]

    rad = is_fus & (y > Y_RADOME)
    rgb[rad] = RADOME
    tips = is_wing & (ax > 6.55)
    rgb[tips] = TIP

    lines = np.zeros(len(p))
    for yy in (Y_RADOME, 4.30, 0.05, -3.00, -6.40):
        lines = np.maximum(lines, P.line_mask(y - yy, 0.010) * (is_fus | is_nac))
    rgb = rgb * (1.0 - 0.15 * lines)[:, None]

    # red stars on the wings (top and bottom) and the fins
    wing_faces = is_wing & (np.abs(n[:, 2]) > 0.5)
    roundel(rgb, wing_faces, y, ax, (-3.55, 5.55), 0.42)
    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.3)
    sx = np.sign(n[:, 0])
    roundel(rgb, fin_faces, (y + 5.55) * sx, z, (0.0, 2.05), 0.30)

    # side number under the cockpit
    side = is_fus & (np.abs(n[:, 0]) > 0.5) & (y > 3.5) & (y < 6.5)
    num = np.zeros(len(p))
    rim = np.zeros(len(p))
    u = (y[side] - 4.75) * np.sign(n[side, 0])
    num[side] = P.text_mask(SIDE_NUMBER, u, z[side], (0.0, 0.62), 0.34)
    for du, dv in ((0.02, 0), (-0.02, 0), (0, 0.02), (0, -0.02)):
        rim[side] = np.maximum(rim[side], P.text_mask(SIDE_NUMBER, u + du, z[side] + dv, (0.0, 0.62), 0.34))
    rgb = P.mix(rgb, WHITE, 0.9 * rim)
    rgb = P.mix(rgb, (0.12, 0.20, 0.36), 0.95 * num)

    rough = np.full(len(p), 0.50) + 0.05 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
