"""F-35A of the US Air Force: the paint, from the photograph.

The "Have Glass" radar absorbent finish: a mid grey with a faint metallic sheen, the edges (leading edges, the
intake lips, the canopy frame, the panel edges) a little lighter and smoother; the low visibility star and bar in
dark grey on the wings and the intakes, the tail code and serial in dark grey on the fins.
"""

import numpy as np

import f35_shape as S
import jk_paint as P

TAIL_CODE = "HL"
SERIAL = "AF 12-5050"
GREY = (0.500, 0.505, 0.505)
BELLY = (0.535, 0.540, 0.540)
EDGE = (0.600, 0.605, 0.600)
MARK = (0.330, 0.335, 0.340)
Y_RADOME = 6.40


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
    is_stab = starts("stab")

    t = P.smooth(-0.45, 0.15, n[:, 2])
    rgb = np.asarray(BELLY) * (1 - t)[:, None] + np.asarray(GREY) * t[:, None]
    rgb = rgb * (0.965 + 0.07 * P.fbm(p, 1.0, 3, seed=3))[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 0.18, 2, seed=9))[:, None]

    # the lighter edge strips: leading edges of the wing, the stabilators, the fins, the intake lips
    le_dist = np.full(len(p), 9.0)
    le_dist[is_wing | starts("lef")] = np.abs(y[is_wing | starts("lef")] - S.wing_le(ax[is_wing | starts("lef")]))
    rgb[(le_dist < 0.10)] = EDGE
    lip = is_nac & (y > S.Y_FACE_BOT - 0.12)
    rgb[lip] = EDGE

    # the sawtooth edges of the doors and panels (lighter lines)
    lines = np.zeros(len(p))
    for yy in (Y_RADOME, 4.20, 1.60, -0.80, -3.20, -5.40):
        zig = 0.12 * np.abs(((ax * 3.0) % 2.0) - 1.0)
        lines = np.maximum(lines, P.line_mask(y - yy - zig, 0.016) * (is_fus | is_nac))
    rgb = P.mix(rgb, EDGE, 0.55 * lines)
    near = np.hypot(x, z - 0.12)
    soot = is_fus * P.smooth(-5.9, -6.4, y) * P.smooth(0.85, 0.60, near)
    rgb = P.mix(rgb, (0.35, 0.34, 0.33), 0.4 * soot)

    # star and bar: right wing top, left wing bottom, both intakes
    def insignia(sel, u, v, c, r, up):
        m, st = P.star_and_bar(u[sel], v[sel], c, r, up)
        idx = np.where(sel)[0]
        rgb[idx[m & ~st]] = MARK
    wtop = is_wing & (n[:, 2] > 0.5) & (x > 0)
    insignia(wtop, ax, y, (4.10, -2.65), 0.32, (0.0, 1.0))
    wbot = is_wing & (n[:, 2] < -0.5) & (x < 0)
    insignia(wbot, ax, y, (4.10, -2.65), 0.32, (0.0, 1.0))
    side = is_nac & (n[:, 0] * np.sign(x) > 0.5)
    sx = np.sign(n[:, 0])
    for s_ in (1.0, -1.0):
        sel = side & (sx == s_)
        insignia(sel, y * s_, z, (1.40 * s_, 0.05), 0.24, (0.0, 1.0))

    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.4)
    txt = np.zeros(len(p))
    txt[fin_faces] = P.text_mask(TAIL_CODE, (y[fin_faces] + 6.10) * sx[fin_faces], z[fin_faces], (0.0, 1.95), 0.32)
    txt[fin_faces] = np.maximum(txt[fin_faces], P.text_mask(SERIAL, (y[fin_faces] + 6.25) * sx[fin_faces], z[fin_faces],
                                                            (0.0, 1.45), 0.09))
    rgb = P.mix(rgb, MARK, 0.9 * txt)

    rough = np.full(len(p), 0.38) + 0.05 * (P.fbm(p, 0.6, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_m = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    out_m[mask] = 0.25
    return out_rgb, out_r, out_m
