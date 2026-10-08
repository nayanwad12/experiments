'use strict';
// ONCOXPRESS: 10 s typographic ad, Apple style. Text only: white canvas, Inter Tight, blur-up and mask-rise reveals,
// a rolling word slot, gradient type for the product name. 120 BPM: 1 beat = 0.5 s, every cut lands on a beat.
// Cue times are mirrored in audio.py.

const W = 1920, H = 1080, DUR = 10;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 60);
const MB = +(Q.get('mb') || (RENDER ? 4 : 1));
const SHUTTER = 0.5;

const C = { bg: '#FFFFFF', ink: '#1D1D1F', grey: '#86868B', grey2: '#6E6E73' };
const GRAD = ['#0066D6', '#0A8FC2', '#0FAFA0', '#0A8FC2', '#0066D6'];

// ------------------------------------------------------------------ math
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const inv = (a, b, x) => clamp((x - a) / (b - a));
function bez(x1, y1, x2, y2) {
  const f = (a, b, t) => 3 * a * t * (1 - t) * (1 - t) + 3 * b * t * t * (1 - t) + t * t * t;
  return x => {
    if (x <= 0) return 0; if (x >= 1) return 1;
    let lo = 0, hi = 1, t = x;
    for (let i = 0; i < 22; i++) { t = (lo + hi) / 2; if (f(x1, x2, t) < x) lo = t; else hi = t; }
    return f(y1, y2, t);
  };
}
const E = { out: bez(0.16, 1, 0.3, 1), io: bez(0.65, 0, 0.35, 1), inn: bez(0.55, 0, 1, 0.45) };
const P = (t, t0, d = 0.8, e = E.out) => e(inv(t0, t0 + d, t));
function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
function hex2rgb(h) { const n = parseInt(h.slice(1), 16); return [n >> 16, n >> 8 & 255, n & 255]; }
function mix(a, b, t) { const A = hex2rgb(a), B = hex2rgb(b); return `rgb(${A.map((v, i) => Math.round(lerp(v, B[i], t))).join(',')})`; }
function palAt(pal, u) { u = ((u % 1) + 1) % 1; const n = pal.length - 1, x = u * n, i = Math.floor(x); return mix(pal[i], pal[i + 1], x - i); }
function gradX(g, x0, x1, phase = 0) {
  const gr = g.createLinearGradient(x0, 0, x1, 0);
  for (let k = 0; k <= 8; k++) gr.addColorStop(k / 8, palAt(GRAD, phase + k / 8 * 0.5));
  return gr;
}
function mk(w = W, h = H) { const c = document.createElement('canvas'); c.width = w; c.height = h; c.g = c.getContext('2d'); return c; }
const FAM = '"Inter Tight", "Helvetica Neue", Arial, sans-serif';
function font(g, px, w = 700) { g.font = `${w} ${px}px ${FAM}`; g.letterSpacing = (-px * (px > 90 ? 0.04 : 0.02)) + 'px'; }
function blur(g, b) { g.filter = b > 0.35 ? `blur(${b.toFixed(2)}px)` : 'none'; }

// a line of words that blur up into place; spec: [[word, style]] with style 'ink' | 'grey' | 'grad'
function line(g, spec, cx, y, t, t0, o = {}) {
  const size = o.size || 160;
  font(g, size, o.w || 700);
  const sp = g.measureText(' ').width, ws = spec.map(([w]) => g.measureText(w).width);
  const tot = ws.reduce((a, b) => a + b, 0) + sp * (spec.length - 1);
  let x = cx - tot / 2; const x0 = x;
  g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  const out = o.out || 0;
  spec.forEach(([w, st], i) => {
    const p = P(t, t0 + i * (o.stagger ?? 0.1), o.dur || 0.75);
    const q = out > 0 ? E.inn(clamp(out * 1.3 - i * 0.06)) : 0;
    if (p > 0.001 && q < 0.999) {
      g.save();
      g.globalAlpha = clamp(p * 1.4) * (1 - q);
      blur(g, (1 - p) * 16 + q * 16);
      g.fillStyle = st === 'grad' ? gradX(g, x0, x0 + tot, (t - t0) * 0.08) : st === 'grey' ? C.grey : C.ink;
      g.fillText(w, x, y + (1 - p) * size * 0.32 - q * size * 0.22);
      g.restore();
    }
    x += ws[i] + sp;
  });
}
// per-letter mask rise
function rise(g, s, cx, y, t, t0, o = {}) {
  const size = o.size || 220;
  font(g, size, o.w || 700);
  const tw = g.measureText(s).width, x0 = cx - tw / 2;
  g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  const out = o.out || 0;
  for (let i = 0; i < s.length; i++) {
    const xi = x0 + g.measureText(s.slice(0, i)).width;
    const p = P(t, t0 + i * (o.stagger ?? 0.03), o.dur || 0.85);
    if (p <= 0) continue;
    g.save();
    g.beginPath(); g.rect(xi - 40, y - size * 1.05, size * 1.6, size * 1.36); g.clip();
    g.globalAlpha = clamp(p * 1.6) * (1 - out); blur(g, out * 14);
    g.fillStyle = o.grad ? gradX(g, x0, x0 + tw, (t - t0) * 0.08) : (o.col || C.ink);
    g.fillText(s[i], xi, y + (1 - p) * size - out * size * 0.2);
    g.restore();
  }
}

// rolling slot: words pass through a feathered window
const slot = mk(W, 640);
function slotWords(g, items, cy, t, size) {
  const sg = slot.g, OY = cy - 360;
  sg.clearRect(0, 0, W, 640);
  items.forEach(([t0, t1, word], i) => {
    const pin = P(t, t0, 0.6), pout = P(t, t1 - 0.08, 0.35, E.io);
    if (pin <= 0 || pout >= 1) return;
    sg.save(); sg.globalAlpha = clamp(pin * 1.3) * (1 - pout); blur(sg, (1 - pin) * 12 + pout * 12);
    font(sg, size, 700); sg.textAlign = 'center'; sg.textBaseline = 'alphabetic'; sg.fillStyle = C.ink;
    sg.fillText(word, W / 2, 360 + size * 0.36 + (1 - pin) * 170 - pout * 170);
    sg.restore();
  });
  sg.save(); sg.globalCompositeOperation = 'destination-in';
  const m = sg.createLinearGradient(0, 0, 0, 640);
  m.addColorStop(0, 'rgba(0,0,0,0)'); m.addColorStop(0.28, 'rgba(0,0,0,1)'); m.addColorStop(0.78, 'rgba(0,0,0,1)'); m.addColorStop(1, 'rgba(0,0,0,0)');
  sg.fillStyle = m; sg.fillRect(0, 0, W, 640); sg.restore();
  g.drawImage(slot, 0, OY);
}

// ================================================================== timeline (beats at 0.5 s)
function drawAt(g, t) {
  g.fillStyle = C.bg; g.fillRect(0, 0, W, H);
  const z = 1 + t * 0.004;
  g.save(); g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
  // 0–2: The OncoXpress
  if (t < 2.4) line(g, [['The', 'grey'], ['OncoXpress', 'grad']], W / 2, 600, t, 0.25, { size: 200, stagger: 0.5, dur: 0.8, out: P(t, 1.8, 0.5, E.io) });
  // 2–4: Band. / Ring. through the slot
  if (t >= 1.9 && t < 4.2) slotWords(g, [[2.0, 3.0, 'Band.'], [3.0, 4.05, 'Ring.']], 540, t, 320);
  // 4–6: Band and Ring.
  if (t >= 3.9 && t < 6.3) line(g, [['Band', 'ink'], ['and', 'grey'], ['Ring.', 'ink']], W / 2, 600, t, 4.0, { size: 210, stagger: 0.12, dur: 0.7, out: P(t, 5.8, 0.5, E.io) });
  // 6–8: Coming soon.
  if (t >= 5.9 && t < 8.3) rise(g, 'Coming soon.', W / 2, 615, t, 6.0, { size: 230, stagger: 0.035, out: P(t, 7.75, 0.45, E.io) });
  // 8–10: end card
  if (t >= 7.9) {
    rise(g, 'OncoXpress', W / 2, 560, t, 8.0, { size: 190, stagger: 0.03, grad: true });
    line(g, [['Band', 'ink'], ['&', 'grey'], ['Ring', 'ink'], ['·', 'grey'], ['Coming', 'grey'], ['soon', 'grey']], W / 2, 690, t, 8.55, { size: 48, w: 600, stagger: 0.04, dur: 0.6 });
  }
  g.restore();
  const fo = P(t, 9.55, 0.45, E.io);
  if (fo > 0) { g.fillStyle = `rgba(255,255,255,${fo})`; g.fillRect(0, 0, W, H); }
}

const grain = mk(256, 256);
(() => { const id = grain.g.createImageData(256, 256); for (let i = 0; i < id.data.length; i += 4) { const v = Math.random() < 0.5 ? 0 : 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 4; } grain.g.putImageData(id, 0, 0); })();

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
  const faces = [500, 600, 700].map(w => new FontFace('Inter Tight', `url(fonts/InterTight-${w}.woff)`, { weight: String(w) }));
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
  });
}
