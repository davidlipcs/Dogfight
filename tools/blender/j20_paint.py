"""Chengdu J-20 of the PLA Air Force: the paint, from the photograph.

Mid grey all over with a faint sheen (the radar absorbent coating), slightly darker radome, the low visibility
insignia - the star with the "8-1" and the bars - in a darker grey on the fins and the wings, the serial in dark grey on
the nose sides, the sawtooth edges of the panels.
"""

import numpy as np

import jk_paint as P

SERIAL = "78271"
GREY = (0.545, 0.565, 0.590)
BELLY = (0.580, 0.595, 0.615)
RADOME = (0.470, 0.485, 0.505)
MARK = (0.390, 0.400, 0.420)
Y_RADOME = 8.80


def star(u, v, c, r, inner=0.40, rot=0.0):
    pts = []
    for k in range(10):
        a = np.pi / 2 + rot + k * np.pi / 5
        rr = r if k % 2 == 0 else r * inner
        pts.append((c[0] + rr * np.cos(a), c[1] + rr * np.sin(a)))
    return P.in_polygon(u, v, pts)


def insignia(u, v, c, r, up):
    """The PLAAF star with the bars either side; ``up`` is the (du, dv) direction the star points to."""
    rot = np.arctan2(up[1], up[0]) - np.pi / 2
    m = star(u, v, c, r, rot=rot)
    # the bars: across the star, 2.2 r long each side, 0.32 r wide, perpendicular to ``up``
    du, dv = -up[1], up[0]
    a = (u - c[0]) * du + (v - c[1]) * dv
    b = (u - c[0]) * up[0] + (v - c[1]) * up[1]
    bars = (np.abs(a) > 0.75 * r) & (np.abs(a) < 2.3 * r) & (np.abs(b + 0.10 * r) < 0.16 * r)
    return m | bars


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
    is_nac = starts("nacelle", "boom")

    t = P.smooth(-0.45, 0.15, n[:, 2])
    rgb = np.asarray(BELLY) * (1 - t)[:, None] + np.asarray(GREY) * t[:, None]
    rgb = rgb * (0.97 + 0.06 * P.fbm(p, 1.5, 3, seed=3))[:, None]
    rad = is_fus & (y > Y_RADOME)
    rgb[rad] = RADOME

    # the sawtooth panel edges (stealth): zig-zag lines across the body
    lines = np.zeros(len(p))
    for yy in (Y_RADOME, 6.70, 4.00, 1.50, -1.50, -4.00, -6.50, -8.80):
        zig = 0.10 * np.abs(((ax * 2.5) % 2.0) - 1.0)
        lines = np.maximum(lines, P.line_mask(y - yy - zig, 0.012) * (is_fus | is_nac))
    for xx in (3.40, 4.50, 5.60):
        lines = np.maximum(lines, P.line_mask(ax - xx, 0.009) * is_wing * (np.abs(n[:, 2]) > 0.5))
    rgb = rgb * (1.0 - 0.15 * lines)[:, None]
    near = np.hypot(ax - 0.92, z + 0.20)
    soot = (is_fus | is_nac) * P.smooth(-9.1, -9.6, y) * P.smooth(0.75, 0.50, near)
    rgb = P.mix(rgb, (0.30, 0.29, 0.28), 0.45 * soot)

    wing_top = is_wing & (np.abs(n[:, 2]) > 0.5)
    m = np.zeros(len(p), bool)
    m[wing_top] = insignia(y[wing_top], ax[wing_top], (-5.0, 4.95), 0.40, (0.0, 1.0))
    rgb[m] = MARK
    fin_faces = is_fin & (np.abs(n[:, 0]) > 0.3)
    sx = np.sign(n[:, 0])
    m = np.zeros(len(p), bool)
    m[fin_faces] = star((y[fin_faces] + 9.75) * sx[fin_faces], z[fin_faces], (0.0, 1.45), 0.32)
    rgb[m] = MARK
    side = is_fus & (np.abs(n[:, 0]) > 0.5) & (y > 6.0) & (y < 8.5)
    num = np.zeros(len(p))
    num[side] = P.text_mask(SERIAL, (y[side] - 7.20) * np.sign(n[side, 0]), z[side], (0.0, -0.30), 0.22)
    rgb = P.mix(rgb, (0.25, 0.26, 0.28), 0.9 * num)

    rough = np.full(len(p), 0.42) + 0.06 * (P.fbm(p, 0.7, 2, seed=21) - 0.5)
    out_rgb = np.zeros((H, W, 3), np.float32)
    out_r = np.zeros((H, W), np.float32)
    out_m = np.full((H, W), 0.0, np.float32)
    out_rgb[mask] = rgb
    out_r[mask] = rough
    out_m[mask] = 0.15
    return out_rgb, out_r, out_m
