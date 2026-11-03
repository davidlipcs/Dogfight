"""JAS 39C Gripen of the Hungarian Air Force (59th Tactical Wing, Kecskemét): the paint, from the photograph.

Blue-grey all over (a little lighter underneath, the fin darker), a light grey radome, the low visibility marks: the
Hungarian chevron triangle drawn only in light grey outlines (on the fin and on the wings), "HUNAF" on the fin, the
dark grey side number on the nose.
"""

import numpy as np

import jk_paint as P

SIDE_NUMBER = "41"
UPPER = (0.455, 0.505, 0.580)
LOWER = (0.590, 0.630, 0.690)
FIN = (0.385, 0.425, 0.500)
RADOME = (0.660, 0.680, 0.700)
MARK = (0.800, 0.820, 0.840)
DARK = (0.240, 0.265, 0.300)
Y_RADOME = 4.80


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
    rgb = np.asarray(LOWER) * (1 - t)[:, None] + np.asarray(UPPER) * t[:, None]
    rgb[is_fin] = FIN
    rgb = rgb * (0.975 + 0.05 * P.fbm(p, 1.2, 3, seed=3))[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 0.25, 2, seed=9))[:, None]
    rad = is_fus & (y > Y_RADOME)
    rgb[rad] = RADOME

    lines = np.zeros(len(p))
    for yy in (Y_RADOME, 3.65, 1.45, 0.00, -1.50, -3.00, -4.50, -5.80):
        lines = np.maximum(lines, P.line_mask(y - yy, 0.010) * (is_fus | is_nac))
    for xx in (1.80, 2.50, 3.20):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.009) * is_wing * (np.abs(n[:, 2]) > 0.5))
    rgb = rgb * (1.0 - 0.18 * lines)[:, None]
    near = np.hypot(x, z - 0.38)
    soot = is_fus * P.smooth(-5.6, -6.35, y) * P.smooth(0.70, 0.45, near)
    rgb = P.mix(rgb, (0.25, 0.25, 0.26), 0.5 * soot)

    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.5)
    sx = np.sign(n[:, 0])
    m = P.chevron_outline(y, z, (-4.00, 1.85), (-4.62, 2.22), (-4.62, 1.48), 0.11, 0.028) & fin_faces
    rgb[m] = MARK
    wing_top = is_wing & (np.abs(n[:, 2]) > 0.5)
    m = P.chevron_outline(ax, y, (3.05, -2.95), (2.55, -3.75), (3.55, -3.75), 0.12, 0.03) & wing_top
    rgb[m] = MARK
    hu = np.zeros(len(p))
    hu[fin_faces] = P.text_mask("HUNAF", (y[fin_faces] + 4.30) * sx[fin_faces], z[fin_faces], (0.0, 1.30), 0.13)
    rgb = P.mix(rgb, DARK, 0.9 * hu)
    side = is_fus & (np.abs(n[:, 0]) > 0.5) & (y > 2.5) & (y < 4.6)
    num = np.zeros(len(p))
    num[side] = P.text_mask(SIDE_NUMBER, (y[side] - 3.20) * np.sign(n[side, 0]), z[side], (0.0, 0.22), 0.34)
    rgb = P.mix(rgb, DARK, 0.85 * num)

    rough = np.full(len(p), 0.55) + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
