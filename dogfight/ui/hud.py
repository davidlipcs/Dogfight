"""Head-up display in War Thunder style.

* white circle  = where the mouse wants the aircraft to fly (mouse aim)
* green cross   = where the nose / gun points
* small circle with wings = flight path marker (where the aircraft actually goes)
* green square  = radar lock (STT), amber blinking brackets = acquiring
* circle that follows the target = AIM-9 seeker head
* circle with a dot = gun lead indicator (needs a radar lock)
"""

import math

import numpy as np
from panda3d.core import CardMaker, Point2, Point3, Texture, TextNode, TransparencyAttrib, Vec3

from ..mathutil import DEG, angle_between, clamp, heading_deg, safe_normalized
from ..sim.guns import gun_lead
from ..sim.missile import flyout_time, launch_zone, time_to_impact
from ..sim.radar import ACM, STT
from ..sim.specs import ARH, IR
from .colors import AMBER, CYAN, DIM, ENEMY, GREEN, RED, WHITE
from .draw import Canvas, TextPool
from .scopes import draw_radar, draw_rwr

MESSAGE_COLORS = {"good": GREEN, "warn": AMBER, "bad": RED, "info": WHITE}



def _vignette_texture(size=256):
    """White texture whose alpha grows from the centre to the edges."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.hypot(xx / (size - 1) * 2 - 1, yy / (size - 1) * 2 - 1)
    a = np.clip((r - 0.45) / 0.55, 0.0, 1.0) ** 1.5
    img = np.dstack([np.full_like(a, 255), np.full_like(a, 255), np.full_like(a, 255), a * 255]).astype(np.uint8)
    tex = Texture("g_vignette")
    tex.setup2dTexture(size, size, Texture.T_unsigned_byte, Texture.F_rgba)
    tex.setRamImage(img[:, :, [2, 1, 0, 3]].tobytes())
    tex.setWrapU(Texture.WM_clamp)
    tex.setWrapV(Texture.WM_clamp)
    return tex


def _overlay_card(base, texture):
    cm = CardMaker("g_overlay")
    cm.setFrame(-1, 1, -1, 1)
    card = base.aspect2d.attachNewNode(cm.generate())
    if texture is not None:
        card.setTexture(texture)
    card.setTransparency(TransparencyAttrib.MAlpha)
    card.hide()
    return card

class HUD:
    def __init__(self, base, fonts):
        self.base = base
        self.fonts = fonts
        # G effect overlays (below the symbology): a radial vignette and a full screen tint per colour
        self.g_black = self.g_red = 0.0
        vignette = _vignette_texture()
        self._g_black_cards = (_overlay_card(base, vignette), _overlay_card(base, None))
        self._g_red_cards = (_overlay_card(base, vignette), _overlay_card(base, None))
        self.root = base.aspect2d.attachNewNode("hud")
        self.canvas = Canvas(self.root, 1.6)
        self.labels = TextPool(self.root, fonts.mono, 0.034, fonts.t)
        self.titles = TextPool(self.root, fonts.text, 0.06, fonts.t)
        self.messages = []          # [text, color, time left]
        self.killfeed = []          # [text, color, time left]
        self.show_markers = True
        self.hitmarker = 0.0
        self.time = 0.0
        self._dlz = None
        self._dlz_timer = 0.0

    # --------------------------------------------------------------- events
    def message(self, text, kind="info", duration=2.5, key=None):
        """Show a message; messages with the same ``key`` (or text) replace each other."""
        key = key or text
        for m in self.messages:
            if m[3] == key:
                m[0] = text
                m[1] = MESSAGE_COLORS.get(kind, WHITE)
                m[2] = duration
                return
        self.messages.append([text, MESSAGE_COLORS.get(kind, WHITE), duration, key])
        self.messages = self.messages[-4:]

    def handle_event(self, kind, data, player):
        if kind == "message" and data.get("to") is player:
            self.message(data["text"], data.get("level", "info"))
        elif kind == "kill":
            victim = data["victim"]
            killer = data.get("killer")
            weapon = data.get("weapon")
            if killer is not None and killer is not victim:
                text = "%s -> %s  [%s]" % (killer.name, victim.name, weapon)
            else:
                text = "%s lezuhant" % victim.name
            color = GREEN if killer is player else (RED if victim is player else WHITE)
            self.killfeed.append([text, color, 7.0])
            self.killfeed = self.killfeed[-5:]
            if killer is player and victim is not player:
                self.message("CÉLPONT MEGSEMMISÍTVE", "good", 3.0)
        elif kind == "hit" and data.get("shooter") is player and data.get("target") is not player:
            self.hitmarker = 0.25
        elif kind == "pitbull" and data["missile"].shooter is player:
            self.message("PITBULL - AIM-120 aktív", "good")

    # ------------------------------------------------------------ projection
    def project(self, world_pos):
        base = self.base
        p3 = base.cam.getRelativePoint(base.render, Point3(world_pos))
        if p3.y < 1.0:
            return None
        p2 = Point2()
        base.camLens.project(p3, p2)
        return p2.x * base.getAspectRatio(), p2.y

    def edge_arrow(self, world_pos, color):
        """Arrow at the screen edge pointing to an off-screen object."""
        base = self.base
        p3 = base.cam.getRelativePoint(base.render, Point3(world_pos))
        ang = math.atan2(p3.x, p3.z)
        r = 0.78
        x = math.sin(ang) * r * base.getAspectRatio() * 0.8
        y = math.cos(ang) * r
        tip = (x + math.sin(ang) * 0.04, y + math.cos(ang) * 0.04)
        side = (math.cos(ang) * 0.025, -math.sin(ang) * 0.025)
        self.canvas.polyline([(x + side[0], y + side[1]), tip, (x - side[0], y - side[1])], color, closed=True)

    # ---------------------------------------------------------------- frame
    def update(self, dt, player, world, cam, game):
        self.time += dt
        self.hitmarker = max(0.0, self.hitmarker - dt)
        for lst in (self.messages, self.killfeed):
            for m in lst:
                m[2] -= dt
        self.messages = [m for m in self.messages if m[2] > 0]
        self.killfeed = [m for m in self.killfeed if m[2] > 0]

        c = self.canvas
        c.begin()
        self.labels.begin()
        self.titles.begin()
        aspect = self.base.getAspectRatio()

        self._g_effects(player, dt, aspect)
        if player is not None and player.alive:
            self._incoming_missiles(player)
            self._flight_symbols(player, world, cam)
            self._targets(player, world)
            self._weapons_symbols(player, world, dt)
            self._panels(player, world, aspect)
            draw_radar(c, self.labels, player.radar, player, self.time, aspect - 0.34, -0.66, 0.5)
            draw_rwr(c, self.labels, player.rwr, self.time, -aspect + 0.3, -0.68, 0.22)
            self._warnings(player, world)
            self._missile_list(player, world, aspect)
        self._overlay_text(game, aspect)

        c.end()
        self.labels.end()
        self.titles.end()

    # ------------------------------------------------------------ symbology
    def _flight_symbols(self, ac, world, cam):
        c = self.canvas
        aim_pos = cam.position + cam.aim_direction() * 3000.0
        aim = self.project(aim_pos)
        if aim is not None and not (cam.free_look and not cam.cockpit):
            c.circle(aim[0], aim[1], 0.022, WHITE, segments=24)
        elif aim is None and cam.cockpit:
            self.edge_arrow(aim_pos, WHITE)
        nose = self.project(ac.pos + ac.forward * 800.0)
        if nose is not None:
            c.cross(nose[0], nose[1], 0.035, 0.009, GREEN)
            if self.hitmarker > 0.0:
                k = 0.03
                c.line(nose[0] - k, nose[1] - k, nose[0] - k * 0.4, nose[1] - k * 0.4, WHITE)
                c.line(nose[0] + k, nose[1] + k, nose[0] + k * 0.4, nose[1] + k * 0.4, WHITE)
                c.line(nose[0] - k, nose[1] + k, nose[0] - k * 0.4, nose[1] + k * 0.4, WHITE)
                c.line(nose[0] + k, nose[1] - k, nose[0] + k * 0.4, nose[1] - k * 0.4, WHITE)
        if ac.speed > 20.0:
            fpm = self.project(ac.pos + safe_normalized(ac.vel) * 800.0)
            if fpm is not None:
                x, y = fpm
                c.circle(x, y, 0.012, GREEN, segments=14)
                c.line(x - 0.035, y, x - 0.012, y, GREEN)
                c.line(x + 0.012, y, x + 0.035, y, GREEN)
                c.line(x, y + 0.012, x, y + 0.026, GREEN)
        if cam.cockpit:
            self._pitch_ladder(ac, cam)

    def _pitch_ladder(self, ac, cam):
        c = self.canvas
        hdg = math.atan2(ac.forward.x, ac.forward.y)
        base = cam.position

        def direction(h, e):
            return Vec3(math.sin(h) * math.cos(e), math.cos(h) * math.cos(e), math.sin(e))
        pitch = math.degrees(math.asin(clamp(ac.forward.z, -1, 1)))
        for e in range(-80, 90, 10):
            if abs(e - pitch) > 35:
                continue
            er = e * DEG
            inner, outer = (2.0, 9.0) if e != 0 else (1.5, 25.0)
            for side in (-1, 1):
                a = self.project(base + direction(hdg + side * inner * DEG, er) * 5000.0)
                b = self.project(base + direction(hdg + side * outer * DEG, er) * 5000.0)
                if a is None or b is None:
                    continue
                color = GREEN if e >= 0 else DIM
                c.line(a[0], a[1], b[0], b[1], color)
                if e != 0 and side == 1:
                    self.labels.text("%d" % e, b[0] + 0.01, b[1] - 0.01, color, scale=0.028)

    def _targets(self, ac, world):
        if not self.show_markers:
            return
        c = self.canvas
        for tgt in world.aircraft:
            if tgt is ac or not tgt.alive or tgt.team == ac.team:
                continue
            dist = (tgt.pos - ac.pos).length()
            if dist > 80000.0:
                continue
            p = self.project(tgt.pos)
            if p is None:
                continue
            x, y = p
            if tgt is self._lock_target(ac, ac.selected_spec):
                continue                       # drawn by the lock box
            c.polyline([(x - 0.012, y + 0.03), (x + 0.012, y + 0.03), (x, y + 0.016)], ENEMY, closed=True)
            self.labels.text("%.1f" % (dist / 1000.0), x, y + 0.04, ENEMY, scale=0.026, align=TextNode.ACenter)

    def _weapons_symbols(self, ac, world, dt):
        c = self.canvas
        radar = ac.radar
        # radar lock box
        if radar.mode == STT and radar.track_pos is not None:
            tgt = radar.locked
            p = self.project(radar.track_pos)
            color = GREEN if radar.lost_time == 0 else AMBER
            if p is None:
                self.edge_arrow(radar.track_pos, color)
            elif radar.lost_time > 0:
                self.labels.text("MEM", p[0], p[1] - 0.07, AMBER, scale=0.03, align=TextNode.ACenter)
            # gun lead indicator
            if tgt is not None and (tgt.pos - ac.pos).length() < ac.spec.gun.max_lead_range:
                aim_dir, tof = gun_lead(ac.pos, ac.vel, tgt.pos, tgt.vel, ac.spec.gun)
                dist = (tgt.pos - ac.pos).length()
                lp = self.project(ac.pos + aim_dir * dist)
                if lp is not None:
                    c.circle(lp[0], lp[1], 0.03, WHITE, segments=24)
                    c.circle(lp[0], lp[1], 0.004, WHITE, segments=6)
                    frac = clamp(dist / ac.spec.gun.max_lead_range, 0.0, 1.0)
                    c.circle(lp[0], lp[1], 0.036, WHITE, segments=20, end=2 * math.pi * (1 - frac))
        elif radar.pending is not None:
            p = self.project(radar.pending.pos)
            if p is not None and int(self.time * 8) % 2 == 0:
                c.brackets(p[0], p[1], 0.035, AMBER)
        elif radar.mode == ACM:
            # vertical scan window in front of the nose
            spec = radar.spec
            corners = []
            for az, el in ((-spec.acm_az, spec.acm_el_low), (spec.acm_az, spec.acm_el_low),
                           (spec.acm_az, spec.acm_el_high), (-spec.acm_az, spec.acm_el_high)):
                d = ac.quat.xform(Vec3(math.sin(az * DEG) * math.cos(el * DEG), math.cos(az * DEG) * math.cos(el * DEG),
                                       math.sin(el * DEG)))
                corners.append(self.project(ac.pos + d * 3000.0))
            if all(p is not None for p in corners):
                c.polyline(corners, (1.0, 0.78, 0.25, 0.5), closed=True)
        if radar.selected is not None and radar.mode != STT and radar.selected.alive:
            p = self.project(radar.selected.pos)
            if p is not None:
                c.brackets(p[0], p[1], 0.03, DIM)

        self._missile_paths(ac, world)
        spec = ac.selected_spec
        if spec is None:
            return
        if spec.guidance == IR:
            seeker = ac.ir_seeker
            if seeker.axis is not None:
                p = self.project(ac.pos + seeker.axis * 2000.0)
                if p is not None:
                    if seeker.locked:
                        c.circle(p[0], p[1], 0.04, GREEN, segments=24)
                        c.circle(p[0], p[1], 0.044, GREEN, segments=24)
                        c.diamond(p[0], p[1], 0.01, GREEN)
                    else:
                        # search circle as big as the seeker's search cone (wide with the lock assist)
                        fov = (seeker.acq_fov or seeker.spec.seeker_fov) * DEG
                        vfov = self.base.camLens.getFov()[1] * DEG
                        radius = max(0.04, math.tan(fov) / math.tan(vfov / 2.0))
                        if seeker.candidate is not None:
                            color = GREEN if int(self.time * 10) % 2 == 0 else WHITE
                        else:
                            color = DIM
                        c.circle(p[0], p[1], radius, color, segments=40)
        self._dlz_bar(ac, spec, dt)
        self._lock_box(ac, spec)

    @staticmethod
    def _lock_target(ac, spec):
        """What the selected missile is locked on (IR seeker or radar STT), or None."""
        seeker = ac.ir_seeker
        if spec is not None and spec.guidance == IR and seeker.locked and not getattr(seeker.target, "is_flare", False):
            return seeker.target
        radar = ac.radar
        if radar.mode == STT and radar.locked is not None and radar.locked.alive:
            return radar.locked
        return None

    def _dashed(self, a, b, color, on=0.018, off=0.012):
        c = self.canvas
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return
        s = 0.0
        while s < length:
            e = min(s + on, length)
            c.line(a[0] + dx * s / length, a[1] + dy * s / length, a[0] + dx * e / length, a[1] + dy * e / length, color)
            s += on + off

    def _lock_box(self, ac, spec):
        """Big square around the locked aircraft and where a missile fired now would meet it."""
        tgt = self._lock_target(ac, spec)
        if tgt is None:
            return
        c = self.canvas
        radar = ac.radar
        pos = radar.track_pos if (radar.mode == STT and radar.locked is tgt and radar.track_pos is not None) else tgt.pos
        rel = pos - ac.pos
        dist = rel.length()
        in_range = self._dlz is not None and spec is not None and spec.min_range < dist < self._dlz[0]
        color = RED if in_range else GREEN
        p = self.project(pos)
        if spec is not None:
            tt = flyout_time(spec, ac.speed, ac.pos.z, dist)
            ip = pos
            for _ in range(4):
                if tt is None:
                    break
                ip = pos + tgt.vel * tt
                tt = flyout_time(spec, ac.speed, ac.pos.z, (ip - ac.pos).length())
            a = self.project(ac.pos + ac.forward * 25.0)
            b = self.project(ip) if tt is not None else None
            if a is not None and b is not None:
                self._dashed(a, b, color)
                if p is not None:
                    self._dashed(p, b, ENEMY, 0.006, 0.008)
                k = 0.014
                c.line(b[0] - k, b[1] - k, b[0] + k, b[1] + k, color)
                c.line(b[0] - k, b[1] + k, b[0] + k, b[1] - k, color)
                c.circle(b[0], b[1], 0.02, color, segments=16)
                self.labels.text("találat ~%d s" % round(tt), b[0] + 0.028, b[1] - 0.03, color, scale=0.026)
        if p is None:
            return
        vfov = self.base.camLens.getFov()[1] * DEG
        hs = clamp(7.0 / max(dist, 1.0) / math.tan(vfov / 2.0), 0.045, 0.25)
        for off in (0.0, 0.004):                     # double line = thick box
            c.rect(p[0], p[1], hs + off, hs + off, color)
        for sx in (-1, 1):
            for sy in (-1, 1):
                c.line(p[0] + sx * (hs + 0.008), p[1] + sy * hs, p[0] + sx * (hs + 0.02), p[1] + sy * hs, color)
                c.line(p[0] + sx * hs, p[1] + sy * (hs + 0.008), p[0] + sx * hs, p[1] + sy * (hs + 0.02), color)
        closure = -(tgt.vel - ac.vel).dot(safe_normalized(rel))
        self.labels.text("LOCK  %s" % (spec.name if spec else ""), p[0] - hs, p[1] + hs + 0.025, color, scale=0.034)
        self.labels.text("%.1f km   Vc %+d" % (dist / 1000.0, closure * 3.6), p[0] - hs, p[1] - hs - 0.04, color,
                         scale=0.026)
        note = None
        if in_range:
            if int(self.time * 4) % 2 == 0:
                note = ("LŐHETSZ!  (Space)", RED, 0.04)
        elif spec is not None and dist <= spec.min_range:
            note = ("túl közel", AMBER, 0.028)
        elif spec is not None and spec.guidance == IR and dist > 9000.0 and ac.missile_count("AIM-120A"):
            note = ("messze van - válts AIM-120-ra (2)", AMBER, 0.028)
        elif spec is not None and self._dlz is not None and dist >= self._dlz[0]:
            note = ("még messze", AMBER, 0.028)
        if note is not None:
            self.labels.text(note[0], p[0], p[1] - hs - 0.085, note[1], scale=note[2], align=TextNode.ACenter)

    def _missile_paths(self, ac, world):
        """Own missiles in flight: marker on the missile and its path to the target."""
        c = self.canvas
        for m in world.missiles:
            if m.shooter is not ac or not m.alive:
                continue
            mp = self.project(m.pos)
            aim = m.guided_target.pos if m.guided_target is not None else m.est_pos
            ap = self.project(aim) if aim is not None else None
            if mp is not None and ap is not None:
                self._dashed(mp, ap, CYAN, 0.01, 0.01)
            if mp is not None:
                c.diamond(mp[0], mp[1], 0.011, CYAN)
                ttg = time_to_impact(m)
                if ttg is not None and ttg < 99:
                    self.labels.text("%.1f s" % ttg, mp[0] + 0.015, mp[1] + 0.015, CYAN, scale=0.024)

    def _dlz_bar(self, ac, spec, dt):
        radar = ac.radar
        tgt = radar.locked if radar.mode == STT else None
        if spec.guidance == IR and ac.ir_seeker.locked and not getattr(ac.ir_seeker.target, "is_flare", False):
            tgt = ac.ir_seeker.target
        if tgt is None:
            self._dlz = None
            return
        rel = tgt.pos - ac.pos
        dist = rel.length()
        closing_target = -tgt.vel.dot(safe_normalized(rel))
        self._dlz_timer -= dt
        if self._dlz is None or self._dlz_timer <= 0.0:
            self._dlz = launch_zone(spec, ac.speed, ac.pos.z, closing_target)
            self._dlz_timer = 0.5
        rmax, rne = self._dlz
        rmin = spec.min_range
        c = self.canvas
        x = 0.34
        y0, y1 = -0.22, 0.22
        scale = max(rmax * 1.25, dist * 1.05, 2000.0)

        def ry(r):
            return y0 + (y1 - y0) * clamp(r / scale, 0.0, 1.0)
        c.line(x, ry(rmin), x, ry(rmax), GREEN)
        c.line(x - 0.012, ry(rmax), x + 0.012, ry(rmax), GREEN)
        c.line(x - 0.012, ry(rmin), x + 0.012, ry(rmin), GREEN)
        c.line(x - 0.02, ry(rne), x + 0.02, ry(rne), GREEN)
        c.line(x, ry(rne), x + 0.02, ry(rne) + 0.01, GREEN)
        yy = ry(dist)
        c.polyline([(x - 0.035, yy + 0.012), (x - 0.015, yy), (x - 0.035, yy - 0.012)], WHITE)
        self.labels.text("%.1f" % (rmax / 1000.0), x + 0.02, ry(rmax) - 0.01, DIM, scale=0.026)
        in_range = rmin < dist < rmax
        no_escape = rmin < dist < rne
        if no_escape:
            self.labels.text("NO ESC", x - 0.03, y0 - 0.05, RED, scale=0.03)
        elif in_range:
            self.labels.text("IN RNG", x - 0.03, y0 - 0.05, GREEN, scale=0.03)
        elif dist <= rmin:
            self.labels.text("MIN", x - 0.03, y0 - 0.05, AMBER, scale=0.03)

    # ---------------------------------------------------------------- panels
    def _panels(self, ac, world, aspect):
        fm = ac.fm
        L = self.labels
        ias = fm.ias * 3.6
        thr = ac.controls.throttle
        thr_text = "AB" if thr > 1.0 else "%3d%%" % (thr * 100)
        eng_text = "AB" if fm.engine > 1.001 else "%3d%%" % (fm.engine * 100)
        x = -0.78
        y = 0.22
        L.text("IAS %5d km/h" % ias, x, y, GREEN)
        L.text("TAS %5d" % (ac.speed * 3.6), x, y - 0.05, DIM)
        L.text("M   %5.2f" % fm.mach, x, y - 0.10, GREEN)
        g_col = AMBER if fm.g_load > 7.5 else GREEN
        L.text("G   %5.1f" % fm.g_load, x, y - 0.15, g_col)
        aoa_col = AMBER if fm.alpha / DEG > 20 else GREEN
        L.text("AoA %5.1f" % (fm.alpha / DEG), x, y - 0.20, aoa_col)
        L.text("THR  %s" % thr_text, x, y - 0.25, AMBER if thr > 1.0 else GREEN)
        L.text("MOT  %s" % eng_text, x + 0.24, y - 0.25, DIM if abs(fm.engine - thr) > 0.02 else GREEN)
        gear = fm.gear_pos
        if gear > 0.98:
            L.text("GEAR DOWN", x, y - 0.30, GREEN)
        elif gear > 0.02:
            L.text("GEAR %s" % ("↓" if fm.gear_down else "↑"), x, y - 0.30, AMBER)
        else:
            L.text("GEAR UP", x, y - 0.30, DIM)
        if ac.on_ground:
            L.text("GS  %5d km/h" % (ac.speed * 3.6), x, y - 0.35, GREEN)
            if ac.controls.brakes:
                L.text("BRAKES", x, y - 0.40, AMBER)
        elif ac.controls.airbrake:
            L.text("SPD BRK", x, y - 0.35, AMBER)

        x = 0.52
        terrain_h = world.terrain.height(ac.pos.x, ac.pos.y)
        L.text("ALT %6d m" % ac.pos.z, x, y, GREEN)
        L.text("AGL %6d" % (ac.pos.z - terrain_h), x, y - 0.05, DIM)
        L.text("VS  %+6d" % fm.vel.z, x, y - 0.10, GREEN)
        L.text("HDG    %03d" % heading_deg(ac.forward), x, y - 0.15, GREEN)
        fuel_col = RED if fm.fuel < 400 else (AMBER if fm.fuel < 900 else GREEN)
        L.text("FUEL %5d kg" % fm.fuel, x, y - 0.20, fuel_col)
        L.text("HP   %5d" % max(0, ac.hp), x, y - 0.25, GREEN if ac.hp > 50 else RED)

        # weapons
        y = -0.79
        parts = []
        for key in ac.weapon_keys():
            n = ac.missile_count(key)
            text = "%s x%d" % (key, n)
            pending = [s.reload for s in ac.stations if s.key == key and not s.loaded and s.reload is not None]
            if pending:
                text += " +%d (%ds)" % (len(pending), math.ceil(min(pending)))
            parts.append(("[%s]" if key == ac.selected else " %s ") % text)
        L.text("   ".join(parts), 0.0, y, GREEN, align=TextNode.ACenter)
        L.text("GUN %3d    FLR %2d   CHF %2d" % (ac.gun.ammo, ac.flares, ac.chaff), 0.0, y - 0.05, GREEN,
               align=TextNode.ACenter)
        spec = ac.selected_spec
        status = ""
        color = GREEN
        if spec is not None and spec.guidance == IR:
            seeker = ac.ir_seeker
            if seeker.locked:
                status = "AIM-9M: LOCK (F: elenged)"
            elif seeker.candidate is not None:
                status = "AIM-9M: HŐFORRÁS A KERESŐBEN - F: lock"
                color = WHITE
            else:
                status = "AIM-9M: keresés (growl)"
                color = DIM
        elif spec is not None and spec.guidance == ARH:
            if ac.radar.mode == STT:
                status = "AIM-120A: radar lock OK"
            else:
                status = "AIM-120A: nincs lock (maddog) - T: radar lock"
                color = AMBER
        L.text(status, 0.0, y - 0.10, color, align=TextNode.ACenter)
        radar = ac.radar
        if radar.mode == STT and radar.track_pos is not None:
            rel = radar.track_pos - ac.pos
            closure = -(radar.track_vel - ac.vel).dot(safe_normalized(rel))
            aspect_deg = math.degrees(angle_between(radar.track_vel, ac.pos - radar.track_pos))
            note = "  NOTCH!" if radar.notched else ""
            L.text("STT %.1f km  Vc %+d km/h  ASP %d%s" % (rel.length() / 1000, closure * 3.6, aspect_deg, note),
                   0.0, y - 0.15, AMBER if note else GREEN, align=TextNode.ACenter)
        elif radar.mode == ACM:
            L.text("ACM: tedd az orrod elé a célt", 0.0, y - 0.15, AMBER, align=TextNode.ACenter)

    def _g_effects(self, ac, dt, aspect):
        """Grey-out / blackout under sustained positive G, red-out under negative G."""
        if ac is None or not ac.alive:
            self.g_black = self.g_red = 0.0
        else:
            g = ac.fm.g_load
            rate = (g - 7.5) * 0.15 if g > 7.5 else (-0.4 if g < 6.5 else 0.0)
            self.g_black = clamp(self.g_black + rate * dt, 0.0, 1.0)
            rate = (-g - 1.8) * 0.35 if g < -1.8 else -0.6
            self.g_red = clamp(self.g_red + rate * dt, 0.0, 1.0)
        for (vignette, fill), level, rgb in ((self._g_black_cards, self.g_black, (0, 0, 0)),
                                             (self._g_red_cards, self.g_red, (0.6, 0, 0))):
            if level <= 0.01:
                vignette.hide()
                fill.hide()
                continue
            vignette.show()
            vignette.setScale(aspect * (1.3 - level * 0.45), 1, 1.3 - level * 0.45)
            vignette.setColor(rgb[0], rgb[1], rgb[2], min(0.97, level * 1.4))
            fill.setScale(aspect, 1, 1)
            if level > 0.6:
                fill.show()
                fill.setColor(rgb[0], rgb[1], rgb[2], (level - 0.6) * 2.2)
            else:
                fill.hide()

    def _incoming_missiles(self, ac):
        """Missiles flying at the player: red marker (or edge arrow) with distance and time to impact."""
        c = self.canvas
        blink = int(self.time * 6) % 2 == 0
        for dist, m in ac.rwr.incoming:
            p = self.project(m.pos)
            if p is None:
                self.edge_arrow(m.pos, RED)
                continue
            closing = (m.vel - ac.vel).dot(safe_normalized(ac.pos - m.pos))
            c.diamond(p[0], p[1], 0.022, RED)
            if blink:
                c.circle(p[0], p[1], 0.034, RED, segments=20)
            text = "RAKÉTA %.1f km" % (dist / 1000.0)
            if closing > 1.0 and dist / closing < 60.0:
                text += "  %.1f s" % (dist / closing)
            self.labels.text(text, p[0] + 0.045, p[1] - 0.01, RED, scale=0.028)

    def _warnings(self, ac, world):
        T = self.titles
        y = 0.5
        blink = int(self.time * 4) % 2 == 0
        ahead = ac.pos + ac.vel * 4.0
        terrain = world.terrain
        if not ac.on_ground and ac.fm.gear_pos < 0.5 and (
                ahead.z < terrain.height(ahead.x, ahead.y) + 60.0
                or (ac.pos.z - terrain.height(ac.pos.x, ac.pos.y) < 150.0 and ac.vel.z < -15.0)):
            if blink:
                T.text("PULL UP", 0.0, y, RED, align=TextNode.ACenter)
            y -= 0.08
        if ac.rwr.max_level >= 3:
            if blink:
                T.text("MISSILE!", 0.0, y, RED, align=TextNode.ACenter)
            y -= 0.08
        elif ac.rwr.max_level == 2:
            T.text("RADAR LOCK", 0.0, y, AMBER, scale=0.045, align=TextNode.ACenter)
            y -= 0.07
        if ac.fm.ias < 70.0 and not ac.on_ground:
            T.text("SPEED LOW", 0.0, y, AMBER, scale=0.045, align=TextNode.ACenter)
            y -= 0.07
        agl = ac.pos.z - terrain.height(ac.pos.x, ac.pos.y)
        if (not ac.on_ground and ac.fm.gear_pos < 0.98 and agl < 300.0 and ac.fm.ias < 95.0
                and ac.vel.z < -2.0 and blink):
            T.text("FUTÓMŰ!", 0.0, y, RED, scale=0.05, align=TextNode.ACenter)
            y -= 0.07
        if ac.fm.gear_pos > 0.02 and ac.fm.ias > 155.0 and blink:
            T.text("GEAR SPEED", 0.0, y, AMBER, scale=0.045, align=TextNode.ACenter)
            y -= 0.07
        if 0 < ac.fm.fuel < 400.0:
            T.text("BINGO FUEL", 0.0, y, AMBER, scale=0.045, align=TextNode.ACenter)
        # messages
        my = 0.33
        for text, color, _, _ in self.messages:
            self.labels.text(text, 0.0, my, color, scale=0.042, align=TextNode.ACenter)
            my -= 0.05

    def _missile_list(self, ac, world, aspect):
        y = 0.62
        x = aspect - 0.05
        for m in world.missiles:
            if m.shooter is not ac:
                continue
            ttg = time_to_impact(m)
            t_text = "%4.1fs" % ttg if ttg is not None and ttg < 99 else "  -- "
            color = CYAN if m.status in ("TRACK", "ACTIVE", "DATALINK") else AMBER
            self.labels.text("%s %-8s %s" % (m.spec.name.split()[0], m.status, t_text), x, y, color, scale=0.03,
                             align=TextNode.ARight)
            y -= 0.04

    def _overlay_text(self, game, aspect):
        L = self.labels
        L.text("HULLÁM %d   LELŐVE %d   HALÁL %d" % (game.wave, game.kills, game.deaths), -aspect + 0.04, 0.92,
               WHITE, scale=0.034)
        L.text("H = súgó", -aspect + 0.04, 0.87, DIM, scale=0.03)
        y = 0.92
        for text, color, _ in self.killfeed:
            L.text(text, aspect - 0.04, y, color, scale=0.032, align=TextNode.ARight)
            y -= 0.045
        if game.banner:
            self.titles.text(game.banner, 0.0, 0.12, WHITE, scale=0.08, align=TextNode.ACenter)
        if game.sub_banner:
            y = 0.03 if game.banner else 0.62
            self.labels.text(game.sub_banner, 0.0, y, WHITE, scale=0.04, align=TextNode.ACenter)
