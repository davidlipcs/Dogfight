"""Eurofighter Typhoon FGR4 of the Royal Air Force: the paint, from the photograph.

Light grey with darker grey disruptive patches on the upper surfaces (the photograph's two tone scheme), light grey
underneath, a light grey radome, low visibility roundels (pale red and blue) on the wings and the intake sides, the
squadron code on the fin and the serial on the rear fuselage in dark grey.
"""

import numpy as np

import jk_paint as P

CODE = "FA"
SERIAL = "ZK301"
LIGHT = (0.640, 0.660, 0.680)
PATCH = (0.520, 0.545, 0.570)
BELLY = (0.700, 0.715, 0.730)
RADOME = (0.600, 0.610, 0.620)
DARK = (0.250, 0.260, 0.280)
PINK, PALEBLUE = (0.780, 0.520, 0.520), (0.500, 0.600, 0.740)
Y_RADOME = 6.40


def roundel(rgb, sel, u, v, c, r):
    d = np.hypot(u[sel] - c[0], v[sel] - c[1])
    idx = np.where(sel)[0]
    rgb[idx[d < r]] = PALEBLUE                # RAF low visibility: pale blue ring, pink centre
    rgb[idx[d < r * 0.5]] = PINK


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

    # the patches: long soft edged blotches on the upper surfaces, mirrored
    q = np.stack([ax * 0.7 + y * 0.7, y * 0.7 - ax * 0.7, z], axis=1)
    f = P.fbm(q * np.array([0.6, 1.4, 1.0]), 2.6, 3, seed=17)
    patch = (f > 0.56) & (n[:, 2] > 0.25) & (is_wing | is_fus) & (y < 4.0)
    t = P.smooth(-0.40, 0.15, n[:, 2])
    rgb = np.asarray(BELLY) * (1 - t)[:, None] + np.asarray(LIGHT) * t[:, None]
    rgb[patch] = PATCH
    rgb = rgb * (0.975 + 0.05 * P.fbm(p, 1.4, 3, seed=3))[:, None]
    rad = is_fus & (y > Y_RADOME)
    rgb[rad] = RADOME

    lines = np.zeros(len(p))
    for yy in (Y_RADOME, 5.75, 2.40, 0.80, -1.00, -2.80, -4.50, -6.00):
        lines = np.maximum(lines, P.line_mask(y - yy, 0.010) * (is_fus | is_nac))
    for xx in (2.30, 3.20, 4.30):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.009) * is_wing * (np.abs(n[:, 2]) > 0.5))
    rgb = rgb * (1.0 - 0.18 * lines)[:, None]
    near = np.hypot(ax - 0.47, z - 0.08)
    soot = is_fus * P.smooth(-6.0, -6.45, y) * P.smooth(0.65, 0.42, near)
    rgb = P.mix(rgb, (0.30, 0.29, 0.28), 0.5 * soot)

    wing_faces = is_wing & (np.abs(n[:, 2]) > 0.5) & starts("wing")
    roundel(rgb, wing_faces, ax, y, (4.30, -3.95), 0.38)
    side = (is_fus | is_nac) & (n[:, 0] * np.sign(x) > 0.6) & (y > 0.4) & (y < 2.4)
    roundel(rgb, side, y, z, (1.40, 0.35), 0.30)

    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    sx = np.sign(n[:, 0])
    txt = np.zeros(len(p))
    txt[fin_faces] = P.text_mask(CODE, (y[fin_faces] + 6.55) * sx[fin_faces], z[fin_faces], (0.0, 2.00), 0.38)
    rear = is_fus & (np.abs(n[:, 0]) > 0.5) & (y < -3.5) & (y > -6.0)
    txt[rear] = np.maximum(txt[rear], P.text_mask(SERIAL, (y[rear] + 4.80) * np.sign(n[rear, 0]), z[rear], (0.0, 0.45), 0.16))
    rgb = P.mix(rgb, DARK, 0.85 * txt)

    rough = np.full(len(p), 0.55) + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
