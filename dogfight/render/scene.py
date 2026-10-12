"""Keeps the 3D scene in sync with the simulation and spawns visual effects."""

import math

from panda3d.core import (BitMask32, Camera, CardMaker, ColorBlendAttrib, LineSegs, NodePath, PerspectiveLens,
                          TransparencyAttrib, Vec3)

from ..mathutil import quat_look
from ..sim.guns import GUN_OFFSET
from .effects import SpriteSystem, soft_texture
from .f16_model import ControlSurfaces
from .models import ModelLibrary

WINGTIPS = (Vec3(-4.9, -2.4, 0.12), Vec3(4.9, -2.4, 0.12))
STRAKE_VORTEX = (Vec3(-0.92, 2.2, 0.22), Vec3(0.92, 2.2, 0.22), Vec3(-1.15, 1.4, 0.2), Vec3(1.15, 1.4, 0.2))
NAV_LIGHTS = ((Vec3(-0.62, 2.0, -0.78), (1.0, 0.15, 0.1, 1.0)), (Vec3(0.62, 2.0, -0.78), (0.2, 1.0, 0.3, 1.0)),
              (Vec3(0.0, -6.70, 3.74), (1.0, 1.0, 0.95, 1.0)))
STROBE = Vec3(0.0, -5.85, 3.80)
NOZZLE = Vec3(0.0, -7.45, 0.07)
MAIN_MASK = BitMask32.bit(0)
COCKPIT_MASK = BitMask32.bit(1)


class AircraftVisual:
    def __init__(self, parent, ac, models, glow=None):
        self.ac = ac
        self.layer = parent.attachNewNode("aircraft_layer")     # camera masks live here (cockpit pass)
        self.in_cockpit_pass = False
        self.root = self.layer.attachNewNode("aircraft")
        self.body = models.aircraft(ac.livery)
        self.body.reparentTo(self.root)
        self.surfaces = ControlSurfaces(self.body)
        self.lights = []
        self.strobe = None
        if glow is not None:
            for pos, color in NAV_LIGHTS:
                self.lights.append(self._lamp(glow, pos, color, 0.7))
            self.strobe = self._lamp(glow, STROBE, (1.0, 1.0, 1.0, 1.0), 1.6)
        self.stores = {}
        for st in ac.stations:
            node = models.missile(st.key)
            node.reparentTo(self.root)
            node.setPos(st.mount)
            self.stores[st.number] = node
        self.gear = models.gear()
        self.gear.reparentTo(self.root)
        self.flame = models.flame()
        self.flame.reparentTo(self.root)
        self.flame.setPos(NOZZLE)
        self.flame.hide()
        self.trail_timer = 0.0

    def _lamp(self, glow, pos, color, size):
        lamp = glow.copyTo(self.root)
        lamp.setPos(pos)
        lamp.setScale(size)
        lamp.setColor(*color)
        return lamp

    def update(self, dt, visible, time):
        ac = self.ac
        if ac.crashed or not visible:
            self.root.hide()
            return
        if ac.alive:
            fm = ac.fm
            c = ac.controls
            flaps = fm.gear_pos * min(1.0, max(0.0, (125.0 - fm.ias) / 25.0))
            self.surfaces.update(dt, c.pitch, c.roll, c.yaw, math.degrees(fm.alpha), flaps,
                                 1.0 if (c.airbrake and not ac.on_ground) else 0.0, ac.on_ground)
        if self.strobe is not None:
            phase = (time + (id(ac) % 97) * 0.13) % 1.2
            if phase < 0.06 or 0.18 < phase < 0.24:
                self.strobe.show()
            else:
                self.strobe.hide()
        self.root.show()
        self.root.setPos(ac.pos)
        self.root.setQuat(ac.quat)
        for st in ac.stations:
            node = self.stores.get(st.number)
            if node is not None:
                if st.loaded:
                    node.show()
                else:
                    node.hide()
        gear = ac.fm.gear_pos
        if gear < 0.03:
            self.gear.hide()
        else:
            self.gear.show()
            self.gear.setScale(1.0, 1.0, gear)        # simple "fold up into the belly" animation
        engine = ac.engine_setting
        if ac.alive and engine > 1.0:
            ab = (engine - 1.0) / 0.1
            flicker = 1.0 + 0.08 * math.sin(time * 61.0) + 0.05 * math.sin(time * 23.0)
            self.flame.show()
            self.flame.setScale(0.85 + 0.15 * ab, (2.0 + 3.2 * ab) * flicker, 0.85 + 0.15 * ab)
        else:
            self.flame.hide()

    def set_cockpit_pass(self, on):
        """Draw this aircraft only in the near cockpit pass (own aircraft in cockpit view)."""
        if on == self.in_cockpit_pass:
            return
        self.in_cockpit_pass = on
        if on:
            self.layer.hide(MAIN_MASK)
            self.layer.showThrough(COCKPIT_MASK)
        else:
            self.layer.show(MAIN_MASK)
            self.layer.hide(COCKPIT_MASK)

    def destroy(self):
        self.layer.removeNode()


class MissileVisual:
    def __init__(self, parent, missile, models):
        self.m = missile
        self.root = models.missile(missile.spec.name.split()[0])
        self.root.reparentTo(parent)
        self.last_puff = Vec3(missile.pos)

    def update(self):
        m = self.m
        self.root.setPos(m.pos)
        self.root.setQuat(quat_look(m.dir))

    def destroy(self):
        self.root.removeNode()


class SceneRenderer:
    def __init__(self, base, world, models=None):
        self.base = base
        self.world = world
        self.models = models or ModelLibrary()
        self.root = base.render.attachNewNode("scene")
        soft = soft_texture(64, 1.4, "smoke")
        glow = soft_texture(64, 2.2, "glow")
        self.smoke = SpriteSystem(self.root, soft, additive=False, max_count=1400, sort=10, name="smoke")
        self.fire = SpriteSystem(self.root, glow, additive=True, max_count=700, sort=30, name="fire")
        self.glow = self._glow_card(soft_texture(32, 2.4, "navlight"))
        self.aircraft = {}
        self.missiles = {}
        self.tracers = None
        self.cockpit_view = False
        self._time = 0.0
        self._setup_cockpit_pass(base)

    def _setup_cockpit_pass(self, base):
        """A second display region draws the own aircraft (cockpit) with a near plane of a few centimetres
        after clearing depth, so the instrument panel is not clipped by the main camera's near plane."""
        self.base = base
        self.cockpit_region = None
        if base.win is None:
            return
        base.cam.node().setCameraMask(MAIN_MASK)
        base.render.hide(COCKPIT_MASK)
        self.cockpit_lens = PerspectiveLens()
        self.cockpit_lens.setNearFar(0.03, 400.0)
        cam = Camera("cockpit_cam", self.cockpit_lens)
        cam.setCameraMask(COCKPIT_MASK)
        cam_np = base.camera.attachNewNode(cam)
        dr = base.win.makeDisplayRegion()
        dr.setSort(5)
        dr.setClearDepthActive(True)
        dr.setCamera(cam_np)
        dr.setActive(False)
        self.cockpit_region = dr

    @staticmethod
    def _glow_card(texture):
        cm = CardMaker("glow")
        cm.setFrame(-0.5, 0.5, -0.5, 0.5)
        card = NodePath(cm.generate())
        card.setTexture(texture)
        card.setBillboardPointEye()
        card.setLightOff(1)
        card.setDepthWrite(False)
        card.setTransparency(TransparencyAttrib.MAlpha)
        card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha,
                                             ColorBlendAttrib.OOne))
        card.setBin("fixed", 25)
        return card

    def reset(self):
        for v in self.aircraft.values():
            v.destroy()
        for v in self.missiles.values():
            v.destroy()
        self.aircraft.clear()
        self.missiles.clear()
        self.smoke.clear()
        self.fire.clear()

    # --------------------------------------------------------------- events
    def handle_event(self, kind, data):
        if kind == "explosion":
            self.explosion(data["pos"], data.get("size", 1.0), data.get("ground", False))
        elif kind == "hit":
            for _ in range(3):
                self.fire.spawn(data["pos"], Vec3(*(self._rand3(20.0))), life=0.18, size=(1.5, 3.5),
                                color=((1.0, 0.85, 0.5, 1.0), (1.0, 0.4, 0.1, 0.0)))
            self.smoke.spawn(data["pos"], None, life=1.2, size=(2.0, 6.0),
                             color=((0.3, 0.3, 0.3, 0.6), (0.4, 0.4, 0.4, 0.0)))
        elif kind == "impact":
            self.smoke.spawn(data["pos"], Vec3(0, 0, 6), life=1.5, size=(3.0, 9.0),
                             color=((0.55, 0.48, 0.38, 0.7), (0.6, 0.55, 0.45, 0.0)))
        elif kind == "chaff":
            ch = data["chaff"]
            for _ in range(3):
                self.smoke.spawn(ch.pos, ch.vel * 0.2 + Vec3(*self._rand3(4.0)), life=ch.life, size=(2.0, 12.0),
                                 color=((0.75, 0.78, 0.82, 0.35), (0.8, 0.82, 0.85, 0.0)), drag=1.5)
        elif kind == "launch":
            m = data["missile"]
            for _ in range(4):
                self.smoke.spawn(m.pos, m.vel * 0.9 + Vec3(*self._rand3(6.0)), life=1.6, size=(2.0, 8.0),
                                 color=((0.85, 0.85, 0.85, 0.6), (0.9, 0.9, 0.9, 0.0)), drag=2.0)

    def explosion(self, pos, size=1.0, ground=False):
        for _ in range(int(8 * size) + 4):
            self.fire.spawn(pos + Vec3(*self._rand3(3.0 * size)), Vec3(*self._rand3(25.0 * size)),
                            life=0.5 + 0.5 * self.world.rng.random(), size=(4.0 * size, 22.0 * size),
                            color=((1.0, 0.75, 0.35, 1.0), (0.9, 0.25, 0.05, 0.0)), drag=2.5)
        smoke_col = (0.25, 0.23, 0.21, 0.75) if not ground else (0.35, 0.3, 0.25, 0.85)
        for _ in range(int(10 * size) + 4):
            self.smoke.spawn(pos + Vec3(*self._rand3(4.0 * size)), Vec3(*self._rand3(12.0 * size)),
                             life=4.0 + 3.0 * self.world.rng.random(), size=(8.0 * size, 40.0 * size),
                             color=(smoke_col, (0.45, 0.43, 0.42, 0.0)), drag=0.8, rise=2.0 if ground else 0.5)

    def _rand3(self, scale):
        r = self.world.rng
        return (r.uniform(-scale, scale), r.uniform(-scale, scale), r.uniform(-scale, scale))

    # --------------------------------------------------------------- update
    def update(self, dt, player=None):
        self._time += dt
        world = self.world
        if self.cockpit_region is not None:
            self.cockpit_region.setActive(self.cockpit_view)
            if self.cockpit_view:
                self.cockpit_lens.setFov(self.base.camLens.getFov())
        # aircraft
        present = set()
        for ac in world.aircraft:
            present.add(ac)
            vis = self.aircraft.get(ac)
            if vis is None:
                vis = self.aircraft[ac] = AircraftVisual(self.root, ac, self.models, self.glow)
            own_cockpit = self.cockpit_view and ac is player
            vis.set_cockpit_pass(own_cockpit)
            vis.update(dt, True, self._time)
            self._aircraft_effects(ac, dt, vis, not own_cockpit)
        for ac in [a for a in self.aircraft if a not in present]:
            self.aircraft.pop(ac).destroy()

        # missiles
        present = set()
        for m in world.missiles:
            present.add(m)
            vis = self.missiles.get(m)
            if vis is None:
                vis = self.missiles[m] = MissileVisual(self.root, m, self.models)
            vis.update()
            if m.burning:
                tail = m.pos - m.dir * (m.spec.length * 0.5)
                self.fire.spawn(tail, m.vel, life=0.05, size=(1.6, 1.0),
                                color=((1.0, 0.8, 0.5, 1.0), (1.0, 0.5, 0.2, 0.0)))
                step = (m.pos - vis.last_puff).length()
                if step > 7.0:
                    n = min(int(step / 7.0), 12)
                    for k in range(n):
                        p = vis.last_puff + (tail - vis.last_puff) * ((k + 1) / n)
                        a = 0.75 * m.spec.smoke
                        self.smoke.spawn(p, Vec3(*self._rand3(1.5)), life=5.0, size=(1.5, 7.0),
                                         color=((0.92, 0.92, 0.92, a), (0.95, 0.95, 0.95, 0.0)))
                    vis.last_puff = Vec3(tail)
        for m in [x for x in self.missiles if x not in present]:
            self.missiles.pop(m).destroy()

        # flares
        for f in world.flares:
            k = f.intensity / f.peak
            self.fire.spawn(f.pos, None, life=0.06, size=(5.0 * k + 1.0, 4.0 * k + 1.0),
                            color=((1.0, 0.95, 0.8, 1.0), (1.0, 0.7, 0.4, 0.6)))
            if self.world.rng.random() < 0.5:
                self.smoke.spawn(f.pos, None, life=2.0, size=(1.0, 4.0),
                                 color=((0.95, 0.95, 0.95, 0.35), (1, 1, 1, 0.0)))

        self._draw_tracers()
        self.smoke.update(dt)
        self.fire.update(dt)

    def _aircraft_effects(self, ac, dt, vis, visible):
        if ac.crashed:
            return
        quat = ac.quat
        if ac.burning or ac.damaged:
            vis.trail_timer -= dt
            if vis.trail_timer <= 0.0:
                vis.trail_timer = 0.04
                tail = ac.pos + quat.xform(Vec3(0, -6.0, 0.3))
                if ac.burning:
                    self.fire.spawn(tail, ac.vel * 0.7, life=0.35, size=(4.0, 8.0),
                                    color=((1.0, 0.6, 0.2, 0.9), (0.8, 0.2, 0.05, 0.0)), drag=3.0)
                    self.smoke.spawn(tail, ac.vel * 0.5, life=7.0, size=(4.0, 22.0),
                                     color=((0.12, 0.11, 0.1, 0.8), (0.3, 0.3, 0.3, 0.0)), drag=2.0)
                else:
                    self.smoke.spawn(tail, ac.vel * 0.5, life=3.5, size=(2.0, 10.0),
                                     color=((0.45, 0.45, 0.45, 0.5), (0.6, 0.6, 0.6, 0.0)), drag=2.0)
        if not ac.alive or not visible:
            return
        # vortices off the strakes at high angle of attack (the classic F-16 look)
        alpha = math.degrees(ac.fm.alpha)
        if alpha > 13.0 and ac.speed > 70.0:
            a = 0.38 * min(1.0, (alpha - 13.0) / 9.0)
            for src in STRAKE_VORTEX:
                self.smoke.spawn(ac.pos + quat.xform(src), ac.vel * 0.9, life=0.45, size=(0.7, 2.8),
                                 color=((1, 1, 1, a), (1, 1, 1, 0.0)), drag=1.5)
        # wingtip vortices when pulling hard
        if ac.fm.g_load > 5.5 and ac.speed > 120.0:
            a = min(0.45, (ac.fm.g_load - 5.5) * 0.12)
            for tip in WINGTIPS:
                self.smoke.spawn(ac.pos + quat.xform(tip), ac.vel * 0.85, life=0.7, size=(0.5, 1.4),
                                 color=((1, 1, 1, a), (1, 1, 1, 0.0)), drag=2.0)
        # muzzle flash
        if ac.gun.firing:
            self.fire.spawn(ac.pos + quat.xform(GUN_OFFSET + Vec3(0, 0.6, 0)), ac.vel, life=0.04, size=(1.2, 2.2),
                            color=((1.0, 0.85, 0.5, 1.0), (1.0, 0.5, 0.1, 0.0)))

    def _draw_tracers(self):
        if self.tracers is not None:
            self.tracers.removeNode()
            self.tracers = None
        bullets = [b for b in self.world.bullets if b.tracer]
        if not bullets:
            return
        ls = LineSegs("tracers")
        ls.setThickness(2.0)
        for b in bullets:
            ls.setColor(1.0, 0.85, 0.35, 1.0)
            ls.moveTo(b.pos)
            ls.setColor(1.0, 0.45, 0.1, 0.0)
            ls.drawTo(b.pos - b.vel * 0.014)
        self.tracers = self.root.attachNewNode(ls.create())
        self.tracers.setLightOff(1)
        self.tracers.setTransparency(TransparencyAttrib.MAlpha)
        self.tracers.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha,
                                                     ColorBlendAttrib.OOne))
        self.tracers.setDepthWrite(False)
        self.tracers.setBin("fixed", 40)
