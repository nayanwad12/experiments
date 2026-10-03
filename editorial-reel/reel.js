'use strict';
// "Same reel. Two editors." 16:9 editorial motion piece, 1920x1080. Every frame is a pure function of t (s).
// Look: grey studio paper, acid-yellow panels, heavy tight grotesk, halftone objects with soft shadows,
// viewfinder brackets, tiny serif text blocks, handwritten sign-off.
// Word onsets come from work/words.json (forced alignment); keep T_ in sync with it and with audio.py.

const W = 1920, H = 1080, DUR = 35.8;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 30);
const MB = +(Q.get('mb') || (RENDER ? 2 : 1));
const SHUTTER = 0.5;

const T_ = {
  same: 0.00, reel: 0.38, two: 1.04, editors: 1.31,
  e1a: 2.27, opens1: 2.89, timeline: 3.37, e2a: 4.29, opens2: 5.02, chat: 5.39,
  e1b: 6.29, drags: 6.94, twoH: 7.89, clips: 8.48, e2b: 9.39, types: 9.97, cut: 10.62, pauses: 11.02,
  e1c: 12.09, key: 13.01, capt: 13.92, colour: 14.70, export: 15.47, crash: 16.29,
  e2c: 17.37, hits: 17.99, enter: 18.25, six: 19.07, later6: 19.71, e1d: 20.45, posts: 21.07,
  twelve: 21.98, later12: 22.61, e2d: 23.29, reel3: 24.22, number: 24.49, three: 24.70,
  idea: 25.48, same2: 26.45, footage: 26.81, only: 27.54, diff: 27.83, oneof: 28.66, knew: 29.15,
  what: 29.50, to: 29.86, ask: 29.96, for: 30.33, thats: 30.98, vibe: 31.39, editing: 31.72,
  comment: 32.45, vibeW: 32.81, and: 33.41, ill: 33.57, show: 33.67, you: 33.83, how: 33.99, sign: 34.25,
};

const C = {
  ink: '#2B2B2B', ink2: '#555553', mid: '#9A9A97', paper: '#E6E6E3', yellow: '#E9EF1A', yellow2: '#D9DF0E',
  white: '#F7F7F4', red: '#E23B2E',
};
const SANS = (w, s) => `${w} ${s}px "Inter Tight"`;
const SERIF = (s, it = false) => `${it ? 'italic ' : ''}400 ${s}px "Instrument Serif"`;
const SCRIPT = s => `400 ${s}px "Mrs Saint Delafield"`;

// ------------------------------------------------------------------ math
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const inv = (a, b, x) => clamp((x - a) / (b - a));
const TAU = Math.PI * 2;
const E = {
  outQ: x => 1 - (1 - x) * (1 - x), inQ: x => x * x,
  outC: x => 1 - Math.pow(1 - x, 3), inC: x => x * x * x,
  ioC: x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2,
  outX: x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x),
  ioX: x => x <= 0 ? 0 : x >= 1 ? 1 : x < .5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2,
  outB: (x, s = 1.7) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2),
};
const ease = (t, a, d, f = E.outC) => f(inv(a, a + d, t));
function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
function noise1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u) * 2 - 1; }
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
// visibility window: fades in at a, out at b
const vis = (t, a, b, fi = .2, fo = .18) => ease(t, a, fi, E.outQ) * (1 - ease(t, b - fo, fo, E.inQ));

// ------------------------------------------------------------------ canvas helpers
function mk(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; c.g = c.getContext('2d'); return c; }
const OUT = document.getElementById('out'), G = OUT.getContext('2d');
const FR = mk(W, H), ACC = mk(W, H);
function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function at(g, x, y, s, a, fn, rot = 0) {
  if (a <= 0.003 || s <= 0.003) return;
  g.save(); g.translate(x, y); if (rot) g.rotate(rot); g.scale(s, s); g.globalAlpha *= clamp(a); fn(); g.restore();
}
// heavy tight grotesk text; returns width
function txt(g, s, x, y, size, o = {}) {
  const { w = 800, col = C.ink, align = 'left', ls = -0.05, shadow = true, font = null } = o;
  g.font = font || SANS(w, size); g.letterSpacing = `${size * ls}px`; g.textAlign = align; g.fillStyle = col;
  if (shadow) { g.shadowColor = 'rgba(0,0,0,0.22)'; g.shadowBlur = size * .1; g.shadowOffsetX = size * .025; g.shadowOffsetY = size * .045; }
  g.fillText(s, x, y);
  g.shadowColor = 'transparent'; g.shadowBlur = 0; g.shadowOffsetX = 0; g.shadowOffsetY = 0;
  const wd = g.measureText(s).width; g.letterSpacing = '0px'; return wd;
}
function measure(g, s, size, w = 800, ls = -0.05) { g.font = SANS(w, size); g.letterSpacing = `${size * ls}px`; const m = g.measureText(s).width; g.letterSpacing = '0px'; return m; }
// extruded 3D type (ref: STORYTELLING)
function extruded(g, s, x, y, size, depth = 14, align = 'center') {
  g.font = SANS(800, size); g.letterSpacing = `${size * -0.05}px`; g.textAlign = align;
  for (let i = depth; i > 0; i--) { g.fillStyle = mixc('#7d7d7a', '#b9b9b6', i / depth); g.fillText(s, x + i * .9, y + i * 1.4); }
  g.fillStyle = C.ink2; g.fillText(s, x, y);
  g.letterSpacing = '0px';
}
// ghost repeats of a word, fading away from the main copy (dir -1 = up, +1 = down)
function ghosts(g, s, x, y, size, n, dir, a = 1, align = 'center') {
  g.font = SANS(800, size); g.letterSpacing = `${size * -0.05}px`; g.textAlign = align;
  for (let k = n; k >= 1; k--) { g.globalAlpha = a * .22 * (1 - k / (n + 1)); g.fillStyle = C.ink2; g.fillText(s, x, y + dir * k * size * .62); }
  g.globalAlpha = 1; g.letterSpacing = '0px';
}
function mixc(c1, c2, t) {
  const p = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
  const a = p(c1), b = p(c2);
  return `rgb(${a.map((v, i) => Math.round(lerp(v, b[i], clamp(t)))).join(',')})`;
}
// word pop: returns {a, s, dy}
function pop(t, t0, d = .38) {
  const k = ease(t, t0, d, E.outB);
  return { a: ease(t, t0, d * .5, E.outQ), s: lerp(.82, 1, k), dy: (1 - ease(t, t0, d)) * 36 };
}
// masked rise: text slides up out of an invisible line
function rise(g, t, t0, x, y, size, fn, d = .45) {
  const k = ease(t, t0, d, E.outX);
  if (k <= 0) return;
  g.save(); g.beginPath(); g.rect(x - 2000, y - size * 1.05, 4000, size * 1.35); g.clip();
  g.translate(0, (1 - k) * size * 1.2); fn(); g.restore();
}

// ------------------------------------------------------------------ baked layers
function paperLayer(col0, col1, seed) {
  const c = mk(W, H), g = c.g;
  const r = g.createRadialGradient(W * .5, H * .45, 80, W * .5, H * .5, W * .62);
  r.addColorStop(0, col0); r.addColorStop(1, col1);
  g.fillStyle = r; g.fillRect(0, 0, W, H);
  const d = g.getImageData(0, 0, W, H), R = rng(seed);
  for (let i = 0; i < d.data.length; i += 4) { const n = (R() - .5) * 9; d.data[i] += n; d.data[i + 1] += n; d.data[i + 2] += n; }
  g.putImageData(d, 0, 0);
  return c;
}
let PAPER, YEL, PARA1, PARA2, SP = {};
const PARA_TEXT = 'Editing is the process of selecting, arranging and refining footage into one clear story. Every cut, caption and colour choice is a decision. Vibe Editing moves those decisions into plain language: you describe the feeling, the machine does the clicking, and the story arrives faster than the timeline ever could.';
function paragraph(width, align, size = 15) {
  const c = mk(width, 200), g = c.g;
  g.font = SERIF(size); g.fillStyle = '#4a4a48'; g.textAlign = align;
  const words = PARA_TEXT.split(' '); let line = '', y = size + 2;
  const lines = [];
  for (const w of words) { const tl = line ? line + ' ' + w : w; if (g.measureText(tl).width > width) { lines.push(line); line = w; } else line = tl; }
  lines.push(line);
  for (const l of lines.slice(0, 7)) { g.fillText(l, align === 'right' ? width : align === 'center' ? width / 2 : 0, y); y += size * 1.25; }
  return c;
}

// halftone sprite: draw() paints a grayscale object; dots size by darkness; soft drop shadow baked in
function halftone(w, h, draw, { cell = 7, pad = 70, flat = null, sh = [24, 34], dot = '#262626' } = {}) {
  const src = mk(w, h); draw(src.g, w, h);
  const id = src.g.getImageData(0, 0, w, h).data;
  const out = mk(w + pad * 2, h + pad * 2), o = out.g;
  const sil = mk(w, h); sil.g.drawImage(src, 0, 0); sil.g.globalCompositeOperation = 'source-in'; sil.g.fillStyle = '#000'; sil.g.fillRect(0, 0, w, h);
  o.save(); o.filter = 'blur(22px)'; o.globalAlpha = .34; o.drawImage(sil, pad + sh[0], pad + sh[1]); o.restore();
  const base = mk(w, h); base.g.drawImage(src, 0, 0); base.g.globalCompositeOperation = 'source-in'; base.g.fillStyle = '#F2F2EF'; base.g.fillRect(0, 0, w, h);
  o.drawImage(base, pad, pad);
  o.fillStyle = dot;
  for (let row = 0, y = cell / 2; y < h; y += cell * .87, row++) {
    for (let x = (row % 2 ? cell / 2 : 0) + cell / 2; x < w; x += cell) {
      const i = (Math.floor(y) * w + Math.floor(x)) * 4;
      if (id[i + 3] < 128) continue;
      const dark = 1 - (id[i] * .3 + id[i + 1] * .59 + id[i + 2] * .11) / 255;
      const r = cell * .64 * Math.sqrt(dark);
      if (r < .45) continue;
      o.beginPath(); o.arc(pad + x, pad + y, r, 0, TAU); o.fill();
    }
  }
  if (flat) { o.save(); o.translate(pad, pad); flat(o, w, h); o.restore(); }
  return { c: out, pad, w, h };
}
function flatSprite(w, h, draw, { pad = 80, sh = [22, 32], blur = 26, alpha = .3 } = {}) {
  const src = mk(w, h); draw(src.g, w, h);
  const out = mk(w + pad * 2, h + pad * 2), o = out.g;
  const sil = mk(w, h); sil.g.drawImage(src, 0, 0); sil.g.globalCompositeOperation = 'source-in'; sil.g.fillStyle = '#000'; sil.g.fillRect(0, 0, w, h);
  o.save(); o.filter = `blur(${blur}px)`; o.globalAlpha = alpha; o.drawImage(sil, pad + sh[0], pad + sh[1]); o.restore();
  o.drawImage(src, pad, pad);
  return { c: out, pad, w, h };
}
// draw sprite centred at (x,y)
function spr(g, sp, x, y, s = 1, a = 1, rot = 0) {
  at(g, x, y, s, a, () => g.drawImage(sp.c, -sp.w / 2 - sp.pad, -sp.h / 2 - sp.pad), rot);
}
const lg = (g, x0, y0, x1, y1, stops) => { const gr = g.createLinearGradient(x0, y0, x1, y1); stops.forEach(([o, c]) => gr.addColorStop(o, c)); return gr; };

// --- object drawings (grayscale, for halftoning) ---
const COMP_SCREEN = { x: 140, y: 78, w: 300, h: 206 };
function drawComputer(g) {
  // keyboard
  g.fillStyle = lg(g, 0, 430, 0, 520, [[0, '#d8d8d8'], [1, '#8d8d8d']]);
  g.beginPath(); g.moveTo(55, 430); g.lineTo(525, 430); g.lineTo(565, 520); g.lineTo(15, 520); g.closePath(); g.fill();
  g.fillStyle = '#6f6f6f';
  for (let r = 0; r < 4; r++) for (let k = 0; k < 12; k++) {
    const y = 442 + r * 18, sh = r * 6, x = 82 - sh + k * (36 + r * .9);
    g.fillRect(x, y, 30, 12);
  }
  // stand
  g.fillStyle = lg(g, 0, 380, 0, 420, [[0, '#7a7a7a'], [1, '#a5a5a5']]);
  g.beginPath(); g.moveTo(215, 386); g.lineTo(365, 386); g.lineTo(395, 418); g.lineTo(185, 418); g.closePath(); g.fill();
  // side face + body
  g.fillStyle = '#7b7b7b';
  g.beginPath(); g.moveTo(500, 14); g.lineTo(545, 44); g.lineTo(545, 360); g.lineTo(500, 392); g.closePath(); g.fill();
  g.fillStyle = lg(g, 70, 0, 500, 390, [[0, '#f4f4f4'], [.6, '#d0d0d0'], [1, '#a2a2a2']]);
  rr(g, 70, 4, 432, 388, 30); g.fill();
  // bezel + screen
  g.fillStyle = lg(g, 0, 50, 0, 320, [[0, '#7a7a7a'], [1, '#b6b6b6']]);
  rr(g, 116, 54, 348, 254, 18); g.fill();
  g.fillStyle = '#3a3a3a'; rr(g, COMP_SCREEN.x, COMP_SCREEN.y, COMP_SCREEN.w, COMP_SCREEN.h, 10); g.fill();
  g.fillStyle = '#9a9a9a'; g.fillRect(120, 336, 120, 10); g.fillRect(400, 330, 46, 22);
}
function screenRect(x, y, sc) {
  return { x: x + (-SP.computer.w / 2 + COMP_SCREEN.x) * sc, y: y + (-SP.computer.h / 2 + COMP_SCREEN.y) * sc, w: COMP_SCREEN.w * sc, h: COMP_SCREEN.h * sc };
}
function drawClock(g) {
  g.fillStyle = '#8c8c8c';
  g.beginPath(); g.arc(110, 80, 62, Math.PI * .9, Math.PI * 1.95); g.closePath(); g.fill();
  g.beginPath(); g.arc(310, 80, 62, Math.PI * 1.05, Math.PI * .1); g.closePath(); g.fill();
  g.fillRect(105, 355, 22, 50); g.fillRect(293, 355, 22, 50);
  const r = g.createRadialGradient(170, 190, 30, 210, 240, 190); r.addColorStop(0, '#f2f2f2'); r.addColorStop(1, '#7c7c7c');
  g.fillStyle = r; g.beginPath(); g.arc(210, 240, 172, 0, TAU); g.fill();
  g.fillStyle = '#f7f7f7'; g.beginPath(); g.arc(210, 240, 138, 0, TAU); g.fill();
  g.fillStyle = '#3a3a3a';
  for (let i = 0; i < 12; i++) { g.save(); g.translate(210, 240); g.rotate(i / 12 * TAU); g.fillRect(-5, -128, 10, i % 3 ? 16 : 28); g.restore(); }
}
function drawPhone(g, w, h) {
  g.fillStyle = lg(g, 0, 0, w, h, [[0, '#e6e6e6'], [1, '#8a8a8a']]); rr(g, 0, 0, w, h, 34); g.fill();
  g.fillStyle = '#4a4a4a'; rr(g, 14, 44, w - 28, h - 92, 12); g.fill();
  g.fillStyle = '#6e6e6e'; rr(g, w / 2 - 26, 18, 52, 10, 5); g.fill();
}
function drawKey(g, w, h) {
  g.fillStyle = lg(g, 0, 60, 0, h, [[0, '#9c9c9c'], [1, '#5c5c5c']]); rr(g, 0, 50, w, h - 50, 46); g.fill();
  g.fillStyle = lg(g, 30, 0, w - 30, h - 80, [[0, '#fbfbfb'], [1, '#c4c4c4']]); rr(g, 30, 0, w - 60, h - 70, 40); g.fill();
}
function drawReel(g) {
  const r = g.createRadialGradient(140, 140, 20, 180, 180, 180); r.addColorStop(0, '#e6e6e6'); r.addColorStop(1, '#6e6e6e');
  g.fillStyle = r; g.beginPath(); g.arc(180, 180, 172, 0, TAU); g.fill();
  g.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < 6; i++) { const a = i / 6 * TAU; g.beginPath(); g.arc(180 + Math.cos(a) * 100, 180 + Math.sin(a) * 100, 38, 0, TAU); g.fill(); }
  g.beginPath(); g.arc(180, 180, 14, 0, TAU); g.fill();
  g.globalCompositeOperation = 'source-over';
  g.strokeStyle = '#555'; g.lineWidth = 10; g.beginPath(); g.arc(180, 180, 40, 0, TAU); g.stroke();
}
function drawFootage(g, w, h) {
  g.fillStyle = '#2f2f2f'; g.fillRect(0, 0, w, h);
  g.fillStyle = '#f0f0f0';
  for (let x = 18; x < w - 20; x += 38) { g.fillRect(x, 10, 20, 16); g.fillRect(x, h - 26, 20, 16); }
  const ix = 20, iy = 40, iw = w - 40, ih = h - 80;
  g.fillStyle = lg(g, 0, iy, 0, iy + ih, [[0, '#f4f4f4'], [1, '#b0b0b0']]); g.fillRect(ix, iy, iw, ih);
  g.fillStyle = '#d8d8d8'; g.beginPath(); g.arc(ix + iw * .72, iy + ih * .32, 34, 0, TAU); g.fill();
  g.fillStyle = '#7c7c7c'; g.beginPath(); g.moveTo(ix, iy + ih); g.lineTo(ix + iw * .32, iy + ih * .38); g.lineTo(ix + iw * .58, iy + ih); g.fill();
  g.fillStyle = '#5a5a5a'; g.beginPath(); g.moveTo(ix + iw * .35, iy + ih); g.lineTo(ix + iw * .66, iy + ih * .5); g.lineTo(ix + iw, iy + ih * .85); g.lineTo(ix + iw, iy + ih); g.fill();
}
function drawClip(g, w, h, v) {
  g.fillStyle = '#353535'; g.fillRect(0, 0, w, h);
  g.fillStyle = '#efefef'; for (let x = 8; x < w - 8; x += 18) { g.fillRect(x, 5, 9, 7); g.fillRect(x, h - 12, 9, 7); }
  g.fillStyle = lg(g, 0, 16, w, h - 16, [[0, ['#e0e0e0', '#bdbdbd', '#f0f0f0'][v]], [1, ['#8a8a8a', '#5d5d5d', '#a8a8a8'][v]]]);
  g.fillRect(8, 17, w - 16, h - 34);
}
function bakeSprites() {
  SP.computer = halftone(580, 525, drawComputer, { flat: (o) => { o.fillStyle = C.yellow; rr(o, COMP_SCREEN.x, COMP_SCREEN.y, COMP_SCREEN.w, COMP_SCREEN.h, 10); o.fill(); } });
  SP.computerDark = halftone(580, 525, drawComputer);
  SP.clock = halftone(420, 410, drawClock);
  SP.phone = halftone(230, 430, drawPhone, { flat: (o, w, h) => { o.fillStyle = C.white; rr(o, 14, 44, w - 28, h - 92, 12); o.fill(); } });
  SP.phoneY = halftone(230, 430, drawPhone, { flat: (o, w, h) => { o.fillStyle = C.yellow; rr(o, 14, 44, w - 28, h - 92, 12); o.fill(); } });
  SP.key = halftone(560, 380, drawKey, { cell: 8 });
  SP.reel = halftone(360, 360, drawReel);
  SP.footage = halftone(560, 340, drawFootage, { cell: 6 });
  SP.clips = [0, 1, 2].map(v => halftone(150, 100, (g, w, h) => drawClip(g, w, h, v), { cell: 5, pad: 30, sh: [8, 12] }));
  SP.disc = flatSprite(700, 700, g => { g.fillStyle = C.yellow; g.beginPath(); g.arc(350, 350, 350, 0, TAU); g.fill(); });
  SP.rect = flatSprite(800, 500, g => { g.fillStyle = C.yellow; g.fillRect(0, 0, 800, 500); });
  SP.bubble = flatSprite(640, 230, g => {
    g.fillStyle = C.white; rr(g, 0, 0, 640, 190, 34); g.fill();
    g.beginPath(); g.moveTo(90, 180); g.lineTo(60, 230); g.lineTo(150, 186); g.fill();
  });
  SP.card = flatSprite(300, 150, g => { g.fillStyle = C.white; rr(g, 0, 0, 300, 150, 18); g.fill(); }, { pad: 40, sh: [10, 16], blur: 16 });
  PAPER = paperLayer('#F3F3F1', '#C4C4C1', 3);
  YEL = paperLayer('#F0F53A', '#D0D60A', 4);
  PARA1 = paragraph(380, 'right'); PARA2 = paragraph(380, 'left');
}

// ------------------------------------------------------------------ decorations
function brackets(g, x0, y0, x1, y1, a = 1, len = 70, col = C.ink) {
  g.save(); g.globalAlpha *= a; g.strokeStyle = col; g.lineWidth = 3; g.beginPath();
  g.moveTo(x0, y0 + len); g.lineTo(x0, y0); g.lineTo(x0 + len, y0);
  g.moveTo(x1 - len, y0); g.lineTo(x1, y0); g.lineTo(x1, y0 + len);
  g.moveTo(x1, y1 - len); g.lineTo(x1, y1); g.lineTo(x1 - len, y1);
  g.moveTo(x0 + len, y1); g.lineTo(x0, y1); g.lineTo(x0, y1 - len);
  g.stroke(); g.restore();
}
function ruleDot(g, x, y0, y1, k) {   // thin vertical line drawing down, ending in a dot
  if (k <= 0) return;
  const y = lerp(y0, y1, k);
  g.strokeStyle = C.ink; g.lineWidth = 3; g.beginPath(); g.moveTo(x, y0); g.lineTo(x, y); g.stroke();
  g.fillStyle = C.ink; g.beginPath(); g.arc(x, y + 10, 11 * clamp(k * 3 - 2), 0, TAU); g.fill();
}
function para(g, c, x, y, a, align = 'left') { if (a <= 0) return; g.globalAlpha = a; g.drawImage(c, align === 'right' ? x - c.width : x, y); g.globalAlpha = 1; }
function sparks(g, x, y, s, t, seed = 0) {   // yellow zig-zag sparks (ref: retro computer)
  const on = Math.floor(t * 9 + seed) % 3 !== 0;
  if (!on) return;
  g.save(); g.translate(x, y); g.scale(s, s);
  g.strokeStyle = C.yellow; g.lineWidth = 15; g.lineJoin = 'miter'; g.lineCap = 'butt';
  g.shadowColor = 'rgba(0,0,0,0.18)'; g.shadowBlur = 8; g.shadowOffsetY = 5;
  const z = (pts) => { g.beginPath(); pts.forEach(([a, b], i) => i ? g.lineTo(a, b) : g.moveTo(a, b)); g.stroke(); };
  z([[150, -250], [130, -190], [175, -205], [150, -140]]);
  z([[215, -200], [200, -160], [255, -175]]);
  z([[-260, 40], [-200, 30], [-235, 80], [-170, 70]]);
  z([[-250, 150], [-210, 120], [-215, 175]]);
  g.restore();
}

// ------------------------------------------------------------------ scene A: same reel.
function sOpen(g, t) {
  g.drawImage(PAPER, 0, 0);
  const d = ease(t, 0, .5, E.outB);
  spr(g, SP.disc, 1180, 560, .9 * d, 1);
  const rk = ease(t, .05, .7, E.outC);
  spr(g, SP.reel, lerp(600, 1230, rk), 560, .95, rk, (t * 1.6) % TAU + (1 - rk) * -6);
  let p = pop(t, T_.same);
  at(g, 300, 400 - p.dy, p.s, p.a, () => txt(g, 'same', 0, 0, 140));
  p = pop(t, T_.reel);
  at(g, 300, 640 - p.dy, p.s, p.a, () => txt(g, 'reel.', 0, 0, 300));
  para(g, PARA1, 1760, 90, ease(t, .2, .5), 'right');
  ruleDot(g, 1830, 60, 230, ease(t, .1, .6));
}

// ------------------------------------------------------------------ split section (two editors)
// split x: left = editor one (paper), right = editor two (yellow)
const SPLIT = [[T_.two - .02, 960], [T_.e1a - .05, 1250], [T_.e2a - .05, 680], [T_.e1b - .05, 1250], [T_.e2b - .05, 680],
  [T_.e1c - .05, 1480], [T_.e2c - .05, 0], [T_.six - .08, 1250], [T_.twelve - .05, 700], [T_.idea - .05, 960]];
function splitX(t) {
  let x = 1920;
  for (const [t0, v] of SPLIT) x = lerp(x, v, ease(t, t0, .5, E.ioX));
  return x;
}
// scale a half's content around the vertical centre so narrow halves shrink as a unit
function side(g, cx, s, a, fn) {
  if (a <= .003) return;
  g.save(); g.translate(cx, 540); g.scale(s, s); g.translate(0, -540); g.globalAlpha *= clamp(a); fn(); g.restore();
}
function sideScale(w) { return clamp(w / 960, .6, 1.3); }

function leftContent(g, t, cx, w, s) {
  const top = 230;
  // label
  const lab = pop(t, T_.two);
  at(g, cx, 150 - lab.dy, 1, lab.a * (1 - ease(t, T_.six - .2, .2)), () => {
    g.font = SANS(700, 26); g.letterSpacing = '6px'; g.textAlign = 'center'; g.fillStyle = C.ink; g.fillText('EDITOR 01', 0, 0); g.letterSpacing = '0px';
  });
  // L0: "one."
  let a = vis(t, T_.two, T_.e1a + .1);
  if (a > 0) { const p = pop(t, T_.editors); at(g, cx, 640 - p.dy, s * p.s, a * p.a, () => { txt(g, 'one.', 0, 0, 330, { align: 'center' }); }); }
  // L1: computer + timeline
  a = vis(t, T_.e1a, T_.e1b + .1);
  if (a > 0) {
    const k = ease(t, T_.e1a, .55, E.outB);
    side(g, cx, s, a, () => {
      const cy = 650 + (1 - k) * 500;
      spr(g, SP.computerDark, 0, cy + 40, .85, 1);
      const sr = screenRect(0, cy + 40, .85), ox = sr.x, oy = sr.y;
      g.save(); g.beginPath(); g.rect(sr.x, sr.y, sr.w, sr.h); g.clip();
      g.fillStyle = '#3a3a3a'; g.fillRect(sr.x, sr.y, sr.w, sr.h);
      const ta = ease(t, T_.timeline - .05, .5);
      for (let r = 0; r < 6; r++) for (let i = 0; i < 7; i++) {
        const bw = 20 + hash(r * 7 + i) * 40, bx = ox + 10 + i * 42 + hash(i + r) * 10;
        if (hash(r * 13 + i) > ta) continue;
        g.fillStyle = [C.yellow, '#dcdcdc', '#9a9a9a'][(r + i) % 3]; g.fillRect(bx, oy + 12 + r * 31, bw, 20);
      }
      g.fillStyle = C.red; g.fillRect(ox + 40 + ((t * 80) % 220), oy, 3, sr.h);
      g.restore();
    });
    side(g, cx, s, a, () => {
      const p1 = pop(t, T_.opens1), p2 = pop(t, T_.timeline);
      at(g, -400, top + 70 - p1.dy, p1.s, p1.a, () => txt(g, 'opens', 0, 0, 64));
      at(g, -400, top + 210 - p2.dy, p2.s, p2.a, () => txt(g, 'the timeline.', 0, 0, 132));
    });
  }
  // L2: clips raining into a pile + 200 counter
  a = vis(t, T_.e1b, T_.e1c + .1);
  if (a > 0) {
    side(g, cx, s, a, () => {
      const R = rng(9);
      for (let i = 0; i < 70; i++) {
        const t0 = T_.e1b + .02 + i * .028 + R() * .1, tx = (R() - .5) * 760, ty = 760 + R() * 210 - Math.abs(tx) * .12, rot = (R() - .5) * 1.4, v = Math.floor(R() * 3);
        const k = ease(t, t0, .5, E.outB);
        if (k <= 0) continue;
        spr(g, SP.clips[v], tx * lerp(.6, 1, k), lerp(-300, ty, ease(t, t0, .45, E.inQ)), .95, 1, rot * k);
      }
      const n = Math.round(200 * ease(t, T_.twoH - .05, .7, E.outC));
      if (t > T_.twoH - .05) {
        const p = pop(t, T_.twoH - .05);
        at(g, 0, 520 - p.dy, p.s, p.a, () => { ghosts(g, String(n), 0, 0, 300, 2, -1); txt(g, String(n), 0, 0, 300, { align: 'center' }); });
      }
      const pc = pop(t, T_.clips);
      at(g, 230, 640 - pc.dy, pc.s, pc.a, () => txt(g, 'clips.', 0, 0, 110));
      const pd = pop(t, T_.drags);
      at(g, -330, top - pd.dy, pd.s, pd.a * (1 - ease(t, T_.twoH, .3)), () => txt(g, 'drags…', 0, 0, 96));
    });
  }
  // L3: keyframes / captions / colour / export
  a = vis(t, T_.e1c, T_.crash + .05, .2, .05);
  if (a > 0) {
    const words = [[T_.key, 'keyframes.'], [T_.capt, 'captions.'], [T_.colour, 'colour.'], [T_.export, 'export…']];
    side(g, cx, s, a, () => {
      let shown = words.filter(w => t >= w[0] - .05);
      shown.forEach(([t0, s0], i) => {
        const age = shown.length - 1 - i;
        const k = ease(t, t0 - .05, .35, E.outB);
        const y = 600 + age * 125 * ease(t, (shown[i + 1] || [99])[0] - .05, .3) + (1 - k) * 60;
        const size = age === 0 ? 190 : 90;
        at(g, 0, y, lerp(.7, 1, k), clamp(k * 2) * (age === 0 ? 1 : (.35 - age * .07) * (1 - ease(t, T_.export - .1, .25))), () => {
          if (age === 0) ghosts(g, s0, 0, 0, size, 2, -1, 1);
          txt(g, s0, 0, 0, size, { align: 'center', shadow: age === 0 });
        });
      });
      // export bar
      const eb = ease(t, T_.export, .3);
      if (eb > 0) {
        g.globalAlpha *= eb;
        g.strokeStyle = C.ink; g.lineWidth = 4; rr(g, -330, 700, 660, 44, 22); g.stroke();
        const p = .08 + .3 * ease(t, T_.export + .1, .8, E.outQ);
        g.fillStyle = C.ink; rr(g, -324, 706, 648 * p, 32, 16); g.fill();
        g.font = SANS(700, 26); g.textAlign = 'center'; g.fillText(`${Math.round(p * 100)}%`, 0, 800);
      }
    });
  }
  // L4: crash
  a = vis(t, T_.crash - .02, T_.e2c + .2, .05, .2);
  if (a > 0) {
    const k = ease(t, T_.crash - .02, .3, E.outB);
    side(g, cx, s, a, () => {
      const sc = lerp(1.15, .9, k), jit = (hash(Math.floor(t * 30)) - .5) * 10 * (1 - k);
      spr(g, SP.computerDark, jit, 690, sc, 1);
      const sr = screenRect(jit, 690, sc), cx0 = sr.x + sr.w * .56, cy0 = sr.y + sr.h * .42;
      g.save(); g.beginPath(); g.rect(sr.x, sr.y, sr.w, sr.h); g.clip();
      if (Math.floor(t * 14) % 3 === 0) { g.fillStyle = 'rgba(233,239,26,0.5)'; g.fillRect(sr.x, sr.y, sr.w, sr.h); }
      g.strokeStyle = '#f2f2ee'; g.lineWidth = 3;
      for (let i = 0; i < 9; i++) { const an = i / 9 * TAU + .3; g.beginPath(); g.moveTo(cx0, cy0); g.lineTo(cx0 + Math.cos(an) * 60, cy0 + Math.sin(an) * 45); g.lineTo(cx0 + Math.cos(an + .2) * 170, cy0 + Math.sin(an + .2) * 120); g.stroke(); }
      g.restore();
      sparks(g, 0, 690, .9, t);
      const p = pop(t, T_.crash);
      at(g, 0, 380 - p.dy, p.s, p.a, () => {
        g.save(); g.beginPath(); g.rect(-600, -230, 1200, 160); g.clip(); txt(g, 'crash.', -8, 0, 170, { align: 'center' }); g.restore();
        g.save(); g.beginPath(); g.rect(-600, -70, 1200, 160); g.clip(); txt(g, 'crash.', 14, 6, 170, { align: 'center' }); g.restore();
      });
    });
  }
  // L5: six hours later, editor one posts
  a = vis(t, T_.six - .05, T_.idea + .05);
  if (a > 0) {
    side(g, cx, s, a, () => {
      const k = ease(t, T_.six - .05, .5, E.outB);
      spr(g, SP.clock, -170, 640, .95 * k, 1);
      // hands sweep 6 hours
      const sweep = ease(t, T_.six, 1.1, E.ioC) * 6;
      g.save(); g.translate(-170, 640 + 35 * .95 * k); g.scale(.95 * k, .95 * k);
      g.strokeStyle = C.ink; g.lineCap = 'round';
      g.lineWidth = 12; g.beginPath(); g.moveTo(0, 0); const ha = (10 + sweep) / 12 * TAU; g.lineTo(Math.sin(ha) * 70, -Math.cos(ha) * 70); g.stroke();
      g.lineWidth = 7; g.beginPath(); g.moveTo(0, 0); const ma = sweep * TAU; g.lineTo(Math.sin(ma) * 110, -Math.cos(ma) * 110); g.stroke();
      g.fillStyle = C.ink; g.beginPath(); g.arc(0, 0, 12, 0, TAU); g.fill();
      g.restore();
      const p1 = pop(t, T_.six), p2 = pop(t, T_.later6);
      at(g, -360, 310 - p1.dy, p1.s, p1.a, () => txt(g, 'six hours', 0, 0, 150));
      at(g, 300, 390 - p2.dy, p2.s, p2.a, () => txt(g, 'later.', 0, 0, 64, { w: 700 }));
      // one lonely post
      const pp = ease(t, T_.posts - .05, .5, E.outB);
      if (pp > 0) {
        spr(g, SP.phone, 260, 690, .78 * pp, 1, .08);
        at(g, 260, 690, .78 * pp, 1, () => {
          g.rotate(.08);
          g.fillStyle = C.ink; g.font = SANS(800, 64); g.textAlign = 'center'; g.fillText('01', 0, -20);
          g.font = SANS(700, 30); g.fillText('♥ 3', 0, 60);
        });
        const po = pop(t, T_.posts);
        at(g, 260, 890 - po.dy, po.s, po.a, () => txt(g, 'posts.', 0, 0, 80, { align: 'center' }));
      }
    });
  }
}

function rightContent(g, t, cx, w, s) {
  const top = 230;
  const lab = pop(t, T_.two + .08);
  at(g, cx, 150 - lab.dy, 1, lab.a * (1 - ease(t, T_.six - .2, .2)), () => {
    g.font = SANS(700, 26); g.letterSpacing = '6px'; g.textAlign = 'center'; g.fillStyle = C.ink; g.fillText('EDITOR 02', 0, 0); g.letterSpacing = '0px';
  });
  // R0: "two."
  let a = vis(t, T_.two, T_.e2a + .1);
  if (a > 0) { const p = pop(t, T_.editors + .1); at(g, cx, 640 - p.dy, s * p.s, a * p.a, () => txt(g, 'two.', 0, 0, 330, { align: 'center' })); }
  // R1+R2: chat bubble, then "cut my pauses." typed
  a = vis(t, T_.e2a, T_.e2c + .15);
  if (a > 0) {
    side(g, cx, s, a, () => {
      const k = ease(t, T_.chat - .1, .5, E.outB);
      spr(g, SP.bubble, 0, 600, k, 1);
      const typed = 'cut my pauses.';
      const n = Math.floor(typed.length * inv(T_.cut - .05, T_.pauses + .45, t));
      g.textAlign = 'left';
      if (n === 0) {   // typing dots
        for (let i = 0; i < 3; i++) { g.fillStyle = C.ink; g.globalAlpha = k * (.35 + .65 * (Math.sin(t * 8 - i) * .5 + .5)); g.beginPath(); g.arc(-60 + i * 60, 575, 16, 0, TAU); g.fill(); }
        g.globalAlpha = 1;
      } else {
        txt(g, typed.slice(0, n), -270, 600, 82, { shadow: false });
        const cw = measure(g, typed.slice(0, n), 82);
        if (Math.floor(t * 3) % 2 === 0) { g.fillStyle = C.ink; g.fillRect(-262 + cw, 535, 6, 80); }
      }
      const p1 = pop(t, T_.opens2), p2 = pop(t, T_.chat);
      const fade = 1 - ease(t, T_.e2b - .1, .25);
      at(g, -300, top - p1.dy, p1.s, p1.a * fade, () => txt(g, 'opens', 0, 0, 64));
      at(g, -300, top + 150 - p2.dy, p2.s, p2.a * fade, () => txt(g, 'a chat.', 0, 0, 132));
      const p3 = pop(t, T_.types);
      at(g, -300, top + 120 - p3.dy, p3.s, p3.a, () => txt(g, 'types:', 0, 0, 96));
      // waiting enter hint while editor one grinds
      const wa = ease(t, T_.e1c + .3, .4) * (1 - ease(t, T_.e2c - .1, .2));
      if (wa > 0) { g.globalAlpha *= wa; g.font = SANS(700, 34); g.fillStyle = C.ink; g.textAlign = 'center'; g.fillText('↵  ready', 0, 840); }
    });
  }
  // R3: ENTER (full-screen yellow)
  a = vis(t, T_.e2c - .05, T_.six + .15, .2, .25);
  if (a > 0) {
    const press = Math.sin(inv(T_.enter - .06, T_.enter + .16, t) * Math.PI);
    const k = ease(t, T_.e2c, .5, E.outB);
    at(g, cx, 0, 1, a, () => {
      // burst
      const b = inv(T_.enter, T_.enter + .5, t);
      if (b > 0 && b < 1) {
        g.strokeStyle = C.ink; g.lineWidth = 8; g.lineCap = 'round';
        for (let i = 0; i < 14; i++) { const an = i / 14 * TAU, r0 = 330 + E.outC(b) * 120, r1 = r0 + 80 * (1 - b); g.beginPath(); g.moveTo(Math.cos(an) * r0 * 1.3, 620 + Math.sin(an) * r0 * .8); g.lineTo(Math.cos(an) * r1 * 1.3, 620 + Math.sin(an) * r1 * .8); g.stroke(); }
      }
      g.save(); g.translate(0, 620 + press * 18); g.scale(k, k * (1 - press * .08));
      spr(g, SP.key, 0, 0, 1, 1);
      g.fillStyle = C.ink; g.font = SANS(800, 92); g.letterSpacing = '-4px'; g.textAlign = 'center'; g.fillText('enter ↵', 0, -10); g.letterSpacing = '0px';
      g.restore();
      const p1 = pop(t, T_.hits), p2 = pop(t, T_.enter);
      at(g, -720, 250 - p1.dy, p1.s, p1.a, () => txt(g, 'hits', 0, 0, 96));
      at(g, 380, 250 - p2.dy, p2.s, p2.a, () => txt(g, 'enter.', 0, 0, 150));
    });
  }
  // R5: twelve minutes later, reel number three
  a = vis(t, T_.six + .1, T_.idea + .05);
  if (a > 0) {
    side(g, cx, s, a, () => {
      const pre = 1 - ease(t, T_.twelve - .1, .25);
      if (pre > 0) { g.globalAlpha *= pre; spr(g, SP.phoneY, 0, 620, .8, 1); g.font = SANS(800, 70); g.fillStyle = C.ink; g.textAlign = 'center'; g.fillText('✓', 0, 640); g.globalAlpha = a; }
      const p1 = pop(t, T_.twelve), p2 = pop(t, T_.later12);
      at(g, -380, 310 - p1.dy, p1.s, p1.a, () => txt(g, 'twelve minutes', 0, 0, 104));
      at(g, 300, 390 - p2.dy, p2.s, p2.a, () => txt(g, 'later.', 0, 0, 64, { w: 700 }));
      [[T_.reel3, -300, -.12], [T_.number, 0, 0], [T_.three, 300, .12]].forEach(([t0, x, rot], i) => {
        const k = ease(t, t0 - .08, .5, E.outB);
        if (k <= 0) return;
        spr(g, SP.phoneY, x * k, 660 + (1 - k) * 400, .82, 1, rot * k);
        at(g, x * k, 660 + (1 - k) * 400, .82, 1, () => { g.rotate(rot * k); g.fillStyle = C.ink; g.font = SANS(800, 110); g.letterSpacing = '-5px'; g.textAlign = 'center'; g.fillText(`0${i + 1}`, 0, 30); g.letterSpacing = '0px'; });
      });
      const pr = pop(t, T_.three);
      at(g, 0, 1010 - pr.dy, pr.s, pr.a, () => txt(g, 'reel number three.', 0, 0, 64, { align: 'center' }));
    });
  }
}

function sSplit(g, t) {
  const sx = splitX(t);
  // underlying opening scene slides away left while the yellow panel enters
  if (t < T_.e1a) { g.save(); const k = ease(t, T_.two - .02, .5, E.ioX); g.translate(-k * 400, 0); g.globalAlpha = 1 - k; sOpen(g, t); g.restore(); }
  // left: paper
  if (sx > 1) {
    g.save(); g.beginPath(); g.rect(0, 0, sx, H); g.clip();
    if (t >= T_.e1a) g.drawImage(PAPER, 0, 0);
    else { g.globalAlpha = ease(t, T_.two - .02, .5, E.ioX); g.drawImage(PAPER, 0, 0); g.globalAlpha = 1; }
    leftContent(g, t, sx / 2, sx, sideScale(sx));
    brackets(g, 50, 60, sx - 50, H - 60, ease(t, T_.two, .4) * clamp((sx - 300) / 300));
    g.restore();
  }
  // right: yellow
  if (sx < W - 1) {
    g.save(); g.beginPath(); g.rect(sx, 0, W - sx, H); g.clip();
    g.drawImage(YEL, 0, 0);
    // soft shadow the yellow panel casts on the paper edge
    const sh = g.createLinearGradient(sx, 0, sx + 40, 0); sh.addColorStop(0, 'rgba(0,0,0,0.12)'); sh.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = sh; g.fillRect(sx, 0, 40, H);
    rightContent(g, t, (sx + W) / 2, W - sx, sideScale(W - sx));
    brackets(g, sx + 50, 60, W - 50, H - 60, ease(t, T_.two, .4) * clamp((W - sx - 300) / 300));
    g.restore();
  }
  // shared caption across the seam: same idea / same footage
  const ia = ease(t, T_.idea, .3);
  if (ia > 0) {
    const k = ease(t, T_.idea - .05, .6, E.outB);
    spr(g, SP.footage, 480, 560, .95 * k, 1, -.04);
    spr(g, SP.footage, 1440, 560, .95 * k, 1, .04);
    brackets(g, 150, 330, 810, 790, k * .9, 40);
    brackets(g, 1110, 330, 1770, 790, k * .9, 40);
    const p1 = pop(t, T_.idea), p2 = pop(t, T_.same2);
    at(g, 960, 200 - p1.dy, p1.s, p1.a, () => txt(g, 'same idea.', 0, 0, 130, { align: 'center' }));
    at(g, 960, 1000 - p2.dy, p2.s, p2.a, () => txt(g, 'same footage.', 0, 0, 130, { align: 'center' }));
    const eq = pop(t, T_.footage);
    at(g, 960, 600, eq.s, eq.a, () => { g.fillStyle = C.ink; g.fillRect(-60, -50, 120, 26); g.fillRect(-60, 0, 120, 26); });
  }
}

// ------------------------------------------------------------------ the only difference? / what to ask for
function sDiff(g, t) {
  g.drawImage(PAPER, 0, 0);
  para(g, PARA1, 1700, 110, ease(t, T_.only, .4), 'right');
  ruleDot(g, 1780, 70, 250, ease(t, T_.only, .6));
  para(g, PARA2, 120, 880, ease(t, T_.only + .1, .4));
  ruleDot(g, 90, 1010, 830, ease(t, T_.only + .1, .6));
  const out = 1 - ease(t, T_.oneof - .15, .2);
  const p1 = pop(t, T_.only), p2 = pop(t, T_.diff);
  at(g, 300, 430 - p1.dy, p1.s, p1.a * out, () => txt(g, 'the only', 0, 0, 110));
  at(g, 300, 680 - p2.dy, p2.s, p2.a * out, () => {
    const w = txt(g, 'difference', 0, 0, 250);
    const q = ease(t, T_.diff + .3, .4, E.outB);
    spr(g, SP.disc, w + 120, -80, .3 * q, 1);
    txt(g, '?', w + 70, 0, 250, { shadow: false });
  });
}
function sAsk(g, t) {
  g.drawImage(PAPER, 0, 0);
  para(g, PARA1, 1700, 90, 1, 'right');
  ruleDot(g, 1780, 60, 230, 1);
  para(g, PARA2, 120, 900, 1);
  // "one of them knew"
  const pk = pop(t, T_.oneof), out = 1 - ease(t, T_.what - .1, .2);
  at(g, 960, 560 - pk.dy, pk.s, pk.a * out, () => txt(g, 'one of them knew…', 0, 0, 120, { align: 'center' }));
  // top word behind the yellow card, bottom word in front (ref: STORYTELLING)
  const wa = ease(t, T_.what - .05, .35);
  if (wa > 0) {
    at(g, 960, 0, 1, wa, () => {
      ghosts(g, 'WHAT TO', 0, 330, 200, 2, 1, 1);
      rise(g, t, T_.what - .05, 0, 330, 200, () => extruded(g, t >= T_.to - .05 ? 'WHAT TO' : 'WHAT', 0, 330, 200));
    });
    at(g, 960, 0, 1, ease(t, T_.ask - .05, .3), () => ghosts(g, 'ASK FOR.', 0, 960, 200, 2, -1, 1));
    const rk = ease(t, T_.what, .5, E.outB);
    spr(g, SP.rect, 960, 590, .82 * rk, 1);
    spr(g, SP.computer, 1080, 640, .78 * rk, 1);
    sparks(g, 1080, 640, .78, t, 1);
    // bubble from the screen
    const bk = ease(t, T_.for - .05, .45, E.outB);
    if (bk > 0) {
      spr(g, SP.card, 760, 500, bk, 1, -.05);
      at(g, 760, 500, bk, 1, () => { g.rotate(-.05); txt(g, 'make it hit.', 0, 14, 44, { align: 'center', shadow: false }); });
    }
    at(g, 960, 0, 1, ease(t, T_.ask - .05, .3), () => {
      rise(g, t, T_.ask - .05, 0, 960, 200, () => extruded(g, t >= T_.for - .05 ? 'ASK FOR.' : 'ASK', 0, 960, 200));
    });
  }
}

// ------------------------------------------------------------------ that's vibe editing
function sVibe(g, t) {
  g.drawImage(PAPER, 0, 0);
  const k = ease(t, T_.thats - .05, .55, E.outB);
  spr(g, SP.computer, 1010, 720, .95 * k, 1);
  sparks(g, 1010, 720, .95, t);
  const p0 = pop(t, T_.thats), p1 = pop(t, T_.vibe), p2 = pop(t, T_.editing);
  at(g, 520, 170 - p0.dy, p0.s, p0.a, () => txt(g, "that's", 0, 0, 70, { w: 700 }));
  at(g, 500, 400 - p1.dy, p1.s, p1.a, () => txt(g, 'Vibe', 0, 0, 280));
  at(g, 900, 520 - p2.dy, p2.s, p2.a, () => txt(g, 'editing.', 0, 0, 130));
}

// ------------------------------------------------------------------ comment VIBE (yellow / paper split)
function sCTA(g, t) {
  const sx = lerp(1920, 960, ease(t, T_.comment - .12, .45, E.ioX));
  g.drawImage(PAPER, 0, 0);
  g.save(); g.beginPath(); g.rect(0, 0, sx, H); g.clip(); g.drawImage(YEL, 0, 0); g.restore();
  // header paragraph + brackets
  para(g, paragraph(520, 'center', 14), 700, 50, ease(t, T_.comment, .4));
  brackets(g, 80, 130, 1840, 950, ease(t, T_.comment, .4), 90);
  const p1 = pop(t, T_.comment);
  at(g, 200, 330 - p1.dy, p1.s, p1.a, () => txt(g, 'comment', 0, 0, 120));
  const bk = ease(t, T_.vibeW - .1, .45, E.outB);
  spr(g, SP.bubble, 1000, 560, 1.05 * bk, 1);
  const n = Math.floor(5 * inv(T_.vibeW - .05, T_.vibeW + .3, t));
  if (bk > 0) { at(g, 1000, 560, 1.05 * bk, 1, () => { txt(g, 'VIBE'.slice(0, n), -250, 62, 170, { shadow: false }); }); }
  // bottom row (ref: "Said  Out  Loud")
  [[T_.and, 'and', 120], [T_.ill, "I'll", 520], [T_.show, 'show', 880], [T_.you, 'you', 1290], [T_.how, 'how.', 1600]].forEach(([t0, s, x]) => {
    rise(g, t, t0 - .04, x, 1040, 120, () => txt(g, s, x, 1040, 120), .35);
  });
}

// ------------------------------------------------------------------ sign-off
function sSign(g, t) {
  g.drawImage(PAPER, 0, 0);
  const w = ease(t, T_.sign + .05, .3);
  g.globalAlpha = w; g.font = SERIF(70, true); g.fillStyle = C.ink; g.textAlign = 'left'; g.fillText('edit by', 520, 520); g.globalAlpha = 1;
  // script written on with a moving wipe
  const k = ease(t, T_.sign + .25, 1.2, E.ioC);
  if (k > 0) {
    g.save(); g.beginPath(); g.rect(700, 300, 900 * k, 400); g.clip();
    g.font = SCRIPT(210); g.fillStyle = C.ink; g.fillText('Vibe Editing', 720, 600);
    g.restore();
  }
}

// ------------------------------------------------------------------ timeline
const SECTIONS = [
  [0, T_.two - .02, sOpen],
  [T_.two - .02, T_.only - .12, sSplit],
  [T_.only - .12, T_.oneof - .02, sDiff],
  [T_.oneof - .02, T_.thats - .12, sAsk],
  [T_.thats - .12, T_.comment - .12, sVibe],
  [T_.comment - .12, T_.sign, sCTA],
  [T_.sign, DUR + 1, sSign],
];
function drawFrame(t) {
  t = clamp(t, 0, DUR);
  const g = FR.g;
  g.save(); g.fillStyle = C.paper; g.fillRect(0, 0, W, H);
  // gentle camera: slow push per section + drift; a kick on hard moments
  let s0 = 0; for (const [a] of SECTIONS) if (t >= a) s0 = a;
  const shake = Math.exp(-Math.max(0, t - T_.crash) * 6) * (t > T_.crash ? 1 : 0) * 14;
  const z = 1 + .025 * clamp((t - s0) / 4) + .002 * noise1(t * .4);
  g.translate(W / 2 + noise1(t * .5) * 4 + noise1(t * 40) * shake, H / 2 + noise1(t * .45 + 7) * 4 + noise1(t * 40 + 9) * shake);
  g.scale(z, z); g.translate(-W / 2, -H / 2);
  for (const [a, b, fn] of SECTIONS) if (t >= a && t < b) { g.save(); fn(g, t); g.restore(); }
  g.restore();
  // section entrance flash of yellow wipe (hard cut helper)
  const v = g.createRadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, W * .65);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.16)');
  g.fillStyle = v; g.fillRect(0, 0, W, H);
}

// ------------------------------------------------------------------ frame driver
window.META = { FRAMES: Math.round(DUR * FPS), FPS, DUR };
window.renderFrame = i => {
  const t = i / FPS;
  if (MB <= 1) { drawFrame(t); G.drawImage(FR, 0, 0); return; }
  for (let k = 0; k < MB; k++) {
    drawFrame(t + (k / MB - .5) * SHUTTER / FPS);
    ACC.g.globalAlpha = 1 / (k + 1); ACC.g.drawImage(FR, 0, 0);
  }
  ACC.g.globalAlpha = 1; G.drawImage(ACC, 0, 0);
};
window.READY = (async () => {
  await Promise.all([SANS(800, 40), SANS(700, 40), SERIF(20), SERIF(40, true), SCRIPT(40)].map(f => document.fonts.load(f)));
  bakeSprites();
  if (RENDER) { document.body.classList.add('render'); return true; }
  const audio = new Audio('work/narration.mp3');
  let t0 = performance.now(), off = 0, playing = false;
  addEventListener('keydown', e => {
    if (e.code === 'Space') { playing = !playing; if (playing) { t0 = performance.now(); audio.currentTime = off; audio.play(); } else { off += (performance.now() - t0) / 1000; audio.pause(); } }
    if (e.code === 'ArrowRight') off = Math.min(DUR, off + 1);
    if (e.code === 'ArrowLeft') off = Math.max(0, off - 1);
  });
  const loop = () => { const t = playing ? off + (performance.now() - t0) / 1000 : off; drawFrame(t % DUR); G.drawImage(FR, 0, 0); requestAnimationFrame(loop); };
  loop();
  return true;
})();
