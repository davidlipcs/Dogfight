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

// what the visor does to the view from inside the cockpit: the colour the scene is multiplied by (clear glass = white),
// the darkness of the visor's rim and whether it is a mirror coating.  Not darker than 25% so that it stays playable.
export function visorEffect(o) {
  if (!o) return null;
  const T = Math.max(0.25, Math.min(1, o.visorT === undefined ? 1 : o.visorT)), k = 1 - T;
  if (T >= 0.95) return null;
  const c = (sh) => Math.round(255 * (T + k * ((o.visor >> sh & 255) / 255) * 0.9));
  return { mul: `rgb(${c(16)},${c(8)},${c(0)})`, rim: Math.min(0.55, 0.12 + k * 0.5), mirror: !!o.mirror, T };
}

// the helmet's livery as a picture (for the 3D helmet): the shell colour with the pattern over it
export function helmetTexture(o, size = 512) {
  const cv = document.createElement('canvas'); cv.width = size; cv.height = size / 2;
  const ctx = cv.getContext('2d'), w = cv.width, h = cv.height;
  ctx.fillStyle = hex(o.helmet); ctx.fillRect(0, 0, w, h);
  const c2 = hex(o.helmet2);
  ctx.fillStyle = c2; ctx.strokeStyle = c2;
  // u = 0.25 is the front of the sphere used for the helmet, 0.75 the back; v = 0 the crown, 1 the neck
  const band = (u0, u1) => ctx.fillRect(u0 * w, 0, (u1 - u0) * w, h * 0.62);
  switch (o.pattern) {
    case 'stripes': band(0.22, 0.28); band(0.72, 0.78); ctx.fillRect(0, 0, w, h * 0.04); break;
    case 'chevron': for (let k = 0; k < 3; k++) { ctx.beginPath(); ctx.moveTo(0.25 * w - 0.12 * w, h * (0.1 + k * 0.12)); ctx.lineTo(0.25 * w, h * (0.28 + k * 0.12)); ctx.lineTo(0.25 * w + 0.12 * w, h * (0.1 + k * 0.12)); ctx.lineWidth = h * 0.05; ctx.stroke(); } break;
    case 'camo': { const r = seeded(11); ctx.globalAlpha = 0.85; for (let k = 0; k < 38; k++) { ctx.beginPath(); ctx.ellipse(r() * w, r() * h * 0.8, w * (0.02 + r() * 0.06), h * (0.04 + r() * 0.1), r() * 3, 0, 7); ctx.fill(); } ctx.globalAlpha = 1; break; }
    case 'wolf': for (let k = 0; k < 6; k++) { const u = 0.25 + (k - 2.5) * 0.045; ctx.beginPath(); ctx.moveTo(u * w, 0); ctx.lineTo((u + 0.02) * w, h * 0.55); ctx.lineTo((u + 0.035) * w, 0); ctx.fill(); } break;
    case 'circuit': { ctx.lineWidth = 2.2; const r = seeded(5); for (let k = 0; k < 14; k++) { let x = r() * w, y = r() * h * 0.5; ctx.beginPath(); ctx.moveTo(x, y); for (let j = 0; j < 4; j++) { if (j % 2) y += (r() - 0.3) * h * 0.2; else x += (r() - 0.5) * w * 0.12; ctx.lineTo(x, y); } ctx.stroke(); ctx.beginPath(); ctx.arc(x, y, 3.4, 0, 7); ctx.fill(); } break; }
    case 'tricolor': { const cols = ['#cd2a3e', '#f4f4f0', '#2e8a4a']; cols.forEach((c, k) => { ctx.fillStyle = c; ctx.fillRect((0.25 - 0.045 + k * 0.03) * w, 0, 0.03 * w, h * 0.66); ctx.fillRect((0.75 - 0.045 + k * 0.03) * w, 0, 0.03 * w, h * 0.66); }); break; }
    case 'trim': ctx.fillRect(0, h * 0.62, w, h * 0.035); ctx.fillRect(0, h * 0.78, w, h * 0.015); ctx.beginPath(); ctx.arc(0.25 * w, h * 0.1, h * 0.06, 0, 7); ctx.fill(); break;
    default: break;
  }
  return cv;
}

export function pilotSvg(p) {
  const T = p.visorT === undefined ? 0.3 : p.visorT, a = hex(p.accent), c2 = hex(p.helmet2), mirror = !!p.mirror, press = !!p.pressure;
  const faceVis = Math.max(0, Math.min(1, (T - 0.22) / 0.7));           // how much of the face shows through the glass
  const tintOp = (1 - T) * 1.12 > 0.9 ? 0.9 : (1 - T) * 1.12;
  const livery = (() => {
    switch (p.pattern) {
      case 'stripes': return `<rect x="56" y="12" width="8" height="34" fill="${c2}"/><rect x="48" y="14" width="1.6" height="30" fill="${c2}" opacity=".8"/><rect x="70.4" y="14" width="1.6" height="30" fill="${c2}" opacity=".8"/>`;
      case 'chevron': return [0, 1, 2].map((k) => `<path d="M34 ${28 + k * 7}L60 ${14 + k * 7}L86 ${28 + k * 7}" fill="none" stroke="${c2}" stroke-width="4"/>`).join('');
      case 'camo': return `<g fill="${c2}" opacity=".85"><path d="M30 40c6-6 14-3 18-10 4-6 12-2 11 4s-9 8-14 12-14 6-15-6z"/><path d="M62 20c8-3 16 0 20 8s-6 12-12 8-14-12-8-16z"/><path d="M80 44c6-4 12 1 10 8s-8 6-12 2 0-8 2-10z"/></g><g fill="${mix(p.helmet2, -0.35)}" opacity=".7"><path d="M44 18c5-3 10 0 8 5s-8 4-8-5z"/><path d="M70 36c5-2 8 3 4 6s-8-1-4-6z"/></g>`;
      case 'wolf': return `<g fill="${c2}"><path d="M44 12l6 32-12-26z"/><path d="M52 10l6 34-9-30z"/><path d="M68 10l-6 34 9-30z"/><path d="M76 12l-6 32 12-26z"/><path d="M36 22l8 22-14-12z"/><path d="M84 22l-8 22 14-12z"/></g>`;
      case 'circuit': return `<g stroke="${c2}" stroke-width="1.3" fill="none" opacity=".95"><path d="M40 36h10v-10h14M52 44v-8M64 44v-12h14v-8M78 38h8M44 22h8"/></g><g fill="${c2}"><circle cx="64" cy="26" r="1.8"/><circle cx="78" cy="24" r="1.8"/><circle cx="50" cy="26" r="1.8"/><circle cx="86" cy="38" r="1.8"/></g>`;
      case 'tricolor': return `<rect x="52" y="12" width="5.4" height="34" fill="#cd2a3e"/><rect x="57.3" y="12" width="5.4" height="34" fill="#f4f4f0"/><rect x="62.6" y="12" width="5.4" height="34" fill="#2e8a4a"/>`;
      case 'trim': return `<path d="M28 44C32 24 44 16 60 16s28 8 32 28" fill="none" stroke="${c2}" stroke-width="2.4"/><path d="M60 19l2.6 5.6 6 .7-4.5 4.1 1.3 6-5.4-3.1-5.4 3.1 1.3-6-4.5-4.1 6-.7z" fill="${c2}"/>`;
      default: return '';
    }
  })();
  const patch = (() => {
    switch (p.patch) {
      case 'flag-hu': return `<rect x="8" y="118" width="14" height="3.3" fill="#cd2a3e"/><rect x="8" y="121.3" width="14" height="3.3" fill="#f4f4f0"/><rect x="8" y="124.6" width="14" height="3.3" fill="#2e8a4a"/>`;
      case 'anchor': return `<circle cx="15" cy="122" r="6.5" fill="${a}"/><path d="M15 117v10M11 124c0 3 8 3 8 0M12 119h6" stroke="#111" stroke-width="1.2" fill="none"/>`;
      case 'skull': return `<circle cx="15" cy="122" r="6.5" fill="#111" stroke="${a}" stroke-width="1"/><circle cx="13" cy="121" r="1.4" fill="${a}"/><circle cx="17" cy="121" r="1.4" fill="${a}"/><rect x="13.4" y="124" width="3.2" height="2" fill="${a}"/>`;
      case 'cross': return `<circle cx="15" cy="122" r="6.5" fill="#111" stroke="${a}" stroke-width="1"/><path d="M15 117.5l2 3.5 3.5 2-3.5 2-2 3.5-2-3.5-3.5-2 3.5-2z" fill="${a}"/>`;
      case 'star': return `<circle cx="15" cy="122" r="6.5" fill="#111" stroke="${a}" stroke-width="1"/><path d="M15 117.5l1.5 3.2 3.5.4-2.6 2.4.7 3.5-3.1-1.8-3.1 1.8.7-3.5-2.6-2.4 3.5-.4z" fill="${a}"/>`;
      default: return `<path d="M15 116l7 3v6c0 3-4 5-7 6-3-1-7-3-7-6v-6z" fill="${a}" opacity=".9"/><path d="M15 119v9M11.5 122.5h7" stroke="#111" stroke-width="1.1"/>`;
    }
  })();
  const helmetBody = press
    ? `<ellipse cx="60" cy="50" rx="37" ry="41" fill="url(#hel)"/><ellipse cx="60" cy="86" rx="31" ry="7.5" fill="#9aa2aa" stroke="#6c737b" stroke-width="1.2"/><rect x="29" y="82" width="62" height="7" rx="3" fill="url(#met)"/>`
    : `<ellipse cx="60" cy="52" rx="34" ry="38" fill="url(#hel)"/>`;
  const face = `<g clip-path="url(#face)"><rect x="30" y="36" width="60" height="44" fill="url(#skin)"/>${faceVis < 0.08 ? '' : `<g opacity="${faceVis}"><ellipse cx="48.5" cy="54" rx="4.2" ry="2.6" fill="#f2efe8"/><ellipse cx="71.5" cy="54" rx="4.2" ry="2.6" fill="#f2efe8"/><circle cx="49" cy="54" r="2" fill="#3b2a1c"/><circle cx="71" cy="54" r="2" fill="#3b2a1c"/><circle cx="49.6" cy="53.4" r=".7" fill="#fff"/><circle cx="71.6" cy="53.4" r=".7" fill="#fff"/><path d="M43 49.5q5.5-3.2 11 0M66 49.5q5.5-3.2 11 0" stroke="#4a3322" stroke-width="1.6" fill="none" stroke-linecap="round"/></g>`}</g>`;
  const facePath = 'M33 52C33 42 44 38 60 38S87 42 87 52v9c0 8-12 13-27 13S33 69 33 61z';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 140"><defs>
<radialGradient id="bg" cx=".5" cy=".35" r=".8"><stop offset="0" stop-color="#3f505c"/><stop offset="1" stop-color="#0e1419"/></radialGradient>
<linearGradient id="suit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mix(p.suit, 0.22)}"/><stop offset="1" stop-color="${mix(p.suit, -0.38)}"/></linearGradient>
<linearGradient id="suit2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${mix(p.suit2, 0.18)}"/><stop offset="1" stop-color="${mix(p.suit2, -0.3)}"/></linearGradient>
<radialGradient id="hel" cx=".36" cy=".26" r=".9"><stop offset="0" stop-color="${mix(p.helmet, 0.55)}"/><stop offset=".42" stop-color="${hex(p.helmet)}"/><stop offset="1" stop-color="${mix(p.helmet, -0.55)}"/></radialGradient>
<linearGradient id="vis" x1="0" y1="0" x2=".35" y2="1"><stop offset="0" stop-color="${mix(p.visor, 0.3)}" stop-opacity="${tintOp}"/><stop offset="1" stop-color="${mix(p.visor, -0.35)}" stop-opacity="${Math.min(1, tintOp + 0.12)}"/></linearGradient>
<linearGradient id="mir" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfe6ff" stop-opacity=".55"/><stop offset=".48" stop-color="#cfe6ff" stop-opacity=".12"/><stop offset=".5" stop-color="#2a3a2a" stop-opacity=".35"/><stop offset="1" stop-color="#101810" stop-opacity=".5"/></linearGradient>
<linearGradient id="mask" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#454c47"/><stop offset="1" stop-color="#1a1e1c"/></linearGradient>
<linearGradient id="met" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e8ecf0"/><stop offset="1" stop-color="#6c737b"/></linearGradient>
<radialGradient id="skin" cx=".5" cy=".4" r=".7"><stop offset="0" stop-color="#d6a984"/><stop offset="1" stop-color="#8e6446"/></radialGradient>
<clipPath id="face"><path d="${facePath}"/></clipPath>
<clipPath id="hc"><ellipse cx="60" cy="${press ? 50 : 52}" rx="${press ? 37 : 34}" ry="${press ? 41 : 38}"/></clipPath>
</defs>
<rect width="120" height="140" fill="url(#bg)"/>
<path d="M-4 30C20 8 40-2 60-2s40 10 64 32M-4 70C14 54 30 46 44 42" stroke="#5a6b78" stroke-width="2" fill="none" opacity=".3"/>
<path d="M4 140c1-27 20-41 46-45h20c26 4 45 18 46 45z" fill="url(#suit)"/>
<path d="M12 128c2-16 16-28 36-32l-8 44h-28zM108 128c-2-16-16-28-36-32l8 44h28z" fill="url(#suit2)" opacity=".85"/>
<path d="M4 140c1-27 20-41 46-45" stroke="#000" stroke-opacity=".28" stroke-width="1.5" fill="none"/>
<path d="M60 100v40" stroke="#000" stroke-opacity=".25" stroke-width="1"/><path d="M58.6 102v38M61.4 102v38" stroke="#fff" stroke-opacity=".12" stroke-width=".6" stroke-dasharray="2 1.6"/>
${press ? '<ellipse cx="60" cy="96" rx="25" ry="7" fill="#aab2ba" stroke="#6c737b" stroke-width="1.4"/><circle cx="40" cy="97" r="3.6" fill="' + a + '"/><circle cx="80" cy="97" r="3.6" fill="' + a + '"/>' : `<ellipse cx="60" cy="97" rx="19" ry="6.5" fill="${mix(p.suit2, -0.2)}"/><path d="M50 94c3 6 17 6 20 0v6c-4 5-16 5-20 0z" fill="url(#skin)"/>`}
<path d="M30 100l10 40h-11l-11-34z M90 100l-10 40h11l11-34z" fill="#25282c"/><path d="M33 104l9 34M87 104l-9 34" stroke="#6e747b" stroke-width=".8" stroke-dasharray="2 2.2" fill="none"/>
<rect x="38" y="119" width="44" height="5" fill="#25282c"/><rect x="54" y="115.5" width="12" height="12" rx="2" fill="url(#met)" stroke="#3b4147" stroke-width=".8"/><rect x="57.5" y="119" width="5" height="5" fill="#2a2e33"/>
${patch}
<rect x="80" y="128" width="20" height="9" rx="1.5" fill="${mix(p.suit2, -0.1)}" stroke="#000" stroke-opacity=".3" stroke-width=".6"/><text x="90" y="134.2" font-family="monospace" font-size="4.4" font-weight="bold" text-anchor="middle" fill="${hex(p.accent)}">${p.callsign || ''}</text>
<path d="M44 77c-9 6-16 18-14 32 1 6 6 8 8 4-2-10 1-20 9-26" fill="none" stroke="#1d2520" stroke-width="5" stroke-linecap="round"/>
<path d="M44 77c-9 6-16 18-14 32" fill="none" stroke="#56635a" stroke-width="5" stroke-linecap="round" stroke-dasharray="1.2 2.6" opacity=".7"/>
${helmetBody}
<g clip-path="url(#hc)">${livery}</g>
${press ? '' : `<ellipse cx="25.5" cy="63" rx="5.2" ry="10" fill="#2b2f35" stroke="#4a5058" stroke-width="1"/><ellipse cx="94.5" cy="63" rx="5.2" ry="10" fill="#2b2f35" stroke="#4a5058" stroke-width="1"/>`}
<path d="M30 40C34 26 46 18 60 18s26 8 30 22" stroke="#fff" stroke-opacity=".42" stroke-width="2" fill="none" stroke-linecap="round"/>
<path d="M30 49c4-12 16-15 30-15s26 3 30 15v3c-4-8-16-11-30-11S34 44 30 52z" fill="#15181b" opacity=".92"/>
${face}
<path d="${facePath}" fill="url(#vis)" stroke="#0c0e10" stroke-width="2"/>
${mirror ? `<path d="${facePath}" fill="url(#mir)"/><path d="M38 66h44" stroke="#fff" stroke-opacity=".18" stroke-width=".8"/>` : ''}
<path d="M38 47c5-5 14-7 22-7M70 41c7 1 12 4 15 8" stroke="#fff" stroke-opacity="${mirror ? 0.7 : 0.45}" stroke-width="2.2" fill="none" stroke-linecap="round"/>
<path d="M43 64c6-3 28-3 34 0l3 10c-4 12-13 17-20 17s-16-5-20-17z" fill="url(#mask)" stroke="#0c0e10" stroke-width="1"/>
<circle cx="60" cy="79" r="4.5" fill="#101214" stroke="#555d58" stroke-width="1.2"/><path d="M56 79h8M60 75v8" stroke="#3a403c" stroke-width=".8"/>
<rect x="37" y="62" width="7" height="6" rx="1.5" fill="url(#met)"/><rect x="76" y="62" width="7" height="6" rx="1.5" fill="url(#met)"/>
<path d="M44 66c4-2 8-2.5 12-2.5" stroke="#fff" stroke-opacity=".18" stroke-width="1.5" fill="none" stroke-linecap="round"/>
<path d="M52 91l-8 9" stroke="#2a2e33" stroke-width="2" stroke-linecap="round"/><circle cx="43.5" cy="100.5" r="2" fill="${a}"/>
</svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}
