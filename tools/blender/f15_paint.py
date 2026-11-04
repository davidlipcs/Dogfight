"""F-15EX Eagle II of the US Air Force (40th Flight Test Squadron, Eglin): the paint.

The "Mod Eagle" scheme: a light neutral grey all over with large soft edged patches of a darker blue-grey on the upper
surfaces, a grey radome; the low visibility markings in dark grey: the star and bar on the intakes and the wings, the
ET tail code and the serial on the fins, the USAF lettering on the conformal tanks.
"""

import numpy as np

import f15_shape as S
import jk_paint as P

CODE = "ET"
SERIAL = "AF 20-001"
LIGHT = (0.575, 0.595, 0.615)
PATCH = (0.430, 0.455, 0.490)
BELLY = (0.620, 0.635, 0.650)
RADOME = (0.540, 0.555, 0.570)
MARK = (0.310, 0.320, 0.340)


def painter(pos, nrm, oid, names, mask):
    H, W = mask.shape
    p, n = pos[mask].astype(np.float64), nrm[mask].astype(np.float64)
    name = np.array(names)[oid[mask]]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    yd = y - S.Y0
    starts = lambda *k: np.logical_or.reduce([np.char.startswith(name, s) for s in k])
    is_fin = starts("fin", "rudder")
    is_wing = starts("wing", "ail", "flap")
    is_fus = name == "fuselage"
    is_nac = starts("nacelle", "boom")

    q = np.stack([ax * 0.7 + y * 0.7, y * 0.7 - ax * 0.7, z], axis=1)
    f = P.fbm(q * np.array([0.7, 1.3, 1.0]), 3.0, 3, seed=29)
    patch = (f > 0.55) & (n[:, 2] > 0.2)
    t = P.smooth(-0.45, 0.15, n[:, 2])
    rgb = np.asarray(BELLY) * (1 - t)[:, None] + np.asarray(LIGHT) * t[:, None]
    rgb[patch] = PATCH
    rgb = rgb * (0.975 + 0.05 * P.fbm(p, 1.4, 3, seed=3))[:, None]
    rad = is_fus & (yd > -2.40)
    rgb[rad] = RADOME

    lines = np.zeros(len(p))
    for yy in (-2.40, -3.10, -7.70, -9.50, -11.40, -13.20, -15.10, -16.60):
        lines = np.maximum(lines, P.line_mask(yd - yy, 0.011) * (is_fus | is_nac))
    for xx in (2.55, 3.60, 4.55):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.009) * is_wing * (np.abs(n[:, 2]) > 0.5))
    rgb = rgb * (1.0 - 0.18 * lines)[:, None]
    near = np.hypot(ax - 0.95, z - 0.12)
    soot = (is_fus | is_nac) * P.smooth(-16.4, -17.0, yd) * P.smooth(0.80, 0.55, near)
    rgb = P.mix(rgb, (0.30, 0.29, 0.28), 0.5 * soot)

    def insignia(sel, u, v, c, r):
        m, st = P.star_and_bar(u[sel], v[sel], c, r, (0.0, 1.0))
        idx = np.where(sel)[0]
        rgb[idx[m & ~st]] = MARK
    wtop = is_wing & (n[:, 2] > 0.5) & (x < 0)
    insignia(wtop, ax, yd, (5.20, -13.90), 0.40)
    wbot = is_wing & (n[:, 2] < -0.5) & (x > 0)
    insignia(wbot, ax, yd, (5.20, -13.90), 0.40)
    sx = np.sign(n[:, 0])
    side = is_nac & (n[:, 0] * np.sign(x) > 0.6)
    for s_ in (1.0, -1.0):
        insignia(side & (sx == s_) & (yd > -7.5) & (yd < -5.6), yd * s_, z, (-6.50 * s_, 0.05), 0.32)

    txt = np.zeros(len(p))
    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    txt[fin_faces] = P.text_mask(CODE, (yd[fin_faces] + 17.10) * sx[fin_faces], z[fin_faces], (0.0, 2.60), 0.50)
    txt[fin_faces] = np.maximum(txt[fin_faces], P.text_mask(SERIAL, (yd[fin_faces] + 17.20) * sx[fin_faces], z[fin_faces],
                                                            (0.0, 2.05), 0.12))
    cft = is_nac & (n[:, 0] * np.sign(x) > 0.6) & (yd < -9.5) & (yd > -12.5)
    txt[cft] = np.maximum(txt[cft], P.text_mask("U.S. AIR FORCE", (yd[cft] + 11.0) * sx[cft], z[cft], (0.0, -0.05), 0.16))
    rgb = P.mix(rgb, MARK, 0.9 * txt)

    rough = np.full(len(p), 0.56) + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
