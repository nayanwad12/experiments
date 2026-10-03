'use strict';
// VIBE EDITING: faceless narrated reel, 1080x1920. Every frame is a pure function of time t (seconds).
// The motion graphics live on a laptop screen (1600x1000 canvas) composited into a drawn dark room.
// Word times come from work/words.json (forced alignment of the narration); keep W_ in sync with it.

const W = 1080, H = 1920, SW = 1600, SH = 1000;
const DUR = 39.5;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 30);
const MB = +(Q.get('mb') || (RENDER ? 3 : 1));   // motion-blur sub-frames
const SHUTTER = 0.5;

// word onsets (s)
const W_ = {
  fourteen: 0.52, still: 1.92, oneReel: 3.50, reel1: 3.83,
  cuts: 4.61, here: 4.91, captions: 5.66, there: 6.19, keyframes: 6.98, everywhere: 7.90,
  so: 9.28, stopped: 9.61, meet: 10.89, vibe: 11.28,
  one: 12.80, six: 13.64, hours: 14.23, ugh: 15.24, now: 16.39,
  cutting: 17.06, capt: 18.00, zooms: 19.07, sound: 19.99, effects: 20.39,
  twelve: 21.48, nice: 22.67, just: 23.75, type: 23.97, hit: 25.05, enter: 25.30,
  every: 26.23, night: 26.53, before: 27.03, chai: 27.56, posted: 28.51,
  fewer: 29.46, more: 30.49, vibe2: 31.84, oh: 33.32, and: 33.85, made: 35.17, ai: 35.73,
  comment: 36.63, vibeW: 37.42,
};

const C = {
  night: '#0C0D19', night2: '#1A1C38', panel: '#171930', line: 'rgba(255,255,255,0.07)',
  cream: '#F4F1EA', ink: '#17171C', grey: '#75757E', soft: '#B9B6AE',
  orange: '#FF6A2B', white: '#F6F4EF', violet: '#7C6CFF', green: '#3ECF8E', pink: '#E45BB8', blue: '#4DA3FF',
};
const SANS = (w, s) => `${w} ${s}px "Inter Tight"`;
const SERIF = s => `italic 400 ${s}px "Instrument Serif"`;
const MONO = s => `${s}px "JetBrains Mono"`;

// ------------------------------------------------------------------ math
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const inv = (a, b, x) => clamp((x - a) / (b - a));
const TAU = Math.PI * 2;
const E = {
  outQ: x => 1 - (1 - x) * (1 - x),
  inQ: x => x * x,
  outC: x => 1 - Math.pow(1 - x, 3),
  inC: x => x * x * x,
  ioC: x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2,
  outX: x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x),
  ioX: x => x <= 0 ? 0 : x >= 1 ? 1 : x < .5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2,
  outB: (x, s = 1.9) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2),
};
const ease = (t, a, d, f = E.outC) => f(inv(a, a + d, t));
function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
function noise1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u) * 2 - 1; }
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function mix(c1, c2, t) {
  const p = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
  const a = p(c1), b = p(c2);
  return `rgb(${a.map((v, i) => Math.round(lerp(v, b[i], clamp(t)))).join(',')})`;
}

// ------------------------------------------------------------------ canvas helpers
function mk(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; c.g = c.getContext('2d'); return c; }
const OUT = document.getElementById('out'), G = OUT.getContext('2d');
const SCR = mk(SW, SH), ACC = mk(W, H), TMP = mk(W, H), GLOW = mk(120, 90);

// mixed-style text runs: parts = [[text, font, color], ...]; returns width
function runs(g, parts, x, y, align = 'center') {
  let w = 0;
  for (const p of parts) { g.font = p[1]; p.w = g.measureText(p[0]).width; w += p.w; }
  let cx = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  g.textAlign = 'left';
  for (const p of parts) { g.font = p[1]; g.fillStyle = p[2]; g.fillText(p[0], cx, y); cx += p.w; }
  return w;
}
// draw fn() under a transform anchored at (x,y)
function at(g, x, y, s, a, fn, rot = 0) {
  if (a <= 0.002 || s <= 0.002) return;
  g.save(); g.translate(x, y); if (rot) g.rotate(rot); g.scale(s, s); g.globalAlpha *= clamp(a); fn(); g.restore();
}
// standard "pop in" on a word: returns {a, s, dy}
function pop(t, t0, d = .45, out = null) {
  const k = ease(t, t0, d, E.outB), f = ease(t, t0, d * .6, E.outQ);
  let a = f, s = lerp(.86, 1, k), dy = (1 - ease(t, t0, d, E.outC)) * 40;
  if (out) { const o = ease(t, out[0], out[1], E.inC); a *= 1 - o; dy -= o * 30; }
  return { a, s, dy };
}
function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function heart(g, x, y, s) {
  g.beginPath(); g.moveTo(x, y + s * .3);
  g.bezierCurveTo(x, y, x - s * .5, y, x - s * .5, y + s * .3);
  g.bezierCurveTo(x - s * .5, y + s * .6, x, y + s * .75, x, y + s);
  g.bezierCurveTo(x, y + s * .75, x + s * .5, y + s * .6, x + s * .5, y + s * .3);
  g.bezierCurveTo(x + s * .5, y, x, y, x, y + s * .3); g.fill();
}

// ------------------------------------------------------------------ backgrounds
function nightBg(g, t) {
  const r = g.createRadialGradient(SW / 2, SH * .45, 50, SW / 2, SH / 2, SW * .7);
  r.addColorStop(0, C.night2); r.addColorStop(1, C.night);
  g.fillStyle = r; g.fillRect(0, 0, SW, SH);
  g.strokeStyle = C.line; g.lineWidth = 1.5; g.beginPath();
  const off = (t * 6) % 50;
  for (let x = -off; x < SW; x += 50) { g.moveTo(x, 0); g.lineTo(x, SH); }
  for (let y = 0; y < SH; y += 50) { g.moveTo(0, y); g.lineTo(SW, y); }
  g.stroke();
  const v = g.createRadialGradient(SW / 2, SH / 2, SH * .3, SW / 2, SH / 2, SW * .75);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.55)');
  g.fillStyle = v; g.fillRect(0, 0, SW, SH);
}
function creamBg(g) {
  const r = g.createRadialGradient(SW / 2, SH * .42, 40, SW / 2, SH / 2, SW * .75);
  r.addColorStop(0, '#FFFFFF'); r.addColorStop(1, '#ECE7DC');
  g.fillStyle = r; g.fillRect(0, 0, SW, SH);
}

// ------------------------------------------------------------------ logo
function logoMark(g, x, y, s, prog, col = C.orange) {
  // rounded tile with a sine "vibe" wave drawn on
  g.save(); g.translate(x, y); g.scale(s, s);
  const k = E.outB(clamp(prog * 1.6));
  g.save(); g.scale(k, k); g.fillStyle = col; rr(g, -60, -60, 120, 120, 30); g.fill(); g.restore();
  const p = clamp((prog - .25) / .75);
  if (p > 0) {
    g.strokeStyle = '#fff'; g.lineWidth = 11; g.lineCap = 'round'; g.beginPath();
    const n = 40;
    for (let i = 0; i <= n * p; i++) { const u = i / n, xx = -36 + u * 72, yy = Math.sin(u * TAU * 1.25 + .3) * 16 * Math.sin(u * Math.PI); i ? g.lineTo(xx, yy) : g.moveTo(xx, yy); }
    g.stroke();
  }
  g.restore();
}
function logo(g, cx, cy, t, t0, s = 1, inkCol = C.ink) {
  const pm = inv(t0, t0 + .7, t);
  at(g, cx, cy, s, 1, () => {
    g.font = SANS(800, 150); const w1 = g.measureText('Vibe ').width;
    g.font = SERIF(178); const w2 = g.measureText('Editing').width;
    const total = 120 + 40 + w1 + w2, x0 = -total / 2;
    logoMark(g, x0 + 60, -8, 1, pm);
    const a1 = ease(t, t0 + .12, .4), a2 = ease(t, t0 + .26, .4);
    g.save(); g.globalAlpha *= a1; g.font = SANS(800, 150); g.fillStyle = inkCol; g.fillText('Vibe ', x0 + 160, 50 + (1 - a1) * 30); g.restore();
    g.save(); g.globalAlpha *= a2; g.font = SERIF(178); g.fillStyle = C.orange; g.fillText('Editing', x0 + 160 + w1, 50 + (1 - a2) * 30); g.restore();
  });
}

// ------------------------------------------------------------------ scene 1: 1:14 AM + timeline flood
const CLIPS = (() => {
  const R = rng(7), out = [], cols = [C.violet, C.orange, C.green, C.pink, C.blue, '#C9C35A'];
  for (let i = 0; i < 200; i++) {
    const tr = Math.floor(R() * 6), x = R() * 1260, w = 18 + R() * 90;
    out.push({ tr, x, w, c: cols[tr], t: i * .0065 + R() * .05 });
  }
  return out;
})();
function sClock(g, t) {
  nightBg(g, t);
  const tEnd = W_.cuts - .05;
  const exit = ease(t, tEnd - .3, .3, E.inC);
  // clock: centred, then lifts and shrinks when the timeline floods in
  const lift = ease(t, W_.still, .55, E.ioC);
  const cy = lerp(520, 190, lift), cs = lerp(1, .42, lift);
  const intro = ease(t, 0, .5);
  at(g, SW / 2, cy - exit * 80, cs * lerp(1.06, 1, intro), intro * (1 - exit), () => {
    g.font = MONO(30); g.fillStyle = 'rgba(246,244,239,0.55)'; g.textAlign = 'center';
    g.fillText('FRIDAY, OCTOBER 3', 0, -190);
    g.font = SANS(800, 320); g.textAlign = 'left';
    const base = '1:1', wb = g.measureText(base).width, wd = g.measureText('4').width;
    g.font = SANS(700, 86); const wam = g.measureText('AM').width;
    const x0 = -(wb + wd + 24 + wam) / 2;
    g.font = SANS(800, 320); g.fillStyle = C.white; g.fillText(base, x0, 100);
    // last digit rolls 3 -> 4 on "fourteen"
    const k = ease(t, W_.fourteen, .4, E.outB);
    g.save(); g.beginPath(); g.rect(x0 + wb - 10, -170, wd + 30, 300); g.clip();
    g.fillText('3', x0 + wb, 100 - k * 300); g.fillText('4', x0 + wb, 400 - k * 300); g.restore();
    g.font = SANS(700, 86); g.fillStyle = C.orange; g.fillText('AM', x0 + wb + wd + 24, 100);
  });
  // timeline panel
  const pin = ease(t, W_.still - .05, .5, E.outC);
  if (pin > 0) {
    const px = 150, py = lerp(520, 350, pin), pw = 1300, ph = 520;
    g.save(); g.globalAlpha = pin * (1 - exit); g.translate(0, exit * 60);
    g.fillStyle = C.panel; rr(g, px, py, pw, ph, 26); g.fill();
    g.strokeStyle = 'rgba(255,255,255,0.10)'; g.lineWidth = 2; g.stroke();
    g.font = MONO(22); g.fillStyle = 'rgba(246,244,239,0.5)'; g.textAlign = 'left';
    g.fillText('reel_final_FINAL_v7.prproj', px + 30, py + 44);
    const shown = CLIPS.filter(c => t >= W_.still + .15 + c.t).length;
    g.textAlign = 'right'; g.fillStyle = C.orange; g.fillText(`${shown} CLIPS`, px + pw - 30, py + 44);
    for (let r = 0; r < 6; r++) {
      g.fillStyle = 'rgba(255,255,255,0.035)'; rr(g, px + 20, py + 74 + r * 72, pw - 40, 60, 10); g.fill();
    }
    for (const c of CLIPS) {
      const k = ease(t, W_.still + .15 + c.t, .25, E.outB);
      if (k <= 0) continue;
      const y = py + 80 + c.tr * 72, h = 48;
      g.save(); g.translate(px + 20 + c.x + c.w / 2, y + h / 2); g.scale(k, k);
      g.fillStyle = c.c; g.globalAlpha *= .85; rr(g, -c.w / 2, -h / 2, c.w, h, 7); g.fill(); g.restore();
    }
    // playhead
    const ph_x = px + 40 + ((t - W_.still) * 260) % (pw - 80);
    g.fillStyle = '#FF3B4E'; g.fillRect(ph_x, py + 64, 3, ph - 84);
    g.beginPath(); g.moveTo(ph_x - 10, py + 60); g.lineTo(ph_x + 13, py + 60); g.lineTo(ph_x + 1.5, py + 74); g.fill();
    g.restore();
  }
  // "for one reel."
  const p = pop(t, W_.oneReel - .05);
  at(g, SW / 2, 945 - p.dy - exit * 40, p.s, p.a * (1 - exit), () => {
    g.shadowColor = 'rgba(0,0,0,0.6)'; g.shadowBlur = 30;
    runs(g, [['all for ', SANS(800, 92), C.white], ['one', SERIF(112), C.orange], [' reel.', SANS(800, 92), C.white]], 0, 0);
  });
}

// ------------------------------------------------------------------ scene 2: cuts here, captions there, keyframes everywhere
const CARDS = (() => {
  const R = rng(21), out = [];
  const add = (type, n, t0, side, hx, hy, sx, sy) => {
    for (let i = 0; i < n; i++) out.push({
      type, t: t0 + i * .07 + R() * .05, side,
      hx: hx + (R() - .5) * sx, hy: hy + (R() - .5) * sy, rot: (R() - .5) * .25, ang: R() * TAU, s: .8 + R() * .3,
    });
  };
  add('cut', 9, W_.cuts - .05, -1, 470, 470, 640, 520);
  add('cap', 9, W_.captions - .05, 1, 1130, 470, 640, 520);
  add('key', 10, W_.keyframes - .05, 0, 800, 500, 1300, 800);
  out.forEach((c, i) => { c.ring = i / out.length * TAU + R() * .1; c.rr = .85 + R() * .3; });
  return out;
})();
function card(g, c) {
  const w = 240, h = 104;
  g.fillStyle = '#1D2040'; rr(g, -w / 2, -h / 2, w, h, 16); g.fill();
  g.strokeStyle = 'rgba(255,255,255,0.12)'; g.lineWidth = 2; g.stroke();
  g.fillStyle = c.type === 'cut' ? C.violet : c.type === 'cap' ? C.orange : C.green;
  rr(g, -w / 2 + 16, -h / 2 + 16, 44, 44, 10); g.fill();
  g.strokeStyle = '#fff'; g.fillStyle = '#fff'; g.lineWidth = 3.5; g.lineCap = 'round';
  const ix = -w / 2 + 38, iy = -h / 2 + 38;
  if (c.type === 'cut') { // scissors
    g.beginPath(); g.arc(ix - 8, iy + 9, 5, 0, TAU); g.arc(ix + 8, iy + 9, 5, 0, TAU); g.stroke();
    g.beginPath(); g.moveTo(ix - 5, iy + 5); g.lineTo(ix + 9, iy - 12); g.moveTo(ix + 5, iy + 5); g.lineTo(ix - 9, iy - 12); g.stroke();
  } else if (c.type === 'cap') {
    g.font = SANS(800, 24); g.textAlign = 'center'; g.fillText('Aa', ix, iy + 9);
  } else {
    g.beginPath(); g.moveTo(ix, iy - 12); g.lineTo(ix + 12, iy); g.lineTo(ix, iy + 12); g.lineTo(ix - 12, iy); g.closePath(); g.fill();
  }
  g.textAlign = 'left'; g.font = MONO(19); g.fillStyle = 'rgba(246,244,239,0.75)';
  g.fillText(c.type === 'cut' ? 'Cut 00:14:22' : c.type === 'cap' ? 'Caption #37' : 'Keyframe 12', -w / 2 + 74, -h / 2 + 34);
  g.fillStyle = 'rgba(255,255,255,0.16)';
  for (let i = 0; i < 9; i++) { const bh = 6 + hash(i + c.ang * 10) * 22; g.fillRect(-w / 2 + 74 + i * 15, h / 2 - 18 - bh, 9, bh); }
}
function sMess(g, t) {
  nightBg(g, t);
  const ring = ease(t, W_.everywhere - .1, .7, E.ioC);
  const col = ease(t, W_.so, .75, E.inC);                     // collapse into the dot
  for (const c of CARDS) {
    const k = ease(t, c.t, .55, E.outC);
    if (k <= 0) continue;
    const fromX = c.side < 0 ? -300 : c.side > 0 ? SW + 300 : c.hx + Math.cos(c.ang) * 900;
    const fromY = c.side === 0 ? c.hy + Math.sin(c.ang) * 700 : c.hy + (hash(c.ang) - .5) * 300;
    let x = lerp(fromX, c.hx, k), y = lerp(fromY, c.hy, k), rot = c.rot * (1 - k * .4), s = c.s;
    const a = c.ring + t * .22 - col * 2.2;
    const rad = lerp(1, .0, col);
    const ox = SW / 2 + Math.cos(a) * 650 * c.rr * rad, oy = SH / 2 + Math.sin(a) * 380 * c.rr * rad;
    x = lerp(x, ox, ring); y = lerp(y, oy, ring); rot = lerp(rot, 0, ring);
    s *= lerp(1, .78, ring) * (1 - col);
    at(g, x, y, s, k * (1 - ease(t, W_.so + .45, .3)), () => card(g, c), rot);
  }
  const fadeHT = 1 - ease(t, W_.keyframes, .35);
  let p = pop(t, W_.cuts);
  at(g, 140, 210 - p.dy, p.s, p.a * fadeHT, () => runs(g, [['Cuts ', SANS(800, 120), C.white], ['here.', SERIF(140), C.orange]], 0, 0, 'left'));
  p = pop(t, W_.captions);
  at(g, SW - 140, 880 - p.dy, p.s, p.a * fadeHT, () => runs(g, [['Captions ', SANS(800, 120), C.white], ['there.', SERIF(140), C.orange]], 0, 0, 'right'));
  p = pop(t, W_.keyframes - .03, .45);
  at(g, SW / 2, SH / 2 - 120 - p.dy, p.s * (1 - col), p.a * (1 - col), () => { g.shadowColor = 'rgba(0,0,0,0.7)'; g.shadowBlur = 40; runs(g, [['Keyframes', SANS(800, 84), 'rgba(246,244,239,0.7)']], 0, 0); });
  p = pop(t, W_.everywhere - .05, .5);
  const ws = 1 - col;
  at(g, SW / 2, SH / 2 + 60 - p.dy, p.s * ws, p.a * ws, () => {
    g.shadowColor = 'rgba(0,0,0,0.7)'; g.shadowBlur = 40;
    runs(g, [['everywhere.', SANS(800, 210), C.white]], 0, 0);
  });
  // the dot left behind
  const d = ease(t, W_.so + .5, .3, E.outB);
  if (d > 0) {
    const pulse = 1 + .12 * Math.sin((t - W_.so) * 7) * ease(t, W_.so + .9, .3);
    g.fillStyle = C.orange; g.beginPath(); g.arc(SW / 2, SH / 2, 16 * d * pulse, 0, TAU); g.fill();
  }
}

// ------------------------------------------------------------------ scene 3: meet Vibe Editing (cream wipe)
function sMeet(g, t) {
  nightBg(g, t);
  const k = ease(t, W_.meet - .06, .5, E.outX);
  g.save(); g.beginPath(); g.arc(SW / 2, SH / 2, 16 + k * 1000, 0, TAU); g.clip();
  creamBg(g);
  logo(g, SW / 2, SH / 2 + 20, t, W_.vibe - .05, 1);
  g.restore();
  if (k < .99) { g.fillStyle = C.orange; g.globalAlpha = 1 - k; g.beginPath(); g.arc(SW / 2, SH / 2, 16 + k * 1000, 0, TAU); g.lineWidth = 6; g.strokeStyle = C.orange; g.stroke(); g.globalAlpha = 1; }
}

// ------------------------------------------------------------------ scene 4: 6h -> 12m
const DEDUCT = [
  { t: W_.cutting, label: 'Cutting', icon: 'cut', mins: 110 },
  { t: W_.capt, label: 'Captions', icon: 'cap', mins: 100 },
  { t: W_.zooms, label: 'Zooms', icon: 'key', mins: 85 },
  { t: W_.sound + .1, label: 'Sound effects', icon: 'snd', mins: 53 },
];
const fmtHM = m => { m = Math.max(0, Math.round(m)); const h = Math.floor(m / 60), mm = m % 60; return h ? [`${h}`, 'h ', `${String(mm).padStart(2, '0')}`, 'm'] : [`${mm}`, 'm']; };
function minutesAt(t) {
  let m = 360 * ease(t, W_.six, .7, E.outC);
  for (const d of DEDUCT) m -= d.mins * ease(t, d.t + .18, .45, E.ioC);
  return m;
}
function bigNumber(g, x, y, mins, col, s = 1) {
  const parts = fmtHM(mins), big = SANS(800, 300 * s), small = SANS(700, 150 * s);
  const r = parts.map((p, i) => [p, i % 2 ? small : big, col]);
  runs(g, r, x, y);
}
function sNumber(g, t) {
  creamBg(g);
  const lo = ease(t, W_.one - .15, .4, E.inC);
  if (lo < 1) { g.save(); g.globalAlpha = 1 - lo; g.translate(0, -lo * 220); logo(g, SW / 2, SH / 2 + 20, 99, 0, 1); g.restore(); }
  const exit = ease(t, W_.just - .1, .45, E.inC);
  const cx = SW / 2, ny = 500 - exit * 120;
  // label above the number
  const labels = [[W_.one - .05, 'One reel. Edited by hand.'], [W_.now - .05, 'Now take out…'], [W_.twelve - .05, 'Same reel. Vibe edited.']];
  labels.forEach(([t0, s], i) => {
    const nxt = labels[i + 1] ? labels[i + 1][0] : 1e9;
    const a = ease(t, t0, .35) * (1 - ease(t, nxt - .15, .2));
    if (a <= 0) return;
    g.save(); g.globalAlpha = a * (1 - exit); g.font = SANS(600, 46); g.textAlign = 'center';
    g.fillStyle = i === 2 ? C.orange : C.grey; g.fillText(s, cx, ny - 250 + (1 - a) * 14); g.restore();
  });
  // number
  const appear = ease(t, W_.six - .05, .35);
  const m = minutesAt(t);
  const done = ease(t, W_.twelve - .05, .45, E.outB);
  const col = mix('#75757E', C.ink, done);
  // micro "roll" bump whenever the value is moving
  let jiggle = 0;
  for (const d of DEDUCT) jiggle += Math.sin(inv(d.t + .18, d.t + .63, t) * Math.PI) * 10;
  at(g, cx, ny + jiggle * .4, lerp(.94, 1, appear) * lerp(1, 1.12, done), appear * (1 - exit), () => bigNumber(g, 0, 0, m, col));
  // strike-throughs
  for (const d of DEDUCT) {
    const sk = ease(t, d.t - .02, .2, E.outQ), sf = 1 - ease(t, d.t + .25, .25);
    if (sk <= 0 || sf <= 0) continue;
    g.save(); g.globalAlpha = sf * (1 - exit); g.strokeStyle = C.orange; g.lineWidth = 12; g.lineCap = 'round';
    g.beginPath(); g.moveTo(cx - 400, ny - 70); g.lineTo(cx - 400 + 800 * sk, ny - 110); g.stroke(); g.restore();
  }
  // "Ugh."
  const u = pop(t, W_.ugh - .03, .4, [W_.now - .1, .3]);
  at(g, cx + 470, ny - 210 - u.dy, u.s, u.a, () => { g.font = SERIF(130); g.fillStyle = C.orange; g.textAlign = 'center'; g.fillText('Ugh.', 0, 0); }, -.1);
  // deduction chips
  const chipsOut = ease(t, W_.twelve - .1, .35, E.inC);
  DEDUCT.forEach((d, i) => {
    const k = ease(t, d.t + .05, .55, E.outC);
    if (k <= 0) return;
    const tx = cx + (i % 2 ? 300 : -300), ty = 700 + Math.floor(i / 2) * 104;
    const x = lerp(cx + 260, tx, k), y = lerp(ny - 60, ty, k);
    at(g, x, y + chipsOut * 40, lerp(.5, 1, E.outB(k)), clamp(k * 2) * (1 - chipsOut) * (1 - exit), () => {
      const w = 540, h = 80;
      g.fillStyle = '#fff'; g.shadowColor = 'rgba(0,0,0,0.08)'; g.shadowBlur = 24; g.shadowOffsetY = 8;
      rr(g, -w / 2, -h / 2, w, h, 40); g.fill(); g.shadowColor = 'transparent';
      g.strokeStyle = '#E6E1D6'; g.lineWidth = 2; g.stroke();
      g.fillStyle = C.orange; g.font = SANS(800, 40); g.textAlign = 'left'; g.fillText('−', -w / 2 + 30, 14);
      g.fillStyle = C.ink; g.font = SANS(600, 36); g.fillText(d.label, -w / 2 + 72, 13);
      const hm = fmtHM(d.mins).join('');
      g.fillStyle = C.grey; g.font = MONO(30); g.textAlign = 'right'; g.fillText('−' + hm, w / 2 - 30, 11);
    });
  });
  // "Nice."
  const n = pop(t, W_.nice - .03, .4, [W_.just - .1, .3]);
  at(g, cx + 430, ny - 230 - n.dy, n.s, n.a, () => {
    g.font = SERIF(130); g.fillStyle = C.orange; g.textAlign = 'center'; g.fillText('Nice.', 0, 0);
    g.strokeStyle = C.orange; g.lineWidth = 6; g.lineCap = 'round';
    const sp = ease(t, W_.nice + .05, .35);
    for (let i = 0; i < 3; i++) { const a = -2.3 + i * .55; g.beginPath(); g.moveTo(Math.cos(a) * 120 + 130, Math.sin(a) * 70 - 40); g.lineTo(Math.cos(a) * (120 + 50 * sp) + 130, Math.sin(a) * (70 + 30 * sp) - 40); g.globalAlpha *= sp; g.stroke(); }
  }, -.08);
}

// ------------------------------------------------------------------ scene 5: prompt bar
const PROMPT = 'make it punchy, add captions, cut the pauses';
const T_TYPE0 = W_.type - .05, T_TYPE1 = W_.hit - .08;
function sPrompt(g, t, bg = true) {
  if (bg) creamBg(g);
  const inK = ease(t, W_.just - .05, .5, E.outB);
  const exit = ease(t, W_.enter + .32, .4, E.inC);
  const cy = SH / 2;
  at(g, SW / 2, cy + (1 - inK) * 60 - exit * 40, lerp(.9, 1, inK) * lerp(1, .6, exit), clamp(inK * 1.5) * (1 - exit), () => {
    const w = 1300, h = 150;
    g.fillStyle = '#fff'; g.shadowColor = 'rgba(40,30,10,0.14)'; g.shadowBlur = 60; g.shadowOffsetY = 20;
    rr(g, -w / 2, -h / 2, w, h, 75); g.fill(); g.shadowColor = 'transparent';
    g.strokeStyle = '#E6E1D6'; g.lineWidth = 2.5; g.stroke();
    // sparkle icon
    g.fillStyle = C.orange; g.save(); g.translate(-w / 2 + 75, 0);
    g.beginPath(); for (let i = 0; i < 8; i++) { const r = i % 2 ? 9 : 26, a = i / 8 * TAU - Math.PI / 2; g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } g.fill(); g.restore();
    // typed text
    const n = Math.floor(PROMPT.length * inv(T_TYPE0, T_TYPE1, t));
    const s = PROMPT.slice(0, n);
    g.font = SANS(500, 46); g.textAlign = 'left'; g.fillStyle = n ? C.ink : C.soft;
    const tx = -w / 2 + 130;
    g.fillText(n ? s : 'Describe your edit…', tx, 16);
    const cw = n ? g.measureText(s).width : 0;
    if (Math.floor(t * 2.4) % 2 === 0 || (t > T_TYPE0 && t < T_TYPE1)) { g.fillStyle = C.orange; g.fillRect(tx + cw + 4, -28, 4, 56); }
    // send button
    const press = Math.sin(inv(W_.enter - .05, W_.enter + .15, t) * Math.PI);
    g.save(); g.translate(w / 2 - 80, 0); g.scale(1 - press * .15, 1 - press * .15);
    g.fillStyle = C.orange; g.beginPath(); g.arc(0, 0, 50, 0, TAU); g.fill();
    g.strokeStyle = '#fff'; g.lineWidth = 7; g.lineCap = 'round'; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(0, 20); g.lineTo(0, -20); g.moveTo(-15, -6); g.lineTo(0, -21); g.lineTo(15, -6); g.stroke();
    g.restore();
    // ripple
    const rp = inv(W_.enter, W_.enter + .6, t);
    if (rp > 0 && rp < 1) { g.strokeStyle = C.orange; g.globalAlpha *= 1 - rp; g.lineWidth = 6; g.beginPath(); g.arc(w / 2 - 80, 0, 50 + E.outC(rp) * 220, 0, TAU); g.stroke(); }
  });
}

// ------------------------------------------------------------------ scene 6: phone, every night before chai, posted
function phone(g, t, a) {
  const pw = 380, ph = 780;
  g.fillStyle = C.ink; rr(g, -pw / 2 - 12, -ph / 2 - 12, pw + 24, ph + 24, 70); g.fill();
  const sg = g.createLinearGradient(0, -ph / 2, 0, ph / 2);
  sg.addColorStop(0, '#FBF8F2'); sg.addColorStop(.6, '#F7E9DA'); sg.addColorStop(1, '#FFB27A');
  g.fillStyle = sg; rr(g, -pw / 2, -ph / 2, pw, ph, 58); g.fill();
  g.fillStyle = C.ink; rr(g, -60, -ph / 2 + 18, 120, 34, 17); g.fill();
  g.fillStyle = C.grey; g.font = SANS(600, 24); g.textAlign = 'center'; g.fillText('Friday, October 3', 0, -ph / 2 + 120);
  g.fillStyle = C.ink; g.font = SANS(700, 120); g.fillText('10:02', 0, -ph / 2 + 235);
  // notification
  const nk = ease(t, W_.posted - .08, .5, E.outB);
  if (nk > 0) {
    g.save(); g.translate(0, -ph / 2 + 330 + (1 - nk) * -120); g.globalAlpha *= clamp(nk * 1.5);
    const w = pw - 36, h = 112;
    g.fillStyle = 'rgba(255,255,255,0.92)'; g.shadowColor = 'rgba(0,0,0,0.12)'; g.shadowBlur = 20; g.shadowOffsetY = 6;
    rr(g, -w / 2, -h / 2, w, h, 26); g.fill(); g.shadowColor = 'transparent';
    logoMark(g, -w / 2 + 50, 0, .42, 1);
    g.textAlign = 'left'; g.fillStyle = C.ink; g.font = SANS(700, 26); g.fillText('Vibe Editing', -w / 2 + 92, -10);
    g.fillStyle = '#4b4b52'; g.font = SANS(500, 24); g.fillText('Your reel is live  ✓', -w / 2 + 92, 26);
    g.fillStyle = C.grey; g.font = SANS(500, 20); g.textAlign = 'right'; g.fillText('now', w / 2 - 20, -12);
    g.restore();
  }
  // hearts
  for (let i = 0; i < 9; i++) {
    const t0 = W_.posted + .25 + i * .14, p = inv(t0, t0 + 1.6, t);
    if (p <= 0 || p >= 1) continue;
    const x = 110 + noise1(i * 3.1 + p * 3) * 40 - p * 30 + i * 6, y = ph / 2 - 90 - E.outQ(p) * 420;
    g.globalAlpha = a * (1 - p) * clamp(p * 6); g.fillStyle = i % 3 ? C.orange : '#FF4D6D';
    heart(g, x, y, 34 + (i % 3) * 8); g.globalAlpha = a;
  }
}
function sPhone(g, t) {
  creamBg(g);
  const inK = ease(t, W_.enter + .45, .6, E.outC);
  const exit = ease(t, W_.fewer - .42, .35, E.inC);
  at(g, SW / 2, SH / 2 + (1 - inK) * 700 - exit * 200, 1, 1 - exit, () => phone(g, t, 1 - exit));
  let p = pop(t, W_.every - .03, .45, [W_.fewer - .45, .25]);
  at(g, 560, SH / 2 + 30 - p.dy, p.s, p.a, () => runs(g, [['Every ', SANS(800, 84), C.ink], ['night.', SERIF(104), C.orange]], 0, 0, 'right'));
  p = pop(t, W_.before - .03, .45, [W_.fewer - .45, .25]);
  at(g, 1040, SH / 2 + 30 - p.dy, p.s, p.a, () => {
    runs(g, [['before ', SANS(800, 84), C.ink], ['chai.', SERIF(104), C.orange]], 0, 0, 'left');
    // chai cup with steam
    const cx = 120, cy = 110, ck = ease(t, W_.chai - .05, .4, E.outB);
    g.save(); g.translate(cx, cy); g.scale(ck, ck);
    g.strokeStyle = C.ink; g.lineWidth = 6; g.lineJoin = 'round'; g.lineCap = 'round';
    g.beginPath(); g.moveTo(-40, -10); g.lineTo(-32, 50); g.lineTo(32, 50); g.lineTo(40, -10); g.closePath();
    g.fillStyle = '#E9C9A3'; g.fill(); g.stroke();
    g.beginPath(); g.arc(50, 15, 16, -1.2, 1.2); g.stroke();
    g.strokeStyle = 'rgba(23,23,28,0.45)'; g.lineWidth = 5;
    for (let i = -1; i <= 1; i++) { g.beginPath(); for (let k = 0; k <= 12; k++) { const yy = -25 - k * 5, xx = i * 18 + Math.sin(k * .7 + t * 6 + i) * 6; k ? g.lineTo(xx, yy) : g.moveTo(xx, yy); } g.stroke(); }
    g.restore();
  });
  p = pop(t, W_.posted - .05, .45, [W_.fewer - .45, .25]);
  at(g, SW / 2, 960 - p.dy, p.s, p.a, () => runs(g, [['Posted.', SERIF(90), C.orange]], 0, 0));
}

// ------------------------------------------------------------------ scene 7: fewer clicks. more posts. + logo
function sTag(g, t) {
  creamBg(g);
  const exit = ease(t, W_.vibe2 - .42, .32, E.inC);
  const mask = (y0, t0, fn) => {
    const k = ease(t, t0, .5, E.outX);
    g.save(); g.beginPath(); g.rect(0, y0 - 190, SW, 240); g.clip();
    g.translate(0, (1 - k) * 220 - exit * 240); fn(); g.restore();
  };
  mask(450, W_.fewer - .04, () => runs(g, [['Fewer clicks.', SANS(800, 180), C.ink]], SW / 2, 450));
  mask(670, W_.more - .04, () => runs(g, [['More posts.', SERIF(210), C.orange]], SW / 2, 670));
}
function sLogo2(g, t) {
  creamBg(g);
  logo(g, SW / 2, SH / 2 + 20, t, W_.vibe2 - .1, 1);
}

// ------------------------------------------------------------------ scene 8: the reveal (code editor) + CTA
const CODE = [
  "const W_ = { fourteen: 0.52, still: 1.92, cuts: 4.61,",
  "  everywhere: 7.90, meet: 10.89, twelve: 21.48 };",
  "",
  "function sNumber(g, t) {",
  "  creamBg(g);",
  "  const m = minutesAt(t);   // 6h -> 12m",
  "  bigNumber(g, cx, ny, m, mix('#75757E', C.ink, done));",
  "  for (const d of DEDUCT) strike(g, d.t);",
  "}",
  "",
  "function sPrompt(g, t) {",
  "  const s = PROMPT.slice(0, typed(t));",
  "  ripple(g, W_.enter, C.orange);",
  "}",
  "",
  "// every frame is a pure function of t",
  "window.renderFrame = i => draw(i / FPS);",
  "",
  "music.duck(voice, -9);  sfx.at(W_.posted, 'ding');",
  "render({ fps: 30, size: [1080, 1920] });",
];
function codeLine(g, s, x, y) {
  const toks = s.split(/(\s+|[(){}\[\],;.]|'[^']*'|\/\/.*$)/).filter(Boolean);
  let cx = x;
  for (const k of toks) {
    let c = '#C9CBE0';
    if (/^\/\//.test(k)) c = '#5D6188';
    else if (/^'/.test(k)) c = '#8BD49C';
    else if (/^(const|function|for|of|return|window)$/.test(k)) c = '#B48CFF';
    else if (/^-?[\d.]+$/.test(k)) c = C.orange;
    else if (/^[A-Z_]+$/.test(k)) c = '#6CC4FF';
    g.fillStyle = c; g.fillText(k, cx, y); cx += g.measureText(k).width;
  }
}
function sOutro(g, t) {
  // editor
  g.fillStyle = '#0E0F1C'; g.fillRect(0, 0, SW, SH);
  g.fillStyle = '#14152A'; g.fillRect(0, 0, SW, 46);
  ['#FF5F57', '#FEBC2E', '#28C840'].forEach((c, i) => { g.fillStyle = c; g.beginPath(); g.arc(28 + i * 26, 23, 8, 0, TAU); g.fill(); });
  g.font = MONO(20); g.fillStyle = '#6E7196'; g.textAlign = 'left'; g.fillText('faceless-reel / reel.js', 120, 30);
  g.font = MONO(24);
  const scroll = (t - W_.oh) * 22;
  for (let i = 0; i < 40; i++) {
    const y = 100 + i * 36 - scroll;
    if (y < 70 || y > 760) continue;
    g.fillStyle = '#3E4166'; g.textAlign = 'right'; g.fillText(String(i + 1), 64, y);
    g.textAlign = 'left'; codeLine(g, CODE[i % CODE.length], 90, y);
  }
  // timeline bars at the bottom
  g.fillStyle = '#121327'; g.fillRect(0, 780, SW, SH - 780);
  const cols = [C.violet, C.orange, C.green, C.pink, C.blue];
  for (let r = 0; r < 5; r++) for (let i = 0; i < 9; i++) {
    const x = 30 + (hash(r * 20 + i) * .3 + i) * 175, w = 70 + hash(r * 9 + i * 3) * 110;
    g.fillStyle = cols[(r + i) % 5]; g.globalAlpha = .85; rr(g, x, 800 + r * 38, w, 26, 8); g.fill();
  }
  g.globalAlpha = 1;
  const ph = 40 + ((t - W_.oh) * 140) % (SW - 80);
  g.fillStyle = '#FF3B4E'; g.fillRect(ph, 790, 3, 200);
  const c = pop(t, W_.comment - .05, .5);
  g.fillStyle = `rgba(8,8,16,${.6 * c.a})`; g.fillRect(0, 0, SW, SH);
  // the cream screen shrinks into a floating window
  const k = ease(t, W_.oh, .55, E.ioX);
  const wx = lerp(SW / 2, 1080, k), wy = lerp(SH / 2, 360, k), ws = lerp(1, .5, k);
  g.save(); g.translate(wx, wy); g.scale(ws, ws);
  g.shadowColor = 'rgba(0,0,0,0.6)'; g.shadowBlur = 80 * k; g.shadowOffsetY = 30 * k;
  g.fillStyle = C.cream; rr(g, -SW / 2, -SH / 2, SW, SH, 40 * k); g.fill(); g.shadowColor = 'transparent';
  g.save(); g.beginPath(); g.roundRect(-SW / 2, -SH / 2, SW, SH, 40 * k); g.clip(); g.translate(-SW / 2, -SH / 2);
  creamBg(g);
  const sw = ease(t, W_.made - .08, .5, E.ioC);   // logo slides up, "Made with AI." slides in
  g.save(); g.translate(0, -sw * 400); g.globalAlpha = 1 - sw; logo(g, SW / 2, SH / 2 + 20, 99, 0, 1); g.restore();
  g.save(); g.translate(0, (1 - sw) * 400); g.globalAlpha = sw;
  const ai = ease(t, W_.ai - .05, .4, E.outB);
  runs(g, [['Made with ', SANS(800, 190), C.ink]], SW / 2 - 110, SH / 2 + 70);
  g.font = SANS(800, 190); const mw = g.measureText('Made with ').width;
  at(g, SW / 2 - 110 + mw / 2 + 10, SH / 2 + 70, lerp(.6, 1, ai), ai, () => runs(g, [['AI.', SERIF(240), C.orange]], 0, 0, 'left'));
  g.restore();
  g.restore();
  g.restore();
  // "And this whole video?" caption in the editor
  const q = pop(t, W_.and - .05, .45, [W_.comment - .2, .3]);
  at(g, 90, 470 - q.dy, q.s, q.a * k, () => {
    g.shadowColor = '#0E0F1C'; g.shadowBlur = 30; g.font = SANS(800, 64); g.fillStyle = C.white; g.textAlign = 'left'; g.fillText('And this', 0, 0);
    g.fillText('whole video?', 0, 76);
  });
  // CTA pill (editor dims behind it)
  at(g, SW / 2, 770 - c.dy, c.s * 1.35, c.a, () => {
    const w = 760, h = 150, glow = .6 + .4 * Math.sin((t - W_.comment) * 5);
    g.shadowColor = C.orange; g.shadowBlur = 50 * glow;
    g.fillStyle = '#17182E'; rr(g, -w / 2, -h / 2, w, h, 75); g.fill();
    g.shadowBlur = 0; g.strokeStyle = C.orange; g.lineWidth = 5; g.stroke();
    // chat bubble icon
    g.save(); g.translate(-w / 2 + 85, 0); g.strokeStyle = C.white; g.lineWidth = 6; g.lineJoin = 'round';
    g.beginPath(); g.roundRect(-30, -26, 60, 44, 12); g.moveTo(-12, 18); g.lineTo(-20, 34); g.lineTo(4, 18); g.stroke(); g.restore();
    const n = Math.floor(5 * inv(W_.vibeW - .05, W_.vibeW + .3, t));
    runs(g, [['Comment ', SANS(800, 70), C.white], ['VIBE'.slice(0, n), SANS(800, 70), C.orange]], -w / 2 + 150, 25, 'left');
    if (n < 4 && Math.floor(t * 3) % 2 === 0) { g.font = SANS(800, 70); const ww = g.measureText('Comment ' + 'VIBE'.slice(0, n)).width; g.fillStyle = C.orange; g.fillRect(-w / 2 + 156 + ww, -28, 5, 64); }
  });
  // sparks when VIBE lands
  for (let i = 0; i < 14; i++) {
    const p = inv(W_.vibeW + .25, W_.vibeW + 1.1, t);
    if (p <= 0 || p >= 1) continue;
    const a = i / 14 * TAU, r = 230 + E.outC(p) * 260;
    g.globalAlpha = 1 - p; g.fillStyle = i % 2 ? C.orange : C.white;
    g.beginPath(); g.arc(SW / 2 + Math.cos(a) * r * 1.6, 770 + Math.sin(a) * r * .5, 7, 0, TAU); g.fill();
  }
  g.globalAlpha = 1;
}

// ------------------------------------------------------------------ screen: scene list
const SCENES = [
  [0, W_.cuts - .05, sClock],
  [W_.cuts - .05, W_.meet - .1, sMess],
  [W_.meet - .1, W_.one - .15, sMeet],
  [W_.one - .15, W_.just + .25, sNumber],
  [W_.just + .25, W_.enter + .45, sPrompt],
  [W_.enter + .45, W_.fewer - .05, sPhone],
  [W_.fewer - .05, W_.vibe2 - .05, sTag],
  [W_.vibe2 - .05, W_.oh, sLogo2],
  [W_.oh, DUR + 1, sOutro],
];
function drawScreen(t) {
  const g = SCR.g;
  g.save(); g.globalAlpha = 1; g.textBaseline = 'alphabetic';
  // short overlaps: the outgoing scene finishes its exit, the incoming scene draws on top
  for (const [a, b, fn] of SCENES) if (t >= a && t < b) fn(g, t);
  if (t >= W_.just - .1 && t < W_.just + .25) { g.save(); sPrompt(g, t, false); g.restore(); }
  if (t >= W_.enter + .3 && t < W_.enter + .45) { g.save(); g.globalAlpha = inv(W_.enter + .3, W_.enter + .45, t); sPhone(g, t); g.restore(); }
  g.restore();
}
// how bright the screen is (lights the keyboard + room)
function screenLum(t) {
  const up = ease(t, W_.meet - .06, .5, E.outX), down = ease(t, W_.oh, .55, E.ioX);
  return lerp(.12, 1, up) - down * .7;
}

// ------------------------------------------------------------------ room + laptop
const SX0 = 40, SY0 = 660, SWD = 1000, SHT = 625;   // screen rect on the 1080x1920 frame
const DECK = { y0: 1314, y1: 1680, l0: 0, r0: 1080, l1: -170, r1: 1250 };
const GRAIN = [0, 1, 2].map(s => {
  const c = mk(270, 480), d = c.g.createImageData(270, 480), R = rng(100 + s);
  for (let i = 0; i < d.data.length; i += 4) { const v = R() * 255; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255; }
  c.g.putImageData(d, 0, 0); return c;
});
function deckPt(u, v) {
  const pv = Math.pow(v, 1.25);
  const y = lerp(DECK.y0, DECK.y1, pv), l = lerp(DECK.l0, DECK.l1, pv), r = lerp(DECK.r0, DECK.r1, pv);
  return [lerp(l, r, u), y];
}
function quad(g, u0, v0, u1, v1) {
  const a = deckPt(u0, v0), b = deckPt(u1, v0), c = deckPt(u1, v1), d = deckPt(u0, v1);
  g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.lineTo(c[0], c[1]); g.lineTo(d[0], d[1]); g.closePath();
}
function drawRoom(g, t) {
  const lum = screenLum(t);
  g.fillStyle = '#050407'; g.fillRect(0, 0, W, H);
  // purple wall / curtain glow
  const wall = g.createRadialGradient(W * .55, 480, 60, W * .55, 600, 950);
  wall.addColorStop(0, 'rgba(118,62,210,0.62)'); wall.addColorStop(.5, 'rgba(70,30,140,0.32)'); wall.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = wall; g.fillRect(0, 0, W, 1400);
  for (let i = 0; i < 14; i++) {      // curtain folds
    const x = i * 80 + 20 + Math.sin(i * 1.7) * 18;
    const fg = g.createLinearGradient(x - 40, 0, x + 40, 0);
    fg.addColorStop(0, 'rgba(0,0,0,0)'); fg.addColorStop(.5, 'rgba(0,0,0,0.22)'); fg.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = fg; g.fillRect(x - 40, 0, 80, 1350);
  }
  // screen light spill on the wall
  GLOW.g.clearRect(0, 0, 120, 90); GLOW.g.filter = 'blur(9px)'; GLOW.g.drawImage(SCR, 20, 20, 80, 50); GLOW.g.filter = 'none';
  g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = .22 + .3 * lum;
  g.drawImage(GLOW, SX0 - SWD * .25, SY0 - SHT * .4, SWD * 1.5, SHT * 1.8); g.restore();
  // table + deck
  const tg = g.createLinearGradient(0, 1280, 0, H);
  tg.addColorStop(0, '#0c0b10'); tg.addColorStop(1, '#020203');
  g.fillStyle = tg; g.fillRect(0, 1280, W, H - 1280);
  const deckTop = mix('#17161c', '#9c99a6', lum * .85), deckBot = mix('#0a0a0d', '#3b3944', lum * .8);
  const dg = g.createLinearGradient(0, DECK.y0, 0, DECK.y1);
  dg.addColorStop(0, deckTop); dg.addColorStop(1, deckBot);
  g.fillStyle = dg; quad(g, 0, 0, 1, 1); g.fill();
  g.fillStyle = 'rgba(255,255,255,0.10)'; quad(g, 0, 0, 1, .012); g.fill();
  // keys (purple backlight)
  const keyFill = mix('#0d0c12', '#5b5675', lum * .7);
  const rows = [[.04, .10], [.115, .175], [.19, .25], [.265, .325], [.34, .40], [.415, .485]];
  rows.forEach(([v0, v1], r) => {
    const n = r === 5 ? 9 : 14;
    for (let k = 0; k < n; k++) {
      let u0, u1;
      if (r === 5) { const wd = [1, 1, 1, 1.2, 4.6, 1.2, 1, 1, 1]; const sum = wd.reduce((a, b) => a + b); let acc = 0; for (let j = 0; j < k; j++) acc += wd[j]; u0 = .09 + acc / sum * .82; u1 = u0 + wd[k] / sum * .82 - .006; }
      else { u0 = .09 + k / n * .82; u1 = u0 + .82 / n - .006; }
      g.fillStyle = keyFill; quad(g, u0, v0, u1, v1); g.fill();
      g.strokeStyle = `rgba(140,96,255,${.28 + .1 * Math.sin(t * .8 + k)})`; g.lineWidth = 1.5; g.stroke();
    }
  });
  // trackpad
  g.fillStyle = mix('#121117', '#8d8a96', lum * .75); quad(g, .32, .56, .68, .95); g.fill();
  g.strokeStyle = 'rgba(255,255,255,0.08)'; g.lineWidth = 2; g.stroke();
  // hinge + lid bezel
  g.fillStyle = '#08080a'; g.fillRect(SX0 - 30, SY0 + SHT + 14, SWD + 60, 26);
  g.fillStyle = '#0b0b0e'; rr(g, SX0 - 24, SY0 - 24, SWD + 48, SHT + 50, 26); g.fill();
  g.strokeStyle = 'rgba(255,255,255,0.10)'; g.lineWidth = 2; g.stroke();
  // the screen itself
  g.save(); rr(g, SX0, SY0, SWD, SHT, 8); g.clip();
  g.drawImage(SCR, SX0, SY0, SWD, SHT);
  const gl = g.createLinearGradient(SX0, SY0, SX0 + SWD, SY0 + SHT);
  gl.addColorStop(0, 'rgba(255,255,255,0.05)'); gl.addColorStop(.45, 'rgba(255,255,255,0)'); gl.addColorStop(1, 'rgba(255,255,255,0.02)');
  g.fillStyle = gl; g.fillRect(SX0, SY0, SWD, SHT);
  g.restore();
  // deck glow right under the screen
  const sp = g.createRadialGradient(W / 2, DECK.y0, 20, W / 2, DECK.y0, 700);
  sp.addColorStop(0, `rgba(255,250,240,${.10 + .22 * lum})`); sp.addColorStop(1, 'rgba(255,250,240,0)');
  g.fillStyle = sp; quad(g, 0, 0, 1, 1); g.fill();
}
function drawFrame(t) {
  t = clamp(t, 0, DUR);
  drawScreen(t);
  const g = TMP.g;
  // handheld camera: slow push-in + drift
  const s = 1.0 + .045 * (t / DUR) + .004 * noise1(t * .5 + 9);
  const dx = noise1(t * .6) * 7, dy = noise1(t * .5 + 40) * 6, rot = noise1(t * .4 + 80) * .0035;
  g.save(); g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
  g.translate(W / 2 + dx, 1000 + dy); g.rotate(rot); g.scale(s, s); g.translate(-W / 2, -1000);
  drawRoom(g, t);
  g.restore();
  // grain + vignette
  g.save(); g.globalCompositeOperation = 'overlay'; g.globalAlpha = .07;
  g.drawImage(GRAIN[Math.floor(Math.max(0, t) * 24) % 3], 0, 0, W, H); g.restore();
  const v = g.createRadialGradient(W / 2, H * .45, H * .25, W / 2, H / 2, H * .7);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.5)');
  g.fillStyle = v; g.fillRect(0, 0, W, H);
}

// ------------------------------------------------------------------ frame driver
window.META = { FRAMES: Math.round(DUR * FPS), FPS, DUR };
window.renderFrame = i => {
  const t = i / FPS;
  if (MB <= 1) { drawFrame(t); G.drawImage(TMP, 0, 0); return; }
  for (let k = 0; k < MB; k++) {
    drawFrame(t + (k / MB - .5) * SHUTTER / FPS);
    ACC.g.globalAlpha = 1 / (k + 1); ACC.g.drawImage(TMP, 0, 0);
  }
  ACC.g.globalAlpha = 1; G.drawImage(ACC, 0, 0);
};
window.READY = (async () => {
  await Promise.all([SANS(800, 40), SANS(500, 40), SANS(600, 40), SANS(700, 40), SERIF(40), MONO(20), '400 40px "Instrument Serif"'].map(f => document.fonts.load(f)));
  if (RENDER) { document.body.classList.add('render'); return true; }
  // live preview
  const audio = new Audio('work/narration.mp3');
  let t0 = performance.now(), off = 0, playing = false;
  addEventListener('keydown', e => {
    if (e.code === 'Space') { playing = !playing; if (playing) { t0 = performance.now(); audio.currentTime = off; audio.play(); } else { off += (performance.now() - t0) / 1000; audio.pause(); } }
    if (e.code === 'ArrowRight') off = Math.min(DUR, off + 1);
    if (e.code === 'ArrowLeft') off = Math.max(0, off - 1);
  });
  const loop = () => { const t = playing ? off + (performance.now() - t0) / 1000 : off; drawFrame(t % DUR); G.drawImage(TMP, 0, 0); requestAnimationFrame(loop); };
  loop();
  return true;
})();
