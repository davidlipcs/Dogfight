// Live cockpit displays: every screen of the instrument panel is a canvas texture with pages like the real
// ones - radar (B-scope), situation map (HSD / AMPCD), stores (SMS), engines and performance, RWR, and the
// data line (F-16 DED / Hornet UFCD).  They show more than the HUD overlay: target type and data, energy
// rate (Ps), thrust to weight, fuel to get home, the combat zone and the base on a map.
import { THREE, V, sub, len, norm, dot, clamp, DEG, toLocal, headingDeg, angleBetween } from './util.js';
import { isa } from './flight.js';
import { IR, ARH } from './specs.js';
import { STT, ACM, OFF, launchZone } from './weapons.js';

const C = {
  bg: '#020805', g: '#52ff73', gd: '#2c9c47', gdd: '#14451f', w: '#eaffea', a: '#ffc23a', r: '#ff4b3b', c: '#62d9ff',
};
const FONT = '"JetBrains Mono", Consolas, "Courier New", monospace';
const PAGE_NAMES = { radar: 'RDR', sa: 'SA', sms: 'SMS', eng: 'ENG', rwr: 'RWR' };

// screen name -> canvas size, pages and the key that cycles them
const LAYOUTS = {
  f16: {
    mfd_l: { w: 512, h: 512, pages: ['radar', 'sms', 'eng'], key: 'J', inset: 0.09 },
    mfd_r: { w: 512, h: 512, pages: ['sa', 'eng', 'sms'], key: 'K', inset: 0.09 },
    ded: { w: 512, h: 180, pages: ['ded'], inset: 0.04 },
    rwr: { w: 256, h: 256, pages: ['rwrmini'], inset: 0.04 },
  },
  fa18: {
    screen_ddi_l: { w: 512, h: 512, pages: ['eng', 'sms', 'rwr'], key: 'J' },
    screen_ddi_r: { w: 512, h: 512, pages: ['radar', 'sms'], key: 'K' },
    screen_ampcd: { w: 512, h: 512, pages: ['sa', 'rwr'], key: 'L' },
    screen_ufcd: { w: 512, h: 420, pages: ['ded'] },
  },
};
const SIDE_KEYS = { left: 'J', right: 'K', center: 'L' };

const bearingTo = (ac, p) => ((Math.atan2(p.x - ac.pos.x, p.y - ac.pos.y) / DEG) + 360) % 360;
const pad3 = (d) => String(Math.round(d) % 360).padStart(3, '0');
const km = (m) => (m >= 10000 ? (m / 1000).toFixed(0) : (m / 1000).toFixed(1));

export class CockpitDisplays {
  constructor(spec, screens) {
    this.spec = spec; this.list = []; this.turn = 0; this.time = 0; this.gHi = 1; this.gLo = 1; this.dlzCache = new Map();
    const layout = LAYOUTS[spec.model] || LAYOUTS.f16;
    for (const [name, lay] of Object.entries(layout)) {
      const meshes = screens[name];
      if (!meshes || !meshes.length) continue;
      const canvas = document.createElement('canvas');
      canvas.width = lay.w; canvas.height = lay.h;
      const tex = new THREE.CanvasTexture(canvas);
      tex.encoding = THREE.sRGBEncoding; tex.anisotropy = 8;
      const mat = new THREE.MeshBasicMaterial({ map: tex, toneMapped: false });
      for (const m of meshes) m.material = mat;
      this.list.push({ name, ...lay, canvas, g: canvas.getContext('2d'), tex, page: 0 });
    }
    this.fresh = true;
  }
  cycle(side) {
    const d = this.list.find((x) => x.key === SIDE_KEYS[side]);
    if (!d || d.pages.length < 2) return null;
    d.page = (d.page + 1) % d.pages.length;
    if (this.last) this.draw(d, this.last.ac, this.last.world, this.last.info);
    return PAGE_NAMES[d.pages[d.page]];
  }
  update(dt, ac, world, info) {
    this.time += dt;
    this.last = { ac, world, info };
    if (ac.alive) { this.gHi = Math.max(this.gHi, ac.fm.gLoad); this.gLo = Math.min(this.gLo, ac.fm.gLoad); }
    // half of the displays per frame (each one ~30 times a second), all of them the first time
    const n = this.fresh ? this.list.length : Math.ceil(this.list.length / 2);
    this.fresh = false;
    for (let k = 0; k < n; k++) this.draw(this.list[(this.turn++) % this.list.length], ac, world, info);
  }

  // --------------------------------------------------------------- drawing
  draw(d, ac, world, info) {
    const g = d.g, W = d.w, H = d.h;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.fillStyle = C.bg; g.fillRect(0, 0, W, H);
    g.lineWidth = 2.5; g.lineCap = 'round'; g.lineJoin = 'round';
    const page = d.pages[d.page];
    // the old F-16 panel's bezels cover the screen edges: draw the page a little smaller
    if (d.inset) { const k = 1 - 2 * d.inset; g.setTransform(k, 0, 0, k, W * d.inset, H * d.inset); }
    if (!ac.alive) { this.text(g, 'NO DATA', W / 2, H / 2, C.gd, Math.round(H / 8), 'center'); d.tex.needsUpdate = true; return; }
    this[page](g, W, H, ac, world, info, d);
    if (d.pages.length > 1) this.osb(g, W, H, d);
    // a faint scanline glow: the screen reads as a display, not a sticker
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.fillStyle = 'rgba(82,255,115,0.025)';
    for (let y = 0; y < H; y += 4) g.fillRect(0, y, W, 1);
    d.tex.needsUpdate = true;
  }
  text(g, t, x, y, col, size, align = 'left', bold = true) {
    g.font = `${bold ? '700 ' : ''}${size}px ${FONT}`; g.textAlign = align; g.textBaseline = 'middle';
    g.fillStyle = col; g.fillText(t, x, y);
  }
  line(g, x1, y1, x2, y2, col, w = 2.5) { g.strokeStyle = col; g.lineWidth = w; g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke(); }
  circle(g, x, y, r, col, w = 2.5, dash = null) {
    g.strokeStyle = col; g.lineWidth = w; if (dash) g.setLineDash(dash);
    g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.stroke(); g.setLineDash([]);
  }
  poly(g, pts, col, fill = false, w = 2.5) {
    g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
    for (const p of pts.slice(1)) g.lineTo(p[0], p[1]);
    g.closePath();
    if (fill) { g.fillStyle = col; g.fill(); } else { g.strokeStyle = col; g.lineWidth = w; g.stroke(); }
  }
  box(g, x, y, w, h, col, lw = 2.5) { g.strokeStyle = col; g.lineWidth = lw; g.strokeRect(x, y, w, h); }
  // push-button labels along the bottom edge: the pages of this display, the shown one boxed
  osb(g, W, H, d) {
    const n = d.pages.length, step = W / (n + 1);
    d.pages.forEach((p, i) => {
      const x = step * (i + 1), active = i === d.page;
      this.text(g, PAGE_NAMES[p], x, H - 18, active ? C.w : C.gd, 24, 'center');
      if (active) this.box(g, x - 34, H - 34, 68, 32, C.w, 2);
    });
    this.text(g, d.key, W - 14, H - 18, C.gdd, 20, 'right');
  }

  // ------------------------------------------------------------------ radar
  radar(g, W, H, ac, world, info) {
    const r = ac.radar, sp = r.spec;
    const x0 = 34, x1 = W - 74, y0 = 62, y1 = H - 150, cx = (x0 + x1) / 2, sw = x1 - x0, sh = y1 - y0;
    const tgt = r.locked || r.pending || r.selected;
    let scale = sp.searchRange > 80000 ? 80000 : 40000;
    if (r.mode === ACM) scale = 20000;
    else if (tgt) { const dd = len(sub(tgt.pos, ac.pos)); scale = [10000, 20000, 40000, 80000, 160000].find((s) => dd < s * 0.85) || 160000; }
    this.text(g, r.mode === OFF ? 'RDR OFF' : r.mode, 14, 24, r.mode === STT ? C.w : C.g, 28);
    this.text(g, `${scale / 1000} KM`, W / 2 - 20, 24, C.g, 28, 'center');
    this.text(g, sp.name.includes('79') ? 'APG-79' : 'APG-68', W - 14, 24, C.gd, 22, 'right');
    // scope frame, azimuth and range ticks
    this.box(g, x0, y0, sw, sh, C.gd, 2);
    const azMax = sp.scanAz * DEG, toXY = (az, dist) => [cx + clamp(az / azMax, -1, 1) * sw / 2, y1 - Math.min(dist / scale, 1) * sh];
    for (const az of [-30, 0, 30]) { const x = cx + az / sp.scanAz * sw / 2; g.setLineDash([4, 10]); this.line(g, x, y0, x, y1, C.gdd, 2); g.setLineDash([]); }
    for (const k of [1, 2, 3]) { const y = y1 - sh * k / 4; this.line(g, x0, y, x0 + 14, y, C.gd); this.line(g, x1 - 14, y, x1, y, C.gd); }
    this.text(g, `${scale / 2000}`, x0 + 18, y1 - sh / 2, C.gd, 20);
    if (r.mode === OFF) { this.text(g, 'R = RADAR BE', cx, (y0 + y1) / 2, C.a, 30, 'center'); }
    else if (r.mode === ACM) {
      const w = sp.acmAz / sp.scanAz * sw / 2, y = y1 - Math.min(sp.acmRange / scale, 1) * sh;
      this.poly(g, [[cx - w, y1], [cx - w, y], [cx + w, y], [cx + w, y1]], C.a);
    } else if (r.mode !== STT) {
      const x = cx + r.beamAz / azMax * sw / 2;
      this.line(g, x, y1, x, y0, 'rgba(82,255,115,0.35)', 3);
    }
    // own heading caret
    this.poly(g, [[cx, y1 + 4], [cx - 10, y1 + 20], [cx + 10, y1 + 20]], C.g);
    for (const [t, c] of r.contacts) {
      if (t === r.locked) continue;
      const [x, y] = toXY(c.az, c.range);
      const col = t.team === ac.team ? C.c : C.g;
      g.fillStyle = col; g.fillRect(x - 9, y - 9, 18, 18);
      const hl = toLocal(ac.quat, c.vel), hn = Math.hypot(hl.x, hl.y);
      if (hn > 1) this.line(g, x, y, x + hl.x / hn * 30, y - hl.y / hn * 30, col);
      this.text(g, (c.pos.z / 1000).toFixed(0), x + 14, y + 16, C.gd, 20);
      if (t === r.selected) this.box(g, x - 16, y - 16, 32, 32, C.w, 2);
    }
    if (r.pending && Math.floor(this.time * 8) % 2 === 0) {
      const [az, , dd] = r.anglesTo(r.pending.pos), [x, y] = toXY(az, dd);
      this.box(g, x - 20, y - 20, 40, 40, C.a, 3);
    }
    let lines;
    if (r.locked && r.trackPos) {
      const [az, , dd] = r.anglesTo(r.trackPos), [x, y] = toXY(az, dd), col = r.lostTime > 0 ? C.a : C.w;
      this.poly(g, [[x, y - 16], [x + 16, y], [x, y + 16], [x - 16, y]], col, true);
      const hl = toLocal(ac.quat, r.trackVel), hn = Math.hypot(hl.x, hl.y);
      if (hn > 1) this.line(g, x, y, x + hl.x / hn * 44, y - hl.y / hn * 44, col, 3.5);
      const t = r.locked, rel = sub(r.trackPos, ac.pos), vc = -dot(sub(r.trackVel, ac.vel), norm(rel));
      const aspDeg = angleBetween(r.trackVel, sub(ac.pos, r.trackPos)) / DEG;
      const side = toLocal(t.quat, sub(ac.pos, t.pos)).x >= 0 ? 'R' : 'L';
      const tm = len(r.trackVel) / isa(r.trackPos.z)[1];
      lines = [
        [`STT  ${km(dd)} KM   VC ${vc >= 0 ? '+' : ''}${Math.round(vc * 3.6)}`, r.notched ? C.a : C.w],
        [`MAG ${(r.trackPos.z / 1000).toFixed(1)} KM  M${tm.toFixed(2)}  ASP ${Math.round(aspDeg)}${side}`, C.g],
        [`NCTR: ${t.spec.short || t.spec.name}${r.notched ? '   NOTCH!' : r.lostTime > 0 ? '   MEMÓRIA' : ''}`, r.notched || r.lostTime > 0 ? C.a : C.g],
      ];
    } else {
      lines = [
        [`CÉLOK: ${[...r.contacts.keys()].filter((t) => t.team !== ac.team).length}`, C.g],
        [r.mode === ACM ? 'ACM: CÉL AZ ORR ELÉ' : 'T = LOCK   Y = KÖV. CÉL', r.mode === ACM ? C.a : C.gd],
        [r.selected ? `KIJELÖLT: ${km(len(sub(r.selected.pos, ac.pos)))} KM  ${(r.selected.pos.z / 1000).toFixed(1)} KM MAG` : '', C.gd],
      ];
    }
    lines.forEach(([t, col], i) => this.text(g, t, 22, y1 + 40 + i * 30, col, 24));
    this.dlz(g, W, H, ac, x1 + 34, y0, y1);
  }
  // launch zone of the selected missile against the locked target: Rmax, no-escape range, Rmin, the target
  dlz(g, W, H, ac, x, y0, y1) {
    const sp = ac.selectedSpec, r = ac.radar;
    let t = r.mode === STT ? r.locked : null;
    if (sp && sp.guidance === IR && ac.irSeeker.locked && !ac.irSeeker.target.isFlare) t = ac.irSeeker.target;
    this.text(g, sp ? (sp.guidance === IR ? '9M' : '120') : '--', x, y0 - 18, C.g, 22, 'center');
    if (!sp || !t) return;
    const rel = sub(t.pos, ac.pos), dd = len(rel), closing = -dot(t.vel, norm(rel));
    let z = this.dlzCache.get(sp);
    if (!z || this.time - z.time > 0.5) { z = { time: this.time, v: launchZone(sp, ac.speed, ac.pos.z, closing) }; this.dlzCache.set(sp, z); }
    const [rmax, rne] = z.v, rmin = sp.minRange;
    const scale = Math.max(rmax * 1.25, dd * 1.05, 2000), ry = (v) => y1 - (y1 - y0) * clamp(v / scale, 0, 1);
    this.line(g, x, ry(rmin), x, ry(rmax), C.g, 4);
    for (const v of [rmax, rmin]) this.line(g, x - 12, ry(v), x + 12, ry(v), C.g, 3);
    this.line(g, x - 18, ry(rne), x + 18, ry(rne), C.g, 3);
    const yy = ry(dd), inRng = dd > rmin && dd < rmax;
    this.poly(g, [[x - 30, yy - 11], [x - 14, yy], [x - 30, yy + 11]], inRng ? C.r : C.w, true);
    this.text(g, km(rmax), x, ry(rmax) - 18, C.gd, 20, 'center');
    if (inRng && Math.floor(this.time * 4) % 2 === 0) this.text(g, dd < rne ? 'NOESC' : 'SHOOT', x, y1 + 24, C.r, 20, 'center');
  }

  // ------------------------------------------------------- situation map
  sa(g, W, H, ac, world, info) {
    const hdg = Math.atan2(ac.forward.x, ac.forward.y), ch = Math.cos(hdg), sh = Math.sin(hdg);
    const cx = W / 2, cy = H * 0.66, enemies = world.aircraft.filter((t) => t.alive && t.team !== ac.team);
    const nearest = enemies.reduce((m, t) => Math.min(m, len(sub(t.pos, ac.pos))), Infinity);
    const toZone = info.zone ? Math.hypot(info.zone.x - ac.pos.x, info.zone.y - ac.pos.y) : 0;
    let range = 40000;
    if (nearest < 14000) range = 20000;
    else if (nearest > 40000 && toZone > 38000) range = 80000;
    const k = (H * 0.58) / range;
    const toS = (p) => {
      const rx = p.x - ac.pos.x, ry = p.y - ac.pos.y;
      return [cx + (rx * ch - ry * sh) * k, cy - (rx * sh + ry * ch) * k];
    };
    g.save();
    g.beginPath(); g.rect(6, 50, W - 12, H - 110); g.clip();
    // range rings and compass rose
    this.circle(g, cx, cy, range * k, C.gd, 3); this.circle(g, cx, cy, range * k / 2, C.gd, 2.5, [8, 10]);
    for (let a = 0; a < 360; a += 30) {
      const ang = a * DEG - hdg, r0 = range * k, r1 = r0 - (a % 90 ? 10 : 18);
      this.line(g, cx + Math.sin(ang) * r0, cy - Math.cos(ang) * r0, cx + Math.sin(ang) * r1, cy - Math.cos(ang) * r1, C.gd, 2);
      if (a % 90 === 0) this.text(g, 'ÉKDN'[a / 90], cx + Math.sin(ang) * (r0 - 34), cy - Math.cos(ang) * (r0 - 34), C.gd, 22, 'center');
    }
    // base and its safe area, the combat zone
    if (info.base) {
      const [bx, by] = toS(info.base);
      this.circle(g, bx, by, info.base.r * k, 'rgba(98,217,255,0.55)', 2.5, [10, 8]);
      g.save(); g.translate(bx, by); g.rotate(-hdg);
      g.fillStyle = C.c; g.fillRect(-4, -16, 8, 32); g.restore();
      this.text(g, 'BÁZIS', bx + 12, by - 18, C.c, 20);
    }
    if (info.zone) {
      const [zx, zy] = toS(info.zone);
      this.circle(g, zx, zy, info.zone.r * k, 'rgba(255,75,59,0.7)', 3, [14, 10]);
      this.text(g, 'HARCI ZÓNA', zx, zy, 'rgba(255,75,59,0.85)', 20, 'center');
    }
    // contacts: radar tracks filled, the rest of the picture (datalink) hollow
    for (const t of enemies) {
      const [x, y] = toS(t.pos), th = Math.atan2(t.forward.x, t.forward.y) - hdg;
      const tri = [[0, -14], [10, 10], [-10, 10]].map(([px, py]) => [x + px * Math.cos(th) - py * Math.sin(th), y + px * Math.sin(th) + py * Math.cos(th)]);
      const tracked = ac.radar.contacts.has(t) || ac.radar.locked === t;
      this.poly(g, tri, C.r, tracked);
      const vx = Math.sin(th), vy = -Math.cos(th);
      this.line(g, x + vx * 14, y + vy * 14, x + vx * 34, y + vy * 34, C.r, 2);
      this.text(g, (t.pos.z / 1000).toFixed(0), x + 14, y + 14, C.r, 18);
      if (ac.radar.locked === t) this.box(g, x - 20, y - 20, 40, 40, C.w, 2.5);
    }
    // missiles: ours cyan, the ones coming at us red
    const blink = Math.floor(this.time * 6) % 2 === 0;
    for (const m of world.missiles) {
      if (!m.alive) continue;
      const [x, y] = toS(m.pos);
      if (m.shooter === ac) { g.fillStyle = C.c; g.beginPath(); g.arc(x, y, 5, 0, Math.PI * 2); g.fill(); }
      else if ((m.guidedTarget === ac || m.intended === ac) && blink) this.text(g, 'M', x, y, C.r, 26, 'center');
    }
    // RWR bearings on the outer ring
    for (const t of ac.rwr.threats) {
      const r0 = range * k + 2, col = t.level === 'launch' ? C.r : t.level === 'lock' ? C.a : C.gd;
      this.line(g, cx + Math.sin(t.bearing) * r0, cy - Math.cos(t.bearing) * r0, cx + Math.sin(t.bearing) * (r0 - 24), cy - Math.cos(t.bearing) * (r0 - 24), col, 5);
    }
    g.restore();
    // own aircraft
    this.poly(g, [[cx, cy - 18], [cx + 12, cy + 12], [cx, cy + 5], [cx - 12, cy + 12]], C.w, true);
    // heading box, range, bearings to the zone and the base
    this.box(g, W / 2 - 46, 6, 92, 40, C.g, 2.5);
    this.text(g, pad3(headingDeg(ac.forward)), W / 2, 27, C.w, 30, 'center');
    this.text(g, `${range / 1000} KM`, 12, 27, C.gd, 22);
    this.text(g, `${enemies.length} BANDITA`, W - 12, 27, enemies.length ? C.r : C.gd, 22, 'right');
    const rows = [];
    if (info.zone) rows.push([`ZÓNA ${pad3(bearingTo(ac, info.zone))}° ${km(Math.max(0, toZone - info.zone.r))} KM`, toZone < info.zone.r ? C.r : C.a]);
    if (info.base) rows.push([`BÁZIS ${pad3(bearingTo(ac, info.base))}° ${km(Math.hypot(info.base.x - ac.pos.x, info.base.y - ac.pos.y))} KM`, C.c]);
    rows.forEach(([t, col], i) => this.text(g, t, i ? W - 12 : 12, H - 76, col, 21, i ? 'right' : 'left'));
  }

  // ----------------------------------------------------------------- stores
  sms(g, W, H, ac, world, info) {
    const sp = ac.spec, sel = ac.selected;
    this.text(g, 'SMS', 14, 26, C.g, 30);
    this.box(g, W - 196, 8, 184, 36, C.g, 2.5);
    this.text(g, 'MASTER ARM', W - 104, 27, C.w, 22, 'center');
    // planform from the spec's dimensions, stations at their real spanwise positions
    const span = sp.wingSpan, sx = (W - 60) / span, cx = W / 2, cy = 190;
    const half = span / 2 * sx, lenPx = Math.min(sp.length * sx * 0.62, 230);
    g.strokeStyle = C.gd; g.lineWidth = 2.5;
    this.poly(g, [[cx, cy - lenPx * 0.62], [cx + 16, cy - lenPx * 0.3], [cx + half, cy + 18], [cx + half, cy + 34], [cx + 22, cy + 40],
      [cx + 70, cy + lenPx * 0.42], [cx + 16, cy + lenPx * 0.38], [cx, cy + lenPx * 0.42], [cx - 16, cy + lenPx * 0.38],
      [cx - 70, cy + lenPx * 0.42], [cx - 22, cy + 40], [cx - half, cy + 34], [cx - half, cy + 18], [cx - 16, cy - lenPx * 0.3]], C.gd);
    for (const st of ac.stations) {
      const p = sp.stations[st.number], x = cx + p[0] * sx, y = cy + 34 + (Math.abs(p[0]) < 1.5 ? 30 : 0);
      const is9 = st.spec.guidance === IR, col = !st.loaded ? C.gdd : st.key === sel ? C.w : C.g;
      if (st.loaded) { g.fillStyle = col; g.fillRect(x - 15, y, 30, 54); }
      else this.box(g, x - 15, y, 30, 54, col, 2);
      this.text(g, is9 ? '9' : '120', x, y + 70, st.loaded ? col : C.gdd, is9 ? 22 : 18, 'center');
      this.text(g, String(st.number), x, y - 14, C.gd, 18, 'center');
      if (!st.loaded && st.reload !== undefined) this.text(g, `${Math.ceil(st.reload)}`, x, y + 27, C.a, 18, 'center');
    }
    const rows = [];
    for (const key of ac.weaponKeys()) {
      const total = ac.stations.filter((s) => s.key === key).length;
      rows.push([`${key === sel ? '>' : ' '} ${key.padEnd(9)} ${ac.missileCount(key)} / ${total}`, key === sel ? C.w : C.g]);
    }
    rows.push([`  GUN ${sp.gun.name}  ${ac.gun.ammo} RDS`, ac.gun.ammo ? C.g : C.a]);
    rows.push([`  FLARE ${ac.flares}   CHAFF ${ac.chaff}`, ac.flares ? C.g : C.a]);
    const s = ac.selectedSpec;
    let status = '', col = C.g;
    if (s && s.guidance === IR) {
      const sk = ac.irSeeker;
      status = sk.locked ? 'AIM-9M: LOCK' : sk.candidate ? 'AIM-9M: HŐFORRÁS (F)' : 'AIM-9M: KERESÉS';
      col = sk.locked ? C.w : sk.candidate ? C.a : C.gd;
    } else if (s && s.guidance === ARH) {
      const lock = ac.radar.mode === STT;
      status = lock ? 'AIM-120A: RADAR LOCK OK' : 'AIM-120A: NINCS LOCK (T)'; col = lock ? C.w : C.a;
    }
    rows.push([`  ${status}`, col]);
    rows.forEach(([t, c], i) => this.text(g, t, 18, 318 + i * 30, c, 23));
  }

  // ---------------------------------------------------- engines, fuel, performance
  eng(g, W, H, ac, world, info) {
    const fm = ac.fm, sp = ac.spec, n = sp.engines || 1, e = fm.engine;
    const ab = clamp((e - 1) / 0.1, 0, 1), dry = Math.min(e, 1);
    const rpm = e > 1 ? 100 + 2 * ab : 64 + 36 * Math.pow(dry, 0.7);
    const noz = e > 1 ? 25 + 75 * ab : 8 + 30 * (1 - dry);
    const egt = 420 + 430 * Math.pow(dry, 1.6) + 40 * ab;
    this.text(g, n > 1 ? 'ENG  F414-GE-400 ×2' : 'ENG  F110-GE-129', 14, 26, C.g, 26);
    // per engine: RPM bar, nozzle, temperature, fuel flow, thrust
    const colW = n > 1 ? 112 : 150;
    for (let k = 0; k < n; k++) {
      const x = 30 + k * colW, top = 64, bh = 180;
      this.text(g, n > 1 ? ['BAL', 'JOBB'][k] : 'RPM', x + 30, top, C.gd, 20, 'center');
      this.box(g, x + 10, top + 18, 40, bh, C.gd, 2);
      const f = clamp((rpm - 50) / 55, 0, 1);
      g.fillStyle = e > 1 ? C.a : C.g; g.fillRect(x + 12, top + 20 + bh * (1 - f), 36, bh * f - 4);
      this.text(g, `${Math.round(rpm)}%`, x + 30, top + bh + 40, e > 1 ? C.a : C.w, 24, 'center');
      this.text(g, `NOZ ${Math.round(noz)}`, x + 30, top + bh + 70, C.g, 19, 'center');
    }
    const ff = fm.fuelFlow * 3600 / n, thr = fm.thrust / n / 1000;
    const L = [
      [`EGT ${Math.round(egt)}°C`, egt > 870 ? C.a : C.g],
      [`FF  ${Math.round(ff)} KG/H${n > 1 ? ' ×2' : ''}`, C.g],
      [`THR ${thr.toFixed(1)} KN${n > 1 ? ' ×2' : ''}`, C.g],
      [e > 1 ? `AB  ${Math.round(ab * 100)}%` : 'AB  KI', e > 1 ? C.a : C.gd],
    ];
    const xl = n > 1 ? 262 : 210;
    L.forEach(([t, c], i) => this.text(g, t, xl, 82 + i * 34, c, 23));
    // performance: thrust to weight, specific excess power, drag, mass, G range
    const mass = fm.mass, tw = fm.thrust / (mass * 9.81);
    const ps = fm.vel.z + dot(fm.vel, fm.accel) / 9.81;
    const toBase = info.base ? Math.hypot(info.base.x - ac.pos.x, info.base.y - ac.pos.y) : 0;
    const perKm = sp.fuelFlowDry * 0.35 / 0.23, bingo = toBase / 1000 * perKm + sp.internalFuel * 0.08;
    const minutes = fm.fuelFlow > 0.01 ? fm.fuel / fm.fuelFlow / 60 : 99;
    const R = [
      [`T/W ${tw.toFixed(2)}`, tw >= 1 ? C.w : C.g],
      [`PS  ${ps >= 0 ? '+' : ''}${Math.round(ps)} M/S`, ps >= 0 ? C.g : C.a],
      [`D   ${(fm.drag / 1000).toFixed(0)} KN`, C.g],
      [`M ${fm.mach.toFixed(2)}  ${Math.round(fm.ias * 3.6)} KM/H`, C.g],
      [`AOA ${(fm.alpha / DEG).toFixed(1)}° / ${sp.alphaLimit}°`, fm.alpha / DEG > sp.alphaLimit * 0.8 ? C.a : C.g],
      [`G ${fm.gLoad.toFixed(1)}  (+${this.gHi.toFixed(1)} / ${this.gLo.toFixed(1)})`, fm.gLoad > sp.gMax * 0.85 ? C.a : C.g],
    ];
    R.forEach(([t, c], i) => this.text(g, t, xl, 222 + i * 27, c, 22));
    // fuel
    const fy = H - 112, frac = clamp(fm.fuel / sp.internalFuel, 0, 1), low = fm.fuel < bingo;
    this.box(g, 14, fy - 14, W - 28, 26, C.gd, 2);
    g.fillStyle = low ? C.r : frac < 0.3 ? C.a : C.g; g.fillRect(16, fy - 12, (W - 32) * frac, 22);
    this.text(g, `FUEL ${Math.round(fm.fuel)} KG   ${minutes < 99 ? Math.floor(minutes) + ' PERC' : ''}`, 14, fy + 32, low ? C.r : C.w, 23);
    this.text(g, `BINGO ${Math.round(bingo)}`, W - 14, fy + 32, low ? C.r : C.gd, 21, 'right');
    this.text(g, `TÖMEG ${(mass / 1000).toFixed(1)} T`, W - 14, 26, C.gd, 21, 'right');
  }

  // -------------------------------------------------------------------- RWR
  rwr(g, W, H, ac, world, info, d, mini = false) {
    const cx = W / 2, cy = mini ? H / 2 : H * 0.42, R = mini ? W * 0.44 : W * 0.34;
    this.circle(g, cx, cy, R, C.gd, mini ? 2 : 2.5); this.circle(g, cx, cy, R * 0.5, C.gdd, 2);
    for (let k = 0; k < 12; k++) {
      const a = k * Math.PI / 6;
      this.line(g, cx + Math.sin(a) * R, cy - Math.cos(a) * R, cx + Math.sin(a) * R * 0.9, cy - Math.cos(a) * R * 0.9, C.gd, 2);
    }
    this.poly(g, [[cx, cy - 10], [cx + 8, cy + 8], [cx - 8, cy + 8]], C.g);
    if (!mini) this.text(g, 'RWR  ALR-67', 14, 26, C.g, 26);
    const blink = Math.floor(this.time * 6) % 2 === 0;
    for (const t of ac.rwr.threats) {
      let rad = R * 0.8, col = C.g;
      if (t.level === 'launch') { rad = R * 0.3; col = C.r; if (!blink) continue; } else if (t.level === 'lock') { rad = R * 0.55; col = C.a; }
      const x = cx + Math.sin(t.bearing) * rad, y = cy - Math.cos(t.bearing) * rad;
      this.text(g, t.symbol, x, y, col, mini ? 26 : 34, 'center');
      if (t.level !== 'search') this.circle(g, x, y, mini ? 18 : 26, col, 3);
    }
    if (mini) return;
    const rows = [];
    for (const { missile: m, dist } of ac.rwr.incoming) {
      const closing = dot(sub(m.vel, ac.vel), norm(sub(ac.pos, m.pos))), tti = closing > 1 ? dist / closing : null;
      rows.push([`RAKÉTA ${m.spec.name} ${km(dist)} KM${tti !== null && tti < 60 ? '  ' + tti.toFixed(0) + ' S' : ''}`, C.r]);
    }
    if (!rows.length) rows.push([ac.rwr.threats.length ? `${ac.rwr.threats.length} RADAR FIGYEL` : 'NINCS FENYEGETÉS', ac.rwr.threats.length ? C.a : C.gd]);
    rows.push([`FLARE ${ac.flares}   CHAFF ${ac.chaff}   (X)`, C.g]);
    rows.slice(0, 4).forEach(([t, c], i) => this.text(g, t, 18, H * 0.42 + R + 36 + i * 30, c, 22));
  }
  rwrmini(g, W, H, ac, world, info, d) { this.rwr(g, W, H, ac, world, info, d, true); }

  // ----------------------------------------------- data line (DED / UFCD)
  ded(g, W, H, ac, world, info) {
    const fm = ac.fm, rows = [];
    const toZone = info.zone ? Math.hypot(info.zone.x - ac.pos.x, info.zone.y - ac.pos.y) : 0;
    const toBase = info.base ? Math.hypot(info.base.x - ac.pos.x, info.base.y - ac.pos.y) : 0;
    const where = info.base && toBase < info.base.r ? ['BÁZIS: BIZTONSÁGI ZÓNA', C.c] : info.zone && toZone < info.zone.r ? ['HARCI ZÓNÁBAN', C.r] : null;
    if (info.zone) rows.push([`ZÓNA ${pad3(bearingTo(ac, info.zone))}° ${km(Math.max(0, toZone - info.zone.r)).padStart(4)}  BÁZ ${pad3(bearingTo(ac, info.base))}° ${km(toBase)}`, C.g]);
    const perKm = ac.spec.fuelFlowDry * 0.35 / 0.23, bingo = toBase / 1000 * perKm + ac.spec.internalFuel * 0.08;
    rows.push([`FUEL ${String(Math.round(fm.fuel)).padStart(5)}  BINGO ${Math.round(bingo)}`, fm.fuel < bingo ? C.r : C.g]);
    const w = ac.weaponKeys().map((k) => `${k === 'AIM-9M' ? '9M' : '120'}×${ac.missileCount(k)}`).join(' ');
    rows.push([`${w}  GUN ${ac.gun.ammo}`, C.g]);
    rows.push(where || [`HULLÁM ${info.wave || 0}  BANDITA ${info.enemies || 0}`, C.gd]);
    if (H > W * 0.6) {                // the Hornet's taller UFCD: flight data and fuel endurance too
      const minutes = fm.fuelFlow > 0.01 ? Math.floor(fm.fuel / fm.fuelFlow / 60) : 99;
      rows.splice(1, 0, [`ALT ${Math.round(ac.pos.z)}  M${fm.mach.toFixed(2)}  G${fm.gLoad.toFixed(1)}`, C.w]);
      rows.splice(3, 0, [`IDŐ ${minutes} PERC  FF ${Math.round(fm.fuelFlow * 3600)}`, C.g]);
      rows.push([`FLARE ${ac.flares}  CHAFF ${ac.chaff}`, C.gd]);
    }
    const lh = H / (rows.length + 0.4), fs = Math.min(Math.floor(lh * 0.66), Math.floor(W / 19));
    rows.forEach(([t, c], i) => this.text(g, t, 12, lh * (i + 0.7), c, fs));
  }
}
