"""Jet kit, painting helpers (pure numpy + PIL): every function works on the arrays of texel positions / normals
from jk_blend.bake_positions, so the paint is drawn on the aircraft itself.

Colours are sRGB 0..1.
"""

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]


def smooth(a, b, t):
    t = np.clip((np.asarray(t, float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFF).astype(np.float32) / 65535.0


def value_noise(p, scale, seed=0):
    """Smooth 3D value noise in 0..1 at points p (..., 3), features ``scale`` metres apart."""
    q = np.asarray(p, np.float64) / scale
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3.0 - 2.0 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                out = out + w * _hash(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
    return out


def fbm(p, scale, octaves=4, seed=0):
    total, amp, norm = 0.0, 1.0, 0.0
    for k in range(octaves):
        total = total + amp * value_noise(p, scale / (2 ** k), seed + 17 * k)
        norm += amp
        amp *= 0.5
    return total / norm


def line_mask(d, width, soft=0.004):
    """1 on a line of ``width`` metres round d = 0 (d: signed distance)."""
    return 1.0 - smooth(0.5 * width, 0.5 * width + soft, np.abs(d))


# ------------------------------------------------------------------ flat shapes (in 2D decal coordinates)
def in_polygon(u, v, poly):
    """Even-odd point in polygon test, vectorised."""
    inside = np.zeros(np.shape(u), bool)
    n = len(poly)
    for k in range(n):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % n]
        cond = ((y1 > v) != (y2 > v)) & (u < (x2 - x1) * (v - y1) / ((y2 - y1) + 1e-12) + x1)
        inside ^= cond
    return inside


def chevron_triangle(u, v, apex, base_a, base_b, band):
    """The Hungarian triangle: nested chevrons from the apex, each ``band`` wide along the two sides.
    -> 0 outside, 1 outer band, 2 middle band, 3 core."""
    A, B, C = (np.asarray(p, float) for p in (apex, base_a, base_b))

    def side_dist(P, Q):                      # distance from the line P-Q, positive towards the triangle
        d = Q - P
        nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
        cen = (A + B + C) / 3.0
        if np.dot(cen - P, nrm) < 0:
            nrm = -nrm
        return (u - P[0]) * nrm[0] + (v - P[1]) * nrm[1]
    d1, d2, d3 = side_dist(A, B), side_dist(A, C), side_dist(B, C)
    inside = (d1 >= 0) & (d2 >= 0) & (d3 >= 0)
    m = np.minimum(d1, d2)
    out = np.zeros(np.shape(u), np.int8)
    out[inside] = 1
    out[inside & (m >= band)] = 2
    out[inside & (m >= 2 * band)] = 3
    return out


def text_mask(text, u, v, centre, height, font_px=200, spacing=0.0, stretch=1.0):
    """Mask of ``text`` drawn ``height`` metres tall (cap height) centred on ``centre`` in (u, v) (u: reading
    direction, v: up)."""
    font = None
    for f in FONTS:
        if os.path.exists(f):
            font = ImageFont.truetype(f, font_px)
            break
    if font is None:
        font = ImageFont.load_default()
    box = font.getbbox(text)
    w, h = box[2] - box[0] + 20, box[3] - box[1] + 20
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).text((10 - box[0], 10 - box[1]), text, fill=255, font=font)
    a = np.asarray(img, np.float32) / 255.0
    ppm = (box[3] - box[1]) / height                     # pixels per metre
    uu = (np.asarray(u) - centre[0]) * ppm / stretch + w / 2.0
    vv = h / 2.0 - (np.asarray(v) - centre[1]) * ppm
    ok = (uu >= 0) & (uu < w - 1) & (vv >= 0) & (vv < h - 1)
    out = np.zeros(np.shape(u), np.float32)
    iu, iv = uu[ok].astype(int), vv[ok].astype(int)
    out[ok] = a[iv, iu]
    return out


def mix(rgb, colour, alpha):
    a = np.asarray(alpha, np.float32)[..., None]
    return rgb * (1.0 - a) + np.asarray(colour, np.float32) * a


def chevron_outline(u, v, apex, base_a, base_b, band, line):
    """The low visibility form of chevron_triangle: only the outlines (the outer border, the base and the borders
    between the chevrons), ``line`` metres wide."""
    A, B, C = (np.asarray(p, float) for p in (apex, base_a, base_b))
    cen = (A + B + C) / 3.0

    def side_dist(P_, Q):
        d = Q - P_
        nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
        if np.dot(cen - P_, nrm) < 0:
            nrm = -nrm
        return (np.asarray(u) - P_[0]) * nrm[0] + (np.asarray(v) - P_[1]) * nrm[1]
    d1, d2, d3 = side_dist(A, B), side_dist(A, C), side_dist(B, C)
    inside = (d1 >= 0) & (d2 >= 0) & (d3 >= 0)
    m = np.minimum(d1, d2)
    edge = (m < line) | (d3 < line) | (np.abs(m - band) < 0.5 * line) | (np.abs(m - 2 * band) < 0.5 * line)
    return inside & edge


def star5(u, v, c, r, inner=0.38, rot=0.0):
    pts = []
    for k in range(10):
        a = np.pi / 2 + rot + k * np.pi / 5
        rr = r if k % 2 == 0 else r * inner
        pts.append((c[0] + rr * np.cos(a), c[1] + rr * np.sin(a)))
    return in_polygon(u, v, pts)


def star_and_bar(u, v, c, r, up=(0.0, 1.0)):
    """The US national insignia: a disc of radius r with the bars either side; -> (disc and bars, the star).  ``up``:
    the (du, dv) direction the star points to (the bars run across it)."""
    up = np.asarray(up, float) / np.hypot(*up)
    across = np.array([up[1], -up[0]])
    du, dv = np.asarray(u) - c[0], np.asarray(v) - c[1]
    a = du * across[0] + dv * across[1]
    b = du * up[0] + dv * up[1]
    disc = np.hypot(du, dv) < r
    bars = (np.abs(a) < 2.0 * r) & (b < -0.06 * r) & (b > -0.06 * r - 0.62 * r)
    rot = np.arctan2(up[1], up[0]) - np.pi / 2
    st = star5(u, v, c, 0.95 * r, rot=rot)
    return disc | bars, st


def star_and_bar_colour(rgb, sel, u, v, c, r, up=(0.0, 1.0)):
    """The full colour US insignia (blue disc and bar outline, white star and bars, the red stripe) on rgb[sel]."""
    idx = np.where(sel)[0]
    uu, vv = np.asarray(u)[sel], np.asarray(v)[sel]
    big, _ = star_and_bar(uu, vv, c, r * 1.12, up)          # the blue outline
    m, st = star_and_bar(uu, vv, c, r, up)
    up = np.asarray(up, float) / np.hypot(*up)
    across = np.array([up[1], -up[0]])
    du, dv = uu - c[0], vv - c[1]
    a = du * across[0] + dv * across[1]
    b = du * up[0] + dv * up[1]
    stripe = (np.abs(a) > 1.05 * r) & (np.abs(a) < 1.95 * r) & (b < -0.25 * r) & (b > -0.45 * r)
    disc = np.hypot(du, dv) < r
    rgb[idx[big]] = (0.08, 0.15, 0.40)
    rgb[idx[m & ~disc]] = (0.94, 0.94, 0.93)
    rgb[idx[disc]] = (0.08, 0.15, 0.40)
    rgb[idx[st]] = (0.94, 0.94, 0.93)
    rgb[idx[stripe]] = (0.75, 0.10, 0.12)
