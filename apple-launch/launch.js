'use strict';
// VIBE EDITING by Ideabro Studio: 40 s launch film in an Apple-style white, minimal look.
// Every frame is a pure function of time t (seconds). 120 BPM: 1 beat = 0.5 s, 1 bar = 2 s, 20 bars.
// Cue times are kept in sync with audio.py.

const W = 1920, H = 1080, DUR = 40;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 60);
const MB = +(Q.get('mb') || (RENDER ? 4 : 1));   // motion-blur sub-frames
const SHUTTER = 0.5;                                // 180° shutter

const C = {
  bg: '#FFFFFF', soft: '#F5F5F7', ink: '#1D1D1F', grey: '#6E6E73', grey2: '#86868B',
  line: '#D2D2D7', hair: '#E8E8ED', blue: '#0071E3', link: '#0066CC',
};
// Apple-Intelligence-style spectrum
const SPEC = ['#0A84FF', '#5E5CE6', '#BF5AF2', '#FF375F', '#FF9F0A', '#FFD60A', '#64D2FF'];
const TEXTG = ['#2F6BFF', '#7B4DFF', '#C846E8', '#FF4F7B', '#FF8A3D'];

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
  outC: x => 1 - Math.pow(1 - clamp(x), 3),
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
function palAt(pal, u) { u = ((u % 1) + 1) % 1; const n = pal.length, x = u * n, i = Math.floor(x); return mix(pal[i % n], pal[(i + 1) % n], x - i); }
function gradX(g, x0, x1, phase = 0, pal = TEXTG, cyc = 0.75) {
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
function serif(g, px) { g.font = `italic 400 ${px}px "Instrument Serif", serif`; g.letterSpacing = '0px'; }
function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function blur(g, b) { g.filter = b > 0.35 ? `blur(${b.toFixed(2)}px)` : 'none'; }
function softShadow(g, a = 0.12, b = 60, oy = 24) { g.shadowColor = `rgba(0,0,0,${a})`; g.shadowBlur = b; g.shadowOffsetX = 0; g.shadowOffsetY = oy; }
function noShadow(g) { g.shadowColor = 'transparent'; g.shadowBlur = 0; g.shadowOffsetY = 0; }

// Words blur up into place one after another (the signature Apple text reveal).
// o: size, w, col | grad(phase), stagger, dur, dy, bl, a, align ('c' | 'l'), track, out (0..1 exit progress)
function words(g, str, x, y, t, t0, o = {}) {
  const size = o.size || 80;
  font(g, size, o.w || 600, o.track);
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
      g.fillStyle = o.grad != null ? gradX(g, x0, x0 + total, o.grad, o.pal || TEXTG, o.cyc ?? 0.75) : (o.col || C.ink);
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

// Apple-Intelligence edge glow around a rounded rect. k = intensity 0..1
function glowRect(g, x, y, w, h, r, t, k, th = 1) {
  if (k <= 0.002) return;
  const cx = x + w / 2, cy = y + h / 2;
  const cg = g.createConicGradient(t * 1.9, cx, cy);
  const n = SPEC.length;
  for (let i = 0; i <= n; i++) cg.addColorStop(i / n, SPEC[i % n]);
  g.save();
  g.globalCompositeOperation = 'source-over';
  g.strokeStyle = cg;
  const passes = [[38 * th, 26 * th, 0.55], [14 * th, 9 * th, 0.8], [3.5 * th, 0, 1]];
  for (const [lw, b, a] of passes) {
    g.globalAlpha = a * k; g.lineWidth = lw; blur(g, b * (0.6 + 0.4 * k));
    rr(g, x, y, w, h, r); g.stroke();
  }
  g.restore();
}

// soft colour blobs (aurora) without filters: radial gradients only
function aurora(g, t, a, cx = W / 2, cy = H / 2, sx = 1, sy = 1) {
  if (a <= 0.002) return;
  g.save(); g.globalAlpha = a;
  const blobs = [[SPEC[0], -380, -40, 520], [SPEC[2], 60, 60, 480], [SPEC[3], 420, -30, 460], [SPEC[4], 200, 160, 360]];
  blobs.forEach(([col, dx, dy, r], i) => {
    const x = cx + (dx + Math.sin(t * 0.5 + i * 2) * 60) * sx, y = cy + (dy + Math.cos(t * 0.4 + i) * 40) * sy;
    const gr = g.createRadialGradient(x, y, 0, x, y, r * sx);
    gr.addColorStop(0, rgba(col, 0.55)); gr.addColorStop(0.5, rgba(col, 0.18)); gr.addColorStop(1, rgba(col, 0));
    g.fillStyle = gr; g.fillRect(x - r * sx, y - r * sx, r * 2 * sx, r * 2 * sx);
  });
  g.restore();
}

// ================================================================== SCENES
// 01 OPEN (0–5): "Editing used to mean" + rolling word slot
const slot = mk(W, 520);
const SLOT = [[1.5, 'keyframes.'], [2.25, 'layers.'], [3.0, 'render bars.'], [3.75, 'endless hours.']];
function sOpen(g, t) {
  const drift = 1 + t * 0.006;
  g.save(); g.translate(W / 2, H / 2); g.scale(drift, drift); g.translate(-W / 2, -H / 2);
  words(g, 'Editing used to mean', W / 2, 440, t, 0.45, { size: 64, w: 500, col: C.grey2, stagger: 0.1 });
  // slot words roll through a feathered window (drawn in a strip layer, masked with an alpha gradient)
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
    if (i === SLOT.length - 1) {          // strike through the last word
      const w = sg.measureText(s).width, ps = P(t, 4.25, 0.5, E.io);
      sg.filter = 'none';
      if (ps > 0) { sg.fillRect(W / 2 - w / 2 - 10, y - 56, (w + 20) * ps, 9); }
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

// 02 PROMPT (4.9–10.2): a glass prompt pill, typed instruction, send, edge glow
const PROMPT1 = 'Make it cinematic. Warm, punchy, with captions.';
const TYPE1 = [5.6, 24];   // start, chars per second
function typed(s, t, t0, cps) { return s.slice(0, clamp(Math.floor((t - t0) * cps), 0, s.length)); }
function sPrompt(g, t) {
  const pw = 1180, ph = 128;
  const sIn = spring(t - 5.0, 1.25, 0.7);
  const exitP = P(t, 8.75, 0.7, E.io);
  const sc = lerp(0.86, 1, sIn) * lerp(1, 0.55, exitP);
  const cy = lerp(600, 560, exitP);
  const a = clamp((t - 5.0) / 0.35) * (1 - P(t, 8.85, 0.45, E.std));

  words(g, 'Now, you just say it.', W / 2, 400, t, 5.15, { size: 76, w: 700, out: P(t, 8.1, 0.6, E.io), stagger: 0.08 });

  // full-screen edge glow bloom after send
  const eg = P(t, 8.75, 0.75, E.io) * (1 - P(t, 9.5, 0.75, E.io));
  if (a > 0.001) {
    g.save(); g.translate(W / 2, cy); g.scale(sc, sc); g.globalAlpha = a;
    const x = -pw / 2, y = -ph / 2;
    // glow behind pill once sent
    const gk = P(t, 8.0, 0.5) * (1 - exitP * 0.6);
    glowRect(g, x, y, pw, ph, ph / 2, t, gk, 1.25);
    softShadow(g, 0.10, 70, 26);
    g.fillStyle = '#FFFFFF'; rr(g, x, y, pw, ph, ph / 2); g.fill();
    noShadow(g);
    g.lineWidth = 1.5; g.strokeStyle = C.hair; rr(g, x, y, pw, ph, ph / 2); g.stroke();
    // sparkle icon
    g.fillStyle = gradX(g, x + 40, x + 100, t * 0.2); sparkle(g, x + 72, 0, 24, t * 0.6); g.fill();
    // text
    const s = typed(PROMPT1, t, TYPE1[0], TYPE1[1]);
    font(g, 40, 500); g.textAlign = 'left'; g.textBaseline = 'middle';
    if (s.length === 0) { g.fillStyle = C.grey2; g.fillText('Describe your edit…', x + 122, 2); }
    else { g.fillStyle = C.ink; g.fillText(s, x + 122, 2); }
    const caretX = x + 122 + (s.length ? g.measureText(s).width + 4 : 0);
    if (t < 8.0 && Math.floor(t * 2.2) % 2 === 0 || (t > TYPE1[0] && t < 7.7)) { g.fillStyle = C.blue; g.fillRect(caretX, -26, 3, 52); }
    // send button
    const bp = 1 - 0.12 * Math.exp(-Math.pow((t - 8.03) / 0.07, 2));
    const ready = clamp((t - 7.6) / 0.25);
    g.save(); g.translate(x + pw - 70, 0); g.scale(bp, bp);
    g.fillStyle = ready > 0 ? mix('#D2D2D7', '#1D1D1F', ready) : '#D2D2D7';
    if (t > 8.0) g.fillStyle = gradX(g, -40, 40, t * 0.3);
    g.beginPath(); g.arc(0, 0, 40, 0, TAU); g.fill();
    g.strokeStyle = '#FFFFFF'; g.lineWidth = 5.5; g.lineCap = 'round'; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(0, 15); g.lineTo(0, -15); g.moveTo(-12, -3); g.lineTo(0, -15); g.lineTo(12, -3); g.stroke();
    g.restore();
    g.restore();
  }
  if (eg > 0.001) {
    const inset = lerp(260, 14, P(t, 8.75, 0.75, E.io));
    glowRect(g, inset, inset * 0.55, W - inset * 2, H - inset * 1.1, 48, t, eg, 2.2);
    aurora(g, t, eg * 0.22);
  }
}

// 03 REVEAL (9.4–14.4): Introducing / Vibe Editing / A course by Ideabro Studio
function sReveal(g, t) {
  const push = 1 + (t - 9.4) * 0.008;
  g.save(); g.translate(W / 2, H / 2); g.scale(push, push); g.translate(-W / 2, -H / 2);
  aurora(g, t, 0.16 * P(t, 9.9, 1.6, E.io), W / 2, 520, 1.2, 0.7);
  words(g, 'Introducing', W / 2, 395, t, 9.5, { size: 48, w: 600, col: C.grey, dy: 20, bl: 10 });
  // per-letter mask rise
  const title = 'Vibe Editing', size = 236;
  font(g, size, 700);
  const tw = g.measureText(title).width, x0 = W / 2 - tw / 2, base = 625;
  const fill = gradX(g, x0, x0 + tw, (t - 10) * 0.035, TEXTG, 0.8);
  g.textAlign = 'left';
  for (let i = 0; i < title.length; i++) {
    const ch = title[i];
    const xi = x0 + g.measureText(title.slice(0, i)).width;
    const p = P(t, 10.0 + i * 0.035, 1.1);
    if (p > 0) {
      g.save();
      g.beginPath(); g.rect(xi - 40, base - size * 1.05, 400, size * 1.32); g.clip();
      g.globalAlpha = clamp(p * 1.6);
      g.fillStyle = fill;
      g.fillText(ch, xi, base + (1 - p) * size * 1.0);
      g.restore();
    }
  }
  const y2 = 735;
  font(g, 50, 500);
  const s1 = 'A course by ', s2 = 'Ideabro Studio.';
  const w1 = g.measureText(s1).width; font(g, 50, 650); const w2 = g.measureText(s2).width;
  const p2 = P(t, 11.5, 1.0);
  if (p2 > 0) {
    const sx = W / 2 - (w1 + w2) / 2;
    g.save(); g.globalAlpha = clamp(p2 * 1.4); blur(g, (1 - p2) * 12);
    font(g, 50, 500); g.textAlign = 'left'; g.fillStyle = C.grey; g.fillText(s1, sx, y2 + (1 - p2) * 18);
    font(g, 50, 650); g.fillStyle = C.ink; g.fillText(s2, sx + w1, y2 + (1 - p2) * 18);
    g.restore();
  }
  g.restore();
}

// ------------------------------------------------------------------ the "video" inside the editor (procedural landscape)
function drawVideo(g, x, y, w, h, t, G, cap = null, capT = 0, capSize = 0.075, karaoke = false) {
  g.save(); rr(g, x, y, w, h, Math.min(w, h) * 0.02); g.clip();
  const sky = g.createLinearGradient(0, y, 0, y + h);
  sky.addColorStop(0, mix('#7F93A8', '#123A57', G));
  sky.addColorStop(0.55, mix('#B4C0CC', '#E9874A', G));
  sky.addColorStop(1, mix('#CDD3D9', '#FFC27A', G));
  g.fillStyle = sky; g.fillRect(x, y, w, h);
  // sun + halo
  const sx = x + w * 0.66, sy = y + h * (0.5 - G * 0.02);
  const halo = g.createRadialGradient(sx, sy, 0, sx, sy, w * 0.45);
  halo.addColorStop(0, `rgba(255,${Math.round(lerp(250, 214, G))},${Math.round(lerp(240, 150, G))},${lerp(0.35, 0.85, G)})`);
  halo.addColorStop(1, 'rgba(255,200,140,0)');
  g.fillStyle = halo; g.fillRect(x, y, w, h);
  g.fillStyle = mix('#F4F6F8', '#FFF1D2', G); g.beginPath(); g.arc(sx, sy, w * 0.055, 0, TAU); g.fill();
  // three mountain ranges, parallax pan
  const layers = [['#8592A0', '#3B3550', 0.62, 0.12, 4], ['#66717E', '#24223A', 0.72, 0.09, 7], ['#46505B', '#14121F', 0.84, 0.06, 13]];
  layers.forEach(([c0, c1, hy, amp, sp], li) => {
    g.fillStyle = mix(c0, c1, G);
    g.beginPath(); g.moveTo(x, y + h);
    for (let i = 0; i <= 48; i++) {
      const u = i / 48, X = u * w + x;
      const k = u * (3 + li * 2) + t * 0.03 * sp + li * 10;
      const Y = y + h * (hy - amp * (0.6 * noise1(k) + 0.4 * noise1(k * 2.3 + 5)));
      g.lineTo(X, Y);
    }
    g.lineTo(x + w, y + h); g.closePath(); g.fill();
  });
  // haze / grade
  g.fillStyle = `rgba(255,170,90,${0.10 * G})`; g.fillRect(x, y, w, h);
  const vg = g.createRadialGradient(x + w / 2, y + h / 2, h * 0.3, x + w / 2, y + h / 2, w * 0.75);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, `rgba(0,0,0,${0.45 * G})`);
  g.fillStyle = vg; g.fillRect(x, y, w, h);
  // letterbox
  const lb = h * 0.11 * clamp(G * 1.2 - 0.1);
  g.fillStyle = '#000'; g.fillRect(x, y, w, lb); g.fillRect(x, y + h - lb, w, lb);
  // captions, word by word
  if (cap) {
    const ws = cap.split(' ');
    const fs = h * capSize;
    font(g, fs, 700, 0); g.textAlign = 'left'; g.textBaseline = 'middle';
    const sp = g.measureText(' ').width, wl = ws.map(s => g.measureText(s).width);
    const tot = wl.reduce((a, b) => a + b) + sp * (ws.length - 1);
    let cx = x + w / 2 - tot / 2; const cy = y + h * 0.78;
    ws.forEach((s, i) => {
      const p = spring(capT - i * 0.16, 2.2, 0.55);
      if (p > 0.01) {
        g.save(); g.globalAlpha = clamp(p);
        const on = karaoke ? Math.floor(capT / 0.3) % ws.length === i : capT >= i * 0.16 && capT < (i + 1) * 0.16 + 0.12;
        g.translate(cx + wl[i] / 2, cy); g.scale(lerp(0.6, 1, p), lerp(0.6, 1, p));
        if (on) { g.fillStyle = '#FFD60A'; rr(g, -wl[i] / 2 - fs * 0.18, -fs * 0.62, wl[i] + fs * 0.36, fs * 1.2, fs * 0.22); g.fill(); }
        g.shadowColor = 'rgba(0,0,0,0.35)'; g.shadowBlur = on ? 0 : 8;
        g.fillStyle = on ? '#111' : '#FFF'; g.fillText(s, -wl[i] / 2, 2);
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
const PROMPT2 = 'warm cinematic grade, cut to the beat';
const T2 = [15.9, 22];   // typing start, cps
const SEND2 = 18.0;
const CLIPS_A = [[0, 210], [210, 330], [330, 610], [610, 770], [770, 1060]];
function clipsB() { const out = []; let x = 0; const w = [132, 132, 66, 66, 132, 132, 132, 132, 66, 66, 132]; for (const k of w) { out.push([x, x + k]); x += k; } return out; }
const CLIPS_B = clipsB();
function drawEditor(t) {
  const g = scr.g; g.save();
  g.fillStyle = '#1C1C1E'; g.fillRect(0, 0, SW, SH);
  const G = E.io(inv(SEND2 + 0.1, SEND2 + 1.3, t));
  // toolbar
  g.fillStyle = '#2A2A2D'; g.fillRect(0, 0, SW, 44);
  ['#FF5F57', '#FEBC2E', '#28C840'].forEach((c, i) => { g.fillStyle = c; g.beginPath(); g.arc(22 + i * 22, 22, 7, 0, TAU); g.fill(); });
  text(g, 'Golden Hour — Vibe Editor', SW / 2, 28, { size: 15, w: 600, col: '#A1A1A6', track: 0 });
  // sidebar
  g.fillStyle = '#232326'; g.fillRect(0, 44, 230, 426);
  text(g, 'Library', 18, 76, { size: 14, w: 700, col: '#8E8E93', align: 'left', track: 0 });
  for (let i = 0; i < 8; i++) {
    const cx = 18 + (i % 2) * 104, cy = 92 + Math.floor(i / 2) * 72;
    const gr = g.createLinearGradient(cx, cy, cx + 94, cy + 58);
    gr.addColorStop(0, palAt(SPEC, i * 0.13)); gr.addColorStop(1, mix('#1C1C1E', rgbHex(palAt(SPEC, i * 0.13 + 0.3)), 0.5));
    g.globalAlpha = 0.8; g.fillStyle = gr; rr(g, cx, cy, 94, 58, 7); g.fill(); g.globalAlpha = 1;
  }
  // viewer
  g.fillStyle = '#141416'; g.fillRect(230, 44, 698, 426);
  const vx = 259, vy = 70, vw = 640, vh = 360;
  const capT = t - (SEND2 + 1.5);
  drawVideo(g, vx, vy, vw, vh, t, G, capT > 0 ? 'Golden hour, every frame.' : null, capT);
  // in-viewer prompt pill
  const pa = clamp((t - 15.4) / 0.3) * (1 - P(t, SEND2 + 0.15, 0.4, E.std));
  if (pa > 0.001) {
    const pw = 520, ph = 46, px = vx + vw / 2 - pw / 2, py = vy + vh - ph - 18 + (1 - spring(t - 15.4, 1.6, 0.7)) * 20;
    g.save(); g.globalAlpha = pa;
    glowRect(g, px, py, pw, ph, ph / 2, t, P(t, SEND2 - 0.05, 0.25) * 0.9, 0.45);
    g.fillStyle = 'rgba(40,40,44,0.86)'; rr(g, px, py, pw, ph, ph / 2); g.fill();
    g.strokeStyle = 'rgba(255,255,255,0.14)'; g.lineWidth = 1; rr(g, px, py, pw, ph, ph / 2); g.stroke();
    g.fillStyle = gradX(g, px + 10, px + 40, t * 0.3); sparkle(g, px + 26, py + ph / 2, 10, t); g.fill();
    const s = typed(PROMPT2, t, T2[0], T2[1]);
    font(g, 17, 500, 0); g.textAlign = 'left'; g.textBaseline = 'middle';
    g.fillStyle = s ? '#F5F5F7' : '#8E8E93'; g.fillText(s || 'Ask for any edit…', px + 46, py + ph / 2 + 1);
    if (Math.floor(t * 2.4) % 2 === 0 || (t > T2[0] && t < T2[0] + PROMPT2.length / T2[1])) { g.fillStyle = '#0A84FF'; g.fillRect(px + 48 + (s ? g.measureText(s).width : -2), py + 13, 2, 21); }
    g.restore();
  }
  // inspector
  g.fillStyle = '#232326'; g.fillRect(928, 44, 220, 426);
  text(g, 'Inspector', 946, 76, { size: 14, w: 700, col: '#8E8E93', align: 'left', track: 0 });
  const sl = [['Temperature', 0.45, 0.82], ['Contrast', 0.4, 0.68], ['Saturation', 0.5, 0.74], ['Tempo sync', 0.1, 1.0]];
  sl.forEach(([n, a, b], i) => {
    const y = 112 + i * 64, v = lerp(a, b, E.io(inv(SEND2 + 0.2 + i * 0.12, SEND2 + 1.2 + i * 0.12, t)));
    text(g, n, 946, y, { size: 13, w: 500, col: '#C7C7CC', align: 'left', track: 0 });
    text(g, Math.round(v * 100) + '', 1130, y, { size: 13, w: 600, col: '#8E8E93', align: 'right', track: 0 });
    g.fillStyle = '#3A3A3C'; rr(g, 946, y + 14, 184, 4, 2); g.fill();
    g.fillStyle = gradX(g, 946, 1130, 0.1 + i * 0.15); rr(g, 946, y + 14, 184 * v, 4, 2); g.fill();
    g.fillStyle = '#FFF'; g.beginPath(); g.arc(946 + 184 * v, y + 16, 7, 0, TAU); g.fill();
  });
  // timeline
  const ty = 470;
  g.fillStyle = '#1A1A1C'; g.fillRect(0, ty, SW, SH - ty);
  g.fillStyle = '#2C2C2E'; g.fillRect(0, ty, SW, 1);
  const X0 = 74, TW = 1060;
  for (let i = 0; i <= 40; i++) {
    const x = X0 + i * TW / 40;
    g.fillStyle = '#48484A'; g.fillRect(x, ty + 10, 1, i % 4 === 0 ? 12 : 6);
    if (i % 8 === 0) text(g, `00:0${i / 8}`, x + 4, ty + 22, { size: 10, w: 500, col: '#8E8E93', align: 'left', track: 0 });
  }
  const tracks = [['T1', 506, 30], ['V1', 544, 56], ['A1', 608, 44], ['A2', 660, 36]];
  tracks.forEach(([n, y, h]) => {
    g.fillStyle = '#232326'; g.fillRect(0, y, 64, h);
    text(g, n, 32, y + h / 2 + 5, { size: 12, w: 700, col: '#8E8E93', track: 0 });
  });
  // V1 clips morph: 5 uneven -> 11 beat-cut clips
  for (let i = 0; i < CLIPS_B.length; i++) {
    const k = E.io(inv(SEND2 + 0.25 + i * 0.05, SEND2 + 0.95 + i * 0.05, t));
    const A = CLIPS_A[Math.min(i, CLIPS_A.length - 1)], B = CLIPS_B[i];
    const a0 = i < CLIPS_A.length ? A[0] : 1060, a1 = i < CLIPS_A.length ? A[1] : 1060;
    const x0 = X0 + lerp(a0, B[0], k) + 1.5, x1 = X0 + lerp(a1, B[1], k) - 1.5;
    if (x1 - x0 < 1) continue;
    const hue = palAt(['#4A6FA5', '#5B6B8C', '#4F7D8F', '#6A5D8F'], i * 0.27);
    const hueB = palAt(['#E07A3F', '#C9583A', '#E8A04B', '#3D6E8A'], i * 0.31);
    const gr = g.createLinearGradient(x0, 0, x1, 0);
    gr.addColorStop(0, mix(rgbHex(hue), rgbHex(hueB), G)); gr.addColorStop(1, mix(rgbHex(hue), '#1E2C3A', 0.35 + 0.2 * G));
    g.fillStyle = gr; rr(g, x0, 547, x1 - x0, 50, 6); g.fill();
    g.strokeStyle = 'rgba(255,255,255,0.18)'; g.lineWidth = 1; rr(g, x0, 547, x1 - x0, 50, 6); g.stroke();
  }
  // T1 titles
  const tg = E.io(inv(SEND2 + 1.3, SEND2 + 1.9, t));
  if (tg > 0) { g.fillStyle = '#BF5AF2'; g.globalAlpha = 0.9; rr(g, X0 + 132, 509, 528 * tg, 24, 5); g.fill(); g.globalAlpha = 1; text(g, 'Captions', X0 + 142, 526, { size: 11, w: 700, col: '#FFF', align: 'left', track: 0 }); }
  // A1 waveform
  g.save(); rr(g, X0, 611, TW, 38, 6); g.clip();
  g.fillStyle = 'rgba(48,209,88,0.20)'; g.fillRect(X0, 611, TW, 38);
  g.fillStyle = '#30D158';
  for (let i = 0; i < 212; i++) {
    const x = X0 + i * 5, beat = Math.exp(-((i % 26.5) / 3));
    const a = (0.25 + 0.55 * Math.abs(noise1(i * 0.7)) + 0.5 * beat * G) * 17;
    g.fillRect(x, 630 - a, 2.4, a * 2);
  }
  g.restore();
  // A2 music bed
  g.fillStyle = 'rgba(100,210,255,0.28)'; rr(g, X0, 663, TW, 30, 6); g.fill();
  g.strokeStyle = '#64D2FF'; g.lineWidth = 1.5; g.beginPath();
  for (let i = 0; i <= 200; i++) { const x = X0 + i * TW / 200; g.lineTo(x, 678 + Math.sin(i * 0.35) * 6 * Math.sin(i * 0.05)); }
  g.stroke();
  // beat markers appear after the edit
  for (let i = 0; i <= 16; i++) {
    const k = P(t, SEND2 + 0.4 + i * 0.03, 0.4);
    if (k <= 0) continue;
    g.fillStyle = `rgba(255,214,10,${k})`; const x = X0 + i * 66.25;
    g.beginPath(); g.moveTo(x, ty + 26); g.lineTo(x + 4, ty + 30); g.lineTo(x, ty + 34); g.lineTo(x - 4, ty + 30); g.fill();
  }
  // playhead
  const ph = X0 + ((t - 14.0) * 132) % TW;
  g.fillStyle = '#FFFFFF'; g.fillRect(ph - 1, ty + 4, 2, SH - ty - 8);
  g.beginPath(); g.moveTo(ph - 7, ty + 4); g.lineTo(ph + 7, ty + 4); g.lineTo(ph, ty + 13); g.fill();
  // AI working glow inside the screen
  const gw = P(t, SEND2, 0.35) * (1 - P(t, SEND2 + 1.0, 0.9, E.io));
  glowRect(g, 4, 4, SW - 8, SH - 8, 14, t, gw, 0.8);
  g.restore();
}
function rgbHex(s) { if (s[0] === '#') return s; const m = s.match(/\d+/g); return '#' + m.slice(0, 3).map(v => (+v).toString(16).padStart(2, '0')).join(''); }

// 04 DEVICE (13.6–23.6)
function laptop(g, t, cx, top, s, tilt) {
  const bw = SW + 32, bh = SH + 34;
  g.save(); g.translate(cx, top); g.scale(s, s * tilt);
  // floor shadow
  const sh = g.createRadialGradient(0, bh + 40, 0, 0, bh + 40, bw * 0.62);
  sh.addColorStop(0, 'rgba(0,0,0,0.18)'); sh.addColorStop(1, 'rgba(0,0,0,0)');
  g.save(); g.scale(1, 0.09); g.fillStyle = sh; g.beginPath(); g.arc(0, (bh + 40) / 0.09, bw * 0.62, 0, TAU); g.fill(); g.restore();
  // lid
  softShadow(g, 0.16, 80, 40);
  g.fillStyle = '#0C0C0E'; rr(g, -bw / 2, 0, bw, bh, 30); g.fill();
  noShadow(g);
  g.strokeStyle = '#B9BBC0'; g.lineWidth = 3; rr(g, -bw / 2 - 1.5, -1.5, bw + 3, bh + 3, 31.5); g.stroke();
  g.strokeStyle = '#3A3A3D'; g.lineWidth = 1.5; rr(g, -bw / 2 + 1, 1, bw - 2, bh - 2, 29); g.stroke();
  // screen
  g.save(); rr(g, -SW / 2, 16, SW, SH, 12); g.clip();
  g.drawImage(scr, -SW / 2, 16);
  const rf = g.createLinearGradient(-SW / 2, 16, SW / 2, 16 + SH);
  rf.addColorStop(0, 'rgba(255,255,255,0.07)'); rf.addColorStop(0.45, 'rgba(255,255,255,0.0)'); rf.addColorStop(1, 'rgba(255,255,255,0.02)');
  g.fillStyle = rf; g.fillRect(-SW / 2, 16, SW, SH);
  g.restore();
  // notch
  g.fillStyle = '#0C0C0E'; rr(g, -78, 8, 156, 26, 10); g.fill();
  g.fillStyle = '#1F2A33'; g.beginPath(); g.arc(0, 19, 4, 0, TAU); g.fill();
  // hinge + base
  const hb = g.createLinearGradient(0, bh, 0, bh + 12);
  hb.addColorStop(0, '#3A3B3E'); hb.addColorStop(1, '#8E9095');
  g.fillStyle = hb; rr(g, -bw / 2 + 40, bh - 2, bw - 80, 12, 3); g.fill();
  const BW = bw * 1.17, BY = bh + 8;
  const bg = g.createLinearGradient(0, BY, 0, BY + 26);
  bg.addColorStop(0, '#F1F2F4'); bg.addColorStop(0.35, '#D9DADD'); bg.addColorStop(1, '#A7A9AE');
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
  words(g, 'AI handles the edit.', W / 2, 150, t, 18.35, { size: 72, w: 700, grad: (t - 18.3) * 0.04 });
  laptop(g, t, W / 2, top, s, tilt);
}

// 05 BENTO (23.2–32.2): what you'll master
const CARDS = [
  { x: 160, y: 260, w: 760, h: 350, title: 'AI Captions', sub: 'Word-perfect and auto-styled.', fn: cardCaptions },
  { x: 944, y: 260, w: 388, h: 350, title: 'Motion Graphics', sub: 'Type and shapes that move.', fn: cardMotion },
  { x: 1356, y: 260, w: 404, h: 350, title: 'Color Grading', sub: 'Any mood, one prompt.', fn: cardColor },
  { x: 160, y: 634, w: 500, h: 350, title: 'Smart Cuts', sub: 'Every cut lands on the beat.', fn: cardCuts },
  { x: 684, y: 634, w: 388, h: 350, title: 'Sound Design', sub: 'Music, SFX and mix.', fn: cardSound },
  { x: 1096, y: 634, w: 664, h: 350, title: 'Prompt Workflows', sub: 'Direct AI like a senior editor.', fn: cardPrompt },
];
const CARD_T = [24.0, 24.25, 24.5, 24.75, 25.0, 25.25];
function cardCaptions(g, c, t, u) {
  const vx = c.x + 28, vy = c.y + 28, vw = c.w - 56, vh = c.h - 140;
  const cyc = ((t - 24.0) % 2.6 + 2.6) % 2.6;
  drawVideo(g, vx, vy, vw, vh, t, 1, 'Captions that land on every word', cyc, 0.12, cyc > 1.0);
}
function cardMotion(g, c, t) {
  const cx = c.x + c.w / 2, cy = c.y + 120;
  const b = (t - 24) * 2;   // beats
  const ph = b % 1, bi = Math.floor(b);
  for (let i = 0; i < 3; i++) {
    const a = TAU * (i / 3) + E.io(clamp(ph * 1.6)) * TAU / 3 + bi * TAU / 3;
    const r = 66 + 10 * Math.sin(t * 2 + i);
    const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r * 0.85;
    const sq = 1 + 0.25 * Math.exp(-ph * 6);
    g.save(); g.translate(x, y); g.rotate(a + t);
    g.scale(sq, 1 / sq);
    g.fillStyle = gradX(g, -40, 40, i * 0.25 + t * 0.1);
    if (i === 0) { g.beginPath(); g.arc(0, 0, 34, 0, TAU); g.fill(); }
    else if (i === 1) { rr(g, -30, -30, 60, 60, 16); g.fill(); }
    else { g.beginPath(); g.moveTo(0, -36); g.lineTo(32, 26); g.lineTo(-32, 26); g.closePath(); g.lineJoin = 'round'; g.lineWidth = 10; g.strokeStyle = g.fillStyle; g.stroke(); g.fill(); }
    g.restore();
  }
}
function cardColor(g, c, t) {
  const cx = c.x + c.w / 2, cy = c.y + 122, r = 92;
  const cg = g.createConicGradient(0, cx, cy);
  ['#FF375F', '#FF9F0A', '#FFD60A', '#30D158', '#64D2FF', '#0A84FF', '#BF5AF2', '#FF375F'].forEach((col, i, a) => cg.addColorStop(i / (a.length - 1), col));
  g.fillStyle = cg; g.beginPath(); g.arc(cx, cy, r, 0, TAU); g.fill();
  const rg = g.createRadialGradient(cx, cy, 0, cx, cy, r);
  rg.addColorStop(0, 'rgba(255,255,255,1)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rg; g.beginPath(); g.arc(cx, cy, r, 0, TAU); g.fill();
  const a = -0.6 + Math.sin((t - 24) * 1.1) * 1.1, d = 52 + 14 * Math.sin(t * 1.7);
  const kx = cx + Math.cos(a) * d, ky = cy + Math.sin(a) * d;
  softShadow(g, 0.25, 10, 3);
  g.fillStyle = '#FFF'; g.beginPath(); g.arc(kx, ky, 13, 0, TAU); g.fill(); noShadow(g);
  g.strokeStyle = 'rgba(0,0,0,0.15)'; g.lineWidth = 1; g.stroke();
  g.strokeStyle = 'rgba(255,255,255,0.9)'; g.lineWidth = 2; g.beginPath(); g.moveTo(cx, cy); g.lineTo(kx, ky); g.stroke();
}
function cardCuts(g, c, t) {
  const x0 = c.x + 34, x1 = c.x + c.w - 34, cy = c.y + 118, n = 64, dx = (x1 - x0) / n;
  const b = (t - 24) * 2;
  for (let i = 0; i < n; i++) {
    const beat = Math.exp(-((i % 8)) / 1.6);
    const a = 12 + 50 * (0.35 * Math.abs(noise1(i * 0.8 + 3)) + 0.65 * beat);
    g.fillStyle = (i % 8 === 0) ? C.ink : '#C7C7CC';
    rr(g, x0 + i * dx + 1, cy - a, dx - 3, a * 2, 2); g.fill();
  }
  for (let k = 0; k < 8; k++) {
    const p = P(b, 1 + k * 0.5, 0.8);
    if (p <= 0) continue;
    const x = x0 + k * 8 * dx - 1;
    g.globalAlpha = p; g.fillStyle = C.blue; g.fillRect(x, cy - 80 * p, 3, 160 * p);
    g.beginPath(); g.arc(x + 1.5, cy - 80 * p - 8, 7, 0, TAU); g.fill(); g.globalAlpha = 1;
  }
}
function cardSound(g, c, t) {
  const n = 13, bw = 16, gap = 10, tot = n * bw + (n - 1) * gap, x0 = c.x + c.w / 2 - tot / 2, base = c.y + 200;
  const b = (t - 24) * 2, kick = Math.exp(-(b % 1) * 4);
  for (let i = 0; i < n; i++) {
    const env = Math.exp(-Math.pow((i - 6) / 4.2, 2));
    const h = 18 + 140 * env * (0.45 + 0.35 * kick + 0.25 * Math.abs(noise1(t * 5 + i * 1.7)));
    g.fillStyle = gradX(g, x0, x0 + tot, 0.05 + t * 0.04);
    rr(g, x0 + i * (bw + gap), base - h, bw, h, bw / 2); g.fill();
  }
}
const PROMPTS3 = ['zoom in on the punchline', 'add warm film grain', 'sync every cut to the drop'];
function cardPrompt(g, c, t) {
  const pw = c.w - 96, ph = 76, px = c.x + 48, py = c.y + 84;
  const lt = t - 25.2, per = 2.0, k = Math.max(0, Math.floor(lt / per)) % PROMPTS3.length, lk = lt - Math.floor(Math.max(0, lt) / per) * per;
  const s = lt < 0 ? '' : typed(PROMPTS3[k], lk, 0.1, 26);
  const send = lk > 1.25 && lt > 0;
  glowRect(g, px, py, pw, ph, ph / 2, t, send ? clamp((lk - 1.25) / 0.2) * (1 - clamp((lk - 1.7) / 0.3)) : 0, 0.75);
  softShadow(g, 0.08, 30, 10);
  g.fillStyle = '#FFF'; rr(g, px, py, pw, ph, ph / 2); g.fill(); noShadow(g);
  g.fillStyle = gradX(g, px + 20, px + 60, t * 0.2); sparkle(g, px + 44, py + ph / 2, 16, t * 0.7); g.fill();
  font(g, 26, 500, 0); g.textAlign = 'left'; g.textBaseline = 'middle';
  g.fillStyle = s ? C.ink : C.grey2; g.fillText(s || 'Describe your edit…', px + 80, py + ph / 2 + 1);
  if (!send && Math.floor(t * 2.4) % 2 === 0 || (lk > 0.1 && lk < 1.2)) { g.fillStyle = C.blue; g.fillRect(px + 82 + (s ? g.measureText(s).width : -2), py + 22, 2.5, 32); }
  g.fillStyle = send ? C.ink : '#D2D2D7'; g.beginPath(); g.arc(px + pw - 40, py + ph / 2, 24, 0, TAU); g.fill();
  g.strokeStyle = '#FFF'; g.lineWidth = 3.5; g.lineCap = 'round'; g.lineJoin = 'round';
  const bx = px + pw - 40, by = py + ph / 2; g.beginPath(); g.moveTo(bx, by + 9); g.lineTo(bx, by - 9); g.moveTo(bx - 7, by - 2); g.lineTo(bx, by - 9); g.lineTo(bx + 7, by - 2); g.stroke();
}
function sBento(g, t) {
  const z = lerp(1.035, 1.0, E.out(inv(23.4, 31.5, t)));
  g.save(); g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
  words(g, 'What you’ll master', W / 2, 112, t, 23.4, { size: 30, w: 600, col: C.grey, dy: 12, bl: 8 });
  words(g, 'Pro edits. Zero grind.', W / 2, 200, t, 23.55, { size: 80, w: 700, stagger: 0.08 });
  const out = P(t, 31.35, 0.7, E.io);
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
    g.fillStyle = C.soft; rr(g, c.x, c.y, c.w, c.h, 32); g.fill();
    g.save(); rr(g, c.x, c.y, c.w, c.h, 32); g.clip();
    c.fn(g, c, t);
    g.restore();
    text(g, c.title, c.x + 34, c.y + c.h - 62, { size: 32, w: 700, align: 'left' });
    text(g, c.sub, c.x + 34, c.y + c.h - 28, { size: 22, w: 500, col: C.grey, align: 'left', track: 0 });
    g.restore();
  });
  g.restore();
}

// 06 STATEMENT (31.8–36.2)
function sStatement(g, t) {
  const z = 1 + (t - 31.8) * 0.01;
  g.save(); g.translate(W / 2, H / 2); g.scale(z, z); g.translate(-W / 2, -H / 2);
  aurora(g, t, 0.13 * P(t, 32.9, 1.2, E.io), W / 2, 650, 1.1, 0.5);
  const out = P(t, 35.3, 0.6, E.io);
  words(g, 'Less timeline.', W / 2, 500, t, 32.0, { size: 176, w: 700, col: C.ink, stagger: 0.12, out, dur: 1.0 });
  words(g, 'More vibe.', W / 2, 690, t, 33.0, { size: 176, w: 700, grad: 0.12 + (t - 33) * 0.04, stagger: 0.12, out, dur: 1.0 });
  g.restore();
}

// 07 END CARD (35.8–40)
function squircle(g, x, y, s) {
  const r = s / 2, n = 5; g.beginPath();
  for (let i = 0; i <= 72; i++) {
    const a = i / 72 * TAU, c = Math.cos(a), sn = Math.sin(a);
    g.lineTo(x + Math.sign(c) * Math.pow(Math.abs(c), 2 / n) * r, y + Math.sign(sn) * Math.pow(Math.abs(sn), 2 / n) * r);
  }
  g.closePath();
}
function appIcon(g, x, y, s, t, shine) {
  softShadow(g, 0.22, s * 0.28, s * 0.12);
  const bg = g.createLinearGradient(x - s / 2, y - s / 2, x + s / 2, y + s / 2);
  bg.addColorStop(0, '#2F6BFF'); bg.addColorStop(0.38, '#7B4DFF'); bg.addColorStop(0.7, '#E2468F'); bg.addColorStop(1, '#FF9A3D');
  g.fillStyle = bg; squircle(g, x, y, s); g.fill(); noShadow(g);
  g.save(); squircle(g, x, y, s); g.clip();
  const hl = g.createRadialGradient(x - s * 0.3, y - s * 0.4, 0, x - s * 0.3, y - s * 0.4, s * 0.9);
  hl.addColorStop(0, 'rgba(255,255,255,0.45)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = hl; g.fillRect(x - s, y - s, s * 2, s * 2);
  const lo = g.createRadialGradient(x + s * 0.4, y + s * 0.5, 0, x + s * 0.4, y + s * 0.5, s * 0.7);
  lo.addColorStop(0, 'rgba(255,214,10,0.45)'); lo.addColorStop(1, 'rgba(255,214,10,0)');
  g.fillStyle = lo; g.fillRect(x - s, y - s, s * 2, s * 2);
  if (shine > 0 && shine < 1) {
    const sx = lerp(x - s * 1.2, x + s * 1.2, shine);
    const sg = g.createLinearGradient(sx - s * 0.3, y - s, sx + s * 0.3, y + s);
    sg.addColorStop(0, 'rgba(255,255,255,0)'); sg.addColorStop(0.5, 'rgba(255,255,255,0.55)'); sg.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = sg; g.fillRect(x - s, y - s, s * 2, s * 2);
  }
  g.restore();
  // glyph: play triangle + sparkle
  g.save(); g.shadowColor = 'rgba(40,0,80,0.25)'; g.shadowBlur = s * 0.06; g.shadowOffsetY = s * 0.02;
  g.fillStyle = '#FFFFFF'; g.lineJoin = 'round'; g.strokeStyle = '#FFF'; g.lineWidth = s * 0.07;
  const k = s * 0.2, ox = x - s * 0.04, oy = y + s * 0.03;
  g.beginPath(); g.moveTo(ox - k * 0.8, oy - k); g.lineTo(ox + k * 1.05, oy); g.lineTo(ox - k * 0.8, oy + k); g.closePath(); g.stroke(); g.fill();
  sparkle(g, x + s * 0.22, y - s * 0.22, s * 0.11, 0); g.fill();
  g.restore();
}
function sEnd(g, t) {
  const ip = spring(t - 36.0, 1.1, 0.6);
  const ia = clamp((t - 36.0) / 0.3);
  const settle = E.io(inv(36.0, 39.6, t));
  const iy = lerp(395, 380, settle);
  if (ia > 0) {
    g.save(); g.globalAlpha = ia; blur(g, (1 - clamp(ip)) * 10);
    g.translate(W / 2, iy); g.scale(lerp(0.5, 1, ip), lerp(0.5, 1, ip));
    appIcon(g, 0, 0, 210, t, inv(36.7, 37.6, t));
    g.restore();
  }
  words(g, 'Vibe Editing', W / 2, 640, t, 36.45, { size: 128, w: 700, stagger: 0.1 });
  words(g, 'by Ideabro Studio', W / 2, 716, t, 36.95, { size: 44, w: 500, col: C.grey, stagger: 0.08 });
  // CTA row
  const bp = spring(t - 37.5, 1.3, 0.7), ba = clamp((t - 37.5) / 0.3);
  if (ba > 0) {
    font(g, 34, 600, 0);
    const label = 'Enroll now', lw = g.measureText(label).width, bw = lw + 84, bh = 78;
    const link = 'Learn more', ll = g.measureText(link).width + 30;
    const gap = 44, tot = bw + gap + ll, x0 = W / 2 - tot / 2, y = 850;
    g.save(); g.globalAlpha = ba;
    g.translate(0, (1 - bp) * 30);
    g.fillStyle = C.blue; rr(g, x0, y - bh / 2, bw, bh, bh / 2); g.fill();
    g.fillStyle = '#FFF'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(label, x0 + bw / 2, y + 1);
    const la = clamp((t - 37.75) / 0.3); g.globalAlpha = ba * la;
    g.fillStyle = C.link; g.textAlign = 'left'; g.fillText(link, x0 + bw + gap, y + 1);
    const cx = x0 + bw + gap + ll - 12;
    g.strokeStyle = C.link; g.lineWidth = 3.5; g.lineCap = 'round'; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(cx - 6, y - 10); g.lineTo(cx + 3, y + 1); g.lineTo(cx - 6, y + 12); g.stroke();
    g.restore();
  }
}

// ================================================================== composition
// [start, end, fn, exitStart, exitEnd, exitScale]
const SCENES = [
  [0, 5.3, sOpen, 4.55, 5.25, 0.94],
  [4.9, 10.3, sPrompt, 9.6, 10.25, 1.0],
  [9.4, 14.6, sReveal, 13.55, 14.35, 1.12],
  [13.8, 23.7, sDevice, 22.85, 23.65, 0.9],
  [23.2, 32.3, sBento, 99, 99, 1],
  [31.8, 36.3, sStatement, 99, 99, 1],
  [35.8, 40.01, sEnd, 39.55, 40.01, 1.0],
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

// film-like dither so 8-bit gradients on white do not band
const grain = mk(256, 256);
(() => { const id = grain.g.createImageData(256, 256); for (let i = 0; i < id.data.length; i += 4) { const v = Math.random() < 0.5 ? 0 : 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 5; } grain.g.putImageData(id, 0, 0); })();

const cv = document.getElementById('c');
cv.width = W; cv.height = H;
const out = cv.getContext('2d');
const tmp = mk(), acc = mk();
function renderT(t0, tEnd) {
  if (MB <= 1) { drawAt(out, t0); }
  else {
    for (let s = 0; s < MB; s++) {
      const t = t0 + ((s + 0.5) / MB - 0.5) * SHUTTER / FPS;
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
  faces.push(new FontFace('Instrument Serif', 'url(fonts/InstrumentSerif-Italic.woff)', { style: 'italic' }));
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
