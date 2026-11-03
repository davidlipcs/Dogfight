"""MiG-29 of the Hungarian Air Force (59. Szentgyörgyi Dezső Repülőbázis, Kecskemét): the paint, from photographs.

Light bluish grey all over (a touch lighter underneath), a light grey radome, light dielectric caps on the fin tips,
the red-white-green chevron triangle (pointing forwards) on the fins and on the wings, "HuAF" on the fins, the
black side number on the intake sides.  Called by build_mig29.py through jk_blend.paint().
"""

import numpy as np

import jk_paint as P

SIDE_NUMBER = "04"
UPPER = (0.600, 0.632, 0.658)
LOWER = (0.660, 0.680, 0.690)
RADOME = (0.665, 0.668, 0.655)
DIELECTRIC = (0.70, 0.71, 0.70)
LINE = 0.80                     # panel lines: the paint times this
RED, WHITE, GREEN = (0.78, 0.10, 0.12), (0.93, 0.93, 0.92), (0.10, 0.48, 0.24)
BLACK = (0.06, 0.06, 0.065)
Y_RADOME = 6.38


def painter(pos, nrm, oid, names, mask):
    H, W = mask.shape
    p, n = pos[mask].astype(np.float64), nrm[mask].astype(np.float64)
    name = np.array(names)[oid[mask]]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)

    is_fin = np.char.startswith(name, "fin") | np.char.startswith(name, "rudder")
    is_wing = np.char.startswith(name, "wing") | np.char.startswith(name, "ail") | np.char.startswith(name, "flap") \
        | np.char.startswith(name, "lef")
    is_fus = name == "fuselage"
    is_nac = np.char.startswith(name, "nacelle")
    is_stab = np.char.startswith(name, "stab")

    # base: upper / lower by the normal, a little weathering
    t = P.smooth(-0.35, 0.25, n[:, 2])
    rgb = np.asarray(LOWER) * (1 - t)[:, None] + np.asarray(UPPER) * t[:, None]
    rgb = rgb * (0.975 + 0.05 * P.fbm(p, 1.6, 3, seed=3))[:, None]
    rgb = rgb * (0.985 + 0.03 * P.fbm(p, 0.25, 2, seed=9))[:, None]

    # radome and its seam
    rad = is_fus & (y > Y_RADOME)
    rgb[rad] = np.asarray(RADOME) * (0.985 + 0.03 * P.fbm(p[rad], 0.8, 2, seed=5))[:, None]
    # dielectric fin caps and the rudder top
    cap = is_fin & (z > 2.44)
    rgb[cap] = DIELECTRIC

    # panel lines (frames round the body, a few lines on the wings, the nacelles' joints)
    lines = np.zeros(len(p))
    for yy in (8.40, Y_RADOME, 5.95, 3.10, 2.20, 1.25, 0.20, -0.90, -2.05, -3.10, -4.05):
        lines = np.maximum(lines, P.line_mask(y - yy, 0.012) * (is_fus | is_nac))
    for xx in (2.55, 3.60, 4.65):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.010) * is_wing * (np.abs(n[:, 2]) > 0.5))
    lines = np.maximum(lines, P.line_mask(z - 0.55, 0.010) * is_fin)
    lines = np.maximum(lines, P.line_mask(ax - 0.62, 0.012) * is_fus * (n[:, 2] > 0.6) * (y < 5.5) * (y > -3.0))
    rgb = rgb * (1.0 - (1.0 - LINE) * lines)[:, None]

    # the auxiliary intake louvers on top of the LERX (open on the ground: dark slots)
    lerx_top = is_fus & (n[:, 2] > 0.5) & (ax > 0.60) & (ax < 0.98)
    slot = np.zeros(len(p), bool)
    for y0 in np.arange(1.90, 2.62, 0.145):
        slot |= (y < y0 + 0.10) & (y > y0)
    rgb[lerx_top & slot] = (0.10, 0.10, 0.11)
    frame = lerx_top & (y > 1.86) & (y < 2.66) & ~slot
    rgb[frame] = rgb[frame] * 0.85

    # soot behind the engines
    near = np.hypot(ax - 0.99, z + 0.74)
    soot = (is_nac | is_fus) * P.smooth(-4.55, -5.05, y) * P.smooth(0.75, 0.45, near) * (0.6 + 0.4 * P.fbm(p, 0.3, 2, seed=11))
    rgb = P.mix(rgb, (0.30, 0.28, 0.26), 0.45 * soot)

    # fin insignia: the chevron triangle pointing forwards, both faces of both fins
    finfaces = is_fin & (np.abs(n[:, 0]) > 0.5)
    u, v = y, z
    tri = P.chevron_triangle(u, v, apex=(-4.30, 1.50), base_a=(-5.02, 1.94), base_b=(-5.02, 1.06), band=0.10)
    tri = tri * finfaces
    for k, col in ((1, RED), (2, WHITE), (3, GREEN)):
        rgb[tri == k] = col
    # "HuAF" under it, reading left to right for whoever looks at that face
    sx = np.sign(n[:, 0])
    hu = np.zeros(len(p))
    sel = finfaces
    hu[sel] = P.text_mask("HuAF", (y[sel] + 4.80) * sx[sel], z[sel], (0.0, 0.70), 0.19)
    rgb = P.mix(rgb, BLACK, 0.92 * hu)

    # wing insignia, top and bottom (pointing forwards)
    wing_faces = is_wing & (np.abs(n[:, 2]) > 0.5)
    tw = P.chevron_triangle(ax, y, apex=(4.55, -1.22), base_a=(4.05, -2.10), base_b=(5.05, -2.10), band=0.12)
    tw = tw * wing_faces
    for k, col in ((1, RED), (2, WHITE), (3, GREEN)):
        rgb[tw == k] = col

    # side number on the intakes (outer face of the nacelles, under the LERX)
    side = is_nac & (n[:, 0] * np.sign(x) > 0.55)
    num = np.zeros(len(p))
    num[side] = P.text_mask(SIDE_NUMBER, (y[side] - 1.15) * np.sign(n[side, 0]), z[side], (0.0, -0.62), 0.42)
    rgb = P.mix(rgb, BLACK, 0.95 * num)
    # small insignia on the nose sides, under the windscreen
    nose_side = is_fus & (np.abs(n[:, 0]) > 0.6) & (y > 5.0) & (y < 6.2)
    tn = P.chevron_triangle(y, z, apex=(5.92, 0.42), base_a=(5.62, 0.58), base_b=(5.62, 0.26), band=0.045) * nose_side
    for k, col in ((1, RED), (2, WHITE), (3, GREEN)):
        rgb[tn == k] = col

    rough = np.full(len(p), 0.58)
    rough[rad] = 0.45
    rough = rough + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    return out_rgb, out_r, np.zeros((H, W), np.float32)
