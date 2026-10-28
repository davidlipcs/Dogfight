// Shop art: the patterns of the paint schemes (drawn on a canvas, laid over the jet's own paint texture), the
// small swatch pictures of the shop, and the pilot's helmet bust (SVG) for the shop, the radio and the parachute.
const hex = (n) => `#${n.toString(16).padStart(6, '0')}`;
const rgba = (n, a) => `rgba(${n >> 16 & 255},${n >> 8 & 255},${n & 255},${a})`;
// a small seeded generator: the same scheme always gets the same pattern
function seeded(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const hash = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };

// draws the pattern `kind` in colour `col` (0xRRGGBB) over a w x h canvas context
export function drawPattern(ctx, w, h, kind, col, seed = 1) {
  const r = seeded(seed), u = Math.max(w, h);
  ctx.save();
  ctx.fillStyle = rgba(col, 0.78); ctx.strokeStyle = rgba(col, 0.78); ctx.lineJoin = 'round';
  if (kind === 'camo') {
    for (let i = 0; i < 46; i++) {
      const cx = r() * w, cy = r() * h, rad = u * (0.04 + r() * 0.09), n = 7 + Math.floor(r() * 4);
      ctx.beginPath();
      for (let k = 0; k < n; k++) { const a = k / n * Math.PI * 2, d = rad * (0.55 + r() * 0.7); ctx[k ? 'lineTo' : 'moveTo'](cx + Math.cos(a) * d * 1.4, cy + Math.sin(a) * d * 0.8); }
      ctx.closePath(); ctx.fill();
    }
  } else if (kind === 'splinter') {
    for (let i = 0; i < 40; i++) {
      const cx = r() * w, cy = r() * h, s = u * (0.04 + r() * 0.1), a0 = r() * Math.PI * 2;
      ctx.beginPath();
      for (let k = 0; k < 4; k++) { const a = a0 + k * Math.PI / 2 + (r() - 0.5) * 0.9, d = s * (0.5 + r()); ctx[k ? 'lineTo' : 'moveTo'](cx + Math.cos(a) * d, cy + Math.sin(a) * d); }
      ctx.closePath(); ctx.fill();
    }
  } else if (kind === 'digital') {
    const n = 42, cw = w / n, ch = h / n, grid = [];
    for (let y = 0; y < n; y++) { grid.push([]); for (let x = 0; x < n; x++) grid[y].push(r() < 0.2 + (x > 0 && grid[y][x - 1] ? 0.35 : 0) + (y > 0 && grid[y - 1][x] ? 0.3 : 0) ? 1 : 0); }
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (grid[y][x]) ctx.fillRect(x * cw, y * ch, cw + 0.5, ch + 0.5);
  } else if (kind === 'tiger') {
    ctx.lineCap = 'round';
    for (let i = 0; i < 18; i++) {
      const x0 = (i / 18) * w * 1.3 - w * 0.15, wig = u * 0.04;
      ctx.lineWidth = u * (0.012 + r() * 0.018);
      ctx.beginPath(); ctx.moveTo(x0, -10);
      for (let y = 0; y <= h; y += h / 8) ctx.lineTo(x0 + (y / h) * w * 0.25 + (r() - 0.5) * wig * 2, y);
      ctx.stroke();
    }
  } else if (kind === 'stripes') {
    ctx.translate(w / 2, h / 2); ctx.rotate(-0.35);
    const band = u / 14;
    for (let x = -u; x < u; x += band * 2) ctx.fillRect(x, -u, band, u * 2);
  } else if (kind === 'checker') {
    const n = 14, c = w / n;
    for (let y = 0; y < Math.ceil(h / c); y++) for (let x = 0; x < n; x++) if ((x + y) % 2) ctx.fillRect(x * c, y * c, c + 0.5, c + 0.5);
  } else if (kind === 'hex') {
    const s = u / 22, hh = s * Math.sqrt(3);
    ctx.lineWidth = Math.max(1.5, s * 0.18);
    for (let row = -1; row < h / hh + 1; row++) for (let col2 = -1; col2 < w / (s * 1.5) + 1; col2++) {
      const cx = col2 * s * 1.5, cy = row * hh + (col2 % 2 ? hh / 2 : 0);
      ctx.beginPath();
      for (let k = 0; k < 6; k++) { const a = k * Math.PI / 3; ctx[k ? 'lineTo' : 'moveTo'](cx + Math.cos(a) * s * 0.92, cy + Math.sin(a) * s * 0.92); }
      ctx.closePath(); ctx.stroke();
    }
  } else if (kind === 'dots') {
    const s = u / 18;
    for (let y = 0; y < h / s + 1; y++) for (let x = 0; x < w / s + 1; x++) { ctx.beginPath(); ctx.arc(x * s + (y % 2 ? s / 2 : 0), y * s, s * 0.28, 0, Math.PI * 2); ctx.fill(); }
  } else if (kind === 'wave') {
    ctx.lineWidth = u * 0.016;
    for (let y = -u * 0.1; y < h + u * 0.1; y += u * 0.07) {
      ctx.beginPath();
      for (let x = 0; x <= w; x += w / 40) ctx[x ? 'lineTo' : 'moveTo'](x, y + Math.sin(x / w * Math.PI * 6 + y * 0.02) * u * 0.02);
      ctx.stroke();
    }
  } else if (kind === 'flame') {
    for (let x = -u * 0.05; x < w + u * 0.05; x += u * 0.075) {
      const hgt = h * (0.25 + r() * 0.35), wd = u * 0.06;
      ctx.beginPath(); ctx.moveTo(x - wd, h);
      ctx.bezierCurveTo(x - wd, h - hgt * 0.5, x + wd * 0.6, h - hgt * 0.55, x + (r() - 0.5) * wd, h - hgt);
      ctx.bezierCurveTo(x + wd * 1.4, h - hgt * 0.5, x + wd * 1.2, h - hgt * 0.2, x + wd, h);
      ctx.closePath(); ctx.fill();
    }
  } else if (kind === 'rainbow') {
    ctx.translate(w / 2, h / 2); ctx.rotate(-0.5);
    const cols = ['#ff3b3b', '#ff9a2a', '#ffe83a', '#3bd86a', '#3ba8ff', '#8a4aff'], band = u / 9;
    cols.forEach((c, i) => { ctx.fillStyle = c; ctx.globalAlpha = 0.85; ctx.fillRect(-u, -u + i * band * 1.6 + u * 0.1, u * 2, band); });
  }
  ctx.restore();
}

// the pattern over a given base picture (an image / canvas) at most `max` px wide: returns a canvas
export function patterned(img, skin, max = 2048) {
  const iw = img.width || img.videoWidth || 1024, ih = img.height || img.videoHeight || 1024, k = Math.min(1, max / Math.max(iw, ih));
  const cv = document.createElement('canvas'); cv.width = Math.max(8, Math.round(iw * k)); cv.height = Math.max(8, Math.round(ih * k));
  const ctx = cv.getContext('2d');
  ctx.drawImage(img, 0, 0, cv.width, cv.height);
  drawPattern(ctx, cv.width, cv.height, skin.pattern, skin.pcolor, hash(skin.id));
  return cv;
}

const swatchCache = {};
// a small picture of a paint scheme (tint, pattern, a metal sheen), as a data URL
export function swatch(skin, size = 72) {
  const ck = skin.id + size;
  if (swatchCache[ck]) return swatchCache[ck];
  const cv = document.createElement('canvas'); cv.width = cv.height = size;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = hex(skin.color); ctx.fillRect(0, 0, size, size);
  if (skin.pattern) drawPattern(ctx, size, size, skin.pattern, skin.pcolor, hash(skin.id));
  const shine = ctx.createLinearGradient(0, 0, size, size);
  const m = skin.metal === null || skin.metal === undefined ? 0.15 : skin.metal;
  shine.addColorStop(0, `rgba(255,255,255,${0.1 + m * 0.35})`); shine.addColorStop(0.5, 'rgba(255,255,255,0)'); shine.addColorStop(1, 'rgba(0,0,0,0.35)');
  ctx.fillStyle = shine; ctx.fillRect(0, 0, size, size);
  if (skin.emissive) { ctx.fillStyle = rgba(skin.emissive, 0.35); ctx.fillRect(0, 0, size, size); }
  return (swatchCache[ck] = cv.toDataURL('image/png'));
}

// ---- the pilot: a flight helmet with visor and oxygen mask, hose, harness, as an SVG picture (shop, radio portrait)
const mix = (n, k) => {                                    // k > 0 lighter, k < 0 darker
  const f = (v) => Math.max(0, Math.min(255, Math.round(k >= 0 ? v + (255 - v) * k : v * (1 + k))));
  return `rgb(${f(n >> 16 & 255)},${f(n >> 8 & 255)},${f(n & 255)})`;
};
const luma = (n) => 0.299 * (n >> 16 & 255) + 0.587 * (n >> 8 & 255) + 0.114 * (n & 255);

export function pilotSvg(p) {
  const a = hex(p.accent), sun = luma(p.visor) < 70;
  const decal = (() => {
    switch (p.decal) {
      case 'stripe': return `<rect x="56.5" y="13" width="7" height="26" rx="2" fill="${a}"/>`;
      case 'star': return `<path d="M60 15l3.4 7.4 8 .9-6 5.4 1.7 7.9-7.1-4-7.1 4 1.7-7.9-6-5.4 8-.9z" fill="${a}"/>`;
      case 'skull': return `<circle cx="60" cy="26" r="8" fill="${a}"/><circle cx="56.5" cy="25" r="2.2" fill="#111"/><circle cx="63.5" cy="25" r="2.2" fill="#111"/><rect x="57" y="31" width="6" height="3.5" rx="1" fill="#111"/>`;
      case 'flame': return `<path d="M42 40c1-9 7-11 5-20 7 5 6 11 9 12 0-5 3-9 3-13 7 7 12 13 10 21z" fill="${a}"/>`;
      case 'wings': return `<path d="M60 27c-7-7-17-7-23-3 7 2 13 5 23 9zM60 27c7-7 17-7 23-3-7 2-13 5-23 9z" fill="${a}"/>`;
      case 'bolt': return `<path d="M63 12l-11 17h7.5l-4 15 15-20h-8.5z" fill="${a}"/>`;
      case 'check': return [0, 1, 2, 3].map((i) => [0, 1].map((j) => ((i + j) % 2 ? '' : `<rect x="${44 + i * 8}" y="${17 + j * 8}" width="8" height="8" fill="${a}"/>`)).join('')).join('');
      case 'dots': return [[48, 24], [60, 18], [72, 24], [54, 33], [66, 33]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3" fill="${a}"/>`).join('');
      default: return '';
    }
  })();
  const eyes = sun ? '' : `<ellipse cx="48.5" cy="54" rx="4.2" ry="2.6" fill="#f2efe8"/><ellipse cx="71.5" cy="54" rx="4.2" ry="2.6" fill="#f2efe8"/>
<circle cx="49" cy="54" r="2" fill="#3b2a1c"/><circle cx="71" cy="54" r="2" fill="#3b2a1c"/><circle cx="49.6" cy="53.4" r=".7" fill="#fff"/><circle cx="71.6" cy="53.4" r=".7" fill="#fff"/>
<path d="M43 49.5q5.5-3.2 11 0M66 49.5q5.5-3.2 11 0" stroke="#4a3322" stroke-width="1.6" fill="none" stroke-linecap="round"/>`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 140"><defs>
<radialGradient id="bg" cx=".5" cy=".35" r=".8"><stop offset="0" stop-color="#3a4a56"/><stop offset="1" stop-color="#10171d"/></radialGradient>
<linearGradient id="suit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mix(p.suit, 0.22)}"/><stop offset="1" stop-color="${mix(p.suit, -0.35)}"/></linearGradient>
<radialGradient id="hel" cx=".38" cy=".28" r=".85"><stop offset="0" stop-color="${mix(p.helmet, 0.5)}"/><stop offset=".45" stop-color="${hex(p.helmet)}"/><stop offset="1" stop-color="${mix(p.helmet, -0.5)}"/></radialGradient>
<linearGradient id="vis" x1="0" y1="0" x2=".3" y2="1"><stop offset="0" stop-color="${mix(p.visor, 0.35)}" stop-opacity="${sun ? 1 : 0.5}"/><stop offset="1" stop-color="${hex(p.visor)}" stop-opacity="${sun ? 1 : 0.28}"/></linearGradient>
<linearGradient id="mask" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#454c47"/><stop offset="1" stop-color="#1a1e1c"/></linearGradient>
<linearGradient id="met" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e8ecf0"/><stop offset="1" stop-color="#6c737b"/></linearGradient>
<radialGradient id="skin" cx=".5" cy=".4" r=".7"><stop offset="0" stop-color="#d6a984"/><stop offset="1" stop-color="#8e6446"/></radialGradient>
<clipPath id="face"><path d="M33 52C33 42 44 38 60 38S87 42 87 52v9c0 8-12 13-27 13S33 69 33 61z"/></clipPath>
</defs>
<rect width="120" height="140" fill="url(#bg)"/>
<path d="M-4 30C20 8 40-2 60-2s40 10 64 32M-4 70C14 54 30 46 44 42" stroke="#52626e" stroke-width="2" fill="none" opacity=".35"/>
<path d="M4 140c1-27 20-41 46-45h20c26 4 45 18 46 45z" fill="url(#suit)"/>
<path d="M4 140c1-27 20-41 46-45" stroke="#000" stroke-opacity=".25" stroke-width="1.5" fill="none"/>
<ellipse cx="60" cy="97" rx="19" ry="6.5" fill="${mix(p.suit, -0.45)}"/><path d="M50 94c3 6 17 6 20 0v6c-4 5-16 5-20 0z" fill="url(#skin)"/>
<path d="M30 100l10 40h-11l-11-34z M90 100l-10 40h11l11-34z" fill="#25282c"/><path d="M33 104l9 34M87 104l-9 34" stroke="#6e747b" stroke-width=".8" stroke-dasharray="2 2.2" fill="none"/>
<rect x="38" y="119" width="44" height="5" fill="#25282c"/><rect x="54" y="115.5" width="12" height="12" rx="2" fill="url(#met)" stroke="#3b4147" stroke-width=".8"/><rect x="57.5" y="119" width="5" height="5" fill="#2a2e33"/>
<rect x="24" y="112" width="15" height="7" rx="1" fill="${a}" opacity=".92"/><path d="M26 114.5h11M26 116.8h8" stroke="#000" stroke-opacity=".45" stroke-width=".9"/>
<rect x="8" y="118" width="12" height="9" rx="1.5" fill="${a}" opacity=".8"/>
<path d="M44 77c-9 6-16 18-14 32 1 6 6 8 8 4-2-10 1-20 9-26" fill="none" stroke="#1d2520" stroke-width="5" stroke-linecap="round"/>
<path d="M44 77c-9 6-16 18-14 32" fill="none" stroke="#56635a" stroke-width="5" stroke-linecap="round" stroke-dasharray="1.2 2.6" opacity=".7"/>
<ellipse cx="60" cy="52" rx="34" ry="38" fill="url(#hel)"/>
<ellipse cx="25.5" cy="63" rx="5.2" ry="10" fill="#2b2f35" stroke="#4a5058" stroke-width="1"/><ellipse cx="94.5" cy="63" rx="5.2" ry="10" fill="#2b2f35" stroke="#4a5058" stroke-width="1"/>
${decal}
<path d="M30 40C34 26 46 18 60 18s26 8 30 22" stroke="#fff" stroke-opacity=".4" stroke-width="2" fill="none" stroke-linecap="round"/>
<path d="M30 49c4-12 16-15 30-15s26 3 30 15v3c-4-8-16-11-30-11S34 44 30 52z" fill="#15181b" opacity=".9"/>
<g clip-path="url(#face)"><rect x="30" y="36" width="60" height="42" fill="url(#skin)"/>${eyes}</g>
<path d="M33 52C33 42 44 38 60 38S87 42 87 52v9c0 8-12 13-27 13S33 69 33 61z" fill="url(#vis)" stroke="#0c0e10" stroke-width="2"/>
<path d="M38 47c5-5 14-7 22-7M70 41c7 1 12 4 15 8" stroke="#fff" stroke-opacity="${sun ? 0.5 : 0.45}" stroke-width="2.2" fill="none" stroke-linecap="round"/>
<path d="M43 64c6-3 28-3 34 0l3 10c-4 12-13 17-20 17s-16-5-20-17z" fill="url(#mask)" stroke="#0c0e10" stroke-width="1"/>
<circle cx="60" cy="79" r="4.5" fill="#101214" stroke="#555d58" stroke-width="1.2"/><path d="M56 79h8M60 75v8" stroke="#3a403c" stroke-width=".8"/>
<rect x="37" y="62" width="7" height="6" rx="1.5" fill="url(#met)"/><rect x="76" y="62" width="7" height="6" rx="1.5" fill="url(#met)"/>
<path d="M44 66c4-2 8-2.5 12-2.5" stroke="#fff" stroke-opacity=".18" stroke-width="1.5" fill="none" stroke-linecap="round"/>
</svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}
