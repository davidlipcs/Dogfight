// Tunnel run (Alagútfutam): a closed circuit of gates inside a glass lattice tube with a road on its floor,
// flown for a few laps against the clock (and against a friend over the link, net.js).  The circuit is the same
// everywhere (a fixed shape lifted above the highest ground below it), so lap times can be compared.
//   - the clock starts when the start gate is crossed, a lap is complete at the next crossing of it
//   - leaving the tube (more than TUBE_R from the middle line) doubles the clock while you are outside
import { THREE, V, add, sub, mul, len, norm, dot } from './util.js';
import { Race } from './race.js';

export const GATES = 28, LAPS = 3, TUBE_R = 95, KEY = 'dogfight-tube';
const SAMPLES = 360, SHAPE_R = 1500;

export class TubeRun extends Race {
  // centre: the middle of the circuit (x, y); the gates are hung over it
  constructor(terrain, scene, centre) {
    super(terrain, scene, centre, 0, { rings: GATES, R: 80, key: KEY, record: false });
    this.laps = LAPS; this.limit = null;
    try { const s = JSON.parse(localStorage.getItem(KEY) || '{}'); this.best = s.best || null; this.bestLap = s.lap || null; } catch (e) { this.best = null; this.bestLap = null; }
    this.build(scene);
    this.reset();
  }
  layout(centre) {
    const t = this.terrain, N = SAMPLES;
    const shape = (u) => SHAPE_R * (1 + 0.18 * Math.sin(2 * u + 0.6) + 0.1 * Math.sin(3 * u + 1.9));
    const flat = [];
    let top = 0;
    for (let i = 0; i < N; i++) {
      const u = i / N * Math.PI * 2, r = shape(u), x = centre.x + Math.sin(u) * r, y = centre.y - Math.cos(u) * r;
      flat.push([x, y, u]);
      for (let a = 0; a < 6; a++) top = Math.max(top, t.height(x + Math.cos(a * 1.047) * 120, y + Math.sin(a * 1.047) * 120));
    }
    const base = top + 240;
    this.samples = flat.map(([x, y, u]) => V(x, y, base + 70 * Math.sin(2 * u + 1)));
    this.lapLength = 0;
    for (let i = 0; i < N; i++) this.lapLength += len(sub(this.samples[(i + 1) % N], this.samples[i]));
    const out = [];
    for (let k = 0; k < this.count; k++) {
      const i = Math.floor(k * N / this.count), a = this.samples[(i + N - 1) % N], b = this.samples[(i + 1) % N];
      out.push({ c: this.samples[i].clone(), n: norm(sub(b, a)) });
    }
    return out;
  }
  // where the player starts: a little before the start gate, on the middle line, flying along it
  startPose(back = 550) {
    const N = SAMPLES, step = this.lapLength / N, i = (N - Math.round(back / step)) % N;
    const a = this.samples[i], b = this.samples[(i + 3) % N], d = norm(sub(b, a));
    return { pos: a.clone(), heading: Math.atan2(d.x, d.y) / (Math.PI / 180), dir: d };
  }
  build(scene) {
    const pts = [];
    for (let i = 0; i < SAMPLES; i += 6) pts.push(this.samples[i]);
    const curve = new THREE.CatmullRomCurve3(pts, true, 'catmullrom', 0.5);
    this.tube = new THREE.Group();
    const lattice = new THREE.Mesh(new THREE.TubeGeometry(curve, 240, TUBE_R, 14, true),
      new THREE.MeshBasicMaterial({ color: 0x8fc0e8, wireframe: true, transparent: true, opacity: 0.55, fog: false }));
    lattice.frustumCulled = false;
    this.tube.add(lattice);
    // the road: a dark strip with a dashed middle line along the floor of the tube
    const pos = [], idx = [], dash = [], dIdx = [];
    const N = SAMPLES, floor = TUBE_R * 0.72;
    for (let i = 0; i <= N; i++) {
      const p = this.samples[i % N], q = this.samples[(i + 1) % N], d = norm(sub(q, p));
      const side = norm(V(d.y, -d.x, 0)), c = V(p.x, p.y, p.z - floor);
      for (const [w, arr] of [[48, pos], [1.6, dash]]) arr.push(c.x - side.x * w, c.y - side.y * w, c.z, c.x + side.x * w, c.y + side.y * w, c.z);
    }
    for (let i = 0; i < N; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); if (i % 6 < 3) dIdx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    const strip = (arr, ids, color) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3)); g.setIndex(ids);
      const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide, fog: false }));
      m.frustumCulled = false; return m;
    };
    this.tube.add(strip(pos, idx, 0x2b2f38), strip(dash, dIdx, 0xf2f2f2));
    scene.add(this.tube);
  }
  reset() {
    super.reset();
    this.next = 0; this.penalty = 0; this.outside = false; this.warnT = 0;
    this.lapStart = 0; this.lapTimes = []; this.lastLap = null; this.finalTime = null; this.success = true;
    this.paint();
  }
  get total() { return this.laps * this.count; }
  get lap() { return Math.min(this.laps, Math.floor(this.next / this.count) + 1); }
  get target() { return this.finished ? null : this.rings[this.next % this.count]; }
  get clock() { return this.time + this.penalty; }
  paint() {
    const P = this.rings.length, cur = this.next % P;
    this.rings.forEach((r, i) => {
      r.mesh.visible = true;
      r.mesh.material.color.setHex(i === cur ? 0xffc840 : i === (cur + 1) % P ? 0x6bff85 : i === 0 ? 0xfff2b0 : 0x9fb0bf);
      r.mesh.material.opacity = i === cur ? 0.95 : i === (cur + 1) % P ? 0.7 : i === 0 ? 0.6 : 0.3;
    });
  }
  // distance of a point from the middle line of the tube
  offAxis(p) {
    let best = 1e9;
    for (const s of this.samples) { const d = (s.x - p.x) ** 2 + (s.y - p.y) ** 2 + (s.z - p.z) ** 2; if (d < best) best = d; }
    return Math.sqrt(best);
  }
  // 'ring' | 'lap' | 'finish' | 'out' | null
  update(dt, ac, prev) {
    if (this.finished) return null;
    let ev = null;
    if (this.running) this.time += dt;
    const P = this.count, r = this.rings[this.next % P];
    const s0 = dot(sub(prev, r.c), r.n), s1 = dot(sub(ac.pos, r.c), r.n);
    if (s0 < 0 && s1 >= 0) {
      const hit = add(prev, mul(sub(ac.pos, prev), s0 / (s0 - s1)));
      if (len(sub(hit, r.c)) <= this.R) {
        this.next++; this.running = true; ev = 'ring';
        if (this.next % P === 0) {
          const t = this.clock;
          this.lastLap = t - this.lapStart; this.lapStart = t; this.lapTimes.push(this.lastLap);
          if (!this.bestLap || this.lastLap < this.bestLap) this.bestLap = this.lastLap;
          ev = 'lap';
          if (this.next >= this.total) {
            this.finished = true; this.finalTime = t; this.record = !this.best || t < this.best;
            if (this.record) this.best = t;
            try { localStorage.setItem(KEY, JSON.stringify({ best: this.best, lap: this.bestLap })); } catch (e) { /* private */ }
            this.paint(); return 'finish';
          }
        }
        this.paint();
      }
    }
    if (this.running) {
      const out = this.offAxis(ac.pos) > TUBE_R;
      if (out) { this.penalty += dt; this.warnT -= dt; }
      if (out && !this.outside && this.warnT <= 0) { this.outside = true; this.warnT = 3; if (!ev) ev = 'out'; }
      if (!out) this.outside = false;
    }
    return ev;
  }
  dispose() { super.dispose(); this.scene.remove(this.tube); }
}
