// The air base on foot: the apron with the parked jets, the operations building, the equipment container and
// the alert hut at the runway.  A first person walker (WASD, Shift = run, mouse = look) moves through it; the
// interaction points (the jet, the locker, the door) show a prompt ([E]) and a beacon you can see from afar.
// Used by the lobby (the entry view: walk along the line-up and pick your jet) and by the sorties of the career
// (walk to the jet with your kit, and back to the ops building after the landing).
// All positions are metres from the middle of the air base (the field), x east, y north.
import { THREE, V, clamp, DEG } from './util.js';
import { APRON, TAXIWAY_OFFSET, TAXIWAY_WIDTH } from './terrain.js';
import { AIRCRAFT, TRAINERS, PLANE_GROUPS } from './specs.js';

const $ = (id) => document.getElementById(id);

// where things are (relative to the field)
export const SPOTS = {
  ops: [420, 320],            // operations building centre (30 x 16 m)
  door: [420, 311],           // its door, on the south side
  locker: [398, 300],         // the life support container: helmet, G suit, harness
  jet: [275, 150],            // the parking place of your jet (nose west)
  jetHeading: 270,
  alertHut: [52, -1345],      // the quick reaction shed next to the runway
  alertJet: [0, -1380],       // the jet on alert: on the runway, ready
  lineup: { x: [262, 340], y0: -330, dy: 52, rows: 9 },   // the display line of all types (lobby)
  gate: [330, 108],           // where you stand when you walk in
};
export const EYE = 1.72, WALK = 3.4, RUN = 7.0;

const sign = (text, w = 8, h = 2) => {
  const c = document.createElement('canvas'); c.width = 512; c.height = Math.round(512 * h / w);
  const g = c.getContext('2d');
  g.fillStyle = '#16212a'; g.fillRect(0, 0, c.width, c.height);
  g.strokeStyle = '#d9b13a'; g.lineWidth = 6; g.strokeRect(6, 6, c.width - 12, c.height - 12);
  g.fillStyle = '#f3f0e0'; g.font = `700 ${Math.round(c.height * 0.44)}px sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(text, c.width / 2, c.height / 2 + 3);
  const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding;
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: t }));
};

// ---------------------------------------------------------------------------------------- the base
export class Base {
  constructor(game) {
    this.g = game; this.group = null; this.points = []; this.obstacles = []; this.beacons = []; this.walker = new Walker(game, this);
    this.time = 0; this.prompt = null;
    this.hud = $('walkhud');
  }
  get field() { return this.g.terrain.airfield; }
  // world position of a field-relative spot
  at(rel, z = 0) { const f = this.field; return V(f.x + rel[0], f.y + rel[1], f.elevation + z); }
  rel(p) { const f = this.field; return [p.x - f.x, p.y - f.y]; }
  // (re)build the buildings for the current map
  build() {
    this.dispose();
    const g = this.group = new THREE.Group(), f = this.field;
    g.position.set(f.x, f.y, f.elevation);
    this.obstacles = [];
    const box = (w, d, h, color, x, y, z = 0) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, d, h), new THREE.MeshLambertMaterial({ color }));
      m.position.set(x, y, z + h / 2); m.castShadow = m.receiveShadow = true; g.add(m); return m;
    };
    // operations building: walls, a flat roof, windows, a door on the south side, a sign
    const [ox, oy] = SPOTS.ops;
    box(30, 16, 5, 0x9a9a92, ox, oy);
    box(31, 17, 0.5, 0x5a5d58, ox, oy, 5);
    box(5, 0.4, 3, 0x2c3f4a, ox, oy - 8.05, 0);                       // the door
    for (const wx of [-10, -5, 5, 10]) box(2.4, 0.3, 1.4, 0x2c4450, ox + wx, oy - 8.05, 1.9);
    const s = sign('MŰVELETI ÉPÜLET', 9, 1.6); s.rotation.x = Math.PI / 2; s.position.set(ox, oy - 8.2, 4.2); g.add(s);
    this.obstacles.push({ x0: ox - 15.5, x1: ox + 15.5, y0: oy - 8.5, y1: oy + 8.5 });
    // the life support container
    const [lx, ly] = SPOTS.locker;
    box(6, 2.6, 2.6, 0x3d5a4a, lx, ly);
    const ls = sign('FELSZERELÉS', 5, 1); ls.rotation.x = Math.PI / 2; ls.position.set(lx, ly - 1.35, 1.6); g.add(ls);
    this.obstacles.push({ x0: lx - 3.2, x1: lx + 3.2, y0: ly - 1.5, y1: ly + 1.5 });
    // the alert hut by the runway start
    const [ax, ay] = SPOTS.alertHut;
    box(9, 5, 3, 0x7d6f4e, ax, ay);
    const as = sign('RIADÓ · QRA', 6, 1.2); as.rotation.x = Math.PI / 2; as.rotation.z = Math.PI / 2; as.position.set(ax - 4.6, ay, 2.1); g.add(as);
    this.obstacles.push({ x0: ax - 4.8, x1: ax + 4.8, y0: ay - 2.8, y1: ay + 2.8 });
    // the buildings the airfield already has (render.js): tower, hangar, shelters
    const [tx, , ay0, ay1] = [TAXIWAY_OFFSET, 0, APRON[2], APRON[3]];
    this.obstacles.push({ x0: tx + 80 - 6, x1: tx + 80 + 6, y0: ay0 - 66, y1: ay0 - 54 });
    this.obstacles.push({ x0: tx + 120 - 41, x1: tx + 120 + 41, y0: ay1 + 80 - 31, y1: ay1 + 80 + 31 });
    for (let k = 0; k < 6; k++) this.obstacles.push({ x0: APRON[1] - 40 - 19, x1: APRON[1] - 40 + 19, y0: APRON[2] + 60 + k * 115 - 14, y1: APRON[2] + 60 + k * 115 + 14 });
    for (let k = 0; k < 4; k++) this.obstacles.push({ c: [APRON[1] + 60, APRON[2] + 40 + k * 22], r: 8.5 });
    // flag poles with windsocks
    for (const [px, py] of [[SPOTS.gate[0] + 60, SPOTS.gate[1] + 40]]) {
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, 9, 8).rotateX(Math.PI / 2), new THREE.MeshLambertMaterial({ color: 0xdddddd }));
      pole.position.set(px, py, 4.5); g.add(pole);
      const sock = new THREE.Mesh(new THREE.ConeGeometry(0.7, 3, 12).rotateZ(-Math.PI / 2), new THREE.MeshLambertMaterial({ color: 0xff7a1a }));
      sock.position.set(px + 1.6, py, 8.6); g.add(sock);
    }
    this.g.view.scene.add(g);
  }
  dispose() {
    if (this.group) { this.g.view.scene.remove(this.group); this.group.traverse((o) => { if (o.geometry) o.geometry.dispose(); }); this.group = null; }
    this.clearBeacons();
    if (this.lineupGroup) { this.g.view.scene.remove(this.lineupGroup); this.lineupGroup = null; }
  }
  // parked jets of the line-up (lobby): one model per type except the one that is yours (the real aircraft)
  buildLineup(types, mine) {
    if (this.lineupGroup) this.g.view.scene.remove(this.lineupGroup);
    const g = this.lineupGroup = new THREE.Group(), f = this.field, L = SPOTS.lineup;
    g.position.set(f.x, f.y, f.elevation);
    this.lineup = [];
    let i = 0;
    for (const key of types) {
      const col = Math.floor(i / L.rows), row = i % L.rows;
      i++;
      if (col >= L.x.length) break;
      const x = L.x[col], y = L.y0 + row * L.dy;
      this.lineup.push({ key, x, y });
      if (key === mine) continue;
      const model = ({ ...AIRCRAFT, ...TRAINERS }[key] || {}).model || key;
      const m = this.g.models.aircraft(model);
      m.position.set(x, y, this.g.models.types[model].gearHeight); m.rotation.z = Math.PI / 2;
      const meshes = [];
      m.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = true; meshes.push(o); } });
      this.lineup[this.lineup.length - 1].meshes = meshes; this.lineup[this.lineup.length - 1].sh = false;
      g.add(m);
    }
    this.g.view.scene.add(g);
    // the original parked jets of the airfield would stand in the same places
    if (this.g.view.parkedDecor) for (const d of this.g.view.parkedDecor) { d.userData.hide = true; d.visible = false; }
    return this.lineup;
  }
  showDecor(on) { if (this.g.view.parkedDecor) for (const d of this.g.view.parkedDecor) { d.userData.hide = !on; d.visible = on; } }
  // park an aircraft (the player's) at a spot, brakes on, engine off, or hot
  park(ac, rel, headingDeg, hot = false) {
    const f = this.field, x = f.x + rel[0], y = f.y + rel[1], z = this.g.terrain.height(x, y);
    ac.fm.placeOnGround(x, y, z, headingDeg);
    ac.fm.parkBrake = !hot; ac.controls.throttle = hot ? 0.2 : 0; ac.fm.engine = hot ? 0.3 : 0;
    ac.controls.brakes = false;
  }
  // --- interaction points: { id, x, y (field relative), r, label, action, beacon, color, enabled() }
  setPoints(points) { this.points = points; this.clearBeacons(); for (const p of points) if (p.beacon) this.addBeacon(p); }
  addBeacon(p) {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, 70, 14, 1, true).rotateX(Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: p.color || 0xffc840, transparent: true, opacity: 0.3, depthWrite: false, side: THREE.DoubleSide, fog: false }));
    const f = this.field;
    m.position.set(f.x + p.x, f.y + p.y, f.elevation + 35); m.userData.p = p;
    this.g.view.scene.add(m); this.beacons.push(m);
  }
  clearBeacons() { for (const b of this.beacons) this.g.view.scene.remove(b); this.beacons = []; }
  interact() {
    const p = this.near;
    if (p && p.action) p.action();
  }
  // every frame, walking or not: beacons pulse, the nearest point gives the prompt
  update(dt) {
    this.time += dt;
    for (const b of this.beacons) { b.material.opacity = 0.26 + 0.1 * Math.sin(this.time * 3); b.visible = !b.userData.p.enabled || b.userData.p.enabled(); }
    const w = this.walker;
    this.near = null;
    if (w.active && !this.g.state.paused) {
      let best = 1e9;
      for (const p of this.points) {
        if (p.enabled && !p.enabled()) continue;
        const d = Math.hypot(w.pos.x - (this.field.x + p.x), w.pos.y - (this.field.y + p.y));
        if (d < p.r && d < best) { best = d; this.near = p; }
      }
    }
    // the line-up's shadows (every jet is 70-120 thousand triangles, twice with a shadow): only the ones near you
    if (this.lineup && w.active) for (const e of this.lineup) {
      if (!e.meshes) continue;
      const want = Math.hypot(w.pos.x - (this.field.x + e.x), w.pos.y - (this.field.y + e.y)) < 45;
      if (want !== e.sh) { e.sh = want; for (const o of e.meshes) o.castShadow = want; }
    }
    this.drawHud();
  }
  drawHud() {
    const el = this.hud;
    if (!el) return;
    const w = this.walker, show = w.active && !this.g.state.paused && !this.g.inMenu;
    el.hidden = !show;
    if (!show) return;
    const near = this.near;
    const pr = el.querySelector('.wk-prompt');
    pr.hidden = !near;
    const prHtml = near ? `<kbd>E</kbd> ${typeof near.label === 'function' ? near.label() : near.label}` : '';
    if (prHtml !== this._pr) { pr.innerHTML = prHtml; this._pr = prHtml; }
    // labels over the objective beacons (or an arrow at the edge when they are behind you)
    const cam = this.g.view.camera, box = el.querySelector('.wk-marks');
    let html = '';
    for (const p of this.points) {
      if (!p.beacon || (p.enabled && !p.enabled())) continue;
      const v = new THREE.Vector3(this.field.x + p.x, this.field.y + p.y, this.field.elevation + 14).project(cam);
      const d = Math.round(Math.hypot(w.pos.x - (this.field.x + p.x), w.pos.y - (this.field.y + p.y)));
      const behind = v.z > 1;
      let sx = (v.x * 0.5 + 0.5) * 100, sy = (-v.y * 0.5 + 0.5) * 100;
      if (behind) { sx = v.x < 0 ? 94 : 6; sy = 50; }
      sx = clamp(sx, 6, 94); sy = clamp(sy, 8, 88);
      html += `<div class="wk-mark" style="left:${sx}%;top:${sy}%"><b>${p.name || p.label}</b><span>${d} m${behind ? (v.x < 0 ? ' ▶' : ' ◀') : ''}</span></div>`;
    }
    if (html !== this._html) { box.innerHTML = html; this._html = html; }
    const infoHtml = w.info ? w.info() : '';
    if (infoHtml !== this._info) { el.querySelector('.wk-info').innerHTML = infoHtml; this._info = infoHtml; }
  }
  // is a point of the ground blocked? (the walker keeps out of these)
  push(x, y, r = 0.45) {
    const f = this.field;
    let px = x - f.x, py = y - f.y;
    for (const o of this.obstacles) {
      if (o.c) {
        const dx = px - o.c[0], dy = py - o.c[1], d = Math.hypot(dx, dy), min = o.r + r;
        if (d < min) { const k = min / Math.max(d, 1e-3); px = o.c[0] + dx * k; py = o.c[1] + dy * k; }
      } else if (px > o.x0 - r && px < o.x1 + r && py > o.y0 - r && py < o.y1 + r) {
        const dl = px - (o.x0 - r), dr = (o.x1 + r) - px, db = py - (o.y0 - r), dtp = (o.y1 + r) - py, m = Math.min(dl, dr, db, dtp);
        if (m === dl) px = o.x0 - r; else if (m === dr) px = o.x1 + r; else if (m === db) py = o.y0 - r; else py = o.y1 + r;
      }
    }
    // the parked jets: a line along the fuselage
    for (const a of this.jetsOnGround || []) {
      const [jx, jy, hd] = a, c = Math.cos(hd * DEG), s = Math.sin(hd * DEG);
      // fuselage axis for a heading (0 = north, clockwise): (sin h, cos h)
      const ax = Math.sin(hd * DEG), ay = Math.cos(hd * DEG);
      for (const t of [-7, -3.5, 0, 3.5, 7]) {
        const cx = jx + ax * t, cy = jy + ay * t, dx = px - cx, dy = py - cy, d = Math.hypot(dx, dy), min = 2.4 + r;
        if (d < min) { const k = min / Math.max(d, 1e-3); px = cx + dx * k; py = cy + dy * k; }
      }
      for (const t of [-5, 5]) {          // the wings
        const cx = jx - ay * t, cy = jy + ax * t, dx = px - cx, dy = py - cy, d = Math.hypot(dx, dy), min = 1.8 + r;
        if (d < min) { const k = min / Math.max(d, 1e-3); px = cx + dx * k; py = cy + dy * k; }
      }
      void c; void s;
    }
    return [f.x + px, f.y + py];
  }
}

// ------------------------------------------------------------------------------------- the walker
export class Walker {
  constructor(game, base) {
    this.g = game; this.base = base; this.active = false; this.pos = V(); this.yaw = 0; this.pitch = 0; this.bob = 0; this.moving = 0;
    this.kit = false; this.info = null; this.orbit = 0;
  }
  // stand at a field-relative spot, looking along a compass heading (degrees, 0 = north)
  enter(rel, headingDeg = 0) {
    const f = this.base.field;
    this.pos.set(f.x + rel[0], f.y + rel[1], this.ground(f.x + rel[0], f.y + rel[1]));
    this.yaw = -headingDeg * DEG; this.pitch = 0; this.active = true; this.g.cam.walker = this;
    this.g.cam.cockpit = false; this.g.cam.panelLook = false;
  }
  leave() { this.active = false; if (this.g.cam.walker === this) this.g.cam.walker = null; }
  ground(x, y) { return this.g.terrain.height(x, y); }
  get eye() { return V(this.pos.x, this.pos.y, this.pos.z + EYE + Math.sin(this.bob) * 0.035 * this.moving); }
  // paused menu in the lobby: a slow walk-around view of the line-up (no input)
  idle(dt) {
    this.orbit += dt * 0.07;
    const f = this.base.field, cx = f.x + 300, cy = f.y - 90, r = 95;
    this.pos.set(cx + Math.cos(this.orbit) * r, cy + Math.sin(this.orbit) * r * 0.8, this.ground(f.x + 300, f.y - 90) + 4.5 - EYE);
    this.yaw = Math.atan2(-(cx - this.pos.x), cy - this.pos.y); this.pitch = -0.12;
  }
  update(dt) {
    const g = this.g, inp = g.input, cam = g.cam;
    const [dx, dy] = inp.takeDelta();
    let yawD = 0, pitD = 0;
    // look: the mouse (pointer lock), or dragging with the left button, or the arrow keys
    if (g.locked || inp.mouse[0]) { yawD = -dx * cam.sensitivity; pitD = -dy * cam.sensitivity * (cam.invertY ? -1 : 1); }
    yawD += ((inp.key('ArrowLeft') ? 1 : 0) - (inp.key('ArrowRight') ? 1 : 0)) * 90 * dt;
    pitD += ((inp.key('ArrowUp') ? 1 : 0) - (inp.key('ArrowDown') ? 1 : 0)) * 60 * dt;
    const pad = g.pad && g.pad.connected ? g.pad : null;
    if (pad) { yawD += -pad.rx * 110 * dt; pitD += -pad.ry * 80 * dt; }
    this.yaw += yawD * DEG; this.pitch = clamp(this.pitch + pitD * DEG, -1.35, 1.35);
    let fw = (inp.key('w') ? 1 : 0) - (inp.key('s') ? 1 : 0), sd = (inp.key('d') ? 1 : 0) - (inp.key('a') ? 1 : 0);
    if (pad) { fw += -pad.ly; sd += pad.lx; }
    fw = clamp(fw, -1, 1); sd = clamp(sd, -1, 1);
    const run = inp.key('shift') || (pad && pad.held(10));
    const sp = (run ? RUN : WALK) * (fw < 0 ? 0.6 : 1);
    const len = Math.hypot(fw, sd) || 1;
    // forward for a yaw about +Z, starting from north (+y): (-sin, cos); right: (cos, sin)
    const fx = -Math.sin(this.yaw), fy = Math.cos(this.yaw), rx = Math.cos(this.yaw), ry = Math.sin(this.yaw);
    const mx = (fx * fw + rx * sd) / len * sp * dt, my = (fy * fw + ry * sd) / len * sp * dt;
    this.moving = fw || sd ? 1 : 0;
    this.bob += dt * (run ? 11 : 7) * this.moving;
    if (this.moving) {
      let [nx, ny] = this.base.push(this.pos.x + mx, this.pos.y + my);
      const lim = this.g.terrain.half - 50;
      nx = clamp(nx, -lim, lim); ny = clamp(ny, -lim, lim);
      this.pos.x = nx; this.pos.y = ny;
    }
    this.pos.z = this.ground(this.pos.x, this.pos.y);
  }
  // metres to a field-relative spot
  distTo(rel) { const f = this.base.field; return Math.hypot(this.pos.x - f.x - rel[0], this.pos.y - f.y - rel[1]); }
}

// -------------------------------------------------------------------------------- the lobby
// The entry view: the base with all the jets on the line-up.  The menu sits at the side; walk along the line
// (the lobby-walk button), [E] on a jet makes it yours, [E] on your own jet takes you out to the runway.
export class Lobby {
  constructor(game) {
    this.g = game;
    const b = game.base, ALL = { ...AIRCRAFT, ...TRAINERS };
    b.build();
    this.types = PLANE_GROUPS.flatMap(([, keys]) => keys);
    this.setup(game.opts.aircraft in ALL ? game.opts.aircraft : 'f16');
    b.walker.enter(SPOTS.gate, 270);
    b.walker.info = () => `Gép: <b>${ALL[this.mine].name}</b> · WASD = séta · Shift = futás · E = választás / indulás · Esc = menü`;
    game.state.subBanner = ''; game.state.banner = '';
  }
  // the real aircraft takes its place in the line, the others are models
  setup(mine) {
    const g = this.g, b = g.base, ALL = { ...AIRCRAFT, ...TRAINERS };
    this.mine = mine;
    if (g.opts.aircraft !== mine || !g.player) { g.opts.aircraft = mine; g.spawnPlayer(); }
    const line = b.buildLineup(this.types, mine);
    const slot = line.find((l) => l.key === mine);
    b.park(g.player, slot ? [slot.x, slot.y] : SPOTS.jet, SPOTS.jetHeading);
    g.state.subBanner = ''; g.state.banner = '';
    g.cam.eye = g.models.types[g.player.spec.model].eye.clone();
    b.jetsOnGround = line.map((l) => [b.field.x + l.x, b.field.y + l.y, SPOTS.jetHeading]);
    if (!slot) b.jetsOnGround.push([b.field.x + SPOTS.jet[0], b.field.y + SPOTS.jet[1], SPOTS.jetHeading]);
    b.setPoints(line.map((l) => l.key === mine
      ? { id: l.key, x: l.x, y: l.y, r: 17, name: 'A TE GÉPED', beacon: true, color: 0x6bff85, label: () => `Felszállás: <b>${ALL[l.key].name}</b> (kifutó)`, action: () => g.onLobbyStart && g.onLobbyStart() }
      : { id: l.key, x: l.x, y: l.y, r: 17, label: () => `Ez legyen a gépem: <b>${ALL[l.key].name}</b>`, action: () => this.choose(l.key) }));
  }
  choose(key) {
    this.setup(key);
    if (this.g.onLobbySelect) this.g.onLobbySelect(key);
    const ALL = { ...AIRCRAFT, ...TRAINERS };
    this.g.hud.message(`KIVÁLASZTVA: ${ALL[key].name}`, 'good', 2.5, 'pick');
  }
  update() {}
  onEvent() {}
  enter() {}
  respawn() {}
}
