// A Nimitz-class aircraft carrier ("USS Dogfight", CVN-80) anchored 15 km south of the home base.  Its flight
// deck is part of the ground: Terrain.height() returns the deck height over it, so landing, taxiing and
// taking off work with the normal flight model.  Plus what only a carrier has:
//   * an angled landing deck with four arresting wires: touch down in the wire zone and the hook stops you
//     in about two seconds (a trap); miss them and it is a bolter - full power, go around
//   * two bow catapults: stop at the catapult, full throttle, and the shuttle throws you off the bow
//   * the optical landing system ("meatball"): the HUD shows whether you are high, low or on the glide slope
// Real numbers: 333 m long, 77 m wide flight deck, 9 degree angled deck, deck ~19 m above the sea.
import { THREE, V } from './util.js';

export const DECK_Z = 19.5;
const ANGLE = -9 * Math.PI / 180;                // the landing deck points 9 degrees to port of the bow
// deck outline in the carrier's frame (x starboard, y bow), metres
const OUTLINE = [[22, 166], [24, 40], [24, -150], [12, -166], [-26, -166], [-47, 34], [-47, 70], [-30, 96], [-18, 166]];
const WIRES = [52, 64, 76, 88];                    // distance of the wires from the stern, along the landing line
const CATS = [[9, 30, 160], [-9, 30, 160]];         // [x, start y, end y]

const inside = (x, y) => {
  let c = false;
  for (let i = 0, j = OUTLINE.length - 1; i < OUTLINE.length; j = i++) {
    const [xi, yi] = OUTLINE[i], [xj, yj] = OUTLINE[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
};

export class Carrier {
  constructor(terrain, x = 21000, y = -42000, heading = 0) {
    this.terrain = terrain; this.x = x; this.y = y; this.heading = heading;
    this.cos = Math.cos(heading * Math.PI / 180); this.sin = Math.sin(heading * Math.PI / 180);
    // landing line: from the stern on the port side, 9 degrees off the bow
    this.landStart = [-8, -166]; this.landDir = [Math.sin(ANGLE), Math.cos(ANGLE)];
    // the deck becomes ground: wrap the terrain's height and the airfield's "paved" test
    const h0 = terrain.height.bind(terrain), af = terrain.airfield, p0 = af.onPaved.bind(af);
    terrain.height = (px, py) => (this.onDeck(px, py) ? DECK_Z : h0(px, py));
    af.onPaved = (px, py) => this.onDeck(px, py) || p0(px, py);
    terrain.isWater = (px, py) => !this.onDeck(px, py) && terrain.rawHeight(px, py) < 0;
    terrain.carrier = this;
  }
  // world -> carrier frame
  local(px, py) {
    const dx = px - this.x, dy = py - this.y;
    return [dx * this.cos - dy * this.sin, dx * this.sin + dy * this.cos];
  }
  world(lx, ly, z = DECK_Z) { return V(this.x + lx * this.cos + ly * this.sin, this.y - lx * this.sin + ly * this.cos, z); }
  // a new map: anchor somewhere else (null: no sea on this map - no carrier)
  moveTo(p) {
    this.active = !!p;
    if (p) { this.x = p.x; this.y = p.y; }
    if (this.group) { this.group.visible = this.active; this.group.position.set(this.x, this.y, 0); }
  }
  onDeck(px, py) {
    if (this.active === false) return false;
    if (Math.abs(px - this.x) > 200 || Math.abs(py - this.y) > 200) return false;
    const [lx, ly] = this.local(px, py);
    return inside(lx, ly);
  }
  // how far along the landing line from the stern, and how far off it (m)
  landing(px, py) {
    const [lx, ly] = this.local(px, py), [sx, sy] = this.landStart, [dx, dy] = this.landDir;
    const rx = lx - sx, ry = ly - sy;
    return { along: rx * dx + ry * dy, off: rx * dy - ry * dx };
  }
  get headingDeg() { return this.heading; }
  get landingHeading() { return this.heading + ANGLE * 180 / Math.PI; }
  // a point on the glide slope (3.5 degrees) behind the stern, for approaches and the meatball
  glide(px, py, pz) {
    const l = this.landing(px, py), target = 60;                 // aim at the third wire
    const dist = target - l.along;
    const want = DECK_Z + Math.tan(3.5 * Math.PI / 180) * dist;
    return { dist, off: l.off, high: pz - 2 - want, behind: dist > 0 };
  }
  // a parking / catapult spot in the world: [x, y, heading]
  catapult(k = 0) { const [cx, y0] = CATS[k]; const p = this.world(cx, y0); return [p.x, p.y, this.heading]; }
  onCatapult(px, py) {
    const [lx, ly] = this.local(px, py);
    return CATS.some(([cx, y0, y1]) => Math.abs(lx - cx) < 6 && ly > y0 - 8 && ly < y1);
  }
  inWires(px, py) {
    const l = this.landing(px, py);
    return Math.abs(l.off) < 14 && l.along > WIRES[0] - 14 && l.along < WIRES[3] + 10;
  }
  wireNumber(px, py) {
    const l = this.landing(px, py);
    let best = 1, bd = 1e9;
    WIRES.forEach((w, i) => { const d = Math.abs(l.along - w); if (d < bd) { bd = d; best = i + 1; } });
    return best;
  }

  // ------------------------------------------------------------------ model
  build(models) {
    const g = new THREE.Group();
    g.position.set(this.x, this.y, 0);
    g.rotation.z = -this.heading * Math.PI / 180;
    const grey = new THREE.MeshStandardMaterial({ color: 0x7c848c, roughness: 0.75, metalness: 0.15 });
    const dark = new THREE.MeshStandardMaterial({ color: 0x3b4046, roughness: 0.8 });
    const red = new THREE.MeshStandardMaterial({ color: 0x6a2a24, roughness: 0.8 });
    // hull: sections from the bow to the stern, the deck flares out over it
    const shape = (w, z0, z1) => {
      const s = new THREE.Shape();
      s.moveTo(-w * 0.82, z0); s.lineTo(w * 0.82, z0); s.lineTo(w, z1); s.lineTo(-w, z1); s.closePath();
      return s;
    };
    const hull = new THREE.Group();
    const secs = [[166, 2], [150, 12], [120, 18], [60, 20.5], [-100, 20.5], [-150, 19], [-162, 17]];
    for (let i = 0; i < secs.length - 1; i++) {
      const [y0, w0] = secs[i], [y1, w1] = secs[i + 1], len = y0 - y1;
      // the section (x across, height up) extruded along +Z, then turned so it runs from y0 towards the stern
      const geo = new THREE.ExtrudeGeometry(shape((w0 + w1) / 2, -6, DECK_Z - 1.2), { depth: len, bevelEnabled: false });
      geo.rotateX(Math.PI / 2); geo.translate(0, y0, 0);
      hull.add(new THREE.Mesh(geo, grey));
    }
    g.add(hull);
    // the red boot topping at the waterline
    const boot = new THREE.Mesh(new THREE.BoxGeometry(38, 300, 2.2), red); boot.position.set(0, 0, 0.4); g.add(boot);
    // flight deck: the outline as one slab with a painted top
    const ds = new THREE.Shape(OUTLINE.map(([x, y]) => new THREE.Vector2(x, y)));
    const deckGeo = new THREE.ExtrudeGeometry(ds, { depth: 1.2, bevelEnabled: false });
    deckGeo.translate(0, 0, DECK_Z - 1.2);
    const uv = deckGeo.attributes.uv, pos = deckGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) uv.setXY(i, (pos.getX(i) + 50) / 80, (pos.getY(i) + 170) / 340);
    g.add(new THREE.Mesh(deckGeo, [new THREE.MeshStandardMaterial({ map: this.deckTexture(), roughness: 0.9 }), dark]));
    // the island: superstructure on the starboard side, with the bridge windows, masts and radars
    const island = new THREE.Group(); island.position.set(19, 0, DECK_Z);
    const block = (w, l, h, x, y, z, mat = grey) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, l, h), mat); b.position.set(x, y, z + h / 2); island.add(b); return b; };
    block(9, 34, 14, 0, 6, 0); block(8, 26, 6, -0.3, 8, 14); block(7, 18, 5, -0.5, 9, 20);
    block(8.2, 26.2, 1.4, -0.3, 8, 17.5, new THREE.MeshBasicMaterial({ color: 0x0d1418 }));       // bridge windows
    const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.8, 16, 8), grey); mast.rotation.x = Math.PI / 2; mast.position.set(0, 10, 33); island.add(mast);
    const radar = new THREE.Mesh(new THREE.BoxGeometry(7, 0.4, 2.2), dark); radar.position.set(0, 10, 39); island.add(radar);
    this.radar = radar;
    const dish = new THREE.Mesh(new THREE.SphereGeometry(1.6, 12, 8), new THREE.MeshStandardMaterial({ color: 0xe8e8e8 })); dish.position.set(-2.5, 14, 28); island.add(dish);
    const num = new THREE.Mesh(new THREE.PlaneGeometry(6, 5), new THREE.MeshBasicMaterial({ map: this.numberTexture(), transparent: true }));
    num.rotation.x = Math.PI / 2; num.rotation.y = -Math.PI / 2; num.position.set(-4.55, 2, 10); island.add(num);
    g.add(island);
    // hull number on the bow, both sides
    for (const s of [1, -1]) {
      const n = new THREE.Mesh(new THREE.PlaneGeometry(14, 8), new THREE.MeshBasicMaterial({ map: this.numberTexture(), transparent: true }));
      n.rotation.x = Math.PI / 2; n.rotation.y = s * Math.PI / 2 * -1; n.position.set(s * 13.2, 135, 11); g.add(n);
    }
    // the optical landing system on the port side: a light bar with the amber "meatball"
    const lens = new THREE.Group(); lens.position.set(-34, -55, DECK_Z + 2);
    lens.add(new THREE.Mesh(new THREE.BoxGeometry(0.6, 8, 0.6), dark));
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.5, 10, 8), new THREE.MeshBasicMaterial({ color: 0xffb030 }));
    lens.add(ball);
    for (const s of [-1, 1]) { const d = new THREE.Mesh(new THREE.BoxGeometry(0.4, 4, 0.4), new THREE.MeshBasicMaterial({ color: 0x40ff60 })); d.position.set(0, s * 5, 0); lens.add(d); }
    g.add(lens);
    // parked Super Hornets along the starboard side and the bow
    if (models && models.aircraft) {
      this.parked = new THREE.Group(); g.add(this.parked);
      for (const [x, y, h] of [[16, -62, 200], [16, -86, 200], [15, 80, 230]]) {
        const a = models.aircraft('fa18'); a.position.set(x, y, DECK_Z + (models.types.fa18 ? models.types.fa18.gearHeight : 2.4));
        a.rotation.z = (h * Math.PI) / 180; this.parked.add(a);
      }
    }
    // foam around the bow and a wake behind the stern
    const foam = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35, depthWrite: false });
    const wake = new THREE.Mesh(new THREE.PlaneGeometry(40, 600), foam); wake.position.set(0, -470, 0.3); g.add(wake);
    const bow = new THREE.Mesh(new THREE.RingGeometry(12, 24, 24, 1, -0.6, 1.2 + Math.PI), foam); bow.position.set(0, 160, 0.3); g.add(bow);
    this.group = g; if (this.active === false) g.visible = false;
    g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    return g;
  }
  deckTexture() {
    const W = 512, H = 2176, c = document.createElement('canvas'); c.width = W; c.height = H;
    const x = c.getContext('2d');
    const px = (m) => ((m + 50) / 80) * W, py = (m) => H - ((m + 170) / 340) * H;     // deck metres -> pixels
    x.fillStyle = '#41464c'; x.fillRect(0, 0, W, H);
    for (let k = 0; k < 9000; k++) { x.fillStyle = `rgba(${Math.random() < 0.5 ? '20,22,24' : '90,95,100'},${Math.random() * 0.18})`; x.fillRect(Math.random() * W, Math.random() * H, 2, 3 + Math.random() * 10); }
    const line = (pts, col, w, dash) => { x.strokeStyle = col; x.lineWidth = w; x.setLineDash(dash || []); x.beginPath(); pts.forEach(([a, b], i) => (i ? x.lineTo(px(a), py(b)) : x.moveTo(px(a), py(b)))); x.stroke(); x.setLineDash([]); };
    // landing area: centre line (dashed white), the edges (white and the red/white "foul" line)
    const [sx, sy] = this.landStart, [dx, dy] = this.landDir, L = 240, at = (a, o) => [sx + dx * a + dy * o, sy + dy * a - dx * o];
    line([at(0, 0), at(L, 0)], '#f2f2f2', 5, [26, 18]);
    line([at(0, -14), at(L, -14)], '#f2f2f2', 3); line([at(0, 14), at(L, 14)], '#e8d23c', 3);
    for (const wr of WIRES) line([at(wr, -12), at(wr, 12)], '#b9b9b9', 4);
    // catapult tracks and their jet blast deflectors
    for (const [cx, y0, y1] of CATS) {
      line([[cx, y0], [cx, y1]], '#202326', 6); line([[cx - 1.5, y0], [cx - 1.5, y1]], '#e8d23c', 1.5);
      line([[cx - 6, y0 - 12], [cx + 6, y0 - 12]], '#8a2a22', 8);
    }
    // bow number and the elevator outlines
    x.save(); x.translate(px(-2), py(130)); x.rotate(Math.PI); x.fillStyle = '#e8e8e8'; x.font = 'bold 120px Arial'; x.textAlign = 'center'; x.fillText('80', 0, 40); x.restore();
    for (const [a, b] of [[24, -10], [24, -60], [-38, -20]]) { x.strokeStyle = '#d9c23a'; x.lineWidth = 2; x.strokeRect(px(a - 8), py(b + 10), px(8) - px(0), py(0) - py(20)); }
    const t = new THREE.CanvasTexture(c);
    t.encoding = THREE.sRGBEncoding; t.anisotropy = 8;
    return t;
  }
  numberTexture() {
    if (this.numTex) return this.numTex;
    const c = document.createElement('canvas'); c.width = 256; c.height = 160;
    const x = c.getContext('2d');
    x.fillStyle = '#f0f0f0'; x.font = 'bold 130px Arial'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('80', 128, 84);
    this.numTex = new THREE.CanvasTexture(c); this.numTex.encoding = THREE.sRGBEncoding;
    return this.numTex;
  }
  update(dt) { if (this.radar) this.radar.rotation.z += dt * 2.2; }
}
