// Browser entry point: asset loading, camera, input, game flow and the main loop (port of dogfight/game.py,
// camera.py and controls.py).
import { THREE, V, add, sub, mul, dot, cross, len, norm, clamp, DEG, qaxis, qmul, qlook, fwdOf, upOf, xform, rng } from './util.js';
import { AIRCRAFT, BANDITS, PLAYER_MISSILES, BANDIT_MISSILES, IR, buildLoadout, loadoutLimits } from './specs.js';
import { Terrain } from './terrain.js';
import { Aircraft, World } from './sim.js';
import { PlayerPilot, AIPilot } from './ai.js';
import { Models, SceneView } from './render.js';
import { parseGLB } from './glb.js';
import { HUD } from './hud.js';
import { CockpitDisplays } from './mfd.js';
import { Tutorial } from './tutorial.js';
import { Sounds } from './audio.js';

// The fight happens on the far side of the map: the enemies live in the combat zone and never attack anyone
// near the home base (safe area), so taking off and landing is quiet.  An air start puts the player on the
// way there, just outside the zone.
const ZONE = { x: -14000, y: 16000, r: 16000 }, ENGAGE_MARGIN = 12000, SAFE_RADIUS = 14000;
const TAKEOFF_HINT = 'FELSZÁLLÁS: Shift tartva = gáz 100%-ig, újra Shift = utánégető  ·  ~280 km/h-nál emeld az egeret (vagy S)  ·  G = futómű';
const WAVE_DELAY = 5, FIRST_WAVE_DELAY = 25, RELOAD_TIME = 10, MAX_ENEMIES = 6, THROTTLE_RATE = 0.4, MAX_AB = 1.1;
const CHASE_DISTANCE = 26, CHASE_HEIGHT = 5.5;
const HEAD_YAW = 160 * DEG;                           // a pilot turns the head at most 160 degrees each way
const CAM_FIX = qaxis(V(1, 0, 0), Math.PI / 2);     // three.js cameras look down -Z with +Y up
// cockpit view: the head turns about the neck (the eyes sit in front of it), and to look back the pilot
// leans forward and to the side, past the ejection seat's head box
const NECK = V(0, -0.09, -0.06), EYE_FROM_NECK = V(0, 0.09, 0.06), LEAN_SIDE = 0.18, LEAN_FWD = 0.12;
const COCKPIT_SHIFT = 0.13;                           // cockpit view: picture shifted down by this part of its height
const STICK_GAIN = 0.045;                             // mouse joystick: px of mouse travel per full deflection / sensitivity
const STICK_DEADZONE = 0.07;                          // mouse joystick: neutral band around the centre
const ease = (t) => { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };

const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------------ camera
class FlightCamera {
  constructor(camera, terrain) {
    this.camera = camera; this.terrain = terrain; this.eye = V(0, 2.4, 1.1);
    this.sensitivity = 0.09; this.invertY = false;
    this.aim = new THREE.Quaternion(); this.look = new THREE.Quaternion();
    this.freeLook = false; this.cockpit = false; this.position = V(); this.fov = 70; this.phase = 0; this.zoom = 0;
    this.headYaw = 0; this.headPitch = 0; this.headG = 0;   // cockpit: head turn (rad) and G sag (m)
    this.panelLook = false; this.panel = null; this.panelFov = 30;   // N: look down at the displays (panel point, aircraft frame)
  }
  reset(ac) { this.aim = qlook(ac.forward); this.look = this.aim.clone(); }
  aimDirection() { return fwdOf(this.aim); }
  setFreeLook(on) {
    if (on && !this.freeLook && !this.cockpit) this.look = this.aim.clone();
    if (on) this.panelLook = false;
    this.freeLook = on;
  }
  rotate(yawDeg, pitchDeg) {
    if (this.cockpit && this.freeLook) {             // turning the head inside the cockpit
      this.headYaw = clamp(this.headYaw + yawDeg * DEG, -HEAD_YAW, HEAD_YAW);
      this.headPitch = clamp(this.headPitch + pitchDeg * DEG, -0.9, 1.4);
      return;
    }
    let q = this.freeLook ? this.look : this.aim;
    q = qmul(qaxis(V(0, 0, 1), yawDeg * DEG), q);           // yaw around world up
    q = qmul(q, qaxis(V(1, 0, 0), pitchDeg * DEG)).normalize();  // pitch around local right
    if (this.freeLook) this.look = q; else this.aim = q;
  }
  mouseDelta(dx, dy) { this.rotate(-dx * this.sensitivity, -dy * this.sensitivity * (this.invertY ? -1 : 1)); }
  static level(q, dt, rate = 1.6) {
    const fwd = fwdOf(q);
    if (Math.abs(fwd.z) > 0.96) return q;
    const up = upOf(q), want = norm(sub(V(0, 0, 1), mul(fwd, fwd.z)));
    const ang = Math.atan2(dot(cross(up, want), fwd), dot(up, want));
    const step = Math.abs(ang) < 2.5 ? clamp(ang, -rate * dt, rate * dt) : ang * Math.min(1, rate * 0.6 * dt);
    return qmul(q, qaxis(V(0, 1, 0), step));
  }
  update(dt, ac) {
    this.aim = FlightCamera.level(this.aim, dt);
    if (this.freeLook) this.look = FlightCamera.level(this.look, dt);
    if (!ac) return;
    let view = this.freeLook ? this.look : this.aim;
    if (this.cockpit && ac.alive) {
      // the pilot's head is part of the jet: the view rolls, pitches and yaws with it.  Under G the head
      // sags (positive) or lifts (negative) a few centimetres.
      if (!this.freeLook) {
        // the head comes back to the front, or with N turns down to the instrument panel
        const k = Math.exp(-6 * dt), p = this.panelLook && this.panel ? Math.atan2(this.panel.z - this.eye.z, this.panel.y - this.eye.y) : 0;
        this.headYaw *= k; this.headPitch = p + (this.headPitch - p) * k;
      }
      const sag = clamp(-(ac.fm.gLoad - 1) * 0.012, -0.06, 0.09);
      this.headG += (sag - this.headG) * Math.min(1, dt * 6);
      const head = qmul(qaxis(V(0, 0, 1), this.headYaw), qaxis(V(1, 0, 0), this.headPitch));
      view = qmul(ac.quat, head);
      const lean = ease((Math.abs(this.headYaw) - 40 * DEG) / (100 * DEG));
      const body = V(-Math.sign(this.headYaw) * LEAN_SIDE * lean, LEAN_FWD * lean, this.headG);
      const eye = add(add(this.eye, NECK), add(xform(head, EYE_FROM_NECK), body));
      this.position = add(ac.pos, xform(ac.quat, eye));
    } else {
      const dist = ac.alive ? CHASE_DISTANCE : 70;
      this.position = add(sub(ac.pos, mul(fwdOf(view), dist)), mul(upOf(view), CHASE_HEIGHT));
      const ground = this.terrain.height(this.position.x, this.position.y);
      if (this.position.z < ground + 3) this.position.z = ground + 3;
    }
    const cam = this.camera;
    cam.position.copy(this.position);
    let q = qmul(view, CAM_FIX);
    this.phase += dt;
    let shake = 0;
    if (ac.alive && ac.gun.firing) shake += 0.07;
    if (ac.alive && ac.fm.gLoad > 6) shake += (ac.fm.gLoad - 6) * 0.03;
    if (shake > 0) q = qmul(q, new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.sin(this.phase * 53) * shake * DEG, Math.sin(this.phase * 71) * shake * DEG, 0)));
    cam.quaternion.copy(q);
    const panel = this.cockpit && this.panelLook && ac.alive;
    const target = panel ? this.panelFov : [this.cockpit ? 75 : 70, 45, 28][this.zoom];
    this.fov += (target - this.fov) * Math.min(1, dt * 8);
    if (Math.abs(cam.fov - this.fov) > 0.01) { cam.fov = this.fov; cam.updateProjectionMatrix(); }
    // cockpit: the picture is shifted (lens shift, no rotation) so the HUD sits above the screen centre and
    // the displays on the instrument panel fit at the bottom
    const shift = this.cockpit && ac.alive && !panel ? COCKPIT_SHIFT : 0;
    this.shift = (this.shift || 0) + (shift - (this.shift || 0)) * Math.min(1, dt * 8);
    if (this.shift > 0.002) cam.setViewOffset(1000 * cam.aspect, 1000, 0, 1000 * this.shift, 1000 * cam.aspect, 1000);
    else if (cam.view && cam.view.enabled) cam.clearViewOffset();
    cam.updateMatrixWorld();
  }
}

// ------------------------------------------------------------------- input
class Input {
  constructor(el) {
    this.el = el; this.held = new Set(); this.codeName = new Map(); this.mouse = [false, false, false];
    this.handlers = {}; this.dx = 0; this.dy = 0; this.mx = 0; this.my = 0; this.inside = false;
    addEventListener('keydown', (e) => {
      const name = Input.name(e);
      if (['Space', 'Tab', 'F1', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code) || name.length === 1) {
        if (!e.ctrlKey && !e.metaKey) e.preventDefault();
      }
      if (e.code === 'ControlLeft' || e.code === 'ControlRight') {
        if (!this.held.has('control') && this.handlers.press) this.handlers.press('control');
        this.codeName.set(e.code, 'control'); this.held.add('control'); return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      this.codeName.set(e.code, name);
      if (!this.held.has(name) && this.handlers.press) this.handlers.press(name);
      this.held.add(name);
    });
    addEventListener('keyup', (e) => { const n = this.codeName.get(e.code) || Input.name(e); this.held.delete(n); this.codeName.delete(e.code); });
    const releaseAll = () => { this.held.clear(); this.codeName.clear(); this.mouse = [false, false, false]; };
    addEventListener('blur', releaseAll);
    document.addEventListener('visibilitychange', releaseAll);
    document.addEventListener('pointerlockchange', releaseAll);
    // a lost Shift key-up (Windows Sticky Keys popup, alt-tab...) would leave the throttle (afterburner)
    // running up forever: every key and mouse event carries the real Shift state, so resync from it
    const syncShift = (e) => { if (!e.shiftKey) this.held.delete('shift'); if (!e.ctrlKey) this.held.delete('control'); };
    addEventListener('keydown', syncShift, true);
    addEventListener('mousedown', syncShift, true);
    el.addEventListener('mousedown', (e) => {
      if (e.button === 1) e.preventDefault();          // middle button: no autoscroll
      this.mouse[e.button] = true; if (this.handlers.mousedown) this.handlers.mousedown(e);
    });
    addEventListener('mouseup', (e) => { this.mouse[e.button] = false; });
    addEventListener('mousemove', (e) => {
      syncShift(e);
      this.dx += e.movementX || 0; this.dy += e.movementY || 0;
      const r = el.getBoundingClientRect();
      this.mx = (e.clientX - r.left) / r.width * 2 - 1; this.my = (e.clientY - r.top) / r.height * 2 - 1;
    });
    el.addEventListener('mouseenter', () => { this.inside = true; });
    el.addEventListener('mouseleave', () => { this.inside = false; });
    el.addEventListener('contextmenu', (e) => e.preventDefault());
    let wheelAcc = 0, wheelTime = 0;
    el.addEventListener('wheel', (e) => {
      e.preventDefault();
      // touchpads send many small events: one weapon step per notch-sized amount, at most ~6 per second
      const now = performance.now();
      if (now - wheelTime > 400) wheelAcc = 0;
      wheelAcc += e.deltaMode === 1 ? e.deltaY * 33 : e.deltaY;
      if (Math.abs(wheelAcc) >= 40 && now - wheelTime > 150) {
        if (this.handlers.wheel) this.handlers.wheel(Math.sign(wheelAcc));
        wheelAcc = 0; wheelTime = now;
      }
    }, { passive: false });
  }
  static name(e) {
    if (e.code && e.code.startsWith('Digit')) return e.code.slice(5);
    if (e.key && e.key.length === 1 && /[a-z]/i.test(e.key)) return e.key.toLowerCase();
    if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') return 'shift';
    return e.code || e.key;
  }
  key(k) { return this.held.has(k); }
  axis(pos, neg) { const p = this.key(pos), n = this.key(neg); return p && !n ? 1 : n && !p ? -1 : null; }
  takeDelta() { const d = [this.dx, this.dy]; this.dx = 0; this.dy = 0; return d; }
}

// ----------------------------------------------------------------- gamepad
// Standard mapping (Xbox / PlayStation pads): left stick flies the jet directly (stick back = nose up),
// right stick moves the aim circle like the mouse, triggers = throttle, RB gun, A missile, LB flares,
// X radar lock, B IR lock, Y next weapon, D-pad up gear / down air brake / left view / right zoom,
// Start = pause, Back = help, L3 held = look around with the right stick.
const PAD = { A: 0, B: 1, X: 2, Y: 3, LB: 4, RB: 5, LT: 6, RT: 7, BACK: 8, START: 9, L3: 10, R3: 11, UP: 12, DOWN: 13, LEFT: 14, RIGHT: 15 };
class Pad {
  constructor() { this.prev = null; this.connected = false; this.name = ''; }
  poll() {
    const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
    const gp = pads.find((p) => p.mapping === 'standard') || pads[0];
    this.connected = !!gp;
    if (!gp) { this.pressed = () => false; this.held = () => false; return false; }
    this.name = gp.id;
    const now = gp.buttons.map((b) => b.pressed || b.value > 0.5);
    const prev = this.prev || now;              // first poll: buttons already down are not new presses
    this.held = (i) => !!now[i];
    this.pressed = (i) => !!now[i] && !prev[i];
    this.value = (i) => (gp.buttons[i] ? gp.buttons[i].value : 0);
    const dz = (v) => { const a = Math.abs(v); return a < 0.12 ? 0 : Math.sign(v) * Math.pow((a - 0.12) / 0.88, 1.5); };
    this.lx = dz(gp.axes[0] || 0); this.ly = dz(gp.axes[1] || 0);
    this.rx = dz(gp.axes[2] || 0); this.ry = dz(gp.axes[3] || 0);
    this.prev = now;
    return true;
  }
}

// -------------------------------------------------------------------- game
class Game {
  constructor(assets, opts) {
    this.opts = opts;
    const canvas = $('view');
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance', logarithmicDepthBuffer: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.outputEncoding = THREE.sRGBEncoding;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.terrain = new Terrain(assets.terrain);
    this.world = new World(this.terrain, Math.floor(Math.random() * 1e9));
    this.rnd = this.world.rnd;
    this.models = new Models(assets.f16, { viper: assets.viper, aggressor: assets.aggressor, terrain: assets.terrainTex, cockpit: assets.cockpitTex }, assets.glb, AIRCRAFT);
    this.view = new SceneView(this.renderer, this.models, this.terrain, this.world);
    this.cam = new FlightCamera(this.view.camera, this.terrain);
    this.hud = new HUD($('hud'));
    this.sounds = new Sounds(0.7);
    this.input = new Input(canvas);
    this.pad = new Pad();
    addEventListener('gamepadconnected', (e) => this.hud.message(`KONTROLLER CSATLAKOZTATVA`, 'good', 3, 'pad'));
    this.state = Game.freshState();
    this.player = null; this.pilot = null; this.helpVisible = false; this.locked = false; this.inMenu = false;
    this.stick = { x: 0, y: 0, idle: 0 };
    this.input.handlers.press = (k) => this.onKey(k);
    this.input.handlers.wheel = (s) => this.cycleWeapon(s);
    this.input.handlers.mousedown = (e) => {
      if (this.state.paused && !this.helpVisible) this.resume();
      else if (e.button === 1) this.cam.zoom = (this.cam.zoom + 1) % 3;     // middle button: zoom steps
    };
    document.addEventListener('pointerlockchange', () => {
      this.locked = document.pointerLockElement === canvas;
      if (!this.locked && !this.state.paused && this.lockWanted) this.pause();
    });
    document.addEventListener('pointerlockerror', () => { this.locked = false; this.lockWanted = false; });
    const field = this.terrain.airfield;
    this.nav = { zone: { ...ZONE, engage: ZONE.r + ENGAGE_MARGIN }, base: { x: field.x, y: field.y, r: SAFE_RADIUS }, wave: 0, enemies: 0 };
    this.spawnPlayer();
    this.startTutorial();
    this.resize();
    addEventListener('resize', () => this.resize());
    this.last = performance.now();
    this.fpsAcc = 0; this.fpsN = 0;
    requestAnimationFrame((t) => this.frame(t));
  }

  static freshState() {
    return { wave: 0, kills: 0, deaths: 0, banner: '', subBanner: '', paused: true, waveTimer: FIRST_WAVE_DELAY, waveActive: false };
  }
  // a new match on the same scene (terrain, models and the renderer stay)
  newMatch(opts) {
    this.opts = opts;
    const v = this.view;
    for (const vis of v.visuals.values()) v.scene.remove(vis.root);
    for (const mv of v.missileVis.values()) v.scene.remove(mv.mesh);
    v.visuals.clear(); v.missileVis.clear();
    v.smoke.list = []; v.fire.list = [];
    this.world = new World(this.terrain, Math.floor(Math.random() * 1e9));
    this.rnd = this.world.rnd; v.world = this.world;
    this.state = Game.freshState();
    this.hud.messages = []; this.hud.killfeed = [];
    this.cam.cockpit = false; this.cam.headYaw = 0; this.cam.headPitch = 0;
    this.stick = { x: 0, y: 0, idle: 0 };
    this.player = null;
    this.spawnPlayer();
    this.startTutorial();
  }
  // the optional guided flight (main menu -> Oktatás); no enemy waves while it runs
  startTutorial() {
    $('tutorial').hidden = true;
    this.tutorial = this.opts.tutorial ? new Tutorial(this) : null;
  }

  resize() {
    const w = innerWidth, h = innerHeight;
    this.renderer.setSize(w, h, false);
    this.view.camera.aspect = w / h; this.view.camera.updateProjectionMatrix();
  }

  // ---------------------------------------------------------------- spawning
  spawnPlayer() {
    const w = this.world;
    if (this.player) w.aircraft = w.aircraft.filter((a) => a !== this.player);
    const air = this.opts.airStart, field = this.terrain.airfield;
    let pos, heading = 0, speed = 0;
    if (air) {
      // between the base and the combat zone, heading for the zone
      const k = 0.45;
      pos = V(field.x + (ZONE.x - field.x) * k, field.y + (ZONE.y - field.y) * k, 4500);
      pos.z = Math.max(pos.z, this.terrain.height(pos.x, pos.y) + 1500); speed = 250;
      heading = Math.atan2(ZONE.x - pos.x, ZONE.y - pos.y) / DEG;
    } else {
      const [x, y, hdg] = field.startPosition();
      pos = V(x, y, 0); heading = hdg;
    }
    const spec = AIRCRAFT[this.opts.aircraft] || AIRCRAFT.f16;
    const ac = new Aircraft(spec, `Te (${spec.callsign} 1)`, 'blue', pos, heading, speed, { isPlayer: true, livery: 'viper', lockAssist: true,
      missiles: PLAYER_MISSILES, loadout: this.opts.loadout || 'default', rnd: rng(Math.floor(this.rnd() * 1e9)) });
    this.cam.eye = this.models.types[spec.model].eye.clone();
    this.cam.panel = this.models.types[spec.model].panel.clone();
    this.cam.panelFov = this.models.types[spec.model].panelFov;
    if (air) ac.controls.throttle = 0.95;
    else {
      ac.fm.placeOnGround(pos.x, pos.y, this.terrain.height(pos.x, pos.y), heading);
      ac.controls.throttle = 0;
      this.state.subBanner = TAKEOFF_HINT;
    }
    w.addAircraft(ac);
    this.player = ac; this.pilot = new PlayerPilot(ac);
    this.cam.reset(ac);
  }

  // a wave appears in the combat zone, on its far side from the player, facing the player's way in
  spawnWave() {
    const st = this.state, p = this.player, r = this.rnd;
    st.wave++;
    const count = Math.min(this.opts.enemies + st.wave - 1, MAX_ENEMIES);
    const from = norm(V(ZONE.x - p.pos.x, ZONE.y - p.pos.y, 0), V(0, 1, 0));
    const center = add(V(ZONE.x, ZONE.y, 0), mul(from, ZONE.r * 0.35));
    const side = V(from.y, -from.x, 0), area = { ...this.nav.zone, safe: this.nav.base };
    for (let i = 0; i < count; i++) {
      const pos = add(center, mul(side, (i - (count - 1) / 2) * 3500 + r.uniform(-800, 800)));
      pos.z = Math.max(r.uniform(3000, 7500), this.terrain.height(pos.x, pos.y) + 1500);
      const heading = Math.atan2(-from.x, -from.y) / DEG + r.uniform(-20, 20);
      const type = this.opts.enemyType === 'mixed' ? ['f16', 'fa18', 'f22'][Math.floor(r() * 3)] : (this.opts.enemyType || 'f16');
      const spec = BANDITS[type];
      const loadout = type === 'f16' ? 'default' : buildLoadout(spec, 2, 4).layout;
      const ac = new Aircraft(spec, `Bandita ${i + 1} (${spec.short})`, 'red', pos, heading, 240, { livery: 'viper', missiles: BANDIT_MISSILES, loadout, rnd: rng(Math.floor(r() * 1e9)) });
      new AIPilot(ac, this.opts.difficulty, area);
      this.world.addAircraft(ac);
    }
    st.waveActive = true;
    const toZone = Math.max(0, Math.hypot(ZONE.x - p.pos.x, ZONE.y - p.pos.y) - ZONE.r);
    this.hud.message(`${st.wave}. HULLÁM - ${count} ellenség a harci zónában${toZone > 1000 ? ` (${(toZone / 1000).toFixed(0)} km)` : ''}`, 'warn', 5);
  }
  enemiesAlive() { return this.world.aircraft.filter((a) => a.team !== 'blue' && a.alive); }

  // ------------------------------------------------------------------ input
  canAct() { return !this.state.paused && this.player && this.player.alive; }
  onKey(k) {
    if (this.inMenu) return;                          // the main menu is open: its buttons do the work
    if (k === 'h' || k === 'F1') { this.toggleHelp(); return; }
    if (k === 'Escape') { if (!this.state.paused) this.pause(); return; }
    if (k === 'p') { if (this.state.paused) this.resume(); else this.pause(); return; }
    if (k === 'Enter' || k === 'NumpadEnter') { if (this.tutorial) this.tutorial.enter(); else this.respawn(); return; }
    if (k === 'm') { this.hud.markers = !this.hud.markers; return; }
    if (k === 'v') { this.cam.cockpit = !this.cam.cockpit; this.cam.panelLook = false; return; }
    if (k === 'n') {
      if (!this.cam.cockpit) { this.cam.cockpit = true; this.cam.panelLook = true; } else this.cam.panelLook = !this.cam.panelLook;
      return;
    }
    if (k === 'j' || k === 'k' || k === 'l') {
      const vis = this.view.visuals.get(this.player);
      const page = vis && vis.displays ? vis.displays.cycle({ j: 'left', k: 'right', l: 'center' }[k]) : null;
      if (page) this.hud.message(`KIJELZŐ: ${page}`, 'info', 1, 'mfd');
      return;
    }
    if (!this.canAct()) return;
    if (k === 'shift') { this.throttleStep(1); return; }
    if (k === 'z' || k === 'control') { this.throttleStep(-1); return; }
    const p = this.player, msg = (t, l = 'info', d = 1.5) => this.hud.message(t, l, d);
    switch (k) {
      case 'Space': {
        const m = p.fireMissile(this.world);
        if (m) msg(m.pending ? `${m.spec.guidance === IR ? 'FOX 2' : 'FOX 3'} - fegyvertér nyílik` : m.spec.guidance === IR ? 'FOX 2' : 'FOX 3');
        break;
      }
      case 'f':
        if (!p.selectedSpec || p.selectedSpec.guidance !== IR) p.select('AIM-9M');
        if (p.irSeeker.locked) { p.toggleIrLock(this.world); msg('KERESŐ ELENGEDVE', 'info', 1.2); }
        else if (p.toggleIrLock(this.world)) msg('SEEKER LOCK - Space: indítás', 'good');
        else msg('Nincs ellenség az orr előtt (±30°)', 'warn');
        break;
      case 't': {
        // lock the enemy closest to where you are looking (mouse aim, or free look)
        const view = V(0, 0, -1).applyQuaternion(this.cam.camera.quaternion);
        const res = p.radar.quickLock(this.world, view);
        const t = { unlocked: ['UNLOCK', 'info'], locking: ['LOCKOLÁS...', 'info'], keep: ['Nincs másik cél', 'info'],
          none: ['Nincs cél a nézési irányban - fordulj felé', 'warn'] }[res];
        if (t) msg(t[0], t[1], 1.6);
        break;
      }
      case 'y': p.radar.cycleTarget(); break;
      case 'r': p.radar.togglePower(); msg(`RADAR ${p.radar.on ? 'BE' : 'KI'}`, 'info', 1.2); break;
      case '1': if (p.select('AIM-9M')) msg('AIM-9M', 'info', 1); break;
      case '2': if (p.select('AIM-120A')) msg('AIM-120A', 'info', 1); break;
      case 'Tab':
        if (p.toggleExtreme()) msg(p.extreme ? 'EXTRÉM MÓD BE - tolóerő-vektorálás, 9 G, teljes húzás = Cobra' : 'EXTRÉM MÓD KI', p.extreme ? 'warn' : 'info', 2.5);
        else if (p.spec.tvcAlways) msg('F-22: a tolóerő-vektorálás mindig be van kapcsolva', 'info');
        else msg('Extrém mód (tolóerő-vektorálás) csak az F-16-on van', 'warn');
        break;
      case 'g':
        if (p.toggleGear()) msg(`FUTÓMŰ ${p.fm.gearDown ? 'KI' : 'BE'}`);
        else msg('A földön nem húzható be a futómű', 'warn');
        break;
    }
  }
  applyInput(dt) {
    const inp = this.input, p = this.player, c = p.controls, cam = this.cam;
    const [dx, dy] = inp.takeDelta();
    // outside: the mouse moves the aim circle and the jet points its nose there.  In the cockpit the mouse
    // is the control stick itself (push = nose down, pull = nose up, sideways = roll), seen from the seat.
    const joystick = cam.cockpit && !cam.freeLook;
    if (joystick) this.flyStick(dt, dx, dy);
    else if (this.locked) cam.mouseDelta(dx, dy);
    else if (inp.inside && !this.state.paused) {
      // no pointer lock (e.g. blocked by the page): the cursor works as a joystick around the screen centre
      const dz = (v) => (Math.abs(v) < 0.06 ? 0 : (v - Math.sign(v) * 0.06) / 0.94);
      cam.rotate(-dz(inp.mx) * 95 * dt, -dz(inp.my) * 70 * dt * (cam.invertY ? -1 : 1));
    }
    const pad = this.pad.connected ? this.pad : null;
    if (pad) {
      cam.setFreeLook(pad.held(PAD.L3));
      cam.rotate(-pad.rx * 110 * dt, -pad.ry * 80 * dt * (cam.invertY ? -1 : 1));
    }
    this.pilot.aim = cam.aimDirection();
    this.pilot.pitch = inp.axis('s', 'w');      // S = nose up (pull), W = nose down (push)
    this.pilot.roll = inp.axis('d', 'a');
    this.pilot.yaw = inp.axis('e', 'q');
    if (joystick) {
      const dz = (v) => (Math.abs(v) < STICK_DEADZONE ? 0 : (v - Math.sign(v) * STICK_DEADZONE) / (1 - STICK_DEADZONE));
      if (this.pilot.pitch === null) this.pilot.pitch = dz(this.stick.y);
      if (this.pilot.roll === null) this.pilot.roll = dz(this.stick.x);
    } else { this.stick.x = 0; this.stick.y = 0; }
    cam.stick = joystick ? this.stick : null;
    if (pad && (pad.lx || pad.ly)) {            // left stick: direct control, stick back = nose up
      if (this.pilot.pitch === null) this.pilot.pitch = pad.ly;
      if (this.pilot.roll === null) this.pilot.roll = pad.lx;
    }
    // flying with the keys: the mouse aim point rides on the nose, so letting go does not yank the jet back
    if (this.pilot.manual) cam.aim = qlook(p.forward);
    const rt = pad ? pad.value(PAD.RT) > 0.5 : false, lt = pad ? pad.value(PAD.LT) > 0.5 : false;
    if (pad && pad.pressed(PAD.RT)) this.throttleStep(1);
    if (pad && pad.pressed(PAD.LT)) this.throttleStep(-1);
    this.throttleInput(dt, inp.key('shift') || rt, inp.key('z') || inp.key('control') || lt);
    const brake = inp.key('b') || (pad && pad.held(PAD.DOWN));
    c.airbrake = brake;
    c.brakes = brake && p.onGround;
    p.trigger = inp.mouse[0] || (pad && pad.held(PAD.RB));
    p.cmHold = inp.key('x') || (pad && pad.held(PAD.LB));
    if (!pad || !pad.held(PAD.L3)) cam.setFreeLook(inp.key('c') || inp.mouse[2]);
    if (pad) {
      if (pad.pressed(PAD.A)) this.onKey('Space');
      if (pad.pressed(PAD.X)) this.onKey('t');
      if (pad.pressed(PAD.B)) this.onKey('f');
      if (pad.pressed(PAD.Y)) this.cycleWeapon(1);
      if (pad.pressed(PAD.UP)) this.onKey('g');
      if (pad.pressed(PAD.LEFT)) this.onKey('v');
      if (pad.pressed(PAD.RIGHT)) this.cam.zoom = (this.cam.zoom + 1) % 3;
      if (pad.pressed(PAD.R3)) this.onKey('m');
    }
  }

  // Mouse joystick for the cockpit.  The stick stays exactly where you put it - nothing pulls it back to the
  // middle, so a slow turn or a long hard break can be held as long as you want.  A small dead zone around
  // the centre makes neutral easy to find (the gauge shows it: the dot turns green there).
  flyStick(dt, dx, dy) {
    const s = this.stick, inp = this.input, cam = this.cam, inv = cam.invertY ? -1 : 1;
    if (this.locked) {
      const k = cam.sensitivity * STICK_GAIN;
      s.x = clamp(s.x + dx * k, -1, 1); s.y = clamp(s.y + dy * k * inv, -1, 1);
    } else if (inp.inside && !this.state.paused) {   // no pointer lock: the cursor's offset from the centre is the stick
      const dz = (v) => (Math.abs(v) < 0.04 ? 0 : (v - Math.sign(v) * 0.04) / 0.96);
      s.x = clamp(dz(inp.mx) * 1.6, -1, 1); s.y = clamp(dz(inp.my) * 1.6 * inv, -1, 1);
    }
  }

  // Throttle like a real lever with a MIL detent: a tap moves it 5 % (taken from the key event itself, so
  // even a very short tap counts), holding slews it 40 %/s.  Going up it stops at 100 % (MIL); the
  // afterburner needs a new press of Shift there.  Down from AB goes straight to MIL.
  throttleStep(dir) {
    const c = this.player.controls;
    this.thrPress = performance.now();
    if (dir > 0) {
      if (c.throttle >= 0.999) { if (c.throttle < MAX_AB) { c.throttle = MAX_AB; this.hud.message('UTÁNÉGETŐ BE', 'warn', 1.2, 'thr'); } }
      else c.throttle = Math.min(1, Math.floor(c.throttle * 20 + 1e-6) / 20 + 0.05);
    } else if (c.throttle > 1.001) { c.throttle = 1; this.hud.message('UTÁNÉGETŐ KI', 'info', 1.2, 'thr'); }
    else c.throttle = Math.max(0, Math.ceil(c.throttle * 20 - 1e-6) / 20 - 0.05);
  }
  throttleInput(dt, up, down) {
    const c = this.player.controls, dir = up && !down ? 1 : down && !up ? -1 : 0;
    if (!dir || performance.now() - (this.thrPress || 0) < 300) return;
    if (dir > 0 && c.throttle < 1) c.throttle = Math.min(1, c.throttle + THROTTLE_RATE * dt);
    else if (dir < 0) c.throttle = c.throttle > 1 ? 1 : Math.max(0, c.throttle - THROTTLE_RATE * dt);
  }

  // ------------------------------------------------------------ pause/help
  pause() {
    this.state.paused = true;
    if (document.pointerLockElement) document.exitPointerLock();
    this.showOverlay(this.helpVisible || this.inMenu ? null : 'pause');
    const st = this.state;
    $('pausestats').textContent = `${st.wave}. hullám · lelőve ${st.kills} · halál ${st.deaths}`;
  }
  resume() {
    this.inMenu = false;
    $('menu').hidden = true;
    this.helpVisible = false;
    this.state.paused = false;
    this.showOverlay(null);
    this.sounds.resume();
    this.input.takeDelta();
    const cv = $('view');
    cv.focus();
    this.lockWanted = true;
    try {
      const r = cv.requestPointerLock && cv.requestPointerLock();
      if (r && r.catch) r.catch(() => { this.lockWanted = false; });
    } catch (e) { this.lockWanted = false; }
  }
  toggleHelp() {
    this.helpVisible = !this.helpVisible;
    if (this.helpVisible) { this.state.paused = true; if (document.pointerLockElement) document.exitPointerLock(); this.showOverlay('help'); }
    else this.showOverlay('pause');
  }
  showOverlay(which) {
    $('help').hidden = which !== 'help';
    $('pause').hidden = which !== 'pause';
  }
  cycleWeapon(dir) {
    if (!this.canAct()) return;
    const p = this.player;
    const keys = p.weaponKeys();
    const loaded = keys.filter((k) => p.missileCount(k) > 0);
    const list = loaded.length ? loaded : keys;
    if (!list.length) return;
    const i = list.indexOf(p.selected);
    const next = list[((i < 0 ? 0 : i + (dir > 0 ? 1 : -1)) % list.length + list.length) % list.length];
    if (next !== p.selected && p.select(next)) this.hud.message(`${next}  (${p.missileCount(next)})`, 'info', 1);
  }
  respawn() {
    if (this.player && !this.player.alive) {
      const st = this.state;
      st.banner = st.subBanner = '';
      this.spawnPlayer();
    }
  }

  // ------------------------------------------------------------------ loop
  frame(t) {
    requestAnimationFrame((tt) => this.frame(tt));
    const dt = clamp((t - this.last) / 1000, 0, 0.1);
    this.last = t;
    const st = this.state;
    if (this.pad.poll()) {
      if (!this.inMenu && this.pad.pressed(PAD.START)) { if (st.paused) this.resume(); else this.pause(); }
      if (!this.inMenu && this.pad.pressed(PAD.BACK)) this.toggleHelp();
      if (!this.player.alive && this.pad.pressed(PAD.A)) this.respawn();
    }
    if (!st.paused) {
      if (this.player.alive) this.applyInput(dt);
      else this.input.takeDelta();
      this.world.update(dt);
      if (this.tutorial) this.tutorial.update(dt);
      this.gameFlow(dt);
    } else this.input.takeDelta();
    for (const [kind, d] of this.world.drainEvents()) {
      this.view.handleEvent(kind, d);
      this.hud.handleEvent(kind, d, this.player);
      this.sounds.handleEvent(kind, d, this.player);
      this.onEvent(kind, d);
      if (this.tutorial) this.tutorial.onEvent(kind, d);
    }
    const sdt = st.paused ? 0 : dt;
    this.cam.update(sdt, this.player);
    this.view.cockpitView = this.cam.cockpit && this.player.alive;
    this.view.update(sdt, this.player);
    // the cockpit displays of the player's jet (drawn only while they can be seen)
    const nav = this.nav;
    nav.wave = st.wave; nav.enemies = this.enemiesAlive().length;
    this.hud.nav = nav; this.hud.tutorial = !!this.tutorial;
    const vis = this.view.visuals.get(this.player);
    if (vis && vis.screens && !vis.displays) vis.displays = new CockpitDisplays(this.player.spec, vis.screens);
    if (vis && vis.displays && this.view.cockpitView) vis.displays.update(sdt, this.player, this.world, nav);
    this.view.render();
    this.hud.update(dt, this.player, this.world, this.view.camera, this.cam, st);
    this.sounds.update(this.player, st.paused);
    this.fpsAcc += dt; this.fpsN++;
    if (this.fpsAcc > 1) { $('fps').textContent = `${Math.round(this.fpsN / this.fpsAcc)} FPS`; this.fpsAcc = 0; this.fpsN = 0; }
  }
  onEvent(kind, d) {
    if (kind !== 'kill') return;
    const st = this.state;
    if (d.victim === this.player) {
      st.deaths++;
      st.banner = d.weapon !== 'crash' ? 'LELŐTTEK!' : 'LEZUHANTÁL!';
      st.subBanner = this.tutorial ? 'Pár másodperc, és újra a levegőben vagy – a lecke elölről indul'
        : 'Enter: újraéledés  ·  Esc: menü (főmenü, új játék)';
    } else if (d.killer === this.player) st.kills++;
  }
  gameFlow(dt) {
    const st = this.state, p = this.player;
    if (!p.alive) return;
    const field = this.terrain.airfield;
    const airborne = !p.onGround && p.pos.z - this.terrain.height(p.pos.x, p.pos.y) > 150;
    if (st.subBanner === TAKEOFF_HINT && airborne) {
      st.subBanner = '';
      this.hud.message('SIKERES FELSZÁLLÁS - húzd be a futóművet (G)', 'good', 4);
    }
    if (!this.tutorial && st.waveActive && !this.enemiesAlive().length) {
      st.waveActive = false; st.waveTimer = WAVE_DELAY;
      this.hud.message('HULLÁM TELJESÍTVE - leszállhatsz a bázison újrafegyverezni', 'good', 5);
    }
    if (!this.tutorial && !st.waveActive && airborne) {
      st.waveTimer -= dt;
      if (st.waveTimer <= 0) this.spawnWave();
    }
    // arcade: every fired missile comes back on its rail RELOAD_TIME seconds later
    if (this.opts.mode === 'arcade') {
      for (const s of p.stations) {
        if (s.loaded) { s.reload = undefined; continue; }
        s.reload = (s.reload ?? RELOAD_TIME) - dt;
        if (s.reload <= 0) {
          s.loaded = true; s.reload = undefined; p.updateStores();
          if (!p.selected || p.missileCount(p.selected) === 0) p.select(s.key);
          this.hud.message(`${s.key} ÚJRATÖLTVE`, 'good', 1.5, 'reload');
        }
      }
    }
    // arcade: the gun and the flare / chaff dispensers refill too (full in 10 s, after a 2 s pause)
    if (this.opts.mode === 'arcade') {
      this.gunIdle = p.gun.firing ? 0 : (this.gunIdle || 0) + dt;
      this.cmIdle = p.cmHold ? 0 : (this.cmIdle || 0) + dt;
      const refill = (have, max, idle, key) => {
        if (have >= max || idle < 2) { this[key] = 0; return have; }
        this[key] = (this[key] || 0) + max / RELOAD_TIME * dt;
        const n = Math.floor(this[key]); this[key] -= n;
        return Math.min(max, have + n);
      };
      p.gun.ammo = refill(p.gun.ammo, p.spec.gun.ammo, this.gunIdle, 'ammoAcc');
      p.flares = refill(p.flares, p.spec.cm.flares, this.cmIdle, 'flareAcc');
      p.chaff = refill(p.chaff, p.spec.cm.chaff, this.cmIdle, 'chaffAcc');
    }
    // both modes: landing on the base (on the concrete, slowed down) rearms, refuels and repairs at once
    const needs = p.hp < p.spec.hp || p.fm.fuel < p.spec.internalFuel * 0.95 || p.gun.ammo < p.spec.gun.ammo ||
      p.stations.some((s) => !s.loaded) || p.flares < p.spec.cm.flares;
    if (p.onGround && p.speed < 25 && needs && field.onPaved(p.pos.x, p.pos.y)) {
      p.rearm(); p.hp = p.spec.hp; p.burning = false; p.fm.fuel = p.spec.internalFuel;
      for (const s of p.stations) s.reload = undefined;
      this.hud.message('ÚJRAFEGYVERZÉS, TANKOLÁS, JAVÍTÁS KÉSZ', 'good', 4, 'service');
    }
  }
}

// ----------------------------------------------------------------- loading
// the offline single-file build (tools/build_offline.py) carries every asset inline as a data: URI
const assetUrl = (name) => (window.DOGFIGHT_ASSETS && window.DOGFIGHT_ASSETS[name]) || `assets/${name}`;

async function fetchJSON(url, onDone) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  const j = await r.json(); onDone(); return j;
}
async function fetchGLB(url, onDone) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  const g = await parseGLB(await r.arrayBuffer()); onDone(); return g;
}
function loadTexture(url, onDone) {
  return new Promise((res, rej) => new THREE.TextureLoader().load(url, (t) => { onDone(); res(t); }, undefined, () => rej(new Error(url))));
}

async function boot() {
  const status = $('status'), bar = $('bar');
  if (!THREE) { status.textContent = 'A three.js nem töltődött be - ellenőrizd az internetkapcsolatot.'; return; }
  let done = 0;
  const tick = () => { done++; bar.style.width = `${done / 11 * 100}%`; };
  let assets;
  try {
    const [f16, terrain, viper, aggressor, terrainTex, cockpitTex, glbF16, glbFa18, glbF22, glbAim9, glbAim120] = await Promise.all([
      fetchJSON(assetUrl('f16.json'), tick), fetchJSON(assetUrl('terrain.json'), tick),
      loadTexture(assetUrl('livery_viper.jpg'), tick), loadTexture(assetUrl('livery_aggressor.jpg'), tick),
      loadTexture(assetUrl('terrain_color.jpg'), tick), loadTexture(assetUrl('cockpit.png'), tick),
      fetchGLB(assetUrl('f16.glb'), tick), fetchGLB(assetUrl('fa18.glb'), tick), fetchGLB(assetUrl('f22.glb'), tick),
      fetchGLB(assetUrl('aim9m.glb'), tick), fetchGLB(assetUrl('aim120c.glb'), tick)]);
    assets = { f16, terrain, viper, aggressor, terrainTex, cockpitTex, glb: { f16: glbF16, fa18: glbFa18, f22: glbF22, aim9m: glbAim9, aim120c: glbAim120 } };
  } catch (e) {
    status.textContent = 'Betöltési hiba: ' + e.message; console.error(e); return;
  }
  status.textContent = 'Kész!';
  $('loading').hidden = true;
  $('menu').hidden = false;
  // offer the one-file offline copy where a plain download link works (GitHub Pages or a local server)
  if (!window.DOGFIGHT_ASSETS && /github\.io$|^localhost$|^127\./.test(location.hostname)) $('download').hidden = false;
  // Loadout editor: how many AIM-9M and AIM-120A; the stations are filled like the real jet would carry them
  // (specs.js buildLoadout), the row of chips shows where each one hangs.
  const arms = { 'AIM-9M': 0, 'AIM-120A': 0 };
  const plane = () => AIRCRAFT[document.querySelector('input[name=plane]:checked').value];
  const defaults = (spec) => {
    const l = Object.values(spec.loadouts.default);
    arms['AIM-9M'] = l.filter((k) => k === 'AIM-9M').length; arms['AIM-120A'] = l.filter((k) => k === 'AIM-120A').length;
  };
  const showLoadout = () => {
    const spec = plane(), lim = loadoutLimits(spec);
    for (const key of ['AIM-9M', 'AIM-120A']) {
      const other = key === 'AIM-9M' ? 'AIM-120A' : 'AIM-9M';
      // a weapon can have as many as its stations, as long as the other one still fits on the rest
      arms[key] = clamp(arms[key], 0, Math.min(lim[key], lim.total - arms[other]));
    }
    let { layout, left } = buildLoadout(spec, arms['AIM-9M'], arms['AIM-120A']);
    while (left['AIM-9M'] > 0 || left['AIM-120A'] > 0) {          // did not fit: take back what is left over
      arms['AIM-9M'] -= left['AIM-9M']; arms['AIM-120A'] -= left['AIM-120A'];
      ({ layout, left } = buildLoadout(spec, arms['AIM-9M'], arms['AIM-120A']));
    }
    $('n9').textContent = arms['AIM-9M']; $('n120').textContent = arms['AIM-120A'];
    const nums = Object.keys(spec.stations).map(Number).sort((a, b) => a - b);
    $('stations').innerHTML = nums.map((n) => {
      const w = layout[n], cls = w === 'AIM-9M' ? 'st s9' : w === 'AIM-120A' ? 'st s120' : 'st';
      return `<span class="${cls}" title="${n}. állomás: ${w || 'üres'}"><i>${n}</i>${w === 'AIM-9M' ? '9M' : w === 'AIM-120A' ? '120' : '–'}</span>`;
    }).join('');
    const mass = Object.values(layout).reduce((m, k) => m + (k === 'AIM-9M' ? 86 : 152), 0);
    $('loadout-hint').textContent = `${arms['AIM-9M'] + arms['AIM-120A']} rakéta · ${mass} kg`;
    $('brand').textContent = spec.callsign;
    $('plane-hint').textContent = {
      fa18: '2 × F414 · 196 kN · nagy állásszög, lassabb energia',
      f22: '2 × F119 · 312 kN · lopakodó, belső fegyvertér, APG-77, max 8 G',
    }[spec.id] || '1 × F110 · 132 kN · 9 G, jobb tolóerő/tömeg';
  };
  for (const el of document.querySelectorAll('input[name=plane]')) el.addEventListener('change', () => { defaults(plane()); showLoadout(); });
  for (const [id, key, d] of [['m9', 'AIM-9M', -1], ['p9', 'AIM-9M', 1], ['m120', 'AIM-120A', -1], ['p120', 'AIM-120A', 1]]) {
    $(id).addEventListener('click', () => { arms[key] += d; showLoadout(); });
  }
  $('ld-default').addEventListener('click', () => { defaults(plane()); showLoadout(); });
  defaults(plane()); showLoadout();
  // The main menu starts a match, and the game can come back to it any time (Esc -> Főmenü), during a match
  // or after it: from there the match continues (Folytatás) or a new one starts on the same scene.
  const start = (airStart, tutorial = false) => {
    const difficulty = document.querySelector('input[name=diff]:checked').value;
    const enemies = Number($('enemies').value);
    const mode = document.querySelector('input[name=mode]:checked').value;
    const aircraft = document.querySelector('input[name=plane]:checked').value;
    const enemyType = document.querySelector('input[name=foe]:checked').value;
    const loadout = buildLoadout(AIRCRAFT[aircraft], arms['AIM-9M'], arms['AIM-120A']).layout;
    const opts = { airStart: airStart || tutorial, difficulty, enemies, mode: tutorial ? 'arcade' : mode, aircraft, enemyType, loadout, tutorial };
    $('menu').hidden = true;
    let game = window.game;
    if (game) game.newMatch(opts);
    else {
      try { game = new Game(assets, opts); }
      catch (e) { console.error(e); $('menu').hidden = false; $('menuerr').textContent = 'Hiba: ' + e.message + ' (WebGL szükséges)'; return; }
      window.game = game;
      game.onTutorialEnd = () => { showMenu(); $('current').textContent = 'Az oktatás véget ért. Folytatás = szabad repülés hullámokkal, vagy indíts új játékot.'; };
      $('sens').addEventListener('input', (e) => { game.cam.sensitivity = Number(e.target.value); });
      $('invert').addEventListener('change', (e) => { game.cam.invertY = e.target.checked; });
    }
    game.cam.sensitivity = Number($('sens').value);
    game.cam.invertY = $('invert').checked;
    game.resume();
  };
  const showMenu = () => {
    const game = window.game;
    if (!game) return;
    game.inMenu = true;
    game.pause();
    game.showOverlay(null);
    const st = game.state;
    $('continue').hidden = false;
    $('current').hidden = false;
    $('current').textContent = `Futó játék: ${st.wave}. hullám · lelőve ${st.kills} · halál ${st.deaths}` +
      (game.player && !game.player.alive ? ' · lelőttek, a Folytatás után Enter = újraéledés' : '');
    $('start-ground').classList.remove('primary');
    $('menu').hidden = false;
    $('continue').focus();
  };
  $('continue').addEventListener('click', () => window.game && window.game.resume());
  $('to-menu').addEventListener('click', (e) => { e.stopPropagation(); showMenu(); });
  $('resume').addEventListener('click', (e) => { e.stopPropagation(); if (window.game) window.game.resume(); });
  $('help-btn').addEventListener('click', (e) => { e.stopPropagation(); if (window.game) window.game.toggleHelp(); });
  for (const el of document.querySelectorAll('input[name=mode]')) {
    el.addEventListener('change', () => {
      $('mode-hint').textContent = el.value === 'arcade' ? 'rakéták 10 s alatt újratöltődnek' : 'újratöltés csak leszállás után';
    });
  }
  $('start-ground').addEventListener('click', () => start(false));
  // controller on the main menu: A = continue the match (or take off from the runway), X = start in the air,
  // B = take off from the runway (new match)
  const menuPad = new Pad();
  const menuPoll = () => {
    requestAnimationFrame(menuPoll);
    if ($('menu').hidden || !menuPad.poll()) return;
    if (menuPad.pressed(PAD.A)) { if (window.game) window.game.resume(); else start(false); }
    else if (menuPad.pressed(PAD.X)) start(true);
    else if (menuPad.pressed(PAD.B) && window.game) start(false);
  };
  requestAnimationFrame(menuPoll);
  $('start-air').addEventListener('click', () => start(true));
  $('start-tutorial').addEventListener('click', () => start(true, true));
  $('help').addEventListener('click', () => window.game && window.game.resume());
  $('fullscreen').addEventListener('click', (e) => {
    e.stopPropagation();
    const el = document.documentElement;
    if (document.fullscreenElement) document.exitFullscreen(); else if (el.requestFullscreen) el.requestFullscreen().catch(() => {});
  });
}

// leaving by accident (Ctrl+W while Ctrl is the throttle key) asks first
addEventListener('beforeunload', (e) => {
  if (window.game && !window.game.state.paused) { e.preventDefault(); e.returnValue = ''; }
});

boot();
