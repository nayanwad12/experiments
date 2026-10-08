'use strict';
// ONCOXPRESS band + ring teaser: 26.4 s sci-fi film. Holographic wireframe devices (true 3D, perspective-projected,
// additive glow + bloom), scan-plane materialisation, a particle morph from band to ring, HUD overlays and decoding
// display type. Every frame is a pure function of time t. 100 BPM: 1 beat = 0.6 s, 1 bar = 2.4 s, 11 bars.
// Cue times are mirrored in audio.py.

const W = 1920, H = 1080, DUR = 26.4;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 60);
const MB = +(Q.get('mb') || (RENDER ? 4 : 1));
const SHUTTER = 0.5;

const C = {
  bg0: '#010409', cyan: '#46F0FF', cyanHi: '#C4FCFF', teal: '#00D1B2', amber: '#FFB347', dim: '#4F7486', white: '#E9FBFF',
};
// ---- cues (keep in sync with audio.py)
const T_TITLE = 2.4, T_BAND = 4.8, T_DISSOLVE = 9.6, T_RING = 12.0, T_BOTH = 16.8, T_SOON = 21.6;

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
const E = { out: bez(0.16, 1, 0.3, 1), io: bez(0.65, 0, 0.35, 1), inn: bez(0.55, 0, 1, 0.45) };
const P = (t, t0, d = 0.9, e = E.out) => e(inv(t0, t0 + d, t));
function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
function rgba(h, a) { const n = parseInt(h.slice(1), 16); return `rgba(${n >> 16},${n >> 8 & 255},${n & 255},${a})`; }
function mk(w = W, h = H) { const c = document.createElement('canvas'); c.width = w; c.height = h; c.g = c.getContext('2d'); return c; }
function blur(g, b) { g.filter = b > 0.35 ? `blur(${b.toFixed(2)}px)` : 'none'; }

// ------------------------------------------------------------------ 3D
function xform(p, o) {   // object space -> camera space (pose o: yaw, pitch, roll, s)
  let [x, y, z] = p;
  let c = Math.cos(o.spin || 0), s = Math.sin(o.spin || 0); [y, z] = [y * c - z * s, y * s + z * c];   // spin about the object's own axis (x)
  c = Math.cos(o.roll || 0); s = Math.sin(o.roll || 0); [x, y] = [x * c - y * s, x * s + y * c];
  c = Math.cos(o.yaw); s = Math.sin(o.yaw); [x, z] = [x * c + z * s, -x * s + z * c];
  c = Math.cos(o.pitch); s = Math.sin(o.pitch); [y, z] = [y * c - z * s, y * s + z * c];
  return [x, y, z];
}
const DIST = 4.2;
function project(p, o) {   // -> [sx, sy, depth]
  const q = xform(p, o), k = DIST / (DIST + q[2]);
  return [o.x + q[0] * o.s * k, o.y - q[1] * o.s * k, q[2]];
}

// geometry as strands (polylines in object space) with a weight
function bandGeom() {
  const S = [];
  const a = 0.95, b = 0.78, hw = 0.3, N = 120;
  const loop = (sc, x) => { const pts = []; for (let i = 0; i <= N; i++) { const th = i / N * TAU; pts.push([x, b * sc * Math.sin(th), a * sc * Math.cos(th)]); } return pts; };
  for (const x of [-hw, hw]) { S.push({ p: loop(1, x), w: 1.0 }); S.push({ p: loop(0.9, x), w: 0.55 }); }
  for (const x of [-hw / 2, 0, hw / 2]) S.push({ p: loop(1, x), w: 0.3 });
  for (let i = 0; i < 72; i++) {
    const th = i / 72 * TAU, sn = Math.sin(th), cs = Math.cos(th);
    S.push({ p: [[-hw, b * sn, a * cs], [hw, b * sn, a * cs]], w: 0.32 });
    if (i % 3 === 0) for (const x of [-hw, hw]) S.push({ p: [[x, b * sn, a * cs], [x, b * 0.9 * sn, a * 0.9 * cs]], w: 0.4 });
  }
  // display module on top
  const mx = 0.36, mz = 0.44, y0 = b - 0.02, y1 = b + 0.15, r = 0.1;
  const rrect = (y, ix = mx, iz = mz, rr = r) => {
    const pts = [];
    const corners = [[ix - rr, iz - rr, 0], [-(ix - rr), iz - rr, 1], [-(ix - rr), -(iz - rr), 2], [ix - rr, -(iz - rr), 3]];
    for (const [cx, cz, q] of corners) for (let j = 0; j <= 6; j++) { const an = q * Math.PI / 2 + j / 6 * Math.PI / 2; pts.push([cx + Math.cos(an) * rr, y, cz + Math.sin(an) * rr]); }
    pts.push(pts[0]); return pts;
  };
  S.push({ p: rrect(y1), w: 1.0, mod: 1 }); S.push({ p: rrect(y0), w: 0.6, mod: 1 }); S.push({ p: rrect(y1 + 0.002, mx - 0.06, mz - 0.06, 0.06), w: 0.5, mod: 1 });
  for (const [sx, sz] of [[1, 1], [-1, 1], [-1, -1], [1, -1]]) S.push({ p: [[sx * (mx - 0.03), y0, sz * (mz - 0.03)], [sx * (mx - 0.03), y1, sz * (mz - 0.03)]], w: 0.6, mod: 1 });
  return S;
}
function ringGeom() {
  const S = [];
  const R = 0.62, th = 0.085, hw = 0.17, N = 140;
  const prof = [[-hw, R - th], [-hw, R - 0.012], [-hw + 0.03, R + 0.012], [0, R + 0.02], [hw - 0.03, R + 0.012], [hw, R - 0.012], [hw, R - th], [0, R - th - 0.006]];
  prof.forEach(([x, r], k) => {
    const pts = []; for (let i = 0; i <= N; i++) { const a = i / N * TAU; pts.push([x, r * Math.sin(a), r * Math.cos(a)]); }
    S.push({ p: pts, w: k === 3 ? 0.5 : (k === 7 ? 0.35 : 0.9) });
  });
  for (let i = 0; i < 96; i++) {
    const a = i / 96 * TAU, sn = Math.sin(a), cs = Math.cos(a);
    const pts = prof.concat([prof[0]]).map(([x, r]) => [x, r * sn, r * cs]);
    S.push({ p: pts, w: 0.28 });
  }
  return S;
}
const BAND = bandGeom(), RING = ringGeom();
const RING_NODES = [-0.42, 0, 0.42].map(d => { const a = -Math.PI / 2 + d; return [0, 0.53 * Math.sin(a), 0.53 * Math.cos(a)]; });
// sample points for the particle morph
function samplePts(geom, n, seed) {
  const all = []; geom.forEach(s => { for (let i = 0; i < s.p.length - 1; i++) all.push([s.p[i], s.p[i + 1]]); });
  const out = [];
  for (let i = 0; i < n; i++) { const [a, b] = all[Math.floor(hash(i * 1.37 + seed) * all.length)]; const u = hash(i * 2.11 + seed * 3); out.push([lerp(a[0], b[0], u), lerp(a[1], b[1], u), lerp(a[2], b[2], u)]); }
  return out;
}
const NP = 900, PB = samplePts(BAND, NP, 1), PR = samplePts(RING, NP, 7);

// draw a wireframe: segments bucketed by alpha, additive
function wire(g, geom, o, t, opt = {}) {
  const buckets = Array.from({ length: 8 }, () => []);
  let top = 1e9, bot = -1e9, left = 1e9, right = -1e9;
  const projd = geom.map(s => s.p.map(p => project(p, o)));
  projd.forEach(pp => pp.forEach(([x, y]) => { top = Math.min(top, y); bot = Math.max(bot, y); left = Math.min(left, x); right = Math.max(right, x); }));
  const scanY = opt.scan == null ? 1e9 : lerp(top - 30, bot + 30, opt.scan);
  const scanning = opt.scan != null && opt.scan > 0 && opt.scan < 1;
  const flashes = [];
  geom.forEach((s, si) => {
    const pp = projd[si];
    for (let i = 0; i < pp.length - 1; i++) {
      const [x1, y1, z1] = pp[i], [x2, y2, z2] = pp[i + 1];
      const zm = (z1 + z2) / 2, ym = (y1 + y2) / 2;
      let a = s.w * clamp(0.75 - zm * 0.55, 0.12, 1) * (opt.a ?? 1);
      if (opt.scan != null) {
        a *= clamp((scanY - ym) / 40);
        if (scanning) { const f = Math.exp(-Math.abs(ym - scanY) / 16); if (f > 0.2) flashes.push([x1, y1, x2, y2, f]); }
      }
      if (a <= 0.01) continue;
      buckets[Math.min(7, Math.floor(a * 8))].push([x1, y1, x2, y2]);
    }
  });
  g.save(); g.globalCompositeOperation = 'lighter'; g.lineCap = 'round';
  buckets.forEach((segs, k) => {
    if (!segs.length) return;
    g.strokeStyle = rgba(opt.col || C.cyan, (k + 0.5) / 8); g.lineWidth = opt.lw || 1.6;
    g.beginPath(); segs.forEach(([a, b, c, d]) => { g.moveTo(a, b); g.lineTo(c, d); }); g.stroke();
  });
  if (flashes.length) {
    g.strokeStyle = rgba(C.cyanHi, 0.9); g.lineWidth = 2.4;
    g.beginPath(); flashes.forEach(([a, b, c, d]) => { g.moveTo(a, b); g.lineTo(c, d); }); g.stroke();
  }
  if (scanning) {   // the scan plane
    const gr = g.createLinearGradient(left - 80, 0, right + 80, 0);
    gr.addColorStop(0, rgba(C.cyan, 0)); gr.addColorStop(0.5, rgba(C.cyanHi, 0.95)); gr.addColorStop(1, rgba(C.cyan, 0));
    g.fillStyle = gr; g.fillRect(left - 80, scanY - 1.5, right - left + 160, 3);
    const hz = g.createLinearGradient(0, scanY - 70, 0, scanY);
    hz.addColorStop(0, rgba(C.cyan, 0)); hz.addColorStop(1, rgba(C.cyan, 0.16));
    g.fillStyle = hz; g.fillRect(left - 40, scanY - 70, right - left + 80, 70);
  }
  g.restore();
  return { top, bot, left, right };
}

// ------------------------------------------------------------------ type
const ORB = 'Orbitron, sans-serif', RAJ = 'Rajdhani, sans-serif', MONO = '"JetBrains Mono", monospace';
const GLYPHS = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%&$@<>/\\[]{}=+*';
// decoding title: characters scramble then lock left to right. o: size, w, fam, track, align, col, stagger, out
function decode(g, str, x, y, t, t0, o = {}) {
  const size = o.size || 100, track = o.track ?? size * 0.12;
  g.font = `${o.w || 900} ${size}px ${o.fam || ORB}`; g.letterSpacing = track + 'px';
  g.textBaseline = 'alphabetic'; g.textAlign = 'left';
  const total = g.measureText(str).width - track;
  let x0 = o.align === 'l' ? x : o.align === 'r' ? x - total : x - total / 2;
  const st = o.stagger ?? 0.045, out = o.out || 0;
  const frame = Math.floor(t * 24);
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < str.length; i++) {
    const ch = str[i]; if (ch === ' ') continue;
    const xi = x0 + g.measureText(str.slice(0, i)).width;
    const appear = t0 + i * st * 0.5, lock = t0 + 0.25 + i * st;
    if (t < appear) continue;
    let c = ch, a = 1;
    if (t < lock) { c = GLYPHS[Math.floor(hash(frame * 7.3 + i * 13.1) * GLYPHS.length)]; a = 0.55; }
    if (out > 0) { const q = clamp(out * 1.6 - hash(i * 3.3) * 0.6); if (q >= 1) continue; if (hash(frame + i) < q) c = GLYPHS[Math.floor(hash(frame * 3.1 + i) * GLYPHS.length)]; a *= 1 - q; }
    const flick = t < lock + 0.12 ? 0.6 + 0.4 * hash(frame * 1.7 + i) : 1;
    g.globalAlpha = a * flick * (o.a ?? 1);
    g.shadowColor = rgba(C.cyan, 0.85); g.shadowBlur = size * 0.25;
    g.fillStyle = o.col || C.white;
    g.fillText(c, xi, y);
  }
  g.restore();
  return total;
}
function mono(g, s, x, y, o = {}) {
  g.font = `700 ${o.size || 18}px ${MONO}`; g.letterSpacing = (o.track ?? 2) + 'px';
  g.textAlign = o.align || 'left'; g.textBaseline = 'alphabetic';
  g.fillStyle = o.col || C.dim; g.globalAlpha = o.a ?? 1; g.fillText(s, x, y); g.globalAlpha = 1;
}
function typed(s, t, t0, cps = 40) { return s.slice(0, clamp(Math.floor((t - t0) * cps), 0, s.length)); }

// ------------------------------------------------------------------ background: space, nebula, stars, grid floor
const STARS = Array.from({ length: 700 }, (_, i) => [(hash(i * 1.1) - 0.5) * 8, (hash(i * 2.3) - 0.5) * 5, hash(i * 3.7) * 10 + 0.3, hash(i * 5.9)]);
const neb = mk(480, 270);
(() => {
  const g = neb.g; g.fillStyle = '#000'; g.fillRect(0, 0, 480, 270); g.filter = 'blur(26px)';
  [[150, 110, 120, '#0A4A66', 0.6], [330, 160, 140, '#1B2C6E', 0.5], [260, 70, 90, '#055E5A', 0.45], [90, 210, 80, '#2A1A55', 0.4]].forEach(([x, y, r, c, a]) => {
    g.globalAlpha = a; g.fillStyle = c; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill();
  });
})();
function background(g, t, glow = 1) {
  g.fillStyle = C.bg0; g.fillRect(0, 0, W, H);
  g.save(); g.globalAlpha = 0.55 * glow; g.globalCompositeOperation = 'lighter';
  g.drawImage(neb, -60 + Math.sin(t * 0.05) * 30, -40, W + 120, H + 80); g.restore();
  // stars drift toward camera
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const [x, y, z0, tw] of STARS) {
    const z = ((z0 - t * 0.35) % 10 + 10) % 10 + 0.3;
    const k = 700 / z, sx = W / 2 + x * k, sy = H / 2 + y * k;
    if (sx < 0 || sx > W || sy < 0 || sy > H) continue;
    const a = clamp(1.2 - z / 8) * (0.55 + 0.45 * Math.sin(t * 3 + tw * 40));
    const r = clamp(2.2 - z * 0.18, 0.5, 2.2);
    g.fillStyle = `rgba(200,245,255,${a * 0.8})`; g.fillRect(sx - r / 2, sy - r / 2, r, r);
  }
  g.restore();
  // perspective grid floor
  const hy = H * 0.66;
  g.save(); g.globalCompositeOperation = 'lighter';
  const fade = g.createLinearGradient(0, hy, 0, H);
  fade.addColorStop(0, rgba(C.cyan, 0)); fade.addColorStop(1, rgba(C.cyan, 0.16 * glow));
  g.strokeStyle = fade; g.lineWidth = 1;
  g.beginPath();
  for (let i = -24; i <= 24; i++) { g.moveTo(W / 2 + i * 12, hy); g.lineTo(W / 2 + i * 260, H + 40); }
  for (let k = 0; k < 18; k++) { const z = ((k - t * 1.2) % 18 + 18) % 18 + 1; const y = hy + 420 / z; g.moveTo(0, y); g.lineTo(W, y); }
  g.stroke();
  g.restore();
}

// ------------------------------------------------------------------ HUD pieces
function brackets(g, a) {
  g.save(); g.globalAlpha = a; g.strokeStyle = rgba(C.cyan, 0.7); g.lineWidth = 2;
  const m = 48, L = 56;
  for (const [x, y, sx, sy] of [[m, m, 1, 1], [W - m, m, -1, 1], [m, H - m, 1, -1], [W - m, H - m, -1, -1]]) { g.beginPath(); g.moveTo(x, y + sy * L); g.lineTo(x, y); g.lineTo(x + sx * L, y); g.stroke(); }
  g.restore();
}
function reticle(g, x, y, r, t, a) {
  if (a <= 0.01) return;
  g.save(); g.globalAlpha = a; g.globalCompositeOperation = 'lighter'; g.translate(x, y);
  g.strokeStyle = rgba(C.cyan, 0.35); g.lineWidth = 1.2;
  g.beginPath(); g.arc(0, 0, r, 0, TAU); g.stroke();
  for (let i = 0; i < 72; i++) {
    const an = i / 72 * TAU + t * 0.15, l = i % 6 === 0 ? 16 : 7;
    g.beginPath(); g.moveTo(Math.cos(an) * r, Math.sin(an) * r); g.lineTo(Math.cos(an) * (r + l), Math.sin(an) * (r + l)); g.stroke();
  }
  g.strokeStyle = rgba(C.cyan, 0.8); g.lineWidth = 3;
  g.beginPath(); g.arc(0, 0, r + 28, -t * 0.6, -t * 0.6 + 0.9); g.stroke();
  g.beginPath(); g.arc(0, 0, r + 28, -t * 0.6 + Math.PI, -t * 0.6 + Math.PI + 0.5); g.stroke();
  g.strokeStyle = rgba(C.amber, 0.7); g.lineWidth = 2;
  g.beginPath(); g.arc(0, 0, r - 18, t * 0.9, t * 0.9 + 0.35); g.stroke();
  g.restore();
}
function callout(g, ax, ay, bx, by, label, sub, t, t0, side = 1) {
  const p = P(t, t0, 0.5), q = P(t, t0 + 0.3, 0.6);
  if (p <= 0) return;
  g.save(); g.globalCompositeOperation = 'lighter';
  g.strokeStyle = rgba(C.cyan, 0.8); g.lineWidth = 1.5;
  const mx = lerp(ax, bx, 0.45);
  const pts = [[ax, ay], [mx, by], [bx, by]];
  g.beginPath(); g.moveTo(ax, ay);
  const d1 = Math.hypot(mx - ax, by - ay), d2 = Math.abs(bx - mx), L = (d1 + d2) * p;
  if (L <= d1) g.lineTo(lerp(ax, mx, L / d1), lerp(ay, by, L / d1)); else { g.lineTo(mx, by); g.lineTo(mx + (bx - mx) * ((L - d1) / d2), by); }
  g.stroke();
  g.fillStyle = C.cyanHi; g.beginPath(); g.arc(ax, ay, 4, 0, TAU); g.fill();
  g.strokeStyle = rgba(C.cyan, 0.5); g.beginPath(); g.arc(ax, ay, 9 + 4 * Math.sin(t * 5), 0, TAU); g.stroke();
  if (q > 0) {
    const al = side > 0 ? 'left' : 'right', tx = bx + side * 12;
    g.globalAlpha = q;
    g.font = `600 26px ${RAJ}`; g.letterSpacing = '3px'; g.textAlign = al; g.fillStyle = C.white; g.fillText(typed(label, t, t0 + 0.3, 30), tx, by - 8);
    g.font = `700 14px ${MONO}`; g.letterSpacing = '2px'; g.fillStyle = C.dim; g.fillText(typed(sub, t, t0 + 0.5, 40), tx, by + 18);
  }
  g.restore();
}

// ------------------------------------------------------------------ poses
function bandPose(t) {
  if (t < T_BOTH) return { x: 1190, y: 560, s: lerp(300, 330, inv(T_BAND, T_DISSOLVE, t)), yaw: 0.5 + (t - T_BAND) * 0.55, pitch: -0.45, roll: 0.12 };
  return { x: 620, y: 520, s: 235, yaw: 0.5 + (t - T_BOTH) * 0.55, pitch: -0.45, roll: 0.12 };
}
function ringPose(t) {
  const k = E.io(inv(16.15, 16.95, t));
  return { x: lerp(730, 1300, k), y: lerp(560, 520, k), s: lerp(420, 300, k), yaw: 1.0 + 0.3 * Math.sin(t * 0.55), pitch: 0.55, roll: 0.3, spin: t * 0.9 };
}

// ================================================================== scene layer (blooms)
function scene(g, t) {
  // 00 boot + title
  if (t < T_BAND + 0.2) {
    const lines = [['> OPTICS ......................... ONLINE', 0.35], ['> RENDER CORE .................... ONLINE', 0.85], ['> INCOMING SIGNAL ................ LOCKED', 1.35]];
    const bootOut = P(t, 2.1, 0.4, E.io);
    lines.forEach(([s, t0], i) => { if (t > t0 && bootOut < 1) mono(g, typed(s, t, t0, 70), 200, 460 + i * 40, { size: 22, col: i === 2 ? C.cyan : C.dim, a: 1 - bootOut }); });
    const out = P(t, 4.3, 0.5, E.io);
    if (t > T_TITLE - 0.1 && out < 1) {
      mono(g, typed('// INCOMING TRANSMISSION', t, T_TITLE - 0.1, 50), W / 2, 450, { size: 20, col: C.cyan, align: 'center', track: 6, a: 1 - out });
      decode(g, 'THE ONCOXPRESS', W / 2, 600, t, T_TITLE, { size: 118, out });
    }
  }
  // 01 band
  if (t >= T_BAND && t < T_DISSOLVE + 1.0) {
    const o = bandPose(t);
    const scan = inv(T_BAND, T_BAND + 1.6, t);
    const fade = 1 - P(t, T_DISSOLVE, 0.7, E.io);
    reticle(g, o.x, o.y, 360, t, P(t, 5.4, 0.8) * fade);
    const bb = wire(g, BAND, o, t, { scan: scan < 1 ? scan : null, a: fade });
    if (fade > 0.02) {
      const top = project([0, 0.93, 0], o), side = project([0.3, -0.3, -0.85], o);
      g.save(); g.globalAlpha = fade;
      callout(g, top[0], top[1], o.x + 430, 300, 'DISPLAY MODULE', 'NODE 01 // ACTIVE', t, 6.6, 1);
      callout(g, side[0], side[1], o.x + 440, 830, 'BAND', 'FORM 01 // FLEX', t, 7.1, 1);
      g.restore();
      // module screen pulse
      const sp = P(t, 6.2, 0.6) * fade;
      if (sp > 0) {
        const pts = []; for (let i = 0; i <= 40; i++) { const u = i / 40, zz = lerp(-0.3, 0.3, u); const ph = ((u * 2 - t * 1.1) % 1 + 1) % 1; const h = Math.exp(-Math.pow((ph - 0.5) / 0.04, 2)) * 0.12 - Math.exp(-Math.pow((ph - 0.56) / 0.03, 2)) * 0.05; pts.push(project([h, 0.935, zz], o)); }
        g.save(); g.globalCompositeOperation = 'lighter'; g.strokeStyle = rgba(C.teal, 0.95 * sp); g.lineWidth = 2.5; g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.stroke(); g.restore();
      }
    }
    const tOut = P(t, 9.3, 0.5, E.io);
    if (tOut < 1) {
      mono(g, typed('WEARABLE // 01', t, 5.8, 40), 170, 470, { size: 22, col: C.cyan, track: 6, a: 1 - tOut });
      decode(g, 'BAND', 162, 620, t, 6.0, { size: 170, align: 'l', out: tOut });
      g.save(); g.globalAlpha = (1 - tOut) * P(t, 6.6, 0.6);
      g.font = `600 34px ${RAJ}`; g.letterSpacing = '10px'; g.fillStyle = C.cyanHi; g.textAlign = 'left'; g.fillText('ONCOXPRESS', 172, 690);
      g.restore();
    }
  }
  // particle morph band -> ring
  if (t >= T_DISSOLVE - 0.1 && t < 12.6) {
    const ob = bandPose(T_DISSOLVE), orr = ringPose(11.6);
    g.save(); g.globalCompositeOperation = 'lighter';
    for (let i = 0; i < NP; i++) {
      const d = hash(i * 9.7), t0 = T_DISSOLVE + d * 0.7, u = E.io(clamp((t - t0) / 1.3));
      if (t < t0) continue;
      const a0 = project(PB[i], ob), a1 = project(PR[i], orr);
      const sw = Math.sin(u * Math.PI);
      const ang = hash(i * 4.4) * TAU + u * 3;
      const x = lerp(a0[0], a1[0], u) + Math.cos(ang) * 140 * sw, y = lerp(a0[1], a1[1], u) + Math.sin(ang) * 90 * sw - 60 * sw;
      const al = clamp((t - t0) / 0.15) * (1 - P(t, 11.7 + d * 0.4, 0.5));
      if (al <= 0.01) continue;
      const r = 1.6 + 1.6 * sw;
      g.fillStyle = `rgba(${hash(i) < 0.15 ? '255,179,71' : '120,240,255'},${al})`;
      g.fillRect(x - r / 2, y - r / 2, r, r);
    }
    g.restore();
  }
  // 02 ring
  if (t >= 11.4 && t < T_SOON + 0.5) {
    const o = ringPose(t);
    const scan = inv(11.4, 12.6, t);
    const out = P(t, 21.15, 0.5, E.io);
    const rk = 1 - E.io(inv(16.15, 16.8, t));
    reticle(g, o.x, o.y, 330, t, P(t, 12.2, 0.8) * rk);
    wire(g, RING, o, t, { scan: scan < 1 ? scan : null, a: 1 - out, lw: 1.5 });
    // inner nodes pulse
    const np = P(t, 12.8, 0.6) * (1 - out);
    if (np > 0) {
      g.save(); g.globalCompositeOperation = 'lighter';
      RING_NODES.forEach((p, i) => {
        const [x, y, z] = project(p, o), pul = 0.6 + 0.4 * Math.sin(t * 6 + i * 2);
        const gr = g.createRadialGradient(x, y, 0, x, y, 26); gr.addColorStop(0, rgba(C.teal, 0.9 * np * pul)); gr.addColorStop(1, rgba(C.teal, 0));
        g.fillStyle = gr; g.fillRect(x - 26, y - 26, 52, 52);
      });
      g.restore();
    }
    if (rk > 0.01) {
      const n0 = project(RING_NODES[1], o), outer = project([0, 0.64, 0], o);
      g.save(); g.globalAlpha = rk;
      callout(g, n0[0], n0[1], o.x - 470, 820, 'INNER LAYER', 'NODE 02 // ACTIVE', t, 13.2, -1);
      callout(g, outer[0], outer[1], o.x - 480, 290, 'RING', 'FORM 02 // MINIMAL', t, 13.7, -1);
      g.restore();
      const tOut = P(t, 15.9, 0.5, E.io);
      if (tOut < 1) {
        mono(g, typed('WEARABLE // 02', t, 11.8, 40), W - 170, 470, { size: 22, col: C.cyan, track: 6, align: 'right', a: 1 - tOut });
        decode(g, 'RING', W - 162, 620, t, T_RING, { size: 170, align: 'r', out: tOut });
        g.save(); g.globalAlpha = (1 - tOut) * P(t, 12.6, 0.6);
        g.font = `600 34px ${RAJ}`; g.letterSpacing = '10px'; g.fillStyle = C.cyanHi; g.textAlign = 'right'; g.fillText('ONCOXPRESS', W - 162, 690);
        g.restore();
      }
    }
  }
  // 03 both
  if (t >= T_BOTH && t < T_SOON + 0.5) {
    const o = bandPose(t), out = P(t, 21.15, 0.5, E.io);
    wire(g, BAND, o, t, { scan: t < 17.9 ? inv(T_BOTH, 17.9, t) : null, a: 1 - out });
    // sync link between the devices
    const sp = P(t, 18.4, 0.6) * (1 - out);
    if (sp > 0) {
      const ro = ringPose(t), x0 = o.x + 190, x1 = ro.x - 230, y = 520;
      g.save(); g.globalCompositeOperation = 'lighter';
      g.strokeStyle = rgba(C.cyan, 0.35 * sp); g.setLineDash([6, 10]); g.lineDashOffset = -t * 60; g.lineWidth = 2;
      g.beginPath(); g.moveTo(x0, y); g.lineTo(lerp(x0, x1, sp), y); g.stroke(); g.setLineDash([]);
      for (let k = 0; k < 3; k++) { const u = ((t * 0.7 + k / 3) % 1); const px = lerp(x0, x1, u); const gr = g.createRadialGradient(px, y, 0, px, y, 18); gr.addColorStop(0, rgba(C.cyanHi, sp)); gr.addColorStop(1, rgba(C.cyan, 0)); g.fillStyle = gr; g.fillRect(px - 18, y - 18, 36, 36); }
      mono(g, 'SYNC', (x0 + x1) / 2, y - 22, { size: 16, col: C.cyan, align: 'center', track: 6, a: sp });
      g.restore();
    }
    decode(g, 'THE ONCOXPRESS', W / 2, 880, t, 17.5, { size: 58, out });
    decode(g, 'BAND AND RING', W / 2, 975, t, 18.1, { size: 78, col: C.cyanHi, out });
  }
  // 04 coming soon
  if (t >= T_SOON) {
    const fo = P(t, 25.6, 0.8, E.io);
    decode(g, 'THE ONCOXPRESS BAND AND RING', W / 2, 455, t, T_SOON + 0.35, { size: 34, w: 700, track: 10, stagger: 0.02, col: C.cyanHi, a: 1 - fo });
    decode(g, 'COMING SOON', W / 2, 640, t, T_SOON + 0.1, { size: 156, track: 26, stagger: 0.06, a: 1 - fo });
    // anamorphic streak across the title
    const sk = Math.exp(-Math.max(0, t - T_SOON) / 0.6) * 0.9 + 0.25 * (1 - fo);
    g.save(); g.globalCompositeOperation = 'lighter';
    const gr = g.createLinearGradient(0, 0, W, 0); gr.addColorStop(0, rgba(C.cyan, 0)); gr.addColorStop(0.5, rgba(C.cyanHi, sk)); gr.addColorStop(1, rgba(C.cyan, 0));
    g.fillStyle = gr; g.fillRect(0, 586, W, 3);
    g.fillStyle = rgba(C.cyan, 0.15 * (1 - fo)); g.fillRect(W / 2 - 300 * P(t, T_SOON + 1.2, 1.0), 700, 600 * P(t, T_SOON + 1.2, 1.0), 2);
    g.restore();
  }
}

// ================================================================== HUD layer (no bloom)
function hud(g, t) {
  const a = P(t, 0.2, 0.8) * (1 - P(t, 25.6, 0.8, E.io));
  brackets(g, a);
  mono(g, 'ONCOXPRESS // PROTOTYPE VIEW', 120, 92, { size: 16, a });
  const tc = Math.floor(t * 100);
  mono(g, `T+ 00:${String(Math.floor(t)).padStart(2, '0')}:${String(tc % 100).padStart(2, '0')}`, W - 120, 92, { size: 16, align: 'right', a });
  const status = t < T_BAND ? 'STATUS: INITIALIZING' : t < T_DISSOLVE ? 'SCANNING: BAND' : t < T_BOTH ? (t < 11.4 ? 'RECONFIGURING' : 'SCANNING: RING') : t < T_SOON ? 'SYNC: BAND + RING' : 'STATUS: COMING SOON';
  mono(g, status, 120, H - 84, { size: 16, col: C.cyan, a });
  g.save(); g.globalAlpha = a;
  for (let i = 0; i < 24; i++) { const h = 6 + 22 * Math.abs(Math.sin(t * 3 + i * 0.7) * hash(i + Math.floor(t * 6))); g.fillStyle = rgba(C.cyan, 0.45); g.fillRect(W - 120 - (24 - i) * 9, H - 84 - h, 5, h); }
  g.restore();
}

// ================================================================== glitch, flash, post
function glitchAmt(t) {
  let k = 0;
  for (const c of [T_BAND, T_DISSOLVE + 0.2, T_RING, T_BOTH, T_SOON]) k = Math.max(k, Math.exp(-Math.abs(t - c) / 0.07) * (t >= c - 0.12 ? 1 : 0));
  return k;
}
const scn = mk(), hdl = mk(), small = mk(480, 270), tiny = mk(240, 135), comp = mk();
const scan = mk(W, H);
(() => { const g = scan.g; g.fillStyle = 'rgba(0,0,0,0.12)'; for (let y = 0; y < H; y += 3) g.fillRect(0, y, W, 1); })();
function drawAt(g, t) {
  background(g, t, 1 - 0.6 * P(t, 25.6, 0.8, E.io));
  const S = scn.g; S.clearRect(0, 0, W, H); S.save(); scene(S, t); S.restore();
  // bloom
  small.g.clearRect(0, 0, 480, 270); small.g.filter = 'blur(5px)'; small.g.drawImage(scn, 0, 0, 480, 270); small.g.filter = 'none';
  tiny.g.clearRect(0, 0, 240, 135); tiny.g.filter = 'blur(6px)'; tiny.g.drawImage(scn, 0, 0, 240, 135); tiny.g.filter = 'none';
  g.save(); g.globalCompositeOperation = 'lighter';
  g.drawImage(scn, 0, 0);
  g.globalAlpha = 0.9; g.drawImage(small, 0, 0, W, H);
  g.globalAlpha = 0.7; g.drawImage(tiny, 0, 0, W, H);
  g.restore();
  const Hh = hdl.g; Hh.clearRect(0, 0, W, H); hud(Hh, t);
  g.drawImage(hdl, 0, 0);
  // glitch: chromatic split + slice displacement
  const gk = glitchAmt(t);
  if (gk > 0.05) {
    comp.g.clearRect(0, 0, W, H); comp.g.drawImage(g.canvas, 0, 0);
    g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = 0.5 * gk;
    g.filter = 'none';
    g.drawImage(comp, 14 * gk, 0); g.drawImage(comp, -14 * gk, 0);
    g.restore();
    const fr = Math.floor(t * 60);
    for (let i = 0; i < 9; i++) {
      const y = Math.floor(hash(fr * 3.1 + i) * H), h = 6 + Math.floor(hash(fr + i * 7) * 60), dx = (hash(fr * 1.3 + i * 5) - 0.5) * 140 * gk;
      g.drawImage(comp, 0, y, W, h, dx, y, W, h);
    }
  }
  // flash on the coming-soon hit
  const fl = Math.exp(-Math.max(0, t - T_SOON) / 0.25) * (t >= T_SOON - 0.02 ? 1 : 0);
  if (fl > 0.01) { g.fillStyle = `rgba(190,250,255,${0.55 * fl})`; g.fillRect(0, 0, W, H); }
  g.drawImage(scan, 0, 0);
  const vg = g.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, W * 0.7);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,0.6)');
  g.fillStyle = vg; g.fillRect(0, 0, W, H);
  const fi = 1 - P(t, 0, 0.8, E.io), fo = P(t, 26.0, 0.4, E.io);
  if (fi + fo > 0) { g.fillStyle = `rgba(1,4,9,${Math.max(fi, fo)})`; g.fillRect(0, 0, W, H); }
}

const grain = mk(256, 256);
(() => { const id = grain.g.createImageData(256, 256); for (let i = 0; i < id.data.length; i += 4) { const v = Math.random() < 0.5 ? 0 : 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 7; } grain.g.putImageData(id, 0, 0); })();

const cv = document.getElementById('c');
cv.width = W; cv.height = H;
const out = cv.getContext('2d');
const tmp = mk(), acc = mk();
const CUTS = [T_SOON];
function renderT(t0) {
  if (MB <= 1) { drawAt(out, t0); }
  else {
    for (let s = 0; s < MB; s++) {
      let t = t0 + ((s + 0.5) / MB - 0.5) * SHUTTER / FPS;
      for (const c of CUTS) { if (t0 < c && t >= c) t = c - 1e-4; else if (t0 >= c && t < c) t = c + 1e-4; }
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
  const faces = [500, 700, 900].map(w => new FontFace('Orbitron', `url(fonts/Orbitron-${w}.woff)`, { weight: String(w) }))
    .concat([500, 600].map(w => new FontFace('Rajdhani', `url(fonts/Rajdhani-${w}.woff)`, { weight: String(w) })))
    .concat([new FontFace('JetBrains Mono', 'url(fonts/JetBrainsMono-Bold.ttf)', { weight: '700' })]);
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
    if (e.code === 'ArrowRight' || e.code === 'ArrowLeft') { off = clamp(now() + (e.code === 'ArrowRight' ? 2.4 : -2.4), 0, DUR - 0.01); if (playing) { start = performance.now() - off * 1000; audio.currentTime = off; } }
  });
}
