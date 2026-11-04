"""F/A-18E Super Hornet of the US Navy: the paint, from the photograph.

The tactical two-tone grey: dark ghost grey on top, light ghost grey underneath (soft boundary on the sides), a light
grey radome; the low visibility markings in a darker grey: the star and bar on the fuselage sides behind the intakes
and on the wings (left on top, right underneath), NAVY on the engine bays, the modex 200 on the nose and on the flap,
the air wing code on the fins.
"""

import numpy as np

import fa18_shape as S
import jk_paint as P

MODEX = "200"
CODE = "NH"
UPPER = (0.505, 0.540, 0.580)
LOWER = (0.625, 0.650, 0.680)
RADOME = (0.640, 0.650, 0.660)
MARK = (0.330, 0.345, 0.370)


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

    t = P.smooth(-0.40, 0.25, n[:, 2])
    rgb = np.asarray(LOWER) * (1 - t)[:, None] + np.asarray(UPPER) * t[:, None]
    rgb[is_fin] = UPPER
    rgb = rgb * (0.965 + 0.07 * P.fbm(p, 1.3, 3, seed=3))[:, None]          # the weathered navy finish
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 0.22, 2, seed=9))[:, None]
    rad = is_fus & (yd > -2.30)
    rgb[rad] = RADOME

    lines = np.zeros(len(p))
    for yy in (-2.30, -3.40, -7.10, -8.60, -10.40, -12.20, -14.00, -15.80):
        lines = np.maximum(lines, P.line_mask(yd - yy, 0.011) * (is_fus | is_nac))
    for xx in (3.10, 4.30, 5.50):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.009) * is_wing * (np.abs(n[:, 2]) > 0.5))
    rgb = rgb * (1.0 - 0.18 * lines)[:, None]
    near = np.hypot(ax - 0.58, z - 0.04)
    soot = is_fus * P.smooth(-16.2, -16.8, yd) * P.smooth(0.70, 0.46, near)
    rgb = P.mix(rgb, (0.30, 0.29, 0.28), 0.5 * soot)

    def insignia(sel, u, v, c, r):
        m, st = P.star_and_bar(u[sel], v[sel], c, r, (0.0, 1.0))
        idx = np.where(sel)[0]
        rgb[idx[m & ~st]] = MARK
    wtop = is_wing & (n[:, 2] > 0.5) & (x < 0)
    insignia(wtop, ax, yd, (5.20, -12.05), 0.36)
    wbot = is_wing & (n[:, 2] < -0.5) & (x > 0)
    insignia(wbot, ax, yd, (5.20, -12.05), 0.36)
    sx = np.sign(n[:, 0])
    side = (is_fus | is_nac) & (np.abs(n[:, 0]) > 0.6)
    for s_ in (1.0, -1.0):
        sel = side & (sx == s_) & (yd < -6.8) & (yd > -9.0)
        insignia(sel, yd * s_, z, (-7.90 * s_, 0.10), 0.30)

    txt = np.zeros(len(p))
    nose = is_fus & (np.abs(n[:, 0]) > 0.5) & (yd > -3.4) & (yd < -1.2)
    txt[nose] = P.text_mask(MODEX, (yd[nose] + 2.40) * sx[nose], z[nose], (0.0, 0.22), 0.30)
    eng = is_fus & (np.abs(n[:, 0]) > 0.5) & (yd < -11.5) & (yd > -14.5)
    txt[eng] = np.maximum(txt[eng], P.text_mask("NAVY", (yd[eng] + 13.0) * sx[eng], z[eng], (0.0, 0.20), 0.26))
    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.4)
    txt[fin_faces] = np.maximum(txt[fin_faces], P.text_mask(CODE, (yd[fin_faces] + 16.1) * sx[fin_faces], z[fin_faces],
                                                            (0.0, 2.30), 0.36))
    rgb = P.mix(rgb, MARK, 0.9 * txt)

    rough = np.full(len(p), 0.58) + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
