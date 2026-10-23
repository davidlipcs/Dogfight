// The world map of the main menu: where to fight.  A slippy map (drag, wheel / pinch zoom, click to pick) on
// satellite tiles - or, where those cannot be loaded, on a relief map coloured from the elevation tiles - with a
// place search (OpenStreetMap Nominatim) and a list of ready places.  The 102 km square that will be built is
// drawn around the picked point.
import { PLACES, ATTRIBUTION, lonToX, latToY, xToLon, yToLat, loadImage } from './world.js';
import { clamp } from './util.js';

const $ = (id) => document.getElementById(id);
const IMAGERY = (z, x, y) => `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`;
const ELEV = (z, x, y) => `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/${z}/${x}/${y}.png`;
const tiles = () => ({ imagery: IMAGERY, elev: ELEV, ...(window.DOGFIGHT_TILES || {}) });
const SIZE_KM = 102.4;

// relief colours for the elevation tiles (sea depths blue, land green - brown - white)
function relief(img) {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d', { willReadFrequently: true });
  g.drawImage(img, 0, 0);
  const id = g.getImageData(0, 0, 256, 256), d = id.data;
  const h = (i) => d[i] * 256 + d[i + 1] + d[i + 2] / 256 - 32768;
  for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) {
    const i = (y * 256 + x) * 4, e = h(i);
    const ex = h(((y * 256) + Math.min(255, x + 1)) * 4), ey = h((Math.min(255, y + 1) * 256 + x) * 4);
    let r, gg, b;
    if (e <= 0) { const k = clamp(-e / 5000, 0, 1); r = 40 - 25 * k; gg = 92 - 50 * k; b = 140 - 50 * k; }
    else {
      const k = clamp(e / 4500, 0, 1);
      r = 90 + 120 * k; gg = 130 + 40 * k - 60 * k * k; b = 70 + 60 * k;
      if (e > 3500) { r = gg = b = 235; }
      const sh = clamp(1 + (e - ex - (e - ey)) * 0.004, 0.65, 1.35);
      r *= sh; gg *= sh; b *= sh;
    }
    d[i] = r; d[i + 1] = gg; d[i + 2] = b; d[i + 3] = 255;
  }
  g.putImageData(id, 0, 0);
  return c;
}

export class MapPicker {
  constructor() {
    this.canvas = $('mp-map'); this.g = this.canvas.getContext('2d');
    this.cache = new Map(); this.useImagery = true; this.imageryFails = 0;
    this.z = 3; this.cx = lonToX(19, 3); this.cy = latToY(47.5, 3);
    this.sel = null; this.onPick = null;
    const c = this.canvas;
    let drag = null, pinch = null;
    const pts = new Map();
    c.addEventListener('pointerdown', (e) => {
      pts.set(e.pointerId, [e.offsetX, e.offsetY]);
      try { c.setPointerCapture(e.pointerId); } catch (err) { /* synthetic pointer */ }
      if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), z: this.z }; drag = null; }
      else drag = { x: e.offsetX, y: e.offsetY, cx: this.cx, cy: this.cy, moved: false };
    });
    c.addEventListener('pointermove', (e) => {
      if (!pts.has(e.pointerId)) return;
      pts.set(e.pointerId, [e.offsetX, e.offsetY]);
      if (pinch && pts.size === 2) {
        const [a, b] = [...pts.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
        const want = clamp(Math.round(pinch.z + Math.log2(d / pinch.d)), 2, 13);
        if (want !== this.z) this.zoomAt(want, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2);
        return;
      }
      if (!drag) return;
      const dx = e.offsetX - drag.x, dy = e.offsetY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
      this.cx = drag.cx - dx / 256; this.cy = clamp(drag.cy - dy / 256, 0, 2 ** this.z);
      this.draw();
    });
    const up = (e) => {
      pts.delete(e.pointerId);
      if (pinch) { if (pts.size < 2) pinch = null; drag = null; return; }
      if (drag && !drag.moved) this.pickAt(e.offsetX, e.offsetY);
      drag = null;
    };
    c.addEventListener('pointerup', up); c.addEventListener('pointercancel', up);
    c.addEventListener('wheel', (e) => { e.preventDefault(); this.zoomAt(clamp(this.z + (e.deltaY < 0 ? 1 : -1), 2, 13), e.offsetX, e.offsetY); }, { passive: false });
    $('mp-zin').addEventListener('click', () => this.zoomAt(Math.min(13, this.z + 1), c.width / 2, c.height / 2));
    $('mp-zout').addEventListener('click', () => this.zoomAt(Math.max(2, this.z - 1), c.width / 2, c.height / 2));
    $('mp-places').innerHTML = PLACES.map((p) => `<button type="button" class="small" data-place="${p.id}">${p.name}</button>`).join('');
    for (const b of $('mp-places').querySelectorAll('button')) {
      b.onclick = () => { const p = PLACES.find((q) => q.id === b.dataset.place); this.select(p); if (p.lat !== null) this.centre(p.lat, p.lon, 8); };
    }
    $('mp-search').addEventListener('submit', (e) => { e.preventDefault(); this.search($('mp-q').value); });
    $('mp-cancel').addEventListener('click', () => this.close());
    $('mp-ok').addEventListener('click', () => { if (this.sel && this.onPick) this.onPick(this.sel); this.close(); });
    $('mp-attr').textContent = ATTRIBUTION + ' · Keresés: © OpenStreetMap';
    addEventListener('resize', () => { if (!$('mappick').hidden) this.fit(); });
  }
  open(current, onPick) {
    this.onPick = onPick;
    $('mappick').hidden = false;
    this.fit();
    this.select(current || PLACES[0]);
    if (current && current.lat !== null && current.lat !== undefined) this.centre(current.lat, current.lon, 7);
    else this.centre(30, 10, 2);
  }
  close() { $('mappick').hidden = true; }
  fit() {
    const r = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = Math.max(200, Math.floor(r.width)); this.canvas.height = Math.max(200, Math.floor(r.height));
    this.draw();
  }
  centre(lat, lon, z) { this.z = z; this.cx = lonToX(lon, z); this.cy = latToY(lat, z); this.draw(); }
  zoomAt(z, sx, sy) {
    const W = this.canvas.width, H = this.canvas.height;
    const tx = this.cx + (sx - W / 2) / 256, ty = this.cy + (sy - H / 2) / 256, k = 2 ** (z - this.z);
    this.cx = tx * k - (sx - W / 2) / 256; this.cy = ty * k - (sy - H / 2) / 256; this.z = z;
    this.draw();
  }
  pickAt(sx, sy) {
    const W = this.canvas.width, H = this.canvas.height;
    const tx = this.cx + (sx - W / 2) / 256, ty = this.cy + (sy - H / 2) / 256;
    const lat = clamp(yToLat(ty, this.z), -80, 80), lon = ((xToLon(tx, this.z) + 540) % 360) - 180;
    this.select({ id: 'pick', name: `${Math.abs(lat).toFixed(2)}° ${lat >= 0 ? 'É' : 'D'}, ${Math.abs(lon).toFixed(2)}° ${lon >= 0 ? 'K' : 'Ny'}`, lat, lon });
    this.reverse(lat, lon);
  }
  select(p) {
    this.sel = p;
    $('mp-sel').textContent = p.lat === null ? `Kiválasztva: ${p.name}` : `Kiválasztva: ${p.name} (102 × 102 km)`;
    this.draw();
  }
  async reverse(lat, lon) {
    try {
      const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&zoom=10&accept-language=hu&lat=${lat}&lon=${lon}`);
      const j = await r.json();
      if (this.sel && this.sel.lat === lat && j.display_name) this.select({ ...this.sel, name: j.display_name.split(',').slice(0, 2).join(',') });
    } catch (e) { /* offline: the coordinates stay as the name */ }
  }
  async search(q) {
    if (!q.trim()) return;
    $('mp-results').textContent = 'Keresés…';
    try {
      const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=6&accept-language=hu&q=${encodeURIComponent(q)}`);
      const list = await r.json();
      if (!list.length) { $('mp-results').textContent = 'Nincs találat.'; return; }
      $('mp-results').innerHTML = list.map((p, i) => `<button type="button" class="small" data-i="${i}">${p.display_name.split(',').slice(0, 3).join(',')}</button>`).join('');
      for (const b of $('mp-results').querySelectorAll('button')) {
        b.onclick = () => {
          const p = list[Number(b.dataset.i)], lat = Number(p.lat), lon = Number(p.lon);
          this.select({ id: 'search', name: p.display_name.split(',').slice(0, 2).join(','), lat, lon });
          this.centre(lat, lon, 8);
        };
      }
    } catch (e) { $('mp-results').textContent = 'A kereséshez internet kell – kattints a térképre vagy válassz a listából.'; }
  }
  tile(z, x, y) {
    const n = 2 ** z, wx = ((x % n) + n) % n, key = `${z}/${wx}/${y}`;
    const c = this.cache.get(key);
    if (c !== undefined) return c;
    this.cache.set(key, null);
    const done = (img) => { this.cache.set(key, img); this.draw(); };
    const fallback = () => loadImage(tiles().elev(z, wx, y)).then((img) => done(relief(img))).catch(() => { /* no tile */ });
    if (this.useImagery) {
      loadImage(tiles().imagery(z, wx, y)).then(done).catch(() => { if (++this.imageryFails > 3) this.useImagery = false; fallback(); });
    } else fallback();
    return null;
  }
  draw() {
    if ($('mappick').hidden) return;
    const g = this.g, W = this.canvas.width, H = this.canvas.height, z = this.z, n = 2 ** z;
    g.fillStyle = '#1c3550'; g.fillRect(0, 0, W, H);
    const x0 = Math.floor(this.cx - W / 512), x1 = Math.floor(this.cx + W / 512), y0 = Math.max(0, Math.floor(this.cy - H / 512)), y1 = Math.min(n - 1, Math.floor(this.cy + H / 512));
    for (let ty = y0; ty <= y1; ty++) for (let tx = x0; tx <= x1; tx++) {
      const sx = Math.round(W / 2 + (tx - this.cx) * 256), sy = Math.round(H / 2 + (ty - this.cy) * 256);
      const img = this.tile(z, tx, ty);
      if (img) g.drawImage(img, sx, sy, 256, 256);
      else {                                            // a coarser tile, stretched, while this one loads
        for (let up = 1; up <= 4 && z - up >= 0; up++) {
          const k = 2 ** up, px = Math.floor(tx / k), py = Math.floor(ty / k), parent = this.cache.get(`${z - up}/${((px % (n / k)) + n / k) % (n / k)}/${py}`);
          if (parent) { const s = 256 / k; g.drawImage(parent, (tx - px * k) * s, (ty - py * k) * s, s, s, sx, sy, 256, 256); break; }
        }
      }
    }
    const p = this.sel;
    if (p && p.lat !== null && p.lat !== undefined) {
      const px = W / 2 + (lonToX(p.lon, z) - this.cx) * 256, py = H / 2 + (latToY(p.lat, z) - this.cy) * 256;
      const mPerPx = 40075016 * Math.cos(p.lat * Math.PI / 180) / (256 * n), side = SIZE_KM * 1000 / mPerPx;
      g.strokeStyle = '#ffc840'; g.lineWidth = 2; g.setLineDash([8, 6]);
      g.strokeRect(px - side / 2, py - side / 2, side, side); g.setLineDash([]);
      g.fillStyle = '#ffc840'; g.beginPath(); g.arc(px, py, 6, 0, Math.PI * 2); g.fill();
      g.strokeStyle = '#000'; g.lineWidth = 1.5; g.stroke();
    }
    g.fillStyle = 'rgba(0,0,0,0.55)'; g.fillRect(0, H - 22, W, 22);
    g.fillStyle = '#dfe8ef'; g.font = '12px system-ui, sans-serif';
    g.fillText('Húzd a térképet, görgővel nagyíts, kattints oda, ahol harcolni akarsz.', 8, H - 7);
  }
}
