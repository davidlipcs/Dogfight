"""MiG-31 of the Russian Aerospace Forces: the paint, from photographs.

The light grey of the Russian interceptors all over, a slightly lighter radome, a grey dielectric fin cap, darker
titanium round the nozzles, red stars on the fins and under the wings, the red side number on the intake boxes.
"""

import numpy as np

import jk_paint as P

SIDE_NUMBER = "26"
GREY = (0.665, 0.690, 0.710)
BELLY = (0.700, 0.720, 0.735)
RADOME = (0.720, 0.725, 0.715)
DIELECTRIC = (0.55, 0.57, 0.58)
TITANIUM = (0.420, 0.420, 0.430)
RED, WHITE = (0.80, 0.10, 0.10), (0.94, 0.94, 0.93)
Y_RADOME = 8.10


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
    is_nac = starts("nacelle", "boom")

    t = P.smooth(-0.5, 0.2, n[:, 2])
    rgb = np.asarray(BELLY) * (1 - t)[:, None] + np.asarray(GREY) * t[:, None]
    rgb = rgb * (0.975 + 0.05 * P.fbm(p, 1.8, 3, seed=3))[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 0.3, 2, seed=9))[:, None]
    rad = is_fus & (y > Y_RADOME)
    rgb[rad] = RADOME
    cap = is_fin & (z > 3.30)
    rgb[cap] = DIELECTRIC
    ti = (is_nac | is_fus) & (y < -9.2)
    rgb[ti] = np.asarray(TITANIUM) * (0.95 + 0.1 * P.fbm(p[ti], 0.4, 2, seed=5))[:, None]

    lines = np.zeros(len(p))
    for yy in (Y_RADOME, 7.30, 2.90, 1.00, -1.50, -4.00, -6.70, -8.50):
        lines = np.maximum(lines, P.line_mask(y - yy, 0.012) * (is_fus | is_nac))
    for xx in (3.20, 4.40, 5.60):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.010) * is_wing * (np.abs(n[:, 2]) > 0.5))
    rgb = rgb * (1.0 - 0.17 * lines)[:, None]

    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    sx = np.sign(n[:, 0])
    roundel(rgb, fin_faces, (y + 8.05) * sx, z, (0.0, 2.15), 0.42)
    under = is_wing & (n[:, 2] < -0.5)
    roundel(rgb, under, y, ax, (-4.10, 5.15), 0.62)

    side = is_nac & (n[:, 0] * np.sign(x) > 0.6) & (y > -1.0) & (y < 2.5)
    num = np.zeros(len(p))
    rim = np.zeros(len(p))
    u = (y[side] - 0.80) * np.sign(n[side, 0])
    num[side] = P.text_mask(SIDE_NUMBER, u, z[side], (0.0, -0.10), 0.55)
    for du, dv in ((0.025, 0), (-0.025, 0), (0, 0.025), (0, -0.025)):
        rim[side] = np.maximum(rim[side], P.text_mask(SIDE_NUMBER, u + du, z[side] + dv, (0.0, -0.10), 0.55))
    rgb = P.mix(rgb, WHITE, 0.95 * rim)
    rgb = P.mix(rgb, RED, 0.95 * num)

    rough = np.full(len(p), 0.58) + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    rough[ti] = 0.42
    metal = np.zeros(len(p))
    metal[ti] = 0.6
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_m = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    out_m[mask] = metal
    return out_rgb, out_r, out_m
