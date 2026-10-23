// Google Photorealistic 3D Tiles over a real-world map (world.js), like in Microsoft Flight Simulator: the
// cities, buildings, forests and mountains streamed from Google, with the player's own API key (Google Cloud ->
// Map Tiles API).  They are only the picture: the ground the jets hit and land on stays the elevation grid of
// world.js (the same real terrain).  js/tiles.min.js is 3DTilesRendererJS 0.3.46 (Apache-2.0, NASA-AMMOS),
// bundled for the game's three.js; it is loaded only when the key is set.
import { THREE } from './util.js';

const DEG = Math.PI / 180;
let loading = null;
function loadLib() {
  if (window.DogfightTiles) return Promise.resolve();
  if (!loading) {
    loading = new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = (window.DOGFIGHT_ASSETS && window.DOGFIGHT_ASSETS['tiles.min.js']) || 'js/tiles.min.js';
      s.onload = () => resolve(); s.onerror = () => reject(new Error('tiles.min.js'));
      document.head.appendChild(s);
    });
  }
  return loading;
}

export class GoogleTiles {
  // view: the SceneView; info: world.js info (lat, lon); quality: settings quality
  constructor(view, key, info, quality) {
    this.view = view; this.key = key; this.info = info; this.offset = 0; this.calibrated = 0; this.nextCal = 4;
    this.ready = loadLib().then(() => this.init(quality)).catch((e) => { console.error(e); this.failed = e.message; });
  }
  init(quality) {
    const T = window.DogfightTiles, v = this.view;
    const tiles = this.tiles = new T.TilesRenderer();
    tiles.registerPlugin(new T.GoogleCloudAuthPlugin({ apiToken: this.key, autoRefreshToken: true }));
    const draco = new T.DRACOLoader().setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
    tiles.registerPlugin(new T.GLTFExtensionsPlugin({ dracoLoader: draco }));
    tiles.registerPlugin(new T.TileCompressionPlugin());
    tiles.registerPlugin(new T.UnloadTilesPlugin());
    tiles.errorTarget = { low: 40, medium: 24, high: 14, ultra: 6 }[quality] || 14;
    tiles.downloadQueue.maxJobs = 30; tiles.parseQueue.maxJobs = 10;
    tiles.lruCache.maxSize = quality === 'ultra' ? 12000 : 6000;
    tiles.addEventListener('load-error', (e) => { this.errors = (this.errors || 0) + 1; if (e && e.error) this.lastError = String(e.error.message || e.error); });
    // Earth centred coordinates -> the map's east / north / up metres
    const enu = new THREE.Matrix4();
    T.WGS84_ELLIPSOID.getEastNorthUpFrame(this.info.lat * DEG, this.info.lon * DEG, enu);
    this.base = enu.invert();
    tiles.group.matrixAutoUpdate = false;
    this.place();
    v.scene.add(tiles.group);
    // the elevation-grid ground and the flat sea stay hidden under the photorealistic ground
    if (v.terrainGroup) v.terrainGroup.visible = false;
    if (v.seaMesh) v.seaMesh.visible = false;
    this.credit = document.getElementById('gcredit');
    if (this.credit) this.credit.hidden = false;
  }
  // our z is height above sea level; the tiles are on the WGS84 ellipsoid: shift them by the measured difference
  place() {
    this.tiles.group.matrix.copy(this.base).premultiply(new THREE.Matrix4().makeTranslation(0, 0, -this.offset));
    this.tiles.group.matrixWorldNeedsUpdate = true;
  }
  update(dt, camera, renderer) {
    const t = this.tiles;
    if (!t) return;
    camera.updateMatrixWorld();
    t.setCamera(camera);
    t.setResolutionFromRenderer(camera, renderer);
    t.update();
    this.nextCal -= dt;
    if (this.nextCal <= 0 && this.calibrated < 6) { this.nextCal = 5; this.calibrate(camera); }
    if (this.credit && (this.creditT = (this.creditT || 0) - dt) <= 0) {
      this.creditT = 2;
      const a = t.getAttributions ? t.getAttributions() : [];
      this.credit.textContent = 'Google' + (a.length ? ' · ' + a.map((x) => x.value).join(' ') : '');
    }
  }
  // raycast the loaded tiles straight down at a few points around the camera and compare with the elevation
  // grid (away from the levelled air base): the median difference is the geoid height here
  calibrate(camera) {
    const terr = this.view.terrain, ray = new THREE.Raycaster(), diffs = [], p = camera.position;
    const field = terr.airfield;
    for (let k = 0; k < 16; k++) {
      const a = k / 16 * Math.PI * 2, r = 1500 + (k % 4) * 1200, x = p.x + Math.cos(a) * r, y = p.y + Math.sin(a) * r;
      if (Math.abs(x - field.x) < 1500 && Math.abs(y - field.y) < 2500) continue;
      ray.set(new THREE.Vector3(x, y, 9000), new THREE.Vector3(0, 0, -1));
      const hit = ray.intersectObject(this.tiles.group, true)[0];
      if (hit) diffs.push(hit.point.z - terr.rawHeight(x, y));
    }
    if (diffs.length < 5) return;
    diffs.sort((a, b) => a - b);
    const med = diffs[diffs.length >> 1];
    if (Math.abs(med) < 150) { this.offset += med * (this.calibrated ? 0.5 : 1); this.calibrated++; this.place(); }
  }
  dispose() {
    const v = this.view;
    if (this.tiles) { v.scene.remove(this.tiles.group); this.tiles.dispose(); this.tiles = null; }
    if (v.terrainGroup) v.terrainGroup.visible = true;
    if (v.seaMesh) v.seaMesh.visible = true;
    if (this.credit) this.credit.hidden = true;
  }
}
