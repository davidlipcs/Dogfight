"""F-22A Raptor of the US Air Force (1st Fighter Wing, Langley): the paint.

The two grey radar absorbent scheme: a medium grey with large soft edged lighter grey patches, the sawtooth edges
of the doors and panels, the low visibility markings in dark grey: the star and bar on the wings and the intakes,
the FF tail code and the serial on the fins.
"""

import numpy as np

import f22_shape as S
import jk_paint as P

CODE = "FF"
SERIAL = "AF 04-4080"
MEDIUM = (0.480, 0.495, 0.510)
LIGHT = (0.565, 0.580, 0.595)
MARK = (0.330, 0.340, 0.355)


def painter(pos, nrm, oid, names, mask):
    H, W = mask.shape
    p, n = pos[mask].astype(np.float64), nrm[mask].astype(np.float64)
    name = np.array(names)[oid[mask]]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    yd = y - S.Y0
    starts = lambda *k: np.logical_or.reduce([np.char.startswith(name, s) for s in k])
    is_fin = starts("fin", "rudder")
    is_wing = starts("wing", "ail", "flap", "lef")
    is_fus = name == "fuselage"
    is_nac = starts("nacelle")
    is_door = starts("bay_")

    q = np.stack([ax * 0.8 + y * 0.6, y * 0.8 - ax * 0.6, z], axis=1)
    f = P.fbm(q * np.array([0.8, 1.2, 1.0]), 3.2, 3, seed=41)
    rgb = np.where((f > 0.54)[:, None], np.asarray(LIGHT), np.asarray(MEDIUM))
    rgb = rgb * (0.975 + 0.05 * P.fbm(p, 1.0, 3, seed=3))[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 0.2, 2, seed=9))[:, None]

    # sawtooth panel edges (lighter), also on the bay doors' ends
    lines = np.zeros(len(p))
    for yy in (-2.30, -6.30, -8.37, -10.30, -12.37, -14.50, -16.20):
        zig = 0.14 * np.abs(((ax * 2.6) % 2.0) - 1.0)
        lines = np.maximum(lines, P.line_mask(yd - yy - zig, 0.018) * (is_fus | is_nac | is_door))
    rgb = P.mix(rgb, (0.62, 0.635, 0.65), 0.55 * lines)
    near = np.hypot(ax - 0.66, z - 0.02)
    soot = is_fus * P.smooth(-16.3, -16.7, yd) * P.smooth(0.75, 0.50, near)
    rgb = P.mix(rgb, (0.32, 0.31, 0.30), 0.4 * soot)

    def insignia(sel, u, v, c, r):
        m, st = P.star_and_bar(u[sel], v[sel], c, r, (0.0, 1.0))
        idx = np.where(sel)[0]
        rgb[idx[m & ~st]] = MARK
    wtop = is_wing & (n[:, 2] > 0.5) & (x < 0)
    insignia(wtop, ax, yd, (5.40, -12.40), 0.38)
    wbot = is_wing & (n[:, 2] < -0.5) & (x > 0)
    insignia(wbot, ax, yd, (5.40, -12.40), 0.38)
    sx = np.sign(n[:, 0])
    side = is_nac & (n[:, 0] * np.sign(x) > 0.5)
    for s_ in (1.0, -1.0):
        insignia(side & (sx == s_) & (yd < -6.5) & (yd > -8.6), yd * s_, z, (-7.50 * s_, -0.10), 0.28)

    txt = np.zeros(len(p))
    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.4)
    txt[fin_faces] = P.text_mask(CODE, (yd[fin_faces] + 15.60) * sx[fin_faces], z[fin_faces], (0.0, 2.20), 0.42)
    txt[fin_faces] = np.maximum(txt[fin_faces], P.text_mask(SERIAL, (yd[fin_faces] + 15.75) * sx[fin_faces], z[fin_faces],
                                                            (0.0, 1.70), 0.10))
    rgb = P.mix(rgb, MARK, 0.9 * txt)

    rough = np.full(len(p), 0.40) + 0.05 * (P.fbm(p, 0.6, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_m = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    out_m[mask] = 0.15
    return out_rgb, out_r, out_m
