// Offline cache for the installed app (console-anywhere): everything the game loads is kept after the first
// visit, so it starts without internet.  Same-origin files: cache first, then refreshed in the background.
const CACHE = 'dogfight-plus-v3';
const CORE = ['./', 'index.html', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'js/three.min.js', 'js/game.js',
  'js/util.js', 'js/specs.js', 'js/terrain.js', 'js/sim.js', 'js/ai.js', 'js/render.js', 'js/glb.js', 'js/hud.js', 'js/mfd.js',
  'js/tutorial.js', 'js/audio.js', 'js/flight.js', 'js/weapons.js', 'js/career.js', 'js/voice.js', 'js/touch.js', 'js/hangar.js',
  'js/shopui.js', 'js/music.js', 'js/keys.js', 'js/race.js',
  'assets/f16.json', 'assets/terrain.json', 'assets/livery_viper.jpg', 'assets/livery_aggressor.jpg', 'assets/terrain_color.jpg',
  'assets/cockpit.png', 'assets/f16.glb', 'assets/fa18.glb', 'assets/f22.glb', 'assets/f15.glb', 'assets/aim9m.glb', 'assets/aim120c.glb'];
self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting())); });
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(async (c) => {
    const hit = await c.match(e.request, { ignoreSearch: true });
    const net = fetch(e.request).then((r) => { if (r.ok) c.put(e.request, r.clone()); return r; }).catch(() => hit);
    return hit || net;
  }));
});
