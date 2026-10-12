"""Paints the F-16 cockpit texture atlas (instrument panel, MFDs, DED, consoles, seat details).

Writes dogfight/render/cockpit.png; the UV layout is ``ATLAS`` in dogfight/render/cockpit.py.
Needs Pillow (only for this tool - the game just loads the PNG).
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dogfight.render.cockpit import ATLAS, SIZE  # noqa: E402

FONT_DIRS = ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/TTF/", "C:/Windows/Fonts/")
PANEL = (44, 46, 49)
PANEL_EDGE = (66, 69, 72)
LABEL = (225, 228, 222)
GREEN = (90, 255, 120)
AMBER = (255, 190, 60)
CYAN = (110, 220, 255)


def font(size, mono=False, bold=False):
    names = ["DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"] if mono else \
        ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "arialbd.ttf" if bold else "arial.ttf"]
    for d in FONT_DIRS:
        for n in names:
            if os.path.exists(d + n):
                return ImageFont.truetype(d + n, size)
    return ImageFont.load_default()


def rect(region):
    x0, y0, x1, y1 = region
    return x0, y0, x1, y1


def text(d, xy, s, size, color=LABEL, anchor="mm", mono=False, bold=False):
    d.text(xy, s, fill=color, font=font(size, mono, bold), anchor=anchor)


def knob(d, x, y, r, rnd):
    d.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2), fill=(20, 20, 22))
    d.ellipse((x - r, y - r, x + r, y + r), fill=(32, 33, 35), outline=(80, 82, 84))
    a = rnd.uniform(0, 2 * math.pi)
    d.line((x, y, x + math.cos(a) * r * 0.85, y + math.sin(a) * r * 0.85), fill=(235, 235, 230), width=2)


def toggle(d, x, y, rnd):
    d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(150, 152, 150), outline=(30, 30, 30))
    dy = rnd.choice((-1, 1)) * 9
    d.line((x, y, x, y + dy), fill=(215, 215, 210), width=4)
    d.ellipse((x - 3, y + dy - 3, x + 3, y + dy + 3), fill=(230, 230, 225))


def sub_panel(d, box, title, rnd, knobs=2, toggles=3):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=PANEL, outline=(18, 18, 20), width=2)
    d.line((x0 + 2, y0 + 2, x1 - 2, y0 + 2), fill=PANEL_EDGE, width=1)
    for sx, sy in ((x0 + 6, y0 + 6), (x1 - 6, y0 + 6), (x0 + 6, y1 - 6), (x1 - 6, y1 - 6)):
        d.ellipse((sx - 2, sy - 2, sx + 2, sy + 2), fill=(90, 92, 94))      # dzus fasteners
    w, h = x1 - x0, y1 - y0
    if title:
        text(d, ((x0 + x1) / 2, y0 + 13), title, 11, LABEL, bold=True)
    n = knobs + toggles
    for i in range(n):
        cx = x0 + w * (i + 0.5) / n
        cy = y0 + h * (0.58 if h > 60 else 0.62)
        if i < knobs:
            knob(d, cx, cy, min(13, h * 0.2), rnd)
            text(d, (cx, y1 - 9), rnd.choice(("VOL", "MODE", "CHAN", "BRT", "TEST", "SEL")), 8)
        else:
            toggle(d, cx, cy, rnd)
            text(d, (cx, cy - 20), rnd.choice(("ON", "NORM", "ARM", "AUTO", "OPEN")), 8)


def bezel(d, outer, screen):
    x0, y0, x1, y1 = outer
    d.rounded_rectangle(outer, 14, fill=(30, 31, 33), outline=(12, 12, 13), width=3)
    sx0, sy0, sx1, sy1 = screen
    # option select buttons, five per side
    for k in range(5):
        t = (k + 0.5) / 5
        bx = sx0 + (sx1 - sx0) * t
        by = sy0 + (sy1 - sy0) * t
        for cx, cy in ((bx, y0 + 18), (bx, y1 - 18), (x0 + 18, by), (x1 - 18, by)):
            d.rounded_rectangle((cx - 13, cy - 10, cx + 13, cy + 10), 3, fill=(64, 66, 68), outline=(12, 12, 12))
    for cx, cy in ((x0 + 22, y0 + 22), (x1 - 22, y0 + 22), (x0 + 22, y1 - 22), (x1 - 22, y1 - 22)):
        d.rectangle((cx - 9, cy - 4, cx + 9, cy + 4), fill=(55, 57, 59))      # rocker switches
    d.rectangle((sx0 - 4, sy0 - 4, sx1 + 4, sy1 + 4), fill=(6, 6, 7))


def osb_labels(d, screen, top, bottom, left=(), right=()):
    x0, y0, x1, y1 = screen
    f = 13
    for k, s in enumerate(top):
        text(d, (x0 + (x1 - x0) * (k + 0.5) / 5, y0 + 12), s, f, GREEN, mono=True)
    for k, s in enumerate(bottom):
        text(d, (x0 + (x1 - x0) * (k + 0.5) / 5, y1 - 12), s, f, GREEN, mono=True)
    for k, s in enumerate(left):
        text(d, (x0 + 8, y0 + (y1 - y0) * (k + 0.5) / 5), s, f, GREEN, anchor="lm", mono=True)
    for k, s in enumerate(right):
        text(d, (x1 - 8, y0 + (y1 - y0) * (k + 0.5) / 5), s, f, GREEN, anchor="rm", mono=True)


def radar_page(d, screen, rnd):
    x0, y0, x1, y1 = screen
    d.rectangle(screen, fill=(4, 8, 6))
    ix0, iy0, ix1, iy1 = x0 + 34, y0 + 30, x1 - 34, y1 - 30
    for k in range(5):                            # azimuth lines
        x = ix0 + (ix1 - ix0) * k / 4
        for y in range(int(iy0), int(iy1), 10):
            d.line((x, y, x, y + 4), fill=(60, 130, 70))
    for k in range(1, 4):                         # range ticks
        y = iy0 + (iy1 - iy0) * k / 4
        d.line((ix0 - 6, y, ix0 + 6, y), fill=(90, 190, 100), width=2)
    d.line((ix0 + 20, (iy0 + iy1) / 2 + 6, ix1 - 20, (iy0 + iy1) / 2 - 6), fill=(90, 190, 100), width=2)  # horizon
    text(d, (ix0 - 14, iy0 + 6), "40", 12, GREEN, mono=True)
    cx, cy = ix0 + (ix1 - ix0) * 0.58, iy0 + (iy1 - iy0) * 0.42
    d.line((cx - 6, cy - 9, cx - 6, cy + 9), fill=(230, 255, 230), width=2)       # acquisition cursor
    d.line((cx + 6, cy - 9, cx + 6, cy + 9), fill=(230, 255, 230), width=2)
    for tx, ty in ((0.30, 0.35), (0.62, 0.55), (0.71, 0.30)):                     # search targets
        px, py = ix0 + (ix1 - ix0) * tx, iy0 + (iy1 - iy0) * ty
        d.rectangle((px - 5, py - 3, px + 5, py + 3), fill=(220, 255, 225))
    d.polygon([(ix0 + (ix1 - ix0) * 0.5, iy1 + 2), (ix0 + (ix1 - ix0) * 0.5 - 6, iy1 + 12),
               (ix0 + (ix1 - ix0) * 0.5 + 6, iy1 + 12)], outline=(90, 190, 100))
    osb_labels(d, screen, ("CRM", "RWS", "NORM", "OVRD", "CNTL"), ("SWAP", "HSD", "SMS", "FCR", "DCLT"),
               ("A6", "", "", "", ""), ("", "", "", "", ""))


def sms_page(d, screen):
    x0, y0, x1, y1 = screen
    d.rectangle(screen, fill=(4, 6, 8))
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2 + 10
    # aircraft planform
    pts = [(cx, cy - 70), (cx + 10, cy - 40), (cx + 12, cy - 6), (cx + 80, cy + 26), (cx + 80, cy + 36),
           (cx + 14, cy + 30), (cx + 12, cy + 52), (cx + 34, cy + 66), (cx + 34, cy + 74), (cx, cy + 70)]
    pts = pts + [(2 * cx - x, y) for x, y in reversed(pts)]
    d.line(pts + [pts[0]], fill=(110, 200, 240), width=2)
    for k, (sx, lab) in enumerate(((-84, "1 9M"), (-58, "2 9M"), (-34, "3 120"), (34, "7 120"), (58, "8 9M"),
                                   (84, "9 9M"))):
        y = cy + 20 + (2 if abs(sx) > 70 else 8)
        text(d, (cx + sx, y + 26), lab.split()[0], 12, CYAN, mono=True)
        d.rectangle((cx + sx - 3, y - 4, cx + sx + 3, y + 10), fill=(220, 240, 255))
    text(d, (cx, y0 + 42), "AIM-9M  4    AIM-120A  2", 13, GREEN, mono=True)
    text(d, (cx, y1 - 40), "GUN 511 PGU-28", 13, GREEN, mono=True)
    osb_labels(d, screen, ("AAM", "INV", "", "", "SLAV"), ("SWAP", "HSD", "SMS", "FCR", "DCLT"),
               ("", "", "", "", ""), ("", "", "SCAN", "", ""))


def gauge(d, cx, cy, r, kind, rnd):
    d.ellipse((cx - r - 7, cy - r - 7, cx + r + 7, cy + r + 7), fill=(22, 22, 24), outline=(70, 72, 74), width=2)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(10, 10, 11))
    if kind == "adi":
        d.pieslice((cx - r, cy - r, cx + r, cy + r), 180, 360, fill=(150, 152, 150))   # sky
        d.line((cx - r, cy, cx + r, cy), fill=(250, 250, 245), width=3)
        for k in (-2, -1, 1, 2):
            w = r * (0.35 if k % 2 else 0.55)
            d.line((cx - w, cy - k * r * 0.22, cx + w, cy - k * r * 0.22), fill=(240, 240, 235) if k > 0 else
                   (210, 210, 205), width=2)
        d.line((cx - r * 0.55, cy + 2, cx - r * 0.18, cy + 2), fill=AMBER, width=4)
        d.line((cx + r * 0.18, cy + 2, cx + r * 0.55, cy + 2), fill=AMBER, width=4)
        d.ellipse((cx - 4, cy - 2, cx + 4, cy + 6), fill=AMBER)
        return
    n = 36 if kind == "hsi" else 30
    for k in range(n):
        a = 2 * math.pi * k / n - math.pi / 2
        inner = r * (0.80 if k % 3 == 0 else 0.88)
        d.line((cx + math.cos(a) * inner, cy + math.sin(a) * inner, cx + math.cos(a) * r * 0.97,
                cy + math.sin(a) * r * 0.97), fill=(230, 230, 225), width=2 if k % 3 == 0 else 1)
    if kind == "hsi":
        for k, s in enumerate(("N", "3", "6", "E", "12", "15", "S", "21", "24", "W", "30", "33")):
            a = 2 * math.pi * k / 12 - math.pi / 2
            text(d, (cx + math.cos(a) * r * 0.64, cy + math.sin(a) * r * 0.64), s, 11, LABEL, bold=True)
        d.polygon([(cx, cy - r * 0.5), (cx - 7, cy + r * 0.3), (cx + 7, cy + r * 0.3)], outline=(250, 200, 60))
        d.line((cx, cy - r * 0.55, cx, cy + r * 0.55), fill=(250, 200, 60), width=2)
    elif kind == "rwr":
        d.ellipse((cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5), outline=(60, 140, 70))
        d.line((cx - 8, cy, cx + 8, cy), fill=(90, 220, 110), width=2)
        d.line((cx, cy - 8, cx, cy + 6), fill=(90, 220, 110), width=2)
        text(d, (cx + r * 0.45, cy - r * 0.42), "29", 13, (90, 255, 120), bold=True)
    else:
        for k in range(0, 10, 2):
            a = 2 * math.pi * k / 10 - math.pi / 2
            text(d, (cx + math.cos(a) * r * 0.62, cy + math.sin(a) * r * 0.62), str(k), 11, LABEL, bold=True)
        a = rnd.uniform(0, 2 * math.pi)
        d.line((cx, cy, cx + math.cos(a) * r * 0.8, cy + math.sin(a) * r * 0.8), fill=(245, 245, 240), width=3)
        d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(60, 60, 60))
        text(d, (cx, cy + r * 0.32), {"alt": "ALT", "ias": "KNOTS", "fuel": "FUEL"}.get(kind, ""), 9, LABEL)


def ded(d, box):
    x0, y0, x1, y1 = box
    d.rectangle((x0 - 6, y0 - 6, x1 + 6, y1 + 6), fill=(26, 27, 29), outline=(10, 10, 10), width=2)
    d.rectangle(box, fill=(6, 10, 4))
    lines = ("UHF 292.30   STPT  \u25b2 1", "             10:24:47", "VHF  127.00  M1 3  C 4.5",
             "TCN  75X     ALOW 1500")
    for k, s in enumerate(lines):
        text(d, (x0 + 8, y0 + 12 + k * 19), s, 14, (150, 255, 110), anchor="lm", mono=True)


def icp(d, box):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, 8, fill=(36, 37, 40), outline=(10, 10, 10), width=2)
    keys = (("1\nT-ILS", "2\nALOW", "3", "RCL"), ("4\nSTPT", "5\nCRUS", "6\nTIME", "ENTR"),
            ("7\nMARK", "8\nFIX", "9\nA-CAL", "0\nM-SEL"))
    w, h = (x1 - x0) * 0.62, (y1 - y0) - 60
    for r_, row in enumerate(keys):
        for c, lab in enumerate(row):
            bx = x0 + 30 + c * w / 4
            by = y0 + 50 + r_ * h / 3
            d.rounded_rectangle((bx, by, bx + w / 4 - 8, by + h / 3 - 8), 4, fill=(196, 198, 194),
                                outline=(20, 20, 20))
            parts = lab.split("\n")
            text(d, (bx + (w / 4 - 8) / 2, by + 13), parts[0], 13, (20, 20, 20), bold=True)
            if len(parts) > 1:
                text(d, (bx + (w / 4 - 8) / 2, by + 28), parts[1], 8, (20, 20, 20))
    for k, lab in enumerate(("COM1", "COM2", "IFF", "LIST", "A-A", "A-G")):
        bx = x0 + 22 + k * (x1 - x0 - 44) / 6
        d.rounded_rectangle((bx, y0 + 10, bx + (x1 - x0 - 44) / 6 - 8, y0 + 36), 4, fill=(70, 72, 74),
                            outline=(14, 14, 14))
        text(d, (bx + ((x1 - x0 - 44) / 6 - 8) / 2, y0 + 23), lab, 10, LABEL, bold=True)
    # rocker / wheels on the right
    rx = x0 + w + 46
    for k in range(3):
        d.rounded_rectangle((rx, y0 + 52 + k * 42, rx + 46, y0 + 80 + k * 42), 6, fill=(22, 22, 24),
                            outline=(90, 90, 90))
        for j in range(5):
            d.line((rx + 6 + j * 9, y0 + 55 + k * 42, rx + 6 + j * 9, y0 + 77 + k * 42), fill=(70, 70, 70))
    text(d, (rx + 23, y1 - 14), "SYM  BRT", 9, LABEL)


def caution_light(d, x, y, label, color):
    d.rectangle((x - 30, y - 12, x + 30, y + 12), fill=(18, 18, 18), outline=(80, 80, 80))
    d.rectangle((x - 27, y - 9, x + 27, y + 9), fill=tuple(int(c * 0.35) for c in color))
    text(d, (x, y), label, 9, tuple(min(255, int(c * 0.9)) for c in color), bold=True)


def instrument_panel(img, d, rnd):
    x0, y0, x1, y1 = ATLAS["panel"]
    d.rectangle((x0, y0, x1, y1), fill=PANEL)
    # sub panels
    for box in ((x0 + 6, y0 + 6, x0 + 320, y0 + 228), (x1 - 320, y0 + 6, x1 - 6, y0 + 228),
                (x0 + 6, y0 + 234, x0 + 410, y1 - 6), (x1 - 410, y0 + 234, x1 - 6, y1 - 6),
                (x0 + 416, y0 + 234, x1 - 416, y1 - 6)):
        d.rectangle(box, outline=(20, 20, 22), width=3)
        d.line((box[0] + 3, box[1] + 3, box[2] - 3, box[1] + 3), fill=PANEL_EDGE)
    ox, oy = x0, y0
    lm, rm = ATLAS["mfd_l"], ATLAS["mfd_r"]
    bezel(d, (lm[0] - 46, lm[1] - 46, lm[2] + 46, lm[3] + 46), lm)
    bezel(d, (rm[0] - 46, rm[1] - 46, rm[2] + 46, rm[3] + 46), rm)
    radar_page(d, lm, rnd)
    sms_page(d, rm)
    # RWR azimuth indicator, upper left, with caution lights
    rw = ATLAS["rwr"]
    gauge(d, (rw[0] + rw[2]) / 2, (rw[1] + rw[3]) / 2, (rw[2] - rw[0]) / 2, "rwr", rnd)
    for k, (lab, col) in enumerate((("MASTER", AMBER), ("TF FAIL", AMBER), ("ENG FIRE", (255, 60, 40)),
                                    ("ENGINE", (255, 60, 40)), ("HYD/OIL", (255, 60, 40)), ("CANOPY", (255, 60, 40)))):
        caution_light(d, ox + 44 + (k % 2) * 66, oy + 30 + (k // 2) * 32, lab, col)
    text(d, ((rw[0] + rw[2]) / 2, rw[3] + 18), "THREAT WARNING", 9)
    for k, s in enumerate(("MASTER ARM  -  ARM", "LASER ARM", "RF  NORM / QUIET")):
        text(d, (ox + 74, oy + 150 + k * 20), s, 9)
        toggle(d, ox + 150, oy + 150 + k * 20, rnd)
    # landing gear handle panel (left of the left MFD)
    d.rectangle((ox + 14, oy + 250, ox + 30, oy + 420), fill=(30, 30, 32))
    d.rounded_rectangle((ox + 8, oy + 230, ox + 36, oy + 262), 10, fill=(220, 220, 215), outline=(40, 40, 40))
    for k in range(3):
        d.ellipse((ox + 12, oy + 440 + k * 26, ox + 30, oy + 458 + k * 26), fill=(40, 120, 50))
    text(d, (ox + 22, oy + 530), "GEAR", 9)
    # ICP, DED (upper centre) and standby instruments (centre)
    icp(d, ATLAS["icp"])
    ded(d, ATLAS["ded"])
    text(d, ((ATLAS["ded"][0] + ATLAS["ded"][2]) / 2, ATLAS["ded"][3] + 16), "DATA ENTRY DISPLAY", 9)
    cx = (x0 + x1) / 2
    gauge(d, cx, oy + 330, 74, "adi", rnd)
    gauge(d, cx, oy + 520, 74, "hsi", rnd)
    # engine / fuel readouts under the DED
    for k, (lab, kind) in enumerate((("FTIT", "eng"), ("RPM", "eng"), ("FUEL", "fuel"))):
        gx = x1 - 274 + k * 92
        gauge(d, gx, oy + 172, 30, kind, rnd)
        text(d, (gx, oy + 216), lab, 9)


def console(d, box, titles, rnd):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(26, 27, 29))
    x = x0 + 4
    widths = [rnd.uniform(0.7, 1.3) for _ in titles]
    total = sum(widths)
    for t, w in zip(titles, widths):
        pw = (x1 - x0 - 8) * w / total
        sub_panel(d, (x, y0 + 4, x + pw - 4, y1 - 4), t, rnd, knobs=rnd.randint(1, 2), toggles=rnd.randint(1, 3))
        x += pw


def seat_details(d):
    x0, y0, x1, y1 = ATLAS["stripes"]
    d.rectangle((x0, y0, x1, y1), fill=(235, 190, 30))
    for k in range(-8, 16):
        xa = x0 + k * 18
        d.polygon([(xa, y1), (xa + 9, y1), (xa + 9 + (y1 - y0), y0), (xa + (y1 - y0), y0)], fill=(20, 20, 18))
    d.rectangle((x0, y0, x1, y1), outline=(235, 190, 30), width=1)
    # quilted cushion
    x0, y0, x1, y1 = ATLAS["cushion"]
    d.rectangle((x0, y0, x1, y1), fill=(58, 64, 50))
    for k in range(0, x1 - x0, 32):
        d.line((x0 + k, y0, x0 + k, y1), fill=(40, 44, 34), width=3)
    for k in range(0, y1 - y0, 32):
        d.line((x0, y0 + k, x1, y0 + k), fill=(40, 44, 34), width=3)
    # dark interior paint with scuffs
    x0, y0, x1, y1 = ATLAS["tub"]
    d.rectangle((x0, y0, x1, y1), fill=(52, 54, 57))
    # warning placard
    x0, y0, x1, y1 = ATLAS["placard"]
    d.rectangle((x0, y0, x1, y1), fill=(230, 30, 20))
    text(d, ((x0 + x1) / 2, (y0 + y1) / 2 - 12), "WARNING", 22, (255, 255, 255), bold=True)
    text(d, ((x0 + x1) / 2, (y0 + y1) / 2 + 14), "EJECTION SEAT", 14, (255, 255, 255), bold=True)


def main():
    rnd = random.Random(16)
    img = Image.new("RGB", (SIZE, SIZE), (40, 40, 40))
    d = ImageDraw.Draw(img)
    instrument_panel(img, d, rnd)
    console(d, ATLAS["console_l"], ("AUDIO 1", "AUDIO 2", "MANUAL TRIM", "SNSR PWR", "EPU", "ELEC"), rnd)
    console(d, ATLAS["console_r"], ("AVIONIC POWER", "LIGHTING", "AIR COND", "ZEROIZE", "OXYGEN"), rnd)
    seat_details(d)
    # light grain so flat panels don't look like plastic
    noise = Image.effect_noise((SIZE, SIZE), 9).convert("RGB").filter(ImageFilter.GaussianBlur(0.6))
    img = Image.blend(img, Image.composite(img, noise, Image.new("L", (SIZE, SIZE), 238)), 1.0)
    out = os.path.join(ROOT, "dogfight", "render", "cockpit.png")
    img.save(out, optimize=True)
    print("wrote", out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
