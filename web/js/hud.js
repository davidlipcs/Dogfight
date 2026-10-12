// HUD drawn on a 2D canvas over the WebGL view (port of dogfight/ui/hud.py + scopes.py).
import { THREE, V, add, sub, mul, dot, len, norm, clamp, DEG, toLocal, xform, angleBetween, headingDeg } from './util.js';
import { IR, ARH } from './specs.js';
import { STT, ACM, OFF, SEARCH, gunLead, launchZone, timeToImpact } from './weapons.js';

const GREEN = 'rgba(107,255,133,0.95)', DIM = 'rgba(107,255,133,0.5)', AMBER = '#ffc840', RED = '#ff4d40',
  WHITE = 'rgba(245,245,245,0.95)', ENEMY = 'rgba(255,84,72,0.95)', CYAN = 'rgba(115,217,255,0.95)';
const MONO = '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace';
const LEVEL_COLOR = { good: GREEN, warn: AMBER, bad: RED, info: WHITE };

export class HUD {
  constructor(canvas) {
    this.canvas = canvas; this.g = canvas.getContext('2d');
    this.messages = []; this.killfeed = []; this.markers = true; this.hitmarker = 0; this.time = 0; this.dlz = null; this.dlzTimer = 0;
  }
  message(text, level = 'info', duration = 2.5, key = null) {
    key = key || text;
    const m = this.messages.find((x) => x.key === key);
    if (m) { m.text = text; m.color = LEVEL_COLOR[level] || WHITE; m.t = duration; return; }
    this.messages.push({ text, color: LEVEL_COLOR[level] || WHITE, t: duration, key });
    this.messages = this.messages.slice(-4);
  }
  handleEvent(kind, d, player) {
    if (kind === 'message' && d.to === player) this.message(d.text, d.level || 'info');
    else if (kind === 'kill') {
      const text = d.killer && d.killer !== d.victim ? `${d.killer.name} → ${d.victim.name}  [${d.weapon}]` : `${d.victim.name} lezuhant`;
      this.killfeed.push({ text, color: d.killer === player ? GREEN : d.victim === player ? RED : WHITE, t: 7 });
      this.killfeed = this.killfeed.slice(-5);
      if (d.killer === player && d.victim !== player) this.message('CÉLPONT MEGSEMMISÍTVE', 'good', 3);
    } else if (kind === 'hit' && d.shooter === player && d.target !== player) this.hitmarker = 0.25;
    else if (kind === 'pitbull' && d.missile.shooter === player) this.message('PITBULL - AIM-120 aktív', 'good');
  }

  // screen projection: returns [x, y] in px or null if behind the camera
  project(cam, p) {
    const v = new THREE.Vector3(p.x, p.y, p.z).applyMatrix4(cam.matrixWorldInverse);
    if (v.z > -1) return null;
    v.applyMatrix4(cam.projectionMatrix);
    return [(v.x + 1) / 2 * this.w, (1 - v.y) / 2 * this.h];
  }

  // ------------------------------------------------------------ primitives
  line(x1, y1, x2, y2, c) { const g = this.g; g.strokeStyle = c; g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke(); }
  circle(x, y, r, c, a0 = 0, a1 = Math.PI * 2) { const g = this.g; g.strokeStyle = c; g.beginPath(); g.arc(x, y, r, a0, a1); g.stroke(); }
  rect(x, y, hw, hh, c) { this.g.strokeStyle = c; this.g.strokeRect(x - hw, y - hh, 2 * hw, 2 * hh); }
  poly(pts, c, closed = true) {
    const g = this.g; g.strokeStyle = c; g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
    for (const p of pts.slice(1)) g.lineTo(p[0], p[1]);
    if (closed) g.closePath();
    g.stroke();
  }
  brackets(x, y, r, c) {
    for (const sx of [-1, 1]) for (const sy of [-1, 1]) this.poly([[x + sx * r, y + sy * r * 0.6], [x + sx * r, y + sy * r], [x + sx * r * 0.6, y + sy * r]], c, false);
  }
  text(t, x, y, c, size = 13, align = 'left', font = MONO) {
    const g = this.g; g.font = `${size}px ${font}`; g.textAlign = align; g.textBaseline = 'middle';
    g.fillStyle = 'rgba(0,0,0,0.55)'; g.fillText(t, x + 1, y + 1);
    g.fillStyle = c; g.fillText(t, x, y);
  }

  update(dt, player, world, cam, camCtl, game) {
    const cv = this.canvas, dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth, h = cv.clientHeight;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    const g = this.g;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    this.w = w; this.h = h; this.u = Math.min(w, h) / 900;       // scale unit
    g.lineWidth = Math.max(1.2, 1.6 * this.u);
    this.time += dt; this.hitmarker = Math.max(0, this.hitmarker - dt);
    for (const l of [this.messages, this.killfeed]) for (const m of l) m.t -= dt;
    this.messages = this.messages.filter((m) => m.t > 0); this.killfeed = this.killfeed.filter((m) => m.t > 0);
    if (player && player.alive) {
      this.flightSymbols(player, cam, camCtl);
      this.targets(player, world, cam);
      this.weaponSymbols(player, world, cam, dt);
      this.panels(player, world);
      this.radarScope(player);
      this.rwrScope(player);
      this.warnings(player, world);
      this.missileList(player, world);
    }
    this.overlay(game);
  }

  flightSymbols(ac, cam, camCtl) {
    const u = this.u;
    const aim = this.project(cam, add(camCtl.position, mul(camCtl.aimDirection(), 3000)));
    if (aim && !camCtl.freeLook) this.circle(aim[0], aim[1], 14 * u, WHITE);
    const nose = this.project(cam, add(ac.pos, mul(ac.forward, 800)));
    if (nose) {
      const [x, y] = nose, r = 22 * u, gap = 6 * u;
      this.line(x - r, y, x - gap, y, GREEN); this.line(x + gap, y, x + r, y, GREEN);
      this.line(x, y - r, x, y - gap, GREEN); this.line(x, y + gap, x, y + r, GREEN);
      if (this.hitmarker > 0) {
        const k = 20 * u;
        for (const [sx, sy] of [[-1, -1], [1, 1], [-1, 1], [1, -1]]) this.line(x + sx * k, y + sy * k, x + sx * k * 0.4, y + sy * k * 0.4, WHITE);
      }
    }
    if (ac.speed > 20) {
      const f = this.project(cam, add(ac.pos, mul(norm(ac.vel), 800)));
      if (f) {
        const [x, y] = f, r = 8 * u;
        this.circle(x, y, r, GREEN);
        this.line(x - 22 * u, y, x - r, y, GREEN); this.line(x + r, y, x + 22 * u, y, GREEN); this.line(x, y - r, x, y - 17 * u, GREEN);
      }
    }
    if (camCtl.cockpit) this.pitchLadder(ac, cam, camCtl);
  }
  pitchLadder(ac, cam, camCtl) {
    const hdg = Math.atan2(ac.forward.x, ac.forward.y), pitch = Math.asin(clamp(ac.forward.z, -1, 1)) / DEG;
    const dir = (h, e) => V(Math.sin(h) * Math.cos(e), Math.cos(h) * Math.cos(e), Math.sin(e));
    for (let e = -80; e <= 80; e += 10) {
      if (Math.abs(e - pitch) > 35) continue;
      const [inner, outer] = e === 0 ? [1.5, 25] : [2, 9];
      for (const s of [-1, 1]) {
        const a = this.project(cam, add(camCtl.position, mul(dir(hdg + s * inner * DEG, e * DEG), 5000)));
        const b = this.project(cam, add(camCtl.position, mul(dir(hdg + s * outer * DEG, e * DEG), 5000)));
        if (!a || !b) continue;
        this.line(a[0], a[1], b[0], b[1], e >= 0 ? GREEN : DIM);
        if (e !== 0 && s === 1) this.text(String(e), b[0] + 6, b[1], e >= 0 ? GREEN : DIM, 11 * this.u + 2);
      }
    }
  }
  targets(ac, world, cam) {
    if (!this.markers) return;
    const u = this.u;
    for (const t of world.aircraft) {
      if (t === ac || !t.alive || t.team === ac.team) continue;
      const d = len(sub(t.pos, ac.pos));
      if (d > 25000) continue;
      const p = this.project(cam, t.pos);
      if (!p) continue;
      if (t !== ac.radar.locked) this.poly([[p[0] - 8 * u, p[1] - 20 * u], [p[0] + 8 * u, p[1] - 20 * u], [p[0], p[1] - 10 * u]], ENEMY);
      this.text((d / 1000).toFixed(1), p[0], p[1] - 30 * u, ENEMY, 11 * u + 2, 'center');
    }
  }
  edgeArrow(cam, pos, c) {
    const v = new THREE.Vector3(pos.x, pos.y, pos.z).applyMatrix4(cam.matrixWorldInverse);
    const ang = Math.atan2(v.x, v.y), r = Math.min(this.w, this.h) * 0.38;
    const x = this.w / 2 + Math.sin(ang) * r, y = this.h / 2 - Math.cos(ang) * r;
    const tip = [x + Math.sin(ang) * 22 * this.u, y - Math.cos(ang) * 22 * this.u];
    const side = [Math.cos(ang) * 12 * this.u, Math.sin(ang) * 12 * this.u];
    this.poly([[x + side[0], y + side[1]], tip, [x - side[0], y - side[1]]], c);
  }
  weaponSymbols(ac, world, cam, dt) {
    const u = this.u, r = ac.radar;
    if (r.mode === STT && r.trackPos) {
      const t = r.locked, p = this.project(cam, r.trackPos), col = r.lostTime === 0 ? GREEN : AMBER;
      if (p) {
        this.rect(p[0], p[1], 20 * u, 20 * u, col);
        const rel = sub(r.trackPos, ac.pos), vc = -dot(sub(r.trackVel, ac.vel), norm(rel));
        this.text(`${(len(rel) / 1000).toFixed(1)} km`, p[0] + 28 * u, p[1] - 8 * u, col, 11 * u + 2);
        this.text(`Vc ${vc * 3.6 >= 0 ? '+' : ''}${Math.round(vc * 3.6)}`, p[0] + 28 * u, p[1] + 10 * u, col, 11 * u + 2);
        if (r.lostTime > 0) this.text('MEM', p[0] - 28 * u, p[1] - 26 * u, AMBER, 11 * u + 2);
      } else this.edgeArrow(cam, r.trackPos, GREEN);
      if (t && len(sub(t.pos, ac.pos)) < ac.spec.gun.maxLeadRange) {
        const [aim] = gunLead(ac.pos, ac.vel, t.pos, t.vel, ac.spec.gun);
        const d = len(sub(t.pos, ac.pos)), lp = this.project(cam, add(ac.pos, mul(aim, d)));
        if (lp) {
          this.circle(lp[0], lp[1], 20 * u, WHITE); this.circle(lp[0], lp[1], 2.5 * u, WHITE);
          const frac = clamp(d / ac.spec.gun.maxLeadRange, 0, 1);
          this.circle(lp[0], lp[1], 24 * u, WHITE, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * (1 - frac));
        }
      }
    } else if (r.pending) {
      const p = this.project(cam, r.pending.pos);
      if (p && Math.floor(this.time * 8) % 2 === 0) this.brackets(p[0], p[1], 24 * u, AMBER);
    } else if (r.mode === ACM) {
      const s = r.spec, pts = [];
      for (const [az, el] of [[-s.acmAz, s.acmElLow], [s.acmAz, s.acmElLow], [s.acmAz, s.acmElHigh], [-s.acmAz, s.acmElHigh]]) {
        const d = xform(ac.quat, V(Math.sin(az * DEG) * Math.cos(el * DEG), Math.cos(az * DEG) * Math.cos(el * DEG), Math.sin(el * DEG)));
        pts.push(this.project(cam, add(ac.pos, mul(d, 3000))));
      }
      if (pts.every(Boolean)) this.poly(pts, 'rgba(255,200,64,0.5)');
    }
    if (r.selected && r.mode !== STT && r.selected.alive) {
      const p = this.project(cam, r.selected.pos);
      if (p) this.brackets(p[0], p[1], 20 * u, DIM);
    }
    const sp = ac.selectedSpec;
    if (!sp) return;
    if (sp.guidance === IR && ac.irSeeker.axis) {
      const s = ac.irSeeker, p = this.project(cam, add(ac.pos, mul(s.axis, 2000)));
      if (p) {
        if (s.locked) { this.circle(p[0], p[1], 26 * u, GREEN); this.circle(p[0], p[1], 29 * u, GREEN); this.poly([[p[0], p[1] - 7 * u], [p[0] + 7 * u, p[1]], [p[0], p[1] + 7 * u], [p[0] - 7 * u, p[1]]], GREEN); }
        else if (s.candidate) this.circle(p[0], p[1], 26 * u, Math.floor(this.time * 10) % 2 ? WHITE : GREEN);
        else this.circle(p[0], p[1], 26 * u, DIM);
      }
    }
    this.dlzBar(ac, sp, dt);
  }
  dlzBar(ac, sp, dt) {
    const r = ac.radar;
    let tgt = r.mode === STT ? r.locked : null;
    if (sp.guidance === IR && ac.irSeeker.locked && !ac.irSeeker.target.isFlare) tgt = ac.irSeeker.target;
    if (!tgt) { this.dlz = null; return; }
    const rel = sub(tgt.pos, ac.pos), d = len(rel), closing = -dot(tgt.vel, norm(rel));
    this.dlzTimer -= dt;
    if (!this.dlz || this.dlzTimer <= 0) { this.dlz = launchZone(sp, ac.speed, ac.pos.z, closing); this.dlzTimer = 0.5; }
    const [rmax, rne] = this.dlz, rmin = sp.minRange, u = this.u;
    const x = this.w / 2 + 210 * u, y0 = this.h / 2 + 140 * u, y1 = this.h / 2 - 140 * u;
    const scale = Math.max(rmax * 1.25, d * 1.05, 2000), ry = (v) => y0 + (y1 - y0) * clamp(v / scale, 0, 1);
    this.line(x, ry(rmin), x, ry(rmax), GREEN);
    for (const v of [rmax, rmin]) this.line(x - 8 * u, ry(v), x + 8 * u, ry(v), GREEN);
    this.line(x - 13 * u, ry(rne), x + 13 * u, ry(rne), GREEN);
    const yy = ry(d);
    this.poly([[x - 24 * u, yy - 8 * u], [x - 10 * u, yy], [x - 24 * u, yy + 8 * u]], WHITE, false);
    this.text((rmax / 1000).toFixed(1), x + 14 * u, ry(rmax), DIM, 11 * u + 2);
    let tag = null;
    if (rmin < d && d < rne) tag = ['NO ESC', RED]; else if (rmin < d && d < rmax) tag = ['IN RNG', GREEN]; else if (d <= rmin) tag = ['MIN', AMBER];
    if (tag) this.text(tag[0], x - 20 * u, y0 + 22 * u, tag[1], 12 * u + 2);
  }
  panels(ac, world) {
    const fm = ac.fm, u = this.u, fs = 13 * u + 3, lh = fs * 1.35;
    const x = this.w / 2 - 330 * u, y = this.h / 2 - 90 * u;
    const thr = fm.engine > 1 ? 'AB' : `${Math.round(fm.engine * 100)}%`;
    const rows = [
      [`IAS ${String(Math.round(fm.ias * 3.6)).padStart(5)} km/h`, GREEN], [`TAS ${String(Math.round(ac.speed * 3.6)).padStart(5)}`, DIM],
      [`M   ${fm.mach.toFixed(2).padStart(5)}`, GREEN], [`G   ${fm.gLoad.toFixed(1).padStart(5)}`, fm.gLoad > 7.5 ? AMBER : GREEN],
      [`AoA ${(fm.alpha / DEG).toFixed(1).padStart(5)}`, fm.alpha / DEG > 20 ? AMBER : GREEN], [`THR  ${thr}`, fm.engine > 1 ? AMBER : GREEN],
      [fm.gearPos > 0.98 ? 'GEAR DOWN' : fm.gearPos > 0.02 ? 'GEAR TRANSIT' : 'GEAR UP', fm.gearPos > 0.98 ? GREEN : fm.gearPos > 0.02 ? AMBER : DIM],
    ];
    if (ac.onGround) rows.push([`GS  ${String(Math.round(ac.speed * 3.6)).padStart(5)} km/h`, GREEN]);
    if (ac.controls.brakes && ac.onGround) rows.push(['BRAKES', AMBER]);
    else if (ac.controls.airbrake) rows.push(['SPD BRK', AMBER]);
    rows.forEach(([t, c], i) => this.text(t, x, y + i * lh, c, fs));
    const terr = world.terrain.height(ac.pos.x, ac.pos.y), xr = this.w / 2 + 250 * u;
    const fuelCol = fm.fuel < 400 ? RED : fm.fuel < 900 ? AMBER : GREEN;
    const right = [
      [`ALT ${String(Math.round(ac.pos.z)).padStart(6)} m`, GREEN], [`AGL ${String(Math.round(ac.pos.z - terr)).padStart(6)}`, DIM],
      [`VS  ${(fm.vel.z >= 0 ? '+' : '') + Math.round(fm.vel.z)}`, GREEN], [`HDG    ${String(Math.round(headingDeg(ac.forward))).padStart(3, '0')}`, GREEN],
      [`FUEL ${String(Math.round(fm.fuel)).padStart(5)} kg`, fuelCol], [`HP   ${String(Math.max(0, Math.round(ac.hp))).padStart(5)}`, ac.hp > 50 ? GREEN : RED],
    ];
    right.forEach(([t, c], i) => this.text(t, xr, y + i * lh, c, fs));
    // weapons
    const yb = this.h - 78 * u, parts = ac.weaponKeys().map((k) => (k === ac.selected ? `[${k} ×${ac.missileCount(k)}]` : ` ${k} ×${ac.missileCount(k)} `));
    this.text(parts.join('   '), this.w / 2, yb, GREEN, fs, 'center');
    this.text(`GUN ${ac.gun.ammo}    FLR ${ac.flares}   CHF ${ac.chaff}`, this.w / 2, yb + lh, GREEN, fs, 'center');
    const sp = ac.selectedSpec;
    let status = '', col = GREEN;
    if (sp && sp.guidance === IR) {
      const s = ac.irSeeker;
      if (s.locked) status = 'AIM-9M: LOCK  (F: elenged)';
      else if (s.candidate) { status = 'AIM-9M: HŐFORRÁS A KERESŐBEN - F: lock'; col = WHITE; }
      else { status = 'AIM-9M: keresés (growl)'; col = DIM; }
    } else if (sp && sp.guidance === ARH) {
      if (ac.radar.mode === STT) status = 'AIM-120A: radar lock OK';
      else { status = 'AIM-120A: nincs lock (maddog) - T: radar lock'; col = AMBER; }
    }
    this.text(status, this.w / 2, yb + 2 * lh, col, fs, 'center');
    const r = ac.radar;
    if (r.mode === STT && r.trackPos) {
      const rel = sub(r.trackPos, ac.pos), vc = -dot(sub(r.trackVel, ac.vel), norm(rel));
      const asp = Math.round(angleBetween(r.trackVel, sub(ac.pos, r.trackPos)) / DEG);
      this.text(`STT ${(len(rel) / 1000).toFixed(1)} km  Vc ${Math.round(vc * 3.6)} km/h  ASP ${asp}${r.notched ? '  NOTCH!' : ''}`, this.w / 2, yb + 3 * lh, r.notched ? AMBER : GREEN, fs, 'center');
    } else if (r.mode === ACM) this.text('ACM: tedd az orrod elé a célt', this.w / 2, yb + 3 * lh, AMBER, fs, 'center');
  }
  radarScope(ac) {
    const r = ac.radar, sp = r.spec, u = this.u, size = 200 * u, hw = size / 2;
    const cx = this.w - hw - 24 * u, cy = this.h - hw - 24 * u, left = cx - hw, top = cy - hw, bottom = cy + hw;
    const g = this.g;
    g.fillStyle = 'rgba(4,16,8,0.45)'; g.fillRect(left, top, size, size);
    this.rect(cx, cy, hw, hw, DIM);
    const tgt = r.locked || r.selected || r.pending;
    let scale = 40000;
    if (r.mode === ACM) scale = 20000;
    else if (tgt) { const d = len(sub(tgt.pos, ac.pos)); scale = [10000, 20000, 40000, 80000].find((s) => d < s * 0.85) || 80000; }
    const azMax = sp.scanAz * DEG, toXY = (az, d) => [cx + clamp(az / azMax, -1, 1) * hw, bottom - Math.min(d / scale, 1) * size];
    for (const k of [1, 2, 3]) { const y = bottom - size * k / 4; this.line(left, y, left + 8 * u, y, DIM); this.line(left + size - 8 * u, y, left + size, y, DIM); }
    for (const az of [-30, 0, 30]) { const x = cx + az / sp.scanAz * hw; this.line(x, bottom, x, bottom - 8 * u, DIM); }
    this.text(`${r.mode}  ${scale / 1000} km`, left + 4 * u, top - 10 * u, GREEN, 11 * u + 2);
    this.text('RADAR', left + size, top - 10 * u, DIM, 11 * u + 2, 'right');
    if (r.mode === OFF) { this.text('KI', cx, cy, DIM, 18 * u, 'center'); return; }
    if (r.mode === SEARCH) { const x = cx + r.beamAz / azMax * hw; this.line(x, bottom, x, top, 'rgba(107,255,133,0.25)'); }
    else if (r.mode === ACM) {
      const w = sp.acmAz / sp.scanAz * hw, y = bottom - Math.min(sp.acmRange / scale, 1) * size;
      this.poly([[cx - w, bottom], [cx - w, y], [cx + w, y], [cx + w, bottom]], AMBER, false);
    }
    for (const [t, c] of r.contacts) {
      if (t === r.locked) continue;
      const [x, y] = toXY(c.az, c.range);
      g.fillStyle = GREEN; g.fillRect(x - 4 * u, y - 4 * u, 8 * u, 8 * u);
      if (t === r.selected) { this.brackets(x, y, 12 * u, GREEN); this.text((t.pos.z / 1000).toFixed(1), x + 15 * u, y, DIM, 10 * u + 2); }
    }
    if (r.pending && Math.floor(this.time * 8) % 2 === 0) { const [az, , d] = r.anglesTo(r.pending.pos); const [x, y] = toXY(az, d); this.brackets(x, y, 14 * u, AMBER); }
    if (r.locked && r.trackPos) {
      const [az, , d] = r.anglesTo(r.trackPos), [x, y] = toXY(az, d), col = r.lostTime > 0 ? AMBER : GREEN;
      this.poly([[x, y - 10 * u], [x + 10 * u, y], [x, y + 10 * u], [x - 10 * u, y]], col);
      const hl = toLocal(ac.quat, r.trackVel), hn = Math.hypot(hl.x, hl.y);
      if (hn > 1) this.line(x, y, x + hl.x / hn * 24 * u, y - hl.y / hn * 24 * u, col);
      this.text((r.trackPos.z / 1000).toFixed(1), x + 15 * u, y, col, 10 * u + 2);
    }
  }
  rwrScope(ac) {
    const u = this.u, R = 90 * u, cx = R + 26 * u, cy = this.h - R - 26 * u, g = this.g;
    g.fillStyle = 'rgba(4,16,8,0.45)'; g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.fill();
    this.circle(cx, cy, R, DIM); this.circle(cx, cy, R * 0.5, 'rgba(107,255,133,0.25)');
    for (let k = 0; k < 12; k++) { const a = k * Math.PI / 6; this.line(cx + Math.sin(a) * R, cy - Math.cos(a) * R, cx + Math.sin(a) * R * 0.92, cy - Math.cos(a) * R * 0.92, DIM); }
    this.text('RWR', cx - R, cy - R + 4 * u, DIM, 11 * u + 2);
    const blink = Math.floor(this.time * 6) % 2 === 0;
    for (const t of ac.rwr.threats) {
      let rad = R * 0.82, col = GREEN;
      if (t.level === 'launch') { if (!blink) continue; rad = R * 0.32; col = RED; } else if (t.level === 'lock') { rad = R * 0.58; col = AMBER; }
      const x = cx + Math.sin(t.bearing) * rad, y = cy - Math.cos(t.bearing) * rad;
      this.text(t.symbol, x, y, col, 14 * u + 2, 'center');
      if (t.level !== 'search') this.circle(x, y, 13 * u, col);
    }
  }
  warnings(ac, world) {
    const u = this.u, terr = world.terrain, blink = Math.floor(this.time * 4) % 2 === 0;
    let y = this.h / 2 - 220 * u;
    const big = (t, c, s = 30) => { this.text(t, this.w / 2, y, c, s * u + 4, 'center', 'Oswald, Impact, sans-serif'); y += (s + 12) * u; };
    const ahead = add(ac.pos, mul(ac.vel, 4)), agl = ac.pos.z - terr.height(ac.pos.x, ac.pos.y);
    if (!ac.onGround && ac.fm.gearPos < 0.5 && (ahead.z < terr.height(ahead.x, ahead.y) + 60 || (agl < 150 && ac.vel.z < -15)) && blink) big('PULL UP', RED);
    if (ac.rwr.maxLevel >= 3) { if (blink) big('MISSILE!', RED); } else if (ac.rwr.maxLevel === 2) big('RADAR LOCK', AMBER, 22);
    if (ac.fm.ias < 70 && !ac.onGround) big('SPEED LOW', AMBER, 22);
    if (!ac.onGround && ac.fm.gearPos < 0.98 && agl < 300 && ac.fm.ias < 95 && ac.vel.z < -2 && blink) big('FUTÓMŰ!', RED, 24);
    if (ac.fm.gearPos > 0.02 && ac.fm.ias > 155 && blink) big('GEAR SPEED', AMBER, 22);
    if (ac.fm.fuel > 0 && ac.fm.fuel < 400) big('BINGO FUEL', AMBER, 22);
    let my = this.h / 2 - 130 * u;
    for (const m of this.messages) { this.text(m.text, this.w / 2, my, m.color, 16 * u + 3, 'center'); my += 22 * u + 4; }
  }
  missileList(ac, world) {
    let y = 110 * this.u;
    for (const m of world.missiles) {
      if (m.shooter !== ac) continue;
      const ttg = timeToImpact(m), col = ['TRACK', 'ACTIVE', 'DATALINK'].includes(m.status) ? CYAN : AMBER;
      this.text(`${m.spec.name} ${m.status.padEnd(8)} ${ttg !== null && ttg < 99 ? ttg.toFixed(1) + 's' : '--'}`, this.w - 20 * this.u, y, col, 11 * this.u + 3, 'right');
      y += 18 * this.u + 3;
    }
  }
  overlay(game) {
    const u = this.u, fs = 12 * u + 3;
    this.text(`HULLÁM ${game.wave}   LELŐVE ${game.kills}   HALÁL ${game.deaths}`, 20 * u, 22 * u, WHITE, fs);
    this.text('H = súgó   Esc = egér elengedése', 20 * u, 42 * u, DIM, 11 * u + 2);
    let y = 22 * u;
    for (const k of this.killfeed) { this.text(k.text, this.w - 20 * u, y, k.color, fs, 'right'); y += 20 * u + 3; }
    if (game.banner) this.text(game.banner, this.w / 2, this.h / 2 - 40 * u, WHITE, 44 * u + 6, 'center', 'Oswald, Impact, sans-serif');
    if (game.subBanner) this.text(game.subBanner, this.w / 2, game.banner ? this.h / 2 + 10 * u : 80 * u, WHITE, 15 * u + 3, 'center');
  }
}
