"""The Panda3D application: window, input, game flow (waves, respawn), main loop."""

import math
import random

from panda3d.core import (AntialiasAttrib, ClockObject, ModifierButtons, Vec3, WindowProperties, loadPrcFileData)

from .ai.pilot import AIPilot
from .audio import SoundBank
from .camera import FlightCamera
from .controls import InputReader, PlayerPilot
from .mathutil import safe_normalized
from .render.environment import Environment
from .render.scene import SceneRenderer
from .sim.aircraft import Aircraft
from .sim.specs import F16C, IR
from .sim.terrain import Terrain
from .sim.world import World
from .ui.fonts import Fonts
from .ui.help import HelpOverlay
from .ui.hud import HUD

PLAYER_START = Vec3(0.0, -26000.0, 4500.0)
WAVE_DELAY = 5.0
MAX_ENEMIES = 6


class GameState:
    def __init__(self):
        self.wave = 0
        self.kills = 0
        self.deaths = 0
        self.banner = ""
        self.sub_banner = ""
        self.paused = True
        self.wave_timer = 1.0
        self.wave_active = False


def configure(options):
    """Panda3D config - must run before ShowBase is created."""
    lines = [
        "window-title Dogfight - F-16C Viper",
        "win-size %d %d" % options.size,
        "fullscreen %s" % ("#t" if options.fullscreen else "#f"),
        "sync-video #t",
        "default-directnotify-level warning",
        "notify-level warning",
    ]
    if not options.no_aa:
        lines += ["framebuffer-multisample 1", "multisamples 4"]
    if options.mute:
        lines.append("audio-library-name null")
    if options.offscreen:
        lines += ["window-type offscreen", "load-display p3tinydisplay", "audio-library-name null"]
    loadPrcFileData("dogfight", "\n".join(lines))


class DogfightApp:
    def __init__(self, options):
        configure(options)
        from direct.showbase.ShowBase import ShowBase   # after the config is loaded

        self.options = options
        self.base = base = ShowBase()
        base.disableMouse()
        base.camLens.setNearFar(0.6, 160000.0)
        base.camLens.setFov(70)
        if not options.no_aa:
            base.render.setAntialias(AntialiasAttrib.MMultisample)
        if options.fps:
            base.setFrameRateMeter(True)
        # plain key names ("t" instead of "shift-t" while Shift is held for throttle)
        if getattr(base, "mouseWatcherNode", None) is not None:
            base.mouseWatcherNode.setModifierButtons(ModifierButtons())
            base.buttonThrowers[0].node().setModifierButtons(ModifierButtons())

        self.rng = random.Random(options.seed)
        self.fonts = Fonts(base.loader)
        self.terrain = Terrain()
        self.environment = Environment(base, self.terrain, cloud_count=options.clouds)
        self.world = World(self.terrain, seed=options.seed)
        self.scene = SceneRenderer(base, self.world)
        self.cam = FlightCamera(base, self.terrain, sensitivity=options.sensitivity, invert_y=options.invert_y)
        self.hud = HUD(base, self.fonts)
        self.help = HelpOverlay(base, self.fonts)
        self.sounds = SoundBank(base, volume=options.volume, enabled=not (options.mute or options.offscreen))
        self.input = InputReader(base)
        self.state = GameState()
        self.player = None
        self.pilot = None
        self._mouse_ready = False

        self.spawn_player()
        self._bind_keys()
        self._capture_mouse(not self.state.paused)
        base.taskMgr.add(self._update, "dogfight-update")

    # ------------------------------------------------------------- spawning
    def spawn_player(self, position=None, heading=0.0):
        if self.player is not None and self.player in self.world.aircraft:
            self.world.aircraft.remove(self.player)
        pos = Vec3(position if position is not None else PLAYER_START)
        pos.z = max(pos.z, self.terrain.height(pos.x, pos.y) + 1500.0)
        ac = Aircraft(F16C, "Te (Viper 1)", "blue", pos, heading, 250.0, loadout=self.options.loadout,
                      rng=self.rng, is_player=True, livery="viper")
        ac.controls.throttle = 0.95
        self.world.add_aircraft(ac)
        self.player = ac
        self.pilot = PlayerPilot(ac)
        self.cam.reset(ac)

    def spawn_wave(self):
        st = self.state
        st.wave += 1
        count = min(self.options.enemies + st.wave - 1, MAX_ENEMIES)
        p = self.player
        ahead = safe_normalized(Vec3(p.forward.x, p.forward.y, 0.0))
        center = p.pos + ahead * self.rng.uniform(32000.0, 40000.0)
        cx, cy = self.terrain.clamp_inside(center.x, center.y, margin=9000.0)
        side = Vec3(ahead.y, -ahead.x, 0.0)
        for i in range(count):
            offset = side * ((i - (count - 1) / 2.0) * 3500.0 + self.rng.uniform(-800, 800))
            pos = Vec3(cx, cy, 0) + offset
            pos.z = max(self.rng.uniform(3000.0, 7500.0), self.terrain.height(pos.x, pos.y) + 1500.0)
            to_player = p.pos - pos
            heading = math.degrees(math.atan2(to_player.x, to_player.y))
            ac = Aircraft(F16C, "Bandita %d" % (i + 1), "red", pos, heading, 240.0, loadout="default",
                          rng=random.Random(self.rng.random()), livery="aggressor")
            AIPilot(ac, skill=self.options.difficulty)
            self.world.add_aircraft(ac)
        st.wave_active = True
        self.hud.message("%d. HULLÁM - %d ellenség" % (st.wave, count), "warn", 4.0)

    def enemies_alive(self):
        return [a for a in self.world.aircraft if a.team != "blue" and a.alive]

    # ----------------------------------------------------------------- input
    def _bind_keys(self):
        b = self.base
        b.accept("space", self._fire_missile)
        b.accept("f", self._ir_lock)
        b.accept("t", self._radar_lock)
        b.accept("y", self._cycle_target)
        b.accept("r", self._radar_power)
        b.accept("1", self._select, ["AIM-9M"])
        b.accept("2", self._select, ["AIM-120A"])
        b.accept("v", self.cam.toggle_view)
        b.accept("m", self._toggle_markers)
        b.accept("h", self._toggle_help)
        b.accept("f1", self._toggle_help)
        b.accept("p", self._toggle_pause)
        b.accept("escape", self._escape)
        b.accept("enter", self._respawn)

    def _can_act(self):
        return not self.state.paused and self.player is not None and self.player.alive

    def _fire_missile(self):
        if not self._can_act():
            return
        m = self.player.fire_missile(self.world)
        if m is not None:
            self.hud.message("FOX 2" if m.spec.guidance == IR else "FOX 3", "info", 1.5)

    def _ir_lock(self):
        if not self._can_act():
            return
        p = self.player
        if p.selected_spec is None or p.selected_spec.guidance != IR:
            p.select("AIM-9M")
        if p.ir_seeker.locked:
            p.ir_seeker.unlock()
            self.hud.message("KERESŐ ELENGEDVE", "info", 1.2)
        elif p.toggle_ir_lock():
            self.hud.message("SEEKER LOCK", "good", 1.5)
        else:
            self.hud.message("Nincs hőforrás a keresőben", "warn", 1.5)

    def _radar_lock(self):
        if not self._can_act():
            return
        result = self.player.radar.lock_button()
        text = {"on": ("RADAR BE", "info"), "unlocked": ("UNLOCK", "info"), "locking": ("LOCKOLÁS...", "info"),
                "acm": ("ACM MÓD - célt az orr elé!", "warn"), "search": ("RADAR KERESÉS", "info")}.get(result)
        if text:
            self.hud.message(*text, duration=1.6)

    def _cycle_target(self):
        if self._can_act():
            self.player.radar.cycle_target()

    def _radar_power(self):
        if self._can_act():
            self.player.radar.toggle_power()
            self.hud.message("RADAR %s" % ("BE" if self.player.radar.on else "KI"), "info", 1.2)

    def _select(self, key):
        if self._can_act() and self.player.select(key):
            self.hud.message(key, "info", 1.0)

    def _toggle_markers(self):
        self.hud.show_markers = not self.hud.show_markers

    def _toggle_help(self):
        self.help.toggle()
        self.state.paused = self.help.visible
        self._capture_mouse(not self.state.paused)

    def _toggle_pause(self):
        if self.help.visible:
            self.help.set_visible(False)
        self.state.paused = not self.state.paused
        self._capture_mouse(not self.state.paused)

    def _escape(self):
        if self.state.paused and not self.help.visible:
            self.quit()
            return
        self.help.set_visible(False)
        self.state.paused = True
        self._capture_mouse(False)

    def _respawn(self):
        if self.player is not None and not self.player.alive:
            enemies = self.enemies_alive()
            start = Vec3(PLAYER_START)
            heading = 0.0
            if enemies:
                cx = sum(e.pos.x for e in enemies) / len(enemies)
                cy = sum(e.pos.y for e in enemies) / len(enemies)
                away = safe_normalized(Vec3(-cx, -cy, 0.0))
                if away.length() < 0.5:
                    away = Vec3(0, -1, 0)
                sx, sy = self.terrain.clamp_inside(cx + away.x * 35000.0, cy + away.y * 35000.0, 9000.0)
                start = Vec3(sx, sy, 4500.0)
                heading = math.degrees(math.atan2(cx - sx, cy - sy))
            self.spawn_player(start, heading)
            self.state.banner = ""
            self.state.sub_banner = ""

    def quit(self):
        self.sounds.stop_all()
        self.base.userExit()

    # ------------------------------------------------------------------ mouse
    def _capture_mouse(self, capture):
        if self.options.offscreen or self.base.win is None:
            return
        props = WindowProperties()
        props.setCursorHidden(capture)
        props.setMouseMode(WindowProperties.M_confined if capture else WindowProperties.M_absolute)
        self.base.win.requestProperties(props)
        self._mouse_ready = False

    def _read_mouse(self):
        win = self.base.win
        if self.options.offscreen or win is None or self.state.paused:
            return
        if not win.getProperties().getForeground():
            self._mouse_ready = False
            return
        cx = win.getXSize() // 2
        cy = win.getYSize() // 2
        pointer = win.getPointer(0)
        if self._mouse_ready and pointer.getInWindow():
            dx = pointer.getX() - cx
            dy = pointer.getY() - cy
            if dx or dy:
                self.cam.mouse_delta(dx, dy)
        win.movePointer(0, cx, cy)
        self._mouse_ready = True

    # ------------------------------------------------------------------ loop
    def _update(self, task):
        dt = min(ClockObject.getGlobalClock().getDt(), 0.1)
        st = self.state
        self._read_mouse()
        if not st.paused:
            if self.player.alive:
                self.input.apply(dt, self.pilot, self.cam)
            self.world.update(dt)
            self._game_flow(dt)
        for kind, data in self.world.drain_events():
            self.scene.handle_event(kind, data)
            self.hud.handle_event(kind, data, self.player)
            self.sounds.handle_event(kind, data, self.player)
            self._on_event(kind, data)

        self.cam.update(dt if not st.paused else 0.0, self.player, zoom=self.input.key("z"))
        self.scene.hide_player = self.cam.cockpit and self.player.alive
        self.scene.update(dt if not st.paused else 0.0, self.player)
        if st.paused and not self.help.visible:
            st.banner, st.sub_banner = "SZÜNET", "P: folytatás   Esc: kilépés   H: súgó"
        elif st.banner == "SZÜNET":
            st.banner = st.sub_banner = ""
        self.hud.update(dt, self.player, self.world, self.cam, st)
        self.sounds.update(self.player, paused=st.paused)
        return task.cont

    def _on_event(self, kind, data):
        st = self.state
        if kind != "kill":
            return
        victim = data["victim"]
        if victim is self.player:
            st.deaths += 1
            st.banner = "LELŐTTEK!" if data.get("weapon") != "crash" else "LEZUHANTÁL!"
            st.sub_banner = "Enter: újraéledés"
        elif data.get("killer") is self.player:
            st.kills += 1

    def _game_flow(self, dt):
        st = self.state
        if st.wave_active and not self.enemies_alive():
            st.wave_active = False
            st.wave_timer = WAVE_DELAY
            if self.player.alive:
                self.hud.message("HULLÁM TELJESÍTVE - újrafegyverzés", "good", 4.0)
        if not st.wave_active:
            st.wave_timer -= dt
            if st.wave_timer <= 0.0 and self.player.alive:
                if st.wave > 0:
                    self.player.rearm()
                    self.player.hp = self.player.spec.hp
                    self.player.burning = False
                    self.player.fm.fuel = self.player.spec.internal_fuel
                self.spawn_wave()

    def run(self):
        self.base.run()
