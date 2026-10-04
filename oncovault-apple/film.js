'use strict';
// ONCOVAULT by BigOHealth: 23.3 s promo in an Apple keynote style. White canvas, Inter Tight display type,
// blur-up word reveals, spring physics, soft cards, and the "intelligence" glow tinted in OncoVault greens.
// Every frame is a pure function of time t. Cues are cut to the supplied track (audio_src/linkedin_audio.mp3,
// ~97 BPM): first hit 1.0 s, groove 7.85 s, second phrase 12.77 s, climax 17.9 s, outro from 20.5 s.

const W = 1920, H = 1080, DUR = 23.34;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 60);
const MB = +(Q.get('mb') || (RENDER ? 4 : 1));
const SHUTTER = 0.5;

const C = {
  bg: '#FFFFFF', soft: '#F5F5F7', ink: '#1D1D1F', grey: '#6E6E73', grey2: '#86868B', hair: '#E8E8ED', line: '#D2D2D7',
  green: '#13A878', deep: '#0B7A55', mint: '#5DD6A8',
};
const TEXTG = ['#0B7A55', '#13A878', '#1FBF8F', '#0EA5A4', '#13A878'];          // gradient type (readable on white)
const GLOW = ['#13A878', '#5DD6A8', '#B8F5DC', '#0EA5A4', '#2CC796', '#FFFFFF']; // intelligence glow

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

// ------------------------------------------------------------------ colour
function hex2rgb(h) { const n = parseInt(h.slice(1), 16); return [n >> 16, n >> 8 & 255, n & 255]; }
function mix(a, b, t) { const A = hex2rgb(a), B = hex2rgb(b); return `rgb(${A.map((v, i) => Math.round(lerp(v, B[i], t))).join(',')})`; }
function rgba(h, a) { const [r, g, b] = hex2rgb(h); return `rgba(${r},${g},${b},${a})`; }
function palAt(pal, u) { u = ((u % 1) + 1) % 1; const n = pal.length, x = u * n, i = Math.floor(x); return mix(pal[i % n], pal[(i + 1) % n], x - i); }
function gradX(g, x0, x1, phase = 0, pal = TEXTG, cyc = 0.6) {
  const gr = g.createLinearGradient(x0, 0, x1, 0);
  for (let k = 0; k <= 8; k++) gr.addColorStop(k / 8, palAt(pal, phase + (k / 8) * cyc));
  return gr;
}

// ------------------------------------------------------------------ canvas helpers
function mk(w = W, h = H) { const c = document.createElement('canvas'); c.width = w; c.height = h; c.g = c.getContext('2d'); return c; }
const FAM = '"Inter Tight", "Helvetica Neue", Arial, sans-serif';
function font(g, px, w = 600, track = null) {
  g.font = `${w} ${px}px ${FAM}`;
  g.letterSpacing = (track == null ? -px * (px > 90 ? 0.035 : px > 40 ? 0.02 : 0.005) : track) + 'px';
}
function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function blur(g, b) { g.filter = b > 0.35 ? `blur(${b.toFixed(2)}px)` : 'none'; }
function softShadow(g, a = 0.12, b = 60, oy = 24) { g.shadowColor = `rgba(0,0,0,${a})`; g.shadowBlur = b; g.shadowOffsetX = 0; g.shadowOffsetY = oy; }
function noShadow(g) { g.shadowColor = 'transparent'; g.shadowBlur = 0; g.shadowOffsetY = 0; }

// Words blur up into place one after another.
// o: size, w, col, grad (phase) or gradFor(i), colFor(i), stagger, dur, dy, bl, a, align, track, out
function words(g, str, x, y, t, t0, o = {}) {
  const size = o.size || 80;
  font(g, size, o.w || 700, o.track);
  const parts = str.split(' ');
  const sp = g.measureText(' ').width;
  const ws = parts.map(p => g.measureText(p).width);
  const total = ws.reduce((a, b) => a + b, 0) + sp * (parts.length - 1);
  let cx = o.align === 'l' ? x : o.align === 'r' ? x - total : x - total / 2;
  const x0 = cx;
  g.textBaseline = 'alphabetic'; g.textAlign = 'left';
  const out = o.out || 0;
  for (let i = 0; i < parts.length; i++) {
    const p = P(t, t0 + i * (o.stagger ?? 0.09), o.dur || 0.9);
    const q = out > 0 ? E.inn(clamp(out * 1.25 - i * 0.05)) : 0;
    if (p > 0.001 && q < 0.999) {
      g.save();
      g.globalAlpha = (o.a ?? 1) * clamp(p * 1.4) * (1 - q);
      blur(g, (1 - p) * (o.bl ?? 14) + q * 14);
      const gradOn = o.gradFor ? o.gradFor(i) : o.grad != null;
      g.fillStyle = gradOn ? gradX(g, x0, x0 + total, o.grad ?? t * 0.05) : (o.colFor ? o.colFor(i) : (o.col || C.ink));
      g.fillText(parts[i], cx, y + (1 - p) * (o.dy ?? size * 0.35) - q * size * 0.25);
      g.restore();
    }
    cx += ws[i] + sp;
  }
  return total;
}
function text(g, s, x, y, o = {}) {
  font(g, o.size || 40, o.w || 500, o.track);
  g.textAlign = o.align || 'center'; g.textBaseline = o.base || 'alphabetic';
  g.fillStyle = o.col || C.ink;
  g.fillText(s, x, y);
  return g.measureText(s).width;
}

// intelligence glow around a rounded rect (green spectrum). k = intensity 0..1
function glowRect(g, x, y, w, h, r, t, k, th = 1) {
  if (k <= 0.002) return;
  const cg = g.createConicGradient(t * 1.9, x + w / 2, y + h / 2);
  const n = GLOW.length;
  for (let i = 0; i <= n; i++) cg.addColorStop(i / n, GLOW[i % n]);
  g.save(); g.strokeStyle = cg;
  for (const [lw, b, a] of [[38 * th, 26 * th, 0.55], [14 * th, 9 * th, 0.8], [3.5 * th, 0, 1]]) {
    g.globalAlpha = a * k; g.lineWidth = lw; blur(g, b * (0.6 + 0.4 * k));
    rr(g, x, y, w, h, r); g.stroke();
  }
  g.restore();
}
function glowCircle(g, x, y, r, t, k, th = 1) {
  if (k <= 0.002) return;
  const cg = g.createConicGradient(t * 1.6, x, y);
  const n = GLOW.length;
  for (let i = 0; i <= n; i++) cg.addColorStop(i / n, GLOW[i % n]);
  g.save(); g.strokeStyle = cg;
  for (const [lw, b, a] of [[44 * th, 30 * th, 0.5], [16 * th, 10 * th, 0.75], [3 * th, 0, 0.9]]) {
    g.globalAlpha = a * k; g.lineWidth = lw; blur(g, b);
    g.beginPath(); g.arc(x, y, r, 0, TAU); g.stroke();
  }
  g.restore();
}
// soft green aurora (radial gradients only)
function aurora(g, t, a, cx = W / 2, cy = H / 2, sx = 1, sy = 1) {
  if (a <= 0.002) return;
  g.save(); g.globalAlpha = a;
  [['#13A878', -380, -40, 520], ['#5DD6A8', 60, 60, 480], ['#0EA5A4', 420, -30, 460], ['#B8F5DC', 200, 160, 360]].forEach(([col, dx, dy, r], i) => {
    const x = cx + (dx + Math.sin(t * 0.5 + i * 2) * 60) * sx, y = cy + (dy + Math.cos(t * 0.4 + i) * 40) * sy;
    const gr = g.createRadialGradient(x, y, 0, x, y, r * sx);
    gr.addColorStop(0, rgba(col, 0.5)); gr.addColorStop(0.5, rgba(col, 0.15)); gr.addColorStop(1, rgba(col, 0));
    g.fillStyle = gr; g.fillRect(x - r * sx, y - r * sx, r * 2 * sx, r * 2 * sx);
  });
  g.restore();
}

// ------------------------------------------------------------------ icons (white line glyphs) and app-icon tiles
function glyph(g, kind, x, y, s, col = '#FFFFFF') {
  g.save(); g.translate(x, y); g.scale(s, s);
  g.strokeStyle = col; g.fillStyle = col; g.lineWidth = 0.13; g.lineCap = 'round'; g.lineJoin = 'round';
  g.beginPath();
  switch (kind) {
    case 'diagnosis': g.arc(-0.12, -0.12, 0.42, 0, TAU); g.moveTo(0.2, 0.2); g.lineTo(0.58, 0.58); g.stroke(); break;
    case 'surgery': g.moveTo(-0.6, 0.6); g.lineTo(0.05, -0.05); g.quadraticCurveTo(0.55, -0.6, 0.62, -0.62); g.quadraticCurveTo(0.45, -0.1, 0.18, 0.08); g.closePath(); g.stroke(); break;
    case 'radiation':
      for (let k = 0; k < 3; k++) { const a = -Math.PI / 2 + k * TAU / 3; g.beginPath(); g.arc(0, 0, 0.6, a - 0.5, a + 0.5); g.arc(0, 0, 0.24, a + 0.5, a - 0.5, true); g.closePath(); g.fill(); }
      g.beginPath(); g.arc(0, 0, 0.12, 0, TAU); g.fill(); break;
    case 'chemo':
      g.moveTo(0, -0.62); g.bezierCurveTo(0.2, -0.3, 0.45, 0, 0.45, 0.2); g.arc(0, 0.2, 0.45, 0, Math.PI); g.bezierCurveTo(-0.45, 0, -0.2, -0.3, 0, -0.62); g.stroke();
      g.beginPath(); g.moveTo(-0.15, 0.17); g.lineTo(0.15, 0.17); g.moveTo(0, 0.02); g.lineTo(0, 0.32); g.stroke(); break;
    case 'molecular':
      for (let k = 0; k < 2; k++) { g.beginPath(); for (let i = 0; i <= 20; i++) { const u = i / 20, yy = -0.62 + u * 1.24, xx = Math.sin(u * TAU * 1.1 + k * Math.PI) * 0.36; i ? g.lineTo(xx, yy) : g.moveTo(xx, yy); } g.stroke(); }
      for (let i = 1; i < 6; i++) { const u = i / 6, yy = -0.62 + u * 1.24, xx = Math.sin(u * TAU * 1.1) * 0.36; g.beginPath(); g.moveTo(xx, yy); g.lineTo(-xx, yy); g.stroke(); } break;
    case 'targeted': g.arc(0, 0, 0.58, 0, TAU); g.stroke(); g.beginPath(); g.arc(0, 0, 0.32, 0, TAU); g.stroke(); g.beginPath(); g.arc(0, 0, 0.1, 0, TAU); g.fill(); break;
  }
  g.restore();
}
function squircle(g, x, y, s) {
  const r = s / 2, n = 5; g.beginPath();
  for (let i = 0; i <= 64; i++) {
    const a = i / 64 * TAU, c = Math.cos(a), sn = Math.sin(a);
    g.lineTo(x + Math.sign(c) * Math.pow(Math.abs(c), 2 / n) * r, y + Math.sign(sn) * Math.pow(Math.abs(sn), 2 / n) * r);
  }
  g.closePath();
}
const TILE_HUES = [['#0B7A55', '#2CC796'], ['#0E8F6B', '#5DD6A8'], ['#0A7F7E', '#2DD4BF'], ['#11865F', '#4ADE9B'], ['#0B6E6A', '#34D3B4'], ['#0F9467', '#7EE2B8']];
function tile(g, kind, i, x, y, s, shadow = true) {
  const [c0, c1] = TILE_HUES[i % TILE_HUES.length];
  if (shadow) softShadow(g, 0.18, s * 0.35, s * 0.14);
  const gr = g.createLinearGradient(x - s / 2, y - s / 2, x + s / 2, y + s / 2);
  gr.addColorStop(0, c1); gr.addColorStop(1, c0);
  g.fillStyle = gr; squircle(g, x, y, s); g.fill(); noShadow(g);
  g.save(); squircle(g, x, y, s); g.clip();
  const hl = g.createLinearGradient(0, y - s / 2, 0, y);
  hl.addColorStop(0, 'rgba(255,255,255,0.28)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = hl; g.fillRect(x - s / 2, y - s / 2, s, s / 2);
  g.restore();
  glyph(g, kind, x, y, s * 0.36);
}

// ================================================================== SCENES
// 01 (0–4.7): Something big is coming. from BigOHealth (on the 1.0 s hit) / Under the mentorship of Dr. Nitesh Rohatgi & Dr. Swarupa Mitra
function sOpen(g, t) {
  const z = 1 + t * 0.006;
  g.save(); g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
  aurora(g, t, 0.10 * P(t, 0.9, 1.6, E.io), W / 2, 560, 1.1, 0.6);
  const up = E.io(inv(0.85, 1.55, t));
  words(g, 'Something big is coming.', W / 2, lerp(560, 470, up), t, 0.15, { size: 124, stagger: 0.08, dur: 0.75 });
  words(g, 'from BigOHealth.', W / 2, 610, t, 1.0, { size: 124, stagger: 0.1, dur: 0.8, gradFor: i => i === 1, grad: (t - 1) * 0.05, colFor: () => C.grey });
  words(g, 'Under the mentorship of', W / 2, 780, t, 2.2, { size: 40, w: 500, col: C.grey2, stagger: 0.05, dy: 16, bl: 10, dur: 0.75 });
  words(g, 'Dr. Nitesh Rohatgi & Dr. Swarupa Mitra', W / 2, 852, t, 2.55, { size: 56, w: 650, stagger: 0.07, dy: 18, dur: 0.8, colFor: i => i === 3 ? C.grey2 : C.ink });
  g.restore();
}

// 02 (4.3–7.9): The entire / cancer journey.
function sJourney(g, t) {
  const z = 1 + (t - 4.4) * 0.014;
  g.save(); g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
  words(g, 'The entire', W / 2, 430, t, 4.5, { size: 64, w: 600, col: C.grey, dy: 20, bl: 10 });
  // per-letter mask rise for the big line
  const title = 'cancer journey.', size = 210;
  font(g, size, 700);
  const tw = g.measureText(title).width, x0 = W / 2 - tw / 2, base = 640;
  g.textAlign = 'left';
  for (let i = 0; i < title.length; i++) {
    const xi = x0 + g.measureText(title.slice(0, i)).width;
    const p = P(t, 4.8 + i * 0.03, 1.0);
    if (p <= 0) continue;
    g.save();
    g.beginPath(); g.rect(xi - 40, base - size * 1.05, 400, size * 1.35); g.clip();
    g.globalAlpha = clamp(p * 1.6); g.fillStyle = C.ink;
    g.fillText(title[i], xi, base + (1 - p) * size);
    g.restore();
  }
  g.restore();
}

// 03 (7.85–17.7): on the groove, pairs in big type, six app tiles land on one timeline, then "together in a single longitudinal timeline."
const STAGES = [
  { k: 'diagnosis', name: 'Diagnosis' }, { k: 'surgery', name: 'Surgery' }, { k: 'radiation', name: 'Radiation' },
  { k: 'chemo', name: 'Chemotherapy' }, { k: 'molecular', name: 'Molecular' }, { k: 'targeted', name: 'Targeted therapy' },
];
const PAIRS = [[7.85, 'From', 'diagnosis', 'surgery,'], [9.36, '', 'radiation', 'chemotherapy,'], [10.87, '', 'molecular', 'targeted therapy.']];
const TILE_T = [8.1, 8.5, 9.6, 10.0, 11.1, 11.5];
const TOGETHER = 12.77;
const TX0 = 300, TX1 = 1620, TY = 760;
const tileX = i => lerp(TX0, TX1, i / 5);
function sTimeline(g, t) {          // slow push-in while "Together…" holds
  const z = 1 + 0.05 * E.io(inv(TOGETHER, 17.4, t));
  g.save(); g.translate(W / 2, 560); g.scale(z, z); g.translate(-W / 2, -560);
  timelineBody(g, t);
  g.restore();
}
function timelineBody(g, t) {
  const sceneOut = P(t, 16.85, 0.7, E.io);
  // pair lines roll through one slot
  for (let k = 0; k < PAIRS.length; k++) {
    const [t0, pre, a, b] = PAIRS[k];
    const t1 = k < PAIRS.length - 1 ? PAIRS[k + 1][0] : TOGETHER;
    const pin = P(t, t0, 0.75), pout = P(t, t1 - 0.12, 0.42, E.io);
    if (pin <= 0 || pout >= 1) continue;
    const parts = [pre, a, 'to', b].filter(Boolean);
    g.save(); g.globalAlpha = clamp(pin * 1.3) * (1 - pout); blur(g, (1 - pin) * 14 + pout * 14);
    font(g, 112, 700); g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    const sp = g.measureText(' ').width, ws = parts.map(s => g.measureText(s).width);
    let x = W / 2 - (ws.reduce((s, w) => s + w, 0) + sp * (parts.length - 1)) / 2;
    const y = 440 + (1 - pin) * 70 - pout * 70;
    parts.forEach((s, i) => { g.fillStyle = (s === 'From' || s === 'to') ? C.grey2 : C.ink; g.fillText(s, x, y); x += ws[i] + sp; });
    g.restore();
  }
  words(g, 'Together in a single', W / 2, 400, t, TOGETHER, { size: 112, stagger: 0.1, out: sceneOut });
  words(g, 'longitudinal timeline.', W / 2, 525, t, TOGETHER + 0.5, { size: 112, stagger: 0.12, grad: (t - TOGETHER) * 0.06, out: sceneOut });

  // the timeline: hairline track, green progress, tiles
  const ta = P(t, 7.55, 0.7) * (1 - sceneOut);
  if (ta <= 0.002) return;
  const lift = E.io(inv(TOGETHER, TOGETHER + 1.0, t)) * 40;
  g.save(); g.globalAlpha = ta; g.translate(0, lift);
  const drawn = E.io(inv(7.55, 8.3, t));
  g.fillStyle = C.line; g.fillRect(lerp(W / 2, TX0, drawn), TY - 1.5, (TX1 - TX0) * drawn, 3);
  let done = -1; TILE_T.forEach((tt, i) => { if (t >= tt) done = i; });
  const prog = done < 0 ? 0 : lerp(tileX(Math.max(0, done - 1)), tileX(done), E.io(clamp((t - TILE_T[done]) / 0.5))) - TX0;
  const full = E.io(inv(TOGETHER + 0.3, TOGETHER + 1.3, t));
  const pw = lerp(prog, TX1 - TX0, full);
  if (pw > 0) {
    const gr = gradX(g, TX0, TX1, (t - 7.85) * 0.05);
    g.fillStyle = gr; g.fillRect(TX0, TY - 2.5, pw, 5);
  }
  // glow along the finished timeline
  const gk = P(t, TOGETHER + 0.8, 0.6) * (1 - P(t, 16.4, 0.6, E.io));
  if (gk > 0.002) {             // luminous pass along the finished track
    g.save();
    for (const [lw, b, a] of [[26, 18, 0.45], [10, 6, 0.7]]) {
      g.globalAlpha = ta * gk * a; blur(g, b); g.fillStyle = gradX(g, TX0, TX1, (t - TOGETHER) * 0.2, GLOW, 1.2);
      g.fillRect(TX0, TY - lw / 2, TX1 - TX0, lw);
    }
    const hx = lerp(TX0, TX1, ((t - TOGETHER - 0.8) / 1.4) % 1);
    const hg = g.createRadialGradient(hx, TY, 0, hx, TY, 120);
    hg.addColorStop(0, 'rgba(184,245,220,0.9)'); hg.addColorStop(1, 'rgba(184,245,220,0)');
    g.globalAlpha = ta * gk; g.filter = 'none'; g.fillStyle = hg; g.fillRect(hx - 120, TY - 40, 240, 80);
    g.restore();
  }
  STAGES.forEach((s, i) => {
    const sp = spring(t - TILE_T[i], 1.5, 0.55);
    if (sp <= 0.001) return;
    const a = clamp((t - TILE_T[i]) / 0.2);
    const bounce = full > 0 ? Math.sin(clamp((t - TOGETHER - 0.4 - i * 0.08) / 0.35) * Math.PI) * 14 : 0;
    const x = tileX(i), y = TY - (1 - sp) * 160 - bounce;
    g.save(); g.globalAlpha = ta * a;
    g.fillStyle = '#FFFFFF'; g.beginPath(); g.arc(x, TY, 13, 0, TAU); g.fill();
    g.strokeStyle = C.green; g.lineWidth = 4; g.stroke();
    g.translate(x, y - 92); g.scale(lerp(0.6, 1, sp), lerp(0.6, 1, sp));
    tile(g, s.k, i, 0, 0, 112);
    g.restore();
    g.save(); g.globalAlpha = ta * clamp((t - TILE_T[i] - 0.15) / 0.3);
    text(g, s.name, x, TY + 62, { size: 30, w: 600 });
    g.restore();
  });
  g.restore();
}

// 04 (17.9–23.3): OncoVault wordmark in an intelligence-glow capsule, then Coming soon / closing line
function sBrand(g, t) {
  const lift = E.io(inv(19.65, 20.4, t));
  const ws = lerp(210, 120, lift), wy = lerp(610, 340, lift);
  aurora(g, t, 0.14 * P(t, 17.9, 1.2, E.io) * (1 - 0.5 * lift), W / 2, wy - ws * 0.35, 1.0, 0.6);
  font(g, ws, 700);
  const s = 'OncoVault', tw = g.measureText(s).width, x0 = W / 2 - tw / 2;
  // capsule glow traces the word, then settles
  const gk = P(t, 17.85, 0.5) * (1 - 0.85 * P(t, 19.3, 1.1, E.io));
  const padX = ws * 0.42, capH = ws * 1.25, capW = tw + padX * 2;
  const cw = capW * E.io(inv(17.85, 18.6, t));
  glowRect(g, W / 2 - cw / 2, wy - ws * 0.36 - capH / 2, cw, capH, capH / 2, t, gk, lerp(1.1, 0.7, lift));
  g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  for (let i = 0; i < s.length; i++) {
    const p = P(t, 17.95 + i * 0.045, 0.9);
    if (p <= 0) continue;
    const xi = x0 + g.measureText(s.slice(0, i + 1)).width - g.measureText(s[i]).width;
    g.save();
    g.beginPath(); g.rect(xi - 40, wy - ws * 1.05, ws * 1.4, ws * 1.35); g.clip();
    g.globalAlpha = clamp(p * 1.5);
    g.fillStyle = i < 4 ? C.ink : gradX(g, x0, x0 + tw, (t - 18) * 0.04);
    g.fillText(s[i], xi, wy + (1 - p) * ws);
    g.restore();
  }
  words(g, 'by BigOHealth', W / 2, 740, t, 18.6, { size: 40, w: 500, col: C.grey, dy: 16, bl: 10, dur: 0.7, out: P(t, 19.45, 0.4, E.io) });
  // Coming soon pill
  const cp = spring(t - 20.15, 1.5, 0.7), ca = clamp((t - 20.15) / 0.25);
  if (ca > 0) {
    font(g, 30, 600, 0);
    const label = 'Coming soon', lw = g.measureText(label).width, pw = lw + 86, ph = 64, px = W / 2 - pw / 2, py = 440;
    g.save(); g.globalAlpha = ca;
    g.translate(W / 2, py + ph / 2); g.scale(lerp(0.85, 1, cp), lerp(0.85, 1, cp)); g.translate(-W / 2, -(py + ph / 2));
    g.fillStyle = C.soft; rr(g, px, py, pw, ph, ph / 2); g.fill();
    const pulse = ((t - 20.15) % 1.0) / 1.0;
    g.fillStyle = rgba(C.green, 0.35 * (1 - pulse)); g.beginPath(); g.arc(px + 36, py + ph / 2, 7 + pulse * 11, 0, TAU); g.fill();
    g.fillStyle = C.green; g.beginPath(); g.arc(px + 36, py + ph / 2, 7, 0, TAU); g.fill();
    font(g, 30, 600, 0); g.fillStyle = C.ink; g.textAlign = 'left'; g.textBaseline = 'middle'; g.fillText(label, px + 58, py + ph / 2 + 1);
    g.restore();
  }
  words(g, 'Because every cancer journey deserves', W / 2, 660, t, 20.45, { size: 78, stagger: 0.06, dur: 0.75 });
  words(g, 'one complete story.', W / 2, 765, t, 21.05, { size: 78, stagger: 0.1, dur: 0.8, grad: (t - 21) * 0.05 });
  const fo = P(t, 22.85, 0.48, E.io);
  if (fo > 0) { g.fillStyle = `rgba(255,255,255,${fo})`; g.fillRect(0, 0, W, H); }
}

// ================================================================== composition
// [start, end, fn, exitStart, exitEnd, exitScale]
const SCENES = [
  [0, 4.7, sOpen, 3.95, 4.65, 0.95],
  [4.3, 7.9, sJourney, 7.15, 7.85, 1.12],
  [7.45, 17.7, sTimeline, 99, 99, 1],
  [17.7, 23.35, sBrand, 99, 99, 1],
];
const layer = mk();
function drawAt(g, t) {
  g.save();
  g.fillStyle = C.bg; g.fillRect(0, 0, W, H);
  for (const [a, b, fn, x0, x1, xs] of SCENES) {
    if (t < a || t >= b) continue;
    const p = E.io(inv(x0, x1, t));
    if (p <= 0) { g.save(); fn(g, t); g.restore(); continue; }
    if (p >= 1) continue;
    const L = layer.g; L.save(); L.clearRect(0, 0, W, H); fn(L, t); L.restore();
    g.save(); g.globalAlpha = 1 - p; blur(g, p * 22);
    g.translate(W / 2, H / 2); const s = lerp(1, xs, p); g.scale(s, s); g.translate(-W / 2, -H / 2);
    g.drawImage(layer, 0, 0); g.restore();
  }
  g.restore();
}

const grain = mk(256, 256);
(() => { const id = grain.g.createImageData(256, 256); for (let i = 0; i < id.data.length; i += 4) { const v = Math.random() < 0.5 ? 0 : 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 5; } grain.g.putImageData(id, 0, 0); })();

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
  const faces = [300, 400, 500, 600, 700, 800].map(w => new FontFace('Inter Tight', `url(fonts/InterTight-${w}.woff)`, { weight: String(w) }));
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
    if (e.code === 'ArrowRight' || e.code === 'ArrowLeft') { off = clamp(now() + (e.code === 'ArrowRight' ? 2 : -2), 0, DUR - 0.01); if (playing) { start = performance.now() - off * 1000; audio.currentTime = off; } }
  });
}
