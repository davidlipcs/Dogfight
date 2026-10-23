// Ring race (Gyűrűverseny): a course of rings laid along the valleys of the island, flown against the
// clock.  The course is worked out from the terrain itself (always the same, so times can be compared):
// from the start it steps on ring by ring, each time choosing the lowest ground ahead within ±45°, away
// from the sea and the edge of the map, and hangs the ring a little above the highest ground on the way.
import { THREE, V, add, sub, mul, dot, len, norm } from './util.js';

const RINGS = 18, STEP = 1600, R = 55, KEY = 'dogfight-race';

export class Race {
  constructor(terrain, scene, start, heading) {
    this.terrain = terrain; this.scene = scene;
    this.rings = this.layout(start, heading);
    this.group = new THREE.Group();
    const geo = new THREE.TorusGeometry(R, 5, 10, 48);
    for (const r of this.rings) {
      const mat = new THREE.MeshBasicMaterial({ color: 0xffc840, transparent: true, opacity: 0.9, fog: false });
      const m = new THREE.Mesh(geo, mat);
      m.position.copy(r.c);
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), r.n);
      r.mesh = m; this.group.add(m);
    }
    scene.add(this.group);
    try { this.best = JSON.parse(localStorage.getItem(KEY) || '{}').best || null; } catch (e) { this.best = null; }
    this.reset();
  }
  layout(start, heading) {
    const t = this.terrain, lim = t.half * 0.8, out = [];
    let p = V(start.x, start.y, 0), h = heading;
    const ground = (x, y) => t.height(x, y);
    const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
    const goal = V(-12000, 9000, 0);                              // the wooded hills west of the middle
    for (let i = 0; i < RINGS; i++) {
      let best = null;
      const want = 28 * Math.sin(i * 0.9) * Math.PI / 180;       // weave left and right
      const toGoal = Math.atan2(goal.x - p.x, goal.y - p.y);
      for (let a = -50; a <= 50; a += 10) {
        const hh = h + a * Math.PI / 180, q = V(p.x + Math.sin(hh) * STEP, p.y + Math.cos(hh) * STEP, 0);
        const g = ground(q.x, q.y), gm = ground((p.x + q.x) / 2, (p.y + q.y) / 2);
        let score = (g + gm * 0.6) * 0.5 + Math.abs(a * Math.PI / 180 - want) * 260 + Math.abs(wrap(hh - toGoal)) * 220;
        if (g < 15) score += 900;                                   // not over the sea
        if (Math.abs(q.x) > lim || Math.abs(q.y) > lim) score += 5000;
        if (!best || score < best.score) best = { score, q, hh };
      }
      let top = 0;
      for (let k = 0; k <= 6; k++) top = Math.max(top, ground(p.x + (best.q.x - p.x) * k / 6, p.y + (best.q.y - p.y) * k / 6));
      const c = V(best.q.x, best.q.y, Math.max(top + 140, ground(best.q.x, best.q.y) + 110, 180));
      out.push({ c, n: norm(V(best.q.x - p.x, best.q.y - p.y, 0)) });
      p = best.q; h = best.hh;
    }
    return out;
  }
  reset() {
    this.next = 0; this.time = 0; this.running = false; this.finished = false; this.missTime = -9;
    this.paint();
  }
  paint() {
    this.rings.forEach((r, i) => {
      r.mesh.visible = i >= this.next;
      r.mesh.material.color.setHex(i === this.next ? 0xffc840 : i === this.next + 1 ? 0x6bff85 : 0x9fb0bf);
      r.mesh.material.opacity = i === this.next ? 0.95 : i === this.next + 1 ? 0.7 : 0.35;
    });
  }
  // returns 'ring' | 'finish' | 'miss' | null
  update(dt, ac, prev) {
    if (this.finished) return null;
    if (this.running) this.time += dt;
    const r = this.rings[this.next];
    const s0 = dot(sub(prev, r.c), r.n), s1 = dot(sub(ac.pos, r.c), r.n);
    if (s0 < 0 && s1 >= 0) {
      const hit = add(prev, mul(sub(ac.pos, prev), s0 / (s0 - s1))), off = len(sub(hit, r.c));
      if (off <= R) {
        this.next++; this.running = true;
        if (this.next >= this.rings.length) {
          this.finished = true; this.record = !this.best || this.time < this.best;
          if (this.record) { this.best = this.time; try { localStorage.setItem(KEY, JSON.stringify({ best: this.time })); } catch (e) { /* private */ } }
          this.paint(); return 'finish';
        }
        this.paint(); return 'ring';
      }
      if (off < R * 2.5) return 'miss';
    }
    return null;
  }
  get target() { return this.finished ? null : this.rings[this.next]; }
  dispose() { this.scene.remove(this.group); }
}
export const fmtTime = (s) => (s === null || s === undefined ? '--' : `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, '0')}`);
export const RACE_RINGS = RINGS;
