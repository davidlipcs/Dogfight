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

// the pilot in his helmet and suit: an SVG picture (shop, radio portrait)
export function pilotSvg(p) {
  const d = (() => {
    const a = hex(p.accent);
    switch (p.decal) {
      case 'stripe': return `<rect x="56" y="14" width="8" height="34" fill="${a}"/>`;
      case 'star': return `<path d="M60 18l4 9 10 1-7.5 6.5 2.5 9.5-9-5.5-9 5.5 2.5-9.5L46 28l10-1z" fill="${a}"/>`;
      case 'skull': return `<circle cx="60" cy="30" r="9" fill="${a}"/><circle cx="56" cy="29" r="2.4" fill="#111"/><circle cx="64" cy="29" r="2.4" fill="#111"/><rect x="56" y="36" width="8" height="4" fill="#111"/>`;
      case 'flame': return `<path d="M44 46c2-10 8-12 6-22 8 6 6 12 10 14 0-6 4-10 4-14 8 8 14 14 12 22z" fill="${a}"/>`;
      case 'wings': return `<path d="M60 30c-8-8-18-8-24-4 8 2 14 6 24 10zM60 30c8-8 18-8 24-4-8 2-14 6-24 10z" fill="${a}"/>`;
      case 'bolt': return `<path d="M64 14l-12 18h8l-4 16 16-22h-9z" fill="${a}"/>`;
      case 'check': return [0, 1, 2, 3].map((i) => [0, 1].map((j) => ((i + j) % 2 ? '' : `<rect x="${42 + i * 9}" y="${18 + j * 9}" width="9" height="9" fill="${a}"/>`)).join('')).join('');
      case 'dots': return [[48, 26], [60, 20], [72, 26], [54, 36], [66, 36]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3.2" fill="${a}"/>`).join('');
      default: return '';
    }
  })();
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 140"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
<rect width="120" height="140" fill="#1b232b"/>
<path d="M8 140c0-30 20-44 52-44s52 14 52 44z" fill="${hex(p.suit)}"/><path d="M52 100h16l-3 40H55z" fill="${hex(p.accent)}" opacity=".9"/>
<rect x="49" y="82" width="22" height="20" rx="6" fill="#c8a07a"/>
<ellipse cx="60" cy="52" rx="34" ry="38" fill="${hex(p.helmet)}"/>${d}
<path d="M30 56c0-10 12-14 30-14s30 4 30 14c0 12-10 22-30 22S30 68 30 56z" fill="${hex(p.visor)}"/>
<path d="M36 52c4-6 14-8 24-8" stroke="#fff" stroke-opacity=".5" stroke-width="3" fill="none" stroke-linecap="round"/>
<path d="M44 78c4 10 28 10 32 0v8c-4 8-28 8-32 0z" fill="#2a2e34"/>
<ellipse cx="60" cy="52" rx="34" ry="38" fill="url(#g)"/></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}
