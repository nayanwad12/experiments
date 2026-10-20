'use strict';
// VIBE EDITING: 20 s logo-animation trailer. Every pixel is a pure function of time t.
// 144 BPM, so 20 s = 48 beats = 12 bars. All timing is written in beats (bt).
//   0-8  cold open (title cards, subliminal style strobe, the breath)
//   8-36 thirteen logo styles, one every 2 beats (the first one gets 4)
//  36-40 accelerating montage, 40-42 slice mosaic, 42-48 hero lockup

const W = 1920, H = 1080;
const BPM = 144, B = 60 / BPM, BEATS = 48, DUR = BEATS * B;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 60);
const MB = +(Q.get('mb') || (RENDER ? 4 : 1));   // motion-blur sub-frames
const SHUTTER = 0.5;                                // 180° shutter

const C = {
  ink: '#07070A', white: '#FFFFFF', lime: '#D4FF3F', pink: '#FF2D95', cyan: '#22E5FF',
  violet: '#7B5CFF', orange: '#FF5A1F', yellow: '#FFE03A', red: '#FF2E4D', blue: '#2B45FF',
};

// ------------------------------------------------------------------ math
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const inv = (a, b, x) => clamp((x - a) / (b - a));
const fract = x => x - Math.floor(x);
const TAU = Math.PI * 2;
const E = {
  inQ: x => x * x,
  outQ: x => 1 - (1 - x) * (1 - x),
  inC: x => x * x * x,
  outC: x => 1 - Math.pow(1 - x, 3),
  ioC: x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2,
  outX: x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x),
  inX: x => x <= 0 ? 0 : Math.pow(2, 10 * x - 10),
  outB: (x, s = 1.70158) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2),
  outBounce: x => {
    const n = 7.5625, d = 2.75;
    if (x < 1 / d) return n * x * x;
    if (x < 2 / d) return n * (x -= 1.5 / d) * x + .75;
    if (x < 2.5 / d) return n * (x -= 2.25 / d) * x + .9375;
    return n * (x -= 2.625 / d) * x + .984375;
  },
};
function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
function noise1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u) * 2 - 1; }
const pulseAt = (bt, at, dec) => bt >= at ? Math.exp(-(bt - at) / dec) : 0;

// ------------------------------------------------------------------ canvas helpers
function mk(w = W, h = H) { const c = document.createElement('canvas'); c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h)); c.g = c.getContext('2d'); return c; }
const FONT = {
  U: ['Unbounded', ''], A: ['Anton', ''], S: ['Instrument Serif', 'italic '], M: ['JetBrains Mono', ''], I: ['Inter Tight', ''],
  MO: ['Montserrat', ''], LG: ['Luckiest Guy', ''], SY: ['Syne', ''], TN: ['Tilt Neon', ''], PS: ['Press Start 2P', ''],
  PF: ['Playfair Display', 'italic '], BG: ['Bungee', ''],
};
function font(g, f, px, ls = 0) { g.font = FONT[f][1] + px + 'px "' + FONT[f][0] + '"'; g.letterSpacing = ls + 'px'; }
function reset(g) {
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'source-over'; g.filter = 'none';
  g.shadowColor = 'transparent'; g.shadowBlur = 0; g.shadowOffsetX = 0; g.shadowOffsetY = 0;
  g.imageSmoothingEnabled = true; g.setLineDash([]); g.lineDashOffset = 0;
}
function bgFill(g, col) { g.fillStyle = col; g.fillRect(-W * 2, -H * 2, W * 5, H * 5); }
function rrect(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function rgba(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${n >> 8 & 255},${n & 255},${a})`; }
function label(g, s, x, y, col, a = .8, px = 16, align = 'left', ls = 2) {
  font(g, 'M', px, ls); g.textAlign = align; g.textBaseline = 'alphabetic';
  g.fillStyle = rgba(col, a); g.fillText(s, x, y);
}
function star4(g, x, y, r, rot = 0) {
  g.beginPath();
  for (let i = 0; i < 8; i++) { const a = rot + i * Math.PI / 4, rr = i % 2 ? r * .2 : r; g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); }
  g.closePath();
}
function glint(g, x, y, r, a, rot = 0, col = '255,255,255') {
  if (a <= 0.003) return;
  g.save(); g.globalCompositeOperation = 'lighter'; g.translate(x, y); g.rotate(rot);
  const gr = g.createRadialGradient(0, 0, 0, 0, 0, r * .7);
  gr.addColorStop(0, `rgba(${col},${a})`); gr.addColorStop(1, `rgba(${col},0)`);
  g.fillStyle = gr; g.beginPath(); g.arc(0, 0, r * .7, 0, TAU); g.fill();
  g.fillStyle = `rgba(${col},${a})`;
  g.beginPath(); g.ellipse(0, 0, r, r * .045, 0, 0, TAU); g.fill();
  g.beginPath(); g.ellipse(0, 0, r * .045, r * .75, 0, 0, TAU); g.fill();
  g.restore();
}
function streak(g, x, y, len, thick, col, a) {
  if (a <= 0.003 || len <= 1) return;
  g.save(); g.globalCompositeOperation = 'lighter';
  let gr = g.createLinearGradient(x - len, 0, x + len, 0);
  gr.addColorStop(0, `rgba(${col},0)`); gr.addColorStop(.5, `rgba(${col},${a})`); gr.addColorStop(1, `rgba(${col},0)`);
  g.fillStyle = gr; g.fillRect(x - len, y - thick / 2, len * 2, thick);
  g.translate(x, y); g.scale(len / 100, thick * 7 / 100);
  gr = g.createRadialGradient(0, 0, 0, 0, 0, 100);
  gr.addColorStop(0, `rgba(${col},${a * .35})`); gr.addColorStop(1, `rgba(${col},0)`);
  g.fillStyle = gr; g.beginPath(); g.arc(0, 0, 100, 0, TAU); g.fill();
  g.restore();
}
function ring(g, lb, x, y, col, maxR = 1400, sy = 1, dur = 1, w0 = 40) {
  const p = inv(0, dur, lb);
  if (p <= 0 || p >= 1) return;
  g.save(); g.strokeStyle = col; g.globalAlpha = (1 - p); g.lineWidth = lerp(w0, 0, E.outQ(p));
  g.beginPath(); g.ellipse(x, y, 20 + E.outX(p) * maxR, (20 + E.outX(p) * maxR) * sy, 0, 0, TAU); g.stroke(); g.restore();
}
function sparks(g, lb, x, y, n, seed, spread = 1400, col = '255,206,150') {
  const ts = lb * B;
  if (ts < 0 || ts > 1.6) return;
  g.save(); g.globalCompositeOperation = 'lighter'; g.lineCap = 'round';
  for (let i = 0; i < n; i++) {
    const h1 = hash(i + seed), h2 = hash(i * 1.7 + seed + 3), h3 = hash(i * 2.9 + seed + 7);
    const life = .45 + h2 * .9;
    if (ts > life) continue;
    const x0 = x + (h1 - .5) * spread, vx = (h2 - .5) * 1400, vy = -400 - h3 * 1100;
    const P = s => [x0 + vx * s, y + vy * s + 1600 * s * s];
    const [px, py] = P(ts), [qx, qy] = P(Math.max(0, ts - .03));
    g.strokeStyle = `rgba(${col},${1 - ts / life})`; g.lineWidth = 1.5 + h3 * 3;
    g.beginPath(); g.moveTo(qx, qy); g.lineTo(px, py); g.stroke();
  }
  g.restore();
}

// ------------------------------------------------------------------ text plates (baked once, animated as images)
const TMP = mk(64, 64);
function meta(c, m) { c.m = m; return c; }
function like(src) { const c = mk(src.width, src.height); c.m = src.m; return c; }
function fitPx(f, s, width) { const g = TMP.g; font(g, f, 200); const m = g.measureText(s); return 200 * width / (m.actualBoundingBoxLeft + m.actualBoundingBoxRight); }
function textMask(f, px, s, o = {}) {
  const ls = o.ls || 0, pad = o.pad ?? 80;
  const t = TMP.g; font(t, f, px, ls);
  const m = t.measureText(s);
  const asc = Math.ceil(m.actualBoundingBoxAscent), desc = Math.ceil(m.actualBoundingBoxDescent);
  const L = Math.ceil(m.actualBoundingBoxLeft), R = Math.ceil(m.actualBoundingBoxRight);
  const c = mk(L + R + pad * 2, asc + desc + pad * 2);
  font(c.g, f, px, ls); c.g.textBaseline = 'alphabetic'; c.g.fillStyle = '#fff';
  c.g.fillText(s, pad + L, pad + asc);
  return meta(c, { f, px, s, ls, pad, asc, desc, tw: L + R, th: asc + desc, bx: pad + L, by: pad + asc, top: pad, bot: pad + asc + desc });
}
function stackMask(f, lines, widths, gap, pad = 80) {
  const ms = lines.map((s, i) => textMask(f, fitPx(f, s, widths[i]), s, { pad: 0 }));
  const w = Math.max(...ms.map(m => m.width)) + pad * 2, h = ms.reduce((a, m) => a + m.height, 0) + gap * (ms.length - 1) + pad * 2;
  const c = mk(w, h); let y = pad;
  for (const m of ms) { c.g.drawImage(m, (w - m.width) / 2, y); y += m.height + gap; }
  return meta(c, { pad, tw: w - pad * 2, th: h - pad * 2, top: pad, bot: h - pad, lines: ms });
}
// one plate per glyph; dx = glyph centre relative to the word's visual centre
function letterPlates(f, px, s, o = {}) {
  const ls = o.ls || 0, pad = o.pad ?? 80;
  const t = TMP.g; font(t, f, px, ls);
  const full = t.measureText(s);
  const asc = Math.ceil(full.actualBoundingBoxAscent), desc = Math.ceil(full.actualBoundingBoxDescent);
  const cx0 = (full.actualBoundingBoxRight - full.actualBoundingBoxLeft) / 2;
  const chars = [...s], out = [];
  let k = 0;
  chars.forEach((ch, i) => {
    if (ch === ' ') return;
    const x0 = t.measureText(chars.slice(0, i).join('')).width;
    const m = t.measureText(ch);
    const l = Math.ceil(m.actualBoundingBoxLeft), r = Math.ceil(m.actualBoundingBoxRight);
    const c = mk(l + r + pad * 2, asc + desc + pad * 2);
    font(c.g, f, px, ls); c.g.fillStyle = '#fff'; c.g.fillText(ch, pad + l, pad + asc);
    meta(c, { f, px, s: ch, pad, asc, desc, tw: l + r, th: asc + desc, bx: pad + l, by: pad + asc, top: pad, bot: pad + asc + desc });
    out.push({ ch, k: k++, dx: x0 + (r - l) / 2 - cx0, w: l + r, mask: c });
  });
  out.tw = full.actualBoundingBoxRight + full.actualBoundingBoxLeft; out.asc = asc; out.desc = desc; out.th = asc + desc;
  return out;
}
function tint(mask, fill) {
  const c = like(mask), g = c.g;
  g.drawImage(mask, 0, 0); g.globalCompositeOperation = 'source-in';
  g.fillStyle = typeof fill === 'function' ? fill(g, mask) : fill; g.fillRect(0, 0, c.width, c.height);
  return c;
}
const vgrad = (stops, y0, y1) => (g, mask) => {
  const gr = g.createLinearGradient(0, y0 ?? mask.m.top, 0, y1 ?? mask.m.bot);
  stops.forEach(([o, c]) => gr.addColorStop(o, c)); return gr;
};
function blurred(src, r) { const c = like(src); c.g.filter = `blur(${r}px)`; c.g.drawImage(src, 0, 0); c.g.filter = 'none'; return c; }
function compose(base, ...layers) {
  const c = like(base); c.g.drawImage(base, 0, 0);
  for (const [l, a = 1, op = 'source-over', dx = 0, dy = 0] of layers) { c.g.globalAlpha = a; c.g.globalCompositeOperation = op; c.g.drawImage(l, dx, dy); }
  c.g.globalAlpha = 1; c.g.globalCompositeOperation = 'source-over';
  return c;
}
// soft inner edge light (top-left) and shade (bottom-right), clipped to the glyphs
function bevel(mask, o = {}) {
  const d = o.d ?? 5, bl = o.blur ?? 4, out = like(mask), tmp = like(mask);
  for (const [s, col, a] of [[1, o.hi ?? '#fff', o.hiA ?? .85], [-1, o.lo ?? '#000', o.loA ?? .5]]) {
    const t = tmp.g; reset(t); t.clearRect(0, 0, tmp.width, tmp.height);
    t.drawImage(mask, 0, 0); t.globalCompositeOperation = 'source-in'; t.fillStyle = col; t.fillRect(0, 0, tmp.width, tmp.height);
    t.globalCompositeOperation = 'destination-out'; t.filter = `blur(${bl}px)`; t.drawImage(mask, s * d, s * d); t.filter = 'none';
    out.g.globalAlpha = a; out.g.drawImage(tmp, 0, 0);
  }
  out.g.globalAlpha = 1;
  return out;
}
function flipFade(plate, a0, frac) {
  const c = like(plate), g = c.g;
  g.translate(0, c.height); g.scale(1, -1); g.drawImage(plate, 0, 0); g.setTransform(1, 0, 0, 1, 0, 0);
  const y0 = c.height - plate.m.bot, gr = g.createLinearGradient(0, y0, 0, y0 + plate.m.th * frac);
  gr.addColorStop(0, `rgba(0,0,0,${a0})`); gr.addColorStop(1, 'rgba(0,0,0,0)');
  g.globalCompositeOperation = 'destination-in'; g.fillStyle = gr; g.fillRect(0, 0, c.width, c.height);
  return c;
}
function blit(g, c, x, y, s = 1, a = 1, rot = 0, sx = 1, sy = 1) {
  if (a <= 0.002 || s <= 0) return;
  g.save(); g.globalAlpha *= Math.min(1, a); g.translate(x, y); if (rot) g.rotate(rot); g.scale(s * sx, s * sy);
  g.drawImage(c, -c.width / 2, -c.height / 2); g.restore();
}
const L1 = mk(2200, 1400), L2 = mk();
// a diagonal light band raking across the glyphs of `mask` (drawn at X0,Y0)
function sweepOver(g, mask, X0, Y0, p, a = 1, w = 230, col = '255,255,255') {
  if (p <= 0 || p >= 1) return;
  const T = L1.g, mw = mask.width, mh = mask.height;
  reset(T); T.clearRect(0, 0, mw, mh);
  T.drawImage(mask, 0, 0); T.globalCompositeOperation = 'source-in';
  const x = lerp(-w * 2, mw + w * 2, p);
  const gr = T.createLinearGradient(x - w, 0, x + w, mh * .5);
  gr.addColorStop(0, `rgba(${col},0)`); gr.addColorStop(.5, `rgba(${col},${a})`); gr.addColorStop(1, `rgba(${col},0)`);
  T.fillStyle = gr; T.fillRect(0, 0, mw, mh);
  g.save(); g.globalCompositeOperation = 'lighter'; g.drawImage(L1, 0, 0, mw, mh, X0, Y0, mw, mh); g.restore();
}

// ------------------------------------------------------------------ WebGL: background shaders + post
const VS = `#version 300 es
in vec2 p; out vec2 uv; void main(){ uv = p*.5+.5; gl_Position = vec4(p,0.,1.); }`;

const BG_FS = `#version 300 es
precision highp float;
uniform vec2 res; uniform float time, dim, hue, pulse, mode; uniform vec3 balls[7];
in vec2 uv; out vec4 o;
vec2 g2(vec2 p){ p = vec2(dot(p,vec2(127.1,311.7)), dot(p,vec2(269.5,183.3))); return -1.0+2.0*fract(sin(p)*43758.5453123); }
float noise(vec2 p){ vec2 i=floor(p), f=fract(p); vec2 u=f*f*(3.0-2.0*f);
  return mix(mix(dot(g2(i),f), dot(g2(i+vec2(1,0)),f-vec2(1,0)),u.x), mix(dot(g2(i+vec2(0,1)),f-vec2(0,1)), dot(g2(i+vec2(1,1)),f-vec2(1,1)),u.x),u.y); }
float fbm(vec2 p){ float f=0.0, a=0.5; mat2 m=mat2(1.6,1.2,-1.2,1.6); for(int i=0;i<4;i++){ f+=a*noise(p); p=m*p; a*=0.5; } return f; }
float field(vec2 p){
  vec2 q = vec2(fbm(p + vec2(0.0, time*0.13)), fbm(p + vec2(5.2,1.3) - time*0.09));
  vec2 r = vec2(fbm(p + 2.6*q + vec2(1.7,9.2) + time*0.11), fbm(p + 2.6*q + vec2(8.3,2.8)));
  return fbm(p + 2.4*r + pulse*0.25);
}
vec3 grad(float x){
  x = fract(x) * 5.0;
  vec3 c0=vec3(0.06,0.09,0.45), c1=vec3(0.48,0.36,1.0), c2=vec3(1.0,0.37,0.66), c3=vec3(1.0,0.45,0.18), c4=vec3(0.83,1.0,0.25);
  if (x<1.0) return mix(c0,c1,smoothstep(0.,1.,x));
  if (x<2.0) return mix(c1,c2,smoothstep(0.,1.,x-1.0));
  if (x<3.0) return mix(c2,c3,smoothstep(0.,1.,x-2.0));
  if (x<4.0) return mix(c3,c4,smoothstep(0.,1.,x-3.0));
  return mix(c4,c0,smoothstep(0.,1.,x-4.0));
}
void main(){
  vec2 fc = vec2(gl_FragCoord.x, res.y - gl_FragCoord.y);
  vec3 L = normalize(vec3(-0.45, -0.55, 0.75));
  vec3 col;
  if (mode < 0.5) {
    vec2 p = (fc/res.y - vec2(0.5*res.x/res.y, 0.5)) * 2.4;
    float e = 0.012;
    float h = field(p), hx = field(p+vec2(e,0.)), hy = field(p+vec2(0.,e));
    vec3 n = normalize(vec3((h-hx)/e*0.32, (h-hy)/e*0.32, 1.0));
    float diff = max(dot(n,L),0.0);
    float spec = pow(max(dot(reflect(-L,n), vec3(0,0,1)),0.0), 28.0);
    float fres = pow(1.0-n.z, 1.6);
    col = grad(h*1.5 + n.x*0.22 + n.y*0.12 + time*0.035 + hue) * (0.28 + 0.85*diff) + spec*0.85 + fres*0.5*grad(h+0.45+hue);
  } else {
    vec2 pp = fc/res.y;
    float f = 0.0; vec2 gr = vec2(0.0);
    for (int i=0;i<7;i++){ vec2 d = pp - balls[i].xy; float r2 = balls[i].z*balls[i].z; float dd = dot(d,d)+1e-4; f += r2/dd; gr += -2.0*r2*d/(dd*dd); }
    float w = fwidth(f)*1.2;
    float inside = smoothstep(1.0-w, 1.0+w, f);
    vec2 nxy = -normalize(gr+1e-6) * (1.0 - smoothstep(1.0, 3.2, f));
    vec3 n = normalize(vec3(nxy*0.95, sqrt(max(0.05, 1.0-dot(nxy,nxy)))));
    float diff = max(dot(n,L),0.0);
    float spec = pow(max(dot(reflect(-L,n), vec3(0,0,1)),0.0), 40.0);
    float tex = fbm(pp*3.0 + time*0.2);
    vec3 surf = grad(n.x*0.55 + n.y*0.35 + tex*0.6 + time*0.05 + hue) * (0.25 + 0.9*diff) + spec*1.1 + pow(1.0-n.z,2.0)*0.6;
    vec3 glow = grad(0.15+hue) * clamp(f*0.12, 0.0, 0.5) * 0.35;
    col = mix(glow, surf, inside);
  }
  o = vec4(col*dim, 1.0);
}`;

const POST_FS = `#version 300 es
precision highp float;
uniform sampler2D tex; uniform vec2 res; uniform float ab, glitch, grain, vig, bloom, flash, invert, seed;
in vec2 uv; out vec4 o;
float h1(float n){ return fract(sin(n)*43758.5453); }
float h2(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)))*43758.5453); }
void main(){
  vec2 p = uv;
  if (glitch > 0.0) {
    float rows = mix(10.0, 44.0, h1(seed*1.37));
    float row = floor(p.y*rows);
    if (h2(vec2(row, seed)) < glitch*0.55) p.x += (h2(vec2(row+7.0, seed))-0.5)*0.22*glitch;
    vec2 blk = floor(p*vec2(24.0, 13.5));
    if (h2(blk+seed*3.1) < glitch*0.07) p += (vec2(h2(blk*1.7+seed), h2(blk*2.3+seed))-0.5)*0.08;
  }
  vec2 d = p - 0.5;
  vec2 da = d*vec2(1.7778,1.0);
  float r2 = dot(da,da);
  float k = ab*(0.0025 + 0.011*r2) + glitch*0.01;
  vec3 c;
  c.r = textureLod(tex, p + d*k + vec2(glitch*0.006,0.), 0.).r;
  c.g = textureLod(tex, p, 0.).g;
  c.b = textureLod(tex, p - d*k - vec2(glitch*0.006,0.), 0.).b;
  vec3 bl = vec3(0.0);
  for (int i=0;i<8;i++){
    float a = float(i)*0.785398 + 0.39;
    vec2 o2 = vec2(cos(a), sin(a));
    bl += textureLod(tex, p + o2*vec2(0.0055,0.0098), 3.5).rgb;
    bl += textureLod(tex, p + o2*vec2(0.016,0.028), 5.0).rgb;
  }
  bl /= 16.0;
  c += bloom * max(bl - 0.42, 0.0) * 1.9;
  if (invert > 0.5) c = 1.0 - c;
  c = mix(c, vec3(1.0), flash);
  c *= 1.0 - vig*smoothstep(0.45, 1.3, length(d*vec2(1.3,1.0))*1.6);
  c += (h2(uv*res + fract(seed*7.13)*97.0) - 0.5)*grain;
  o = vec4(c, 1.0);
}`;

function glProgram(gl, fs) {
  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
  const p = gl.createProgram();
  gl.attachShader(p, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(p, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const U = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) { const info = gl.getActiveUniform(p, i); const nm = info.name.replace('[0]', ''); U[nm] = gl.getUniformLocation(p, nm); }
  return { p, U };
}

const OUT = document.getElementById('out');
const GL = OUT.getContext('webgl2', { preserveDrawingBuffer: true, antialias: false });
const POST = glProgram(GL, POST_FS);
const TEX = GL.createTexture();
GL.bindTexture(GL.TEXTURE_2D, TEX);
GL.texParameteri(GL.TEXTURE_2D, GL.TEXTURE_MIN_FILTER, GL.LINEAR_MIPMAP_LINEAR);
GL.texParameteri(GL.TEXTURE_2D, GL.TEXTURE_MAG_FILTER, GL.LINEAR);
GL.texParameteri(GL.TEXTURE_2D, GL.TEXTURE_WRAP_S, GL.CLAMP_TO_EDGE);
GL.texParameteri(GL.TEXTURE_2D, GL.TEXTURE_WRAP_T, GL.CLAMP_TO_EDGE);
GL.pixelStorei(GL.UNPACK_FLIP_Y_WEBGL, true);

const BGCANVAS = document.createElement('canvas'); BGCANVAS.width = 960; BGCANVAS.height = 540;
const BGL = BGCANVAS.getContext('webgl2', { preserveDrawingBuffer: true, antialias: false });
const BGP = glProgram(BGL, BG_FS);
let FRAME_KEY = 0;
const shaderCache = {};
// Background shader layer, rendered once per output frame (not per blur sub-frame) at half res.
function shader(name, u) {
  const key = FRAME_KEY + '|' + name;
  if (shaderCache[name] && shaderCache[name].key === key) return shaderCache[name].c;
  const gl = BGL; gl.useProgram(BGP.p); gl.viewport(0, 0, 960, 540);
  gl.uniform2f(BGP.U.res, 960, 540);
  gl.uniform1f(BGP.U.time, u.time); gl.uniform1f(BGP.U.dim, u.dim ?? 1); gl.uniform1f(BGP.U.hue, u.hue ?? 0);
  gl.uniform1f(BGP.U.pulse, u.pulse ?? 0); gl.uniform1f(BGP.U.mode, u.mode ?? 0);
  gl.uniform3fv(BGP.U.balls, new Float32Array(u.balls || new Array(21).fill(-5)));
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  const c = (shaderCache[name] && shaderCache[name].c) || mk(960, 540);
  c.g.clearRect(0, 0, 960, 540); c.g.drawImage(BGCANVAS, 0, 0);
  shaderCache[name] = { key, c };
  return c;
}


// ================================================================== the 13 styles
// Each style is fn(g, lb, t): lb = local beats since the style's cut, t = absolute seconds.
// Text is baked into plates in init(); scenes only move, mask and light them.
const PL = {};

// ------------------------------------------------------------------ 01 LIQUID CHROME
function initChrome() {
  const m = textMask('U', fitPx('U', 'VIBE EDITING', 1640), 'VIBE EDITING', { pad: 60 });
  const face = compose(
    tint(m, vgrad([[0, '#fbfdff'], [.2, '#c9d3e1'], [.45, '#4d5768'], [.5, '#121620'], [.55, '#93a3ba'], [.72, '#eef4fb'], [.88, '#8d9aae'], [1, '#ffffff']])),
    [bevel(m, { d: 3, blur: 2, hiA: .95, lo: '#05070b', loA: .6 })]);
  const side = tint(m, vgrad([[0, '#454d5b'], [1, '#090b0f']]));
  const plate = like(m);
  for (let i = 24; i >= 1; i--) plate.g.drawImage(side, 0, i * 1.15);
  plate.g.globalAlpha = .55; plate.g.drawImage(tint(m, '#ffffff'), 0, 1.6); plate.g.globalAlpha = 1;
  plate.g.drawImage(face, 0, 0);
  PL.chrome = { m, plate, reflect: flipFade(plate, .32, .8) };
}
function sChrome(g, lb, t) {
  const P = PL.chrome, m = P.m;
  bgFill(g, '#020203');
  const cy = H / 2 - 40;
  const rg = g.createRadialGradient(W / 2, cy - 80, 0, W / 2, cy, 1150);
  rg.addColorStop(0, '#2c313c'); rg.addColorStop(.5, '#0d0f14'); rg.addColorStop(1, '#020203');
  g.fillStyle = rg; g.fillRect(0, 0, W, H);
  const fy = cy + m.m.th / 2 + 34;
  const fg = g.createLinearGradient(0, fy, 0, H);
  fg.addColorStop(0, 'rgba(140,160,190,.12)'); fg.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = fg; g.fillRect(0, fy, W, H - fy);
  streak(g, W / 2, cy, 1100 + 300 * pulseAt(lb, 0, .6), 3, '170,200,255', .5 + .5 * pulseAt(lb, 0, .5));
  const land = E.outX(inv(0, .55, lb));
  const s = (1 + .3 * (1 - land)) * (1 + .055 * E.ioC(inv(.4, 4, lb)));
  g.save(); g.translate(W / 2, cy); g.scale(s, s); g.translate(-W / 2, -cy);
  const X0 = W / 2 - m.width / 2, Y0 = cy - m.height / 2;
  g.globalAlpha = land; g.drawImage(P.reflect, X0, Y0 + 2 * m.m.bot - m.height + 36);
  g.globalAlpha = clamp(lb / .05); g.drawImage(P.plate, X0, Y0); g.globalAlpha = 1;
  sweepOver(g, m, X0, Y0, inv(.12, .85, lb), 1);
  sweepOver(g, m, X0, Y0, inv(2.1, 3.0, lb), .8, 160);
  g.restore();
  ring(g, lb, W / 2, fy, 'rgba(200,220,255,.9)', 1500, .12, 1.2, 30);
  sparks(g, lb, W / 2, fy - 20, 90, 3);
  sparks(g, lb - 2, W / 2, fy - 20, 40, 9, 900);
  const gx = X0 + m.m.bx + 30, gy = Y0 + m.m.by - m.m.asc + 10;
  glint(g, gx, gy, 170, pulseAt(lb, 2, .35) * (lb > 2), lb * .8);
  glint(g, X0 + m.m.bx + m.m.tw - 40, Y0 + m.m.by - 20, 120, pulseAt(lb, .6, .3) * (lb > .6), -lb);
}

// ------------------------------------------------------------------ 02 GLASSMORPHISM
const GB = mk(480, 270), GBB = mk(480, 270);
function glassBG(t) {
  const g = GB.g; reset(g);
  g.fillStyle = '#0a0b24'; g.fillRect(0, 0, 480, 270);
  g.globalCompositeOperation = 'lighter';
  const cols = ['255,45,149', '123,92,255', '34,229,255', '255,138,61', '43,69,255', '212,255,63'];
  for (let k = 0; k < 6; k++) {
    const x = 240 + 175 * Math.sin(t * 1.1 + k * 1.9), y = 135 + 100 * Math.cos(t * .9 + k * 2.6), r = 120 + 40 * Math.sin(t * .7 + k);
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, `rgba(${cols[k]},${k === 5 ? .45 : .85})`); gr.addColorStop(1, `rgba(${cols[k]},0)`);
    g.fillStyle = gr; g.fillRect(0, 0, 480, 270);
  }
  const b = GBB.g; reset(b); b.fillStyle = '#0a0b24'; b.fillRect(0, 0, 480, 270);
  b.filter = 'blur(13px)'; b.drawImage(GB, 0, 0); b.filter = 'none';
}
function initGlass() {
  const L = letterPlates('SY', fitPx('SY', 'VIBE EDITING', 1240), 'VIBE EDITING', { pad: 50 });
  for (const l of L) {
    l.face = compose(tint(l.mask, vgrad([[0, '#ffffff'], [.6, '#efeaff'], [1, 'rgba(255,255,255,.72)']])),
      [bevel(l.mask, { d: 3, blur: 3, hiA: .9, lo: '#5b3cff', loA: .35 })]);
    l.shadow = blurred(tint(l.mask, 'rgba(15,6,60,.55)'), 16);
  }
  PL.glass = { L };
}
function glassOrb(g, x, y, r) {
  g.save(); g.beginPath(); g.arc(x, y, r, 0, TAU); g.clip();
  g.drawImage(GBB, 0, 0, W, H);
  g.fillStyle = 'rgba(255,255,255,.12)'; g.fillRect(x - r, y - r, r * 2, r * 2);
  const gr = g.createRadialGradient(x - r * .4, y - r * .45, 0, x - r * .4, y - r * .45, r * .9);
  gr.addColorStop(0, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2);
  g.restore();
  const sg = g.createLinearGradient(x - r, y - r, x + r, y + r);
  sg.addColorStop(0, 'rgba(255,255,255,.85)'); sg.addColorStop(.5, 'rgba(255,255,255,.08)'); sg.addColorStop(1, 'rgba(255,255,255,.4)');
  g.strokeStyle = sg; g.lineWidth = 2; g.beginPath(); g.arc(x, y, r, 0, TAU); g.stroke();
}
function sGlass(g, lb, t) {
  const P = PL.glass;
  glassBG(t * .9);
  g.drawImage(GB, 0, 0, W, H);
  const p = E.outX(inv(0, .5, lb));
  const cw = 1500, ch = 500, cx = W / 2, cy = H / 2 - 10 + (1 - p) * 200, x = cx - cw / 2, y = cy - ch / 2;
  g.save(); g.globalAlpha = p;
  g.translate(cx, cy); const sc = .86 + .14 * p; g.scale(sc, sc); g.translate(-cx, -cy);
  g.save(); g.shadowColor = 'rgba(4,3,24,.6)'; g.shadowBlur = 90; g.shadowOffsetY = 44;
  rrect(g, x, y, cw, ch, 56); g.fillStyle = '#16153a'; g.fill(); g.restore();
  g.save(); rrect(g, x, y, cw, ch, 56); g.clip();
  g.drawImage(GBB, 0, 0, W, H);
  g.fillStyle = 'rgba(255,255,255,.09)'; g.fillRect(x, y, cw, ch);
  let gr = g.createLinearGradient(0, y, 0, y + ch);
  gr.addColorStop(0, 'rgba(255,255,255,.24)'); gr.addColorStop(.42, 'rgba(255,255,255,.02)'); gr.addColorStop(1, 'rgba(255,255,255,.07)');
  g.fillStyle = gr; g.fillRect(x, y, cw, ch);
  const sx = lerp(x - 600, x + cw + 600, inv(.2, 1.6, lb));
  gr = g.createLinearGradient(sx - 160, y, sx + 160, y + ch * .3);
  gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(.5, 'rgba(255,255,255,.16)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(x, y, cw, ch);
  g.restore();
  rrect(g, x, y, cw, ch, 56);
  gr = g.createLinearGradient(x, y, x + cw, y + ch);
  gr.addColorStop(0, 'rgba(255,255,255,.8)'); gr.addColorStop(.5, 'rgba(255,255,255,.07)'); gr.addColorStop(1, 'rgba(255,255,255,.42)');
  g.strokeStyle = gr; g.lineWidth = 2.5; g.stroke();
  ['#ff5f57', '#febc2e', '#28c840'].forEach((c, i) => { g.fillStyle = c; g.beginPath(); g.arc(x + 46 + i * 30, y + 44, 9, 0, TAU); g.fill(); });
  label(g, 'vibe-editing.studio', cx, y + 51, '#ffffff', .55, 17, 'center', 1);
  g.fillStyle = 'rgba(255,255,255,.14)'; g.fillRect(x, y + 86, cw, 1.5);
  for (const l of P.L) {
    const d = .12 + l.k * .032, q = E.outX(inv(d, d + .5, lb));
    blit(g, l.shadow, cx + l.dx, cy + 40 + 16 + (1 - q) * 90, 1, q);
    blit(g, l.face, cx + l.dx, cy + 40 + (1 - q) * 90, .9 + .1 * q, q);
  }
  g.restore();
  const bob = k => Math.sin(t * 2.2 + k * 2) * 14;
  const oa = E.outC(inv(.25, .7, lb));
  g.save(); g.globalAlpha = oa;
  glassOrb(g, x + cw - 40, y - 20 + bob(0) + (1 - oa) * 80, 82);
  glassOrb(g, x + 30, y + ch + 10 + bob(1) + (1 - oa) * 120, 58);
  glassOrb(g, x + cw * .63, y + ch + 46 + bob(2) + (1 - oa) * 160, 34);
  g.restore();
}

// ------------------------------------------------------------------ 03 NEUMORPHISM
const NEU = '#E3E8EF';
function initNeu() {
  const m1 = textMask('MO', fitPx('MO', 'VIBE', 760), 'VIBE', { pad: 80 });
  const face = tint(m1, vgrad([[0, '#eef2f7'], [1, '#d9dfe8']]));
  const raised = like(m1), r = raised.g;
  for (const [col, s] of [['rgba(255,255,255,.98)', -1], ['rgba(148,163,188,.8)', 1]]) {
    r.shadowColor = col; r.shadowBlur = 34; r.shadowOffsetX = 16 * s; r.shadowOffsetY = 16 * s; r.drawImage(face, 0, 0);
  }
  reset(r); r.drawImage(face, 0, 0); r.drawImage(bevel(m1, { d: 3, blur: 3, hiA: .7, lo: '#9aa8bd', loA: .35 }), 0, 0);
  const m2 = textMask('MO', fitPx('MO', 'EDITING', 1180), 'EDITING', { pad: 60 });
  const sheet = like(m2);
  sheet.g.fillStyle = NEU; sheet.g.fillRect(0, 0, sheet.width, sheet.height);
  sheet.g.globalCompositeOperation = 'destination-out'; sheet.g.drawImage(m2, 0, 0);
  const inset = like(m2), n = inset.g;
  n.drawImage(tint(m2, '#dbe1ea'), 0, 0);
  for (const [col, s] of [['rgba(140,155,182,.95)', 1], ['rgba(255,255,255,1)', -1]]) {
    n.save(); n.shadowColor = col; n.shadowBlur = 16; n.shadowOffsetX = 9 * s; n.shadowOffsetY = 9 * s; n.drawImage(sheet, 0, 0); n.restore();
  }
  n.globalCompositeOperation = 'destination-in'; n.drawImage(m2, 0, 0);
  PL.neu = { raised, inset };
}
function neuRaised(g, add, d = 10, blur = 22, fill = NEU) {
  g.save();
  for (const [col, s] of [['rgba(255,255,255,.98)', -1], ['rgba(148,163,188,.8)', 1]]) {
    g.shadowColor = col; g.shadowBlur = blur; g.shadowOffsetX = d * s; g.shadowOffsetY = d * s;
    g.beginPath(); add(g); g.fillStyle = fill; g.fill();
  }
  g.restore();
}
// inner shadows: a sheet with the shape punched out casts its shadows into the hole
// (built offscreen: clip + blurred shadow + even-odd fill wipes the canvas in Chromium)
const NT = mk(700, 300);
function neuInset(g, add, box, d = 6, blur = 10, fill = '#DCE2EA') {
  const [bx, by, bw, bh] = box, m = 40, w = bw + m * 2, h = bh + m * 2;
  const t = NT.g; reset(t); t.clearRect(0, 0, NT.width, NT.height);
  t.fillStyle = NEU; t.fillRect(0, 0, w, h);
  t.globalCompositeOperation = 'destination-out'; t.translate(m - bx, m - by); t.beginPath(); add(t); t.fill();
  g.save(); g.beginPath(); add(g); g.clip(); g.fillStyle = fill; g.fill();
  for (const [col, s] of [['rgba(140,155,182,.9)', 1], ['rgba(255,255,255,1)', -1]]) {
    g.shadowColor = col; g.shadowBlur = blur; g.shadowOffsetX = d * s; g.shadowOffsetY = d * s;
    g.drawImage(NT, 0, 0, w, h, bx - m, by - m, w, h);
  }
  g.restore();
}
function sNeu(g, lb, t) {
  const P = PL.neu;
  bgFill(g, NEU);
  const rg = g.createRadialGradient(W * .3, H * .2, 0, W * .3, H * .2, 1400);
  rg.addColorStop(0, 'rgba(255,255,255,.55)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rg; g.fillRect(0, 0, W, H);
  const p1 = E.outC(inv(0, .45, lb)), p2 = E.outC(inv(.12, .6, lb));
  blit(g, P.raised, W / 2, H / 2 - 175, 1.04 - .04 * p1, p1);
  blit(g, P.inset, W / 2, H / 2 + 90, 1, p2);
  const uy = H / 2 + 300, ua = E.outC(inv(.25, .7, lb));
  g.save(); g.globalAlpha = ua; g.translate(0, (1 - ua) * 40);
  const press = 1 - .5 * pulseAt(lb, 1, .25) * (lb >= 1);
  neuRaised(g, c => c.arc(W / 2 - 330, uy, 52, 0, TAU), 10 * press, 22);
  g.fillStyle = '#6C63FF'; g.beginPath(); g.moveTo(W / 2 - 342, uy - 20); g.lineTo(W / 2 - 312, uy); g.lineTo(W / 2 - 342, uy + 20); g.closePath(); g.fill();
  neuInset(g, c => c.roundRect(W / 2 - 230, uy - 13, 360, 26, 13), [W / 2 - 230, uy - 13, 360, 26], 5, 8);
  const prog = E.ioC(inv(.3, 1.8, lb));
  const sg = g.createLinearGradient(W / 2 - 230, 0, W / 2 + 130, 0); sg.addColorStop(0, '#6C63FF'); sg.addColorStop(1, '#B18CFF');
  g.fillStyle = sg; rrect(g, W / 2 - 226, uy - 9, Math.max(18, 352 * prog), 18, 9); g.fill();
  neuRaised(g, c => c.arc(W / 2 - 226 + 352 * prog, uy, 22, 0, TAU), 6, 14);
  const on = E.outB(inv(1, 1.25, lb));
  neuInset(g, c => c.roundRect(W / 2 + 200, uy - 31, 132, 62, 31), [W / 2 + 200, uy - 31, 132, 62], 5, 9);
  g.fillStyle = rgba('#6C63FF', .9 * clamp(on)); rrect(g, W / 2 + 205, uy - 26, 122, 52, 26); g.fill();
  neuRaised(g, c => c.arc(W / 2 + 231 + 70 * on, uy, 22, 0, TAU), 5, 12);
  g.restore();
}

// ------------------------------------------------------------------ 04 NEON NOIR
function initNeon() {
  const L = letterPlates('TN', fitPx('TN', 'VIBE EDITING', 1520), 'VIBE EDITING', { pad: 130 });
  for (const l of L) {
    const col = l.k < 4 ? C.pink : C.cyan, light = l.k < 4 ? '#ffc2e2' : '#c4f8ff';
    const glowBig = blurred(tint(l.mask, col), 40), glowMid = blurred(tint(l.mask, col), 11);
    const core = tint(l.mask, '#ffffff'); core.g.globalCompositeOperation = 'destination-in'; core.g.drawImage(blurred(l.mask, 5), 0, 0);
    l.on = compose(glowBig, [glowBig, .7], [glowMid], [tint(l.mask, light)], [core, .95]);
    l.off = compose(tint(l.mask, 'rgba(110,96,130,.35)'), [bevel(l.mask, { d: 2, blur: 2, hiA: .3, loA: .4 })]);
    l.refl = blurred(tint(l.mask, col), 9);
  }
  const wall = mk(), w = wall.g;
  w.fillStyle = '#0b0910'; w.fillRect(0, 0, W, H);
  for (let r = 0; r * 54 < H; r++) for (let c = -1; c * 150 < W; c++) {
    const x = c * 150 + (r % 2) * 75, h1 = hash(r * 31 + c * 7.7), v = 22 + h1 * 12;
    w.fillStyle = `rgb(${v + 6},${v - 4},${v + 12})`; w.fillRect(x + 3, r * 54 + 3, 144, 48);
  }
  const vg = w.createRadialGradient(W / 2, H * .45, 200, W / 2, H * .45, 1200);
  vg.addColorStop(0, 'rgba(0,0,0,.35)'); vg.addColorStop(1, 'rgba(0,0,0,.92)');
  w.fillStyle = vg; w.fillRect(0, 0, W, H);
  PL.neon = { L, wall };
}
function neonState(k, lb) {
  const st = .04 + hash(k * 3.3 + 1) * .42, en = st + .22;
  if (lb < st) return 0;
  if (lb < en) return hash(Math.floor(lb * 30) + k * 13) > .5 ? 1 : .12;
  if (k === 8 && lb > 1.05 && hash(Math.floor(lb * 18) + 77) < .25) return .15;
  return 1;
}
function sNeon(g, lb, t) {
  const P = PL.neon, cy = H / 2 - 60;
  g.drawImage(P.wall, 0, 0);
  const st = P.L.map(l => neonState(l.k, lb));
  const vibe = (st[0] + st[1] + st[2] + st[3]) / 4, edit = st.slice(4).reduce((a, b) => a + b, 0) / 7;
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const [x, col, a] of [[W * .3, '255,45,149', vibe], [W * .64, '34,229,255', edit]]) {
    const gr = g.createRadialGradient(x, cy, 0, x, cy, 900);
    gr.addColorStop(0, `rgba(${col},${.3 * a})`); gr.addColorStop(1, `rgba(${col},0)`);
    g.fillStyle = gr; g.fillRect(0, 0, W, H);
  }
  g.restore();
  // lime frame tube drawing itself around the sign
  const fp = E.ioC(inv(.15, .9, lb)), fw = 1720, fh = 400, per = 2 * (fw + fh);
  if (fp > 0) {
    g.save(); g.setLineDash([per * fp, per]); g.lineCap = 'round';
    for (const [lw, a, bl] of [[14, .35, 30], [5, 1, 12]]) {
      g.shadowColor = C.lime; g.shadowBlur = bl; g.strokeStyle = rgba(C.lime, a); g.lineWidth = lw;
      rrect(g, W / 2 - fw / 2, cy - fh / 2, fw, fh, 46); g.stroke();
    }
    g.shadowBlur = 0; g.strokeStyle = '#f4ffd0'; g.lineWidth = 2; rrect(g, W / 2 - fw / 2, cy - fh / 2, fw, fh, 46); g.stroke();
    g.restore();
  }
  P.L.forEach((l, i) => { blit(g, l.off, W / 2 + l.dx, cy); blit(g, l.on, W / 2 + l.dx, cy, 1, st[i]); });
  const fy = cy + fh / 2 + 34;
  const fg = g.createLinearGradient(0, fy, 0, H); fg.addColorStop(0, 'rgba(20,14,30,.75)'); fg.addColorStop(1, 'rgba(5,4,8,.95)');
  g.fillStyle = fg; g.fillRect(0, fy, W, H - fy);
  g.save(); g.globalCompositeOperation = 'lighter';
  P.L.forEach((l, i) => blit(g, l.refl, W / 2 + l.dx, fy + (fy - cy) * .55, 1, .32 * st[i], 0, 1, -.55));
  g.restore();
  for (let k = 0; k < 7; k++) { g.fillStyle = `rgba(255,255,255,${.03 + .03 * hash(k)})`; g.fillRect(0, fy + 20 + k * 22 + hash(k + 3) * 12, W, 1.5); }
}

// ------------------------------------------------------------------ 05 DATAMOSH GLITCH
function initGlitch() {
  const M = textMask('A', fitPx('A', 'VIBE EDITING', 1520), 'VIBE EDITING', { pad: 60 });
  const scan = mk(); scan.g.fillStyle = 'rgba(0,0,0,.28)';
  for (let y = 0; y < H; y += 4) scan.g.fillRect(0, y, W, 2);
  PL.glitch = { M, R: tint(M, '#ff1f5a'), Cy: tint(M, '#1fffe1'), scan };
}
function glitchAmt(lb) {
  if (lb < .5) return 1 - E.outQ(lb / .5) * .9;
  for (const [a, b] of [[.98, 1.14], [1.45, 1.6], [1.82, 2.2]]) if (lb >= a && lb < b) return .85;
  return .1;
}
function sGlitch(g, lb, t) {
  const P = PL.glitch, M = P.M, mw = M.width, mh = M.height;
  bgFill(g, '#050506');
  const G = glitchAmt(lb), step = Math.floor(lb * 14);
  const T = L1.g; reset(T); T.clearRect(0, 0, mw, mh); T.globalCompositeOperation = 'lighter';
  const dx = 5 + G * 34;
  T.drawImage(P.R, -dx, 0); T.drawImage(P.Cy, dx, 0); T.drawImage(M, 0, 0);
  T.globalCompositeOperation = 'source-over';
  const X0 = W / 2 - mw / 2, Y0 = H / 2 - mh / 2 - 30;
  if (G > .5) { g.globalAlpha = .16; g.drawImage(P.R, X0 - mw * .1 + (hash(step) - .5) * 80, Y0 - mh * .1, mw * 1.2, mh * 1.2); g.globalAlpha = 1; }
  // smeared columns (pixel-sort drips)
  g.save(); g.globalAlpha = .45;
  for (let k = 0; k < 34; k++) {
    const sx = M.m.bx + hash(k * 3.1) * M.m.tw, len = (60 + hash(k * 5.3) * 420) * (.35 + .65 * inv(0, 1.2, lb));
    g.drawImage(L1, sx, M.m.by - M.m.asc * .25, 3, 4, X0 + sx, Y0 + M.m.by - M.m.asc * .25, 3, len);
  }
  g.restore();
  let y = 0, j = 0;
  while (y < mh) {
    const hh = Math.min(mh - y, 6 + Math.floor(hash(step * 7.1 + j * 3.7) * 64));
    const off = hash(step * 1.3 + j * 9.1) < G * .8 ? (hash(step * 5.7 + j) - .5) * 280 * G : 0;
    g.drawImage(L1, 0, y, mw, hh, X0 + off, Y0 + y, mw, hh);
    y += hh; j++;
  }
  const cols = [C.lime, '#ff2bd6', '#ffffff', C.cyan];
  for (let k = 0; k < Math.floor(G * 26); k++) {
    g.fillStyle = cols[k % 4];
    g.fillRect(hash(step * 3 + k) * W, H / 2 - 260 + hash(step * 9 + k * 2) * 460, 20 + hash(k + step) * 220, 4 + hash(k * 7 + step) * 34);
  }
  g.drawImage(P.scan, 0, 0);
  label(g, 'SIGNAL // CORRUPTED', 80, 150, C.lime, .85, 18);
  for (let k = 0; k < 6; k++) {
    const hex = Array.from({ length: 6 }, (_, i) => Math.floor(hash(k * 13 + i + step * .5 | 0) * 255).toString(16).padStart(2, '0')).join(' ');
    label(g, '0x' + (4096 + k * 16).toString(16).toUpperCase() + '  ' + hex.toUpperCase(), W - 80, H - 300 + k * 26, '#ffffff', .35, 15, 'right');
  }
}

// ------------------------------------------------------------------ 06 LIQUID SERIF
function initLiquid() {
  const M = textMask('PF', fitPx('PF', 'VIBE EDITING', 1580), 'VIBE EDITING', { pad: 60 });
  const outline = like(M);
  font(outline.g, 'PF', M.m.px); outline.g.strokeStyle = 'rgba(255,255,255,.6)'; outline.g.lineWidth = 2.5;
  outline.g.strokeText('VIBE EDITING', M.m.bx, M.m.by);
  PL.liquid = { M, outline, bev: bevel(M, { d: 5, blur: 5, hiA: .9, loA: .55 }), glow: blurred(tint(M, '#ff7ab8'), 30) };
}
function sLiquid(g, lb, t) {
  const P = PL.liquid, M = P.M, mw = M.width, mh = M.height;
  const sh = shader('liq', { time: t * .9 + 3, dim: 1.15, hue: .55, mode: 0 });
  g.drawImage(sh, 0, 0, W, H); g.fillStyle = 'rgba(3,2,8,.84)'; g.fillRect(0, 0, W, H);
  const X0 = W / 2 - mw / 2, Y0 = H / 2 - mh / 2 - 30;
  const lvl = E.outC(inv(0, .75, lb));
  const sy = lerp(M.m.bot + 30, M.m.top - 50, lvl), A = lerp(30, 0, inv(.55, 1.2, lb)) + 3;
  const T = L1.g; reset(T); T.clearRect(0, 0, mw, mh);
  T.drawImage(sh, 0, 0, 960, 540, -mw * .1, -mh * 1.4, mw * 1.2, mh * 3.6);
  T.drawImage(P.bev, 0, 0);
  T.globalCompositeOperation = 'destination-in'; T.drawImage(M, 0, 0);
  T.beginPath(); T.moveTo(0, mh);
  for (let x = 0; x <= mw + 24; x += 24) T.lineTo(x, sy + Math.sin(x * .011 + t * 7) * A + Math.sin(x * .027 - t * 11) * A * .45);
  T.lineTo(mw, mh); T.closePath(); T.fill();
  g.globalAlpha = .4 * lvl; g.drawImage(P.glow, X0, Y0); g.globalAlpha = .85 - .45 * lvl; g.drawImage(P.outline, X0, Y0); g.globalAlpha = 1;
  g.drawImage(L1, 0, 0, mw, mh, X0, Y0, mw, mh);
  sweepOver(g, M, X0, Y0, inv(.9, 1.7, lb), .75);
  // droplets thrown off the rising surface
  if (lb < 1) {
    g.save(); g.fillStyle = 'rgba(255,230,245,.85)';
    for (let k = 0; k < 26; k++) {
      const t0 = hash(k * 2.2) * .6, life = .35, q = (lb - t0) / life;
      if (q < 0 || q > 1) continue;
      const x = X0 + M.m.bx + hash(k * 4.1) * M.m.tw, y0 = Y0 + lerp(M.m.bot + 30, M.m.top - 50, E.outC(inv(0, .75, t0)));
      g.beginPath(); g.arc(x + (hash(k) - .5) * 120 * q, y0 - 180 * q + 260 * q * q, 7 * (1 - q) + 2, 0, TAU); g.fill();
    }
    g.restore();
  }
}

// ------------------------------------------------------------------ 07 CLAYMORPHISM
function initClay() {
  const L = letterPlates('LG', fitPx('LG', 'VIBE EDITING', 1480), 'VIBE EDITING', { pad: 70 });
  const cols = ['#FF7AA2', '#FFB347', '#5ED6B4', '#7AA7FF', '#B18CFF', '#FF8F66', '#FFD25E', '#66D9E8', '#FF7AA2', '#8CE07A', '#B18CFF'];
  const speck = mk(400, 400);
  for (let i = 0; i < 1400; i++) { speck.g.fillStyle = hash(i * 1.3) > .5 ? 'rgba(255,255,255,.35)' : 'rgba(60,20,80,.25)'; speck.g.fillRect(hash(i * 7.7) * 400, hash(i * 3.9) * 400, 1.6, 1.6); }
  for (const l of L) {
    const base = tint(l.mask, cols[l.k]);
    const shade = tint(l.mask, vgrad([[0, 'rgba(255,255,255,.35)'], [.45, 'rgba(255,255,255,0)'], [1, 'rgba(50,10,70,.28)']]));
    const sp = like(l.mask); sp.g.drawImage(l.mask, 0, 0); sp.g.globalCompositeOperation = 'source-in';
    sp.g.fillStyle = sp.g.createPattern(speck, 'repeat'); sp.g.fillRect(0, 0, sp.width, sp.height);
    l.face = compose(base, [shade], [bevel(l.mask, { d: 10, blur: 9, hiA: .7, lo: '#2a0f3d', loA: .38 })], [sp, .5]);
    l.shadow = blurred(tint(l.mask, 'rgba(80,35,110,.4)'), 18);
  }
  PL.clay = { L };
}
function clayBall(g, x, y, r, col) {
  const gr = g.createRadialGradient(x - r * .35, y - r * .4, r * .1, x, y, r);
  gr.addColorStop(0, '#ffffff'); gr.addColorStop(.25, col); gr.addColorStop(1, rgba(col, 1));
  g.save(); g.shadowColor = 'rgba(80,35,110,.3)'; g.shadowBlur = 30; g.shadowOffsetY = 22;
  g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); g.restore();
  g.fillStyle = 'rgba(40,10,60,.18)'; g.beginPath(); g.arc(x + r * .12, y + r * .14, r * .9, 0, TAU); g.arc(x, y, r, 0, TAU, true); g.fill();
}
function sClay(g, lb, t) {
  const P = PL.clay, cy = H / 2 - 20;
  const bg = g.createLinearGradient(0, 0, W, H); bg.addColorStop(0, '#FFE4EE'); bg.addColorStop(1, '#E4DCFF');
  g.fillStyle = bg; g.fillRect(-W, -H, W * 3, H * 3);
  const fl = g.createRadialGradient(W / 2, cy + 250, 0, W / 2, cy + 250, 900);
  fl.addColorStop(0, 'rgba(160,110,200,.18)'); fl.addColorStop(1, 'rgba(160,110,200,0)');
  g.fillStyle = fl; g.fillRect(0, 0, W, H);
  const bounce = (k, ph) => -Math.abs(Math.sin(t * 4.2 + ph)) * 40 * E.outC(inv(.3 + k * .1, .7 + k * .1, lb));
  clayBall(g, 250, 230 + bounce(0, 0), 46, '#7AA7FF');
  clayBall(g, W - 260, 270 + bounce(1, 1.2), 64, '#FFB347');
  clayBall(g, W - 420, H - 210 + bounce(2, 2.1), 34, '#FF7AA2');
  clayBall(g, 360, H - 240 + bounce(1, 2.9), 28, '#5ED6B4');
  const hb = P.L.th / 2, by = cy + hb;
  for (const l of P.L) {
    const land = .06 + l.k * .045, fall = inv(land - .32, land, lb);
    if (fall <= 0) continue;
    const yoff = -(1 - E.inQ(fall)) * 860;
    let sx = 1, sy = 1;
    if (lb >= land) { const d = (lb - land) * B, sq = .34 * Math.exp(-d * 8) * Math.cos(d * 26); sy = 1 - sq; sx = 1 + sq * .75; }
    else { sy = 1 + .2 * E.inQ(fall); sx = 1 - .1 * E.inQ(fall); }
    const rot = Math.sin(t * 2.6 + l.k) * .03 * (lb > land);
    const x = W / 2 + l.dx;
    blit(g, l.shadow, x, cy + 30, .6 + .4 * fall, fall * .9, 0, 1, .9);
    g.save(); g.translate(x, by + yoff); g.rotate(rot); g.scale(sx, sy);
    g.drawImage(l.face, -l.face.width / 2, -hb - l.face.height / 2); g.restore();
  }
}

// ------------------------------------------------------------------ 08 SWISS KINETIC
function initKinetic() {
  const px = 196, g = TMP.g; font(g, 'I', px);
  const unit = 'VIBE EDITING — ';
  PL.kinetic = { px, unit, uw: g.measureText(unit).width, cap: g.measureText('V').actualBoundingBoxAscent, hw: g.measureText('VIBE EDITING').width };
}
function sKinetic(g, lb, t) {
  const P = PL.kinetic, rowH = 168;
  bgFill(g, '#EEEAE1');
  font(g, 'I', P.px, -2); g.textBaseline = 'alphabetic'; g.textAlign = 'left'; g.lineJoin = 'round';
  for (let k = -3; k <= 3; k++) {
    if (k === 0) continue;
    const yc = H / 2 + k * rowH, dir = (k & 1) ? 1 : -1, d = Math.abs(k) * .05;
    const off = dir * (lb * (460 + Math.abs(k) * 90) + k * 237) + (1 - E.outX(inv(d, d + .45, lb))) * dir * -1900;
    const mode = { '-3': 'o', '-2': 'k', '-1': 'o', '1': 'o', '2': 'r', '3': 'o' }[k];
    let x = ((off % P.uw) + P.uw) % P.uw - P.uw;
    for (; x < W; x += P.uw) {
      if (mode === 'o') { g.strokeStyle = '#111'; g.lineWidth = 2.5; g.strokeText(P.unit, x, yc + P.cap / 2); }
      else { g.fillStyle = mode === 'k' ? '#111' : '#FF3B1F'; g.fillText(P.unit, x, yc + P.cap / 2); }
    }
  }
  g.fillStyle = '#111';
  for (let k = -3; k <= 4; k++) g.fillRect(0, H / 2 + (k - .5) * rowH - 1, W, 2);
  const bw = E.outX(inv(.05, .4, lb)), hot = lb >= 1;
  g.fillStyle = hot ? '#FF3B1F' : '#111';
  g.fillRect(W / 2 - W / 2 * bw, H / 2 - rowH / 2, W * bw, rowH);
  const sc = 1 + .14 * pulseAt(lb, 1, .18) * hot;
  g.save(); g.translate(W / 2, H / 2); g.scale(sc, sc);
  g.fillStyle = '#EEEAE1'; g.globalAlpha = bw; g.textAlign = 'center';
  g.fillText('VIBE EDITING', 0, P.cap / 2); g.restore();
  g.fillStyle = hot ? '#111' : '#FF3B1F'; g.beginPath(); g.arc(W / 2 + P.hw / 2 + 60, H / 2 - P.cap / 2 + 14, 14 * bw, 0, TAU); g.fill();
}

// ------------------------------------------------------------------ 09 8-BIT ARCADE
const PXC = mk(320, 180);
function pixelize(mask, bands) {
  const w = mask.width, h = mask.height, src = mask.g.getImageData(0, 0, w, h).data;
  const col = like(mask), id = col.g.createImageData(w, h), d = id.data;
  const top = mask.m.by - mask.m.asc, th = mask.m.asc;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = (y * w + x) * 4;
    if (src[i + 3] < 128) continue;
    const b = bands[clamp(Math.floor((y - top) / th * bands.length), 0, bands.length - 1)];
    d[i] = b[0]; d[i + 1] = b[1]; d[i + 2] = b[2]; d[i + 3] = 255;
  }
  col.g.putImageData(id, 0, 0);
  const out = like(mask), o = out.g;
  o.drawImage(tint(col, '#5a1580'), 2, 2);
  const blk = tint(col, '#0b0016');
  for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, 1], [-1, 1], [1, -1]]) o.drawImage(blk, dx, dy);
  o.drawImage(col, 0, 0);
  return out;
}
function initPixel() {
  const bands = [[255, 246, 140], [255, 214, 64], [255, 150, 46], [255, 72, 92]];
  const mkLine = s => letterPlates('PS', 24, s, { pad: 4 }).map(l => ({ ...l, plate: pixelize(l.mask, bands) }));
  PL.pixel = { lines: [mkLine('VIBE'), mkLine('EDITING')] };
}
function sPixel(g, lb, t) {
  const P = PL.pixel, p = PXC.g; reset(p); p.imageSmoothingEnabled = false;
  const lq = Math.floor(lb * B * 15) / (B * 15), tq = Math.floor(t * 15) / 15;
  const sky = ['#0d0221', '#160430', '#24073f', '#3a0b55', '#5b0f68', '#861a74', '#b8287a', '#e8406f'];
  sky.forEach((c, i) => { p.fillStyle = c; p.fillRect(0, i * 14, 320, 14); });
  for (let k = 0; k < 46; k++) {
    if (hash(k * 5 + Math.floor(tq * 4)) < .15) continue;
    p.fillStyle = hash(k) > .7 ? '#ffe38a' : '#ffffff'; p.fillRect(Math.floor(hash(k * 2.3) * 320), Math.floor(hash(k * 7.1) * 92), 1, 1);
  }
  const sx = 160, sy = 98, r = 30;
  for (let y = -r; y <= 0; y++) {
    if (y > -14 && ((y + 40) % 5 < 2)) continue;
    const w = Math.floor(Math.sqrt(r * r - y * y));
    p.fillStyle = y < -20 ? '#fff27a' : y < -10 ? '#ffb347' : '#ff5f7e'; p.fillRect(sx - w, sy + y, w * 2, 1);
  }
  p.fillStyle = '#12002b'; p.fillRect(0, 112, 320, 68);
  p.fillStyle = '#ff2bd6';
  const ph = fract(tq * 1.2);
  for (let k = 0; k < 9; k++) { const z = k + ph, y = Math.floor(112 + z * z * .9); if (y < 180) p.fillRect(0, y, 320, 1); }
  for (let k = -10; k <= 10; k++) for (let y = 113; y < 180; y += 1) p.fillRect(Math.floor(160 + k * (y - 112) * 1.4), y, Math.max(1, Math.ceil(Math.abs(k) * 1.4)), 1);
  let j = 0;
  P.lines.forEach((line, li) => {
    const ly = li === 0 ? 46 : 78;
    for (const l of line) {
      const land = .08 + j * .045; j++;
      const q = inv(land - .25, land + .2, lq);
      if (q <= 0) continue;
      const yoff = Math.round(-130 * (1 - E.outBounce(q)));
      p.drawImage(l.plate, Math.round(160 + l.dx - l.plate.width / 2), Math.round(ly - l.plate.height / 2 + yoff));
    }
  });
  font(p, 'PS', 8); p.textBaseline = 'top'; p.textAlign = 'left';
  p.fillStyle = '#ff4d6d'; p.fillText('1UP', 14, 20);
  p.fillStyle = '#ffffff'; p.fillText(String(Math.floor(lq * 4242) * 10).padStart(6, '0'), 14, 30);
  p.textAlign = 'right'; p.fillStyle = '#ff4d6d'; p.fillText('HI', 306, 20); p.fillStyle = '#ffffff'; p.fillText('999990', 306, 30);
  p.textAlign = 'center';
  if (lq > .7 && Math.floor(lq * 4) % 2 === 0) { p.fillStyle = '#ffffff'; p.fillText('PRESS START', 160, 104); }
  p.fillStyle = '#d4ff3f'; p.fillText('CREDIT 01', 160, 168);
  g.save(); g.imageSmoothingEnabled = false; g.drawImage(PXC, 0, 0, W, H); g.restore();
  g.drawImage(PL.glitch.scan, 0, 0);
}

// ------------------------------------------------------------------ 10 POP ART
function initPop() {
  const m = stackMask('BG', ['VIBE', 'EDITING'], [760, 1260], 30, 60);
  const dots = like(m);
  for (let y = 0; y < m.height; y += 15) for (let x = (y / 15 % 2) * 7.5; x < m.width; x += 15) {
    const r = 6 * inv(m.m.top + m.m.th * .3, m.m.bot, y);
    if (r > .4) { dots.g.fillStyle = '#FF3D7F'; dots.g.beginPath(); dots.g.arc(x, y, r, 0, TAU); dots.g.fill(); }
  }
  const face = compose(tint(m, '#ffffff'), [dots, 1, 'source-atop']);
  const blk = tint(m, '#111111'), outl = like(m);
  for (let a = 0; a < 24; a++) outl.g.drawImage(blk, Math.cos(a / 24 * TAU) * 13, Math.sin(a / 24 * TAU) * 13);
  outl.g.drawImage(blk, 0, 0);
  const plate = compose(outl, [outl, 1, 'destination-over', 20, 22], [face]);
  const ht = mk(), h = ht.g;
  h.fillStyle = C.yellow; h.fillRect(0, 0, W, H); h.fillStyle = 'rgba(255,70,90,.55)';
  for (let y = 0; y < H + 26; y += 26) for (let x = (y / 26 % 2) * 13; x < W + 26; x += 26) {
    const r = 1.5 + 10 * Math.min(1, Math.hypot(x - W / 2, y - H / 2) / 1100);
    h.beginPath(); h.arc(x, y, r, 0, TAU); h.fill();
  }
  const sb = mk(1800, 1800), s = sb.g;
  const burstPath = (R, r, n, seed) => { s.beginPath(); for (let i = 0; i < n * 2; i++) { const a = i / (n * 2) * TAU, rr = i % 2 ? r : R * (.86 + .14 * hash(i + seed)); s.lineTo(900 + Math.cos(a) * rr, 900 + Math.sin(a) * rr); } s.closePath(); };
  burstPath(860, 610, 22, 1); s.fillStyle = '#22C3FF'; s.fill(); s.lineWidth = 12; s.strokeStyle = '#111'; s.lineJoin = 'miter'; s.stroke();
  burstPath(640, 500, 18, 7); s.fillStyle = '#FF3D7F'; s.fill(); s.lineWidth = 8; s.stroke();
  const sl = mk(), l = sl.g; l.fillStyle = '#111';
  for (let i = 0; i < 70; i++) {
    const a = i / 70 * TAU + hash(i) * .05, w = .006 + hash(i * 3) * .01, r0 = 640 + hash(i * 5) * 200;
    l.beginPath(); l.moveTo(W / 2 + Math.cos(a) * r0, H / 2 + Math.sin(a) * r0);
    l.lineTo(W / 2 + Math.cos(a - w) * 1500, H / 2 + Math.sin(a - w) * 1500); l.lineTo(W / 2 + Math.cos(a + w) * 1500, H / 2 + Math.sin(a + w) * 1500); l.fill();
  }
  PL.pop = { plate, ht, sb, sl };
}
function sPop(g, lb, t) {
  const P = PL.pop;
  g.drawImage(P.ht, 0, 0);
  g.globalAlpha = .9 * (1 - inv(.15, .9, lb)); g.drawImage(P.sl, 0, 0); g.globalAlpha = 1;
  const bp = E.outB(inv(0, .32, lb), 2);
  blit(g, P.sb, W / 2, H / 2 + 10, bp * (.62 + .025 * Math.sin(t * 18)), 1, t * .35);
  const s = E.outB(inv(.04, .38, lb), 2.6), rot = lerp(-.5, -.07, E.outC(inv(.04, .45, lb)));
  blit(g, P.plate, W / 2, H / 2 + 10, s * (1 + .03 * pulseAt(lb, 1, .2) * (lb >= 1)), 1, rot);
  const cp = E.outX(inv(.35, .65, lb));
  if (cp > 0) {
    g.save(); g.translate(lerp(-700, 150, cp), 150); g.rotate(-.03);
    g.fillStyle = '#111'; g.fillRect(10, 10, 560, 76); g.fillStyle = '#FFF4C8'; g.fillRect(0, 0, 560, 76);
    g.lineWidth = 5; g.strokeStyle = '#111'; g.strokeRect(0, 0, 560, 76);
    font(g, 'BG', 30); g.fillStyle = '#111'; g.textBaseline = 'middle'; g.textAlign = 'left'; g.fillText('MEANWHILE, IN THE EDIT…', 24, 40);
    g.restore();
  }
}

// ------------------------------------------------------------------ 11 PARTICLE FIELD
function initParticles() {
  const m = textMask('I', fitPx('I', 'VIBE EDITING', 1580), 'VIBE EDITING', { pad: 20 });
  const d = m.g.getImageData(0, 0, m.width, m.height).data, pts = [];
  let i = 0;
  for (let y = 0; y < m.height; y += 6) for (let x = 0; x < m.width; x += 6) {
    if (d[(y * m.width + x) * 4 + 3] < 128) continue;
    i++;
    const th = hash(i * 1.1) * TAU, ph = Math.acos(2 * hash(i * 2.7) - 1), R = 900 + hash(i * 3.3) * 900;
    pts.push({ tx: x - m.width / 2 + (hash(i) - .5) * 2, ty: y - m.height / 2 + (hash(i * 9) - .5) * 2,
      sx: R * Math.sin(ph) * Math.cos(th), sy: R * Math.sin(ph) * Math.sin(th) * .6, sz: R * Math.cos(ph),
      dl: hash(i * 4.4) * .3, pink: hash(i * 5.5) < .16 });
  }
  const gm = textMask('I', m.m.px, 'VIBE EDITING', { pad: 90 });
  PL.particles = { pts, glow: blurred(tint(gm, '#2aa8ff'), 24), m };
}
function sParticles(g, lb, t) {
  const P = PL.particles, cx = W / 2, cy = H / 2 - 30;
  bgFill(g, '#020309');
  const rg = g.createRadialGradient(cx, cy, 0, cx, cy, 1000);
  rg.addColorStop(0, 'rgba(20,50,110,.55)'); rg.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = rg; g.fillRect(0, 0, W, H);
  blit(g, P.glow, cx, cy, 1, .55 * inv(.75, 1.25, lb) * (1 - inv(1.6, 2, lb)));
  g.save(); g.globalCompositeOperation = 'lighter';
  const ex = E.inQ(inv(1.55, 2.1, lb)), wave = (lb - 1) * 1.7 - .9, f = 1500;
  for (const p of P.pts) {
    const q = E.ioC(clamp((lb - p.dl) / .9));
    const a = (1 - q) * 2.6, ca = Math.cos(a), sa = Math.sin(a);
    const rx = p.sx * ca - p.sz * sa, rz = p.sx * sa + p.sz * ca;
    let x = lerp(rx, p.tx, q), y = lerp(p.sy, p.ty, q), z = lerp(rz, 0, q);
    if (ex > 0) { x += p.sx * .35 * ex; y += p.sy * .35 * ex; z -= 900 * ex * (.5 + hash(p.tx)); }
    const k = f / (f + z);
    if (k <= 0) continue;
    const sh = Math.max(0, 1 - Math.abs(p.tx / 900 - wave) * 5);
    g.globalAlpha = clamp((.3 + .6 * q + .6 * sh) * (1 - ex * .6));
    g.fillStyle = p.pink ? '#ff5fb5' : (sh > .3 ? '#ffffff' : '#5fe3ff');
    const s = 3.4 * k;
    g.fillRect(cx + x * k - s / 2, cy + y * k - s / 2, s, s);
  }
  g.restore();
}

// ------------------------------------------------------------------ 12 BLUEPRINT
function initBlueprint() {
  const px = fitPx('U', 'VIBE EDITING', 1500);
  const M = textMask('U', px, 'VIBE EDITING', { pad: 60 });
  const grid = mk(), gg = grid.g;
  const bg = gg.createRadialGradient(W / 2, H / 2, 100, W / 2, H / 2, 1200); bg.addColorStop(0, '#1450b4'); bg.addColorStop(1, '#0a2a6e');
  gg.fillStyle = bg; gg.fillRect(0, 0, W, H);
  for (let x = 0; x < W; x += 24) { gg.fillStyle = x % 120 ? 'rgba(255,255,255,.06)' : 'rgba(255,255,255,.14)'; gg.fillRect(x, 0, 1, H); }
  for (let y = 0; y < H; y += 24) { gg.fillStyle = y % 120 ? 'rgba(255,255,255,.06)' : 'rgba(255,255,255,.14)'; gg.fillRect(0, y, W, 1); }
  const hatch = like(M), hg = hatch.g;
  hg.strokeStyle = 'rgba(255,255,255,.55)'; hg.lineWidth = 1.5;
  for (let x = -M.height; x < M.width; x += 9) { hg.beginPath(); hg.moveTo(x, M.height); hg.lineTo(x + M.height, 0); hg.stroke(); }
  hg.globalCompositeOperation = 'destination-in'; hg.drawImage(M, 0, 0);
  const L = letterPlates('U', px, 'VIBE EDITING', { pad: 0 });
  PL.blueprint = { M, px, grid, hatch, L };
}
function sBlueprint(g, lb, t) {
  const P = PL.blueprint, M = P.M, cy = H / 2 - 30;
  g.drawImage(P.grid, 0, 0);
  const X0 = W / 2 - M.width / 2, Y0 = cy - M.height / 2, base = Y0 + M.m.by, cap = base - M.m.asc;
  const x0 = X0 + M.m.bx, x1 = x0 + M.m.tw;
  g.save(); g.lineWidth = 1.5;
  [[cap, 'CAP HEIGHT'], [(cap + base) / 2, 'MEDIAN'], [base, 'BASELINE']].forEach(([y, s], i) => {
    const p = E.outX(inv(i * .07, .35 + i * .07, lb));
    g.strokeStyle = 'rgba(255,255,255,.45)'; g.setLineDash(i === 1 ? [10, 8] : []);
    g.beginPath(); g.moveTo(70, y); g.lineTo(lerp(70, W - 70, p), y); g.stroke();
    if (p > .3) label(g, s, 74, y - 10, '#ffffff', .7 * p, 14);
  });
  g.setLineDash([6, 6]); g.strokeStyle = 'rgba(255,255,255,.3)';
  const vp = E.outC(inv(.3, .65, lb));
  for (const l of P.L) for (const ex of [-l.w / 2, l.w / 2]) {
    const x = W / 2 + l.dx + ex; g.beginPath(); g.moveTo(x, cap - 70); g.lineTo(x, lerp(cap - 70, base + 70, vp)); g.stroke();
  }
  g.setLineDash([]);
  const cp = E.ioC(inv(.4, .85, lb));
  for (const k of [2, 10]) {
    const l = P.L[k], x = W / 2 + l.dx, y = (cap + base) / 2, r = M.m.asc * .62;
    g.strokeStyle = 'rgba(212,255,63,.85)'; g.lineWidth = 2;
    g.beginPath(); g.arc(x, y, r, -Math.PI / 2, -Math.PI / 2 + TAU * cp); g.stroke();
    if (cp > 0) { g.beginPath(); g.moveTo(x - 10, y); g.lineTo(x + 10, y); g.moveTo(x, y - 10); g.lineTo(x, y + 10); g.stroke(); }
  }
  const dp = E.outX(inv(.5, .8, lb)), dy = base + 90;
  if (dp > 0) {
    g.strokeStyle = '#ffffff'; g.lineWidth = 2; g.globalAlpha = dp;
    const xm = (x0 + x1) / 2, hw = (x1 - x0) / 2 * dp;
    g.beginPath(); g.moveTo(xm - hw, dy); g.lineTo(xm + hw, dy); g.moveTo(xm - hw, dy - 14); g.lineTo(xm - hw, dy + 14); g.moveTo(xm + hw, dy - 14); g.lineTo(xm + hw, dy + 14); g.stroke();
    g.fillStyle = '#0f3f98'; g.fillRect(xm - 90, dy - 18, 180, 36);
    label(g, Math.round(M.m.tw * dp) + ' PX', xm, dy + 6, '#ffffff', 1, 18, 'center');
    g.globalAlpha = 1;
  }
  g.restore();
  g.globalAlpha = inv(.85, 1.3, lb); g.drawImage(P.hatch, X0, Y0); g.globalAlpha = 1;
  g.save(); font(g, 'U', P.px); g.lineWidth = 3; g.strokeStyle = '#ffffff'; g.lineJoin = 'round';
  g.setLineDash([2400, 2400]); g.lineDashOffset = 2400 * (1 - E.ioC(inv(.08, .95, lb)));
  g.strokeText('VIBE EDITING', x0, base); g.restore();
  const tp = E.outC(inv(.2, .5, lb));
  if (tp > 0) {
    g.save(); g.globalAlpha = tp; g.strokeStyle = '#ffffff'; g.lineWidth = 2;
    const bx = W - 560, by = H - 290; g.strokeRect(bx, by, 440, 132);
    g.beginPath(); g.moveTo(bx, by + 44); g.lineTo(bx + 440, by + 44); g.moveTo(bx, by + 88); g.lineTo(bx + 440, by + 88); g.moveTo(bx + 220, by + 44); g.lineTo(bx + 220, by + 132); g.stroke();
    label(g, 'PROJECT  VIBE EDITING', bx + 16, by + 29, '#ffffff', .9, 15);
    label(g, 'SHEET 12/13', bx + 16, by + 73, '#ffffff', .8, 14); label(g, 'SCALE 1:1', bx + 236, by + 73, '#ffffff', .8, 14);
    label(g, 'DRAWN BY CODE', bx + 16, by + 117, '#ffffff', .8, 14); label(g, 'REV 2026', bx + 236, by + 117, '#ffffff', .8, 14);
    g.restore();
  }
}

// ------------------------------------------------------------------ 13 HOLOGRAPHIC FOIL
const HB = mk(480, 270), HBB = mk(480, 270);
function initHolo() {
  const M = textMask('MO', fitPx('MO', 'VIBE EDITING', 1500), 'VIBE EDITING', { pad: 60 });
  const stripes = like(M), s = stripes.g;
  s.strokeStyle = 'rgba(255,255,255,.5)'; s.lineWidth = 1;
  for (let x = -M.height; x < M.width; x += 5) { s.beginPath(); s.moveTo(x, M.height); s.lineTo(x + M.height * .6, 0); s.stroke(); }
  s.globalCompositeOperation = 'destination-in'; s.drawImage(M, 0, 0);
  PL.holo = { M, stripes, dark: tint(M, '#000'), bev: bevel(M, { d: 3, blur: 3, hiA: .95, lo: '#2a1b4a', loA: .4 }), glow: blurred(tint(M, '#b9a6ff'), 34) };
}
const HOLO = ['#ff9ff3', '#feca57', '#7bed9f', '#48dbfb', '#a29bfe', '#ff9ff3'];
function sHolo(g, lb, t) {
  const P = PL.holo, M = P.M, mw = M.width, mh = M.height, cy = H / 2 - 30;
  bgFill(g, '#07060c');
  const h = HB.g; reset(h); h.clearRect(0, 0, 480, 270);
  const cg = h.createConicGradient(t * .7, 240, 135); HOLO.forEach((c, i) => cg.addColorStop(i / 5, c));
  h.fillStyle = cg; h.beginPath(); h.ellipse(240, 135, 190, 100, 0, 0, TAU); h.fill();
  const hb = HBB.g; reset(hb); hb.clearRect(0, 0, 480, 270); hb.filter = 'blur(26px)'; hb.drawImage(HB, 0, 0); hb.filter = 'none';
  g.globalAlpha = .3; g.drawImage(HBB, 0, 0, W, H); g.globalAlpha = 1;
  const T = L1.g; reset(T); T.clearRect(0, 0, mw, mh);
  T.drawImage(M, 0, 0); T.globalCompositeOperation = 'source-in';
  const per = 560, x0 = -per * (1 + fract(t * .45 + lb * .3)), cyc = 6;
  const fg = T.createLinearGradient(x0, 0, x0 + per * cyc, per * cyc * .3);
  for (let i = 0; i <= cyc * 5; i++) fg.addColorStop(i / (cyc * 5), HOLO[i % 5]);
  T.fillStyle = fg; T.fillRect(0, 0, mw, mh);
  T.globalCompositeOperation = 'source-over';
  T.globalAlpha = .35; T.drawImage(P.stripes, 0, 0); T.globalAlpha = 1; T.drawImage(P.bev, 0, 0);
  const flip = E.outC(inv(0, .55, lb)), sx = Math.cos((1 - flip) * Math.PI);
  g.save(); g.translate(W / 2, cy); g.scale(sx, 1); g.transform(1, (1 - flip) * .15, 0, 1, 0, 0);
  g.globalAlpha = .6 * flip; g.drawImage(P.glow, -mw / 2, -mh / 2); g.globalAlpha = 1;
  g.drawImage(L1, 0, 0, mw, mh, -mw / 2, -mh / 2, mw, mh);
  if (sx < 0) { g.globalAlpha = -sx * .55; g.drawImage(P.dark, -mw / 2, -mh / 2); }
  g.restore();
  sweepOver(g, M, W / 2 - mw / 2, cy - mh / 2, inv(.5, 1.3, lb), .9);
  const sa = inv(.4, .8, lb);
  for (let i = 0; i < 16; i++) {
    const x = W / 2 + (hash(i * 3.3) - .5) * 1700, y = cy + (hash(i * 7.9) - .5) * 520;
    glint(g, x, y, 22 + hash(i) * 34, .7 * sa * Math.pow(Math.max(0, Math.sin(t * 5 + i * 1.7)), 6), t + i);
  }
}

// ================================================================== timeline
const STYLES = [
  { key: 'chrome', name: 'LIQUID CHROME', fn: sChrome, init: initChrome, bloom: .6 },
  { key: 'glass', name: 'GLASSMORPHISM', fn: sGlass, init: initGlass, bloom: .5 },
  { key: 'neu', name: 'NEUMORPHISM', fn: sNeu, init: initNeu, light: true },
  { key: 'neon', name: 'NEON NOIR', fn: sNeon, init: initNeon, bloom: 1 },
  { key: 'glitch', name: 'DATAMOSH', fn: sGlitch, init: initGlitch, bloom: .55 },
  { key: 'liquid', name: 'LIQUID SERIF', fn: sLiquid, init: initLiquid, bloom: .6 },
  { key: 'clay', name: 'CLAYMORPHISM', fn: sClay, init: initClay, light: true },
  { key: 'kinetic', name: 'SWISS KINETIC', fn: sKinetic, init: initKinetic, light: true },
  { key: 'pixel', name: '8-BIT ARCADE', fn: sPixel, init: initPixel, bloom: .55 },
  { key: 'pop', name: 'POP ART', fn: sPop, init: initPop, light: true },
  { key: 'particles', name: 'PARTICLE FIELD', fn: sParticles, init: initParticles, bloom: 1.1 },
  { key: 'blueprint', name: 'BLUEPRINT', fn: sBlueprint, init: initBlueprint, bloom: .35 },
  { key: 'holo', name: 'HOLOGRAPHIC', fn: sHolo, init: initHolo, bloom: .75 },
];
STYLES.forEach((s, i) => { s.idx = i; });
const STYLE = Object.fromEntries(STYLES.map(s => [s.key, s]));
let STILLS = [];

// montage: [beat, style, invert]
const MONT = [[36, 'neon', 0], [36.5, 'chrome', 1], [37, 'clay', 0], [37.5, 'glitch', 0], [37.75, 'pixel', 1], [38, 'glass', 0],
  [38.25, 'pop', 0], [38.5, 'holo', 1], [38.75, 'kinetic', 0], [39, 'blueprint', 0], [39.25, 'particles', 0]];
const montageCut = bt => { let c = MONT[0]; for (const k of MONT) if (bt >= k[0]) c = k; return c; };
const TITLES = [[2, 3.5, 'ONE NAME.'], [3.5, 5, '13 STYLES.'], [5, 5.75, 'ZERO LIMITS.']];
const STROBE = [5.75, 7.375];   // 13 stills at 1/8 beat

// ------------------------------------------------------------------ 00 cold open
function converge(g, p) {
  const e = E.inX(p);
  streak(g, W / 2, H / 2, lerp(40, 1500, e), lerp(1, 5, e), '190,215,255', .3 + .7 * e);
  glint(g, W / 2, H / 2, lerp(20, 260, e), .4 + .6 * e, p * 3);
}
function sIntro(g, lb, t) {
  bgFill(g, '#000');
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 70; i++) {
    const x = fract(hash(i) + t * .012 * (hash(i * 2) - .5)) * W, y = fract(hash(i * 3.1) - t * .02 * (.3 + hash(i * 5))) * H;
    g.fillStyle = `rgba(170,190,230,${.08 + .18 * hash(i * 7)})`; g.beginPath(); g.arc(x, y, .8 + 2 * hash(i * 9), 0, TAU); g.fill();
  }
  g.restore();
  if (lb < 2) {
    const beat = 1 + .5 * pulseAt(lb, 0, .12) + .35 * pulseAt(lb, .45, .12) + .5 * pulseAt(lb, 1, .12) + .35 * pulseAt(lb, 1.45, .12);
    streak(g, W / 2, H / 2, E.outX(inv(0, 1.6, lb)) * 950 * beat, 2.5, '170,200,255', .9 * (1 - inv(1.75, 2, lb)));
    const a = inv(.45, .85, lb) * (1 - inv(1.65, 1.95, lb));
    if (a > 0) label(g, 'VIBE EDITING PRESENTS', W / 2, H / 2 + 62, '#c9d6ee', .85 * a, 20, 'center', lerp(8, 18, inv(.45, 2, lb)));
  }
  for (const [a, b, s] of TITLES) {
    if (lb < a || lb >= b) continue;
    const l = lb - a, sc = 1.1 - .08 * E.outC(l / (b - a));
    g.save(); g.translate(W / 2, H / 2); g.scale(sc, sc);
    font(g, 'A', 190, 6); g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillStyle = '#ffffff'; g.globalAlpha = 1 - inv(b - a - .12, b - a, l) * .6;
    g.fillText(s, 0, 8);
    g.restore();
    const lw = E.outX(inv(0, .5, l)) * 620;
    g.fillStyle = 'rgba(255,255,255,.55)'; g.fillRect(W / 2 - lw, H / 2 - 140, lw * 2, 1.5); g.fillRect(W / 2 - lw, H / 2 + 150, lw * 2, 1.5);
  }
  if (lb >= STROBE[0] && lb < STROBE[1]) {
    const i = Math.floor((lb - STROBE[0]) / .125);
    blit(g, STILLS[i % STILLS.length], W / 2, H / 2, 1.08 - .06 * fract((lb - STROBE[0]) / .125));
    font(g, 'A', 120); g.textAlign = 'right'; g.textBaseline = 'alphabetic'; g.fillStyle = (STYLES[i % 13].light ? '#111' : '#fff');
    g.fillText(String(i + 1).padStart(2, '0'), W - 90, H - 90);
  }
  if (lb >= 7.5) converge(g, inv(7.5, 8, lb));
}

// ------------------------------------------------------------------ montage + finale
function sMontage(g, lb, t) {
  const bt = 36 + lb;
  if (bt >= 39.5) { bgFill(g, '#000'); converge(g, inv(39.5, 40, bt)); return false; }
  const c = montageCut(bt), st = STYLE[c[1]];
  st.fn(g, .55 + (bt - c[0]) * 1.4, t);
  return !!st.light;
}
const MOSAIC = ['chrome', 'pop', 'neon', 'neu', 'glitch', 'clay', 'liquid', 'kinetic', 'particles', 'pixel', 'glass', 'holo', 'blueprint'];
function initHero() {
  const LW = 1180, gap = 54, cy = H / 2 - 70;
  const l1 = letterPlates('U', fitPx('U', 'VIBE', LW), 'VIBE', { pad: 70 });
  const l2 = letterPlates('U', fitPx('U', 'EDITING', LW), 'EDITING', { pad: 70 });
  const total = l1.th + gap + l2.th, y1 = cy - total / 2 + l1.th / 2, y2 = cy + total / 2 - l2.th / 2;
  const letters = [...l1.map(l => ({ ...l, y: y1 })), ...l2.map(l => ({ ...l, y: y2, k: l.k + 4 }))];
  const lock = mk(W, H);
  for (const l of letters) {
    l.face = compose(tint(l.mask, vgrad([[0, '#ffffff'], [.44, '#dfe6f1'], [.5, '#7d889e'], [.58, '#c3ccdb'], [.82, '#f6f8fc'], [1, '#ffffff']])),
      [bevel(l.mask, { d: 3, blur: 2.5, hiA: .95, lo: '#141824', loA: .5 })]);
    l.rimP = tint(l.mask, C.pink); l.rimC = tint(l.mask, C.cyan); l.glow = blurred(tint(l.mask, '#ffffff'), 28);
    lock.g.drawImage(l.mask, W / 2 + l.dx - l.mask.width / 2, l.y - l.mask.height / 2);
  }
  PL.hero = { letters, lock, y1, y2, top: y1 - l1.th / 2, bot: y2 + l2.th / 2, LW };
}
function mosaic(g, lb) {
  bgFill(g, '#000');
  const n = MOSAIC.length, sw = W / n;
  for (let k = 0; k < n; k++) {
    const dir = k % 2 ? 1 : -1, d = Math.abs(k - 6) * .035;
    const enter = E.outX(inv(d, d + .45, lb));
    const cw = sw * (1 - E.inC(inv(1.55 + Math.abs(k - 6) * .025, 1.95, lb)));
    if (cw <= .5) continue;
    g.save(); g.beginPath(); g.rect(k * sw + (sw - cw) / 2, 0, cw + .5, H); g.clip();
    g.drawImage(STILLS[STYLE[MOSAIC[k]].idx], 0, dir * ((1 - enter) * H + lb * 26));
    g.restore();
    if (k) { g.fillStyle = 'rgba(255,255,255,.5)'; g.fillRect(k * sw - 1, 0, 2, H); }
  }
}
function hero(g, lb, t) {
  const P = PL.hero;
  bgFill(g, '#030305');
  const sh = shader('aura', { time: t * .5, dim: 1, hue: .1, mode: 0 });
  const T = L2.g; reset(T); T.clearRect(0, 0, W, H); T.drawImage(sh, 0, 0, W, H);
  const cyc = (P.top + P.bot) / 2;
  const rg = T.createRadialGradient(W / 2, cyc, 0, W / 2, cyc, 950);
  rg.addColorStop(0, 'rgba(0,0,0,.8)'); rg.addColorStop(.5, 'rgba(0,0,0,.3)'); rg.addColorStop(1, 'rgba(0,0,0,0)');
  T.globalCompositeOperation = 'destination-in'; T.fillStyle = rg; T.fillRect(0, 0, W, H);
  g.globalAlpha = (.42 + .45 * pulseAt(lb, 0, .8) + .4 * pulseAt(lb, 4, .8)) * E.outC(inv(0, .4, lb)); g.drawImage(L2, 0, 0); g.globalAlpha = 1;
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 60; i++) {
    const x = hash(i * 1.9) * W, y = fract(hash(i * 4.3) - t * .03 * (.4 + hash(i))) * H;
    g.fillStyle = `rgba(200,220,255,${.1 + .2 * hash(i * 6)})`; g.beginPath(); g.arc(x, y, 1 + 1.5 * hash(i * 8), 0, TAU); g.fill();
  }
  g.restore();
  const push = 1 + .04 * E.ioC(inv(0, 6, lb)) + .035 * pulseAt(lb, 4, .3) * (lb >= 4);
  g.save(); g.translate(W / 2, cyc); g.scale(push, push); g.translate(-W / 2, -cyc);
  for (const l of P.letters) {
    const d = l.k * .03, q = E.outX(inv(d, d + .35, lb));
    if (q <= 0) continue;
    const s = lerp(2.6, 1, q), a = clamp(q * 2.5), x = W / 2 + l.dx;
    blit(g, l.glow, x, l.y, s, .2 * a);
    g.save(); g.globalCompositeOperation = 'lighter';
    blit(g, l.rimP, x - 4, l.y, s, .8 * a); blit(g, l.rimC, x + 4, l.y, s, .8 * a);
    g.restore();
    blit(g, l.face, x, l.y, s, a);
  }
  sweepOver(g, P.lock, 0, 0, inv(1, 1.8, lb), 1);
  sweepOver(g, P.lock, 0, 0, inv(4.02, 4.7, lb), .85);
  const sp = E.outB(inv(1.6, 2, lb));
  if (sp > 0) {
    const sx = W / 2 + P.LW / 2 + 52, sy = P.top + 18;
    g.save(); g.fillStyle = C.lime; g.shadowColor = C.lime; g.shadowBlur = 30; star4(g, sx, sy, 34 * sp, lb * 1.4); g.fill(); g.restore();
  }
  g.restore();
  // tagline: scrambles, then locks letter by letter
  const tag = 'ONE NAME  ·  EVERY VIBE', ty = P.bot + 112;
  font(g, 'M', 30, 0); const cwid = g.measureText('M').width + 12, tw = cwid * tag.length;
  g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  const GL = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#%&*/<>';
  for (let i = 0; i < tag.length; i++) {
    const lock = 1.05 + i * .035;
    if (lb < lock - .3 || tag[i] === ' ') continue;
    const ch = lb < lock ? GL[Math.floor(hash(Math.floor(lb * 30) + i * 7) * GL.length)] : tag[i];
    g.fillStyle = lb < lock ? rgba(C.lime, .9) : 'rgba(232,236,244,.95)';
    g.fillText(ch, W / 2 - tw / 2 + i * cwid + 6, ty);
  }
  const ll = E.outX(inv(1.7, 2.3, lb)) * 240;
  g.fillStyle = 'rgba(255,255,255,.4)';
  g.fillRect(W / 2 - tw / 2 - 40 - ll, ty - 11, ll, 1.5); g.fillRect(W / 2 + tw / 2 + 40, ty - 11, ll, 1.5);
  const fa = inv(2.2, 2.8, lb);
  if (fa > 0) label(g, 'LOGO ANIMATION SYSTEM  ·  13 STYLES  ·  2026', W / 2, H - 92, '#ffffff', .45 * fa, 15, 'center', 4);
}
function sFinale(g, lb, t) {
  if (lb < 2) mosaic(g, lb); else hero(g, lb - 2, t);
  return false;
}

// ------------------------------------------------------------------ scene table + transitions
const SCENES = [{ a: 0, b: 8, fn: sIntro }];
SCENES.push({ a: 8, b: 12, fn: sChrome, st: STYLES[0] });
STYLES.slice(1).forEach((s, i) => SCENES.push({ a: 12 + i * 2, b: 14 + i * 2, fn: s.fn, st: s }));
SCENES.push({ a: 36, b: 40, fn: sMontage }, { a: 40, b: 48, fn: sFinale });
const sceneAt = bt => SCENES.find(s => bt >= s.a && bt < s.b) || SCENES[SCENES.length - 1];
const STYLE_CUTS = SCENES.filter(s => s.st && s.a > 8).map(s => s.a);
const TRANS = {};
STYLE_CUTS.forEach((c, i) => { TRANS[c] = ['slice', 'wipe', 'iris', 'zoom'][i % 4]; });
const TD = .32;
const PREV = mk();
function maskTrans(g, P, type, p) {
  g.save(); reset(g);
  if (type === 'slice') {
    const n = 9, bh = H / n; g.beginPath();
    for (let j = 0; j < n; j++) { const q = E.inC(clamp(p * 1.6 - j * .07)), w = W * (1 - q); g.rect(j % 2 ? W - w : 0, j * bh, w, bh + 1); }
    g.clip(); g.drawImage(P, 0, 0);
  } else if (type === 'wipe') {
    const e = lerp(-100, W + 500, E.ioC(p));
    g.save(); g.beginPath(); g.moveTo(e, 0); g.lineTo(W + 600, 0); g.lineTo(W + 600, H); g.lineTo(e - 420, H); g.closePath(); g.clip(); g.drawImage(P, 0, 0); g.restore();
    g.strokeStyle = C.lime; g.lineWidth = 10; g.shadowColor = C.lime; g.shadowBlur = 30;
    g.beginPath(); g.moveTo(e, 0); g.lineTo(e - 420, H); g.stroke();
  } else if (type === 'iris') {
    const r = E.inC(p) * 1250;
    g.save(); g.beginPath(); g.rect(0, 0, W, H); g.arc(W / 2, H / 2, r, 0, TAU); g.clip('evenodd'); g.drawImage(P, 0, 0); g.restore();
    g.strokeStyle = '#fff'; g.lineWidth = 14 * (1 - p); g.beginPath(); g.arc(W / 2, H / 2, r, 0, TAU); g.stroke();
  } else {
    g.globalAlpha = 1 - E.outQ(p); g.translate(W / 2, H / 2); g.scale(1 + p * .7, 1 + p * .7); g.drawImage(P, -W / 2, -H / 2);
  }
  g.restore();
}

// ------------------------------------------------------------------ camera, post fx, HUD
const BIG = [8, 40, 42, 46];
function camera(bt) {
  let z = 1.03, x = 0, y = 0, r = 0;
  for (const h of BIG) z += .1 * pulseAt(bt, h, .3);
  for (const [a] of TITLES) z += .05 * pulseAt(bt, a, .4);
  for (const h of STYLE_CUTS) z += .045 * pulseAt(bt, h, .22);
  if (bt >= 36 && bt < 39.5) { const c = montageCut(bt); z += .08 * pulseAt(bt, c[0], .18); r += (hash(c[0]) - .5) * .04; }
  if (bt >= 8 && bt < 36) z += .012 * Math.exp(-fract(bt) / .12);
  for (const [at, A] of [[8, 36], [40, 30], [42, 28], [46, 18], [2, 9], [3.5, 9], [5, 9]]) {
    const d = bt - at;
    if (d >= 0 && d < 2.5) { const a = A * Math.exp(-d / .35); x += a * noise1(d * 38 + at); y += a * noise1(d * 38 + at + 50); r += a * .0011 * noise1(d * 30 + at + 99); }
  }
  return { z, x, y, r };
}
function applyCam(g, c) { g.translate(W / 2 + c.x, H / 2 + c.y); g.rotate(c.r); g.scale(c.z, c.z); g.translate(-W / 2, -H / 2); }
function fx(bt) {
  let ab = .35, glitch = 0, flash = 0, bloom = .45, invert = 0;
  const FL = [[2, .3], [3.5, .3], [5, .3], [8, 1], [40, .85], [42, 1], [46, .6], ...STYLE_CUTS.map(c => [c, .3])];
  for (const [at, f] of FL) flash = Math.max(flash, f * pulseAt(bt, at, .12));
  if (bt >= STROBE[1] && bt < 7.5) flash = Math.max(flash, 1 - inv(7.43, 7.5, bt));
  for (const h of [...BIG, ...STYLE_CUTS, 2, 3.5, 5]) ab += 2.2 * pulseAt(bt, h, .3);
  const sc = sceneAt(bt);
  if (sc.st) bloom = sc.st.light ? 0 : (sc.st.bloom ?? .45);
  if (sc.st && sc.st.key === 'glitch') { glitch = glitchAmt(bt - sc.a) * .5; ab += glitch * 3; }
  STYLE_CUTS.forEach((c, i) => { if (i % 2 && bt > c - .07 && bt < c + .03) glitch = Math.max(glitch, .55); });
  if (bt >= STROBE[0] && bt < STROBE[1]) { const st = STYLES[Math.floor((bt - STROBE[0]) / .125) % 13]; bloom = st.light ? 0 : .5; ab += 1; }
  if (bt >= 36 && bt < 39.5) {
    const c = montageCut(bt), st = STYLE[c[1]];
    invert = c[2]; bloom = st.light ? 0 : .55; flash = Math.max(flash, .45 * pulseAt(bt, c[0], .07)); ab += 1.8 * pulseAt(bt, c[0], .2);
    if (bt > 39.2) glitch = .4;
  }
  if (bt >= 40 && bt < 42) bloom = .25;
  if (bt >= 42) bloom = .5;
  if (sc.st && bt - sc.a < TD) { const pv = sceneAt(sc.a - .001); if (pv.st && pv.st.light) bloom = Math.min(bloom, .15); }
  return { ab, glitch, flash, bloom, invert };
}
function hud(g, bt, light) {
  let st, a0;
  if (bt >= 8 && bt < 36) { const sc = sceneAt(bt); st = sc.st; a0 = sc.a; }
  else if (bt >= 36 && bt < 39.5) { const c = montageCut(bt); st = STYLE[c[1]]; a0 = c[0]; }
  else return;
  const col = light ? '#0B0B0D' : '#FFFFFF', a = inv(8, 8.5, bt);
  g.save(); g.globalAlpha = a;
  g.strokeStyle = rgba(col, .6); g.lineWidth = 2;
  const m = 40, L = 26;
  for (const [x, y, dx, dy] of [[m, m, 1, 1], [W - m, m, -1, 1], [m, H - m, 1, -1], [W - m, H - m, -1, -1]]) {
    g.beginPath(); g.moveTo(x, y + dy * L); g.lineTo(x, y); g.lineTo(x + dx * L, y); g.stroke();
  }
  label(g, 'VIBE EDITING  /  LOGO SYSTEM', 84, 90, col, .75, 16, 'left', 3);
  label(g, `STYLE ${String(st.idx + 1).padStart(2, '0')} / 13`, W - 84, 90, col, .75, 16, 'right', 3);
  const n = Math.ceil(inv(a0, a0 + .3, bt) * st.name.length);
  g.fillStyle = C.lime; g.fillRect(84, H - 104, 14, 14);
  if (light) { g.strokeStyle = '#0B0B0D'; g.lineWidth = 1.5; g.strokeRect(84, H - 104, 14, 14); }
  label(g, st.name.slice(0, n), 112, H - 90, col, .95, 22, 'left', 4);
  const tw = 30, gp = 8, x0 = W - 84 - 13 * (tw + gp) + gp;
  for (let i = 0; i < 13; i++) {
    g.fillStyle = i === st.idx ? (light ? '#0B0B0D' : C.lime) : rgba(col, i < st.idx ? .55 : .2);
    g.fillRect(x0 + i * (tw + gp), H - 100, tw, i === st.idx ? 8 : 4);
  }
  g.restore();
}

// ------------------------------------------------------------------ frame assembly
const S = mk(), A = mk();
function drawScene(g, t) {
  const bt = t / B, sc = sceneAt(bt), cam = camera(bt);
  reset(g);
  g.save(); applyCam(g, cam);
  const r = sc.fn(g, bt - sc.a, t);
  const light = typeof r === 'boolean' ? r : !!(sc.st && sc.st.light);
  g.restore();
  const tr = TRANS[sc.a];
  if (tr && bt - sc.a < TD) {
    const prev = sceneAt(sc.a - .001), P = PREV.g;
    reset(P); P.save(); applyCam(P, cam); prev.fn(P, bt - prev.a, t); P.restore();
    maskTrans(g, PREV, tr, (bt - sc.a) / TD);
  }
  reset(g);
  hud(g, bt, light);
  const fade = E.inQ(inv(47.05, 47.92, bt));
  if (fade > 0) { g.fillStyle = `rgba(0,0,0,${fade})`; g.fillRect(0, 0, W, H); }
}
function renderAt(t, samples = MB) {
  FRAME_KEY = t;
  const a = A.g;
  a.globalAlpha = 1; a.globalCompositeOperation = 'source-over';
  for (let i = 0; i < samples; i++) {
    const ts = samples > 1 ? t + ((i + .5) / samples - .5) * SHUTTER / FPS : t;
    drawScene(S.g, clamp(ts, 0, DUR - 1e-4));
    a.globalAlpha = 1 / (i + 1);
    a.drawImage(S, 0, 0);
  }
  a.globalAlpha = 1;
  const f = fx(t / B), gl = GL;
  gl.useProgram(POST.p); gl.viewport(0, 0, W, H);
  gl.bindTexture(gl.TEXTURE_2D, TEX);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, A);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.uniform1i(POST.U.tex, 0); gl.uniform2f(POST.U.res, W, H);
  gl.uniform1f(POST.U.ab, f.ab); gl.uniform1f(POST.U.glitch, f.glitch); gl.uniform1f(POST.U.grain, .05);
  gl.uniform1f(POST.U.vig, .42); gl.uniform1f(POST.U.bloom, f.bloom); gl.uniform1f(POST.U.flash, f.flash);
  gl.uniform1f(POST.U.invert, f.invert); gl.uniform1f(POST.U.seed, Math.floor(t * 60) * .137 % 97);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  gl.finish();
}

window.READY = (async () => {
  await Promise.all(Object.values(FONT).map(([fam, it]) => document.fonts.load(it + '100px "' + fam + '"')));
  for (const s of STYLES) s.init();
  initHero();
  STILLS = STYLES.map(s => { const c = mk(); reset(c.g); s.fn(c.g, 1.6, 9); return c; });
  return true;
})();
window.renderFrame = async (i) => { await window.READY; renderAt(i / FPS); return true; };
window.META = { W, H, FPS, DUR, BPM, FRAMES: Math.round(DUR * FPS) };

// ------------------------------------------------------------------ live preview
if (RENDER) document.body.classList.add('render');
else {
  const audio = new Audio('out/audio.wav');
  let playing = false, t0 = 0, start = 0;
  const now = () => playing ? (audio.readyState > 2 && !audio.paused ? audio.currentTime : (performance.now() - start) / 1000 + t0) : t0;
  const tick = () => {
    let t = now();
    if (t >= DUR) { t = 0; t0 = 0; playing = false; audio.pause(); }
    renderAt(t, 1);
    document.getElementById('bar').style.transform = `scaleX(${t / DUR})`;
    requestAnimationFrame(tick);
  };
  window.READY.then(() => requestAnimationFrame(tick));
  addEventListener('keydown', e => {
    if (e.code === 'Space') {
      if (playing) { t0 = now(); playing = false; audio.pause(); }
      else { playing = true; start = performance.now(); audio.currentTime = t0; audio.play().catch(() => {}); }
    }
    if (e.code === 'ArrowRight' || e.code === 'ArrowLeft') { t0 = clamp(now() + (e.code === 'ArrowRight' ? B * 4 : -B * 4), 0, DUR); start = performance.now(); audio.currentTime = t0; }
  });
}
