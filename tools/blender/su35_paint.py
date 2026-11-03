"""Su-35S of the Russian Aerospace Forces: the paint, from photographs.

The standard two-tone blue-grey scheme: soft edged bands of a dark grey-blue and a medium blue-grey over a pale grey-blue
on the upper surfaces and the sides, pale grey-blue underneath, a light grey radome, darker fins with the red star,
red stars under the wings, a red side number with a white rim on the intake sides.
"""

import numpy as np

import jk_paint as P

SIDE_NUMBER = "01"
PALE = (0.700, 0.765, 0.835)
MID = (0.480, 0.580, 0.700)
DARK = (0.300, 0.420, 0.570)
BELLY = (0.790, 0.830, 0.865)
RADOME = (0.780, 0.790, 0.780)
DIELECTRIC = (0.80, 0.81, 0.80)
RED, WHITE = (0.80, 0.10, 0.10), (0.94, 0.94, 0.93)
Y_RADOME = 7.62


def star(u, v, c, r, inner=0.40):
    """5 point star mask (point up) of radius r centred at c in (u, v); the white rim and the red rim round the red
    star of the Russian roundel come from bigger stars drawn first."""
    pts = []
    for k in range(10):
        a = np.pi / 2 + k * np.pi / 5
        rr = r if k % 2 == 0 else r * inner
        pts.append((c[0] + rr * np.cos(a), c[1] + rr * np.sin(a)))
    return P.in_polygon(u, v, pts)


def roundel(rgb, sel, u, v, c, r):
    """The Russian star: red, a white rim, a thin red outline."""
    for rad, col in ((r * 1.18, RED), (r * 1.10, WHITE), (r, RED)):
        m = np.zeros(len(rgb), bool)
        m[sel] = star(u[sel], v[sel], c, rad)
        rgb[m] = col


def painter(pos, nrm, oid, names, mask):
    H, W = mask.shape
    p, n = pos[mask].astype(np.float64), nrm[mask].astype(np.float64)
    name = np.array(names)[oid[mask]]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    starts = lambda *k: np.logical_or.reduce([np.char.startswith(name, s) for s in k])
    is_fin = starts("fin", "rudder")
    is_wing = starts("wing", "ail", "flap", "lef", "pod")
    is_fus = name == "fuselage"
    is_nac = starts("nacelle")
    is_stab = starts("stab")

    # camouflage: bands running diagonally over the top and the sides (the same pattern on both sides, mirrored)
    # long bands across the airframe, leaning back from the leading edges (stretched noise)
    u = (ax * 0.75 + y * 0.66) * 0.55
    v = (y * 0.75 - ax * 0.66) * 1.7
    q = np.stack([u, v, z * 0.8], axis=1)
    f = P.fbm(q, 3.0, 3, seed=7)
    g = P.fbm(q + 31.0, 2.6, 3, seed=13)
    cam = np.where(f > 0.57, 2, np.where(g > 0.54, 1, 0))
    tone = np.array([PALE, MID, DARK])[cam]
    up = P.smooth(-0.55, -0.05, n[:, 2])                  # sides and top: camouflage; underneath: pale
    rgb = np.asarray(BELLY) * (1 - up)[:, None] + tone * up[:, None]
    # the fins: darker overall with the bands
    rgb[is_fin] = rgb[is_fin] * 0.82 + np.asarray(DARK) * 0.18
    rgb = rgb * (0.975 + 0.05 * P.fbm(p, 1.6, 3, seed=3))[:, None]

    rad = is_fus & (y > Y_RADOME)
    rgb[rad] = np.asarray(RADOME) * (0.985 + 0.03 * P.fbm(p[rad], 0.8, 2, seed=5))[:, None]
    cap = is_fin & (z > 3.85)
    rgb[cap] = DIELECTRIC

    lines = np.zeros(len(p))
    for yy in (Y_RADOME, 6.80, 5.30, 2.40, 1.20, -0.50, -2.20, -4.00, -5.80, -7.40, -9.00):
        lines = np.maximum(lines, P.line_mask(y - yy, 0.012) * (is_fus | is_nac))
    for xx in (3.40, 4.70, 6.20):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.010) * is_wing * (np.abs(n[:, 2]) > 0.5))
    lines = np.maximum(lines, P.line_mask(z - 1.4, 0.010) * is_fin)
    rgb = rgb * (1.0 - 0.18 * lines)[:, None]

    near = np.hypot(ax - 1.18, z + 0.46)
    soot = (is_nac | is_fus) * P.smooth(-7.2, -7.75, y) * P.smooth(0.85, 0.55, near)
    rgb = P.mix(rgb, (0.28, 0.27, 0.27), 0.45 * soot)

    # red stars: both faces of the fins, under the wings
    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    sx = np.sign(n[:, 0])
    roundel(rgb, fin_faces, (y + 6.15) * sx, z, (0.0, 1.85), 0.58)
    under = is_wing & (n[:, 2] < -0.5)
    roundel(rgb, under, y, ax, (-3.40, 5.20), 0.75)

    # side number on the intakes (red, white rim)
    side = is_nac & (n[:, 0] * np.sign(x) > 0.55) & (y > 0.5)
    num = np.zeros(len(p))
    rim = np.zeros(len(p))
    u = (y[side] - 1.55) * np.sign(n[side, 0])
    num[side] = P.text_mask(SIDE_NUMBER, u, z[side], (0.0, -0.60), 0.46)
    for du, dv in ((0.025, 0), (-0.025, 0), (0, 0.025), (0, -0.025)):
        rim[side] = np.maximum(rim[side], P.text_mask(SIDE_NUMBER, u + du, z[side] + dv, (0.0, -0.60), 0.46))
    rgb = P.mix(rgb, WHITE, 0.95 * rim)
    rgb = P.mix(rgb, RED, 0.95 * num)

    rough = np.full(len(p), 0.55) + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    rough[rad] = 0.45
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
