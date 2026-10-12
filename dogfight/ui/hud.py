"""Head-up display in War Thunder style.

* white circle  = where the mouse wants the aircraft to fly (mouse aim)
* green cross   = where the nose / gun points
* small circle with wings = flight path marker (where the aircraft actually goes)
* green square  = radar lock (STT), amber blinking brackets = acquiring
* circle that follows the target = AIM-9 seeker head
* circle with a dot = gun lead indicator (needs a radar lock)
"""

import math

from panda3d.core import Point2, Point3, TextNode, Vec3

from ..mathutil import DEG, angle_between, clamp, heading_deg, safe_normalized
from ..sim.guns import gun_lead
from ..sim.missile import launch_zone, time_to_impact
from ..sim.radar import ACM, STT
from ..sim.specs import ARH, IR
from .colors import AMBER, CYAN, DIM, ENEMY, GREEN, RED, WHITE
from .draw import Canvas, TextPool
from .scopes import draw_radar, draw_rwr

MESSAGE_COLORS = {"good": GREEN, "warn": AMBER, "bad": RED, "info": WHITE}


class HUD:
    def __init__(self, base, fonts):
        self.base = base
        self.fonts = fonts
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
    def message(self, text, kind="info", duration=2.5):
        for m in self.messages:
            if m[0] == text:
                m[2] = duration
                return
        self.messages.append([text, MESSAGE_COLORS.get(kind, WHITE), duration])
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

        if player is not None and player.alive:
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
        aim = self.project(cam.position + cam.aim_direction() * 3000.0)
        if aim is not None and not cam.free_look:
            c.circle(aim[0], aim[1], 0.022, WHITE, segments=24)
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
        radar = ac.radar
        for tgt in world.aircraft:
            if tgt is ac or not tgt.alive or tgt.team == ac.team:
                continue
            dist = (tgt.pos - ac.pos).length()
            if dist > 25000.0:
                continue
            p = self.project(tgt.pos)
            if p is None:
                continue
            x, y = p
            if tgt is not radar.locked:
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
            if p is not None:
                c.rect(p[0], p[1], 0.03, 0.03, color)
                rel = radar.track_pos - ac.pos
                closure = -(radar.track_vel - ac.vel).dot(safe_normalized(rel))
                self.labels.text("%.1f km" % (rel.length() / 1000.0), p[0] + 0.04, p[1] + 0.01, color, scale=0.028)
                self.labels.text("Vc %+d" % (closure * 3.6), p[0] + 0.04, p[1] - 0.025, color, scale=0.028)
                if radar.lost_time > 0:
                    self.labels.text("MEM", p[0] - 0.04, p[1] + 0.04, AMBER, scale=0.028)
            else:
                self.edge_arrow(radar.track_pos, GREEN)
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
                    elif seeker.candidate is not None:
                        color = GREEN if int(self.time * 10) % 2 == 0 else WHITE
                        c.circle(p[0], p[1], 0.04, color, segments=24)
                    else:
                        c.circle(p[0], p[1], 0.04, DIM, segments=24)
        self._dlz_bar(ac, spec, dt)

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
        thr = fm.engine
        thr_text = "AB" if thr > 1.0 else "%3d%%" % (thr * 100)
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
        if ac.controls.airbrake:
            L.text("SPD BRK", x, y - 0.30, AMBER)

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
        y = -0.66
        parts = []
        for key in ac.weapon_keys():
            n = ac.missile_count(key)
            parts.append(("[%s x%d]" if key == ac.selected else " %s x%d ") % (key, n))
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

    def _warnings(self, ac, world):
        T = self.titles
        y = 0.5
        blink = int(self.time * 4) % 2 == 0
        ahead = ac.pos + ac.vel * 4.0
        terrain = world.terrain
        if (ahead.z < terrain.height(ahead.x, ahead.y) + 60.0
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
        if ac.fm.ias < 70.0:
            T.text("SPEED LOW", 0.0, y, AMBER, scale=0.045, align=TextNode.ACenter)
            y -= 0.07
        if 0 < ac.fm.fuel < 400.0:
            T.text("BINGO FUEL", 0.0, y, AMBER, scale=0.045, align=TextNode.ACenter)
        # messages
        my = 0.33
        for text, color, _ in self.messages:
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
            self.labels.text(game.sub_banner, 0.0, 0.03, WHITE, scale=0.045, align=TextNode.ACenter)
