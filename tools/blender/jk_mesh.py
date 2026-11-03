"""Jet kit: the airframe meshes of a jet from its shape module (<jet>_shape.py), pure numpy.

``airframe(S)`` -> {name: Piece}: the skin pieces of the jet, the moving surfaces with their hinges, the glass, the
intake ducts and the nozzles.  build_<jet>.py turns them into Blender objects (adding the cockpit, the gear, the
lights, the paint); preview.py into a quick .glb for the checks against the drawing.

What a shape module provides: fuselage_ring(y), fuselage_stations(), the canopy (Y_WS0, Y_WS1, Y_CAN1, canopy_half(y),
canopy_stations(), CANOPY_SILL_X / _Z), WING + FLAP / AIL / LEF, STAB + STAB_PIVOT (+ STAB_Z), FIN + FIN_X / FIN_Z /
FIN_CANT + RUDDER, NACELLE lines + Y_FACE_BOT / Y_NAC1 + nacelle_rake(d), NOZZLE, BOOM; optional VENTRAL (fin like
FIN, hanging down) and TIP_POD (wing tip pod).
"""

import math

import numpy as np

import jk

S = None          # the shape module being built (set by airframe())


class Piece:
    """Vertices + polygons + what it is made of (paint, glass, dark, metal, nozzle) and, for a moving surface,
    its hinge (origin, axis)."""

    def __init__(self, verts, faces, mat="paint", hinge=None, uv="auto"):
        self.verts = np.asarray(verts, float).reshape(-1, 3)
        self.faces = [tuple(f) for f in faces]
        self.mat, self.hinge, self.uv = mat, hinge, uv

    def mirrored(self, same_sense=False):
        """The left-hand copy.  Its hinge axis is chosen so that a positive turn moves it the way the game wants
        for both sides: the mirror image of the motion (flaps, ailerons, stabilators, slats: ``same_sense``
        False) or the same motion (rudders: both trailing edges to the right)."""
        faces = [tuple(reversed(f)) for f in self.faces]
        hinge = None
        if self.hinge is not None:
            o, a = self.hinge
            ma = jk.mirror_x(a)
            hinge = (jk.mirror_x(o), ma if same_sense else -ma)
        return Piece(jk.mirror_x(self.verts), faces, self.mat, hinge, self.uv)

    def __add__(self, other):
        n = len(self.verts)
        return Piece(np.vstack([self.verts, other.verts]), self.faces + [tuple(i + n for i in f) for f in other.faces],
                     self.mat, self.hinge, self.uv)


def merge(pieces):
    out = pieces[0]
    for p in pieces[1:]:
        out = out + p
    return out


def fan(ring, tip, reverse=False):
    ring = np.asarray(ring, float)
    n = len(ring)
    faces = [(j, (j + 1) % n, n) for j in range(n)]
    if reverse:
        faces = [tuple(reversed(f)) for f in faces]
    return np.vstack([ring, [tip]]), faces


# ------------------------------------------------------------------ fuselage
def fuselage():
    ys = S.fuselage_stations()
    rings = np.array([S.fuselage_ring(y) for y in ys])
    nr, nc = rings.shape[:2]
    verts = rings.reshape(-1, 3)
    faces = []
    for i in range(nr - 1):
        for j in range(nc):
            a, b = i * nc + j, i * nc + (j + 1) % nc
            c = verts[[a, b, b + nc, a + nc]].mean(axis=0)
            if S.Y_CAN1 + 0.05 < c[1] < S.Y_WS0 - 0.05 and abs(c[0]) < float(S.CANOPY_SILL_X(c[1])) - 0.03 \
                    and c[2] > float(S.CANOPY_SILL_Z(c[1])) - 0.02:
                continue                                    # the cockpit opening under the canopy
            faces.append((a, b, b + nc, a + nc))
    return Piece(verts, faces)


def canopy():
    ys = S.canopy_stations()
    rings = []
    for y in ys:
        h = S.canopy_half(y)
        right = np.stack([h[:, 0], np.full(len(h), y), h[:, 1]], axis=1)
        left = right[::-1][:-1] * np.array([-1.0, 1.0, 1.0])
        rings.append(np.vstack([left, right]))
    rings = np.array(rings)
    nr, nc = rings.shape[:2]
    return Piece(rings.reshape(-1, 3), jk.grid_faces(nr, nc, close=False), mat="glass")


# ------------------------------------------------------------------ lifting surfaces
def _surface_parts(srf, cuts, span_a, span_b, step=0.22):
    """Split a surface into the fixed part and its moving parts.  ``cuts``: [(name, span0, span1, edge, c0, c1)]
    with edge 'te' (trailing edge flap / aileron, chord c metres) or 'le' (leading edge flap)."""
    pieces = {}
    te_cuts = [c for c in cuts if c[3] == "te"]
    le_cuts = [c for c in cuts if c[3] == "le"]

    def chord_m(cut, sp):
        name, s0, s1, edge, c0, c1 = cut
        return c0 + (c1 - c0) * (sp - s0) / max(s1 - s0, 1e-9)

    def s_front(sp):                     # where the fixed part starts (after a leading edge flap)
        for c in le_cuts:
            if c[1] - 1e-6 <= sp <= c[2] + 1e-6:
                return chord_m(c, sp) / float(srf.chord(sp)) + 0.004
        return 0.0

    def s_back(sp):
        for c in te_cuts:
            if c[1] - 1e-6 <= sp <= c[2] + 1e-6:
                return 1.0 - chord_m(c, sp) / float(srf.chord(sp)) - 0.004
        return 1.0

    # the fixed part in spanwise bands between all the cut ends
    ends = sorted(set([span_a, span_b] + [c[1] for c in cuts] + [c[2] for c in cuts]))
    ends = [e for e in ends if span_a - 1e-9 <= e <= span_b + 1e-9]
    fixed = []
    for a, b in zip(ends, ends[1:]):
        mid = 0.5 * (a + b)
        v, f = srf.patch(a, b, lambda sp: s_front(mid) if s_front(mid) > 0 else 0.0,
                         lambda sp: s_back(mid) if s_back(mid) < 1 else 1.0, step=step)
        fixed.append(Piece(v, f))
    tip_ring = srf.tip_cap(span_b)
    fixed.append(Piece(tip_ring, [tuple(range(len(tip_ring)))]))
    pieces["fixed"] = merge(fixed)
    for cut in cuts:
        name, s0, s1, edge, c0, c1 = cut
        if edge == "te":
            v, f = srf.patch(s0, s1, lambda sp, cut=cut: 1.0 - chord_m(cut, sp) / float(srf.chord(sp)), 1.0,
                             nc=8, step=step, cap0=True, cap1=True)
            hs = lambda sp, cut=cut: 1.0 - chord_m(cut, sp) / float(srf.chord(sp))
        else:
            v, f = srf.patch(s0, s1, 0.0, lambda sp, cut=cut: chord_m(cut, sp) / float(srf.chord(sp)),
                             nc=8, step=step, cap0=True, cap1=True)
            hs = lambda sp, cut=cut: chord_m(cut, sp) / float(srf.chord(sp))
        p0 = 0.5 * (srf.point(s0, hs(s0), 1.0) + srf.point(s0, hs(s0), -1.0))
        p1 = 0.5 * (srf.point(s1, hs(s1), 1.0) + srf.point(s1, hs(s1), -1.0))
        axis = p1 - p0 if edge == "te" else p0 - p1         # + = trailing edge down / leading edge down
        pieces[name] = Piece(v, f, hinge=(p0, axis))
    return pieces


def wing():
    cuts = [("flap", S.FLAP[0], S.FLAP[1], "te", S.FLAP[2], S.FLAP[3]),
            ("ail", S.AIL[0], S.AIL[1], "te", S.AIL[2], S.AIL[3]),
            ("lef", S.LEF[0], S.LEF[1], "le", S.LEF[2], S.LEF[3])]
    return _surface_parts(S.WING, cuts, S.WING.span0, S.WING.span1)


def stab():
    """The all-moving tailplane - or the canard (CANARD, CANARD_PIVOT, CANARD_Z), which the game moves as its
    "stab" too: its hinge axis is reversed, so the same command lifts its leading edge where a tailplane would lower
    its own."""
    canard = getattr(S, "CANARD", None) is not None
    srf = S.CANARD if canard else S.STAB
    v, f = srf.patch(srf.span0, srf.span1, 0.0, 1.0, step=0.2)
    ring = srf.tip_cap(srf.span1)
    p = Piece(v, f) + Piece(ring, [tuple(range(len(ring)))])
    if canard:
        pivot = np.array([srf.span0, S.CANARD_PIVOT, S.CANARD_Z])
        axis = np.array([-1.0, 0.0, 0.0])
    else:
        pivot = np.array([srf.span0, S.STAB_PIVOT, getattr(S, "STAB_Z", -0.12)])
        axis = np.array([1.0, 0.0, 0.0])
    return Piece(p.verts, p.faces, hinge=(pivot, axis))


def fin():
    frame = jk.fin_frame(S.FIN_X, S.FIN_Z, S.FIN_CANT, outward=1.0)
    srf = jk.Surface(S.FIN, frame=frame, airfoil=jk.biconvex_t, nc=14)
    parts = _surface_parts(srf, [("rudder", S.RUDDER[0], S.RUDDER[1], "te", S.RUDDER[2], S.RUDDER[3])],
                           srf.span0, srf.span1, step=0.2)
    return parts


def ventral():
    """A ventral fin hanging under the boom (canted outwards by VENTRAL_CANT from straight down)."""
    v = S.VENTRAL
    c, s_ = math.cos(math.radians(v["cant"])), math.sin(math.radians(v["cant"]))

    def frame(span, y, h):
        span, y, h = np.broadcast_arrays(np.asarray(span, float), np.asarray(y, float), np.asarray(h, float))
        return np.stack([v["x"] + span * s_ + h * c, y, v["z"] - span * c + h * s_], axis=-1)
    srf = jk.Surface(v["sections"], frame=frame, airfoil=jk.biconvex_t, nc=10)
    pv, pf = srf.patch(srf.span0, srf.span1, 0.0, 1.0, step=0.2)
    ring = srf.tip_cap(srf.span1)
    return Piece(pv, pf) + Piece(ring, [tuple(range(len(ring)))])


def tip_pod():
    """A wing tip pod / launch rail (TIP_POD: x, z, y0 (nose), y1 (tail), r)."""
    t = S.TIP_POD
    ys = jk.stations([(t["y0"], t["y0"] - 0.4, 0.05), (t["y0"] - 0.4, t["y1"] + 0.3, 0.3), (t["y1"] + 0.3, t["y1"], 0.1)])
    rings = []
    for y in ys:
        k = min(1.0, (t["y0"] - y) / 0.4) ** 0.6 if y > t["y0"] - 0.4 else 1.0
        k2 = min(1.0, (y - t["y1"]) / 0.3) ** 0.5 if y < t["y1"] + 0.3 else 1.0
        r = t["r"] * max(0.05, min(k, k2))
        rings.append(jk.rounded_ring(t["x"], t["z"], r, r, r, 2.0, 2.0, 16, y=y))
    rings = np.array(rings)
    p = Piece(rings.reshape(-1, 3), jk.grid_faces(len(rings), 16))
    return p + Piece(rings[0], [tuple(range(16))[::-1]]) + Piece(rings[-1], [tuple(range(16))])


# ------------------------------------------------------------------ nacelles, intakes, nozzles
def _nacelle_ring(y_bot, d, seg=40, inset=0.0):
    xi, xo, zt, zb, n = (float(c(y_bot)) for c in S.NACELLE)
    cx, hw = 0.5 * (xi + xo), 0.5 * (xo - xi) - inset
    cz, hh = 0.5 * (zt + zb), 0.5 * (zt - zb) - inset
    r = jk.rounded_ring(cx, cz, hw, hh, hh, n, n, seg)
    rake = S.nacelle_rake(d)
    r[:, 1] = y_bot + rake * (r[:, 2] - zb)
    return r


def nacelle():
    ys = S.nacelle_stations() if hasattr(S, "nacelle_stations") else \
        jk.stations([(S.Y_FACE_BOT, 1.0, 0.10), (1.0, -3.9, 0.30), (-3.9, S.Y_NAC1, 0.12)])
    outer = np.array([_nacelle_ring(y, S.Y_FACE_BOT - y) for y in ys])
    nr, nc = outer.shape[:2]
    skin = Piece(outer.reshape(-1, 3), jk.grid_faces(nr, nc))
    # the lip and the dark duct inside: the face ring, a little inset, going back 1.6 m to a dark compressor face
    lip = []
    for k, ins in enumerate((0.0, 0.03, 0.05)):
        lip.append(_nacelle_ring(S.Y_FACE_BOT - 0.0 - 0.02 * k, 0.0, inset=ins))
    lip = np.array(lip)
    lip_piece = Piece(lip.reshape(-1, 3), [tuple(reversed(f)) for f in jk.grid_faces(3, nc)])
    duct = [_nacelle_ring(S.Y_FACE_BOT - d, d, inset=0.05 + 0.02 * d) for d in np.linspace(0.04, getattr(S, "DUCT_DEPTH", 1.6), 8)]
    duct = np.array(duct)
    duct_piece = Piece(duct.reshape(-1, 3), [tuple(reversed(f)) for f in jk.grid_faces(len(duct), nc)], mat="dark")
    back = duct[-1]
    cap = Piece(back, [tuple(range(len(back)))], mat="dark")
    return dict(skin=skin + lip_piece, duct=duct_piece + cap)


def nozzle():
    n = S.NOZZLE
    rings = []
    for y, r in ((n["y0"] + 0.02, n["r0"]), (n["y0"] - 0.10, n["r0"] * 0.99), (n["y1"] + 0.05, n["r1"] * 1.01),
                 (n["y1"], n["r1"])):
        rings.append(jk.rounded_ring(n["x"], n["z"], r, r, r, 2.0, 2.0, 32, y=y))
    outer = np.array(rings)
    inner = np.array([jk.rounded_ring(n["x"], n["z"], n["r1"] - 0.03, n["r1"] - 0.03, n["r1"] - 0.03, 2, 2, 32, y=n["y1"]),
                      jk.rounded_ring(n["x"], n["z"], n["r1"] - 0.08, n["r1"] - 0.08, n["r1"] - 0.08, 2, 2, 32,
                                      y=n["y1"] + 0.6)])
    p = Piece(outer.reshape(-1, 3), jk.grid_faces(4, 32), mat="metal")
    lipf = np.array([outer[-1], inner[0]])
    p = p + Piece(lipf.reshape(-1, 3), jk.grid_faces(2, 32), mat="metal")
    d = Piece(inner.reshape(-1, 3), [tuple(reversed(f)) for f in jk.grid_faces(2, 32)], mat="dark")
    d = d + Piece(inner[-1], [tuple(range(32))], mat="dark")
    return p, d


def boom():
    b = S.BOOM
    ys = jk.stations([(b["y0"], b["y0"] - 0.5, 0.1), (b["y0"] - 0.5, b["y1"] + 0.6, 0.4), (b["y1"] + 0.6, b["y1"], 0.1)])
    rings = []
    for y in ys:
        k = min(1.0, (b["y0"] - y) / 0.5) ** 0.5 if y > b["y0"] - 0.5 else 1.0
        k2 = min(1.0, (y - b["y1"]) / 0.6) ** 0.6 if y < b["y1"] + 0.6 else 1.0
        s = max(0.04, min(k, k2))
        rings.append(jk.rounded_ring(b["x"], b["z"], b["hw"] * s, b["hh_up"] * s, b["hh_lo"] * s, 2.4, 2.4, 20, y=y))
    rings = np.array(rings)
    v, f = rings.reshape(-1, 3), jk.grid_faces(len(rings), 20)
    p = Piece(v, f)
    p = p + Piece(rings[0], [tuple(range(20))[::-1]]) + Piece(rings[-1], [tuple(range(20))])
    return p


# ------------------------------------------------------------------ all of it
def airframe(shape):
    global S
    S = shape
    out = {"fuselage": fuselage(), "canopy": canopy()}
    w = wing()
    out["wing_R"] = w["fixed"]
    out["wing_L"] = w["fixed"].mirrored()
    for k in ("flap", "ail", "lef"):
        out[k + "_R"] = w[k]
        out[k + "_L"] = w[k].mirrored()
    if getattr(S, "STAB", None) is not None or getattr(S, "CANARD", None) is not None:
        st = stab()
        out["stab_R"], out["stab_L"] = st, st.mirrored()
    f = fin()
    if abs(S.FIN_X) < 1e-6:                                # one fin on the centre line
        out["fin"], out["rudder"] = f["fixed"], f["rudder"]
    else:
        out["fin_R"], out["fin_L"] = f["fixed"], f["fixed"].mirrored()
        out["rudder_R"], out["rudder_L"] = f["rudder"], f["rudder"].mirrored(same_sense=True)
    nac = nacelle()
    out["nacelle_R"], out["nacelle_L"] = nac["skin"], nac["skin"].mirrored()
    out["duct_R"], out["duct_L"] = nac["duct"], nac["duct"].mirrored()
    nz, nd = nozzle()
    if abs(S.NOZZLE["x"]) < 1e-6:                          # one engine
        out["nozzle_C"], out["nozzle_in_C"] = nz, nd
    else:
        out["nozzle_R"], out["nozzle_L"] = nz, nz.mirrored()
        out["nozzle_in_R"], out["nozzle_in_L"] = nd, nd.mirrored()
    if getattr(S, "BOOM", None):
        bm = boom()
        out["boom_R"], out["boom_L"] = bm, bm.mirrored()
    if getattr(S, "VENTRAL", None):
        vt = ventral()
        out["ventral_R"], out["ventral_L"] = vt, vt.mirrored()
    if getattr(S, "TIP_POD", None):
        tp = tip_pod()
        out["pod_R"], out["pod_L"] = tp, tp.mirrored()
    return out
