"""F-16C of the US Air Force (388th Fighter Wing, Hill AFB): the paint.

The "Hill grey II" scheme: medium grey on the top and the sides, light grey underneath, the darker grey of the
radome and the anti-glare panel ahead of the canopy; the low visibility markings in dark grey: the star and bar on the
intake sides and the wings (left on top, right underneath), the HL tail code and the serial on the fin, the black and
yellow checks of the 4th Fighter Squadron on the fin tip.
"""

import numpy as np

import f16_shape as S
import jk_paint as P

CODE = "HL"
SERIAL = "AF 88-425"
MEDIUM = (0.545, 0.565, 0.585)
LIGHT = (0.640, 0.655, 0.670)
DARK = (0.380, 0.395, 0.410)
MARK = (0.300, 0.310, 0.325)


def painter(pos, nrm, oid, names, mask):
    H, W = mask.shape
    p, n = pos[mask].astype(np.float64), nrm[mask].astype(np.float64)
    name = np.array(names)[oid[mask]]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    yd = y - S.Y0
    starts = lambda *k: np.logical_or.reduce([np.char.startswith(name, s) for s in k])
    is_fin = starts("fin", "rudder")
    is_wing = starts("wing", "ail", "flap", "lef", "pod")
    is_fus = name == "fuselage"
    is_nac = starts("nacelle")

    t = P.smooth(-0.45, 0.20, n[:, 2])
    rgb = np.asarray(LIGHT) * (1 - t)[:, None] + np.asarray(MEDIUM) * t[:, None]
    rgb[is_fin] = MEDIUM
    rgb = rgb * (0.97 + 0.06 * P.fbm(p, 1.2, 3, seed=3))[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 0.22, 2, seed=9))[:, None]
    rad = is_fus & (yd > -2.20)
    rgb[rad] = DARK
    glare = is_fus & (yd > -3.05) & (yd < -2.20) & (n[:, 2] > 0.3)
    rgb[glare] = DARK

    lines = np.zeros(len(p))
    for yy in (-2.20, -3.00, -6.40, -7.80, -9.20, -10.70, -12.00, -13.40):
        lines = np.maximum(lines, P.line_mask(yd - yy, 0.010) * (is_fus | is_nac))
    for xx in (2.00, 2.70, 3.60):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.009) * is_wing * (np.abs(n[:, 2]) > 0.5))
    rgb = rgb * (1.0 - 0.18 * lines)[:, None]
    near = np.hypot(x, z - 0.55)
    soot = is_fus * P.smooth(-13.8, -14.3, yd) * P.smooth(0.70, 0.50, near)
    rgb = P.mix(rgb, (0.30, 0.29, 0.28), 0.5 * soot)

    def insignia(sel, u, v, c, r):
        m, st = P.star_and_bar(u[sel], v[sel], c, r, (0.0, 1.0))
        idx = np.where(sel)[0]
        rgb[idx[m & ~st]] = MARK
    wtop = is_wing & (n[:, 2] > 0.5) & (x < 0)
    insignia(wtop, ax, yd, (3.40, -10.35), 0.30)
    wbot = is_wing & (n[:, 2] < -0.5) & (x > 0)
    insignia(wbot, ax, yd, (3.40, -10.35), 0.30)
    sx = np.sign(n[:, 0])
    side = (is_nac | is_fus) & (np.abs(n[:, 0]) > 0.5) & (z < 0.2) & (yd < -5.0) & (yd > -7.0)
    for s_ in (1.0, -1.0):
        insignia(side & (sx == s_), yd * s_, z, (-6.00 * s_, -0.22), 0.22)

    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    txt = np.zeros(len(p))
    txt[fin_faces] = P.text_mask(CODE, (yd[fin_faces] + 13.20) * sx[fin_faces], z[fin_faces], (0.0, 2.55), 0.38)
    txt[fin_faces] = np.maximum(txt[fin_faces], P.text_mask(SERIAL, (yd[fin_faces] + 13.35) * sx[fin_faces], z[fin_faces],
                                                            (0.0, 2.15), 0.10))
    rgb = P.mix(rgb, MARK, 0.9 * txt)
    # the fin tip band: yellow and black checks
    band = fin_faces & (z > 3.30)
    chk = ((np.floor((yd + 20) / 0.16) + np.floor(z / 0.08)) % 2 == 0)
    rgb[band & chk] = (0.08, 0.08, 0.09)
    rgb[band & ~chk] = (0.85, 0.70, 0.12)

    rough = np.full(len(p), 0.56) + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
