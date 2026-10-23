// Browser entry point: asset loading, camera, input, game flow and the main loop (port of dogfight/game.py,
// camera.py and controls.py).
import { THREE, V, add, sub, mul, dot, cross, len, norm, clamp, DEG, qaxis, qmul, qlook, fwdOf, upOf, xform, rng, copy } from './util.js';
import { AIRCRAFT, BANDITS, TRAINERS, PLAYER_MISSILES, BANDIT_MISSILES, IR, buildLoadout, loadoutLimits, PLANE_GROUPS, missilesFor, WEAPON_CLASS } from './specs.js';
import { Terrain } from './terrain.js';
import { Aircraft, World } from './sim.js';
import { PlayerPilot, AIPilot, WingmanPilot } from './ai.js';
import { Models, SceneView } from './render.js';
import { parseGLB } from './glb.js';
import { HUD } from './hud.js';
import { CockpitDisplays } from './mfd.js';
import { Tutorial } from './tutorial.js';
import { Sounds } from './audio.js';
import { Career, ACHIEVEMENTS, killPoints, weaponLabel, isGun, formatTime } from './career.js';
import { Voice } from './voice.js';
import { TouchControls, touchDevice } from './touch.js';
import { Hangar } from './hangar.js';
import { HangarUI } from './shopui.js';
import { Music } from './music.js';
import { keyEditor, buildMap } from './keys.js';
import { Race, fmtTime, RACE_RINGS } from './race.js';
import { Carrier, DECK_Z } from './carrier.js';
import { buildWorld, PLACES } from './world.js';
import { Radio } from './radio.js';
import { MapPicker } from './mappick.js';
import { CareerMode } from './careermode.js';
import { Base, Lobby } from './base.js';

// The fight happens on the far side of the map: the enemies live in the combat zone and never attack anyone
// near the home base (safe area), so taking off and landing is quiet.  An air start puts the player on the
// way there, just outside the zone.
const ZONE = { x: -14000, y: 16000, r: 16000 }, ENGAGE_MARGIN = 12000, SAFE_RADIUS = 14000;
const TAKEOFF_HINT_NOAB = 'FELSZÁLLÁS: Shift tartva = gáz 100%-ig  ·  felemelkedési sebességnél emeld az egeret (vagy S)  ·  G = futómű';
const TAKEOFF_HINT = 'FELSZÁLLÁS: Shift tartva = gáz 100%-ig, újra Shift = utánégető  ·  ~280 km/h-nál emeld az egeret (vagy S)  ·  G = futómű';
const CAT_HINT = 'KATAPULT: adj teljes gázt (Shift tartva, 100%), és a katapult kilő az orr felé  ·  utána húzd az orrot (S), G = futómű';
const SPLASH = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
const WAVE_DELAY = 5, FIRST_WAVE_DELAY = 25, RELOAD_TIME = 10, MAX_ENEMIES = 6, THROTTLE_RATE = 0.4, MAX_AB = 1.1;
const CHASE_DISTANCE = 26, CHASE_HEIGHT = 5.5;
const HEAD_YAW = 160 * DEG;                           // a pilot turns the head at most 160 degrees each way
const CAM_FIX = qaxis(V(1, 0, 0), Math.PI / 2);     // three.js cameras look down -Z with +Y up
// cockpit view: the head turns about the neck (the eyes sit in front of it), and to look back the pilot
// leans forward and to the side, past the ejection seat's head box
const NECK = V(0, -0.09, -0.06), EYE_FROM_NECK = V(0, 0.09, 0.06), LEAN_SIDE = 0.18, LEAN_FWD = 0.12;
const COCKPIT_SHIFT = 0.13;                           // cockpit view: picture shifted down by this part of its height
const STICK_GAIN = 0.045;                             // mouse joystick: px of mouse travel per full deflection / sensitivity
const SENS_BASE = 0.09;                               // "100 %" on the sensitivity sliders
const STICK_DEADZONE = 0.07;                          // mouse joystick: neutral band around the centre
const ease = (t) => { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };

const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------------ camera
// the ejection seat and the parachute: a short rocket ride up, the drogue, then the canopy opens and the pilot
// comes down at ~6 m/s, drifting with the wind; on the ground the canopy collapses
class Parachute {
  constructor(scene, pos, vel, up) {
    this.scene = scene; this.pos = pos.clone(); this.vel = vel.clone().addScaledVector(up, 45); this.t = 0; this.landed = false;
    const g = this.group = new THREE.Group();
    const canopyMat = new THREE.MeshStandardMaterial({ color: 0xd8742c, roughness: 0.8, side: THREE.DoubleSide });
    const white = new THREE.MeshStandardMaterial({ color: 0xe9e6dc, roughness: 0.8, side: THREE.DoubleSide });
    const canopy = this.canopy = new THREE.Group();
    for (let k = 0; k < 12; k++) {                     // gores in two colours
      const gore = new THREE.Mesh(new THREE.SphereGeometry(4.2, 4, 8, k * Math.PI / 6, Math.PI / 6, 0, Math.PI / 2.4), k % 2 ? canopyMat : white);
      canopy.add(gore);
    }
    canopy.rotation.x = Math.PI / 2; canopy.position.z = 7.5;
    const lines = new THREE.BufferGeometry(), lp = [];
    for (let k = 0; k < 12; k++) { const a = k / 12 * Math.PI * 2; lp.push(0, 0, 0.9, Math.cos(a) * 3.3, Math.sin(a) * 3.3, 7.5 + 0.6); }
    lines.setAttribute('position', new THREE.Float32BufferAttribute(lp, 3));
    canopy.userData.lines = new THREE.LineSegments(lines, new THREE.LineBasicMaterial({ color: 0x333333 }));
    const body = new THREE.Mesh(new THREE.CapsuleGeometry ? new THREE.CapsuleGeometry(0.25, 1.1, 4, 8) : new THREE.CylinderGeometry(0.25, 0.25, 1.4, 8),
      new THREE.MeshStandardMaterial({ color: 0x4a5236, roughness: 0.9 }));
    body.rotation.x = Math.PI / 2; body.position.z = 0.1;
    const helmet = new THREE.Mesh(new THREE.SphereGeometry(0.17, 12, 8), new THREE.MeshStandardMaterial({ color: 0x55595c, roughness: 0.4 }));
    helmet.position.z = 0.95;
    g.add(body, helmet, canopy, canopy.userData.lines);
    canopy.visible = false; canopy.userData.lines.visible = false;
    g.position.copy(this.pos);
    scene.add(g);
  }
  update(dt, terrain) {
    if (!dt) return;
    this.t += dt;
    const ground = terrain.height(this.pos.x, this.pos.y);
    if (this.landed) return;
    const open = this.t > 2.2;
    if (open && !this.canopy.visible) { this.canopy.visible = true; this.canopy.userData.lines.visible = true; this.canopy.scale.set(0.2, 0.2, 0.2); }
    if (this.canopy.visible && this.canopy.scale.x < 1) { const s = Math.min(1, this.canopy.scale.x + dt * 1.2); this.canopy.scale.set(s, s, s); }
    const k = open ? 0.9 : 0.12;                       // drag
    this.vel.x += (2.5 - this.vel.x) * Math.min(1, k * dt);          // drift with a light wind
    this.vel.y += (1.5 - this.vel.y) * Math.min(1, k * dt);
    this.vel.z += -9.81 * dt;
    if (open) this.vel.z += (-6 - this.vel.z) * Math.min(1, 1.6 * dt);
    else this.vel.z -= this.vel.z * Math.min(1, 0.12 * dt);
    this.pos.addScaledVector(this.vel, dt);
    if (this.pos.z <= Math.max(ground, 0) + 0.2) {
      this.pos.z = Math.max(ground, 0) + 0.2; this.landed = true; this.vel.set(0, 0, 0);
      this.canopy.rotation.x = 0.2; this.canopy.position.set(4, 0, 0.5); this.canopy.scale.set(1, 1, 0.15); this.canopy.userData.lines.visible = false;
    }
    this.group.position.copy(this.pos);
  }
  dispose() { this.scene.remove(this.group); }
}

class FlightCamera {
  constructor(camera, terrain) {
    this.camera = camera; this.terrain = terrain; this.eye = V(0, 2.4, 1.1);
    this.sensitivity = SENS_BASE * 0.6; this.stickSens = 0.6; this.invertY = false;
    this.aim = new THREE.Quaternion(); this.look = new THREE.Quaternion();
    this.freeLook = false; this.cockpit = false; this.position = V(); this.fov = 70; this.phase = 0; this.zoom = 0;
    this.headYaw = 0; this.headPitch = 0; this.headG = 0;   // cockpit: head turn (rad) and G sag (m)
    this.panelLook = false; this.panel = null; this.panelFov = 30;   // N: look down at the displays (panel point, aircraft frame)
    this.baseFov = 70;                                  // settings: field of view outside (the cockpit gets +5)
    this.follow = null; this.followLabel = '';          // missile cam / kill cam: {pos, dir, dist, height}
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
  // on foot (base.js): the eyes of the walker
  walkView(dt) {
    const w = this.walker, cam = this.camera;
    const view = qmul(qaxis(V(0, 0, 1), w.yaw), qaxis(V(1, 0, 0), w.pitch));
    this.position = w.eye; cam.position.copy(this.position);
    cam.quaternion.copy(qmul(view, CAM_FIX));
    this.fov += (this.baseFov - this.fov) * Math.min(1, dt * 8);
    if (Math.abs(cam.fov - this.fov) > 0.01) { cam.fov = this.fov; cam.updateProjectionMatrix(); }
    if (cam.view && cam.view.enabled) cam.clearViewOffset();
    this.shift = 0;
    cam.updateMatrixWorld();
  }
  update(dt, ac) {
    if (this.walker && this.walker.active) { this.walkView(dt); return; }
    this.aim = FlightCamera.level(this.aim, dt);
    if (this.freeLook) this.look = FlightCamera.level(this.look, dt);
    if (!ac) return;
    let view = this.freeLook ? this.look : this.aim;
    const f = this.follow;
    if (f) {
      // missile cam / kill cam: behind the followed object, looking where it goes
      view = qlook(f.dir);
      this.position = add(sub(f.pos, mul(f.dir, f.dist)), mul(upOf(view), f.height));
      const ground = this.terrain.height(this.position.x, this.position.y);
      if (this.position.z < ground + 3) this.position.z = ground + 3;
    } else if (this.cockpit && ac.alive) {
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
    if (this.kick > 0) { shake += this.kick * 0.6; this.kick = Math.max(0, this.kick - dt * 1.6); }   // a blast nearby
    if (shake > 0) q = qmul(q, new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.sin(this.phase * 53) * shake * DEG, Math.sin(this.phase * 71) * shake * DEG, 0)));
    cam.quaternion.copy(q);
    const panel = this.cockpit && this.panelLook && ac.alive && !f;
    const b = this.baseFov;
    const target = panel ? this.panelFov : f ? b : [this.cockpit ? b + 5 : b, b * 0.64, b * 0.4][this.zoom];
    this.fov += (target - this.fov) * Math.min(1, dt * 8);
    if (Math.abs(cam.fov - this.fov) > 0.01) { cam.fov = this.fov; cam.updateProjectionMatrix(); }
    // cockpit: the picture is shifted (lens shift, no rotation) so the HUD sits above the screen centre and
    // the displays on the instrument panel fit at the bottom
    const shift = this.cockpit && ac.alive && !panel && !f ? COCKPIT_SHIFT : 0;
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
      const name = this.tr(Input.name(e));
      if (['Space', 'Tab', 'F1', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code) || name.length === 1) {
        if (!e.ctrlKey && !e.metaKey) e.preventDefault();
      }
      if (e.code === 'ControlLeft' || e.code === 'ControlRight') {
        if (!this.held.has('control') && this.handlers.press) this.handlers.press('control');
        this.codeName.set(e.code, 'control'); this.held.add('control'); return;
      }
      if (e.ctrlKey && e.code === 'KeyE') { e.preventDefault(); if (this.handlers.press) this.handlers.press('eject'); return; }   // the ejection handle
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      this.codeName.set(e.code, name);
      if (!this.held.has(name) && this.handlers.press) this.handlers.press(name);
      this.held.add(name);
    });
    addEventListener('keyup', (e) => {
      const n = this.codeName.get(e.code) || this.tr(Input.name(e));
      if (this.held.has(n) && this.handlers.release) this.handlers.release(n);
      this.held.delete(n); this.codeName.delete(e.code);
    });
    const releaseAll = () => { this.held.clear(); this.codeName.clear(); this.mouse = [false, false, false]; };
    addEventListener('blur', releaseAll);
    document.addEventListener('visibilitychange', releaseAll);
    document.addEventListener('pointerlockchange', releaseAll);
    // a lost Shift key-up (Windows Sticky Keys popup, alt-tab...) would leave the throttle (afterburner)
    // running up forever: every key and mouse event carries the real Shift state, so resync from it
    const syncShift = (e) => { if (!e.shiftKey && !this.shiftRemapped) this.held.delete('shift'); if (!e.ctrlKey) this.held.delete('control'); };
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
  // key remapping (settings): a pressed key is translated to the default key of its action
  tr(n) { return this.map && n in this.map ? this.map[n] : n; }
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
  constructor() { this.prev = null; this.connected = false; this.name = ''; this.gp = null; this.rumbleOn = true; this.rumbleUntil = 0; }
  // force feedback (Chrome / Edge: dual-rumble).  strong = low-frequency motor, weak = high-frequency motor
  rumble(strong, weak, ms) {
    const a = this.gp && this.gp.vibrationActuator, now = performance.now();
    if (!a || !this.rumbleOn || !a.playEffect) return;
    if (now < this.rumbleUntil && strong < 0.5) return;          // a strong effect is not cut short by a light one
    this.rumbleUntil = now + ms;
    try { a.playEffect('dual-rumble', { startDelay: 0, duration: ms, strongMagnitude: Math.min(1, strong), weakMagnitude: Math.min(1, weak) }).catch(() => {}); } catch (e) { /* not supported */ }
  }
  poll() {
    const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
    const gp = pads.find((p) => p.mapping === 'standard') || pads[0];
    this.connected = !!gp; this.gp = gp || null;
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
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.terrain = new Terrain(assets.terrain);
    this.islandData = assets.terrain; this.place = null;
    this.carrier = new Carrier(this.terrain);                 // CVN-80, 15 km south of the base (its deck is ground)
    this.world = new World(this.terrain, Math.floor(Math.random() * 1e9));
    this.rnd = this.world.rnd;
    this.models = new Models(assets.f16, { viper: assets.viper, aggressor: assets.aggressor, terrain: assets.terrainTex, cockpit: assets.cockpitTex }, assets.glb, { ...AIRCRAFT, ...TRAINERS, ...BANDITS });
    this.view = new SceneView(this.renderer, this.models, this.terrain, this.world);
    this.view.scene.add(this.carrier.build(this.models));
    this.view.carrierParked = this.carrier.parked;
    this.cam = new FlightCamera(this.view.camera, this.terrain);
    this.base = new Base(this);
    this.hud = new HUD($('hud'));
    this.sounds = new Sounds(0.7);
    this.input = new Input(canvas);
    this.pad = new Pad();
    this.career = window.dogfightCareer || new Career();
    this.voice = new Voice();
    this.radio = new Radio(this);
    this.touch = new TouchControls((act) => this.touchTap(act));
    this.touchMode = 'auto'; this.missileCam = false; this.killCam = null; this.wingman = null;
    this.threats = new Set(); this.hitBy = new Set(); this.rumbleT = 0;
    this.hangar = window.dogfightHangar || new Hangar();
    this.bt = { charge: 1, active: 0 }; this.race = null; this.prevPos = null; this.realFps = { n: 0, t: performance.now() };
    addEventListener('gamepadconnected', (e) => this.hud.message(`KONTROLLER CSATLAKOZTATVA`, 'good', 3, 'pad'));
    this.state = Game.freshState();
    this.player = null; this.pilot = null; this.helpVisible = false; this.locked = false; this.inMenu = false;
    this.stick = { x: 0, y: 0, idle: 0 };
    this.input.handlers.press = (k) => this.onKey(k);
    // the radio key: tap = list / type, hold = talk
    this.input.handlers.release = (k) => { if (k === 'i' && !this.inMenu && this.radioDown) { this.radioDown = false; this.radio.keyUp(); } };
    this.input.handlers.wheel = (s) => this.cycleWeapon(s);
    this.input.handlers.mousedown = (e) => {
      if (this.state.paused && !this.helpVisible) this.resume();
      else if (e.button === 1) this.cam.zoom = (this.cam.zoom + 1) % 3;     // middle button: zoom steps
      else if (this.touchOn() && this.player && (!this.player.alive || this.player.ejected || (this.race && this.race.finished))) this.respawn();   // touch: a tap respawns
    };
    document.addEventListener('pointerlockchange', () => {
      this.locked = document.pointerLockElement === canvas;
      if (!this.locked && !this.state.paused && this.lockWanted) this.pause();
    });
    document.addEventListener('pointerlockerror', () => { this.locked = false; this.lockWanted = false; });
    const field = this.terrain.airfield;
    this.nav = { zone: { ...ZONE, engage: ZONE.r + ENGAGE_MARGIN }, base: { x: field.x, y: field.y, r: SAFE_RADIUS }, wave: 0, enemies: 0,
      carrier: { x: this.carrier.x, y: this.carrier.y } };
    this.spawnPlayer();
    this.startTutorial();
    this.resize();
    addEventListener('resize', () => this.resize());
    this.last = performance.now();
    this.fpsAcc = 0; this.fpsN = 0;
    requestAnimationFrame((t) => this.frame(t));
  }

  get walking() { return this.base.walker.active; }
  // the map: the original island (place without lat) or a 102 km piece of the real world (world.js).  The
  // terrain object, the carrier and the scene stay the same objects, their contents are replaced.
  async loadPlace(place, onProgress) {
    if (!place || place.lat === null || place.lat === undefined) {
      this.terrain.load(this.islandData);
      this.carrier.moveTo({ x: 21000, y: -42000 });
      this.view.rebuildWorld(null);
      this.place = null; this.worldInfo = null;
    } else {
      const q = this.settings ? this.settings.quality : 'high', maxTex = this.renderer.capabilities.maxTextureSize;
      const texSize = Math.min(maxTex, { low: 2048, medium: 4096, high: 4096, ultra: 8192 }[q] || 4096);
      const res = q === 'ultra' ? 2048 : 1024;
      const w = await buildWorld({ lat: place.lat, lon: place.lon, name: place.name, res, texSize, onProgress });
      this.terrain.load(w.data);
      this.carrier.moveTo(w.info.carrier);
      this.view.rebuildWorld(w.canvas, w.far);
      this.place = place; this.worldInfo = w.info;
      if (this.view.setGeo) this.view.setGeo(w.info);
    }
    const f = this.terrain.airfield;
    this.nav.base.x = f.x; this.nav.base.y = f.y;
    this.nav.carrier = this.carrier.active === false ? null : { x: this.carrier.x, y: this.carrier.y };
  }

  static freshState() {
    return { wave: 0, kills: 0, deaths: 0, banner: '', subBanner: '', paused: true, waveTimer: FIRST_WAVE_DELAY, waveActive: false,
      score: 0, streak: 0, duelWins: 0, duelLosses: 0, duelStreak: 0, over: false, modeLine: '', credits: 0 };
  }
  // a new match on the same scene (terrain, models and the renderer stay)
  newMatch(opts) {
    this.opts = opts;
    this.base.walker.leave(); this.base.dispose(); this.base.jetsOnGround = [];
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
    this.player = null; this.wingman = null; this.killCam = null; this.followM = null;
    if (this.race) { this.race.dispose(); this.race = null; }
    this.bt = { charge: 1, active: 0 };
    this.threats.clear(); this.hitBy.clear();
    this.spawnPlayer();
    this.startTutorial();
    if (!this.opts.activity) this.base.build();         // the buildings stand at every base
  }
  get scenario() { return this.opts.tutorial ? 'waves' : this.opts.scenario || 'waves'; }
  // the optional guided flight (main menu -> Oktatás); no enemy waves while it runs
  startTutorial() {
    $('tutorial').hidden = true;
    // the radio: everything open in free play; the career gives only the calls taught so far
    this.radio.unlocked = this.opts.radioUnlocked || null;
    this.radio.callsign = this.opts.callsign || 'VIPER 1-1';
    this.radio.portraits = this.opts.portraits || {};
    this.radio.cleared = { taxi: false, takeoff: false, land: false };
    this.nav.zone = { ...ZONE, engage: ZONE.r + ENGAGE_MARGIN }; this.state.missionLine = '';
    if (this.player) this.player.autopilot = null;
    // a career activity (career mode: back seat, school, mission) takes the tutorial's place: no free waves
    this.tutorial = this.opts.activity ? this.opts.activity(this) : this.opts.tutorial ? new Tutorial(this) : null;
    this.setupBench();
  }
  // performance test (settings -> Teljesítményteszt): 8 s of a real fight - the player's jet flown by an AI
  // pilot, four enemies at once - timed on the wall clock; the result picks the graphics quality
  setupBench() {
    this.bench = null;
    if (!this.opts.benchmark) return;
    this.bench = { t0: performance.now(), last: 0, frames: [] };
    this.state.waveTimer = 0;
    this.player.invulnerable = true;
  }
  benchStep(now) {
    const b = this.bench, p = this.player;
    if (p.alive && !(p.pilot instanceof AIPilot)) { new AIPilot(p, 'hard', null); p.invulnerable = true; }
    const el = now - b.t0;
    if (el > 1500 && b.last) b.frames.push(now - b.last);
    b.last = now;
    $('fps').textContent = `TESZT ${Math.max(0, Math.ceil((9500 - el) / 1000))} s`;
    if (el < 9500) return;
    const f = b.frames.sort((x, y) => x - y), mean = f.reduce((a, x) => a + x, 0) / Math.max(1, f.length);
    const res = { fps: 1000 / mean, low: 1000 / (f[Math.floor(f.length * 0.9)] || mean), frames: f.length };
    this.bench = null;
    if (this.onBenchmark) this.onBenchmark(res);
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
    const duel = this.scenario === 'duel', race = this.scenario === 'race', air = this.opts.airStart || duel || race, field = this.terrain.airfield;
    let pos, heading = 0, speed = 0;
    if (race) {
      // ring race: 3 km north of the base, heading north, the first ring ahead
      const start = V(field.x, field.y + 3000, 0);
      if (!this.race) this.race = new Race(this.terrain, this.view.scene, start, 0);
      this.race.reset();
      const r0 = this.race.rings[0];
      pos = add(r0.c, mul(r0.n, -1800)); pos.z = Math.max(r0.c.z + 60, this.terrain.height(pos.x, pos.y) + 250);
      speed = 220; heading = Math.atan2(r0.n.x, r0.n.y) / DEG;
      this.prevPos = null;
    } else if (duel) {
      // duel: in the combat zone, heading north; the opponent comes head-on (spawnDuel)
      pos = V(ZONE.x, ZONE.y - 7000, 5000);
      pos.z = Math.max(pos.z, this.terrain.height(pos.x, pos.y) + 1500); speed = 250;
      for (const a of this.world.aircraft) if (a.team !== 'blue' && a.alive) a.alive = false;
      this.world.aircraft = this.world.aircraft.filter((a) => a.team === 'blue');
      this.state.waveActive = false; this.state.waveTimer = 3;
    } else if (air) {
      // between the base and the combat zone, heading for the zone
      const k = 0.45;
      pos = V(field.x + (ZONE.x - field.x) * k, field.y + (ZONE.y - field.y) * k, 4500);
      pos.z = Math.max(pos.z, this.terrain.height(pos.x, pos.y) + 1500); speed = 250;
      heading = Math.atan2(ZONE.x - pos.x, ZONE.y - pos.y) / DEG;
    } else if (this.opts.carrierStart && this.carrier.active !== false) {
      const [x, y, hdg] = this.carrier.catapult(0);          // on catapult 1, facing the bow
      pos = V(x, y, 0); heading = hdg;
    } else {
      const [x, y, hdg] = field.startPosition();
      pos = V(x, y, 0); heading = hdg;
    }
    // the hangar: engine-room upgrades, the paint scheme and the mods ride on the player's jet
    const hg = this.hangar, base = AIRCRAFT[this.opts.aircraft] || TRAINERS[this.opts.aircraft] || AIRCRAFT.f16;
    const spec = this.opts.benchmark ? base : hg.upgraded(base);
    const ac = new Aircraft(spec, `Te (${spec.callsign} 1)`, 'blue', pos, heading, speed, { isPlayer: true, livery: 'viper', lockAssist: true,
      missiles: missilesFor(spec, false), loadout: spec.trainer ? 'default' : this.opts.loadout || 'default', rnd: rng(Math.floor(this.rnd() * 1e9)),
      skin: hg.skin, blastMult: hg.modOn('bigboom') ? 1.6 : 1, tracerColor: hg.modOn('tracer') ? [0.85, 0.4, 1, 0.45, 0.1, 0.7] : null });
    this.cam.eye = this.models.types[spec.model].eye.clone();
    this.cam.panel = this.models.types[spec.model].panel.clone();
    this.cam.panelFov = this.models.types[spec.model].panelFov;
    if (air) ac.controls.throttle = 0.95;
    else {
      ac.fm.placeOnGround(pos.x, pos.y, this.terrain.height(pos.x, pos.y), heading);
      ac.controls.throttle = 0;
      this.state.subBanner = this.opts.carrierStart && this.carrier.active !== false ? CAT_HINT : spec.noAB ? TAKEOFF_HINT_NOAB : TAKEOFF_HINT;
    }
    w.addAircraft(ac);
    this.player = ac; this.pilot = new PlayerPilot(ac);
    this.cam.reset(ac);
    this.killCam = null; this.followM = null; this.threats.clear(); this.hitBy.clear();
    if (this.wingman && this.wingman.alive) this.wingman.pilot.lead = ac;
    else if (air && this.wantWingman()) this.spawnWingman();
    if (this.scenario === 'survival' && this.state.wave === 0) this.state.waveTimer = air ? 12 : FIRST_WAVE_DELAY;
  }
  wantWingman() { return !!this.opts.wingman && !this.opts.tutorial && this.scenario !== 'duel' && this.scenario !== 'race' && !this.opts.benchmark; }
  // the wingman joins behind and to the right of the player (same type, the weaker AI airframe and missiles)
  spawnWingman() {
    const p = this.player, spec = BANDITS[p.spec.id] || BANDITS[p.spec.model] || BANDITS.f16;
    const fwd = norm(V(p.forward.x, p.forward.y, 0), V(0, 1, 0)), right = V(fwd.y, -fwd.x, 0);
    const pos = add(add(p.pos, mul(fwd, -260)), mul(right, 170));
    pos.z = Math.max(p.pos.z + 20, this.terrain.height(pos.x, pos.y) + 300);
    const loadout = spec.id === 'f16' ? 'default' : buildLoadout(spec, 2, 4).layout;
    const ac = new Aircraft(spec, `${spec.callsign} 2 (kísérő)`, 'blue', pos, Math.atan2(fwd.x, fwd.y) / DEG, Math.max(200, p.speed),
      { livery: 'viper', missiles: missilesFor(spec, true), loadout, rnd: rng(Math.floor(this.rnd() * 1e9)) });
    new WingmanPilot(ac, p);
    this.world.addAircraft(ac);
    this.wingman = ac;
    this.hud.message(`KÍSÉRŐ CSATLAKOZOTT - ${ac.name}`, 'good', 3);
    this.voice.say('wing', 'Two, in position.', 5);
  }

  // a wave appears in the combat zone, on its far side from the player, facing the player's way in
  spawnWave() {
    const st = this.state, p = this.player, r = this.rnd;
    if (this.scenario === 'duel') { this.spawnDuel(); return; }
    st.wave++;
    if (this.wantWingman() && (!this.wingman || !this.wingman.alive)) this.spawnWingman();
    this.career.best('bestWave', st.wave);
    if (st.wave >= 5) this.medal('wave5');
    if (this.scenario === 'survival') { this.career.best('bestSurvival', st.wave); if (st.wave >= 4) this.medal('survivor'); }
    const count = Math.min(this.opts.enemies + st.wave - 1, MAX_ENEMIES);
    const from = norm(V(ZONE.x - p.pos.x, ZONE.y - p.pos.y, 0), V(0, 1, 0));
    const center = add(V(ZONE.x, ZONE.y, 0), mul(from, ZONE.r * 0.35));
    const side = V(from.y, -from.x, 0), area = { ...this.nav.zone, safe: this.nav.base };
    for (let i = 0; i < count; i++) {
      const pos = add(center, mul(side, (i - (count - 1) / 2) * 3500 + r.uniform(-800, 800)));
      pos.z = Math.max(r.uniform(3000, 7500), this.terrain.height(pos.x, pos.y) + 1500);
      const heading = Math.atan2(-from.x, -from.y) / DEG + r.uniform(-20, 20);
      const type = this.enemyType(r);
      const spec = BANDITS[type];
      const loadout = type === 'f16' || spec.proc ? 'default' : buildLoadout(spec, 2, 4).layout;
      const ac = new Aircraft(spec, `Bandita ${i + 1} (${spec.short})`, 'red', pos, heading, 240, { livery: 'viper', missiles: missilesFor(spec, true), loadout, rnd: rng(Math.floor(r() * 1e9)) });
      new AIPilot(ac, this.opts.difficulty, area);
      this.world.addAircraft(ac);
    }
    st.waveActive = true;
    const toZone = Math.max(0, Math.hypot(ZONE.x - p.pos.x, ZONE.y - p.pos.y) - ZONE.r);
    this.hud.message(`${st.wave}. HULLÁM - ${count} ellenség a harci zónában${toZone > 1000 ? ` (${(toZone / 1000).toFixed(0)} km)` : ''}`, 'warn', 5);
  }
  // duel: one opponent 9 km ahead, head-on, same height; every round starts with a full jet
  spawnDuel() {
    const st = this.state, p = this.player, r = this.rnd;
    st.wave++;
    p.rearm(); p.hp = p.spec.hp; p.burning = false; p.fm.fuel = p.spec.internalFuel;
    for (const s of p.stations) s.reload = undefined;
    const fwd = norm(V(p.forward.x, p.forward.y, 0), V(0, 1, 0));
    const pos = add(p.pos, mul(fwd, 9000));
    pos.x = clamp(pos.x, -38000, 38000); pos.y = clamp(pos.y, -38000, 38000);
    pos.z = clamp(p.pos.z + r.uniform(-400, 400), this.terrain.height(pos.x, pos.y) + 1500, 9000);
    const type = this.enemyType(r);
    const spec = BANDITS[type];
    const loadout = type === 'f16' || spec.proc ? 'default' : buildLoadout(spec, 2, 4).layout;
    const ac = new Aircraft(spec, `Ellenfél (${spec.short})`, 'red', pos, Math.atan2(p.pos.x - pos.x, p.pos.y - pos.y) / DEG, 240,
      { livery: 'viper', missiles: missilesFor(spec, true), loadout, rnd: rng(Math.floor(r() * 1e9)) });
    new AIPilot(ac, this.opts.difficulty, null);
    this.world.addAircraft(ac);
    st.waveActive = true;
    this.hud.message(`${st.wave}. PÁRBAJ - ${spec.short} szemből, 9 km`, 'warn', 4);
    this.voice.say('duel', 'Bandit, nose, five miles. Fight\'s on.', 3);
  }
  // the menu's enemy choice: any number of types, one is picked at random for every enemy
  enemyType(r) {
    const list = (this.opts.enemyTypes || [this.opts.enemyType || 'f16']).filter((k) => BANDITS[k]);
    return list.length ? list[Math.floor(r() * list.length)] : 'f16';
  }
  enemiesAlive() { return this.world.aircraft.filter((a) => a.team !== 'blue' && a.alive); }

  // ------------------------------------------------------------------ input
  canAct() { return !this.state.paused && this.player && this.player.alive; }
  onKey(k) {
    if (this.inMenu) return;                          // the main menu is open: its buttons do the work
    if (this.tutorial && this.tutorial.onKey && !this.state.paused && this.tutorial.onKey(k)) return;
    if (this.walking) {                               // on foot: E uses what is near, Esc = menu
      if (k === 'e' && !this.state.paused) { this.base.interact(); return; }
      if (k === 'Escape') { if (!this.state.paused) { if (this.opts.lobby && this.onLobbyEsc) this.onLobbyEsc(); else this.pause(); } return; }
      if (k === 'h' || k === 'F1') { this.toggleHelp(); return; }
      if (k === 'i' && !this.state.paused) { this.radioDown = true; this.radio.keyDown(); return; }
      if (k === 'Enter' || k === 'NumpadEnter') { if (this.tutorial) this.tutorial.enter(); return; }
      return;
    }
    if (k === 'h' || k === 'F1') { this.toggleHelp(); return; }
    if (k === 'Escape') { if (!this.state.paused) this.pause(); return; }
    if (k === 'p') { if (this.state.paused) this.resume(); else this.pause(); return; }
    if (k === 'Enter' || k === 'NumpadEnter') { if (this.tutorial) this.tutorial.enter(); else this.respawn(); return; }
    if (k === 'm') { this.hud.markers = !this.hud.markers; return; }
    if (k === 'i' && !this.state.paused) { this.radioDown = true; this.radio.keyDown(); return; }
    if (k === 'eject' && !this.state.paused) { this.ejectHandle(); return; }
    if (k === 'o' && this.canAct()) {
      if (!this.hangar.modOn('bullettime')) this.hud.message('Bullet time: a Hangárban vehető meg (mod)', 'info', 2, 'bt');
      else if (this.bt.active > 0) this.bt.active = 0;
      else if (this.bt.charge >= 1) { this.bt.active = 4; this.bt.charge = 0; this.hud.message('BULLET TIME', 'warn', 1.5, 'bt'); }
      else this.hud.message(`Bullet time töltődik: ${Math.round(this.bt.charge * 100)}%`, 'info', 1.2, 'bt');
      return;
    }
    if (k === 'u') {
      this.missileCam = !this.missileCam; this.followM = null;
      this.hud.message(this.missileCam ? 'RAKÉTAKAMERA BE - a kilőtt rakétát követi (U = ki)' : 'RAKÉTAKAMERA KI', 'info', 2, 'mcam');
      return;
    }
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
        else msg('Ezen a gépen nincs tolóerő-vektorálás (F-16 és F-15 ACTIVE)', 'warn');
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
    else if (inp.inside && !this.state.paused && !this.touchOn()) {
      // no pointer lock (e.g. blocked by the page): the cursor works as a joystick around the screen centre
      const dz = (v) => (Math.abs(v) < 0.06 ? 0 : (v - Math.sign(v) * 0.06) / 0.94);
      const k = cam.sensitivity / SENS_BASE;
      cam.rotate(-dz(inp.mx) * 95 * k * dt, -dz(inp.my) * 70 * k * dt * (cam.invertY ? -1 : 1));
    }
    const pad = this.pad.connected ? this.pad : null;
    if (pad) {
      cam.setFreeLook(pad.held(PAD.L3));
      cam.rotate(-pad.rx * 110 * dt, -pad.ry * 80 * dt * (cam.invertY ? -1 : 1));
    }
    const tc = this.touchOn() ? this.touch : null;
    if (tc && !joystick) cam.rotate(-tc.stick.x * 120 * dt, -tc.stick.y * 85 * dt * (cam.invertY ? -1 : 1));
    this.pilot.aim = cam.aimDirection();
    this.pilot.pitch = inp.axis('s', 'w');      // S = nose up (pull), W = nose down (push)
    this.pilot.roll = inp.axis('d', 'a');
    this.pilot.yaw = inp.axis('e', 'q');
    if (joystick) {
      const dz = (v) => (Math.abs(v) < STICK_DEADZONE ? 0 : (v - Math.sign(v) * STICK_DEADZONE) / (1 - STICK_DEADZONE));
      if (this.pilot.pitch === null) this.pilot.pitch = dz(this.stick.y);
      if (this.pilot.roll === null) this.pilot.roll = dz(this.stick.x);
    } else { this.stick.x = 0; this.stick.y = 0; }
    if (tc && joystick && (tc.stick.x || tc.stick.y)) { this.pilot.pitch = tc.stick.y; this.pilot.roll = tc.stick.x; }
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
    const tt = tc ? tc.takeThrottle() : null;
    if (tt !== null) c.throttle = tt;
    this.throttleInput(dt, inp.key('shift') || rt, inp.key('z') || inp.key('control') || lt);
    const brake = inp.key('b') || (pad && pad.held(PAD.DOWN)) || (tc && tc.hold.brake);
    c.airbrake = brake;
    c.brakes = brake && p.onGround;
    p.trigger = inp.mouse[0] || (pad && pad.held(PAD.RB)) || (tc && tc.hold.gun);
    p.cmHold = inp.key('x') || (pad && pad.held(PAD.LB)) || (tc && tc.hold.flare);
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
      const k = SENS_BASE * cam.stickSens * STICK_GAIN;
      s.x = clamp(s.x + dx * k, -1, 1); s.y = clamp(s.y + dy * k * inv, -1, 1);
    } else if (inp.inside && !this.state.paused && !this.touchOn()) {   // no pointer lock: the cursor's offset from the centre is the stick
      const dz = (v) => (Math.abs(v) < 0.04 ? 0 : (v - Math.sign(v) * 0.04) / 0.96);
      const k = 1.6 * cam.stickSens;
      s.x = clamp(dz(inp.mx) * k, -1, 1); s.y = clamp(dz(inp.my) * k * inv, -1, 1);
    }
  }

  // Throttle like a real lever with a MIL detent: a tap moves it 5 % (taken from the key event itself, so
  // even a very short tap counts), holding slews it 40 %/s.  Going up it stops at 100 % (MIL); the
  // afterburner needs a new press of Shift there.  Down from AB goes straight to MIL.
  throttleStep(dir) {
    const c = this.player.controls;
    this.thrPress = performance.now();
    if (dir > 0) {
      if (c.throttle >= 0.999) { if (c.throttle < MAX_AB && !this.player.spec.noAB) { c.throttle = MAX_AB; this.hud.message('UTÁNÉGETŐ BE', 'warn', 1.2, 'thr'); } }
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
    if (this.opts.lobby && this.walking && !this.inMenu && this.onLobbyEsc) { this.onLobbyEsc(); return; }   // Esc in the lobby: its menu
    this.state.paused = true;
    if (document.pointerLockElement) document.exitPointerLock();
    this.showOverlay(this.helpVisible || this.inMenu ? null : 'pause');
    const st = this.state;
    $('pausestats').textContent = `${st.wave}. hullám · ${st.score} pont · lelőve ${st.kills} · halál ${st.deaths}` +
      (st.streak > 1 ? ` · sorozat ${st.streak}` : '');
    this.voice.stop();
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
    if (this.touchOn()) { this.lockWanted = false; return; }     // touch: the buttons need the pointer free
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
  // Ctrl+E twice (like the real handle: a deliberate pull): the seat fires, the pilot comes down under the
  // parachute and lives; the jet flies on with nobody at the controls and is lost
  ejectHandle() {
    const p = this.player, now = performance.now();
    if (!p || !p.alive || p.ejected) return;
    if (p.onGround && p.speed < 30) { this.hud.message('A földön állva nem katapultálunk – szállj ki rendesen', 'info', 2, 'eject'); return; }
    if (!this.ejectArm || now - this.ejectArm > 2500) { this.ejectArm = now; this.hud.message('KATAPULTÁLÁS: Ctrl+E még egyszer!', 'warn', 1.5, 'eject'); return; }
    this.ejectArm = 0;
    p.ejected = true;
    p.pilot = { think() {}, fly() { p.controls.pitch = 0.05; p.controls.roll = 0; p.controls.yaw = 0; } };
    p.trigger = false;
    if (this.chute) this.chute.dispose();
    this.chute = new Parachute(this.view.scene, p.pos, p.vel, p.fm.up);
    const st = this.state;
    st.banner = 'KATAPULTÁLTÁL!';
    st.subBanner = `A pilóta életben van – a ${p.spec.short} elveszett  ·  ${this.touchOn() ? 'Koppints' : 'Enter'}: új gép`;
    this.sounds.play && this.sounds.play('eject');
    this.radio.say('you', `${this.radio.callsign}, EJECTING, EJECTING!`);
    this.radio.say('awacs', `${this.radio.callsign}, Magic copies, good chute. Rescue is on the way.`, 4500);
    this.career.data.ejections = (this.career.data.ejections || 0) + 1;
    if (this.onEject) this.onEject(p);
  }
  respawn() {
    if (this.player && this.player.ejected) {
      const st = this.state;
      st.banner = st.subBanner = '';
      if (this.chute) { this.chute.dispose(); this.chute = null; }
      this.spawnPlayer();
      return;
    }
    if (this.race && this.race.finished) { this.state.banner = this.state.subBanner = ''; this.spawnPlayer(); return; }
    if (this.state.over) { this.career.data.matches++; this.newMatch(this.opts); this.resume(); return; }   // survival: a new game
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
      if ((!this.player.alive || this.player.ejected) && this.pad.pressed(PAD.A)) this.respawn();
    }
    if (!st.paused) {
      if (this.walking) this.base.walker.update(dt);
      else if (this.player.alive && !this.player.ejected && !this.player.autopilot) this.applyInput(dt);
      else this.input.takeDelta();
      // bullet time (hangar mod): the world runs slower while it is on; it recharges in 20 s
      const bt = this.bt;
      if (bt.active > 0) bt.active = Math.max(0, bt.active - dt); else bt.charge = Math.min(1, bt.charge + dt / 20);
      const wdt = bt.active > 0 ? dt * 0.35 : dt;
      this.world.update(wdt);
      if (this.race && this.player.alive) this.raceStep(wdt);
      if (this.chute) this.chute.update(wdt, this.terrain);
      if (this.player.alive && !this.player.ejected && this.carrier.active !== false) this.carrierStep(dt);
      this.carrier.update(dt);
      if (this.player.alive && !this.player.onGround) this.career.tick(dt);
      for (const { missile } of this.player.rwr.incoming) this.threats.add(missile);
      if (this.tutorial) this.tutorial.update(dt);
      this.gameFlow(dt);
    } else this.input.takeDelta();
    for (const [kind, d] of this.world.drainEvents()) {
      this.view.handleEvent(kind, d);
      this.hud.handleEvent(kind, d, this.player);
      this.sounds.handleEvent(kind, d, this.player);
      this.onEvent(kind, d);
      this.extraEvent(kind, d);
      if (this.tutorial) this.tutorial.onEvent(kind, d);
    }
    if (this.walking && this.inMenu) this.base.walker.idle(dt);     // the lobby behind the menu: a slow look round
    this.base.update(dt);
    const sdt = st.paused ? 0 : dt;
    this.updateFollow(sdt);
    this.cam.update(sdt, this.player);
    this.view.cockpitView = this.cam.cockpit && this.player.alive && !this.cam.follow;
    this.view.update(sdt, this.player);
    // the cockpit displays of the player's jet (drawn only while they can be seen)
    const nav = this.nav;
    nav.wave = st.wave; nav.enemies = this.enemiesAlive().length;
    this.hud.nav = this.race ? null : nav; this.hud.tutorial = !!this.tutorial;     // race: no combat-zone marks
    const vis = this.view.visuals.get(this.player);
    if (vis && vis.screens && !vis.displays) vis.displays = new CockpitDisplays(this.player.spec, vis.screens);
    if (vis && vis.displays && this.view.cockpitView) vis.displays.update(sdt, this.player, this.world, nav);
    this.view.render();
    st.walking = this.walking;
    st.modeLine = this.modeLine();
    st.credits = this.hangar.data.credits;
    st.meatball = this.meatball();
    st.bt = this.hangar.modOn('bullettime') ? this.bt : null;
    st.raceTarget = this.race && this.race.target ? this.race.target.c : null;
    this.hud.touchLayout = this.touchOn() && !this.inMenu;
    this.hud.update(dt, this.player, this.world, this.view.camera, this.cam, st);
    this.sounds.update(this.player, st.paused, this.world, this.cam.position);
    this.feedback(dt);
    this.touch.update(this.touchOn() && !st.paused && !this.inMenu, this.player);
    // real frames per second (wall clock; the old counter used the clamped dt and read too high on slow machines)
    const rf = this.realFps, now = performance.now();
    rf.n++;
    if (now - rf.t > 1000) { this.fps = rf.n * 1000 / (now - rf.t); $('fps').textContent = `${Math.round(this.fps)} FPS`; rf.n = 0; rf.t = now; }
    if (this.bench) this.benchStep(now);
  }
  onEvent(kind, d) {
    // the wingman's own radio calls
    if (this.wingman) {
      if (kind === 'launch' && d.missile && d.missile.shooter === this.wingman) this.radio.event('wing_fox');
      if (kind === 'kill' && d.killer === this.wingman) this.radio.event('wing_splash');
    }
    if (kind !== 'kill') return;
    const st = this.state, p = this.player, scen = this.scenario;
    if (d.victim === p && p.ejected) { this.hud.message('Az elhagyott gép lezuhant – a pilóta életben van', 'info', 3, 'eject'); return; }
    if (d.victim === p) {
      st.deaths++; st.streak = 0;
      if (!this.tutorial) this.career.data.deaths++;
      if (d.killer && d.killer !== p && d.killer.alive) this.killCam = { killer: d.killer, t: 4 };
      st.banner = d.weapon !== 'crash' ? 'LELŐTTEK!' : 'LEZUHANTÁL!';
      const again = this.touchOn() ? 'Koppints a képernyőre: újraéledés' : 'Enter: újraéledés';
      st.subBanner = this.tutorial ? 'Pár másodperc, és újra a levegőben vagy – a lecke elölről indul'
        : `${again}  ·  Esc: menü (főmenü, új játék)`;
      if (scen === 'duel' && !this.tutorial) { st.duelLosses++; st.duelStreak = 0; st.subBanner = `Párbaj elvesztve  ·  ${again} (új kör)`; }
      if (scen === 'survival') {
        const rec = st.score > (this.career.data.bestScore || 0);
        this.career.best('bestScore', st.score); this.career.best('bestSurvival', st.wave); this.career.save();
        st.over = true; st.banner = 'VÉGE';
        st.subBanner = `Túlélés: ${st.wave}. hullám · ${st.score} pont${rec ? ' · ÚJ REKORD!' : ''}  ·  ${this.touchOn() ? 'Koppints' : 'Enter'}: új játék`;
      }
      this.career.save();
    } else if (d.killer === p) {
      st.kills++;
      d = { ...d, weapon: WEAPON_CLASS[d.weapon] || d.weapon };          // IRIS-T, R-73... count as AIM-9M etc.
      if (this.tutorial || this.opts.benchmark) return;
      st.streak++;
      const pts = killPoints(d.weapon, this.opts.difficulty, st.streak);
      this.addScore(pts);
      this.hud.popup(`+${pts} ${weaponLabel(d.weapon)}${st.streak > 1 ? ` ×${st.streak}` : ''}`);
      const c = this.career.data;
      c.kills++;
      if (d.weapon === 'crash') c.crashKills++; else if (d.weapon === 'AIM-9M') c.irKills++; else if (d.weapon === 'AIM-120A') c.arhKills++; else c.gunKills++;
      c.perPlane[p.spec.id] = (c.perPlane[p.spec.id] || 0) + 1;
      this.career.best('bestStreak', st.streak); this.career.best('bestScore', st.score);
      this.voice.say('splash', `Splash ${SPLASH[Math.min(st.kills, 10) - 1]}.`, 1.5);
      this.medal('first');
      if (d.weapon === 'crash') this.medal('maneuver'); else if (d.weapon === 'AIM-9M') this.medal('fox2');
      else if (d.weapon === 'AIM-120A') this.medal('fox3'); else if (isGun(d.weapon)) this.medal('guns');
      if (st.streak >= 5) this.medal('ace');
      if (d.victim.spec.id === 'f22') this.medal('stealth');
      c.victims = c.victims || {};                                  // intel: which enemy types were shot down
      c.victims[d.victim.spec.id] = (c.victims[d.victim.spec.id] || 0) + 1;
      if (this.opts.difficulty === 'hard' || this.opts.difficulty === 'ace') this.medal('veteran');
      if (st.score >= 5000) this.medal('score5k');
      this.career.save();
    } else if (d.killer && d.killer === this.wingman && d.victim.team !== 'blue') {
      this.addScore(50);
      this.hud.popup('+50 KÍSÉRŐ', 'rgba(115,217,255,0.95)');
      this.voice.say('wsplash', 'Two, splash one.', 3);
      this.medal('team');
    }
  }
  // the extra effects of events: rumble, voice, medals that do not come from kills
  extraEvent(kind, d) {
    const p = this.player, st = this.state;
    if (!p) return;
    if (kind === 'hit' && d.target === p) { this.pad.rumble(0.9, 0.6, 260); if (d.missile) this.hitBy.add(d.missile); }
    else if (kind === 'launch' && d.shooter === p) {
      this.pad.rumble(0.25, 0.5, 160);
      if (!this.tutorial) this.career.data.missilesFired++;
      this.voice.say('fox', d.missile.spec.guidance === IR ? 'Fox two.' : 'Fox three.', 1.2);
    } else if (kind === 'explosion') {
      const dd = len(sub(d.pos, p.pos));
      if (dd < 2500) { const k = 1 - dd / 2500; this.pad.rumble(0.8 * k, 0.5 * k, 320); this.cam.kick = Math.max(this.cam.kick || 0, k * k); }
    } else if (kind === 'missile_end') {
      const m = d.missile;
      if (this.threats.has(m) && !this.hitBy.has(m) && p.alive && !this.tutorial) {
        this.addScore(50); this.hud.popup('+50 KICSELEZVE', 'rgba(115,217,255,0.95)');
        this.medal('evade');
      }
      this.threats.delete(m); this.hitBy.delete(m);
    } else if (kind === 'cobra' && d.target === p && !this.tutorial) this.medal('cobra');
  }
  // carrier: arresting wires on touchdown, bolters, the catapult; the deck counts as paved for rearming
  carrierStep(dt) {
    const p = this.player, fm = p.fm, cv = this.carrier, st = this.state;
    const on = p.onGround && cv.onDeck(p.pos.x, p.pos.y);
    if (on && !this.wasOnDeck && p.speed > 22) {
      if (fm.gearDown && cv.inWires(p.pos.x, p.pos.y)) {
        fm.arrest = 30; this.catState = null; this.trapped = true;
        const n = cv.wireNumber(p.pos.x, p.pos.y);
        this.hud.message(`BEAKADT - ${n}. fékezőkötél${n === 3 ? ' (tökéletes!)' : ''}`, 'good', 4, 'trap');
        this.voice.say('trap', n === 3 ? 'Three wire. Nice.' : `${['One', 'Two', 'Three', 'Four'][n - 1]} wire.`, 3);
        this.pad.rumble(1, 0.8, 500); this.cam.kick = 0.6;
        if (!this.tutorial && !this.opts.benchmark) this.medal('trap');
        if (this.onTrap) this.onTrap(n);
      } else {
        this.hud.message('BOLTER! Teljes gáz, és emelkedj újra', 'warn', 3, 'trap');
        this.voice.say('bolter', 'Bolter, bolter.', 3, true);
      }
    }
    this.wasOnDeck = on;
    if (this.trapped && p.speed < 3) {                   // the wire stopped the jet: throttle back, brakes on
      this.trapped = false; p.controls.throttle = 0; fm.parkBrake = true; this.towTimer = 2.5;
      this.hud.message('ELKAPVA! A fedélzeti személyzet a katapulthoz vontat...', 'good', 3, 'trap');
    }
    if (this.towTimer > 0 && on) {
      this.towTimer -= dt;
      if (this.towTimer <= 0) {                          // towed to catapult 1 (rearmed and refuelled by the deck crew)
        const [x, y, h] = cv.catapult(0);
        fm.placeOnGround(x, y, DECK_Z, h); p.controls.throttle = 0; this.cam.reset(p);
        p.rearm(); p.hp = p.spec.hp; p.burning = false; fm.fuel = p.spec.internalFuel;
        this.hud.message('A KATAPULTON - teljes gáz = kilövés', 'info', 4, 'trap');
      }
    }
    if (fm.parkBrake && (!on || p.controls.throttle >= 0.99)) fm.parkBrake = false;
    // catapult: stopped on the track at full throttle -> 1 s run-up, then the shuttle fires
    const cat = this.catState;
    if (on && cv.onCatapult(p.pos.x, p.pos.y) && fm.gearDown && p.speed < 3 && p.controls.throttle >= 0.99 && !cat) {
      this.catState = { t: 0, fired: false };
      this.hud.message('KATAPULT ÉLESÍTVE...', 'warn', 1.5, 'cat');
    }
    if (cat) {
      cat.t += dt;
      if (!cat.fired && cat.t > 1.0) { cat.fired = true; fm.catapultAcc = 30; this.hud.message('KATAPULT!', 'good', 2, 'cat'); this.voice.say('cat', 'Shooter. Launch.', 3); this.pad.rumble(1, 1, 600); this.cam.kick = 0.8; }
      if (cat.fired && (!p.onGround || p.speed > 88)) {
        fm.catapultAcc = 0; this.catState = null;
        // off the bow: the aim point goes 12 degrees up so the jet climbs away from the sea
        const f = norm(V(p.forward.x, p.forward.y, 0), V(0, 1, 0));
        this.cam.aim = qlook(norm(V(f.x, f.y, 0.21)));
        if (this.onCatapult) this.onCatapult();
      }
      if (!cat.fired && (p.controls.throttle < 0.99 || !on)) this.catState = null;
    }
    if (st.subBanner === CAT_HINT && !p.onGround) st.subBanner = '';
  }
  // optical landing system: shown while flying an approach to the carrier (behind it, gear down, within 4 km)
  meatball() {
    const p = this.player;
    if (!p || !p.alive || p.onGround || !p.fm.gearDown) return null;
    const g = this.carrier.glide(p.pos.x, p.pos.y, p.pos.z);
    if (!g.behind || g.dist > 4500 || Math.abs(g.off) > 700) return null;
    return g;
  }
  addScore(n) {
    this.state.score += n;
    if (!this.tutorial && !this.opts.benchmark) this.hangar.earn(n);
  }
  // ring race: passing rings, the finish, a ring missed
  raceStep(dt) {
    const p = this.player, r = this.race;
    const prev = this.prevPos || copy(p.pos);
    this.prevPos = copy(p.pos);
    const ev = r.update(dt, p, prev);
    if (ev === 'ring') { this.addScore(20); this.hud.popup(`GYŰRŰ ${r.next}/${RACE_RINGS}`, 'rgba(255,200,64,0.95)'); this.sounds.play('splash', 0.4); }
    else if (ev === 'miss') this.hud.message('MELLÉ! Fordulj vissza a gyűrűhöz', 'warn', 2, 'race');
    else if (ev === 'finish') {
      const st = this.state, reward = 300 + (r.record ? 200 : 0);
      this.addScore(reward);
      st.banner = `CÉL!  ${fmtTime(r.time)}`;
      st.subBanner = `${r.record ? 'ÚJ REKORD! · ' : `rekord: ${fmtTime(r.best)} · `}+${reward} kredit  ·  ${this.touchOn() ? 'Koppints' : 'Enter'}: újra`;
      this.sounds.play('medal', 0.7);
      this.career.best('bestScore', st.score); this.career.save();
    }
  }
  medal(id) {
    if (this.opts.benchmark) return;
    const a = this.career.award(id);
    if (!a) return;
    this.hud.showMedal(a);
    this.sounds.play('medal', 0.7);
  }
  modeLine() {
    const st = this.state;
    if (this.tutorial) return '';
    if (this.scenario === 'race' && this.race) {
      const r = this.race;
      return `GYŰRŰVERSENY · ${Math.min(r.next, RACE_RINGS)}/${RACE_RINGS} · ${fmtTime(r.time)} · rekord ${fmtTime(r.best)}`;
    }
    if (this.scenario === 'duel') return `PÁRBAJ · győzelem ${st.duelWins} · vereség ${st.duelLosses}${st.duelStreak > 1 ? ` · ${st.duelStreak} egymás után` : ''}`;
    if (this.scenario === 'survival') return `TÚLÉLÉS · egy életed van · rekord: ${this.career.data.bestSurvival || 0}. hullám`;
    return this.wingman ? `KÍSÉRŐ: ${this.wingman.alive ? 'a levegőben' : 'lelőtték, a következő hullámmal visszajön'}` : '';
  }
  touchOn() { return this.touchMode === 'on' || (this.touchMode === 'auto' && touchDevice()); }
  touchTap(act) {
    if (act === 'pause') { this.pause(); return; }
    if (act === 'weapon') { this.cycleWeapon(1); return; }
    this.onKey(act);
  }
  // missile cam (U) follows the player's newest missile until it ends; kill cam shows who shot the player down
  updateFollow(dt) {
    const p = this.player, cam = this.cam, now = performance.now();
    cam.follow = null; cam.followLabel = '';
    if (!p) return;
    if (p.ejected && this.chute) {                      // the camera stays with the parachute
      const c = this.chute;
      cam.follow = { pos: c.pos, dir: norm(V(c.vel.x, c.vel.y, -0.3), V(0, 1, -0.3)), dist: 22, height: 5 };
      cam.followLabel = c.landed ? 'A PILÓTA LEÉRT – ÉLETBEN VAN' : 'EJTŐERNYŐ';
      return;
    }
    if (!p.alive) {
      const k = this.killCam;
      if (k && k.t > 0 && k.killer && !k.killer.crashed) {
        k.t -= dt;
        cam.follow = { pos: copy(k.killer.pos), dir: norm(k.killer.vel, k.killer.forward), dist: 40, height: 8 };
        cam.followLabel = `LELŐTT: ${k.killer.name}`;
      }
      return;
    }
    if (!this.missileCam) { this.followM = null; return; }
    let m = this.followM;
    if (m && !m.alive && now - this.followEnd > 1500) m = this.followM = null;
    if (!m) {
      const mine = this.world.missiles.filter((x) => x.shooter === p && x.alive);
      m = this.followM = mine.length ? mine[mine.length - 1] : null;
    }
    if (!m) return;
    if (m.alive) {
      this.followEnd = now;
      this.followLast = { pos: copy(m.pos), dir: copy(m.dir) };
      const tg = m.guidedTarget || m.intended;
      cam.follow = { pos: m.pos, dir: m.dir, dist: 8, height: 1.6 };
      cam.followLabel = `RAKÉTAKAMERA · ${m.spec.name} · ${m.status}${tg && tg.alive ? ` · ${(len(sub(tg.pos, m.pos)) / 1000).toFixed(1)} km` : ''}  (U = ki)`;
    } else {
      cam.follow = { pos: this.followLast.pos, dir: this.followLast.dir, dist: 70, height: 12 };
      cam.followLabel = 'RAKÉTAKAMERA · becsapódás';
    }
  }
  // warning voice and controller rumble, from the player's state
  feedback(dt) {
    const p = this.player, st = this.state;
    if (st.paused || !p || !p.alive) { this.gunWas = false; return; }
    const terr = this.terrain, ahead = add(p.pos, mul(p.vel, 4)), agl = p.pos.z - terr.height(p.pos.x, p.pos.y);
    if (!p.onGround && p.fm.gearPos < 0.5 && (ahead.z < terr.height(ahead.x, ahead.y) + 60 || (agl < 150 && p.vel.z < -15))) this.voice.say('pull', 'Pull up. Pull up.', 2.5, true);
    const lvl = p.rwr.maxLevel;
    if (lvl >= 3) this.voice.say('missile', 'Missile. Missile.', 5, true);
    if (p.fm.fuel > 0 && p.fm.fuel < p.spec.internalFuel * 0.12) this.voice.say('bingo', 'Bingo fuel.', 45);
    if (p.fm.gearPos > 0.02 && p.fm.ias > 155) this.voice.say('gear', 'Warning. Gear.', 8);
    if (p.gun.firing && !this.gunWas) this.voice.say('guns', 'Guns, guns.', 6);
    this.gunWas = p.gun.firing;
    this.rumbleT -= dt;
    if (this.rumbleT <= 0 && this.pad.connected) {
      if (p.gun.firing) { this.pad.rumble(0.05, 0.4, 110); this.rumbleT = 0.1; }
      else if (lvl >= 3) { this.pad.rumble(0, 0.3, 90); this.rumbleT = 0.55; }
      else if (p.fm.gLoad > 7.5) { this.pad.rumble(0.15, 0.1, 120); this.rumbleT = 0.15; }
    }
  }
  // settings from the menu / pause screen (boot keeps them in localStorage)
  applySettings(s) {
    const cam = this.cam;
    cam.sensitivity = SENS_BASE * s.aim / 100; cam.stickSens = s.stick / 100; cam.invertY = s.invert;
    cam.baseFov = s.fov;
    this.sounds.setVolume(0.7 * s.volume / 100);
    this.voice.enabled = s.voice; this.voice.volume = Math.min(1, s.volume / 100 + 0.1);
    this.pad.rumbleOn = s.rumble;
    this.touchMode = s.touch;
    this.input.map = buildMap(s.keys || {});
    this.input.shiftRemapped = Object.values(this.input.map).includes('shift') || this.input.map.shift === '__none';
    this.settings = s;
    this.view.setGoogleKey(s.googleKey || '');
    const pr = { low: 0.75, medium: 1, high: 2 }[s.quality] || 2, dpr = window.devicePixelRatio || 1;
    // Ultra: rendered at 1.5x the screen's pixels (supersampling) - for strong graphics cards
    this.renderer.setPixelRatio(s.quality === 'ultra' ? Math.min(3, dpr * 1.5) : Math.min(dpr, pr));
    this.view.setQuality(s.quality);
    if (this.view.timeOfDay !== s.tod) this.view.setTimeOfDay(s.tod);
    this.resize();
  }
  gameFlow(dt) {
    const st = this.state, p = this.player;
    if (!p.alive) return;
    const field = this.terrain.airfield;
    const airborne = !p.onGround && p.pos.z - this.terrain.height(p.pos.x, p.pos.y) > 150;
    if ((st.subBanner === TAKEOFF_HINT || st.subBanner === TAKEOFF_HINT_NOAB) && airborne) {
      st.subBanner = '';
      this.hud.message('SIKERES FELSZÁLLÁS - húzd be a futóművet (G)', 'good', 4);
    }
    if (this.scenario === 'race') return;
    if (!this.tutorial && st.waveActive && !this.enemiesAlive().length) {
      st.waveActive = false; st.waveTimer = WAVE_DELAY;
      const scen = this.scenario;
      if (scen === 'duel') {
        st.duelWins++; st.duelStreak++; this.addScore(300); this.career.data.duelWins++;
        this.hud.popup('+300 PÁRBAJ', 'rgba(255,200,64,0.95)');
        this.hud.message('PÁRBAJ MEGNYERVE - a következő ellenfél pár másodperc múlva jön', 'good', 4);
        if (st.duelStreak >= 3) this.medal('duel3');
        st.waveTimer = 4;
      } else {
        const bonus = 100 * st.wave;
        this.addScore(bonus);
        this.hud.popup(`+${bonus} HULLÁM`, 'rgba(255,200,64,0.95)');
        if (scen === 'survival') { st.waveTimer = 4; this.hud.message('HULLÁM TELJESÍTVE - a következő mindjárt jön', 'good', 4); }
        else this.hud.message('HULLÁM TELJESÍTVE - leszállhatsz a bázison újrafegyverezni', 'good', 5);
      }
      this.career.best('bestScore', st.score); this.career.save();
    }
    if (!this.tutorial && this.wantWingman() && !this.wingman && airborne) this.spawnWingman();
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
    if (this.hangar.modOn('infcm') && !this.opts.benchmark) {          // hangar mod: endless flares and chaff
      p.flares = p.spec.cm.flares; p.chaff = p.spec.cm.chaff;
    }
    // both modes: landing on the base (on the concrete, slowed down) rearms, refuels and repairs at once
    const needs = p.hp < p.spec.hp || p.fm.fuel < p.spec.internalFuel * 0.95 || p.gun.ammo < p.spec.gun.ammo ||
      p.stations.some((s) => !s.loaded) || p.flares < p.spec.cm.flares;
    if (p.onGround && p.speed < 25 && needs && field.onPaved(p.pos.x, p.pos.y)) {
      p.rearm(); p.hp = p.spec.hp; p.burning = false; p.fm.fuel = p.spec.internalFuel;
      for (const s of p.stations) s.reload = undefined;
      this.hud.message('ÚJRAFEGYVERZÉS, TANKOLÁS, JAVÍTÁS KÉSZ', 'good', 4, 'service');
      if (!this.tutorial) this.medal('home');
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

// the aircraft built in Blender (tools/blender): assets/<model>.glb
const GLB_MODELS = ['f16', 'fa18', 'f22', 'f15', 'f35', 'su35', 'su57', 'mig29', 'mig31', 'gripen', 'typhoon', 'rafale', 'j20', 't38', 't45', 't6'];

async function boot() {
  const status = $('status'), bar = $('bar');
  if (!THREE) { status.textContent = 'A three.js nem töltődött be - ellenőrizd az internetkapcsolatot.'; return; }
  let done = 0;
  const total = 10 + GLB_MODELS.length;
  const tick = () => { done++; bar.style.width = `${done / total * 100}%`; };
  let assets;
  try {
    const [f16, terrain, viper, aggressor, terrainTex, cockpitTex, glbAim9, glbAim120, ...jets] = await Promise.all([
      fetchJSON(assetUrl('f16.json'), tick), fetchJSON(assetUrl('terrain.json'), tick),
      loadTexture(assetUrl('livery_viper.jpg'), tick), loadTexture(assetUrl('livery_aggressor.jpg'), tick),
      loadTexture(assetUrl('terrain_color.jpg'), tick), loadTexture(assetUrl('cockpit.png'), tick),
      fetchGLB(assetUrl('aim9m.glb'), tick), fetchGLB(assetUrl('aim120c.glb'), tick),
      ...GLB_MODELS.map((k) => fetchGLB(assetUrl(`${k}.glb`), tick))]);
    const glb = { aim9m: glbAim9, aim120c: glbAim120 };
    GLB_MODELS.forEach((k, i) => { glb[k] = jets[i]; });
    assets = { f16, terrain, viper, aggressor, terrainTex, cockpitTex, glb };
  } catch (e) {
    status.textContent = 'Betöltési hiba: ' + e.message; console.error(e); return;
  }
  status.textContent = 'Kész!';
  $('loading').hidden = true;
  $('menu').hidden = false;
  // offer the one-file offline copy where a plain download link works (GitHub Pages or a local server)
  if (!window.DOGFIGHT_ASSETS && /github\.io$|^localhost$|^127\./.test(location.hostname)) $('download').hidden = false;
  // Settings: mouse (aim and cockpit stick sensitivity 5..200 %, inverted Y), sound, voice, graphics quality,
  // field of view, time of day, touch controls and rumble.  Every control carries data-key; the main menu and
  // the pause screen show the same values; all of it is remembered in this browser.
  const settings = { googleKey: '', aim: 60, stick: 60, invert: false, volume: 70, voice: true, quality: 'high', fov: 70, tod: 'day', touch: 'auto', rumble: true,
    music: 'off', musicVol: 50, keys: {} };
  // music (console-sound): starts on the first click (browsers keep audio silent until the player acts)
  const music = window.dogfightMusic = new Music();
  const syncMusic = () => {
    music.setVolume(settings.musicVol / 100);
    if (music.track !== settings.music && (settings.music !== 'own' || music.ownUrl)) music.play(settings.music);
  };
  addEventListener('pointerdown', () => { if (music.ctx && music.ctx.state !== 'running') music.ctx.resume(); syncMusic(); }, { once: true });
  const hangar = window.dogfightHangar = new Hangar();
  try { Object.assign(settings, JSON.parse(localStorage.getItem('dogfight-settings') || '{}')); } catch (e) { /* private mode */ }
  const applySettings = () => {
    for (const el of document.querySelectorAll('[data-key]')) {
      const v = settings[el.dataset.key];
      if (el.matches('.sens-val')) el.textContent = `${v}${el.dataset.unit || '%'}`;
      else if (el.type === 'checkbox') el.checked = !!v;
      else if (el.type === 'radio') el.checked = el.value === String(v);
      else el.value = v;
    }
    if (window.game) window.game.applySettings(settings);
    if (navigator.userActivation ? navigator.userActivation.hasBeenActive : music.ctx) syncMusic();
    try { localStorage.setItem('dogfight-settings', JSON.stringify(settings)); } catch (e) { /* private mode */ }
  };
  for (const el of document.querySelectorAll('select[data-key]')) {
    el.addEventListener('change', () => { settings[el.dataset.key] = el.value; applySettings(); });
  }
  $('own-music').addEventListener('change', (e) => {
    const f = e.target.files[0]; if (!f) return;
    music.loadOwn(f); $('own-name').textContent = f.name;
    settings.music = 'own'; music.track = null; applySettings();
  });
  keyEditor($('keys-list'), settings.keys, applySettings);
  for (const el of document.querySelectorAll('input[data-key]')) {
    const key = el.dataset.key;
    el.addEventListener(el.type === 'range' ? 'input' : 'change', () => {
      if (el.type === 'range') settings[key] = Number(el.value);
      else if (el.type === 'checkbox') settings[key] = el.checked;
      else if (el.type === 'radio' && el.checked) settings[key] = el.value;
      else if (el.type === 'text') settings[key] = el.value.trim();
      applySettings();
    });
    el.addEventListener('click', (e) => e.stopPropagation());
  }
  for (const el of document.querySelectorAll('#pause .seg label')) el.addEventListener('click', (e) => e.stopPropagation());
  applySettings();
  // Career: totals and medals over every match (career.js), shown in the main menu
  const career = window.dogfightCareer = new Career();
  const renderCareer = () => {
    const c = career.data, got = ACHIEVEMENTS.filter((a) => career.has(a.id)).length;
    const acc = c.missilesFired ? Math.round((c.irKills + c.arhKills) / c.missilesFired * 100) : 0;
    const stat = (v, t) => `<div class="stat"><b>${v}</b><span>${t}</span></div>`;
    $('career-body').innerHTML = `<div class="stats">${stat(c.kills, 'lelövés')}${stat(c.deaths, 'halál')}` +
      `${stat(c.deaths ? (c.kills / c.deaths).toFixed(2) : c.kills, 'K/D arány')}${stat(c.bestScore, 'legjobb pont')}` +
      `${stat(c.bestWave, 'legjobb hullám')}${stat(c.bestSurvival, 'túlélés rekord')}${stat(c.bestStreak, 'leghosszabb sorozat')}` +
      `${stat(c.duelWins, 'megnyert párbaj')}${stat(`${c.gunKills} / ${c.irKills} / ${c.arhKills}`, 'ágyú / AIM-9 / AIM-120')}` +
      `${stat(acc + '%', 'rakéta-találati arány')}${stat(formatTime(c.flightTime), 'repült idő')}${stat(`${got} / ${ACHIEVEMENTS.length}`, 'kitüntetés')}</div>` +
      `<div class="medals">${ACHIEVEMENTS.map((a) => `<div class="medal${career.has(a.id) ? ' got' : ''}"><b>${a.name}</b>${a.desc}</div>`).join('')}</div>`;
  };
  renderCareer();
  $('career-reset').addEventListener('click', () => {
    if (confirm('Biztosan törlöd az összes statisztikát és kitüntetést?')) { career.reset(); renderCareer(); }
  });
  // the menu's choices are remembered too
  const MENU_KEY = 'dogfight-menu';
  let menuSaved = {};
  try { menuSaved = JSON.parse(localStorage.getItem(MENU_KEY) || '{}'); } catch (e) { /* private mode */ }
  const pick = (name) => document.querySelector(`input[name=${name}]:checked`).value;
  const setPick = (name, v) => { const el = document.querySelector(`input[name=${name}][value="${v}"]`); if (el) el.checked = true; };
  // the plane picker (every jet, in groups) and the enemy chips (any number of them)
  const ALL = { ...AIRCRAFT, ...TRAINERS };
  $('plane-pick').innerHTML = PLANE_GROUPS.map(([g, keys]) => `<div class="grp"><span>${g}</span>${keys.map((k) =>
    `<input type="radio" name="plane" id="p-${k}" value="${k}"${k === 'f16' ? ' checked' : ''}><label for="p-${k}">${ALL[k].short}</label>`).join('')}</div>`).join('');
  $('foe-pick').innerHTML = PLANE_GROUPS.filter(([g]) => g !== 'Gyakorlógépek').map(([g, keys]) => `<div class="grp"><span>${g}</span>${keys.filter((k) => BANDITS[k]).map((k) =>
    `<input type="checkbox" name="foe" id="f-${k}" value="${k}"><label for="f-${k}">${ALL[k].short}</label>`).join('')}</div>`).join('');
  const foes = () => [...document.querySelectorAll('input[name=foe]:checked')].map((e) => e.value);
  for (const k of menuSaved.foes && menuSaved.foes.length ? menuSaved.foes : [menuSaved.foe && menuSaved.foe !== 'mixed' ? menuSaved.foe : 'f16']) { const el = $('f-' + k); if (el) el.checked = true; }
  const foeHint = () => { const n = foes().length; $('foe-hint').textContent = n ? `${n} típus · kattints újra a kivételhez` : 'jelölj ki legalább egyet (különben F-16C jön)'; };
  for (const name of ['plane', 'mode', 'diff', 'scen', 'wing']) if (menuSaved[name] !== undefined) setPick(name, menuSaved[name]);
  if (!document.querySelector('input[name=plane]:checked')) $('p-f16').checked = true;
  if (menuSaved.enemies) $('enemies').value = menuSaved.enemies;
  // the place (world map): saved with the menu, built when a match starts there
  let place = menuSaved.place || PLACES[0];
  const showPlace = () => { $('place-name').textContent = place.name; };
  showPlace();
  const picker = new MapPicker();
  $('place-open').addEventListener('click', () => picker.open(place, (p) => { place = p; showPlace(); saveMenu(); }));
  const placeKey = (p) => (p && p.lat !== null && p.lat !== undefined ? `${p.lat.toFixed(4)},${p.lon.toFixed(4)}` : 'island');
  const saveMenu = () => {
    const m = { arms: menuSaved.arms || {}, place };
    for (const name of ['plane', 'mode', 'diff', 'scen', 'wing']) m[name] = pick(name);
    m.foes = foes();
    m.enemies = $('enemies').value;
    menuSaved = m;
    try { localStorage.setItem(MENU_KEY, JSON.stringify(m)); } catch (e) { /* private mode */ }
  };
  const SCEN_HINT = { waves: 'egyre nagyobb hullámok, a bázison újratölthetsz', duel: '1 ellenfél szemből - minden kör tele géppel, a levegőben indul',
    survival: 'egy életed van, a hullámok gyorsan jönnek - meddig bírod?' };
  const DIFF_HINT = { easy: 'pont ×0,6', normal: 'pont ×1', hard: 'pont ×1,5', ace: 'teljes erejű ellenfél · pont ×2' };
  const showHints = () => { $('scen-hint').textContent = SCEN_HINT[pick('scen')]; $('diff-hint').textContent = DIFF_HINT[pick('diff')]; };
  for (const el of document.querySelectorAll('input[name=scen], input[name=diff], input[name=foe], input[name=wing], #enemies')) {
    el.addEventListener('change', () => { showHints(); foeHint(); saveMenu(); });
  }
  foeHint();
  showHints();
  // Loadout editor: how many AIM-9M and AIM-120A; the stations are filled like the real jet would carry them
  // (specs.js buildLoadout), the row of chips shows where each one hangs.
  const arms = { 'AIM-9M': 0, 'AIM-120A': 0 };
  // hangar (shop): credits and paint
  const hangarUI = new HangarUI(hangar, career, () => refreshShop());
  const refreshShop = () => {
    $('menu-credits').textContent = `${hangar.data.credits.toLocaleString('hu-HU')} kredit · festés: ${hangar.skin.name}`;
  };
  $('open-hangar').addEventListener('click', () => hangarUI.open());
  hangar.onChange(refreshShop);
  refreshShop();
  const plane = () => ALL[document.querySelector('input[name=plane]:checked').value];
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
    menuSaved.arms = { ...(menuSaved.arms || {}), [spec.id]: { ...arms } };
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
      f15: '2 × F110 · 263 kN · 9 G, nagy tolóerő, akár 12 rakéta, APG-82',
      f15a: '2 × F100-229 · 258 kN · TVC (Tab), kacsaszárny, Cobra',
      f16: '1 × F110 · 132 kN · 9 G, jobb tolóerő/tömeg',
    }[spec.id] || `${spec.name} · ${spec.engines} hajtómű, ${Math.round(spec.thrustAb / 1000)} kN · ${spec.gMax} G${spec.trainer ? ' · gyakorlógép, fegyver nélkül' : ''}`;
  };
  const restoreArms = (spec) => { const a = menuSaved.arms && menuSaved.arms[spec.id]; if (a) Object.assign(arms, a); else defaults(spec); };
  for (const el of document.querySelectorAll('input[name=plane]')) el.addEventListener('change', () => { restoreArms(plane()); showLoadout(); saveMenu(); });
  for (const [id, key, d] of [['m9', 'AIM-9M', -1], ['p9', 'AIM-9M', 1], ['m120', 'AIM-120A', -1], ['p120', 'AIM-120A', 1]]) {
    $(id).addEventListener('click', () => { arms[key] += d; showLoadout(); saveMenu(); });
  }
  $('ld-default').addEventListener('click', () => { defaults(plane()); showLoadout(); saveMenu(); });
  restoreArms(plane()); showLoadout();
  // The main menu starts a match, and the game can come back to it any time (Esc -> Főmenü), during a match
  // or after it: from there the match continues (Folytatás) or a new one starts on the same scene.
  const start = (airStart, tutorial = false, benchmark = false) => {
    const difficulty = document.querySelector('input[name=diff]:checked').value;
    const enemies = Number($('enemies').value);
    const mode = document.querySelector('input[name=mode]:checked').value;
    const aircraft = document.querySelector('input[name=plane]:checked').value;
    const enemyTypes = foes().length ? foes() : ['f16'];
    const loadout = buildLoadout(ALL[aircraft], arms['AIM-9M'], arms['AIM-120A']).layout;
    const scenario = tutorial ? 'waves' : pick('scen'), wingman = tutorial ? 0 : Number(pick('wing'));
    const opts = benchmark
      ? { airStart: true, difficulty: 'normal', enemies: 4, mode: 'arcade', aircraft, enemyTypes: ['f16', 'fa18', 'su35', 'typhoon'], loadout, tutorial: false, scenario: 'waves', wingman: 0, benchmark: true }
      : { airStart: (airStart === true) || tutorial, carrierStart: airStart === 'carrier' && !tutorial, difficulty, enemies, mode: tutorial ? 'arcade' : mode, aircraft, enemyTypes, loadout, tutorial, scenario, wingman };
    saveMenu();
    if (!tutorial && !benchmark) { career.data.matches++; career.save(); }
    $('menu').hidden = true;
    let game = window.game;
    const fresh = !game;
    if (game && placeKey(game.place) === placeKey(place)) game.newMatch(opts);
    else if (game) { goPlace(game, opts); return; }
    else {
      game = makeGame(opts);
      if (!game) return;
    }
    applySettings();
    if (fresh && placeKey(place) !== 'island') { goPlace(game, opts); return; }
    game.resume();
  };
  // the one game object: made on the first start, then reused (new matches on the same scene)
  function makeGame(opts) {
    let game;
    try { game = new Game(assets, opts); }
    catch (e) { console.error(e); $('menu').hidden = false; $('menuerr').textContent = 'Hiba: ' + e.message + ' (WebGL szükséges)'; return null; }
    window.game = game;
    {
      game.onTutorialEnd = () => { showMenu(); $('current').textContent = 'Az oktatás véget ért. Folytatás = szabad repülés hullámokkal, vagy indíts új játékot.'; };
      // performance test done: pick the quality from the measured frame rate (console-tester)
      game.onBenchmark = (r) => {
        const was = settings.quality, order = ['low', 'medium', 'high'], names = { low: 'Gyors', medium: 'Közepes', high: 'Szép' };
        let q = was;
        if (r.fps < 28 || r.low < 20) q = order[Math.max(0, order.indexOf(was) - 1)];
        else if (r.fps > 55 && r.low > 40) q = order[Math.min(2, order.indexOf(was) + 1)];
        settings.quality = q; applySettings();
        game.newMatch({ ...game.opts, benchmark: false }); game.state.paused = true;
        showMenu();
        $('current').textContent = 'Teszt kész – indíts új játékot.';
        $('menu').querySelector('details.more').open = true;
        $('bench-msg').textContent = `Átlag ${Math.round(r.fps)} FPS, a leglassabb 10%: ${Math.round(r.low)} FPS (${names[was]}) → ${q === was ? 'a mostani beállítás jó' : 'beállítva: ' + names[q]}.`;
      };
    }
    return game;
  }
  // career mode (careermode.js): one flight with its own activity (back seat, school, mission), at a place of
  // the world ({lat, lon, name}) or on the island (null).  Resolves with the game once it flies.
  const launch = async (o, where) => {
    const spec = ALL[o.aircraft] || ALL.f16;
    let loadout = 'default';
    try {
      const l = Object.values(spec.loadouts.default);
      loadout = buildLoadout(spec, l.filter((k) => k === 'AIM-9M').length, l.filter((k) => k === 'AIM-120A').length).layout;
    } catch (e) { /* the spec's own default */ }
    const opts = { airStart: false, carrierStart: false, difficulty: 'normal', enemies: 0, mode: 'realistic', enemyTypes: ['su35'], loadout,
      tutorial: false, scenario: 'waves', wingman: 0, ...o, aircraft: spec.id in ALL ? spec.id : o.aircraft };
    $('menu').hidden = true;
    let game = window.game;
    if (!game) { game = makeGame({ ...opts, activity: null }); if (!game) return null; }
    if (placeKey(game.place) !== placeKey(where)) {
      $('worldload').hidden = false; $('wl-name').textContent = where ? where.name : 'Sziget'; $('wl-bar').style.width = '0%';
      try { await game.loadPlace(where, (msg, f) => { $('wl-status').textContent = msg; $('wl-bar').style.width = `${Math.round(f * 100)}%`; }); }
      catch (e) {
        console.error(e);
        $('wl-status').textContent = `Nem sikerült letölteni (${e.message}) – a szigeten repülsz.`;
        await new Promise((r) => setTimeout(r, 2000));
        await game.loadPlace(null);
      }
      $('worldload').hidden = true;
    }
    applySettings();
    game.newMatch(opts);
    if (o.tod) game.view.setTimeOfDay(o.tod);
    game.resume();
    return game;
  };
  const careerMode = new CareerMode(launch);
  careerMode.onClose = () => goLobby();
  window.dogfightCareerMode = careerMode;
  $('open-career').addEventListener('click', () => { const g = window.game; if (g) { g.inMenu = true; g.pause(); g.showOverlay(null); } careerMode.open(); });
  // a match somewhere else: download and build the place (progress screen), then start
  const goPlace = async (game, opts) => {
    $('worldload').hidden = false; $('wl-name').textContent = place.name; $('wl-bar').style.width = '0%';
    try {
      await game.loadPlace(place, (msg, f) => { $('wl-status').textContent = msg; $('wl-bar').style.width = `${Math.round(f * 100)}%`; });
    } catch (e) {
      console.error(e);
      $('wl-status').textContent = `Nem sikerült (${e.message}) – az eredeti szigeten indul.`;
      await new Promise((r) => setTimeout(r, 2500));
      place = PLACES[0]; showPlace(); saveMenu();
      await game.loadPlace(null);
    }
    game.newMatch(opts);
    $('worldload').hidden = true;
    applySettings();
    game.resume();
  };
  // the entry view: the air base itself (base.js Lobby), the menu to the left of it.  Leaving a fight comes back
  // here; only the Kilépés button leaves the game.
  const lobbyOpts = () => ({ airStart: false, carrierStart: false, difficulty: 'normal', enemies: 0, mode: 'arcade', aircraft: document.querySelector('input[name=plane]:checked').value,
    enemyTypes: ['f16'], loadout: 'default', tutorial: false, scenario: 'waves', wingman: 0, lobby: true, activity: (g) => new Lobby(g) });
  const showLobbyMenu = () => {
    const game = window.game;
    renderCareer(); refreshShop();
    $('menu').classList.add('lobby');
    $('continue').hidden = true; $('current').hidden = true;
    $('start-ground').classList.add('primary');
    $('menu').hidden = false;
    if (game) { game.inMenu = true; game.pause(); game.showOverlay(null); }
    $('start-ground').focus();
  };
  const goLobby = async () => {
    let game = window.game;
    const opts = lobbyOpts();
    $('menu').hidden = true;
    if (!game) { game = makeGame(opts); if (!game) return; }
    else {
      try { if (game.place) await game.loadPlace(null); } catch (e) { console.error(e); }
      game.newMatch(opts);
    }
    game.onLobbyStart = () => start(false);
    game.onLobbyEsc = () => showLobbyMenu();
    game.onLobbySelect = (k) => { const el = document.querySelector(`input[name=plane][value="${k}"]`); if (el) { el.checked = true; el.dispatchEvent(new Event('change')); } };
    applySettings();
    showLobbyMenu();
  };
  const showMenu = () => { goLobby(); };
  window.dogfightLobby = goLobby;
  $('lobby-walk').addEventListener('click', () => { const g = window.game; if (g) { $('menu').hidden = true; g.resume(); } });
  $('quit').addEventListener('click', () => { if (window.game) window.game.pause(); try { window.close(); } catch (e) { /* not allowed */ } $('bye').hidden = false; });
  $('bye-back').addEventListener('click', () => { $('bye').hidden = true; });
  $('continue').addEventListener('click', () => window.game && window.game.resume());
  $('to-menu').addEventListener('click', (e) => { e.stopPropagation(); showMenu(); });
  $('resume').addEventListener('click', (e) => { e.stopPropagation(); if (window.game) window.game.resume(); });
  $('help-btn').addEventListener('click', (e) => { e.stopPropagation(); if (window.game) window.game.toggleHelp(); });
  for (const el of document.querySelectorAll('input[name=mode]')) {
    el.addEventListener('change', () => {
      $('mode-hint').textContent = el.value === 'arcade' ? 'rakéták 10 s alatt újratöltődnek' : 'újratöltés csak leszállás után';
      saveMenu();
    });
  }
  if (pick('mode') !== 'arcade') $('mode-hint').textContent = 'újratöltés csak leszállás után';
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
  $('start-carrier').addEventListener('click', () => start('carrier'));
  $('start-tutorial').addEventListener('click', () => start(true, true));
  $('bench').addEventListener('click', (e) => { e.stopPropagation(); $('bench-msg').textContent = 'Fut…'; start(true, false, true); });
  // installable app (console-anywhere): offered where the browser allows it (served over https / localhost)
  let installEvt = null;
  addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); installEvt = e; $('install-row').hidden = false; });
  $('install').addEventListener('click', async () => { if (!installEvt) return; installEvt.prompt(); await installEvt.userChoice; installEvt = null; $('install-row').hidden = true; });
  if ('serviceWorker' in navigator && !window.DOGFIGHT_ASSETS && location.protocol !== 'file:') navigator.serviceWorker.register('sw.js').catch(() => {});
  $('help').addEventListener('click', () => window.game && window.game.resume());
  $('fullscreen').addEventListener('click', (e) => {
    e.stopPropagation();
    const el = document.documentElement;
    if (document.fullscreenElement) document.exitFullscreen(); else if (el.requestFullscreen) el.requestFullscreen().catch(() => {});
  });
  goLobby();                                    // the entry view
}

// leaving by accident (Ctrl+W while Ctrl is the throttle key) asks first
addEventListener('beforeunload', (e) => {
  if (window.game && !window.game.state.paused) { e.preventDefault(); e.returnValue = ''; }
});

boot();
