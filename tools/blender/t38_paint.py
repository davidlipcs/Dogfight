"""T-38C Talon of the US Air Force (Air Education and Training Command): the paint.

Gloss white all over, the black anti-glare panel ahead of the canopy, the full colour star and bar on the intakes and
the wings, the RA tail code and the serial in dark blue on the fin, the blue and white fin band of the 12th Flying
Training Wing.
"""

import numpy as np

import jk_paint as P
import t38_shape as S

WHITE = (0.900, 0.905, 0.910)
BELLY = (0.860, 0.865, 0.870)
BLACK = (0.06, 0.06, 0.07)
BLUE = (0.10, 0.18, 0.45)


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
    is_nac = starts("nacelle")

    t = P.smooth(-0.45, 0.15, n[:, 2])
    rgb = np.asarray(BELLY) * (1 - t)[:, None] + np.asarray(WHITE) * t[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 1.0, 2, seed=3))[:, None]
    glare = is_fus & (yd > -2.80) & (yd < -0.9) & (n[:, 2] > 0.35) & (ax < 0.25)
    rgb[glare] = BLACK

    lines = np.zeros(len(p))
    for yy in (-1.20, -2.75, -6.45, -8.00, -9.50, -11.00, -12.50):
        lines = np.maximum(lines, P.line_mask(yd - yy, 0.009) * (is_fus | is_nac))
    rgb = rgb * (1.0 - 0.12 * lines)[:, None]
    near = np.hypot(ax - 0.30, z - 0.10)
    soot = is_fus * P.smooth(-13.0, -13.4, yd) * P.smooth(0.45, 0.30, near)
    rgb = P.mix(rgb, (0.30, 0.29, 0.28), 0.5 * soot)

    wtop = is_wing & (n[:, 2] > 0.5) & (x < 0)
    P.star_and_bar_colour(rgb, wtop, ax, yd, (2.80, -9.25), 0.24)
    wbot = is_wing & (n[:, 2] < -0.5) & (x > 0)
    P.star_and_bar_colour(rgb, wbot, ax, yd, (2.80, -9.25), 0.24)
    sx = np.sign(n[:, 0])
    side = (is_fus | is_nac) & (np.abs(n[:, 0]) > 0.6) & (yd < -6.6) & (yd > -8.2) & (z > -0.3)
    for s_ in (1.0, -1.0):
        P.star_and_bar_colour(rgb, side & (sx == s_), yd * s_, z, (-7.45 * s_, 0.10), 0.20)

    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    band = fin_faces & (z > 2.25) & (z < 2.45)
    rgb[band] = BLUE
    txt = np.zeros(len(p))
    txt[fin_faces] = P.text_mask("RA", (yd[fin_faces] + 12.60) * sx[fin_faces], z[fin_faces], (0.0, 1.70), 0.30)
    txt[fin_faces] = np.maximum(txt[fin_faces], P.text_mask("AF 68-155", (yd[fin_faces] + 12.70) * sx[fin_faces],
                                                            z[fin_faces], (0.0, 1.30), 0.09))
    rgb = P.mix(rgb, BLUE, 0.92 * txt)

    rough = np.full(len(p), 0.30) + 0.04 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
