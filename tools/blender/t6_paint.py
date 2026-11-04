"""T-6A Texan II of the US Air Force (Air Education and Training Command): the paint.

White all over, the black anti-glare panel on the cowling ahead of the windscreen, the dark blue band on the fin with
the RA tail code and the serial, the full colour star and bar on the rear fuselage and the wings, the black walkway on
the wing roots, the propeller spinner in dark grey.
"""

import numpy as np

import jk_paint as P
import t6_shape as S

WHITE = (0.900, 0.905, 0.910)
BELLY = (0.860, 0.865, 0.870)
BLACK = (0.06, 0.06, 0.07)
BLUE = (0.10, 0.18, 0.45)
SPINNER = (0.25, 0.26, 0.28)


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

    t = P.smooth(-0.45, 0.15, n[:, 2])
    rgb = np.asarray(BELLY) * (1 - t)[:, None] + np.asarray(WHITE) * t[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 1.0, 2, seed=3))[:, None]
    rgb[is_fus & (yd > -0.62)] = SPINNER
    glare = is_fus & (yd > -2.55) & (yd < -0.75) & (n[:, 2] > 0.30) & (ax < 0.24)
    rgb[glare] = BLACK
    walk = is_wing & (n[:, 2] > 0.5) & (ax < 1.10) & (ax > 0.45) & (yd < -3.6) & (yd > -4.8)
    rgb[walk] = (0.20, 0.21, 0.22)

    lines = np.zeros(len(p))
    for yy in (-0.62, -0.75, -1.60, -2.55, -6.30, -7.40, -8.60):
        lines = np.maximum(lines, P.line_mask(yd - yy, 0.009) * is_fus)
    rgb = rgb * (1.0 - 0.12 * lines)[:, None]
    # exhaust stain along the cowling sides behind the stacks
    stain = is_fus * (np.abs(n[:, 0]) > 0.4) * P.smooth(-1.25, -1.45, yd) * P.smooth(-3.2, -1.8, yd) \
        * P.smooth(0.16, 0.04, np.abs(z - 0.0)) * (0.6 + 0.4 * P.fbm(p, 0.3, 2, seed=5))
    rgb = P.mix(rgb, (0.45, 0.43, 0.40), 0.45 * stain)

    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    rgb[fin_faces & (z > 1.05) & (z < 1.30)] = BLUE
    sx = np.sign(n[:, 0])
    wtop = is_wing & (n[:, 2] > 0.5) & (x < 0)
    P.star_and_bar_colour(rgb, wtop, ax, yd, (3.80, -4.25), 0.26)
    wbot = is_wing & (n[:, 2] < -0.5) & (x > 0)
    P.star_and_bar_colour(rgb, wbot, ax, yd, (3.80, -4.25), 0.26)
    side = is_fus & (np.abs(n[:, 0]) > 0.6) & (yd < -6.6) & (yd > -8.2)
    for s_ in (1.0, -1.0):
        P.star_and_bar_colour(rgb, side & (sx == s_), yd * s_, z, (-7.40 * s_, 0.05), 0.20)
    txt = np.zeros(len(p))
    txt[fin_faces] = P.text_mask("RA", (yd[fin_faces] + 9.10) * sx[fin_faces], z[fin_faces], (0.0, 0.80), 0.26)
    txt[fin_faces] = np.maximum(txt[fin_faces], P.text_mask("AF 07-3864", (yd[fin_faces] + 9.10) * sx[fin_faces],
                                                            z[fin_faces], (0.0, 0.55), 0.07))
    rgb = P.mix(rgb, BLUE, 0.92 * txt)

    rough = np.full(len(p), 0.30) + 0.04 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
