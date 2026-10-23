// Height field (exported from the Python generator) + the home air base.
import { b64ToArray, clamp } from './util.js';

export const RUNWAY_LENGTH = 3000, RUNWAY_WIDTH = 45, TAXIWAY_OFFSET = 190, TAXIWAY_WIDTH = 23;
export const APRON = [260, 520, -350, 350];

export class Airfield {
  constructor(x, y, elevation) { this.x = x; this.y = y; this.elevation = elevation; }
  get southThreshold() { return this.y - RUNWAY_LENGTH / 2; }
  onRunway(x, y, margin = 0) {
    return Math.abs(x - this.x) <= RUNWAY_WIDTH / 2 + margin && Math.abs(y - this.y) <= RUNWAY_LENGTH / 2 + margin;
  }
  onPaved(x, y) {
    const dx = x - this.x, dy = y - this.y;
    if (this.onRunway(x, y, 3)) return true;
    if (Math.abs(dx - TAXIWAY_OFFSET) <= TAXIWAY_WIDTH / 2 && Math.abs(dy) <= RUNWAY_LENGTH / 2) return true;
    for (const cy of [-RUNWAY_LENGTH / 2 + 60, 0, RUNWAY_LENGTH / 2 - 60]) {
      if (dx >= 0 && dx <= TAXIWAY_OFFSET && Math.abs(dy - cy) <= TAXIWAY_WIDTH / 2) return true;
    }
    const [x0, x1, y0, y1] = APRON;
    return dx >= x0 - 70 && dx <= x1 && dy >= y0 && dy <= y1;
  }
  startPosition() { return [this.x, this.southThreshold + 120, 0]; }
}

export class Terrain {
  constructor(data) { this.load(data); }
  // a new map in the same object (the carrier and the scene keep their references): data.heights is the
  // packed Int16 grid of terrain.json, data.grid a ready Float32Array (the real world, world.js)
  load(data) {
    this.size = data.size;
    this.res = data.res;
    this.n = data.res + 1;
    this.cell = this.size / this.res;
    this.half = this.size / 2;
    if (data.grid) this.grid = data.grid;
    else {
      const raw = b64ToArray(data.heights, Int16Array);
      this.grid = new Float32Array(raw.length);
      for (let i = 0; i < raw.length; i++) this.grid[i] = raw[i] * data.scale;
    }
    let max = -1e9;
    for (let i = 0; i < this.grid.length; i++) if (this.grid[i] > max) max = this.grid[i];
    this.maxHeight = max;
    const a = data.airfield;
    if (this.airfield) Object.assign(this.airfield, { x: a.x, y: a.y, elevation: a.elevation });
    else this.airfield = new Airfield(a.x, a.y, a.elevation);
  }
  at(i, j) { return this.grid[j * this.n + i]; }
  rawHeight(x, y) {
    const gx = (x + this.half) / this.cell, gy = (y + this.half) / this.cell;
    if (gx < 0 || gy < 0 || gx >= this.res || gy >= this.res) return -220;
    const i = Math.floor(gx), j = Math.floor(gy), fx = gx - i, fy = gy - j;
    const n = this.n, g = this.grid, k = j * n + i;
    const h0 = g[k] + (g[k + 1] - g[k]) * fx;
    const h1 = g[k + n] + (g[k + n + 1] - g[k + n]) * fx;
    return h0 + (h1 - h0) * fy;
  }
  height(x, y) { return Math.max(this.rawHeight(x, y), 0); }
  slope(x, y, d = 6) {
    const gx = (this.height(x + d, y) - this.height(x - d, y)) / (2 * d);
    const gy = (this.height(x, y + d) - this.height(x, y - d)) / (2 * d);
    return Math.atan(Math.hypot(gx, gy));
  }
  lineOfSight(a, b, samples = 12) {
    if (a.z > this.maxHeight && b.z > this.maxHeight) return true;
    for (let k = 1; k < samples; k++) {
      const t = k / samples, z = a.z + (b.z - a.z) * t;
      if (z < this.maxHeight && z < this.height(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)) return false;
    }
    return true;
  }
  clampInside(x, y, margin = 8000) {
    const lim = this.half - margin;
    return [clamp(x, -lim, lim), clamp(y, -lim, lim)];
  }
}
