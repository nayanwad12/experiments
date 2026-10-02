'use strict';
// VIBE EDITING by Ideabro Studio: 40 s launch film. Apple-style minimal layout in a strict
// black / white / neon-green palette, with the Ideabro "IB" monogram.
//
// Time model: scenes are authored in "virtual" seconds on a 120 BPM grid (1 bar = 2 s) and played
// 25% faster, so they land on a 150 BPM grid (1 bar = 1.6 s). Between real 28.8 s and 35.2 s a
// rapid-fire montage (4 bars) plays in real time, then the end card runs at normal speed.
// Real-time cue times are mirrored in audio.py.

const W = 1920, H = 1080, DUR = 40;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 60);
const MB = +(Q.get('mb') || (RENDER ? 4 : 1));   // motion-blur sub-frames
const SHUTTER = 0.5;                                // 180° shutter

const K = 0.8;                       // real seconds per virtual second (120 -> 150 BPM)
const MON0 = 28.8, MON1 = 35.2;      // montage window (real seconds), bars 18-21
const BEAT = 0.4;
function warp(r) { return r < MON0 ? r / K : 36 + (r - MON1); }

const C = {
  bg: '#FFFFFF', black: '#0A0A0A', ink: '#0A0A0A', grey: '#6B6B6B', grey2: '#8C8C8C',
  hair: '#E6E6E6', card: '#F2F2F2', neon: '#39FF14', neonDim: '#2BD40C',
};
// glow ring: neon with white hot-spots
const GLOW = ['#39FF14', '#C9FFBD', '#39FF14', '#FFFFFF', '#39FF14', '#8CFF70'];

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
const E = {
  out: bez(0.16, 1, 0.3, 1),        // Apple-ish expo-out
  io: bez(0.65, 0, 0.35, 1),         // smooth in-out
  inn: bez(0.55, 0, 1, 0.45),
  std: bez(0.25, 0.1, 0.25, 1),
};
// damped spring step response (t in seconds since trigger)
function spring(t, f = 1.4, z = 0.62) {
  if (t <= 0) return 0;
  const w = TAU * f, wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t));
}
function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
function noise1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u) * 2 - 1; }
const P = (t, t0, d = 0.9, e = E.out) => e(inv(t0, t0 + d, t));

// ------------------------------------------------------------------ colour
function hex2rgb(h) { const n = parseInt(h.slice(1), 16); return [n >> 16, n >> 8 & 255, n & 255]; }
function mix(a, b, t) { const A = hex2rgb(a), B = hex2rgb(b); return `rgb(${A.map((v, i) => Math.round(lerp(v, B[i], t))).join(',')})`; }
function rgba(h, a) { const [r, g, b] = hex2rgb(h); return `rgba(${r},${g},${b},${a})`; }
function grey(v) { const h = Math.round(clamp(v) * 255).toString(16).padStart(2, '0'); return '#' + h + h + h; }

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
// o: size, w, col, stagger, dur, dy, bl, a, align ('c' | 'l' | 'r'), track, out (0..1 exit),
//    hl: indices of words that get a neon highlight block wiping in behind them (text turns black),
//    glow: neon glow on the text
function words(g, str, x, y, t, t0, o = {}) {
  const size = o.size || 80;
  font(g, size, o.w || 600, o.track);
  const parts = str.split(' ');
  const sp = g.measureText(' ').width;
  const ws = parts.map(p => g.measureText(p).width);
  const total = ws.reduce((a, b) => a + b, 0) + sp * (parts.length - 1);
  let cx = o.align === 'l' ? x : o.align === 'r' ? x - total : x - total / 2;
  g.textBaseline = 'alphabetic'; g.textAlign = 'left';
  const out = o.out || 0;
  const hl = o.hl || [];
  // highlight blocks (one per contiguous run, so "Zero grind." gets a single bar)
  if (hl.length) {
    let hx = cx, a0 = null;
    const xs = [];
    for (let i = 0; i < parts.length; i++) { xs.push(hx); hx += ws[i] + sp; }
    const first = hl[0], last = hl[hl.length - 1];
    a0 = xs[first]; const a1 = xs[last] + ws[last];
    const pad = size * 0.11;
    const hp = P(t, t0 + first * (o.stagger ?? 0.09) + 0.12, 0.55, E.io);
    const q = out > 0 ? E.inn(clamp(out * 1.3)) : 0;
    if (hp > 0 && q < 1) {
      g.save(); g.globalAlpha = (o.a ?? 1) * (1 - q);
      g.fillStyle = o.hlCol || C.neon;
      rr(g, a0 - pad, y - size * 0.8, (a1 - a0 + pad * 2) * hp, size * 1.02, size * 0.1); g.fill();
      g.restore();
    }
  }
  for (let i = 0; i < parts.length; i++) {
    const p = P(t, t0 + i * (o.stagger ?? 0.09), o.dur || 0.9);
    const q = out > 0 ? E.inn(clamp(out * 1.25 - i * 0.05)) : 0;
    if (p > 0.001 && q < 0.999) {
      g.save();
      g.globalAlpha = (o.a ?? 1) * clamp(p * 1.4) * (1 - q);
      blur(g, (1 - p) * (o.bl ?? 14) + q * 14);
      g.fillStyle = hl.includes(i) ? (o.hlText || C.black) : (o.col || C.ink);
      if (o.glow) { g.shadowColor = rgba(C.neon, 0.75 * o.glow); g.shadowBlur = size * 0.35; }
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

// 4-point AI sparkle
function sparkle(g, x, y, r, rot = 0) {
  g.save(); g.translate(x, y); g.rotate(rot); g.beginPath();
  for (let k = 0; k < 4; k++) {
    const a = k * TAU / 4, b = a + TAU / 8;
    const px = Math.cos(a) * r, py = Math.sin(a) * r, nx = Math.cos(a + TAU / 4) * r, ny = Math.sin(a + TAU / 4) * r;
    if (k === 0) g.moveTo(px, py);
    g.quadraticCurveTo(Math.cos(b) * r * 0.16, Math.sin(b) * r * 0.16, nx, ny);
  }
  g.closePath(); g.restore();
}

// ------------------------------------------------------------------ Ideabro "IB" monogram (traced from the supplied logo; see logo.svg)
const LOGO_I = new Path2D('M651 620 L765 733 L765 1196 L651 1310 Z');
const LOGO_B = new Path2D('M776 621 L1157 621 C1264 621 1350 710 1350 822 C1350 885 1325 935 1291 965 C1325 995 1350 1045 1350 1108 C1350 1220 1260 1310 1150 1310 L889 1310 L889 1196 L1150 1196 C1198 1196 1236 1158 1236 1108 C1236 1058 1198 1022 1150 1022 L773 1022 L773 909 L1145 909 C1195 909 1236 872 1236 822 C1236 772 1198 734 1150 734 L888 734 Z');
const LOGO_W = 699, LOGO_H = 690, LOGO_CX = 651 + LOGO_W / 2, LOGO_CY = 620 + LOGO_H / 2;
// draws the logo centred at (x, y) with height h; returns its width
function logo(g, x, y, h, col, opt = {}) {
  const s = h / LOGO_H;
  g.save(); g.translate(x, y); g.scale(s, s); g.translate(-LOGO_CX, -LOGO_CY);
  g.fillStyle = col;
  if (opt.glow) { g.shadowColor = rgba(C.neon, opt.glow); g.shadowBlur = opt.glowR || 60 / s * 0.6; }
  g.fill(LOGO_I); g.fill(LOGO_B);
  noShadow(g);
  if (opt.sweep != null && opt.sweep > 0 && opt.sweep < 1) {   // neon light sweep clipped to the mark
    const clip = new Path2D(); clip.addPath(LOGO_I); clip.addPath(LOGO_B);
    g.clip(clip);
    const sx = lerp(600, 1400, opt.sweep);
    const gr = g.createLinearGradient(sx - 160, 600, sx + 160, 1320);
    gr.addColorStop(0, rgba(C.neon, 0)); gr.addColorStop(0.5, rgba(C.neon, 0.95)); gr.addColorStop(1, rgba(C.neon, 0));
    g.fillStyle = gr; g.fillRect(600, 600, 800, 740);
  }
  g.restore();
  return LOGO_W * s;
}

// neon edge glow around a rounded rect. k = intensity 0..1
function glowRect(g, x, y, w, h, r, t, k, th = 1) {
  if (k <= 0.002) return;
  const cx = x + w / 2, cy = y + h / 2;
  const cg = g.createConicGradient(t * 2.4, cx, cy);
  const n = GLOW.length;
  for (let i = 0; i <= n; i++) cg.addColorStop(i / n, GLOW[i % n]);
  g.save();
  g.strokeStyle = cg;
  const passes = [[40 * th, 26 * th, 0.6], [14 * th, 9 * th, 0.85], [3.5 * th, 0, 1]];
  for (const [lw, b, a] of passes) {
    g.globalAlpha = a * k; g.lineWidth = lw; blur(g, b * (0.6 + 0.4 * k));
    rr(g, x, y, w, h, r); g.stroke();
  }
  g.restore();
}

// soft neon haze without filters: radial gradients only
function haze(g, t, a, cx = W / 2, cy = H / 2, sx = 1, sy = 1) {
  if (a <= 0.002) return;
  g.save(); g.globalAlpha = a;
  const blobs = [[-380, -40, 520], [60, 60, 480], [420, -30, 460]];
  blobs.forEach(([dx, dy, r], i) => {
    const x = cx + (dx + Math.sin(t * 0.6 + i * 2) * 60) * sx, y = cy + (dy + Math.cos(t * 0.5 + i) * 40) * sy;
    const gr = g.createRadialGradient(x, y, 0, x, y, r * sx);
    gr.addColorStop(0, rgba(C.neon, 0.45)); gr.addColorStop(0.5, rgba(C.neon, 0.12)); gr.addColorStop(1, rgba(C.neon, 0));
    g.fillStyle = gr; g.fillRect(x - r * sx, y - r * sx, r * 2 * sx, r * 2 * sx);
  });
  g.restore();
}

// ================================================================== SCENES (virtual time t)
// 01 OPEN (0–5): "Editing used to mean" + rolling word slot
const slot = mk(W, 520);
const SLOT = [[1.5, 'keyframes.'], [2.25, 'layers.'], [3.0, 'render bars.'], [3.75, 'endless hours.']];
function sOpen(g, t) {
  const drift = 1 + t * 0.006;
  g.save(); g.translate(W / 2, H / 2); g.scale(drift, drift); g.translate(-W / 2, -H / 2);
  words(g, 'Editing used to mean', W / 2, 440, t, 0.45, { size: 64, w: 500, col: C.grey2, stagger: 0.1 });
  // slot words roll through a feathered window (strip layer masked with an alpha gradient)
  const sg = slot.g, OY = 640 - 300;
  sg.clearRect(0, 0, W, 520);
  for (let i = 0; i < SLOT.length; i++) {
    const [t0, s] = SLOT[i];
    const t1 = SLOT[i + 1] ? SLOT[i + 1][0] : 99;
    const pin = P(t, t0 + (i ? 0.06 : 0), 0.75), pout = P(t, t1 - 0.1, 0.4, E.io);
    if (pin <= 0 || pout >= 1) continue;
    sg.save();
    sg.globalAlpha = clamp(pin * 1.3) * (1 - pout);
    blur(sg, (1 - pin) * 14 + pout * 14);
    font(sg, 164, 700); sg.textAlign = 'center'; sg.fillStyle = C.ink;
    const y = 640 - OY + (1 - pin) * 125 - pout * 125;
    sg.fillText(s, W / 2, y);
    if (i === SLOT.length - 1) {          // neon strike through the last word
      const w = sg.measureText(s).width, ps = P(t, 4.25, 0.45, E.io);
      sg.filter = 'none';
      if (ps > 0) { sg.fillStyle = C.neon; sg.fillRect(W / 2 - w / 2 - 14, y - 62, (w + 28) * ps, 18); }
    }
    sg.restore();
  }
  sg.save(); sg.globalCompositeOperation = 'destination-in';
  const m = sg.createLinearGradient(0, 0, 0, 520);
  m.addColorStop(0, 'rgba(0,0,0,0)'); m.addColorStop(0.3, 'rgba(0,0,0,1)'); m.addColorStop(0.72, 'rgba(0,0,0,1)'); m.addColorStop(0.95, 'rgba(0,0,0,0)');
  sg.fillStyle = m; sg.fillRect(0, 0, W, 520); sg.restore();
  g.drawImage(slot, 0, OY);
  g.restore();
}

// 02 PROMPT (4.9–10.2): prompt pill, typed instruction, send, neon edge glow
const PROMPT1 = 'Make it punchy. Fast cuts, bold captions, neon accents.';
const TYPE1 = [5.55, 25];   // start, chars per (virtual) second
const TYPE1_END = TYPE1[0] + PROMPT1.length / TYPE1[1];
function typed(s, t, t0, cps) { return s.slice(0, clamp(Math.floor((t - t0) * cps), 0, s.length)); }
function sendBtn(g, x, y, r, t, tSend, dark = false) {
  const bp = 1 - 0.14 * Math.exp(-Math.pow((t - tSend - 0.03) / 0.07, 2));
  g.save(); g.translate(x, y); g.scale(bp, bp);
  g.fillStyle = t > tSend ? C.neon : (dark ? '#3A3A3A' : C.black);
  g.beginPath(); g.arc(0, 0, r, 0, TAU); g.fill();
  g.strokeStyle = t > tSend ? C.black : '#FFFFFF'; g.lineWidth = r * 0.14; g.lineCap = 'round'; g.lineJoin = 'round';
  const k = r * 0.38;
  g.beginPath(); g.moveTo(0, k); g.lineTo(0, -k); g.moveTo(-k * 0.8, -k * 0.2); g.lineTo(0, -k); g.lineTo(k * 0.8, -k * 0.2); g.stroke();
  g.restore();
}
function sPrompt(g, t) {
  const pw = 1260, ph = 128;
  const sIn = spring(t - 5.0, 1.25, 0.7);
  const exitP = P(t, 8.75, 0.7, E.io);
  const sc = lerp(0.86, 1, sIn) * lerp(1, 0.55, exitP);
  const cy = lerp(600, 560, exitP);
  const a = clamp((t - 5.0) / 0.35) * (1 - P(t, 8.85, 0.45, E.std));

  words(g, 'Now, you just say it.', W / 2, 400, t, 5.15, { size: 80, w: 700, out: P(t, 8.1, 0.6, E.io), stagger: 0.08, hl: [3, 4] });

  const eg = P(t, 8.75, 0.75, E.io) * (1 - P(t, 9.5, 0.75, E.io));
  if (a > 0.001) {
    g.save(); g.translate(W / 2, cy); g.scale(sc, sc); g.globalAlpha = a;
    const x = -pw / 2, y = -ph / 2;
    const gk = P(t, 8.0, 0.5) * (1 - exitP * 0.6);
    glowRect(g, x, y, pw, ph, ph / 2, t, gk, 1.25);
    softShadow(g, 0.10, 70, 26);
    g.fillStyle = '#FFFFFF'; rr(g, x, y, pw, ph, ph / 2); g.fill();
    noShadow(g);
    g.lineWidth = 1.5; g.strokeStyle = C.hair; rr(g, x, y, pw, ph, ph / 2); g.stroke();
    g.fillStyle = C.black; sparkle(g, x + 72, 0, 24, t * 0.8); g.fill();
    g.fillStyle = C.neon; sparkle(g, x + 72, 0, 9, t * 0.8); g.fill();
    const s = typed(PROMPT1, t, TYPE1[0], TYPE1[1]);
    font(g, 40, 500); g.textAlign = 'left'; g.textBaseline = 'middle';
    if (s.length === 0) { g.fillStyle = C.grey2; g.fillText('Describe your edit…', x + 122, 2); }
    else { g.fillStyle = C.ink; g.fillText(s, x + 122, 2); }
    const caretX = x + 122 + (s.length ? g.measureText(s).width + 4 : 0);
    if (t < 8.0 && (Math.floor(t * 2.6) % 2 === 0 || (t > TYPE1[0] && t < TYPE1_END))) { g.fillStyle = C.black; g.fillRect(caretX, -26, 3, 52); g.fillStyle = C.neon; g.fillRect(caretX, 18, 3, 8); }
    sendBtn(g, x + pw - 70, 0, 40, t, 8.0);
    g.restore();
  }
  if (eg > 0.001) {
    const inset = lerp(260, 14, P(t, 8.75, 0.75, E.io));
    glowRect(g, inset, inset * 0.55, W - inset * 2, H - inset * 1.1, 48, t, eg, 2.2);
    haze(g, t, eg * 0.18);
  }
}

// 03 REVEAL (9.4–14.4): Introducing / Vibe Editing / A course by [IB] Ideabro Studio
function sReveal(g, t) {
  const push = 1 + (t - 9.4) * 0.008;
  g.save(); g.translate(W / 2, H / 2); g.scale(push, push); g.translate(-W / 2, -H / 2);
  haze(g, t, 0.10 * P(t, 9.9, 1.6, E.io), W / 2, 520, 1.2, 0.7);
  words(g, 'Introducing', W / 2, 375, t, 9.5, { size: 48, w: 600, col: C.grey, dy: 20, bl: 10 });
  const title = 'Vibe Editing', size = 236;
  font(g, size, 750);
  const tw = g.measureText(title).width, x0 = W / 2 - tw / 2, base = 615;
  // neon block wipes in behind "Editing"
  const ex = x0 + g.measureText('Vibe ').width, ew = g.measureText('Editing').width;
  const hp = P(t, 10.45, 0.6, E.io);
  if (hp > 0) { g.fillStyle = C.neon; rr(g, ex - 30, base - size * 0.8, (ew + 60) * hp, size * 1.06, 22); g.fill(); }
  g.textAlign = 'left';
  for (let i = 0; i < title.length; i++) {
    const xi = x0 + g.measureText(title.slice(0, i)).width;
    const p = P(t, 10.0 + i * 0.035, 1.1);
    if (p > 0) {
      g.save();
      g.beginPath(); g.rect(xi - 40, base - size * 1.05, 400, size * 1.32); g.clip();
      g.globalAlpha = clamp(p * 1.6);
      g.fillStyle = C.black;
      g.fillText(title[i], xi, base + (1 - p) * size);
      g.restore();
    }
  }
  // A course by [IB] Ideabro Studio.
  const y2 = 760, p2 = P(t, 11.5, 1.0);
  if (p2 > 0) {
    font(g, 50, 500); const s1 = 'A course by ', w1 = g.measureText(s1).width;
    font(g, 50, 700); const s2 = 'Ideabro Studio.', w2 = g.measureText(s2).width;
    const lh = 44, lw = lh * LOGO_W / LOGO_H, gap = 16;
    const sx = W / 2 - (w1 + lw + gap + w2) / 2, dy = (1 - p2) * 18;
    g.save(); g.globalAlpha = clamp(p2 * 1.4); blur(g, (1 - p2) * 12);
    font(g, 50, 500); g.textAlign = 'left'; g.fillStyle = C.grey; g.fillText(s1, sx, y2 + dy);
    logo(g, sx + w1 + lw / 2, y2 - 17 + dy, lh, C.black);
    font(g, 50, 700); g.fillStyle = C.black; g.fillText(s2, sx + w1 + lw + gap, y2 + dy);
    g.restore();
  }
  g.restore();
}

// ------------------------------------------------------------------ the "video" inside the editor (procedural landscape, mono grade)
function drawVideo(g, x, y, w, h, t, G, cap = null, capT = 0, capSize = 0.075, karaoke = false) {
  g.save(); rr(g, x, y, w, h, Math.min(w, h) * 0.02); g.clip();
  const sky = g.createLinearGradient(0, y, 0, y + h);
  sky.addColorStop(0, mix('#8E8E8E', '#030303', G));
  sky.addColorStop(0.58, mix('#AFAFAF', '#5A5A5A', G));
  sky.addColorStop(1, mix('#C2C2C2', '#F2F2F2', G));
  g.fillStyle = sky; g.fillRect(x, y, w, h);
  const sx = x + w * 0.66, sy = y + h * (0.5 - G * 0.02);
  const halo = g.createRadialGradient(sx, sy, 0, sx, sy, w * 0.42);
  halo.addColorStop(0, `rgba(57,255,20,${0.55 * G})`); halo.addColorStop(0.35, `rgba(57,255,20,${0.16 * G})`); halo.addColorStop(1, 'rgba(57,255,20,0)');
  g.fillStyle = halo; g.fillRect(x, y, w, h);
  const wh = g.createRadialGradient(sx, sy, 0, sx, sy, w * 0.3);
  wh.addColorStop(0, `rgba(255,255,255,${lerp(0.35, 0.5, G)})`); wh.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = wh; g.fillRect(x, y, w, h);
  g.fillStyle = '#FFFFFF'; g.beginPath(); g.arc(sx, sy, w * 0.055, 0, TAU); g.fill();
  const layers = [['#7C7C7C', '#202020', 0.62, 0.12, 4], ['#6A6A6A', '#121212', 0.72, 0.09, 7], ['#565656', '#000000', 0.84, 0.06, 13]];
  layers.forEach(([c0, c1, hy, amp, sp], li) => {
    g.fillStyle = mix(c0, c1, G);
    g.beginPath(); g.moveTo(x, y + h);
    for (let i = 0; i <= 48; i++) {
      const u = i / 48, X = u * w + x;
      const k = u * (3 + li * 2) + t * 0.03 * sp + li * 10;
      g.lineTo(X, y + h * (hy - amp * (0.6 * noise1(k) + 0.4 * noise1(k * 2.3 + 5))));
    }
    g.lineTo(x + w, y + h); g.closePath(); g.fill();
  });
  const vg = g.createRadialGradient(x + w / 2, y + h / 2, h * 0.3, x + w / 2, y + h / 2, w * 0.75);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, `rgba(0,0,0,${0.5 * G})`);
  g.fillStyle = vg; g.fillRect(x, y, w, h);
  const lb = h * 0.11 * clamp(G * 1.2 - 0.1);
  g.fillStyle = '#000'; g.fillRect(x, y, w, lb); g.fillRect(x, y + h - lb, w, lb);
  if (cap) {
    const ws = cap.split(' ');
    const fs = h * capSize;
    font(g, fs, 800, 0); g.textAlign = 'left'; g.textBaseline = 'middle';
    const sp = g.measureText(' ').width, wl = ws.map(s => g.measureText(s).width);
    const tot = wl.reduce((a, b) => a + b) + sp * (ws.length - 1);
    let cx = x + w / 2 - tot / 2; const cy = y + h * 0.78;
    ws.forEach((s, i) => {
      const p = spring(capT - i * 0.13, 2.4, 0.55);
      if (p > 0.01) {
        g.save(); g.globalAlpha = clamp(p);
        const on = karaoke ? Math.floor(capT / 0.26) % ws.length === i : capT >= i * 0.13 && capT < (i + 1) * 0.13 + 0.1;
        g.translate(cx + wl[i] / 2, cy); g.scale(lerp(0.6, 1, p), lerp(0.6, 1, p));
        if (on) { g.fillStyle = C.neon; rr(g, -wl[i] / 2 - fs * 0.18, -fs * 0.62, wl[i] + fs * 0.36, fs * 1.2, fs * 0.22); g.fill(); }
        g.shadowColor = 'rgba(0,0,0,0.4)'; g.shadowBlur = on ? 0 : 8;
        g.fillStyle = on ? '#000' : '#FFF'; g.fillText(s, -wl[i] / 2, 2);
        g.restore();
      }
      cx += wl[i] + sp;
    });
  }
  g.restore();
}

// ------------------------------------------------------------------ editor UI (drawn into the laptop screen)
const SW = 1148, SH = 718;
const scr = mk(SW, SH);
const PROMPT2 = 'high-contrast mono grade, cut to the beat';
const T2 = [15.85, 24];   // typing start, cps
const SEND2 = 18.0;
const CLIPS_A = [[0, 210], [210, 330], [330, 610], [610, 770], [770, 1060]];
const CLIPS_BW = [132, 132, 66, 66, 132, 132, 132, 132, 66, 66, 132];
const CLIPS_B = (() => { const out = []; let x = 0; for (const k of CLIPS_BW) { out.push([x, x + k]); x += k; } return out; })();
function drawEditor(t) {
  const g = scr.g; g.save();
  g.fillStyle = '#0B0B0B'; g.fillRect(0, 0, SW, SH);
  const G = E.io(inv(SEND2 + 0.1, SEND2 + 1.2, t));
  // toolbar
  g.fillStyle = '#161616'; g.fillRect(0, 0, SW, 44);
  [0, 1, 2].forEach(i => { g.fillStyle = '#3A3A3A'; g.beginPath(); g.arc(22 + i * 22, 22, 7, 0, TAU); g.fill(); });
  text(g, 'Launch Reel — Vibe Editor', SW / 2, 28, { size: 15, w: 600, col: '#9A9A9A', track: 0 });
  // sidebar
  g.fillStyle = '#121212'; g.fillRect(0, 44, 230, 426);
  text(g, 'Library', 18, 76, { size: 14, w: 700, col: '#8C8C8C', align: 'left', track: 0 });
  for (let i = 0; i < 8; i++) {
    const cx = 18 + (i % 2) * 104, cy = 92 + Math.floor(i / 2) * 72;
    const gr = g.createLinearGradient(cx, cy, cx + 94, cy + 58);
    gr.addColorStop(0, grey(0.25 + 0.5 * hash(i * 3.1))); gr.addColorStop(1, grey(0.06 + 0.15 * hash(i * 7.7)));
    g.fillStyle = gr; rr(g, cx, cy, 94, 58, 7); g.fill();
    if (i === 2) { g.strokeStyle = C.neon; g.lineWidth = 2; rr(g, cx - 1, cy - 1, 96, 60, 8); g.stroke(); }
  }
  // viewer
  g.fillStyle = '#070707'; g.fillRect(230, 44, 698, 426);
  const vx = 259, vy = 70, vw = 640, vh = 360;
  const capT = t - (SEND2 + 1.4);
  drawVideo(g, vx, vy, vw, vh, t, G, capT > 0 ? 'Built for the bold.' : null, capT, 0.085);
  // in-viewer prompt pill
  const pa = clamp((t - 15.4) / 0.3) * (1 - P(t, SEND2 + 0.15, 0.4, E.std));
  if (pa > 0.001) {
    const pw = 540, ph = 46, px = vx + vw / 2 - pw / 2, py = vy + vh - ph - 18 + (1 - spring(t - 15.4, 1.6, 0.7)) * 20;
    g.save(); g.globalAlpha = pa;
    glowRect(g, px, py, pw, ph, ph / 2, t, P(t, SEND2 - 0.05, 0.25) * 0.9, 0.45);
    g.fillStyle = 'rgba(26,26,26,0.9)'; rr(g, px, py, pw, ph, ph / 2); g.fill();
    g.strokeStyle = 'rgba(255,255,255,0.14)'; g.lineWidth = 1; rr(g, px, py, pw, ph, ph / 2); g.stroke();
    g.fillStyle = C.neon; sparkle(g, px + 26, py + ph / 2, 10, t); g.fill();
    const s = typed(PROMPT2, t, T2[0], T2[1]);
    font(g, 17, 500, 0); g.textAlign = 'left'; g.textBaseline = 'middle';
    g.fillStyle = s ? '#F2F2F2' : '#8C8C8C'; g.fillText(s || 'Ask for any edit…', px + 46, py + ph / 2 + 1);
    if (Math.floor(t * 2.6) % 2 === 0 || (t > T2[0] && t < T2[0] + PROMPT2.length / T2[1])) { g.fillStyle = C.neon; g.fillRect(px + 48 + (s ? g.measureText(s).width : -2), py + 13, 2, 21); }
    sendBtn(g, px + pw - 23, py + ph / 2, 15, t, SEND2, true);
    g.restore();
  }
  // inspector
  g.fillStyle = '#121212'; g.fillRect(928, 44, 220, 426);
  text(g, 'Inspector', 946, 76, { size: 14, w: 700, col: '#8C8C8C', align: 'left', track: 0 });
  const sl = [['Contrast', 0.4, 0.9], ['Grain', 0.15, 0.55], ['Sharpness', 0.45, 0.78], ['Tempo sync', 0.1, 1.0]];
  sl.forEach(([n, a, b], i) => {
    const y = 112 + i * 64, v = lerp(a, b, E.io(inv(SEND2 + 0.2 + i * 0.12, SEND2 + 1.1 + i * 0.12, t)));
    text(g, n, 946, y, { size: 13, w: 500, col: '#C7C7C7', align: 'left', track: 0 });
    text(g, Math.round(v * 100) + '', 1130, y, { size: 13, w: 600, col: '#8C8C8C', align: 'right', track: 0 });
    g.fillStyle = '#2E2E2E'; rr(g, 946, y + 14, 184, 4, 2); g.fill();
    g.fillStyle = C.neon; rr(g, 946, y + 14, 184 * v, 4, 2); g.fill();
    g.fillStyle = '#FFF'; g.beginPath(); g.arc(946 + 184 * v, y + 16, 7, 0, TAU); g.fill();
  });
  // timeline
  const ty = 470;
  g.fillStyle = '#0E0E0E'; g.fillRect(0, ty, SW, SH - ty);
  g.fillStyle = '#222'; g.fillRect(0, ty, SW, 1);
  const X0 = 74, TW = 1060;
  for (let i = 0; i <= 40; i++) {
    const x = X0 + i * TW / 40;
    g.fillStyle = '#444'; g.fillRect(x, ty + 10, 1, i % 4 === 0 ? 12 : 6);
    if (i % 8 === 0) text(g, `00:0${i / 8}`, x + 4, ty + 22, { size: 10, w: 500, col: '#8C8C8C', align: 'left', track: 0 });
  }
  [['T1', 506, 30], ['V1', 544, 56], ['A1', 608, 44], ['A2', 660, 36]].forEach(([n, y, h]) => {
    g.fillStyle = '#161616'; g.fillRect(0, y, 64, h);
    text(g, n, 32, y + h / 2 + 5, { size: 12, w: 700, col: '#8C8C8C', track: 0 });
  });
  // V1 clips morph: 5 uneven grey clips -> 11 beat-cut clips (accent cuts in neon)
  for (let i = 0; i < CLIPS_B.length; i++) {
    const k = E.io(inv(SEND2 + 0.25 + i * 0.05, SEND2 + 0.95 + i * 0.05, t));
    const A = CLIPS_A[Math.min(i, CLIPS_A.length - 1)], B = CLIPS_B[i];
    const a0 = i < CLIPS_A.length ? A[0] : 1060, a1 = i < CLIPS_A.length ? A[1] : 1060;
    const x0 = X0 + lerp(a0, B[0], k) + 1.5, x1 = X0 + lerp(a1, B[1], k) - 1.5;
    if (x1 - x0 < 1) continue;
    const before = grey(0.24 + 0.12 * hash(i + 2));
    const after = CLIPS_BW[i] === 66 ? C.neon : grey(0.62 + 0.25 * hash(i * 5.3));
    const gr = g.createLinearGradient(x0, 0, x1, 0);
    gr.addColorStop(0, mix(before, rgbHex(after), G)); gr.addColorStop(1, mix(before, rgbHex(after), G * 0.7));
    g.fillStyle = gr; rr(g, x0, 547, x1 - x0, 50, 6); g.fill();
    g.strokeStyle = 'rgba(255,255,255,0.14)'; g.lineWidth = 1; rr(g, x0, 547, x1 - x0, 50, 6); g.stroke();
  }
  const tg = E.io(inv(SEND2 + 1.2, SEND2 + 1.8, t));
  if (tg > 0) { g.fillStyle = C.neon; rr(g, X0 + 132, 509, 528 * tg, 24, 5); g.fill(); text(g, 'Captions', X0 + 142, 526, { size: 11, w: 800, col: '#000', align: 'left', track: 0 }); }
  g.save(); rr(g, X0, 611, TW, 38, 6); g.clip();
  g.fillStyle = 'rgba(57,255,20,0.12)'; g.fillRect(X0, 611, TW, 38);
  g.fillStyle = C.neon;
  for (let i = 0; i < 212; i++) {
    const x = X0 + i * 5, beat = Math.exp(-((i % 26.5) / 3));
    const a = (0.25 + 0.55 * Math.abs(noise1(i * 0.7)) + 0.5 * beat * G) * 17;
    g.fillRect(x, 630 - a, 2.4, a * 2);
  }
  g.restore();
  g.fillStyle = 'rgba(255,255,255,0.10)'; rr(g, X0, 663, TW, 30, 6); g.fill();
  g.strokeStyle = '#D9D9D9'; g.lineWidth = 1.5; g.beginPath();
  for (let i = 0; i <= 200; i++) { const x = X0 + i * TW / 200; g.lineTo(x, 678 + Math.sin(i * 0.35) * 6 * Math.sin(i * 0.05)); }
  g.stroke();
  for (let i = 0; i <= 16; i++) {
    const k = P(t, SEND2 + 0.4 + i * 0.03, 0.4);
    if (k <= 0) continue;
    g.fillStyle = `rgba(57,255,20,${k})`; const x = X0 + i * 66.25;
    g.beginPath(); g.moveTo(x, ty + 26); g.lineTo(x + 4, ty + 30); g.lineTo(x, ty + 34); g.lineTo(x - 4, ty + 30); g.fill();
  }
  const ph = X0 + ((t - 14.0) * 132) % TW;
  g.fillStyle = '#FFFFFF'; g.fillRect(ph - 1, ty + 4, 2, SH - ty - 8);
  g.beginPath(); g.moveTo(ph - 7, ty + 4); g.lineTo(ph + 7, ty + 4); g.lineTo(ph, ty + 13); g.fill();
  const gw = P(t, SEND2, 0.35) * (1 - P(t, SEND2 + 1.0, 0.9, E.io));
  glowRect(g, 4, 4, SW - 8, SH - 8, 14, t, gw, 0.8);
  g.restore();
}
function rgbHex(s) { if (s[0] === '#') return s; const m = s.match(/\d+/g); return '#' + m.slice(0, 3).map(v => (+v).toString(16).padStart(2, '0')).join(''); }

// 04 DEVICE (13.6–23.6)
function laptop(g, t, cx, top, s, tilt) {
  const bw = SW + 32, bh = SH + 34;
  g.save(); g.translate(cx, top); g.scale(s, s * tilt);
  const sh = g.createRadialGradient(0, bh + 40, 0, 0, bh + 40, bw * 0.62);
  sh.addColorStop(0, 'rgba(0,0,0,0.18)'); sh.addColorStop(1, 'rgba(0,0,0,0)');
  g.save(); g.scale(1, 0.09); g.fillStyle = sh; g.beginPath(); g.arc(0, (bh + 40) / 0.09, bw * 0.62, 0, TAU); g.fill(); g.restore();
  softShadow(g, 0.16, 80, 40);
  g.fillStyle = '#0A0A0A'; rr(g, -bw / 2, 0, bw, bh, 30); g.fill();
  noShadow(g);
  g.strokeStyle = '#BDBDBD'; g.lineWidth = 3; rr(g, -bw / 2 - 1.5, -1.5, bw + 3, bh + 3, 31.5); g.stroke();
  g.strokeStyle = '#3A3A3A'; g.lineWidth = 1.5; rr(g, -bw / 2 + 1, 1, bw - 2, bh - 2, 29); g.stroke();
  g.save(); rr(g, -SW / 2, 16, SW, SH, 12); g.clip();
  g.drawImage(scr, -SW / 2, 16);
  const rf = g.createLinearGradient(-SW / 2, 16, SW / 2, 16 + SH);
  rf.addColorStop(0, 'rgba(255,255,255,0.07)'); rf.addColorStop(0.45, 'rgba(255,255,255,0.0)'); rf.addColorStop(1, 'rgba(255,255,255,0.02)');
  g.fillStyle = rf; g.fillRect(-SW / 2, 16, SW, SH);
  g.restore();
  g.fillStyle = '#0A0A0A'; rr(g, -78, 8, 156, 26, 10); g.fill();
  g.fillStyle = '#222'; g.beginPath(); g.arc(0, 19, 4, 0, TAU); g.fill();
  const hb = g.createLinearGradient(0, bh, 0, bh + 12);
  hb.addColorStop(0, '#3A3A3A'); hb.addColorStop(1, '#8E8E8E');
  g.fillStyle = hb; rr(g, -bw / 2 + 40, bh - 2, bw - 80, 12, 3); g.fill();
  const BW = bw * 1.17, BY = bh + 8;
  const bg = g.createLinearGradient(0, BY, 0, BY + 26);
  bg.addColorStop(0, '#F2F2F2'); bg.addColorStop(0.35, '#DADADA'); bg.addColorStop(1, '#A8A8A8');
  g.fillStyle = bg; g.beginPath();
  g.moveTo(-BW / 2, BY); g.lineTo(BW / 2, BY); g.lineTo(BW / 2 - 6, BY + 18);
  g.quadraticCurveTo(BW / 2 - 24, BY + 26, BW / 2 - 60, BY + 26); g.lineTo(-BW / 2 + 60, BY + 26);
  g.quadraticCurveTo(-BW / 2 + 24, BY + 26, -BW / 2 + 6, BY + 18); g.closePath(); g.fill();
  g.fillStyle = 'rgba(0,0,0,0.12)'; rr(g, -110, BY, 220, 9, [0, 0, 8, 8]); g.fill();
  g.fillStyle = 'rgba(255,255,255,0.9)'; g.fillRect(-BW / 2 + 8, BY, BW - 16, 1.5);
  g.restore();
}
function sDevice(g, t) {
  drawEditor(t);
  const rise = spring(t - 14.0, 0.9, 0.78);
  const push = lerp(0.94, 1.0, E.io(inv(14.0, 23.0, t)));
  const s = 0.93 * push;
  const top = lerp(1180, 226, rise) + (1 - push) * 90;
  const tilt = lerp(0.72, 1, clamp(rise));
  words(g, 'Just describe the vibe.', W / 2, 150, t, 14.45, { size: 72, w: 700, out: P(t, 17.75, 0.55, E.io) });
  words(g, 'AI handles the edit.', W / 2, 150, t, 18.35, { size: 72, w: 700, hl: [0] });
  laptop(g, t, W / 2, top, s, tilt);
}

// 05 BENTO (23.2–32.2): what you'll master
const CARDS = [
  { x: 160, y: 260, w: 760, h: 350, title: 'AI Captions', sub: 'Word-perfect and auto-styled.', fn: cardCaptions },
  { x: 944, y: 260, w: 388, h: 350, title: 'Motion Graphics', sub: 'Type and shapes that move.', fn: cardMotion },
  { x: 1356, y: 260, w: 404, h: 350, title: 'Color Grading', sub: 'Any mood, one prompt.', fn: cardGrade },
  { x: 160, y: 634, w: 500, h: 350, title: 'Smart Cuts', sub: 'Every cut lands on the beat.', fn: cardCuts },
  { x: 684, y: 634, w: 388, h: 350, title: 'Sound Design', sub: 'Music, SFX and mix.', fn: cardSound },
  { x: 1096, y: 634, w: 664, h: 350, title: 'Prompt Workflows', sub: 'Direct AI like a senior editor.', fn: cardPrompt },
];
const CARD_T = [24.0, 24.25, 24.5, 24.75, 25.0, 25.25];
function cardCaptions(g, c, t) {
  const cyc = ((t - 24.0) % 2.4 + 2.4) % 2.4;
  drawVideo(g, c.x + 28, c.y + 28, c.w - 56, c.h - 140, t, 1, 'Captions that land on every word', cyc, 0.12, cyc > 0.9);
}
function cardMotion(g, c, t) {
  const cx = c.x + c.w / 2, cy = c.y + 120;
  const b = (t - 24) * 2, ph = b % 1, bi = Math.floor(b);
  for (let i = 0; i < 3; i++) {
    const a = TAU * (i / 3) + E.io(clamp(ph * 1.6)) * TAU / 3 + bi * TAU / 3;
    const r = 66 + 10 * Math.sin(t * 2 + i);
    const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r * 0.85;
    const sq = 1 + 0.25 * Math.exp(-ph * 6);
    g.save(); g.translate(x, y); g.rotate(a + t); g.scale(sq, 1 / sq);
    if (i === 0) { g.fillStyle = C.neon; g.beginPath(); g.arc(0, 0, 34, 0, TAU); g.fill(); }
    else if (i === 1) { g.fillStyle = C.black; rr(g, -30, -30, 60, 60, 16); g.fill(); }
    else { g.strokeStyle = C.black; g.lineWidth = 9; g.lineJoin = 'round'; g.beginPath(); g.moveTo(0, -36); g.lineTo(32, 26); g.lineTo(-32, 26); g.closePath(); g.stroke(); }
    g.restore();
  }
}
function cardGrade(g, c, t) {
  // curves editor: diagonal eases into a punchy S-curve and back
  const x0 = c.x + 60, y0 = c.y + 30, s = 180, k = 0.5 + 0.5 * Math.sin((t - 24) * 1.6);
  g.strokeStyle = '#D6D6D6'; g.lineWidth = 1;
  for (let i = 0; i <= 4; i++) { g.beginPath(); g.moveTo(x0 + i * s / 4, y0); g.lineTo(x0 + i * s / 4, y0 + s); g.moveTo(x0, y0 + i * s / 4); g.lineTo(x0 + s, y0 + i * s / 4); g.stroke(); }
  const gr = g.createLinearGradient(x0, 0, x0 + s, 0); gr.addColorStop(0, '#000'); gr.addColorStop(1, '#FFF');
  g.fillStyle = gr; rr(g, x0, y0 + s + 14, s, 12, 6); g.fill();
  g.strokeStyle = 'rgba(0,0,0,0.12)'; rr(g, x0, y0 + s + 14, s, 12, 6); g.stroke();
  const p1 = [x0 + s * 0.25, y0 + s - s * lerp(0.25, 0.1, k)], p2 = [x0 + s * 0.75, y0 + s - s * lerp(0.75, 0.92, k)];
  g.strokeStyle = C.neonDim; g.lineWidth = 5; g.lineCap = 'round';
  g.beginPath(); g.moveTo(x0, y0 + s); g.bezierCurveTo(p1[0] + 10, p1[1], p2[0] - 10, p2[1], x0 + s, y0); g.stroke();
  g.strokeStyle = C.black; g.lineWidth = 1.5; g.beginPath(); g.moveTo(x0, y0 + s); g.bezierCurveTo(p1[0] + 10, p1[1], p2[0] - 10, p2[1], x0 + s, y0); g.stroke();
  for (const [px, py] of [p1, p2]) { g.fillStyle = '#FFF'; g.beginPath(); g.arc(px, py, 9, 0, TAU); g.fill(); g.strokeStyle = C.black; g.lineWidth = 2.5; g.stroke(); }
  // mini before/after swatch
  const bx = x0 + s + 30, by = y0 + 10;
  g.fillStyle = mix('#9A9A9A', '#0A0A0A', k); rr(g, bx, by, 64, 76, 10); g.fill();
  g.fillStyle = mix('#B8B8B8', '#FFFFFF', k); rr(g, bx, by + 86, 64, 76, 10); g.fill();
  g.strokeStyle = 'rgba(0,0,0,0.1)'; rr(g, bx, by + 86, 64, 76, 10); g.stroke();
}
function cardCuts(g, c, t) {
  const x0 = c.x + 34, x1 = c.x + c.w - 34, cy = c.y + 118, n = 64, dx = (x1 - x0) / n;
  const b = (t - 24) * 2;
  for (let i = 0; i < n; i++) {
    const beat = Math.exp(-((i % 8)) / 1.6);
    const a = 12 + 50 * (0.35 * Math.abs(noise1(i * 0.8 + 3)) + 0.65 * beat);
    g.fillStyle = (i % 8 === 0) ? C.black : '#C4C4C4';
    rr(g, x0 + i * dx + 1, cy - a, dx - 3, a * 2, 2); g.fill();
  }
  for (let k = 0; k < 8; k++) {
    const p = P(b, 1 + k * 0.5, 0.8);
    if (p <= 0) continue;
    const x = x0 + k * 8 * dx - 1;
    g.globalAlpha = p; g.fillStyle = C.black; g.fillRect(x, cy - 80 * p, 3, 160 * p);
    g.fillStyle = C.neon; g.beginPath(); g.arc(x + 1.5, cy - 80 * p - 9, 9, 0, TAU); g.fill();
    g.strokeStyle = C.black; g.lineWidth = 2; g.stroke(); g.globalAlpha = 1;
  }
}
function cardSound(g, c, t) {
  const n = 13, bw = 16, gap = 10, tot = n * bw + (n - 1) * gap, x0 = c.x + c.w / 2 - tot / 2, base = c.y + 200;
  const b = (t - 24) * 2, kick = Math.exp(-(b % 1) * 4);
  for (let i = 0; i < n; i++) {
    const env = Math.exp(-Math.pow((i - 6) / 4.2, 2));
    const h = 18 + 140 * env * (0.45 + 0.35 * kick + 0.25 * Math.abs(noise1(t * 5 + i * 1.7)));
    g.fillStyle = C.black; rr(g, x0 + i * (bw + gap), base - h, bw, h, bw / 2); g.fill();
    g.fillStyle = C.neon; g.beginPath(); g.arc(x0 + i * (bw + gap) + bw / 2, base - h + bw / 2, bw / 2 - 2, 0, TAU); g.fill();
  }
}
const PROMPTS3 = ['zoom in on the punchline', 'add film grain', 'sync every cut to the drop'];
function cardPrompt(g, c, t) {
  const pw = c.w - 96, ph = 76, px = c.x + 48, py = c.y + 84;
  const lt = t - 25.2, per = 2.0, k = Math.max(0, Math.floor(lt / per)) % PROMPTS3.length, lk = lt - Math.floor(Math.max(0, lt) / per) * per;
  const s = lt < 0 ? '' : typed(PROMPTS3[k], lk, 0.1, 26);
  const sent = lk > 1.25 && lt > 0;
  glowRect(g, px, py, pw, ph, ph / 2, t, sent ? clamp((lk - 1.25) / 0.2) * (1 - clamp((lk - 1.7) / 0.3)) : 0, 0.75);
  softShadow(g, 0.08, 30, 10);
  g.fillStyle = '#FFF'; rr(g, px, py, pw, ph, ph / 2); g.fill(); noShadow(g);
  g.fillStyle = C.black; sparkle(g, px + 44, py + ph / 2, 16, t * 0.7); g.fill();
  g.fillStyle = C.neon; sparkle(g, px + 44, py + ph / 2, 6, t * 0.7); g.fill();
  font(g, 26, 500, 0); g.textAlign = 'left'; g.textBaseline = 'middle';
  g.fillStyle = s ? C.ink : C.grey2; g.fillText(s || 'Describe your edit…', px + 80, py + ph / 2 + 1);
  if (!sent && (Math.floor(t * 2.6) % 2 === 0 || (lk > 0.1 && lk < 1.2))) { g.fillStyle = C.black; g.fillRect(px + 82 + (s ? g.measureText(s).width : -2), py + 22, 2.5, 32); }
  sendBtn(g, px + pw - 40, py + ph / 2, 24, lt < 0 ? 0 : lk, 1.25);
}
function sBento(g, t) {
  const z = lerp(1.035, 1.0, E.out(inv(23.4, 31.5, t)));
  g.save(); g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
  words(g, 'What you’ll master', W / 2, 112, t, 23.4, { size: 30, w: 600, col: C.grey, dy: 12, bl: 8 });
  words(g, 'Pro edits. Zero grind.', W / 2, 205, t, 23.55, { size: 80, w: 700, stagger: 0.08, hl: [2, 3] });
  const out = P(t, 31.35, 0.6, E.io);
  CARDS.forEach((c, i) => {
    const sp = spring(t - CARD_T[i], 1.35, 0.68);
    if (sp <= 0.001) return;
    const o = clamp(out * 1.4 - (i % 3) * 0.12);
    const a = clamp((t - CARD_T[i]) / 0.25) * (1 - o);
    if (a <= 0.002) return;
    const sc = lerp(0.9, 1, sp) * lerp(1, 0.94, o);
    const dy = (1 - sp) * 120 + o * 40;
    g.save(); g.globalAlpha = a;
    g.translate(c.x + c.w / 2, c.y + c.h / 2 + dy); g.scale(sc, sc); g.translate(-(c.x + c.w / 2), -(c.y + c.h / 2));
    g.fillStyle = C.card; rr(g, c.x, c.y, c.w, c.h, 32); g.fill();
    g.save(); rr(g, c.x, c.y, c.w, c.h, 32); g.clip();
    c.fn(g, c, t);
    g.restore();
    text(g, c.title, c.x + 34, c.y + c.h - 62, { size: 32, w: 700, align: 'left' });
    text(g, c.sub, c.x + 34, c.y + c.h - 28, { size: 22, w: 500, col: C.grey, align: 'left', track: 0 });
    g.restore();
  });
  g.restore();
}

// 06 STATEMENT (31.8–36): "Less timeline." on white, then black floods up and "More vibe." glows neon
function sStatement(g, t) {
  const z = 1 + (t - 31.8) * 0.012;
  const wp = P(t, 32.85, 0.4, E.io);
  const ly = 500, my = 700;
  const drawLess = col => words(g, 'Less timeline.', W / 2, ly, t, 32.0, { size: 176, w: 750, col, stagger: 0.12, dur: 1.0 });
  g.save(); g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
  drawLess(C.black);
  g.restore();
  if (wp > 0) {
    const top = H * (1 - wp);
    g.fillStyle = C.black; g.fillRect(0, top, W, H - top);
    g.save(); g.beginPath(); g.rect(0, top, W, H - top); g.clip();
    g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
    drawLess('#4A4A4A');
    words(g, 'More vibe.', W / 2, my, t, 33.0, { size: 176, w: 750, col: C.neon, stagger: 0.12, dur: 1.0, glow: 0.9 });
    g.restore();
  }
}

// 07 END CARD (virtual 36–40.8, i.e. real 35.2–40): black, IB logo, title, CTA
function sEnd(g, t) {
  g.fillStyle = C.black; g.fillRect(0, 0, W, H);
  haze(g, t, 0.07, W / 2, 380, 0.8, 0.5);
  const ip = spring(t - 36.0, 1.1, 0.6);
  const ia = clamp((t - 36.0) / 0.25);
  const iy = lerp(372, 360, E.io(inv(36.0, 40.4, t)));
  if (ia > 0) {
    g.save(); g.globalAlpha = ia; blur(g, (1 - clamp(ip)) * 10);
    g.translate(W / 2, iy); g.scale(lerp(0.5, 1, ip), lerp(0.5, 1, ip));
    const pulse = 0.35 + 0.25 * Math.exp(-(t - 36.0) / 0.5);
    logo(g, 0, 0, 230, '#FFFFFF', { glow: pulse, glowR: 70, sweep: inv(36.55, 37.45, t) });
    g.restore();
  }
  words(g, 'Vibe Editing', W / 2, 640, t, 36.45, { size: 128, w: 750, col: '#FFFFFF', stagger: 0.1 });
  words(g, 'by Ideabro Studio', W / 2, 716, t, 36.95, { size: 44, w: 500, col: C.grey2, stagger: 0.08 });
  const bp = spring(t - 37.5, 1.3, 0.7), ba = clamp((t - 37.5) / 0.3);
  if (ba > 0) {
    font(g, 34, 650, 0);
    const label = 'Enroll now', lw = g.measureText(label).width, bw = lw + 84, bh = 78;
    font(g, 34, 600, 0);
    const link = 'Learn more', ll = g.measureText(link).width + 30;
    const gap = 44, tot = bw + gap + ll, x0 = W / 2 - tot / 2, y = 852;
    g.save(); g.globalAlpha = ba; g.translate(0, (1 - bp) * 30);
    g.shadowColor = rgba(C.neon, 0.45); g.shadowBlur = 36;
    g.fillStyle = C.neon; rr(g, x0, y - bh / 2, bw, bh, bh / 2); g.fill(); noShadow(g);
    font(g, 34, 650, 0); g.fillStyle = C.black; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(label, x0 + bw / 2, y + 1);
    g.globalAlpha = ba * clamp((t - 37.75) / 0.3);
    font(g, 34, 600, 0); g.fillStyle = '#FFFFFF'; g.textAlign = 'left'; g.fillText(link, x0 + bw + gap, y + 1);
    const cx = x0 + bw + gap + ll - 12;
    g.strokeStyle = C.neon; g.lineWidth = 3.5; g.lineCap = 'round'; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(cx - 6, y - 10); g.lineTo(cx + 3, y + 1); g.lineTo(cx - 6, y + 12); g.stroke();
    g.restore();
  }
  const fo = P(t, 40.35, 0.45, E.io);
  if (fo > 0) { g.fillStyle = `rgba(10,10,10,${fo})`; g.fillRect(0, 0, W, H); }
}

// ================================================================== 08 MONTAGE (real time u = 0..6.4, 16 beats @150 BPM)
const MON = [['Captions.', 'W'], ['Cuts.', 'B'], ['Color.', 'N'], ['Motion.', 'W'], ['Sound.', 'B'], ['Titles.', 'N'], ['Transitions.', 'W'], ['Prompts.', 'B']];
const BGC = { W: '#FFFFFF', B: C.black, N: C.neon };
const FGC = { W: C.black, B: '#FFFFFF', N: C.black };
function brackets(g, col, inset, len, lw) {
  g.strokeStyle = col; g.lineWidth = lw; g.lineCap = 'square';
  for (const [x, y, sx, sy] of [[inset, inset, 1, 1], [W - inset, inset, -1, 1], [inset, H - inset, 1, -1], [W - inset, H - inset, -1, -1]]) {
    g.beginPath(); g.moveTo(x, y + sy * len); g.lineTo(x, y); g.lineTo(x + sx * len, y); g.stroke();
  }
}
function sMontage(g, u) {
  const b = Math.min(15, Math.floor(u / BEAT + 1e-6)), lu = Math.max(0, u - b * BEAT);
  if (b < 8) {
    const [word, k] = MON[b];
    const bg = BGC[k], fg = FGC[k], acc = k === 'N' ? C.black : C.neon;
    g.fillStyle = bg; g.fillRect(0, 0, W, H);
    const p = E.out(clamp(lu / 0.22));
    const s = lerp(1.28, 1, p) * (1 + lu * 0.06);
    g.save(); g.translate(W / 2, H / 2 + 20); g.scale(s, s);
    blur(g, (1 - p) * 6);
    font(g, 250, 800); g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillStyle = fg; g.fillText(word, 0, 0);
    const tw = g.measureText(word).width;
    g.filter = 'none';
    g.fillStyle = acc; g.fillRect(-tw / 2, 120, tw * E.out(clamp(lu / 0.3)), 14);
    g.restore();
    brackets(g, acc, 56, 46, 5);
    font(g, 26, 700, 2); g.textBaseline = 'alphabetic';
    g.fillStyle = fg; g.textAlign = 'left'; g.fillText(`0${b + 1} / 08`, 78, 112);
    g.textAlign = 'right'; g.fillText('VIBE EDITING', W - 78, 112);
    // progress
    g.fillStyle = k === 'W' ? '#E6E6E6' : k === 'B' ? '#222' : 'rgba(0,0,0,0.18)'; g.fillRect(78, H - 96, W - 156, 4);
    g.fillStyle = acc; g.fillRect(78, H - 96, (W - 156) * (u / 6.4), 4);
    return;
  }
  // beats 8–15: black. "Edit at the speed of" builds word by word, then "vibe." slams in neon
  g.fillStyle = C.black; g.fillRect(0, 0, W, H);
  const z = 1 + (u - 3.2) * 0.02;
  g.save(); g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
  const line = ['Edit', 'at the', 'speed', 'of'];
  font(g, 120, 750);
  const sp = g.measureText(' ').width, ws = line.map(s => g.measureText(s).width);
  let x = W / 2 - (ws.reduce((a, c) => a + c) + sp * (line.length - 1)) / 2;
  g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  line.forEach((s, i) => {
    const bt = 8 + i, p = E.out(clamp((u - bt * BEAT) / 0.2));
    if (p > 0) {
      g.save(); g.globalAlpha = p; blur(g, (1 - p) * 8);
      g.fillStyle = b >= 12 ? '#8C8C8C' : '#FFFFFF';
      g.fillText(s, x, 430 + (1 - p) * 40);
      g.restore();
    }
    x += ws[i] + sp;
  });
  const vp = clamp((u - 12 * BEAT) / 0.24);
  if (vp > 0) {
    const p = E.out(vp), s = lerp(1.5, 1, p);
    const pulse = 0.6 + 0.4 * Math.exp(-((u - 12 * BEAT) % BEAT) / 0.15);
    g.save(); g.translate(W / 2, 700); g.scale(s, s);
    g.globalAlpha = clamp(vp * 2); blur(g, (1 - p) * 12);
    font(g, 330, 800); g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    g.shadowColor = rgba(C.neon, 0.8 * pulse); g.shadowBlur = 90;
    g.fillStyle = C.neon; g.fillText('vibe.', 0, 0);
    g.restore();
  }
  g.restore();
  brackets(g, C.neon, 56, 46, 5);
  font(g, 26, 700, 2); g.fillStyle = '#FFFFFF'; g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  g.fillText('VIBE EDITING', 78, 112);
  g.textAlign = 'right'; g.fillText('IDEABRO STUDIO', W - 78, 112);
}

// ================================================================== composition
// [start, end, fn, exitStart, exitEnd, exitScale] in virtual seconds
const SCENES = [
  [0, 5.3, sOpen, 4.55, 5.25, 0.94],
  [4.9, 10.3, sPrompt, 9.6, 10.25, 1.0],
  [9.4, 14.6, sReveal, 13.55, 14.35, 1.12],
  [13.8, 23.7, sDevice, 22.85, 23.65, 0.9],
  [23.2, 32.3, sBento, 99, 99, 1],
  [31.8, 36.0, sStatement, 99, 99, 1],
  [36.0, 41, sEnd, 99, 99, 1],
];
const layer = mk();
function drawAt(g, r) {
  g.save();
  g.fillStyle = C.bg; g.fillRect(0, 0, W, H);
  if (r >= MON0 && r < MON1) { sMontage(g, r - MON0); g.restore(); return; }
  const t = warp(r);
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

// film-like dither so 8-bit gradients do not band
const grain = mk(256, 256);
(() => { const id = grain.g.createImageData(256, 256); for (let i = 0; i < id.data.length; i += 4) { const v = Math.random() < 0.5 ? 0 : 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 5; } grain.g.putImageData(id, 0, 0); })();

const cv = document.getElementById('c');
cv.width = W; cv.height = H;
const out = cv.getContext('2d');
const tmp = mk(), acc = mk();
const CUTS = [...Array(17).keys()].map(i => +(MON0 + i * BEAT).toFixed(6));   // montage beats incl. both edges
function renderT(t0) {
  if (MB <= 1) { drawAt(out, t0); }
  else {
    for (let s = 0; s < MB; s++) {
      let t = t0 + ((s + 0.5) / MB - 0.5) * SHUTTER / FPS;
      for (const c of CUTS) {                  // never blur across a hard cut
        if (t0 < c && t >= c) t = c - 1e-4;
        else if (t0 >= c && t < c) t = c + 1e-4;
      }
      drawAt(tmp.g, clamp(t, 0, DUR - 1e-4));
      acc.g.globalAlpha = 1 / (s + 1); acc.g.drawImage(tmp, 0, 0);
    }
    acc.g.globalAlpha = 1; out.drawImage(acc, 0, 0);
  }
  out.save(); out.globalAlpha = 1;
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
    if (e.code === 'ArrowRight' || e.code === 'ArrowLeft') { off = clamp(now() + (e.code === 'ArrowRight' ? 1.6 : -1.6), 0, DUR - 0.01); if (playing) { start = performance.now() - off * 1000; audio.currentTime = off; } }
  });
}
