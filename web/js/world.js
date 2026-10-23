// The real world: a 102 km x 102 km piece of the Earth anywhere you pick, built while the game runs.
//  * elevation: AWS Terrain Tiles (Mapzen "terrarium" PNG tiles, free, world wide, with sea floor depths)
//  * colour: satellite imagery (Esri World Imagery tiles); where a tile cannot be loaded the ground is painted
//    from the height and the slope (sea, beach, grass, forest, rock, snow)
// The result has the same form as assets/terrain.json (a height grid + the air base), so flying, landing, the AI
// and the weapons work on it unchanged.  The air base goes on the flattest ground near the middle (levelled),
// the carrier on open sea nearby if there is any.
import { clamp } from './util.js';

export const PLACES = [
  { id: 'island', name: 'Az eredeti sziget', lat: null, lon: null },
  { id: 'budapest', name: 'Budapest és a Duna-kanyar', lat: 47.55, lon: 19.05 },
  { id: 'balaton', name: 'Balaton', lat: 46.85, lon: 17.75 },
  { id: 'tatra', name: 'Magas-Tátra', lat: 49.17, lon: 20.13 },
  { id: 'alps', name: 'Alpok – Mont Blanc', lat: 45.85, lon: 6.85 },
  { id: 'fjord', name: 'Norvég fjordok', lat: 61.2, lon: 6.9 },
  { id: 'gibraltar', name: 'Gibraltári-szoros', lat: 36.05, lon: -5.5 },
  { id: 'grandcanyon', name: 'Grand Canyon', lat: 36.1, lon: -112.15 },
  { id: 'sanfrancisco', name: 'San Francisco-öböl', lat: 37.75, lon: -122.35 },
  { id: 'hawaii', name: 'Hawaii – Oahu', lat: 21.45, lon: -157.95 },
  { id: 'fuji', name: 'Fuji és Tokiói-öböl', lat: 35.4, lon: 138.9 },
  { id: 'everest', name: 'Himalája – Mount Everest', lat: 27.95, lon: 86.9 },
  { id: 'dubai', name: 'Dubaj és a sivatag', lat: 25.15, lon: 55.25 },
  { id: 'iceland', name: 'Izland – vulkánok', lat: 63.95, lon: -19.4 },
  { id: 'rio', name: 'Rio de Janeiro', lat: -22.95, lon: -43.2 },
];

const ELEV = (z, x, y) => `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/${z}/${x}/${y}.png`;
const IMAGERY = (z, x, y) => `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`;
// tests (and anyone who wants another provider) can replace the URLs: window.DOGFIGHT_TILES = { elev, imagery }
const urls = () => ({ elev: ELEV, imagery: IMAGERY, ...(window.DOGFIGHT_TILES || {}) });
export const ATTRIBUTION = 'Domborzat: Mapzen / AWS Terrain Tiles · Műhold: Esri World Imagery (Maxar, Earthstar Geographics)';

const R = 6378137, M_LAT = 110574, M_LON = 111320;
export const lonToX = (lon, z) => (lon + 180) / 360 * 2 ** z;
export const latToY = (lat, z) => { const s = Math.sin(lat * Math.PI / 180); return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * 2 ** z; };
export const xToLon = (x, z) => x / 2 ** z * 360 - 180;
export const yToLat = (y, z) => { const n = Math.PI - 2 * Math.PI * y / 2 ** z; return 180 / Math.PI * Math.atan(Math.sinh(n)); };
// metres per pixel of a 256 px tile at zoom z
const mpp = (lat, z) => 2 * Math.PI * R * Math.cos(lat * Math.PI / 180) / (256 * 2 ** z);

export function loadImage(url, timeout = 20000) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    const t = setTimeout(() => { img.src = ''; reject(new Error('timeout ' + url)); }, timeout);
    img.onload = () => { clearTimeout(t); resolve(img); };
    img.onerror = () => { clearTimeout(t); reject(new Error('load ' + url)); };
    img.src = url;
  });
}

// run async jobs n at a time
async function pool(jobs, n, onDone) {
  let next = 0, done = 0;
  const worker = async () => {
    while (next < jobs.length) {
      const k = next++;
      try { await jobs[k](); } catch (e) { /* a missing tile: handled by the caller */ }
      done++; if (onDone) onDone(done, jobs.length);
    }
  };
  await Promise.all(Array.from({ length: Math.min(n, jobs.length) }, worker));
}

// the terrarium encoding: height = R * 256 + G + B / 256 - 32768 (metres)
function decodeElevation(img) {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d', { willReadFrequently: true });
  g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, 256, 256).data, out = new Float32Array(256 * 256);
  for (let i = 0; i < out.length; i++) out[i] = d[i * 4] * 256 + d[i * 4 + 1] + d[i * 4 + 2] / 256 - 32768;
  return out;
}

// local metres (x east, y north) <-> latitude / longitude around the centre
export function geoFrame(lat0, lon0) {
  const kx = M_LON * Math.cos(lat0 * Math.PI / 180);
  return {
    lat0, lon0,
    toGeo: (x, y) => [lat0 + y / M_LAT, lon0 + x / kx],
    toLocal: (lat, lon) => [(lon - lon0) * kx, (lat - lat0) * M_LAT],
  };
}

// --------------------------------------------------------------------- the height grid
async function elevationGrid(frame, size, res, onProgress) {
  const half = size / 2, n = res + 1, cell = size / res;
  const z = clamp(Math.ceil(Math.log2(2 * Math.PI * R * Math.cos(frame.lat0 * Math.PI / 180) / (256 * cell * 0.8))), 3, 14);
  const [latS, lonW] = frame.toGeo(-half - cell, -half - cell), [latN, lonE] = frame.toGeo(half + cell, half + cell);
  const x0 = Math.floor(lonToX(lonW, z)), x1 = Math.floor(lonToX(lonE, z));
  const y0 = Math.floor(latToY(latN, z)), y1 = Math.floor(latToY(latS, z));
  const tiles = new Map(), jobs = [];
  let failed = 0;
  for (let ty = y0; ty <= y1; ty++) for (let tx = x0; tx <= x1; tx++) {
    jobs.push(async () => {
      try { tiles.set(`${tx},${ty}`, decodeElevation(await loadImage(urls().elev(z, tx, ty)))); } catch (e) { failed++; throw e; }
    });
  }
  await pool(jobs, 8, (d, all) => onProgress && onProgress(d / all));
  if (failed === jobs.length) throw new Error('A domborzati adatok nem tölthetők le (nincs internet?)');
  const sample = (px, py) => {                      // global pixel coordinates at zoom z
    const tx = Math.floor(px / 256), ty = Math.floor(py / 256), t = tiles.get(`${tx},${ty}`);
    if (!t) return 0;
    const lx = clamp(Math.floor(px - tx * 256), 0, 255), ly = clamp(Math.floor(py - ty * 256), 0, 255);
    return t[ly * 256 + lx];
  };
  const bilinear = (px, py) => {
    const ix = Math.floor(px - 0.5), iy = Math.floor(py - 0.5), fx = px - 0.5 - ix, fy = py - 0.5 - iy;
    const a = sample(ix, iy), b = sample(ix + 1, iy), c = sample(ix, iy + 1), d = sample(ix + 1, iy + 1);
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy;
  };
  const grid = new Float32Array(n * n);
  for (let j = 0; j < n; j++) {
    const y = -half + j * cell;
    for (let i = 0; i < n; i++) {
      const [lat, lon] = frame.toGeo(-half + i * cell, y);
      grid[j * n + i] = bilinear(lonToX(lon, z) * 256, latToY(lat, z) * 256);
    }
  }
  return { grid, zoom: z, metresPerPixel: mpp(frame.lat0, z) };
}

// --------------------------------------------------------------------- the air base and the carrier
const at = (g, n, cell, half, x, y) => {
  const gx = clamp((x + half) / cell, 0, n - 1.001), gy = clamp((y + half) / cell, 0, n - 1.001);
  const i = Math.floor(gx), j = Math.floor(gy), fx = gx - i, fy = gy - j, k = j * n + i;
  return (g[k] + (g[k + 1] - g[k]) * fx) * (1 - fy) + (g[k + n] + (g[k + n + 1] - g[k + n]) * fx) * fy;
};
// the base's footprint (runway N-S at x, taxiway and apron to the east): x -120 .. +620, y -1650 .. +1650
const FOOT = [-120, 620, -1650, 1650];

function placeAirfield(grid, n, cell, half) {
  let best = null;
  for (let cy = -24000; cy <= 24000; cy += 1000) for (let cx = -24000; cx <= 24000; cx += 1000) {
    let lo = 1e9, hi = -1e9, sum = 0, sum2 = 0, k = 0;
    for (let sy = 0; sy <= 8; sy++) for (let sx = 0; sx <= 4; sx++) {
      const h = at(grid, n, cell, half, cx + FOOT[0] + (FOOT[1] - FOOT[0]) * sx / 4, cy + FOOT[2] + (FOOT[3] - FOOT[2]) * sy / 8);
      lo = Math.min(lo, h); hi = Math.max(hi, h); sum += h; sum2 += h * h; k++;
    }
    if (lo < 3) continue;                                   // not in the sea (or a lake shore at sea level)
    const mean = sum / k, sd = Math.sqrt(Math.max(0, sum2 / k - mean * mean));
    const cost = (hi - lo) + 2 * sd + Math.hypot(cx, cy) * 0.0015 + Math.max(0, mean - 2500) * 0.02;
    if (!best || cost < best.cost) best = { x: cx, y: cy, elevation: Math.round(mean * 10) / 10, cost };
  }
  return best || { x: 0, y: 0, elevation: 6, island: true };   // all sea: an artificial island in the middle
}

// level the ground under the base, blending into the land around it over `blend` metres
function levelBase(grid, n, cell, half, a, blend = 700) {
  for (let j = 0; j < n; j++) {
    const y = -half + j * cell - a.y;
    const dy = Math.max(0, FOOT[2] - y, y - FOOT[3]);
    if (dy > blend) continue;
    for (let i = 0; i < n; i++) {
      const x = -half + i * cell - a.x;
      const dx = Math.max(0, FOOT[0] - x, x - FOOT[1]);
      const d = Math.hypot(dx, dy);
      if (d > blend) continue;
      const t = d / blend, w = 1 - t * t * (3 - 2 * t), k = j * n + i;
      grid[k] = grid[k] + (a.elevation - grid[k]) * w;
    }
  }
}

function placeCarrier(grid, n, cell, half, a) {
  let best = null;
  for (let r = 9000; r <= 42000; r += 3000) {
    for (let k = 0; k < 24; k++) {
      const ang = k / 24 * Math.PI * 2, x = a.x + Math.sin(ang) * r, y = a.y + Math.cos(ang) * r;
      if (Math.abs(x) > half - 6000 || Math.abs(y) > half - 6000) continue;
      let deep = true;
      for (let q = 0; q < 9 && deep; q++) {
        const qa = q / 9 * Math.PI * 2;
        if (at(grid, n, cell, half, x + Math.sin(qa) * 2500, y + Math.cos(qa) * 2500) > -12) deep = false;
      }
      if (deep && at(grid, n, cell, half, x, y) < -12) { best = { x, y }; break; }
    }
    if (best) break;
  }
  return best;
}

// --------------------------------------------------------------------- the ground's colour
const MIX = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
// painted from height and slope: what shows where no satellite image could be loaded
function paintGround(ctx, W, grid, n, cell, half, lat) {
  const img = ctx.createImageData(W, W), d = img.data, snow = clamp(4200 - Math.abs(lat) * 55, 400, 5200);
  const SEA = [32, 74, 104], DEEP = [18, 46, 72], SAND = [196, 182, 140], GRASS = [92, 120, 62], FOREST = [52, 78, 44],
    ROCK = [118, 110, 100], SNOW = [236, 240, 244], DRY = [168, 146, 104];
  const dryness = clamp((35 - Math.abs(Math.abs(lat) - 25)) / 20, 0, 1) * (Math.abs(lat) < 40 ? 1 : 0.2);
  for (let py = 0; py < W; py++) {
    const y = half - (py + 0.5) / W * 2 * half;
    for (let px = 0; px < W; px++) {
      const x = -half + (px + 0.5) / W * 2 * half, h = at(grid, n, cell, half, x, y);
      let c;
      if (h <= 0.5) c = MIX(SEA, DEEP, clamp(-h / 60, 0, 1));
      else {
        const sl = Math.hypot(at(grid, n, cell, half, x + cell, y) - at(grid, n, cell, half, x - cell, y),
          at(grid, n, cell, half, x, y + cell) - at(grid, n, cell, half, x, y - cell)) / (2 * cell);
        const noise = Math.sin(x * 0.0013 + Math.sin(y * 0.0009) * 3) * Math.sin(y * 0.0011 + Math.sin(x * 0.0007) * 2);
        c = h < 6 ? SAND : MIX(MIX(GRASS, FOREST, clamp(0.5 + noise * 0.8 + (h - 300) / 1500, 0, 1)), DRY, dryness);
        c = MIX(c, ROCK, clamp((sl - 0.35) * 2.5 + (h - snow * 0.75) / (snow * 0.5), 0, 1));
        c = MIX(c, SNOW, clamp((h - snow) / 300 + (0.5 - sl) * 0.3, 0, 1) * (sl < 0.9 ? 1 : 0.4));
        const shade = clamp(1 + ((at(grid, n, cell, half, x - cell, y) - at(grid, n, cell, half, x + cell, y)) * 0.6
          + (at(grid, n, cell, half, x, y + cell) - at(grid, n, cell, half, x, y - cell)) * 0.4) / (2 * cell) * 0.9, 0.7, 1.25);
        c = [c[0] * shade, c[1] * shade, c[2] * shade];
      }
      const k = (py * W + px) * 4;
      d[k] = c[0]; d[k + 1] = c[1]; d[k + 2] = c[2]; d[k + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
}

async function paintImagery(ctx, W, frame, size, onProgress) {
  const half = size / 2;
  const z = clamp(Math.round(Math.log2(2 * Math.PI * R * Math.cos(frame.lat0 * Math.PI / 180) / (256 * size / W))), 3, 17);
  const [latS, lonW] = frame.toGeo(-half, -half), [latN, lonE] = frame.toGeo(half, half);
  const x0 = Math.floor(lonToX(lonW, z)), x1 = Math.floor(lonToX(lonE, z));
  const y0 = Math.floor(latToY(latN, z)), y1 = Math.floor(latToY(latS, z));
  const toPx = (lat, lon) => { const [x, y] = frame.toLocal(lat, lon); return [(x + half) / size * W, (half - y) / size * W]; };
  const jobs = [];
  let ok = 0;
  for (let ty = y0; ty <= y1; ty++) for (let tx = x0; tx <= x1; tx++) {
    jobs.push(async () => {
      const img = await loadImage(urls().imagery(z, tx, ty));
      const [ax, ay] = toPx(yToLat(ty, z), xToLon(tx, z)), [bx, by] = toPx(yToLat(ty + 1, z), xToLon(tx + 1, z));
      ctx.drawImage(img, ax, ay, bx - ax + 0.6, by - ay + 0.6);   // a hair larger: no seams between tiles
      ok++;
    });
  }
  await pool(jobs, 12, (d, all) => onProgress && onProgress(d / all));
  return { ok, all: jobs.length, zoom: z };
}

// --------------------------------------------------------------------- everything together
// -> { data: terrain data (like terrain.json, heights as a Float32Array), canvas: the ground texture, info }
export async function buildWorld({ lat, lon, name, size = 102400, res = 1024, texSize = 4096, onProgress = () => {} }) {
  const frame = geoFrame(lat, lon), half = size / 2, n = res + 1, cell = size / res;
  onProgress('Domborzat letöltése…', 0);
  const { grid } = await elevationGrid(frame, size, res, (f) => onProgress('Domborzat letöltése…', f * 0.4));
  const field = placeAirfield(grid, n, cell, half);
  levelBase(grid, n, cell, half, field);
  const carrier = placeCarrier(grid, n, cell, half, field);
  onProgress('A táj kifestése…', 0.42);
  await new Promise((r) => setTimeout(r, 0));
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = texSize;
  const ctx = canvas.getContext('2d');
  paintGround(ctx, texSize, grid, n, cell, half, lat);
  onProgress('Műholdképek letöltése…', 0.5);
  const sat = await paintImagery(ctx, texSize, frame, size, (f) => onProgress('Műholdképek letöltése…', 0.5 + f * 0.48));
  let max = -1e9;
  for (let i = 0; i < grid.length; i++) if (grid[i] > max) max = grid[i];
  // the land around it up to the horizon (only to look at): 330 km, 1.5 km cells, a small texture
  onProgress('A látóhatár tája…', 0.985);
  let far = null;
  try {
    const FS = 330000, FR = 220, fh = FS / 2, fn = FR + 1, fc = FS / FR;
    const fg = await elevationGrid(frame, FS, FR);
    const fcan = document.createElement('canvas');
    fcan.width = fcan.height = 1024;
    const fctx = fcan.getContext('2d');
    paintGround(fctx, 1024, fg.grid, fn, fc, fh, lat);
    await paintImagery(fctx, 1024, frame, FS).catch(() => null);
    far = { size: FS, res: FR, grid: fg.grid, canvas: fcan, inner: half };
  } catch (e) { far = null; }
  onProgress('Kész', 1);
  return {
    data: { size, res, grid, airfield: { x: field.x, y: field.y, elevation: field.elevation } },
    canvas,
    info: { name, lat, lon, carrier, imagery: sat.ok / Math.max(1, sat.all), maxHeight: max, frame },
    far,
  };
}
