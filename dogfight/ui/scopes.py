"""Radar B-scope and RWR scope."""

import math

from panda3d.core import TextNode

from ..mathutil import DEG, to_local
from ..sim.radar import ACM, OFF, SEARCH, STT
from .colors import AMBER, DIM, GREEN, RED

RANGE_SCALES = (10000.0, 20000.0, 40000.0, 80000.0)


def _auto_scale(radar, owner):
    tgt = radar.locked or radar.selected or radar.pending
    if radar.mode == ACM:
        return 20000.0
    if tgt is None:
        return 40000.0
    dist = (tgt.pos - owner.pos).length()
    for scale in RANGE_SCALES:
        if dist < scale * 0.85:
            return scale
    return RANGE_SCALES[-1]


def draw_radar(canvas, labels, radar, owner, time, cx, cy, size):
    spec = radar.spec
    hw = size * 0.5
    left, right, bottom, top = cx - hw, cx + hw, cy - hw, cy + hw
    canvas.rect(cx, cy, hw, hw, DIM)
    scale = _auto_scale(radar, owner)
    az_max = spec.scan_az * DEG

    def to_xy(az, rng):
        x = cx + max(-1.0, min(1.0, az / az_max)) * hw
        y = bottom + min(rng / scale, 1.0) * size
        return x, y

    for k in (1, 2, 3):
        y = bottom + size * k / 4
        canvas.line(left, y, left + 0.02, y, DIM)
        canvas.line(right - 0.02, y, right, y, DIM)
    for az in (-30, 0, 30):
        x = cx + az / spec.scan_az * hw
        canvas.line(x, bottom, x, bottom + 0.02, DIM)
        canvas.line(x, top - 0.02, x, top, DIM)

    mode_text = {OFF: "OFF", SEARCH: "SRCH", ACM: "ACM", STT: "STT"}[radar.mode]
    labels.text("%s  %d km" % (mode_text, scale / 1000), left + 0.01, top + 0.012, GREEN, scale=0.03)
    labels.text("RADAR", right, top + 0.012, DIM, scale=0.03, align=TextNode.ARight)
    if radar.mode == OFF:
        labels.text("OFF", cx, cy, DIM, scale=0.05, align=TextNode.ACenter)
        return

    if radar.mode == SEARCH:
        x = cx + radar.beam_az / az_max * hw
        canvas.line(x, bottom, x, top, (0.4, 1.0, 0.5, 0.25))
    elif radar.mode == ACM:
        w = spec.acm_az / spec.scan_az * hw
        y = bottom + min(spec.acm_range / scale, 1.0) * size
        canvas.polyline([(cx - w, bottom), (cx - w, y), (cx + w, y), (cx + w, bottom)], AMBER)

    for tgt, c in radar.contacts.items():
        if tgt is radar.locked:
            continue
        x, y = to_xy(c.az, c.range)
        canvas.filled_box(x, y, 0.008, GREEN)
        if tgt is radar.selected:
            canvas.brackets(x, y, 0.02, GREEN)
            labels.text("%.1f" % (tgt.pos.z / 1000.0), x + 0.024, y - 0.01, DIM, scale=0.026)

    if radar.pending is not None:
        az, el, dist = radar.angles_to(radar.pending.pos)
        x, y = to_xy(az, dist)
        if int(time * 8) % 2 == 0:
            canvas.brackets(x, y, 0.024, AMBER)

    tgt = radar.locked
    if tgt is not None and radar.track_pos is not None:
        az, el, dist = radar.angles_to(radar.track_pos)
        x, y = to_xy(az, dist)
        color = AMBER if radar.lost_time > 0 else GREEN
        canvas.diamond(x, y, 0.016, color)
        heading = to_local(owner.quat, radar.track_vel)
        hl = math.hypot(heading.x, heading.y)
        if hl > 1.0:
            canvas.line(x, y, x + heading.x / hl * 0.04, y + heading.y / hl * 0.04, color)
        labels.text("%.1f" % (radar.track_pos.z / 1000.0), x + 0.024, y - 0.01, color, scale=0.026)


def draw_rwr(canvas, labels, rwr, time, cx, cy, r):
    canvas.circle(cx, cy, r, DIM, segments=40)
    canvas.circle(cx, cy, r * 0.5, (0.4, 1.0, 0.5, 0.25), segments=28)
    for k in range(12):
        a = k * math.pi / 6
        canvas.line(cx + math.sin(a) * r, cy + math.cos(a) * r, cx + math.sin(a) * r * 0.93,
                    cy + math.cos(a) * r * 0.93, DIM)
    canvas.line(cx - 0.012, cy, cx + 0.012, cy, DIM)
    canvas.line(cx, cy - 0.012, cx, cy + 0.016, DIM)
    labels.text("RWR", cx - r, cy + r - 0.02, DIM, scale=0.03)
    blink = int(time * 6) % 2 == 0
    for t in rwr.threats:
        if t.level == "launch":
            radius, color = r * 0.32, RED
            if not blink:
                continue
        elif t.level == "lock":
            radius, color = r * 0.58, AMBER
        else:
            radius, color = r * 0.82, GREEN
        x = cx + math.sin(t.bearing) * radius
        y = cy + math.cos(t.bearing) * radius
        labels.text(t.symbol, x, y - 0.012, color, scale=0.034, align=TextNode.ACenter)
        if t.level != "search":
            canvas.circle(x, y, 0.028, color, segments=16)
