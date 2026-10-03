'use strict';
// ONCOVAULT teaser (BigOHealth). 40 s, 16:9, built in the OncoVault design system: deep-green
// photographic depth, frosted-glass cards, Lora serif headlines with a mint second line, Outfit UI type.
// Every frame is a pure function of time t. 96 BPM: 1 beat = 0.625 s, 1 bar = 2.5 s, 16 bars.
// Cue times are mirrored in audio.py.

const W = 1920, H = 1080, DUR = 40;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 60);
const MB = +(Q.get('mb') || (RENDER ? 4 : 1));
const SHUTTER = 0.5;

const C = {
  bg0: '#03190F', bg1: '#0B3A2B', mint: '#5DD6A8', mintHi: '#8CEBC6', green: '#13A878', deep: '#0B4A35',
  white: '#FFFFFF', muted: '#C3D4CC', muted2: '#8FAA9F', warm: '#F0C27E',
};

// ------------------------------------------------------------------ math
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const inv = (a, b, x) => clamp((x - a) / (b - a));
const TAU = Math.PI * 2;
function bez(x1, y1, x2, y2) {
  const f = (a, b, t) => 3 * a * t * (1 - t) * (1 - t) + 3 * b * t * t * (1 - t) + t * t * t;
  return x => {
    if (x <= 0) return 0; if (x >= 1) return 1;
    let lo = 0, hi = 1, t = x;
    for (let i = 0; i < 22; i++) { t = (lo + hi) / 2; if (f(x1, x2, t) < x) lo = t; else hi = t; }
    return f(y1, y2, t);
  };
}
const E = { out: bez(0.16, 1, 0.3, 1), io: bez(0.65, 0, 0.35, 1), inn: bez(0.55, 0, 1, 0.45), std: bez(0.25, 0.1, 0.25, 1) };
function spring(t, f = 1.4, z = 0.62) {
  if (t <= 0) return 0;
  const w = TAU * f, wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t));
}
function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
const P = (t, t0, d = 0.9, e = E.out) => e(inv(t0, t0 + d, t));
function rgba(h, a) { const n = parseInt(h.slice(1), 16); return `rgba(${n >> 16},${n >> 8 & 255},${n & 255},${a})`; }

// ------------------------------------------------------------------ canvas helpers
function mk(w = W, h = H) { const c = document.createElement('canvas'); c.width = w; c.height = h; c.g = c.getContext('2d'); return c; }
const SERIF = 'Lora, Georgia, serif', SANS = 'Outfit, "Helvetica Neue", Arial, sans-serif';
function font(g, fam, px, w = 500, track = null) {
  g.font = `${w} ${px}px ${fam === 'serif' ? SERIF : SANS}`;
  g.letterSpacing = (track == null ? (fam === 'serif' ? -px * 0.012 : 0) : track) + 'px';
}
function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function blur(g, b) { g.filter = b > 0.35 ? `blur(${b.toFixed(2)}px)` : 'none'; }

// Words blur up into place one after another.
// o: fam, size, w, col, stagger, dur, dy, bl, a, align, out, colFor(i) (per-word colour)
function words(g, str, x, y, t, t0, o = {}) {
  const size = o.size || 80;
  font(g, o.fam || 'serif', size, o.w || 700, o.track);
  const parts = str.split(' ');
  const sp = g.measureText(' ').width;
  const ws = parts.map(p => g.measureText(p).width);
  const total = ws.reduce((a, b) => a + b, 0) + sp * (parts.length - 1);
  let cx = o.align === 'l' ? x : o.align === 'r' ? x - total : x - total / 2;
  g.textBaseline = 'alphabetic'; g.textAlign = 'left';
  const out = o.out || 0;
  for (let i = 0; i < parts.length; i++) {
    const p = P(t, t0 + i * (o.stagger ?? 0.09), o.dur || 1.0);
    const q = out > 0 ? E.inn(clamp(out * 1.25 - i * 0.04)) : 0;
    if (p > 0.001 && q < 0.999) {
      g.save();
      g.globalAlpha = (o.a ?? 1) * clamp(p * 1.3) * (1 - q);
      blur(g, (1 - p) * (o.bl ?? 12) + q * 12);
      g.fillStyle = o.colFor ? o.colFor(i) : (o.col || C.white);
      if (o.glow) { g.shadowColor = rgba(C.mint, o.glow); g.shadowBlur = size * 0.4; }
      g.fillText(parts[i], cx, y + (1 - p) * (o.dy ?? size * 0.3) - q * size * 0.2);
      g.restore();
    }
    cx += ws[i] + sp;
  }
  return total;
}
// the design's divider: hairlines fading out from a mint dot
function divider(g, x, y, w, p, a = 1) {
  if (p <= 0) return;
  g.save(); g.globalAlpha = a;
  const half = w / 2 * p;
  const gr = g.createLinearGradient(x - half, 0, x + half, 0);
  gr.addColorStop(0, rgba(C.mint, 0)); gr.addColorStop(0.5, rgba(C.mint, 0.55)); gr.addColorStop(1, rgba(C.mint, 0));
  g.fillStyle = gr; g.fillRect(x - half, y - 0.75, half * 2, 1.5);
  g.fillStyle = C.mint; g.shadowColor = rgba(C.mint, 0.8); g.shadowBlur = 12;
  g.beginPath(); g.arc(x, y, 5.5 * clamp(p * 2), 0, TAU); g.fill();
  g.restore();
}

// ------------------------------------------------------------------ background: deep green room, warm window bokeh
const bokehA = mk(1100, 620), bokehB = mk(1100, 620);
(() => {
  const paint = (cv, n, rmin, rmax, bl, seed) => {
    const g = cv.g; g.filter = `blur(${bl}px)`;
    for (let i = 0; i < n; i++) {
      const u = hash(i * 3.7 + seed), v = hash(i * 9.1 + seed * 2), s = hash(i * 1.3 + seed * 3);
      const warm = hash(i * 5.5 + seed) < 0.55;
      const x = u * 1100, y = 40 + v * 420 * (warm ? 0.8 : 1.2);
      const r = lerp(rmin, rmax, s);
      g.fillStyle = warm ? `rgba(240,194,126,${lerp(0.10, 0.32, hash(i + seed))})` : `rgba(110,190,150,${lerp(0.08, 0.22, hash(i * 2 + seed))})`;
      g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill();
    }
  };
  paint(bokehA, 46, 8, 34, 5, 1);
  paint(bokehB, 16, 40, 110, 22, 7);
})();
function background(g, t, warmth = 1) {
  const base = g.createRadialGradient(W * 0.5, H * 0.32, 60, W * 0.5, H * 0.45, W * 0.75);
  base.addColorStop(0, '#1A4A38'); base.addColorStop(0.45, '#0B3326'); base.addColorStop(1, C.bg0);
  g.fillStyle = base; g.fillRect(0, 0, W, H);
  // window light
  const wl = g.createRadialGradient(W * 0.47, H * 0.18, 0, W * 0.47, H * 0.18, W * 0.42);
  wl.addColorStop(0, `rgba(240,200,140,${0.20 * warmth})`); wl.addColorStop(1, 'rgba(240,200,140,0)');
  g.fillStyle = wl; g.fillRect(0, 0, W, H);
  g.save();
  g.globalAlpha = 0.85 * warmth;
  g.drawImage(bokehB, -60 + Math.sin(t * 0.07) * 40, -40 + Math.cos(t * 0.05) * 20, W + 160, H * 0.95);
  g.globalAlpha = 0.75 * warmth;
  g.drawImage(bokehA, -100 + Math.sin(t * 0.11 + 1) * 70, -20 + Math.cos(t * 0.09) * 26, W + 200, H * 0.9);
  g.restore();
  // floor-to-ceiling green haze + vignette
  const fl = g.createLinearGradient(0, H * 0.45, 0, H);
  fl.addColorStop(0, 'rgba(3,25,15,0)'); fl.addColorStop(1, 'rgba(3,25,15,0.85)');
  g.fillStyle = fl; g.fillRect(0, 0, W, H);
  const vg = g.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, W * 0.72);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,10,6,0.65)');
  g.fillStyle = vg; g.fillRect(0, 0, W, H);
}
const bgFrame = mk();   // current background, used for the glass backdrop blur

// frosted glass card: blurred backdrop + tint + sheen + hairline border
function glass(g, x, y, w, h, r, a = 1, o = {}) {
  if (a <= 0.003) return;
  g.save(); g.globalAlpha = a;
  g.shadowColor = 'rgba(0,12,7,0.45)'; g.shadowBlur = 50; g.shadowOffsetY = 18;
  g.fillStyle = 'rgba(8,40,29,0.35)'; rr(g, x, y, w, h, r); g.fill();
  g.shadowColor = 'transparent';
  g.save(); rr(g, x, y, w, h, r); g.clip();
  if (!o.noBackdrop) {
    const m = 40;
    const tr = g.getTransform();
    // map the card rect to frame pixels so the backdrop lines up under any transform
    g.setTransform(1, 0, 0, 1, 0, 0);
    const bx = tr.a * x + tr.e, by = tr.d * y + tr.f, bw = tr.a * w, bh = tr.d * h;
    g.filter = 'blur(16px)';
    g.drawImage(bgFrame, bx - m, by - m, bw + 2 * m, bh + 2 * m, bx - m, by - m, bw + 2 * m, bh + 2 * m);
    g.filter = 'none';
    g.setTransform(tr);
  }
  g.fillStyle = 'rgba(160,230,200,0.075)'; g.fillRect(x, y, w, h);
  const sh = g.createLinearGradient(x, y, x, y + h);
  sh.addColorStop(0, 'rgba(255,255,255,0.10)'); sh.addColorStop(0.35, 'rgba(255,255,255,0.02)'); sh.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = sh; g.fillRect(x, y, w, h);
  g.restore();
  g.strokeStyle = 'rgba(200,240,222,0.22)'; g.lineWidth = 1.5; rr(g, x, y, w, h, r); g.stroke();
  g.restore();
}

// ------------------------------------------------------------------ icons (line style, centred at 0,0, size ~1)
function icon(g, kind, x, y, s, col) {
  g.save(); g.translate(x, y); g.scale(s, s);
  g.strokeStyle = col; g.fillStyle = col; g.lineWidth = 2 / s * (s / 14); g.lineWidth = 0.13; g.lineCap = 'round'; g.lineJoin = 'round';
  g.beginPath();
  switch (kind) {
    case 'diagnosis':   // magnifier
      g.arc(-0.12, -0.12, 0.42, 0, TAU); g.moveTo(0.2, 0.2); g.lineTo(0.58, 0.58); g.stroke(); break;
    case 'surgery':     // scalpel
      g.moveTo(-0.6, 0.6); g.lineTo(0.05, -0.05); g.moveTo(0.05, -0.05); g.quadraticCurveTo(0.55, -0.6, 0.62, -0.62); g.quadraticCurveTo(0.45, -0.1, 0.18, 0.08); g.closePath(); g.stroke(); break;
    case 'radiation':   // trefoil
      g.arc(0, 0, 0.12, 0, TAU); g.fill();
      for (let k = 0; k < 3; k++) { const a = -Math.PI / 2 + k * TAU / 3; g.beginPath(); g.moveTo(0, 0); g.arc(0, 0, 0.6, a - 0.5, a + 0.5); g.closePath(); g.globalAlpha *= 1; g.fill(); }
      g.globalCompositeOperation = 'destination-out'; g.beginPath(); g.arc(0, 0, 0.22, 0, TAU); g.fill(); g.globalCompositeOperation = 'source-over';
      g.beginPath(); g.arc(0, 0, 0.1, 0, TAU); g.fill(); break;
    case 'chemo':       // IV drop
      g.moveTo(0, -0.62); g.bezierCurveTo(0.2, -0.3, 0.45, 0, 0.45, 0.2); g.arc(0, 0.2, 0.45, 0, Math.PI); g.bezierCurveTo(-0.45, 0, -0.2, -0.3, 0, -0.62); g.stroke();
      g.beginPath(); g.moveTo(-0.15, 0.15); g.lineTo(0.15, 0.15); g.moveTo(0, 0); g.lineTo(0, 0.3); g.stroke(); break;
    case 'molecular':   // DNA helix
      for (let k = 0; k < 2; k++) { g.beginPath(); for (let i = 0; i <= 20; i++) { const u = i / 20, yy = -0.62 + u * 1.24, xx = Math.sin(u * TAU * 1.1 + k * Math.PI) * 0.36; i ? g.lineTo(xx, yy) : g.moveTo(xx, yy); } g.stroke(); }
      for (let i = 1; i < 6; i++) { const u = i / 6, yy = -0.62 + u * 1.24, xx = Math.sin(u * TAU * 1.1) * 0.36; g.beginPath(); g.moveTo(xx, yy); g.lineTo(-xx, yy); g.globalAlpha *= 0.6; g.stroke(); g.globalAlpha /= 0.6; } break;
    case 'targeted':    // target
      g.arc(0, 0, 0.58, 0, TAU); g.stroke(); g.beginPath(); g.arc(0, 0, 0.32, 0, TAU); g.stroke(); g.beginPath(); g.arc(0, 0, 0.1, 0, TAU); g.fill(); break;
    case 'calendar':
      g.roundRect(-0.55, -0.45, 1.1, 1.0, 0.15); g.moveTo(-0.55, -0.12); g.lineTo(0.55, -0.12); g.moveTo(-0.25, -0.62); g.lineTo(-0.25, -0.35); g.moveTo(0.25, -0.62); g.lineTo(0.25, -0.35); g.stroke(); break;
    case 'sparkle':
      for (let k = 0; k < 4; k++) { const a = k * TAU / 4, b = a + TAU / 8; if (!k) g.moveTo(Math.cos(a) * 0.6, Math.sin(a) * 0.6); g.quadraticCurveTo(Math.cos(b) * 0.1, Math.sin(b) * 0.1, Math.cos(a + TAU / 4) * 0.6, Math.sin(a + TAU / 4) * 0.6); }
      g.closePath(); g.stroke(); break;
    case 'shield':
      g.moveTo(0, -0.62); g.lineTo(0.5, -0.42); g.lineTo(0.5, 0.02); g.quadraticCurveTo(0.45, 0.45, 0, 0.64); g.quadraticCurveTo(-0.45, 0.45, -0.5, 0.02); g.lineTo(-0.5, -0.42); g.closePath(); g.stroke(); break;
  }
  g.restore();
}

// ------------------------------------------------------------------ OncoVault mark: 8 awareness ribbons around a keyhole
function ribbonsMark(g, x, y, R, t, prog = 1, col = C.green) {
  // prog 0..1 assembles: core, then ribbons in sequence, then outer dots
  g.save(); g.translate(x, y);
  const core = E.out(clamp(prog / 0.25));
  if (core > 0) {
    g.save(); g.scale(core, core);
    g.fillStyle = col; g.beginPath(); g.arc(0, 0, R * 0.19, 0, TAU); g.fill();
    g.fillStyle = C.bg0; g.globalCompositeOperation = 'destination-out';
    g.beginPath(); g.arc(0, -R * 0.03, R * 0.045, 0, TAU); g.fill();
    g.beginPath(); g.moveTo(-R * 0.022, -R * 0.02); g.lineTo(R * 0.022, -R * 0.02); g.lineTo(R * 0.03, R * 0.085); g.lineTo(-R * 0.03, R * 0.085); g.closePath(); g.fill();
    g.restore();
  }
  for (let k = 0; k < 8; k++) {
    const kp = E.out(clamp((prog - 0.15 - k * 0.055) / 0.3));
    if (kp <= 0) continue;
    const a = -Math.PI / 2 + k * TAU / 8;
    g.save(); g.rotate(a + Math.PI / 2 + (1 - kp) * 0.6); g.scale(kp, kp);
    // in this frame the ribbon points "up" (outward = -y): loop inward, tails splaying outward in a wide V
    g.strokeStyle = col; g.lineWidth = R * 0.088; g.lineCap = 'butt';
    const ly = -R * 0.47, lr = R * 0.112;
    g.beginPath(); g.arc(0, ly, lr, 0, TAU); g.stroke();
    const cy = ly - lr * 1.05, L = R * 0.39, sa = 0.74;
    g.lineWidth = R * 0.1;
    g.beginPath();
    g.moveTo(Math.sin(sa) * R * 0.05, cy + Math.cos(sa) * R * 0.05); g.lineTo(-Math.sin(sa) * L, cy - Math.cos(sa) * L);
    g.moveTo(-Math.sin(sa) * R * 0.05, cy + Math.cos(sa) * R * 0.05); g.lineTo(Math.sin(sa) * L, cy - Math.cos(sa) * L);
    g.stroke();
    const dp = E.out(clamp((prog - 0.55 - k * 0.04) / 0.25));
    if (dp > 0) { g.fillStyle = col; g.beginPath(); g.arc(0, -R * 0.99, R * 0.072 * dp, 0, TAU); g.fill(); }
    g.restore();
  }
  g.restore();
}
function wordmark(g, x, y, size, t, t0, o = {}) {
  font(g, 'sans', size, 600, -size * 0.01);
  const s = 'OncoVault', tw = g.measureText(s).width;
  let cx = x - tw / 2;
  g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  for (let i = 0; i < s.length; i++) {
    const p = P(t, t0 + i * 0.045, 1.0);
    cx = x - tw / 2 + g.measureText(s.slice(0, i + 1)).width - g.measureText(s[i]).width;
    if (p > 0) {
      g.save(); g.globalAlpha = clamp(p * 1.4) * (o.a ?? 1); blur(g, (1 - p) * 10);
      g.fillStyle = i < 4 ? C.white : C.mint;
      if (o.glow) { g.shadowColor = rgba(C.mint, o.glow); g.shadowBlur = size * 0.35; }
      g.fillText(s[i], cx, y + (1 - p) * size * 0.25);
      g.restore();
    }
  }
  return tw;
}

// ================================================================== SCENES
// 01 (0–7.5): Something big is coming from BigOHealth / under the mentorship of Dr. Nitesh Rohatgi
function sOpen(g, t) {
  const z = 1 + t * 0.006;
  g.save(); g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
  words(g, 'Something big is coming', W / 2, 470, t, 0.6, { size: 104, stagger: 0.14, dur: 1.2 });
  words(g, 'from BigOHealth', W / 2, 590, t, 2.1, { size: 104, stagger: 0.14, dur: 1.2, colFor: i => i ? C.mint : C.white, glow: 0 });
  divider(g, W / 2, 668, 520, P(t, 3.5, 1.2, E.io));
  words(g, 'under the mentorship of', W / 2, 752, t, 4.1, { fam: 'sans', size: 36, w: 400, col: C.muted, stagger: 0.06 });
  words(g, 'Dr. Nitesh Rohatgi', W / 2, 830, t, 4.7, { size: 58, w: 600, stagger: 0.1 });
  g.restore();
}

// 02 (7.5–20): The entire cancer journey -> six stages on a timeline -> one glass timeline card
const STAGES = [
  { k: 'diagnosis', title: 'Diagnosis', sub: 'Biopsy · Staging', date: 'Jan 12, 2024' },
  { k: 'surgery', title: 'Surgery', sub: 'Lumpectomy + SLNB', date: 'Feb 02, 2024' },
  { k: 'radiation', title: 'Radiation', sub: '40 Gy / 15 fractions', date: 'Mar 10, 2024' },
  { k: 'chemo', title: 'Chemotherapy', sub: 'AC → Paclitaxel', date: 'May 20, 2024' },
  { k: 'molecular', title: 'Molecular', sub: 'NGS · Biomarkers', date: 'Aug 05, 2024' },
  { k: 'targeted', title: 'Targeted Therapy', sub: 'HER2-directed', date: 'Sep 18, 2024' },
];
const NODE_T = [10.0, 10.625, 12.5, 13.125, 15.0, 15.625];
const PAIRS = [[10.0, 'From', 'diagnosis', 'to', 'surgery,'], [12.5, '', 'radiation', 'to', 'chemotherapy,'], [15.0, '', 'molecular', 'to', 'targeted therapy']];
const MORPH = 17.5;
const LX0 = 190, LX1 = 1730, LY = 610;
const nodeX = i => LX0 + (i + 0.5) * (LX1 - LX0) / 6;
// card geometry (centre) and as-hero (left) placement
const CARD = { w: 660, h: 700, x: W / 2 - 330, y: 320 };
function rowY(i) { return CARD.y + 128 + i * 92; }
function timelineCard(g, t, morph, cardA, rowsT) {
  // card shell
  glass(g, CARD.x, CARD.y, CARD.w, CARD.h, 30, cardA);
  if (cardA > 0.01) {
    g.save(); g.globalAlpha = cardA;
    icon(g, 'calendar', CARD.x + 52, CARD.y + 58, 26, C.mint);
    font(g, 'sans', 32, 600); g.fillStyle = C.white; g.textAlign = 'left'; g.textBaseline = 'middle';
    g.fillText('Treatment Timeline', CARD.x + 84, CARD.y + 58);
    g.strokeStyle = C.muted; g.lineWidth = 2.5; g.lineCap = 'round';
    g.beginPath(); g.moveTo(CARD.x + CARD.w - 50, CARD.y + 48); g.lineTo(CARD.x + CARD.w - 40, CARD.y + 58); g.lineTo(CARD.x + CARD.w - 50, CARD.y + 68); g.stroke();
    g.fillStyle = 'rgba(255,255,255,0.10)'; g.fillRect(CARD.x + 28, CARD.y + 100, CARD.w - 56, 1);
    // vertical track
    const vx = CARD.x + 50, y0 = rowY(0), y1 = rowY(5);
    g.fillStyle = rgba(C.mint, 0.35); g.fillRect(vx - 1, y0, 2, (y1 - y0) * clamp(morph));
    g.restore();
  }
}
function sJourney(g, t) {
  // headline + rolling subline
  const hOut = P(t, 19.2, 0.6, E.io);
  words(g, 'The entire cancer journey', W / 2, 185, t, 7.8, { size: 92, stagger: 0.12, out: hOut });
  const morph = E.io(inv(MORPH, MORPH + 1.5, t));
  // subline phrases: "From diagnosis to surgery," ... then "together in a single longitudinal timeline."
  for (let k = 0; k < PAIRS.length; k++) {
    const [t0, a, b, c, d] = PAIRS[k];
    const t1 = k < PAIRS.length - 1 ? PAIRS[k + 1][0] : MORPH;
    const pin = P(t, t0, 0.7), pout = P(t, t1 - 0.15, 0.45, E.io);
    if (pin <= 0 || pout >= 1) continue;
    const str = [a, b, c, d].filter(Boolean).join(' ');
    const mintW = new Set([b.toLowerCase(), ...d.replace(',', '').split(' ')]);
    g.save(); g.globalAlpha = clamp(pin * 1.3) * (1 - pout); blur(g, (1 - pin) * 10 + pout * 10);
    font(g, 'sans', 44, 400); g.textBaseline = 'alphabetic'; g.textAlign = 'left';
    const ws = str.split(' '), sp = g.measureText(' ').width;
    const tot = ws.reduce((s, w) => s + g.measureText(w).width, 0) + sp * (ws.length - 1);
    let x = W / 2 - tot / 2;
    const y = 278 + (1 - pin) * 30 - pout * 30;
    for (const w of ws) { const key = w.replace(',', '').toLowerCase(); g.fillStyle = mintW.has(key) || key === 'therapy' && d.includes('therapy') ? C.mint : C.muted; g.fillText(w, x, y); x += g.measureText(w).width + sp; }
    g.restore();
  }
  words(g, 'together in a single longitudinal timeline.', W / 2, 278, t, MORPH + 0.1, { fam: 'sans', size: 44, w: 400, colFor: i => i >= 3 ? C.mint : C.muted, stagger: 0.07, out: P(t, 19.2, 0.6, E.io) });

  // horizontal track + progress
  const trackA = P(t, 8.8, 0.8) * (1 - morph);
  const prog = E.io(inv(9.0, 16.2, t));
  if (trackA > 0.002) {
    g.save(); g.globalAlpha = trackA;
    const drawn = E.io(inv(8.8, 10.0, t));
    g.fillStyle = 'rgba(255,255,255,0.14)'; g.fillRect(LX0, LY - 1, (LX1 - LX0) * drawn, 2);
    const px = lerp(LX0, nodeX(5), prog);
    const gr = g.createLinearGradient(LX0, 0, px, 0); gr.addColorStop(0, rgba(C.mint, 0.1)); gr.addColorStop(1, C.mint);
    g.fillStyle = gr; g.fillRect(LX0, LY - 1.5, px - LX0, 3);
    g.shadowColor = C.mint; g.shadowBlur = 24; g.fillStyle = C.mintHi; g.beginPath(); g.arc(px, LY, 6, 0, TAU); g.fill();
    g.restore();
  }
  const cardA = morph;
  timelineCard(g, t, morph, cardA);
  // nodes + chips: horizontal layout -> card rows
  STAGES.forEach((s, i) => {
    const p = spring(t - NODE_T[i], 1.3, 0.7);
    if (p <= 0.001) return;
    const a = clamp((t - NODE_T[i]) / 0.3);
    const m = E.io(inv(MORPH + i * 0.06, MORPH + 1.1 + i * 0.06, t));
    const up = i % 2 === 0;
    // horizontal chip geometry
    const cw = 250, ch = 112;
    const hx = nodeX(i) - cw / 2, hy = up ? LY - 56 - ch : LY + 56;
    // row geometry inside the card
    const rx = CARD.x + 88, ry = rowY(i) - 34, rw = CARD.w - 120, rh = 72;
    const x = lerp(hx, rx, m), y = lerp(hy + (1 - p) * (up ? 40 : -40), ry, m), w = lerp(cw, rw, m), h = lerp(ch, rh, m);
    // stem + node dot
    const ndx = lerp(nodeX(i), CARD.x + 50, m), ndy = lerp(LY, rowY(i), m);
    g.save(); g.globalAlpha = a;
    if (m < 1) {
      g.globalAlpha = a * (1 - m);
      g.fillStyle = rgba(C.mint, 0.5);
      if (up) g.fillRect(nodeX(i) - 0.75, LY - 56 * p, 1.5, 56 * p); else g.fillRect(nodeX(i) - 0.75, LY, 1.5, 56 * p);
      g.globalAlpha = a;
    }
    g.shadowColor = rgba(C.mint, 0.9); g.shadowBlur = 18;
    g.fillStyle = C.mint; g.beginPath(); g.arc(ndx, ndy, 9 * clamp(p), 0, TAU); g.fill();
    g.shadowBlur = 0; g.strokeStyle = rgba(C.mint, 0.35 * (1 - m)); g.lineWidth = 2;
    g.beginPath(); g.arc(ndx, ndy, 9 + 12 * clamp((t - NODE_T[i]) / 0.8), 0, TAU); g.globalAlpha = a * (1 - clamp((t - NODE_T[i]) / 0.8)); g.stroke();
    g.restore();
    // chip glass fades into the card
    glass(g, x, y, w, h, lerp(22, 14, m), a * (1 - m), { noBackdrop: m > 0.5 });
    g.save(); g.globalAlpha = a;
    const ic = lerp(28, 0, m);
    if (ic > 1) {
      g.fillStyle = rgba(C.mint, 0.16 * (1 - m)); g.beginPath(); g.arc(x + 46, y + h / 2, ic, 0, TAU); g.fill();
      icon(g, s.k, x + 46, y + h / 2, 30 * (1 - m), C.mint);
    }
    const tx = lerp(x + 88, CARD.x + 250, m);
    font(g, 'sans', lerp(28, 27, m), 600); g.fillStyle = C.white; g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    g.fillText(s.title, tx, y + h / 2 - lerp(4, 2, m));
    font(g, 'sans', lerp(21, 22, m), 400); g.fillStyle = C.muted;
    g.fillText(s.sub, tx, y + h / 2 + lerp(28, 28, m));
    if (m > 0) {
      g.globalAlpha = a * m;
      font(g, 'sans', 22, 400); g.fillStyle = C.muted2;
      g.fillText(s.date, CARD.x + 82, rowY(i) + 8);
    }
    g.restore();
  });
}

// 03 (20–27.5): One patient. One treatment timeline. Card to the left, 60-second summary + guard to the right
function heroCardPlacement(t) {
  const k = E.io(inv(20.0, 21.4, t));
  return { k, s: lerp(1, 0.78, k), cx: lerp(W / 2, 64 + CARD.w * 0.78 / 2, k), cy: lerp(CARD.y + CARD.h / 2, 420 + CARD.h * 0.78 / 2, k) };
}
function sOne(g, t) {
  const pl = heroCardPlacement(t);
  // keep the timeline card (fully morphed) on screen, moving into the hero layout
  g.save();
  g.translate(pl.cx, pl.cy); g.scale(pl.s, pl.s); g.translate(-(CARD.x + CARD.w / 2), -(CARD.y + CARD.h / 2));
  timelineCard(g, t, 1, 1);
  STAGES.forEach((s, i) => {
    g.save();
    g.fillStyle = C.mint; g.shadowColor = rgba(C.mint, 0.9); g.shadowBlur = 18;
    g.beginPath(); g.arc(CARD.x + 50, rowY(i), 9, 0, TAU); g.fill(); g.shadowBlur = 0;
    font(g, 'sans', 27, 600); g.fillStyle = C.white; g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    g.fillText(s.title, CARD.x + 250, rowY(i) - 34 + 36 - 2);
    font(g, 'sans', 22, 400); g.fillStyle = C.muted; g.fillText(s.sub, CARD.x + 250, rowY(i) - 34 + 36 + 28);
    font(g, 'sans', 22, 400); g.fillStyle = C.muted2; g.fillText(s.date, CARD.x + 82, rowY(i) + 8);
    g.restore();
  });
  g.restore();
  // headline (design hero style)
  words(g, 'One patient.', W / 2, 190, t, 20.3, { size: 112, stagger: 0.14, dur: 1.1 });
  words(g, 'One treatment timeline.', W / 2, 315, t, 21.3, { size: 112, col: C.mint, stagger: 0.12, dur: 1.1 });
  divider(g, W / 2, 380, 480, P(t, 22.0, 1.0, E.io));
  words(g, 'Every report. Every treatment. Every decision.', W / 2, 452, t, 22.4, { fam: 'sans', size: 36, w: 400, col: C.muted, stagger: 0.05 });
  // right column widgets
  const wx = W - 64 - 440;
  const s1 = spring(t - 22.4, 1.2, 0.72), s2 = spring(t - 23.0, 1.2, 0.72);
  if (s1 > 0.001) {
    const x = wx + (1 - s1) * 220, y = 520, a = clamp((t - 22.4) / 0.35);
    glass(g, x, y, 440, 220, 28, a);
    g.save(); g.globalAlpha = a;
    icon(g, 'sparkle', x + 40, y + 44, 24, C.mint);
    font(g, 'sans', 26, 600); g.fillStyle = C.white; g.textAlign = 'left'; g.textBaseline = 'middle'; g.fillText('60-Second Summary', x + 66, y + 44);
    const cx = x + 100, cy = y + 140, r = 54;
    const sec = Math.max(0, 60 - Math.floor(Math.max(0, t - 22.8) * 4));
    g.strokeStyle = 'rgba(255,255,255,0.12)'; g.lineWidth = 7; g.beginPath(); g.arc(cx, cy, r, 0, TAU); g.stroke();
    g.strokeStyle = C.mint; g.lineCap = 'round'; g.beginPath(); g.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + TAU * (sec / 60)); g.stroke();
    font(g, 'sans', 30, 600); g.fillStyle = C.white; g.textAlign = 'center'; g.fillText(`00:${String(sec).padStart(2, '0')}`, cx, cy - 4);
    font(g, 'sans', 13, 600, 1.5); g.fillStyle = C.muted; g.fillText('SEC', cx, cy + 22);
    g.fillStyle = 'rgba(255,255,255,0.12)'; g.fillRect(x + 186, y + 92, 1, 100);
    font(g, 'sans', 19, 400); g.fillStyle = C.muted; g.textAlign = 'left';
    ['AI-generated summary for', 'your next doctor', 'consultation or tumor', 'board.'].forEach((l, i) => g.fillText(l, x + 206, y + 104 + i * 26));
    g.restore();
  }
  if (s2 > 0.001) {
    const x = wx + (1 - s2) * 220, y = 764, a = clamp((t - 23.0) / 0.35);
    glass(g, x, y, 440, 252, 28, a);
    g.save(); g.globalAlpha = a;
    icon(g, 'shield', x + 40, y + 44, 26, C.mint);
    font(g, 'sans', 26, 600); g.fillStyle = C.white; g.textAlign = 'left'; g.textBaseline = 'middle'; g.fillText('OncoVault Guard', x + 66, y + 44);
    font(g, 'sans', 17, 600); const aw = g.measureText('Active').width + 28;
    g.fillStyle = rgba(C.green, 0.35); rr(g, x + 410 - aw, y + 30, aw, 30, 15); g.fill();
    g.fillStyle = C.mintHi; g.textAlign = 'center'; g.fillText('Active', x + 410 - aw / 2, y + 46);
    // shield with lock, pulsing ring
    const sx = x + 220, sy = y + 132, pulse = (t - 23.0) % 1.25 / 1.25;
    g.strokeStyle = rgba(C.mint, 0.5 * (1 - pulse)); g.lineWidth = 2; g.beginPath(); g.arc(sx, sy, 40 + pulse * 40, 0, TAU); g.stroke();
    g.save(); g.translate(sx, sy); g.scale(62, 62);
    g.fillStyle = rgba(C.green, 0.35); g.strokeStyle = C.mint; g.lineWidth = 0.09; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(0, -0.62); g.lineTo(0.5, -0.42); g.lineTo(0.5, 0.02); g.quadraticCurveTo(0.45, 0.45, 0, 0.64); g.quadraticCurveTo(-0.45, 0.45, -0.5, 0.02); g.lineTo(-0.5, -0.42); g.closePath(); g.fill(); g.stroke();
    g.strokeStyle = C.white; g.lineWidth = 0.08; g.beginPath(); g.arc(0, -0.06, 0.14, Math.PI, 0); g.stroke();
    g.fillStyle = C.white; rr(g, -0.22, -0.06, 0.44, 0.34, 0.06); g.fill();
    g.restore();
    font(g, 'sans', 19, 500); g.fillStyle = C.white; g.textAlign = 'left';
    g.fillText('Reports from another patient are', x + 32, y + 206); g.fillText('detected and blocked automatically.', x + 32, y + 232);
    g.restore();
  }
}

// 04+05 (27.5–40): brand reveal, then coming soon + closing line
function sBrand(g, t) {
  const lift = E.io(inv(32.3, 33.6, t));
  const markY = lerp(450, 250, lift), markR = lerp(185, 108, lift);
  // glow behind the mark
  const ga = P(t, 27.6, 1.4, E.io) * (0.8 - 0.3 * lift);
  if (ga > 0) {
    const gr = g.createRadialGradient(W / 2, markY, 0, W / 2, markY, markR * 3.2);
    gr.addColorStop(0, rgba(C.mint, 0.30 * ga)); gr.addColorStop(0.4, rgba(C.green, 0.10 * ga)); gr.addColorStop(1, rgba(C.green, 0));
    g.fillStyle = gr; g.fillRect(0, 0, W, H);
  }
  // expanding ring on assembly
  const rp = inv(27.7, 29.2, t);
  if (rp > 0 && rp < 1) { g.strokeStyle = rgba(C.mint, 0.45 * (1 - rp)); g.lineWidth = 2; g.beginPath(); g.arc(W / 2, markY, markR * (1 + rp * 1.4), 0, TAU); g.stroke(); }
  const prog = inv(27.6, 29.4, t);
  g.save(); g.shadowColor = rgba(C.mint, 0.5); g.shadowBlur = 30;
  ribbonsMark(g, W / 2, markY, markR, t, prog, C.mint);
  g.restore();
  const wmY = lerp(790, 440, lift), wmS = lerp(150, 92, lift);
  wordmark(g, W / 2, wmY, wmS, t, 29.0, { glow: 0.25 });
  words(g, 'by BigOHealth', W / 2, 870, t, 30.2, { fam: 'sans', size: 34, w: 400, col: C.muted, out: P(t, 32.0, 0.5, E.io) });
  // coming soon pill
  const cp = spring(t - 33.4, 1.3, 0.7), ca = clamp((t - 33.4) / 0.3);
  if (ca > 0) {
    font(g, 'sans', 28, 600, 3);
    const label = 'COMING SOON', lw = g.measureText(label).width, pw = lw + 92, ph = 62, px = W / 2 - pw / 2, py = 520;
    g.save(); g.translate(W / 2, py + ph / 2); g.scale(lerp(0.85, 1, cp), lerp(0.85, 1, cp)); g.translate(-W / 2, -(py + ph / 2));
    glass(g, px, py, pw, ph, ph / 2, ca);
    g.globalAlpha = ca;
    const pulse = (t - 33.4) % 1.25 / 1.25;
    g.fillStyle = rgba(C.mint, 0.5 * (1 - pulse)); g.beginPath(); g.arc(px + 36, py + ph / 2, 7 + pulse * 10, 0, TAU); g.fill();
    g.fillStyle = C.mint; g.shadowColor = C.mint; g.shadowBlur = 12; g.beginPath(); g.arc(px + 36, py + ph / 2, 7, 0, TAU); g.fill(); g.shadowBlur = 0;
    font(g, 'sans', 28, 600, 3); g.fillStyle = C.white; g.textAlign = 'left'; g.textBaseline = 'middle'; g.fillText(label, px + 60, py + ph / 2 + 1);
    g.restore();
  }
  words(g, 'Because every cancer journey deserves', W / 2, 720, t, 34.1, { size: 72, w: 600, stagger: 0.1 });
  words(g, 'one complete story.', W / 2, 812, t, 35.0, { size: 72, w: 600, col: C.mint, stagger: 0.12 });
  divider(g, W / 2, 880, 420, P(t, 35.8, 1.0, E.io));
  const fa = P(t, 36.3, 1.0);
  if (fa > 0) {
    g.save(); g.globalAlpha = fa;
    font(g, 'sans', 26, 400, 0.5); g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    const s1 = 'BigOHealth', s2 = '   ·   Under the mentorship of Dr. Nitesh Rohatgi';
    font(g, 'sans', 26, 600, 0.5); const w1 = g.measureText(s1).width; font(g, 'sans', 26, 400, 0.5); const w2 = g.measureText(s2).width;
    const x0 = W / 2 - (w1 + w2) / 2;
    g.textAlign = 'left';
    font(g, 'sans', 26, 600, 0.5); g.fillStyle = C.white; g.fillText(s1, x0, 960);
    font(g, 'sans', 26, 400, 0.5); g.fillStyle = C.muted; g.fillText(s2, x0 + w1, 960);
    g.restore();
  }
  const fo = P(t, 39.0, 1.0, E.io);
  if (fo > 0) { g.fillStyle = rgba(C.bg0, fo); g.fillRect(0, 0, W, H); }
}

// ================================================================== composition
// [start, end, fn, exitStart, exitEnd, exitScale]
const SCENES = [
  [0, 7.6, sOpen, 6.7, 7.5, 1.04],
  [7.5, 20.0, sJourney, 99, 99, 1],
  [20.0, 27.6, sOne, 26.7, 27.5, 1.06],
  [27.3, 40.01, sBrand, 99, 99, 1],
];
const layer = mk();
function drawAt(g, t) {
  const warmth = 1 - 0.35 * E.io(inv(27.0, 28.5, t));
  background(bgFrame.g, t, warmth);
  g.save();
  g.drawImage(bgFrame, 0, 0);
  const fi = 1 - P(t, 0, 1.2, E.io);   // fade up from black
  for (const [a, b, fn, x0, x1, xs] of SCENES) {
    if (t < a || t >= b) continue;
    const p = E.io(inv(x0, x1, t));
    if (p <= 0) { g.save(); fn(g, t); g.restore(); continue; }
    if (p >= 1) continue;
    const L = layer.g; L.save(); L.clearRect(0, 0, W, H); fn(L, t); L.restore();
    g.save(); g.globalAlpha = 1 - p; blur(g, p * 20);
    g.translate(W / 2, H / 2); const s = lerp(1, xs, p); g.scale(s, s); g.translate(-W / 2, -H / 2);
    g.drawImage(layer, 0, 0); g.restore();
  }
  if (fi > 0) { g.fillStyle = rgba(C.bg0, fi); g.fillRect(0, 0, W, H); }
  g.restore();
}

const grain = mk(256, 256);
(() => { const id = grain.g.createImageData(256, 256); for (let i = 0; i < id.data.length; i += 4) { const v = Math.random() < 0.5 ? 0 : 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 6; } grain.g.putImageData(id, 0, 0); })();

const cv = document.getElementById('c');
cv.width = W; cv.height = H;
const out = cv.getContext('2d');
const tmp = mk(), acc = mk();
function renderT(t0) {
  if (MB <= 1) { drawAt(out, t0); }
  else {
    for (let s = 0; s < MB; s++) {
      const t = t0 + ((s + 0.5) / MB - 0.5) * SHUTTER / FPS;
      drawAt(tmp.g, clamp(t, 0, DUR - 1e-4));
      acc.g.globalAlpha = 1 / (s + 1); acc.g.drawImage(tmp, 0, 0);
    }
    acc.g.globalAlpha = 1; out.drawImage(acc, 0, 0);
  }
  out.save();
  const ox = Math.floor(hash(t0 * 97.3) * 256), oy = Math.floor(hash(t0 * 13.1 + 5) * 256);
  out.translate(-ox, -oy); out.fillStyle = out.createPattern(grain, 'repeat'); out.fillRect(0, 0, W + 256, H + 256);
  out.restore();
}

const FRAMES = Math.round(DUR * FPS);
window.META = { FRAMES, FPS, DUR };
async function loadFonts() {
  const faces = [400, 500, 600, 700].map(w => new FontFace('Lora', `url(fonts/Lora-${w}.woff)`, { weight: String(w) }))
    .concat([300, 400, 500, 600, 700].map(w => new FontFace('Outfit', `url(fonts/Outfit-${w}.woff)`, { weight: String(w) })));
  await Promise.all(faces.map(f => f.load().then(ff => document.fonts.add(ff))));
}
window.READY = loadFonts().then(() => { renderT(0); return true; });
window.renderFrame = i => renderT(i / FPS);

if (!RENDER) {
  const audio = new Audio('out/audio.wav');
  let playing = false, start = 0, off = 0;
  const now = () => playing ? (performance.now() - start) / 1000 : off;
  function loop() { const t = now() % DUR; renderT(t); document.getElementById('tc').textContent = t.toFixed(2) + ' s'; requestAnimationFrame(loop); }
  window.READY.then(loop);
  addEventListener('keydown', e => {
    if (e.code === 'Space') { if (playing) { off = now(); playing = false; audio.pause(); } else { start = performance.now() - off * 1000; playing = true; audio.currentTime = off; audio.play().catch(() => {}); } }
    if (e.code === 'ArrowRight' || e.code === 'ArrowLeft') { off = clamp(now() + (e.code === 'ArrowRight' ? 2.5 : -2.5), 0, DUR - 0.01); if (playing) { start = performance.now() - off * 1000; audio.currentTime = off; } }
  });
}
