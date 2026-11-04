"""T-45C Goshawk of the US Navy (Training Air Wing 1, Meridian): the paint.

Gloss white with the international orange of the Navy trainers on the nose cone, the outer wings, the stabilator tips
and the upper fin; the black anti-glare panel, the full colour star and bar, NAVY on the rear fuselage, the A tail code
and the modex on the nose.
"""

import numpy as np

import jk_paint as P
import t45_shape as S

WHITE = (0.905, 0.910, 0.915)
BELLY = (0.865, 0.870, 0.875)
ORANGE = (0.92, 0.33, 0.10)
BLACK = (0.06, 0.06, 0.07)


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
    is_stab = starts("stab")

    t = P.smooth(-0.45, 0.15, n[:, 2])
    rgb = np.asarray(BELLY) * (1 - t)[:, None] + np.asarray(WHITE) * t[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 1.0, 2, seed=3))[:, None]
    rgb[is_fus & (yd > -1.30)] = ORANGE
    rgb[is_wing & (ax > 3.25)] = ORANGE
    rgb[is_stab & (ax > 1.45)] = ORANGE
    rgb[is_fin & (z > 2.20)] = ORANGE
    glare = is_fus & (yd > -2.20) & (yd < -1.30) & (n[:, 2] > 0.35) & (ax < 0.28)
    rgb[glare] = BLACK

    lines = np.zeros(len(p))
    for yy in (-1.30, -2.20, -5.75, -7.20, -8.80, -10.20):
        lines = np.maximum(lines, P.line_mask(yd - yy, 0.009) * (is_fus | is_nac))
    rgb = rgb * (1.0 - 0.12 * lines)[:, None]

    wtop = is_wing & (n[:, 2] > 0.5) & (x < 0)
    P.star_and_bar_colour(rgb, wtop, ax, yd, (2.40, -7.25), 0.26)
    wbot = is_wing & (n[:, 2] < -0.5) & (x > 0)
    P.star_and_bar_colour(rgb, wbot, ax, yd, (2.40, -7.25), 0.26)
    sx = np.sign(n[:, 0])
    side = is_fus & (np.abs(n[:, 0]) > 0.6) & (yd < -6.8) & (yd > -8.8)
    for s_ in (1.0, -1.0):
        P.star_and_bar_colour(rgb, side & (sx == s_), yd * s_, z, (-7.70 * s_, 0.50), 0.22)

    txt = np.zeros(len(p))
    rear = is_fus & (np.abs(n[:, 0]) > 0.5) & (yd < -9.0) & (yd > -11.0)
    txt[rear] = P.text_mask("NAVY", (yd[rear] + 9.9) * sx[rear], z[rear], (0.0, 0.55), 0.20)
    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    txt[fin_faces] = np.maximum(txt[fin_faces], P.text_mask("A", (yd[fin_faces] + 11.0) * sx[fin_faces], z[fin_faces],
                                                            (0.0, 1.70), 0.32))
    nose = is_fus & (np.abs(n[:, 0]) > 0.5) & (yd > -2.0) & (yd < -1.3)
    txt[nose] = np.maximum(txt[nose], P.text_mask("221", (yd[nose] + 1.65) * sx[nose], z[nose], (0.0, 0.18), 0.16))
    rgb = P.mix(rgb, BLACK, 0.92 * txt)

    rough = np.full(len(p), 0.30) + 0.04 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
