// HUD drawn on a 2D canvas over the WebGL view (port of dogfight/ui/hud.py + scopes.py).
import { THREE, V, add, sub, mul, dot, len, norm, clamp, DEG, toLocal, xform, angleBetween, headingDeg } from './util.js';
import { IR, ARH } from './specs.js';
import { STT, ACM, OFF, SEARCH, gunLead, launchZone, timeToImpact, flyoutTime, rcs, radarRange } from './weapons.js';

const GREEN = 'rgba(107,255,133,0.95)', DIM = 'rgba(107,255,133,0.5)', AMBER = '#ffc840', RED = '#ff4d40',
  WHITE = 'rgba(245,245,245,0.95)', ENEMY = 'rgba(255,84,72,0.95)', CYAN = 'rgba(115,217,255,0.95)';
const MONO = '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace';
const LEVEL_COLOR = { good: GREEN, warn: AMBER, bad: RED, info: WHITE };

export class HUD {
  constructor(canvas) {
    this.canvas = canvas; this.g = canvas.getContext('2d');
    this.messages = []; this.killfeed = []; this.markers = true; this.hitmarker = 0; this.time = 0; this.dlz = null; this.dlzTimer = 0;
    this.popups = []; this.damage = 0; this.medal = null;
  }
  // score popup under the centre ("+150 ÁGYÚ"), rises and fades
  popup(text, color = GREEN) { this.popups.push({ text, color, t: 1.8 }); this.popups = this.popups.slice(-4); }
  showMedal(a) { this.medal = { a, t: 4.5 }; }
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
    else if (kind === 'hit' && d.target === player) this.damage = Math.min(0.8, this.damage + 0.45);
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
    this.player = player;
    const cv = this.canvas, dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth, h = cv.clientHeight;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    const g = this.g;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    this.w = w; this.h = h; this.u = Math.min(w, h) / 900;       // scale unit
    g.lineWidth = Math.max(1.2, 1.6 * this.u);
    this.time += dt; this.dt = dt; this.hitmarker = Math.max(0, this.hitmarker - dt);
    for (const l of [this.messages, this.killfeed, this.popups]) for (const m of l) m.t -= dt;
    this.messages = this.messages.filter((m) => m.t > 0); this.killfeed = this.killfeed.filter((m) => m.t > 0);
    this.popups = this.popups.filter((m) => m.t > 0);
    this.gEffects(player, dt);
    this.damageFlash(dt);
    if (player && player.alive && camCtl.cockpit && camCtl.panelLook) {
      // looking down at the displays: only the warnings and messages stay over them
      this.cockpit = true;
      this.warnings(player, world);
    } else if (player && player.alive) {
      this.incomingMissiles(player, cam);
      if (!camCtl.follow) this.flightSymbols(player, cam, camCtl);
      this.targets(player, world, cam);
      this.navMarks(player, cam);
      if (game.raceTarget) this.raceMark(player, cam, game.raceTarget);
      this.weaponSymbols(player, world, cam, dt);
      if (!camCtl.follow) this.panels(player, world);
      this.radarScope(player);
      this.rwrScope(player);
      this.warnings(player, world);
      this.missileList(player, world);
    }
    this.overlay(game);
    this.extras(game, camCtl);
  }
  // the carrier's optical landing system: the amber ball against the green datum lights (above = high,
  // below = low), the line-up error and the distance to the wires
  meatballBox(m) {
    const u = this.u, g = this.g, cx = this.w - 70 * u, cy = this.h / 2 - 40 * u, hh = 70 * u;
    g.fillStyle = 'rgba(4,10,14,0.55)'; g.fillRect(cx - 34 * u, cy - hh - 26 * u, 68 * u, 2 * hh + 70 * u);
    this.line(cx - 28 * u, cy, cx - 10 * u, cy, GREEN); this.line(cx + 10 * u, cy, cx + 28 * u, cy, GREEN);
    this.rect(cx, cy, 6 * u, hh, DIM);
    const k = clamp(m.high / 12, -1, 1), by = cy - k * hh, col = Math.abs(k) < 0.25 ? AMBER : Math.abs(k) < 0.7 ? AMBER : RED;
    g.fillStyle = k < -0.7 ? RED : col; g.beginPath(); g.arc(cx, by, 7 * u, 0, Math.PI * 2); g.fill();
    this.text('MEATBALL', cx, cy - hh - 14 * u, CYAN, 10 * u + 2, 'center');
    const lu = Math.abs(m.off) < 8 ? ['VONALBAN', GREEN] : m.off > 0 ? ['◀ BALRA', AMBER] : ['JOBBRA ▶', AMBER];
    this.text(lu[0], cx, cy + hh + 14 * u, lu[1], 10 * u + 2, 'center');
    this.text(k > 0.25 ? 'MAGAS' : k < -0.25 ? 'ALACSONY' : 'JÓ', cx, cy + hh + 28 * u, k < -0.7 ? RED : WHITE, 10 * u + 2, 'center');
    this.text(`${Math.round(m.dist)} m`, cx, cy + hh + 42 * u, DIM, 10 * u + 2, 'center');
  }
  // ring race: the next ring - a ring marker with the distance, or an arrow at the edge
  raceMark(ac, cam, c) {
    const u = this.u, p = this.project(cam, c), d = len(sub(c, ac.pos));
    if (!p) { this.edgeArrow(cam, c, AMBER); return; }
    this.circle(p[0], p[1], 16 * u, AMBER); this.circle(p[0], p[1], 3 * u, AMBER);
    this.text(`GYŰRŰ ${(d / 1000).toFixed(1)} km`, p[0], p[1] - 26 * u, AMBER, 12 * u + 2, 'center');
  }
  // red flash at the screen edges when the player is hit
  damageFlash(dt) {
    if (this.damage <= 0.01) { this.damage = 0; return; }
    const g = this.g, w = this.w, h = this.h, R = Math.hypot(w, h) / 2;
    const grd = g.createRadialGradient(w / 2, h / 2, R * 0.45, w / 2, h / 2, R);
    grd.addColorStop(0, 'rgba(255,30,20,0)'); grd.addColorStop(1, `rgba(255,30,20,${this.damage * 0.75})`);
    g.fillStyle = grd; g.fillRect(0, 0, w, h);
    this.damage = Math.max(0, this.damage - dt * 1.4);
  }
  // added layer: score, game mode line, popups, medal banner, camera label
  extras(game, camCtl) {
    const u = this.u, fs = 12 * u + 3;
    if (game.score !== undefined && !this.tutorial) {
      const streak = game.streak > 1 ? `   SOROZAT ${game.streak}` : '';
      this.text(`PONT ${game.score}${streak}   KREDIT ${game.credits}`, 20 * u, 82 * u, AMBER, fs);
    }
    if (game.bt) {                                         // bullet time (hangar mod): charge bar
      const x = 20 * u, y = 122 * u, w = 120 * u, b = game.bt, on = b.active > 0;
      this.g.strokeStyle = DIM; this.g.strokeRect(x, y - 5 * u, w, 10 * u);
      this.g.fillStyle = on ? AMBER : b.charge >= 1 ? GREEN : DIM;
      this.g.fillRect(x, y - 5 * u, w * (on ? b.active / 4 : b.charge), 10 * u);
      this.text(on ? 'BULLET TIME' : b.charge >= 1 ? 'O = bullet time' : 'bullet time töltődik', x + w + 8 * u, y, on ? AMBER : DIM, 10 * u + 2);
    }
    if (game.modeLine) this.text(game.modeLine, 20 * u, 102 * u, WHITE, 11 * u + 2);
    let y = this.h / 2 + 70 * u;
    for (const p of this.popups) {
      const k = Math.min(1, p.t / 0.5), rise = (1.8 - p.t) * 26 * u;
      this.g.globalAlpha = k;
      this.text(p.text, this.w / 2, y - rise, p.color, 22 * u + 4, 'center', 'Oswald, Impact, sans-serif');
      this.g.globalAlpha = 1;
      y += 30 * u;
    }
    if (this.medal) {
      const m = this.medal; m.t -= this.dt || 1 / 60;
      if (m.t <= 0) this.medal = null;
      else {
        const k = Math.min(1, m.t / 0.6), g = this.g, bw = 360 * u, bh = 64 * u, x = this.w / 2 - bw / 2, top = 120 * u;
        g.globalAlpha = k;
        g.fillStyle = 'rgba(20,27,34,0.88)'; g.fillRect(x, top, bw, bh);
        g.strokeStyle = AMBER; g.lineWidth = 2; g.strokeRect(x, top, bw, bh);
        this.text('★ ÚJ KITÜNTETÉS', this.w / 2, top + 18 * u, AMBER, 11 * u + 2, 'center');
        this.text(m.a.name, this.w / 2, top + 36 * u, WHITE, 18 * u + 3, 'center', 'Oswald, Impact, sans-serif');
        this.text(m.a.desc, this.w / 2, top + 54 * u, DIM, 10 * u + 2, 'center');
        g.globalAlpha = 1;
      }
    }
    if (game.meatball) this.meatballBox(game.meatball);
    if (camCtl && camCtl.followLabel) this.text(camCtl.followLabel, this.w / 2, 70 * u, CYAN, 15 * u + 3, 'center', 'Oswald, Impact, sans-serif');
  }

  flightSymbols(ac, cam, camCtl) {
    const u = this.u;
    const aim = this.project(cam, add(camCtl.position, mul(camCtl.aimDirection(), 3000)));
    if (camCtl.stick && !this.touchLayout) this.stickGauge(camCtl.stick);
    else if (aim && !(camCtl.freeLook && !camCtl.cockpit)) this.circle(aim[0], aim[1], 14 * u, WHITE);
    else if (!aim && camCtl.cockpit) this.edgeArrow(cam, add(camCtl.position, mul(camCtl.aimDirection(), 3000)), WHITE);
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
    this.cockpit = camCtl.cockpit;
    if (camCtl.cockpit) this.pitchLadder(ac, cam, camCtl);
  }
  // where the mouse joystick is: box = full deflection, dot = the stick (down = pulled back)
  stickGauge(s) {
    const u = this.u, r = 26 * u, cx = 116 * u, cy = this.h - 270 * u;                 // above the RWR scope
    this.rect(cx, cy, r, r, DIM);
    this.line(cx - r, cy, cx + r, cy, DIM); this.line(cx, cy - r, cx, cy + r, DIM);
    const g = this.g, x = cx + s.x * r, y = cy + s.y * r, dz = 0.07;
    this.rect(cx, cy, r * dz, r * dz, DIM);                                           // neutral band
    const neutral = Math.abs(s.x) < dz && Math.abs(s.y) < dz;
    g.fillStyle = neutral ? GREEN : WHITE; g.beginPath(); g.arc(x, y, 4 * u + 1, 0, Math.PI * 2); g.fill();
    this.text('BOTKORMÁNY', cx, cy + r + 12 * u, DIM, 9 * u + 2, 'center');
  }
  pitchLadder(ac, cam, camCtl) {
    const hdg = Math.atan2(ac.forward.x, ac.forward.y), pitch = Math.asin(clamp(ac.forward.z, -1, 1)) / DEG;
    const dir = (h, e) => V(Math.sin(h) * Math.cos(e), Math.cos(h) * Math.cos(e), Math.sin(e));
    for (let e = -80; e <= 80; e += 10) {
      if (Math.abs(e - pitch) > 16) continue;          // like the real HUD: only near the boresight
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
    this.nearestEnemy = world.aircraft.filter((t) => t.alive && t.team !== ac.team)
      .reduce((b, t) => (!b || len(sub(t.pos, ac.pos)) < len(sub(b.pos, ac.pos)) ? t : b), null);
    for (const t of world.aircraft) {
      if (t !== ac && t.alive && t.team === ac.team) {           // wingman: cyan ring with the distance
        const p = this.project(cam, t.pos), d = len(sub(t.pos, ac.pos));
        if (p && d < 40000) {
          this.circle(p[0], p[1], 9 * u, CYAN);
          this.text(`KÍSÉRŐ ${(d / 1000).toFixed(1)}`, p[0], p[1] - 18 * u, CYAN, 10 * u + 2, 'center');
        }
        continue;
      }
      if (t === ac || !t.alive || t.team === ac.team) continue;
      const d = len(sub(t.pos, ac.pos));
      if (d > 80000) continue;
      const p = this.project(cam, t.pos);
      if (!p) continue;
      if (t === this.lockTarget(ac, ac.selectedSpec)) continue;      // drawn by the lock box
      this.poly([[p[0] - 8 * u, p[1] - 20 * u], [p[0] + 8 * u, p[1] - 20 * u], [p[0], p[1] - 10 * u]], ENEMY);
      this.text((d / 1000).toFixed(1), p[0], p[1] - 30 * u, ENEMY, 11 * u + 2, 'center');
      // in radar lock range and not locked yet: tell how
      // (a stealthy F-22 only shows up on radar much closer)
      const lockable = Math.min(ac.spec.radar.lockRange, radarRange(ac.spec.radar.searchRange, rcs(t, ac.pos)));
      if (ac.radar.mode !== STT && t === this.nearestEnemy) {
        if (d < lockable) this.text('T = lock', p[0], p[1] + 2 * u, AMBER, 11 * u + 2, 'center');
        else if (t.spec.rcsFront < 0.01 && d < 40000) this.text(`lopakodó - radar ~${(lockable / 1000).toFixed(0)} km-től`, p[0], p[1] + 2 * u, DIM, 10 * u + 2, 'center');
      }
    }
  }
  // the combat zone (amber) and the home base (cyan): marker with the distance, and an arrow at the screen
  // edge towards the zone while it is behind you
  navMarks(ac, cam) {
    const n = this.nav, u = this.u;
    if (!n) return;
    const dz = Math.hypot(n.zone.x - ac.pos.x, n.zone.y - ac.pos.y), db = Math.hypot(n.base.x - ac.pos.x, n.base.y - ac.pos.y);
    const where = db < n.base.r ? ['BIZTONSÁGI ZÓNA (bázis) - itt nem támadnak', CYAN] : dz < n.zone.r ? ['HARCI ZÓNA', ENEMY] : null;
    if (where) this.text(where[0], 20 * u, 62 * u, where[1], 11 * u + 2);
    if (!this.markers) return;
    if (dz > n.zone.r) {
      const pos = V(n.zone.x, n.zone.y, Math.max(ac.pos.z, 3500)), p = this.project(cam, pos);
      if (p) {
        const k = 11 * u;
        this.poly([[p[0], p[1] - k], [p[0] + k, p[1]], [p[0], p[1] + k], [p[0] - k, p[1]]], AMBER);
        this.text(`HARCI ZÓNA ${((dz - n.zone.r) / 1000).toFixed(0)} km`, p[0], p[1] - 22 * u, AMBER, 12 * u + 2, 'center');
      } else this.edgeArrow(cam, pos, AMBER);
    }
    if (n.carrier) {                                   // the carrier: cyan ship mark with the distance
      const dc = Math.hypot(n.carrier.x - ac.pos.x, n.carrier.y - ac.pos.y);
      const p = dc > 900 ? this.project(cam, V(n.carrier.x, n.carrier.y, 40)) : null;
      if (p) {
        const k = 9 * u;
        this.poly([[p[0] - k, p[1]], [p[0] - k * 0.6, p[1] + k * 0.6], [p[0] + k * 0.6, p[1] + k * 0.6], [p[0] + k, p[1]]], CYAN);
        this.text(`HORDOZÓ ${(dc / 1000).toFixed(dc < 10000 ? 1 : 0)} km`, p[0], p[1] + 20 * u, CYAN, 11 * u + 2, 'center');
      }
    }
    if (db > 3000) {
      const p = this.project(cam, V(n.base.x, n.base.y, 300));
      if (p) {
        const k = 8 * u;
        this.rect(p[0], p[1], k, k, CYAN);
        this.text(`BÁZIS ${(db / 1000).toFixed(0)} km`, p[0], p[1] + 20 * u, CYAN, 11 * u + 2, 'center');
      }
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
      if (!p) this.edgeArrow(cam, r.trackPos, col);
      else if (r.lostTime > 0) this.text('MEM', p[0], p[1] + 40 * u, AMBER, 12 * u + 2, 'center');
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
    this.missilePaths(ac, world, cam);
    if (!sp) return;
    if (sp.guidance === IR && ac.irSeeker.axis) {
      const s = ac.irSeeker, p = this.project(cam, add(ac.pos, mul(s.axis, 2000)));
      if (p) {
        if (s.locked) { this.circle(p[0], p[1], 26 * u, GREEN); this.circle(p[0], p[1], 29 * u, GREEN); this.poly([[p[0], p[1] - 7 * u], [p[0] + 7 * u, p[1]], [p[0], p[1] + 7 * u], [p[0] - 7 * u, p[1]]], GREEN); }
        else {
          // search circle as big as the seeker's search cone (wide with the lock assist)
          const fov = (s.acqFov || s.spec.seekerFov) * DEG;
          const rad = Math.max(26 * u, Math.tan(fov) / Math.tan(cam.fov * DEG / 2) * this.h / 2);
          this.circle(p[0], p[1], rad, s.candidate ? (Math.floor(this.time * 10) % 2 ? WHITE : GREEN) : DIM);
        }
      }
    }
    this.dlzBar(ac, sp, dt);
    this.lockBox(ac, sp, cam);
  }

  // what the selected missile is locked on (radar STT or IR seeker), or null
  lockTarget(ac, sp) {
    if (sp && sp.guidance === IR && ac.irSeeker.locked && !ac.irSeeker.target.isFlare) return ac.irSeeker.target;
    const r = ac.radar;
    return r.mode === STT && r.locked && r.locked.alive ? r.locked : null;
  }

  // big square around the locked aircraft + where a missile fired now would meet it
  lockBox(ac, sp, cam) {
    const t = this.lockTarget(ac, sp);
    if (!t) return;
    const u = this.u, r = ac.radar;
    const pos = r.mode === STT && r.locked === t && r.trackPos ? r.trackPos : t.pos;
    const p = this.project(cam, pos);
    const rel = sub(pos, ac.pos), d = len(rel);
    const inRange = this.dlz && sp && d > sp.minRange && d < this.dlz[0];
    const blink = Math.floor(this.time * 4) % 2 === 0;
    const col = inRange ? RED : GREEN;
    // predicted intercept point: where the target will be when a missile launched now reaches it
    if (sp) {
      let tt = flyoutTime(sp, ac.speed, ac.pos.z, d), ip = pos;
      for (let i = 0; i < 4 && tt !== null; i++) {
        ip = add(pos, mul(t.vel, tt));
        tt = flyoutTime(sp, ac.speed, ac.pos.z, len(sub(ip, ac.pos)));
      }
      const a = this.project(cam, add(ac.pos, mul(ac.forward, 25))), b = tt !== null ? this.project(cam, ip) : null;
      if (a && b) {
        this.dashed(a[0], a[1], b[0], b[1], col, 10 * u, 7 * u);
        if (p) this.dashed(p[0], p[1], b[0], b[1], ENEMY, 4 * u, 5 * u);
        const k = 9 * u;
        this.line(b[0] - k, b[1] - k, b[0] + k, b[1] + k, col); this.line(b[0] - k, b[1] + k, b[0] + k, b[1] - k, col);
        this.circle(b[0], b[1], 13 * u, col);
        this.text(`találat ~${tt.toFixed(0)} s`, b[0] + 18 * u, b[1] + 14 * u, col, 11 * u + 2);
      }
    }
    if (!p) return;
    // box sized to the target's wingspan on screen
    const pxPerM = this.h / 2 / Math.tan(cam.fov * DEG / 2) / Math.max(d, 1);
    const hs = clamp(7 * pxPerM, 26 * u, 140 * u);
    const g = this.g, lw = g.lineWidth;
    g.lineWidth = Math.max(2.5, 3 * u);
    this.rect(p[0], p[1], hs, hs, col);
    g.lineWidth = lw;
    for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
      // outer corner ticks make the box readable against bright clouds
      this.line(p[0] + sx * (hs + 4 * u), p[1] + sy * hs, p[0] + sx * (hs + 12 * u), p[1] + sy * hs, col);
      this.line(p[0] + sx * hs, p[1] + sy * (hs + 4 * u), p[0] + sx * hs, p[1] + sy * (hs + 12 * u), col);
    }
    const vc = -dot(sub(t.vel, ac.vel), norm(rel));
    this.text(`LOCK  ${sp ? sp.name : ''}`, p[0] - hs, p[1] - hs - 14 * u, col, 13 * u + 3, 'left', 'Oswald, Impact, sans-serif');
    this.text(`${(d / 1000).toFixed(1)} km   Vc ${vc * 3.6 >= 0 ? '+' : ''}${Math.round(vc * 3.6)}`, p[0] - hs, p[1] + hs + 14 * u, col, 11 * u + 2);
    if (inRange && blink) this.text('LŐHETSZ!  (Space)', p[0], p[1] + hs + 34 * u, RED, 15 * u + 4, 'center', 'Oswald, Impact, sans-serif');
    else if (!inRange && sp && sp.guidance === IR && d > 9000 && ac.missileCount('AIM-120A')) this.text('messze van - válts AIM-120-ra (2)', p[0], p[1] + hs + 34 * u, AMBER, 12 * u + 2, 'center');
    else if (!inRange && sp && d >= this.dlz?.[0]) this.text('még messze', p[0], p[1] + hs + 34 * u, AMBER, 12 * u + 2, 'center');
    else if (!inRange && sp && d <= sp.minRange) this.text('túl közel', p[0], p[1] + hs + 34 * u, AMBER, 12 * u + 2, 'center');
  }

  // own missiles in flight: marker on the missile and its path to the target
  missilePaths(ac, world, cam) {
    const u = this.u;
    for (const m of world.missiles) {
      if (m.shooter !== ac || !m.alive) continue;
      const mp = this.project(cam, m.pos);
      const aim = m.guidedTarget ? m.guidedTarget.pos : m.estPos;
      const ap = aim ? this.project(cam, aim) : null;
      if (mp && ap) this.dashed(mp[0], mp[1], ap[0], ap[1], CYAN, 6 * u, 6 * u);
      if (mp) {
        this.poly([[mp[0], mp[1] - 7 * u], [mp[0] + 7 * u, mp[1]], [mp[0], mp[1] + 7 * u], [mp[0] - 7 * u, mp[1]]], CYAN);
        const ttg = timeToImpact(m);
        if (ttg !== null && ttg < 99) this.text(`${ttg.toFixed(1)} s`, mp[0] + 10 * u, mp[1] - 10 * u, CYAN, 11 * u + 2);
      }
    }
  }
  dashed(x1, y1, x2, y2, c, on, off) {
    const g = this.g; g.save(); g.setLineDash([on, off]); this.line(x1, y1, x2, y2, c); g.restore();
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
    const cmd = ac.controls.throttle, thr = cmd > 1 ? 'AB' : `${Math.round(cmd * 100)}%`;
    const eng = fm.engine > 1.001 ? 'AB' : `${Math.round(fm.engine * 100)}%`;
    const rows = [
      [`IAS ${String(Math.round(fm.ias * 3.6)).padStart(5)} km/h`, GREEN], [`TAS ${String(Math.round(ac.speed * 3.6)).padStart(5)}`, DIM],
      [`M   ${fm.mach.toFixed(2).padStart(5)}`, GREEN], [`G   ${fm.gLoad.toFixed(1).padStart(5)}`, fm.gLoad > ac.spec.gMax * 0.85 ? AMBER : GREEN],
      [`AoA ${(fm.alpha / DEG).toFixed(1).padStart(5)}`, fm.alpha / DEG > ac.spec.alphaLimit * 0.8 ? AMBER : GREEN], [`THR  ${thr}`, cmd > 1 ? AMBER : GREEN], [`MOT  ${eng}`, Math.abs(fm.engine - cmd) > 0.02 ? DIM : GREEN],
      [fm.gearPos > 0.98 ? 'GEAR DOWN' : fm.gearPos > 0.02 ? 'GEAR TRANSIT' : 'GEAR UP', fm.gearPos > 0.98 ? GREEN : fm.gearPos > 0.02 ? AMBER : DIM],
    ];
    if (ac.onGround) rows.push([`GS  ${String(Math.round(ac.speed * 3.6)).padStart(5)} km/h`, GREEN]);
    if (ac.extreme) rows.push([`${ac.spec.tvcAlways ? 'TVC' : 'TVC EXTRÉM'}${ac.fm.alpha / DEG > 50 ? '  COBRA' : ''}`, ac.spec.tvcAlways ? DIM : AMBER]);
    if (ac.bayOpenAny > 0.05) rows.push(['FEGYVERTÉR NYITVA', AMBER]);
    if (ac.controls.brakes && ac.onGround) rows.push(['BRAKES', AMBER]);
    else if (ac.controls.airbrake) rows.push(['SPD BRK', AMBER]);
    rows.forEach(([t, c], i) => this.text(t, x, y + i * lh, c, fs));
    // during the tutorial its card covers the right side: the right column goes under the left one
    const terr = world.terrain.height(ac.pos.x, ac.pos.y), xr = this.tutorial ? x : this.w / 2 + 250 * u;
    const yr = this.tutorial ? y + (rows.length + 0.6) * lh : y;
    const fuelCol = fm.fuel < ac.spec.internalFuel * 0.12 ? RED : fm.fuel < ac.spec.internalFuel * 0.28 ? AMBER : GREEN;
    const right = [
      [`ALT ${String(Math.round(ac.pos.z)).padStart(6)} m`, GREEN], [`AGL ${String(Math.round(ac.pos.z - terr)).padStart(6)}`, DIM],
      [`VS  ${(fm.vel.z >= 0 ? '+' : '') + Math.round(fm.vel.z)}`, GREEN], [`HDG    ${String(Math.round(headingDeg(ac.forward))).padStart(3, '0')}`, GREEN],
      [`FUEL ${String(Math.round(fm.fuel)).padStart(5)} kg`, fuelCol], [`HP   ${String(Math.max(0, Math.round(ac.hp))).padStart(5)}`, ac.hp > 50 ? GREEN : RED],
    ];
    right.forEach(([t, c], i) => this.text(t, xr, yr + i * lh, c, fs));
    // weapons
    const reloadText = (k) => {
      const r = ac.stations.filter((s) => s.key === k && !s.loaded && s.reload !== undefined).map((s) => s.reload);
      return r.length ? ` +${r.length} (${Math.ceil(Math.min(...r))}s)` : '';
    };
    // in the cockpit the weapon lines go to the top of the screen: the bottom shows the displays
    const yb = this.cockpit ? 92 * u : this.h - 78 * u, parts = ac.weaponKeys().map((k) => {
      const t = `${k} ×${ac.missileCount(k)}${reloadText(k)}`;
      return k === ac.selected ? `[${t}]` : ` ${t} `;
    });
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
    // touch layout: the buttons own the bottom corners, the scope goes up under the top buttons
    const cx = this.w - hw - 24 * u, cy = this.touchLayout ? 175 * u + hw : this.h - hw - 24 * u, left = cx - hw, top = cy - hw, bottom = cy + hw;
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
    const u = this.u, R = 90 * u, cx = R + 26 * u, cy = this.touchLayout ? 125 * u + R : this.h - R - 26 * u, g = this.g;
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
    if (ac.fm.fuel > 0 && ac.fm.fuel < ac.spec.internalFuel * 0.12) big('BINGO FUEL', AMBER, 22);
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
  // G-LOC grey-out / blackout under sustained positive G, red-out under negative G
  gEffects(ac, dt) {
    if (!ac || !ac.alive) { this.black = 0; this.red = 0; return; }
    const g = ac.fm.gLoad;
    // G-suit: up to ~8 G the pilot keeps the picture; a held 9 G turn greys out slowly (~6 s)
    this.black = clamp((this.black || 0) + (g > 8.2 ? (g - 8.2) * 0.12 : g < 7 ? -0.4 : 0) * dt, 0, 1);
    this.red = clamp((this.red || 0) + (g < -1.8 ? (-g - 1.8) * 0.35 : -0.6) * dt, 0, 1);
    const gfx = this.g, w = this.w, h = this.h, R = Math.hypot(w, h) / 2;
    for (const [lvl, rgb] of [[this.black, '0,0,0'], [this.red, '150,0,0']]) {
      if (lvl <= 0.01) continue;
      const grd = gfx.createRadialGradient(w / 2, h / 2, R * Math.max(0.05, 0.75 - lvl * 0.8), w / 2, h / 2, R * (1.05 - lvl * 0.25));
      grd.addColorStop(0, `rgba(${rgb},0)`); grd.addColorStop(1, `rgba(${rgb},${Math.min(0.97, lvl * 1.4)})`);
      gfx.fillStyle = grd; gfx.fillRect(0, 0, w, h);
      if (lvl > 0.6) { gfx.fillStyle = `rgba(${rgb},${(lvl - 0.6) * 2.2})`; gfx.fillRect(0, 0, w, h); }
    }
  }
  // missiles flying at the player: red marker (or edge arrow) with distance and time to impact
  incomingMissiles(ac, cam) {
    const u = this.u, blink = Math.floor(this.time * 6) % 2 === 0;
    for (const { missile: m, dist } of ac.rwr.incoming) {
      const p = this.project(cam, m.pos);
      const closing = dot(sub(m.vel, ac.vel), norm(sub(ac.pos, m.pos)));
      const tti = closing > 1 ? dist / closing : null;
      if (!p) { this.edgeArrow(cam, m.pos, RED); continue; }
      const k = 14 * u;
      this.poly([[p[0], p[1] - k], [p[0] + k, p[1]], [p[0], p[1] + k], [p[0] - k, p[1]]], RED);
      if (blink) this.circle(p[0], p[1], 22 * u, RED);
      this.text(`RAKÉTA ${(dist / 1000).toFixed(1)} km${tti !== null && tti < 60 ? '  ' + tti.toFixed(1) + ' s' : ''}`, p[0] + 26 * u, p[1], RED, 12 * u + 2);
    }
  }
  overlay(game) {
    const u = this.u, fs = 12 * u + 3;
    this.text(`HULLÁM ${game.wave}   LELŐVE ${game.kills}   HALÁL ${game.deaths}`, 20 * u, 22 * u, WHITE, fs);
    const hint = this.cockpit ? 'H = súgó   Esc = menü   N = kijelzők nézése   J / K / L = lapozás' : 'H = súgó   Esc = menü   V = kabin   N = kijelzők';
    this.text(hint, 20 * u, 42 * u, DIM, 11 * u + 2);
    // F-16: where the extreme mode is (it has no menu entry, only the key)
    const p = this.player;
    if (p && p.alive && p.spec.tvc && !p.spec.tvcAlways) {
      this.g.font = `${11 * u + 2}px ${MONO}`;
      const x = 20 * u + this.g.measureText(hint + '   ').width;
      this.text(p.extreme ? 'Tab = EXTRÉM mód KI' : 'Tab = EXTRÉM mód (TVC, 9 G, Cobra)', x, 42 * u, AMBER, 11 * u + 2);
    }
    let y = 22 * u;
    for (const k of this.killfeed) { this.text(k.text, this.w - 20 * u, y, k.color, fs, 'right'); y += 20 * u + 3; }
    if (game.banner) this.text(game.banner, this.w / 2, this.h / 2 - 40 * u, WHITE, 44 * u + 6, 'center', 'Oswald, Impact, sans-serif');
    if (game.subBanner) this.text(game.subBanner, this.w / 2, game.banner ? this.h / 2 + 10 * u : 80 * u, WHITE, 15 * u + 3, 'center');
  }
}
