"""Keeps the 3D scene in sync with the simulation and spawns visual effects."""

import math

from panda3d.core import ColorBlendAttrib, LineSegs, TransparencyAttrib, Vec3

from ..mathutil import quat_look
from ..sim.guns import GUN_OFFSET
from .effects import SpriteSystem, soft_texture
from .models import ModelLibrary

WINGTIPS = (Vec3(-4.9, -2.4, 0.12), Vec3(4.9, -2.4, 0.12))
NOZZLE = Vec3(0.0, -7.45, 0.07)


class AircraftVisual:
    def __init__(self, parent, ac, models):
        self.ac = ac
        self.root = parent.attachNewNode("aircraft")
        self.body = models.aircraft(ac.livery)
        self.body.reparentTo(self.root)
        self.stores = {}
        for st in ac.stations:
            node = models.missile(st.key)
            node.reparentTo(self.root)
            node.setPos(st.mount)
            self.stores[st.number] = node
        self.flame = models.flame()
        self.flame.reparentTo(self.root)
        self.flame.setPos(NOZZLE)
        self.flame.hide()
        self.trail_timer = 0.0

    def update(self, dt, visible, time):
        ac = self.ac
        if ac.crashed or not visible:
            self.root.hide()
            return
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
        engine = ac.engine_setting
        if ac.alive and engine > 1.0:
            ab = (engine - 1.0) / 0.1
            flicker = 1.0 + 0.08 * math.sin(time * 61.0) + 0.05 * math.sin(time * 23.0)
            self.flame.show()
            self.flame.setScale(0.85 + 0.15 * ab, (2.0 + 3.2 * ab) * flicker, 0.85 + 0.15 * ab)
        else:
            self.flame.hide()

    def destroy(self):
        self.root.removeNode()


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
        self.aircraft = {}
        self.missiles = {}
        self.tracers = None
        self.hide_player = False
        self._time = 0.0

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
        # aircraft
        present = set()
        for ac in world.aircraft:
            present.add(ac)
            vis = self.aircraft.get(ac)
            if vis is None:
                vis = self.aircraft[ac] = AircraftVisual(self.root, ac, self.models)
            visible = not (self.hide_player and ac is player)
            vis.update(dt, visible, self._time)
            self._aircraft_effects(ac, dt, vis, visible)
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
