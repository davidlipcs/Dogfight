// Canyon run (Kanyonfutam): a low level strike through the deepest gorge of the map against the clock.
//   - gates hung just above the valley floor, the course follows the lowest ground (worked out from the terrain,
//     so it is always the same on the same map and times can be compared)
//   - the target gate near the end: the bomb falls the moment you fly through it low and fast
//   - then a steep pull-up over the ridge: the last gate hangs above the rim
//   - the whole run must take less than 2:15; flying high (the radar sees you above 350 m) costs 5 s a time
import { THREE, V, add, sub, mul, len, norm } from './util.js';
import { Race } from './race.js';

export const LIMIT = 135, GATES = 30, STEP = 850, FLOOR = 75, KEY = 'dogfight-canyon';

export class CanyonRun extends Race {
  constructor(terrain, scene) {
    super(terrain, scene, V(0, 0, 0), 0, { rings: GATES + 2, R: 60, key: KEY, record: false });
    this.limit = LIMIT; this.penalty = 0; this.exposure = 0;
    try { this.best = JSON.parse(localStorage.getItem(KEY) || '{}').best || null; } catch (e) { this.best = null; }
    // the target on the ground behind its gate
    const g = this.rings[this.targetIdx], tp = add(g.c, mul(g.n, 260));
    this.targetPos = V(tp.x, tp.y, terrain.height(tp.x, tp.y));
    this.targetMesh = new THREE.Group();
    const box = new THREE.Mesh(new THREE.BoxGeometry(22, 16, 8), new THREE.MeshLambertMaterial({ color: 0x5b5d57 }));
    box.position.z = 4; this.targetMesh.add(box);
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 2.5, 300, 10, 1, true).rotateX(Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff3b2a, transparent: true, opacity: 0.35, depthWrite: false, side: THREE.DoubleSide, fog: false }));
    beam.position.z = 150; this.targetMesh.add(beam);
    this.targetMesh.position.copy(this.targetPos);
    scene.add(this.targetMesh);
    this.reset();
  }
  // the course: the deepest gorge, followed along its floor
  layout() {
    const t = this.terrain, g = (x, y) => t.height(x, y), lim = t.half * 0.82;
    const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
    // 1. the deepest gorge: the point with the most relief around it (high walls, low floor, dry land)
    let best = null;
    for (let x = -lim; x <= lim; x += 800) for (let y = -lim; y <= lim; y += 800) {
      const h = g(x, y);
      if (h < 25) continue;
      let top = h;
      for (let a = 0; a < 8; a++) top = Math.max(top, g(x + Math.cos(a * Math.PI / 4) * 2400, y + Math.sin(a * Math.PI / 4) * 2400));
      const score = top - h - Math.max(0, h - 600) * 0.2;
      if (!best || score > best.score) best = { score, x, y, h };
    }
    const follow = (p0, h0, n) => {                                   // valley floor follower
      const out = []; let p = V(p0.x, p0.y, 0), h = h0, cost = 0;
      for (let i = 0; i < n; i++) {
        let pick = null;
        for (let a = -24; a <= 24; a += 4) {
          const hh = h + a * Math.PI / 180, q = V(p.x + Math.sin(hh) * STEP, p.y + Math.cos(hh) * STEP, 0);
          const gq = g(q.x, q.y), gm = g((p.x + q.x) / 2, (p.y + q.y) / 2);
          // the floor: low ground, and walls on both sides (a gorge, not a slope)
          const sx = Math.cos(hh) * 220, sy = -Math.sin(hh) * 220;
          const wall = Math.min(g(q.x + sx, q.y + sy), g(q.x - sx, q.y - sy)) - gq;
          let score = gq + gm * 0.5 + Math.abs(a) * 1.4 - Math.min(wall, 300) * 0.35;
          if (gq < 15) score += 800;
          if (Math.abs(q.x) > lim || Math.abs(q.y) > lim) score += 6000;
          if (!pick || score < pick.score) pick = { score, q, hh, gq };
        }
        cost += pick.gq; out.push(pick); p = pick.q; h = pick.hh;
      }
      return { out, cost };
    };
    // 2. the direction along the gorge that is longest and lowest
    let line = null;
    for (let k = 0; k < 16; k++) {
      const h0 = k * Math.PI / 8, r = follow(best, h0, GATES);
      if (!line || r.cost < line.cost) line = { ...r, h0 };
    }
    // start so that the first gate is about one step ahead of the starting point (which the game places 1800 m back)
    const rings = [];
    let prev = V(best.x, best.y, 0);
    for (const s of line.out) {
      const c = V(s.q.x, s.q.y, s.gq + FLOOR);
      rings.push({ c, n: norm(V(s.q.x - prev.x, s.q.y - prev.y, 0)) });
      prev = s.q;
    }
    // 3. the target gate (a little lower and later in the course, ring GATES-... ) is the last gate; after it the pull-up
    this.targetIdx = rings.length - 1;
    const last = rings[rings.length - 1], fwd = last.n, base = V(last.c.x + fwd.x * 260, last.c.y + fwd.y * 260, 0);
    let climb = null;
    const hBase = Math.atan2(fwd.x, fwd.y), zT = last.c.z;
    for (let a = -70; a <= 70; a += 10) {
      const hh = hBase + a * Math.PI / 180, D = 2600, q = V(base.x + Math.sin(hh) * D, base.y + Math.cos(hh) * D, 0);
      let top = g(q.x, q.y);
      for (let k = 1; k <= 8; k++) top = Math.max(top, g(base.x + (q.x - base.x) * k / 8, base.y + (q.y - base.y) * k / 8));
      const z = top + 170, slope = (z - zT) / D;
      // the ridge that is highest and still a climb a jet can make (about 40 degrees)
      const score = (slope > 0.84 ? 1000 + slope * 100 : 0) - top + Math.abs(a) * 0.8;
      if (!climb || score < climb.score) climb = { score, q, z, hh };
    }
    rings.push({ c: V(climb.q.x, climb.q.y, climb.z), n: norm(V(Math.sin(climb.hh), Math.cos(climb.hh), 0.2)) });
    return rings;
  }
  reset() {
    super.reset();
    this.penalty = 0; this.exposure = 0; this.hit = false; this.warnT = 0;
    if (this.targetMesh) this.targetMesh.visible = true;
  }
  get finalTime() { return this.time + this.penalty; }
  paint() {
    super.paint();
    const t = this.rings[this.targetIdx];
    if (t && this.next <= this.targetIdx) { t.mesh.material.color.setHex(this.next === this.targetIdx ? 0xff3b2a : 0xb0463a); t.mesh.material.opacity = this.next === this.targetIdx ? 0.95 : 0.5; }
    const c = this.rings[this.rings.length - 1];
    if (c && this.next === this.rings.length - 1) { c.mesh.material.color.setHex(0x62d9ff); c.mesh.material.opacity = 0.95; }
  }
  // 'ring' | 'target' | 'finish' | 'miss' | 'radar' | null
  update(dt, ac, prev) {
    const before = this.next, ev = super.update(dt, ac, prev);
    if (this.finished) {
      if (ev !== 'finish') return null;
      this.time += this.penalty;                                       // the radar penalties count
      this.success = this.time <= this.limit;
      this.record = this.success && (!this.best || this.time < this.best);
      if (this.record) { this.best = this.time; try { localStorage.setItem(KEY, JSON.stringify({ best: this.time })); } catch (e) { /* private */ } }
      return 'finish';
    }
    // above 350 m the enemy radar sees you (not on the final climb)
    if (this.running && this.next <= this.targetIdx) {
      const agl = ac.pos.z - this.terrain.height(ac.pos.x, ac.pos.y);
      this.exposure = agl > 350 ? this.exposure + dt : Math.max(0, this.exposure - dt);
      if (this.exposure > 4) { this.exposure = 0; this.penalty += 5; return 'radar'; }
    }
    if (ev === 'ring' && this.next - 1 === this.targetIdx) { this.hit = true; this.targetMesh.visible = false; return 'target'; }
    void before;
    return ev;
  }
  dispose() { super.dispose(); this.scene.remove(this.targetMesh); }
}
void len; void sub;
