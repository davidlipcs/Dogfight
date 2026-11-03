"""Dassault Rafale C of the French Air and Space Force: the paint, from the photograph.

One dark grey all over (the standard "gris foncé" of the French Rafales; the radome the same), small roundels
(red-white-blue, blue in the centre) on the wings near the tips, top and bottom, and on the intake sides, the low visibility code "4-GA"
under the cockpit and the serial on the fin in a darker grey.
"""

import numpy as np

import jk_paint as P

CODE = "4-GA"
SERIAL = "142"
GREY = (0.330, 0.345, 0.375)
BELLY = (0.370, 0.385, 0.410)
DARK = (0.180, 0.185, 0.200)
BLUE, WHITE, RED = (0.10, 0.20, 0.55), (0.92, 0.92, 0.92), (0.78, 0.10, 0.12)
Y_RADOME = 5.70


def roundel(rgb, sel, u, v, c, r):
    d = np.hypot(u[sel] - c[0], v[sel] - c[1])
    idx = np.where(sel)[0]
    rgb[idx[d < r]] = RED                     # the French roundel: red ring, white, blue centre
    rgb[idx[d < r * 0.66]] = WHITE
    rgb[idx[d < r * 0.33]] = BLUE


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

    t = P.smooth(-0.45, 0.15, n[:, 2])
    rgb = np.asarray(BELLY) * (1 - t)[:, None] + np.asarray(GREY) * t[:, None]
    rgb = rgb * (0.97 + 0.06 * P.fbm(p, 1.2, 3, seed=3))[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 0.25, 2, seed=9))[:, None]

    lines = np.zeros(len(p))
    for yy in (Y_RADOME, 5.00, 2.45, 0.80, -1.00, -2.80, -4.60, -6.30):
        lines = np.maximum(lines, P.line_mask(y - yy, 0.010) * (is_fus | is_nac))
    for xx in (2.20, 3.10, 4.20):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.009) * is_wing * (np.abs(n[:, 2]) > 0.5))
    rgb = rgb * (1.0 - 0.22 * lines)[:, None]
    near = np.hypot(ax - 0.62, z - 0.22)
    soot = is_fus * P.smooth(-6.2, -6.65, y) * P.smooth(0.65, 0.42, near)
    rgb = P.mix(rgb, (0.20, 0.19, 0.19), 0.5 * soot)

    wing_faces = is_wing & (np.abs(n[:, 2]) > 0.5)
    roundel(rgb, wing_faces, ax, y, (4.70, -5.05), 0.26)
    side = (is_nac | is_fus) & (n[:, 0] * np.sign(x) > 0.6) & (y > -1.5) & (y < 1.5)
    roundel(rgb, side, y, z, (0.30, -0.10), 0.24)

    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    sx = np.sign(n[:, 0])
    t1 = np.zeros(len(p))
    t1[fin_faces] = P.text_mask(SERIAL, (y[fin_faces] + 5.70) * sx[fin_faces], z[fin_faces], (0.0, 1.35), 0.20)
    nose = is_fus & (np.abs(n[:, 0]) > 0.5) & (y > 2.5) & (y < 5.2)
    t1[nose] = np.maximum(t1[nose], P.text_mask(CODE, (y[nose] - 3.55) * np.sign(n[nose, 0]), z[nose], (0.0, 0.32), 0.17))
    rgb = P.mix(rgb, DARK, 0.85 * t1)

    rough = np.full(len(p), 0.52) + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
