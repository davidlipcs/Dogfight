// Browser entry point: asset loading, camera, input, game flow and the main loop (port of dogfight/game.py,
// camera.py and controls.py).
import { THREE, V, add, sub, mul, dot, cross, len, norm, clamp, DEG, qaxis, qmul, qlook, fwdOf, upOf, xform, rng } from './util.js';
import { F16C, IR } from './specs.js';
import { Terrain } from './terrain.js';
import { Aircraft, World } from './sim.js';
import { PlayerPilot, AIPilot } from './ai.js';
import { Models, SceneView } from './render.js';
import { HUD } from './hud.js';
import { Sounds } from './audio.js';

const PLAYER_START = V(0, -26000, 4500);
const TAKEOFF_HINT = 'FELSZÁLLÁS: Shift = gáz (100% felett utánégető)  ·  ~280 km/h-nál emeld az egeret  ·  G = futómű';
const WAVE_DELAY = 5, FIRST_WAVE_DELAY = 25, REARM_TIME = 6, MAX_ENEMIES = 6, THROTTLE_RATE = 0.55;
const CHASE_DISTANCE = 26, CHASE_HEIGHT = 5.5;
const CAM_FIX = qaxis(V(1, 0, 0), Math.PI / 2);     // three.js cameras look down -Z with +Y up

const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------------ camera
class FlightCamera {
  constructor(camera, terrain) {
    this.camera = camera; this.terrain = terrain; this.eye = V(0, 2.4, 1.1);
    this.sensitivity = 0.09; this.invertY = false;
    this.aim = new THREE.Quaternion(); this.look = new THREE.Quaternion();
    this.freeLook = false; this.cockpit = false; this.position = V(); this.fov = 70; this.phase = 0; this.zoom = 0;
  }
  reset(ac) { this.aim = qlook(ac.forward); this.look = this.aim.clone(); }
  aimDirection() { return fwdOf(this.aim); }
  setFreeLook(on) { if (on && !this.freeLook) this.look = this.aim.clone(); this.freeLook = on; }
  rotate(yawDeg, pitchDeg) {
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
    const view = this.freeLook ? this.look : this.aim;
    if (this.cockpit && ac.alive) this.position = add(ac.pos, xform(ac.quat, this.eye));
    else {
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
    const target = [this.cockpit ? 75 : 70, 45, 28][this.zoom];
    this.fov += (target - this.fov) * Math.min(1, dt * 8);
    if (Math.abs(cam.fov - this.fov) > 0.01) { cam.fov = this.fov; cam.updateProjectionMatrix(); }
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
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      this.codeName.set(e.code, name);
      if (!this.held.has(name) && this.handlers.press) this.handlers.press(name);
      this.held.add(name);
    });
    addEventListener('keyup', (e) => { const n = this.codeName.get(e.code) || Input.name(e); this.held.delete(n); this.codeName.delete(e.code); });
    addEventListener('blur', () => { this.held.clear(); this.codeName.clear(); this.mouse = [false, false, false]; });
    el.addEventListener('mousedown', (e) => {
      if (e.button === 1) e.preventDefault();          // middle button: no autoscroll
      this.mouse[e.button] = true; if (this.handlers.mousedown) this.handlers.mousedown(e);
    });
    addEventListener('mouseup', (e) => { this.mouse[e.button] = false; });
    addEventListener('mousemove', (e) => {
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
    this.models = new Models(assets.f16, { viper: assets.viper, aggressor: assets.aggressor, terrain: assets.terrainTex, cockpit: assets.cockpitTex });
    this.view = new SceneView(this.renderer, this.models, this.terrain, this.world);
    this.cam = new FlightCamera(this.view.camera, this.terrain);
    if (this.models.eye) this.cam.eye = V(...this.models.eye);
    this.hud = new HUD($('hud'));
    this.sounds = new Sounds(0.7);
    this.input = new Input(canvas);
    this.state = { wave: 0, kills: 0, deaths: 0, banner: '', subBanner: '', paused: true, waveTimer: FIRST_WAVE_DELAY, rearmTimer: 0, waveActive: false };
    this.player = null; this.pilot = null; this.helpVisible = false; this.locked = false;
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
    this.spawnPlayer();
    this.resize();
    addEventListener('resize', () => this.resize());
    this.last = performance.now();
    this.fpsAcc = 0; this.fpsN = 0;
    requestAnimationFrame((t) => this.frame(t));
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
      pos = PLAYER_START.clone();
      pos.z = Math.max(pos.z, this.terrain.height(pos.x, pos.y) + 1500); speed = 250;
    } else {
      const [x, y, hdg] = field.startPosition();
      pos = V(x, y, 0); heading = hdg;
    }
    const ac = new Aircraft(F16C, 'Te (Viper 1)', 'blue', pos, heading, speed, { isPlayer: true, livery: 'viper', rnd: rng(Math.floor(this.rnd() * 1e9)) });
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

  spawnWave() {
    const st = this.state, p = this.player, r = this.rnd;
    st.wave++;
    const count = Math.min(this.opts.enemies + st.wave - 1, MAX_ENEMIES);
    const ahead = norm(V(p.forward.x, p.forward.y, 0), V(0, 1, 0));
    const center = add(p.pos, mul(ahead, r.uniform(32000, 40000)));
    const [cx, cy] = this.terrain.clampInside(center.x, center.y, 9000);
    const side = V(ahead.y, -ahead.x, 0);
    for (let i = 0; i < count; i++) {
      const pos = add(V(cx, cy, 0), mul(side, (i - (count - 1) / 2) * 3500 + r.uniform(-800, 800)));
      pos.z = Math.max(r.uniform(3000, 7500), this.terrain.height(pos.x, pos.y) + 1500);
      const to = sub(p.pos, pos);
      const heading = Math.atan2(to.x, to.y) / DEG;
      const ac = new Aircraft(F16C, `Bandita ${i + 1}`, 'red', pos, heading, 240, { livery: 'aggressor', rnd: rng(Math.floor(r() * 1e9)) });
      new AIPilot(ac, this.opts.difficulty);
      this.world.addAircraft(ac);
    }
    st.waveActive = true;
    this.hud.message(`${st.wave}. HULLÁM - ${count} ellenség`, 'warn', 4);
  }
  enemiesAlive() { return this.world.aircraft.filter((a) => a.team !== 'blue' && a.alive); }

  // ------------------------------------------------------------------ input
  canAct() { return !this.state.paused && this.player && this.player.alive; }
  onKey(k) {
    if (k === 'h' || k === 'F1') { this.toggleHelp(); return; }
    if (k === 'Escape') { if (!this.state.paused) this.pause(); return; }
    if (k === 'p') { if (this.state.paused) this.resume(); else this.pause(); return; }
    if (k === 'Enter' || k === 'NumpadEnter') { this.respawn(); return; }
    if (k === 'm') { this.hud.markers = !this.hud.markers; return; }
    if (k === 'v') { this.cam.cockpit = !this.cam.cockpit; return; }
    if (!this.canAct()) return;
    const p = this.player, msg = (t, l = 'info', d = 1.5) => this.hud.message(t, l, d);
    switch (k) {
      case 'Space': {
        const m = p.fireMissile(this.world);
        if (m) msg(m.spec.guidance === IR ? 'FOX 2' : 'FOX 3');
        break;
      }
      case 'f':
        if (!p.selectedSpec || p.selectedSpec.guidance !== IR) p.select('AIM-9M');
        if (p.irSeeker.locked) { p.irSeeker.unlock(); msg('KERESŐ ELENGEDVE', 'info', 1.2); }
        else if (p.toggleIrLock()) msg('SEEKER LOCK', 'good');
        else msg('Nincs hőforrás a keresőben', 'warn');
        break;
      case 't': {
        const res = p.radar.lockButton();
        const t = { on: ['RADAR BE', 'info'], unlocked: ['UNLOCK', 'info'], locking: ['LOCKOLÁS...', 'info'],
          acm: ['ACM MÓD - célt az orr elé!', 'warn'], search: ['RADAR KERESÉS', 'info'] }[res];
        if (t) msg(t[0], t[1], 1.6);
        break;
      }
      case 'y': p.radar.cycleTarget(); break;
      case 'r': p.radar.togglePower(); msg(`RADAR ${p.radar.on ? 'BE' : 'KI'}`, 'info', 1.2); break;
      case '1': if (p.select('AIM-9M')) msg('AIM-9M', 'info', 1); break;
      case '2': if (p.select('AIM-120A')) msg('AIM-120A', 'info', 1); break;
      case 'g':
        if (p.toggleGear()) msg(`FUTÓMŰ ${p.fm.gearDown ? 'KI' : 'BE'}`);
        else msg('A földön nem húzható be a futómű', 'warn');
        break;
    }
  }
  applyInput(dt) {
    const inp = this.input, p = this.player, c = p.controls, cam = this.cam;
    const [dx, dy] = inp.takeDelta();
    if (this.locked) cam.mouseDelta(dx, dy);
    else if (inp.inside && !this.state.paused) {
      // no pointer lock (e.g. blocked by the page): the cursor works as a joystick around the screen centre
      const dz = (v) => (Math.abs(v) < 0.06 ? 0 : (v - Math.sign(v) * 0.06) / 0.94);
      cam.rotate(-dz(inp.mx) * 95 * dt, -dz(inp.my) * 70 * dt * (cam.invertY ? -1 : 1));
    }
    this.pilot.aim = cam.aimDirection();
    this.pilot.pitch = inp.axis('s', 'w');      // S = nose up (pull), W = nose down (push)
    this.pilot.roll = inp.axis('d', 'a');
    this.pilot.yaw = inp.axis('e', 'q');
    if (inp.key('shift')) c.throttle = Math.min(1.1, c.throttle + THROTTLE_RATE * dt);
    if (inp.key('z')) c.throttle = Math.max(0, c.throttle - THROTTLE_RATE * dt);
    c.airbrake = inp.key('b');
    c.brakes = inp.key('b') && p.onGround;
    p.trigger = inp.mouse[0];
    p.cmHold = inp.key('x');
    cam.setFreeLook(inp.key('c') || inp.mouse[2]);
  }

  // ------------------------------------------------------------ pause/help
  pause() {
    this.state.paused = true;
    if (document.pointerLockElement) document.exitPointerLock();
    this.showOverlay(this.helpVisible ? null : 'pause');
  }
  resume() {
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
      st.banner = st.subBanner = ''; st.rearmTimer = 0;
      this.spawnPlayer();
    }
  }

  // ------------------------------------------------------------------ loop
  frame(t) {
    requestAnimationFrame((tt) => this.frame(tt));
    const dt = Math.min((t - this.last) / 1000, 0.1);
    this.last = t;
    const st = this.state;
    if (!st.paused) {
      if (this.player.alive) this.applyInput(dt);
      else this.input.takeDelta();
      this.world.update(dt);
      this.gameFlow(dt);
    } else this.input.takeDelta();
    for (const [kind, d] of this.world.drainEvents()) {
      this.view.handleEvent(kind, d);
      this.hud.handleEvent(kind, d, this.player);
      this.sounds.handleEvent(kind, d, this.player);
      this.onEvent(kind, d);
    }
    const sdt = st.paused ? 0 : dt;
    this.cam.update(sdt, this.player);
    this.view.cockpitView = this.cam.cockpit && this.player.alive;
    this.view.update(sdt, this.player);
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
      st.subBanner = 'Enter: újraéledés';
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
    if (st.waveActive && !this.enemiesAlive().length) {
      st.waveActive = false; st.waveTimer = WAVE_DELAY;
      this.hud.message('HULLÁM TELJESÍTVE - leszállhatsz a bázison újrafegyverezni', 'good', 5);
    }
    if (!st.waveActive && airborne) {
      st.waveTimer -= dt;
      if (st.waveTimer <= 0) this.spawnWave();
    }
    const needs = p.hp < p.spec.hp || p.fm.fuel < p.spec.internalFuel * 0.95 || p.gun.ammo < p.spec.gun.ammo ||
      p.stations.some((s) => !s.loaded) || p.flares < p.spec.cm.flares;
    if (p.onGround && p.speed < 1 && needs && field.onPaved(p.pos.x, p.pos.y)) {
      st.rearmTimer += dt;
      if (st.rearmTimer >= REARM_TIME) {
        st.rearmTimer = -1e9;
        p.rearm(); p.hp = p.spec.hp; p.burning = false; p.fm.fuel = p.spec.internalFuel;
        this.hud.message('ÚJRAFEGYVERZÉS, TANKOLÁS, JAVÍTÁS KÉSZ', 'good', 4, 'service');
      } else if (st.rearmTimer > 0.5) this.hud.message(`Kiszolgálás... ${Math.floor(REARM_TIME - st.rearmTimer + 1)} s`, 'info', 0.3, 'service');
    } else st.rearmTimer = 0;
  }
}

// ----------------------------------------------------------------- loading
async function fetchJSON(url, onDone) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  const j = await r.json(); onDone(); return j;
}
function loadTexture(url, onDone) {
  return new Promise((res, rej) => new THREE.TextureLoader().load(url, (t) => { onDone(); res(t); }, undefined, () => rej(new Error(url))));
}

async function boot() {
  const status = $('status'), bar = $('bar');
  if (!THREE) { status.textContent = 'A three.js nem töltődött be - ellenőrizd az internetkapcsolatot.'; return; }
  let done = 0;
  const tick = () => { done++; bar.style.width = `${done / 6 * 100}%`; };
  let assets;
  try {
    const [f16, terrain, viper, aggressor, terrainTex, cockpitTex] = await Promise.all([
      fetchJSON('assets/f16.json', tick), fetchJSON('assets/terrain.json', tick),
      loadTexture('assets/livery_viper.jpg', tick), loadTexture('assets/livery_aggressor.jpg', tick),
      loadTexture('assets/terrain_color.jpg', tick), loadTexture('assets/cockpit.png', tick)]);
    assets = { f16, terrain, viper, aggressor, terrainTex, cockpitTex };
  } catch (e) {
    status.textContent = 'Betöltési hiba: ' + e.message; console.error(e); return;
  }
  status.textContent = 'Kész!';
  $('loading').hidden = true;
  $('menu').hidden = false;
  const start = (airStart) => {
    const difficulty = document.querySelector('input[name=diff]:checked').value;
    const enemies = Number($('enemies').value);
    $('menu').hidden = true;
    let game;
    try { game = new Game(assets, { airStart, difficulty, enemies }); }
    catch (e) { console.error(e); $('menu').hidden = false; $('menuerr').textContent = 'Hiba: ' + e.message + ' (WebGL szükséges)'; return; }
    window.game = game;
    $('sens').addEventListener('input', (e) => { game.cam.sensitivity = Number(e.target.value); });
    game.cam.sensitivity = Number($('sens').value);
    game.cam.invertY = $('invert').checked;
    game.resume();
  };
  $('start-ground').addEventListener('click', () => start(false));
  $('start-air').addEventListener('click', () => start(true));
  $('pause').addEventListener('click', () => window.game && window.game.resume());
  $('help').addEventListener('click', () => window.game && window.game.resume());
  $('fullscreen').addEventListener('click', (e) => {
    e.stopPropagation();
    const el = document.documentElement;
    if (document.fullscreenElement) document.exitFullscreen(); else if (el.requestFullscreen) el.requestFullscreen().catch(() => {});
  });
}

boot();
