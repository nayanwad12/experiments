'use strict';
// VIBE EDITING: 30 s showreel. Every pixel is a pure function of time t.
// 128 BPM, so 30 s = 64 beats = 16 bars. All timing is written in beats (bt).

const W = 1920, H = 1080;
const BPM = 128, B = 60 / BPM, BEATS = 64, DUR = BEATS * B;
const Q = new URLSearchParams(location.search);
const RENDER = Q.has('render');
const FPS = +(Q.get('fps') || 60);
const MB = +(Q.get('mb') || (RENDER ? 6 : 1));   // motion-blur sub-frames
const SHUTTER = 0.5;                                // 180° shutter

const C = {
  ink: '#0B0B0D', paper: '#F2EEE3', lime: '#D4FF3F', orange: '#FF5A1F', blue: '#2B45FF',
  pink: '#FF5FA8', violet: '#7B5CFF', yellow: '#FFD02E', white: '#FFFFFF', red: '#FF2E4D',
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
  ioX: x => x <= 0 ? 0 : x >= 1 ? 1 : x < .5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2,
  outB: (x, s = 1.70158) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2),
  inB: (x, s = 1.70158) => (s + 1) * x * x * x - s * x * x,
  outEl: x => x <= 0 ? 0 : x >= 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - .75) * (TAU / 3)) + 1,
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
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
// CSS-style cubic-bezier easing, solved by bisection (robust for steep curves)
function bez(x1, y1, x2, y2) {
  const f = (a, b, t) => 3 * a * t * (1 - t) * (1 - t) + 3 * b * t * t * (1 - t) + t * t * t;
  return x => {
    let lo = 0, hi = 1, t = x;
    for (let i = 0; i < 24; i++) { t = (lo + hi) / 2; if (f(x1, x2, t) < x) lo = t; else hi = t; }
    return f(y1, y2, t);
  };
}
const bpt = (a, b, c, d, t) => { const m = 1 - t; return m * m * m * a + 3 * m * m * t * b + 3 * m * t * t * c + t * t * t * d; };
const pulseAt = (bt, at, dec) => bt >= at ? Math.exp(-(bt - at) / dec) : 0;

// ------------------------------------------------------------------ canvas helpers
function mk(w = W, h = H) { const c = document.createElement('canvas'); c.width = w; c.height = h; c.g = c.getContext('2d'); return c; }
const FONT = { U: 'Unbounded', A: 'Anton', S: 'Instrument Serif', M: 'JetBrains Mono', I: 'Inter Tight' };
function font(g, f, px, ls = 0) { g.font = (f === 'S' ? 'italic ' : '') + px + 'px "' + FONT[f] + '"'; g.letterSpacing = ls + 'px'; }
function bgFill(g, col) { g.fillStyle = col; g.fillRect(-W * 2, -H * 2, W * 5, H * 5); }
// per-letter x offsets (kerning-aware prefix measure)
function glyphs(g, s) {
  const out = []; const arr = [...s];
  for (let i = 0; i < arr.length; i++) {
    const x = g.measureText(arr.slice(0, i).join('')).width;
    const w = g.measureText(arr[i]).width;
    out.push({ c: arr[i], x, w });
  }
  return { list: out, w: g.measureText(s).width };
}
function rrect(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function withAlpha(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${n >> 8 & 255},${n & 255},${a})`; }
function dotGrid(g, step, a, col) {
  g.fillStyle = withAlpha(col, a);
  for (let y = step / 2; y < H; y += step) for (let x = step / 2; x < W; x += step) g.fillRect(x - 1.5, y - 1.5, 3, 3);
}
function diamond(g, x, y, s) { g.beginPath(); g.moveTo(x, y - s); g.lineTo(x + s, y); g.lineTo(x, y + s); g.lineTo(x - s, y); g.closePath(); }
function sparkle(g, x, y, r, rot) {
  g.beginPath();
  for (let i = 0; i < 8; i++) {
    const a = rot + i * Math.PI / 4, rr = i % 2 ? r * .28 : r;
    g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr);
  }
  g.closePath();
}
function shockwave(g, lb, col, x = W / 2, y = H / 2, maxR = 1500, dur = 1.3) {
  for (let k = 0; k < 2; k++) {
    const p = inv(k * .12, dur + k * .12, lb);
    if (p <= 0 || p >= 1) continue;
    g.strokeStyle = col; g.globalAlpha = (1 - p) * (k ? .5 : 1);
    g.lineWidth = lerp(k ? 20 : 70, 0, E.outQ(p));
    g.beginPath(); g.arc(x, y, 30 + E.outX(p) * maxR * (k ? .7 : 1), 0, TAU); g.stroke();
  }
  g.globalAlpha = 1;
}
function burst(g, lb, col, n = 90, seed = 1, x = W / 2, y = H / 2) {
  const p = inv(0, 1.6, lb);
  if (p <= 0 || p >= 1) return;
  g.strokeStyle = col; g.lineCap = 'round';
  for (let i = 0; i < n; i++) {
    const a = hash(i + seed) * TAU, sp = .25 + hash(i * 3.1 + seed) * .9;
    const d1 = 40 + E.outX(p) * sp * 1300, d0 = d1 - lerp(260, 10, E.outC(p)) * sp;
    g.globalAlpha = (1 - p) * .9;
    g.lineWidth = lerp(6, 1, p) * (.5 + hash(i + 9 + seed));
    g.beginPath(); g.moveTo(x + Math.cos(a) * d0, y + Math.sin(a) * d0); g.lineTo(x + Math.cos(a) * d1, y + Math.sin(a) * d1); g.stroke();
  }
  g.globalAlpha = 1;
}
function label(g, s, x, y, col, a = .8, px = 18, align = 'left') {
  font(g, 'M', px, 1); g.textAlign = align; g.textBaseline = 'alphabetic';
  g.fillStyle = withAlpha(col, a); g.fillText(s, x, y);
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

// ------------------------------------------------------------------ shared layout
let LOCK;  // VIBE / EDITING justified lockup metrics
let PTS;   // 3D point-cloud targets
const TMP = mk(), TMP2 = mk();

function init() {
  const g = TMP.g;
  const LW = 1240;
  font(g, 'U', 100); const wV = g.measureText('VIBE').width;
  font(g, 'U', 100); const wE = g.measureText('EDITING').width;
  const sV = 100 * LW / wV, sE = 100 * LW / wE;
  font(g, 'U', sV); const capV = g.measureText('VIBE').actualBoundingBoxAscent;
  font(g, 'U', sE); const capE = g.measureText('EDITING').actualBoundingBoxAscent;
  const gap = sE * .2, total = capV + gap + capE, top = H / 2 - total / 2;
  LOCK = { LW, sV, sE, capV, capE, baseV: top + capV, baseE: top + capV + gap + capE, x0: W / 2 - LW / 2 };
  buildPoints();
}

// ------------------------------------------------------------------ scene 01: EASE (intro)
const EASE_A = [1 / 3, 1 / 3, 2 / 3, 2 / 3], EASE_B = [0.86, 0.0, 0.14, 1.0];
function sIntro(g, lb) {
  bgFill(g, C.ink);
  const col = inv(7.3, 7.92, lb);
  const cs = 1 - E.inB(col, 2.2);
  g.save();
  g.translate(W / 2, H / 2); g.scale(cs, cs); g.translate(-W / 2, -H / 2);
  const gridA = .13 * E.outC(inv(.1, 1.2, lb));
  if (gridA > 0) dotGrid(g, 48, gridA, C.white);

  const hk = E.outEl(inv(2, 3.3, lb));
  const h = EASE_A.map((v, i) => lerp(v, EASE_B[i], hk));
  const ease = bez(...h);
  const GW = 820, GH = 470, GX = W / 2, GY = H / 2 - 10;
  const zp = E.ioC(inv(3.3, 6.4, lb));
  const z = lerp(1, 1.6, zp);
  g.save();
  g.translate(lerp(GX, W * .64, zp), lerp(GY, H * .52, zp)); g.scale(z, z); g.rotate(lerp(0, -.05, zp)); g.translate(-GX, -GY);
  const X = u => GX - GW / 2 + u * GW, Y = v => GY + GH / 2 - v * GH;
  const ga = E.outC(inv(.2, 1.1, lb));
  // grid inside the graph
  g.lineWidth = 1;
  g.strokeStyle = withAlpha(C.white, .07 * ga);
  for (let i = 1; i < 10; i++) {
    g.beginPath(); g.moveTo(X(i / 10), Y(0)); g.lineTo(X(i / 10), Y(0) - GH * ga); g.stroke();
    g.beginPath(); g.moveTo(X(0), Y(i / 10)); g.lineTo(X(0) + GW * ga, Y(i / 10)); g.stroke();
  }
  g.strokeStyle = withAlpha(C.white, .45); g.lineWidth = 2;
  g.beginPath(); g.moveTo(X(0), Y(0)); g.lineTo(X(ga), Y(0)); g.stroke();
  g.beginPath(); g.moveTo(X(0), Y(0)); g.lineTo(X(0), Y(ga)); g.stroke();
  if (ga > .5) {
    label(g, 'VALUE', X(0) - 14, Y(1) + 6, C.white, .45 * ga, 14, 'right');
    label(g, 'TIME →', X(1), Y(0) + 30, C.white, .45 * ga, 14, 'right');
  }
  // the curve
  const cp = E.ioC(inv(.6, 1.9, lb));
  if (cp > 0) {
    const path = () => {
      g.beginPath();
      for (let i = 0; i <= 160 * cp; i++) {
        const s = i / 160;
        const x = bpt(0, h[0], h[2], 1, s), y = bpt(0, h[1], h[3], 1, s);
        i ? g.lineTo(X(x), Y(y)) : g.moveTo(X(x), Y(y));
      }
    };
    g.lineCap = 'round'; g.lineJoin = 'round';
    path(); g.strokeStyle = withAlpha(C.lime, .16); g.lineWidth = 22; g.stroke();
    path(); g.strokeStyle = C.lime; g.lineWidth = 5; g.stroke();
  }
  // bezier handles
  const ha = E.outB(inv(1.5, 1.95, lb));
  if (ha > 0) {
    g.strokeStyle = withAlpha(C.white, .55); g.lineWidth = 2;
    for (const [ax, ay, bx, by] of [[0, 0, h[0], h[1]], [1, 1, h[2], h[3]]]) {
      g.beginPath(); g.moveTo(X(ax), Y(ay)); g.lineTo(X(lerp(ax, bx, ha)), Y(lerp(ay, by, ha))); g.stroke();
      g.fillStyle = C.ink; g.beginPath(); g.arc(X(lerp(ax, bx, ha)), Y(lerp(ay, by, ha)), 11 * ha, 0, TAU); g.fill(); g.stroke();
    }
    // grab cursor yanking handle 1
    const cu = inv(1.7, 3.2, lb);
    if (cu > 0 && cu < 1) {
      const hx = X(h[0]), hy = Y(h[1]);
      g.save(); g.translate(hx + 8, hy + 8); g.globalAlpha = Math.sin(cu * Math.PI);
      g.fillStyle = C.white; g.strokeStyle = C.ink; g.lineWidth = 2;
      g.beginPath(); g.moveTo(0, 0); g.lineTo(0, 30); g.lineTo(8, 23); g.lineTo(14, 36); g.lineTo(19, 33); g.lineTo(13, 21); g.lineTo(23, 21); g.closePath(); g.fill(); g.stroke();
      g.restore();
    }
  }
  // keyframes
  for (const [u, v, d] of [[0, 0, .3], [1, 1, .6]]) {
    const s = E.outB(inv(d, d + .4, lb));
    if (s <= 0) continue;
    g.fillStyle = C.lime; diamond(g, X(u), Y(v), 15 * s); g.fill();
  }
  // runner ball + trail
  if (lb > 1 && lb < 7.4) {
    const k = Math.floor((lb - 1) / 2), pr = clamp(fract((lb - 1) / 2) * 1.25);
    const track = Y(0) + 70;
    g.strokeStyle = withAlpha(C.white, .2); g.lineWidth = 2;
    g.beginPath(); g.moveTo(X(0), track); g.lineTo(X(1), track); g.stroke();
    for (let j = 10; j >= 0; j--) {
      const pj = clamp(pr - j * .018);
      const v = ease(pj), bx = X(k % 2 ? 1 - v : v);
      g.globalAlpha = j ? .09 * (1 - j / 11) : 1;
      g.fillStyle = C.lime; g.beginPath(); g.arc(bx, track, j ? 15 : 17, 0, TAU); g.fill();
      if (!j) {
        g.fillStyle = C.white; g.beginPath(); g.arc(X(pj), Y(v), 8, 0, TAU); g.fill();
        g.strokeStyle = withAlpha(C.white, .25); g.setLineDash([4, 6]);
        g.beginPath(); g.moveTo(X(pj), Y(v)); g.lineTo(X(pj), Y(0)); g.stroke(); g.setLineDash([]);
      }
    }
    g.globalAlpha = 1;
  }
  if (ga > .3) {
    const f = n => n.toFixed(2);
    label(g, `cubic-bezier(${f(h[0])}, ${f(h[1])}, ${f(h[2])}, ${f(h[3])})`, X(0), Y(1) - 28, C.lime, .95 * ga, 20);
    label(g, `FRAME ${String(Math.floor(lb * B * 30)).padStart(4, '0')}`, X(1), Y(1) - 28, C.white, .5 * ga, 16, 'right');
  }
  g.restore();

  // serif statement
  const lines = [['every frame', 4.0, 330], ['is a decision.', 4.9, 470]];
  for (const [s, at, y] of lines) {
    if (lb < at) continue;
    font(g, 'S', 150); g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    const gl = glyphs(g, s);
    for (let i = 0; i < gl.list.length; i++) {
      const p = inv(at + i * .035, at + i * .035 + .55, lb);
      if (p <= 0) continue;
      const q = E.outX(p);
      g.save();
      g.globalAlpha = clamp(p * 2.5);
      g.filter = q < .98 ? `blur(${(1 - q) * 14}px)` : 'none';
      g.fillStyle = C.white;
      g.fillText(gl.list[i].c, 140 + gl.list[i].x, y + (1 - q) * 60);
      g.restore();
    }
  }
  g.restore();
  // everything collapses into a single dot
  if (col > .55) {
    const s = E.outB(inv(.55, .8, col));
    g.fillStyle = C.lime; g.beginPath(); g.arc(W / 2, H / 2, 14 * s, 0, TAU); g.fill();
  }
  return false;
}

// ------------------------------------------------------------------ scene 02: TITLE
function drawLockup(g, lb, fill, opts = {}) {
  const L = LOCK;
  g.textBaseline = 'alphabetic'; g.textAlign = 'left';
  font(g, 'U', L.sV);
  let gl = glyphs(g, 'VIBE');
  for (let i = 0; i < gl.list.length; i++) {
    const p = opts.static ? 1 : inv(i * .07, i * .07 + .55, lb);
    if (p <= 0) continue;
    const q = E.outX(p), s = lerp(3.4, 1, q);
    const cx = L.x0 + gl.list[i].x + gl.list[i].w / 2, cy = L.baseV - L.capV / 2;
    g.save(); g.translate(cx, cy); g.scale(s, s); g.rotate((1 - q) * (i % 2 ? .3 : -.3)); g.translate(-cx, -cy);
    g.globalAlpha = clamp(p * 4);
    if (opts.stroke) { g.strokeStyle = fill; g.lineWidth = opts.stroke; g.strokeText(gl.list[i].c, L.x0 + gl.list[i].x, L.baseV); }
    else { g.fillStyle = fill; g.fillText(gl.list[i].c, L.x0 + gl.list[i].x, L.baseV); }
    g.restore();
  }
  font(g, 'U', L.sE);
  gl = glyphs(g, 'EDITING');
  g.save();
  g.beginPath(); g.rect(-W, L.baseE - L.capE - 6, W * 3, L.capE + 30); g.clip();
  for (let i = 0; i < gl.list.length; i++) {
    const p = opts.static ? 1 : inv(.9 + i * .05, 1.5 + i * .05, lb);
    if (p <= 0) continue;
    const q = E.outX(p);
    if (opts.stroke) { g.strokeStyle = fill; g.lineWidth = opts.stroke; g.strokeText(gl.list[i].c, L.x0 + gl.list[i].x, L.baseE + (1 - q) * L.capE * 1.2); }
    else { g.fillStyle = fill; g.fillText(gl.list[i].c, L.x0 + gl.list[i].x, L.baseE + (1 - q) * L.capE * 1.2); }
  }
  g.restore();
}
function chipTag(g, s, x, y, col, bg, sc) {
  if (sc <= 0) return;
  font(g, 'M', 20, 2); const w = g.measureText(s).width + 32;
  g.save(); g.translate(x, y); g.scale(sc, sc);
  rrect(g, -w / 2, -20, w, 40, 20); g.fillStyle = bg; g.fill(); g.strokeStyle = col; g.lineWidth = 2; g.stroke();
  g.fillStyle = col; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(s, 0, 1);
  g.restore();
}
function sTitle(g, lb) {
  let bg = C.ink, fg = C.lime;
  if (lb >= 2 && lb < 4 && Math.floor(lb * 2) % 2 === 0) { bg = C.lime; fg = C.ink; }
  bgFill(g, bg);
  if (lb < 2) { shockwave(g, lb, fg); burst(g, lb, fg, 90, 3); }
  const L = LOCK;
  const zt = inv(6, 8, lb);
  const camZ = E.inQ(zt) * 4.4;
  // depth echoes (text tunnel)
  const echoA = E.outC(inv(4, 4.6, lb));
  if (echoA > 0) {
    for (let k = 7; k >= 1; k--) {
      const d = k * .62 - camZ + 1;
      if (d < .07) continue;
      const s = 1 / d;
      const a = echoA * clamp((12 - s) / 6) * clamp(1.2 - (k * .62) / 5);
      if (a <= 0) continue;
      g.save(); g.globalAlpha = a;
      g.translate(W / 2, H / 2); g.scale(s, s); g.translate(-W / 2, -H / 2);
      drawLockup(g, 99, k % 2 ? fg : C.white, { static: 1, stroke: 2.5 / s });
      g.restore();
    }
  }
  // main layer
  const d0 = 1 - camZ;
  if (d0 > .07) {
    const s0 = 1 / d0;
    g.save(); g.globalAlpha = clamp((14 - s0) / 7);
    g.translate(W / 2, H / 2); g.scale(s0, s0); g.translate(-W / 2, -H / 2);
    if (lb >= 4 && lb < 6) {
      // snap-slice: each beat, slices jump sideways then settle
      const T = TMP.g; T.setTransform(1, 0, 0, 1, 0, 0); T.clearRect(0, 0, W, H);
      drawLockup(T, lb, fg, { static: 1 });
      const bi = Math.floor(lb), settle = 1 - E.outX(inv(0, .7, fract(lb)));
      const top = L.baseV - L.capV - 20, hh = L.baseE + 20 - top, n = 12;
      for (let j = 0; j < n; j++) {
        const y0 = top + hh * j / n, sh = (hash(j * 3.7 + bi * 17) - .5) * 2 * 150 * settle;
        g.drawImage(TMP, 0, y0, W, hh / n + 1, sh, y0, W, hh / n + 1);
      }
    } else drawLockup(g, lb, fg, { static: lb > 4 });
    g.restore();
  }
  // annotation chips
  if (lb > 2 && lb < 6.4) {
    const out = 1 - E.inC(inv(5.9, 6.3, lb));
    const tags = [['SHOWREEL', L.x0 + 110, L.baseV - L.capV - 70, 2], ['2026', L.x0 + L.LW - 70, L.baseV - L.capV - 70, 2.5],
      ['MOTION × AI', L.x0 + 150, L.baseE + 75, 3], ['30 SEC', L.x0 + L.LW - 90, L.baseE + 75, 3.5]];
    for (const [s, x, y, at] of tags) chipTag(g, s, x, y, fg, bg, E.outB(inv(at, at + .3, lb)) * out);
  }
  return bg === C.lime;
}

// ------------------------------------------------------------------ scene 03: KINETIC TYPE
function sKinetic(g, lb, t) {
  const k = Math.floor(lb), sb = lb - k;
  if (k === 0) { // MOTION: slot-machine rolling letters
    bgFill(g, C.orange);
    font(g, 'A', 560); g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    const gl = glyphs(g, 'MOTION'), x0 = W / 2 - gl.w / 2, base = H / 2 + 200, lh = 600;
    const pool = 'KEYFRAMOTIN';
    for (let i = 0; i < gl.list.length; i++) {
      const p = E.outX(inv(i * .05, i * .05 + .7, sb));
      const off = (1 - p) * 6 * lh;
      g.save(); g.beginPath(); g.rect(x0 + gl.list[i].x - 4, base - 470, gl.list[i].w + 8, 520); g.clip();
      g.fillStyle = C.ink;
      for (let j = 0; j <= 6; j++) {
        const y = base - (6 - j) * lh + off;
        if (y < base - 520 || y > base + lh) continue;
        g.fillText(j === 6 ? gl.list[i].c : pool[Math.floor(hash(i * 7 + j) * pool.length)], x0 + gl.list[i].x, y);
      }
      g.restore();
    }
    g.fillStyle = C.ink; g.fillRect(x0, base + 40, gl.w * E.outX(inv(.45, .95, sb)), 14);
    label(g, 'A — ROLL / STAGGER 0.05', x0, base + 100, C.ink, .8, 20);
    return false;
  }
  if (k === 1) { // TYPE: counter-scrolling marquee wall
    bgFill(g, C.ink);
    font(g, 'A', 150, 4); g.textBaseline = 'middle'; g.textAlign = 'left';
    const unit = g.measureText('TYPE — ').width;
    for (let r = 0; r < 8; r++) {
      const y = 70 + r * 135, dir = r % 2 ? 1 : -1;
      const x = ((dir * (sb * 1100 + r * 180)) % unit + unit) % unit - unit;
      const hot = r === 4;
      const s = 'TYPE — '.repeat(6);
      if (hot) { g.fillStyle = C.lime; g.fillText(s, x, y); }
      else { g.strokeStyle = withAlpha(C.white, .5); g.lineWidth = 2; g.strokeText(s, x, y); }
    }
    return false;
  }
  if (k === 2) { // TIMING: bounce physics
    bgFill(g, C.paper);
    font(g, 'U', 230); g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    const gl = glyphs(g, 'TIMING'), x0 = W / 2 - gl.w / 2, base = H / 2 + 110;
    for (let i = 0; i < gl.list.length; i++) {
      const p = inv(i * .035, i * .035 + .62, sb), b = E.outBounce(p);
      const y = base - (1 - b) * 900;
      const cx = x0 + gl.list[i].x + gl.list[i].w / 2;
      const hgt = clamp((base - y) / 500);
      g.fillStyle = withAlpha(C.ink, .18 * (1 - hgt));
      g.beginPath(); g.ellipse(cx, base + 30, gl.list[i].w * .45 * (1 - hgt * .6), 12 * (1 - hgt * .6), 0, 0, TAU); g.fill();
      const land = 1 - clamp((base - y) / 40);
      g.save(); g.translate(cx, base); g.scale(1 + land * .06 * Math.sin(p * 40), 1 - land * .06 * Math.sin(p * 40)); g.translate(-cx, -base);
      g.fillStyle = i === 3 ? C.blue : C.ink; g.fillText(gl.list[i].c, x0 + gl.list[i].x, y);
      g.restore();
    }
    // mini graph editor showing the bounce
    const gx = 140, gy = H - 190, gw = 260, gh = 110;
    g.strokeStyle = withAlpha(C.ink, .25); g.lineWidth = 1.5; g.strokeRect(gx, gy - gh, gw, gh);
    g.strokeStyle = C.blue; g.lineWidth = 3; g.beginPath();
    for (let i = 0; i <= 80; i++) { const u = i / 80; g.lineTo(gx + u * gw, gy - E.outBounce(u) * gh); }
    g.stroke();
    const u = inv(0, .62, sb);
    g.fillStyle = C.ink; g.beginPath(); g.arc(gx + u * gw, gy - E.outBounce(u) * gh, 6, 0, TAU); g.fill();
    label(g, 'ease: outBounce', gx, gy + 30, C.ink, .7, 16);
    return true;
  }
  if (k === 3) { // FEEL: soft serif
    bgFill(g, C.blue);
    const rg = g.createRadialGradient(W / 2 + Math.sin(t * 2) * 200, H / 2, 0, W / 2, H / 2, 900);
    rg.addColorStop(0, withAlpha(C.pink, .8)); rg.addColorStop(1, withAlpha(C.pink, 0));
    g.fillStyle = rg; g.fillRect(0, 0, W, H);
    font(g, 'S', 640); g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    const gl = glyphs(g, 'feel'), x0 = W / 2 - gl.w / 2, base = H / 2 + 200;
    for (let i = 0; i < gl.list.length; i++) {
      const p = inv(i * .08, i * .08 + .6, sb), q = E.outC(p);
      if (p <= 0) continue;
      g.save(); g.globalAlpha = q; g.filter = q < .98 ? `blur(${(1 - q) * 30}px)` : 'none';
      g.fillStyle = C.paper;
      g.fillText(gl.list[i].c, x0 + gl.list[i].x, base + (1 - q) * 50 + Math.sin(t * 3 + i) * 8);
      g.restore();
    }
    return false;
  }
  if (k < 6) { // IT'S NOT THE SOFTWARE
    bgFill(g, C.ink);
    const words = [["IT'S", 4, 150, 300], ['NOT', 4.5, 250, 540], ['THE', 5, 150, 700], ['SOFTWARE.', 5.5, 230, 920]];
    for (const [s, at, px, y] of words) {
      if (lb < at) continue;
      const q = E.outX(inv(at, at + .3, lb));
      font(g, 'I', px, -2); g.textAlign = 'left'; g.textBaseline = 'alphabetic';
      g.save(); g.translate(150, y); g.scale(lerp(1.12, 1, q), lerp(1.12, 1, q));
      g.fillStyle = s === 'NOT' ? C.lime : C.white; g.fillText(s, 0, (1 - q) * 30);
      g.restore();
      if (s === 'SOFTWARE.') {
        const w = g.measureText(s).width, st = E.outX(inv(5.8, 6, lb));
        g.fillStyle = C.red; g.fillRect(140, y - px * .36, (w + 20) * st, 22);
      }
    }
    label(g, 'TRACKING −2 / LEADING 0.9', W - 150, H - 150, C.white, .5, 18, 'right');
    return false;
  }
  // IT'S THE VIBE.
  bgFill(g, C.lime);
  font(g, 'I', 120, -1); g.textAlign = 'left'; g.textBaseline = 'alphabetic';
  const q0 = E.outX(inv(6, 6.3, lb));
  g.fillStyle = C.ink; g.fillText("IT'S THE", 150, 250 + (1 - q0) * 40);
  if (lb >= 6.5) {
    font(g, 'U', 430); const gl = glyphs(g, 'VIBE.');
    const x0 = W / 2 - gl.w / 2, base = 820;
    for (let i = 0; i < gl.list.length; i++) {
      const p = inv(6.5 + i * .05, 6.5 + i * .05 + .4, lb), q = E.outB(p, 2.2);
      if (p <= 0) continue;
      const cx = x0 + gl.list[i].x + gl.list[i].w / 2;
      g.save(); g.translate(cx, base); g.scale(1, q); g.rotate(Math.sin(t * 40 + i) * .012 * (1 - inv(7, 7.5, lb))); g.translate(-cx, -base);
      g.fillStyle = C.ink; g.fillText(gl.list[i].c, x0 + gl.list[i].x, base);
      g.restore();
    }
  }
  // circle wipe into the shapes scene
  const wp = E.inC(inv(7.45, 8, lb));
  if (wp > 0) { g.fillStyle = C.paper; g.beginPath(); g.arc(W / 2, H / 2, wp * 1150, 0, TAU); g.fill(); }
  return true;
}

// ------------------------------------------------------------------ scene 04: SHAPE LANGUAGE
const SH_COLS = [C.orange, C.blue, C.yellow, C.ink, C.pink];
function shapeR(type, a) {  // polar radius for morphing primitives
  const n = [
    () => 1,
    () => .88 / Math.max(Math.abs(Math.cos(a)), Math.abs(Math.sin(a))),
    () => { const s = TAU / 3; const m = ((a + Math.PI / 2) % s + s) % s - s / 2; return .62 / Math.cos(m); },
    () => .78 + .32 * Math.cos(5 * a) ** 3,
    () => .85 + .15 * Math.cos(8 * a),
  ];
  return n[type]();
}
function morphPath(g, x, y, R, fromT, toT, p, rot) {
  g.beginPath();
  for (let i = 0; i <= 180; i++) {
    const a = i / 180 * TAU;
    const r = R * lerp(shapeR(fromT, a - rot), shapeR(toT, a - rot), p);
    g.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
  }
  g.closePath();
}
function cellShape(g, type, s, col) {
  g.fillStyle = col; g.beginPath();
  if (type === 0) g.arc(0, 0, s / 2, 0, TAU);
  else if (type === 1) g.rect(-s / 2, -s / 2, s, s);
  else if (type === 2) { g.moveTo(-s / 2, -s / 2); g.arc(-s / 2, -s / 2, s, 0, Math.PI / 2); g.closePath(); }
  else if (type === 3) { g.arc(0, s / 2, s / 2, Math.PI, 0); g.closePath(); }
  else { g.moveTo(-s / 2, s / 2); g.lineTo(s / 2, s / 2); g.lineTo(-s / 2, -s / 2); g.closePath(); }
  g.fill();
}
function sShapes(g, lb, t) {
  bgFill(g, C.paper);
  const cols = 12, rows = 7, cs = 150, ox = (W - cols * cs) / 2 + cs / 2, oy = (H - rows * cs) / 2 + cs / 2;
  const origins = [[W / 2, H / 2], [0, 0], [W, H], [W, 0], [0, H]];
  if (lb < 6.2) {
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const i = r * cols + c, x = ox + c * cs, y = oy + r * cs;
      const type = Math.floor(hash(i * 1.3) * 5);
      let rot = Math.floor(hash(i * 2.9) * 4) * Math.PI / 2, sc = 0, colI = Math.floor(hash(i * 4.1) * 4);
      const d0 = Math.hypot(x - W / 2, y - H / 2) / 1100;
      sc = E.outB(inv(d0 * .6, d0 * .6 + .45, lb));
      for (let k = 1; k <= 4; k++) {
        const [px, py] = origins[k];
        const d = Math.hypot(x - px, y - py) / 2200;
        const p = inv(k + d * .7, k + d * .7 + .45, lb);
        rot += E.outB(p) * Math.PI / 2 * (k % 2 ? 1 : -1);
        sc *= 1 - .35 * Math.sin(Math.PI * p);
        if (p >= .5) colI++;
      }
      const out = E.inB(inv(4.6 + (1 - d0) * .5, 5.4 + (1 - d0) * .5, lb));
      sc *= 1 - out;
      if (sc <= .01) continue;
      g.save(); g.translate(x + (x - W / 2) * out * .6, y + (y - H / 2) * out * .6); g.rotate(rot); g.scale(sc, sc);
      cellShape(g, type, 118, SH_COLS[colI % 4]);
      g.restore();
    }
  }
  // hero morph with colour echoes
  if (lb > 4.4) {
    const grow = E.outB(inv(4.4, 5.0, lb));
    const seq = [0, 1, 2, 3, 4, 0];
    for (let e = 4; e >= 0; e--) {
      const lt = lb - e * .07;
      const mi = clamp(Math.floor((lt - 4.8) * 2), 0, seq.length - 2);
      const mp = E.ioX(inv(0, .38, (lt - 4.8) * 2 - mi));
      const shrink = E.ioC(inv(6.2, 7.2, lt));
      const R = 280 * grow * lerp(1, .55, shrink);
      const rot = lt * 1.1 + Math.floor(Math.max(0, lt - 4.8) * 2) * .5;
      const from = lt < 4.8 ? 0 : seq[mi], to = lt < 4.8 ? 0 : seq[mi + 1];
      morphPath(g, W / 2, H / 2, R, shrink > .6 ? 0 : from, shrink > .6 ? 0 : to, shrink > .6 ? 1 : mp, rot);
      g.fillStyle = [C.ink, C.blue, C.orange, C.yellow, C.pink][e];
      g.globalAlpha = e ? .9 : 1;
      g.fill();
    }
    g.globalAlpha = 1;
  }
  label(g, 'SHAPE LANGUAGE — GRID 12×7', 90, 140, C.ink, lb < 4.6 ? 0 : .7, 18);
  // portal: the circle opens onto the liquid world
  const pp = E.inX(inv(7.35, 8, lb));
  if (pp > 0) {
    const R = lerp(154, 1200, pp);
    g.save(); g.beginPath(); g.arc(W / 2, H / 2, R, 0, TAU); g.clip();
    g.drawImage(shader('liquid', { time: (24 + lb) * B }), 0, 0, W, H);
    g.restore();
  }
  return true;
}

// ------------------------------------------------------------------ scene 05: LIQUID
function blobs(lb) {
  const out = [];
  const gather = lb < 5 ? 0 : (Math.floor(lb) % 2 ? E.outEl(inv(0, .9, fract(lb))) : 1 - E.outEl(inv(0, .9, fract(lb))));
  for (let i = 0; i < 7; i++) {
    const a = i / 7 * TAU + lb * .6;
    const orbit = lerp(.36, .12, gather) * (i === 0 ? 0 : 1);
    const x = W / H / 2 + Math.cos(a) * orbit * 1.4 + Math.sin(lb * 1.3 + i) * .03;
    const y = .5 + Math.sin(a) * orbit + Math.cos(lb * 1.1 + i * 2) * .03;
    const r = (i === 0 ? .15 : .088) * E.outB(inv(4 + i * .06, 4.5 + i * .06, lb));
    out.push(x, y, r);
  }
  return out;
}
function sLiquid(g, lb, t) {
  const pulse = pulseAt(lb, Math.floor(lb), .4);
  if (lb < 4) {
    const L = shader('liquid', { time: t, pulse });
    if (lb < 2) {
      g.drawImage(L, 0, 0, W, H);
      font(g, 'U', 420); g.textAlign = 'left'; g.textBaseline = 'alphabetic';
      const gl = glyphs(g, 'FLOW'), x0 = W / 2 - gl.w / 2;
      for (let i = 0; i < gl.list.length; i++) {
        const q = E.outX(inv(i * .06, i * .06 + .6, lb));
        g.fillStyle = C.ink;
        g.save(); g.translate(x0 + gl.list[i].x + gl.list[i].w / 2, H / 2 + 150);
        g.rotate(Math.sin(t * 3 + i * .9) * .05);
        g.fillText(gl.list[i].c, -gl.list[i].w / 2, (1 - q) * 500 + Math.sin(t * 4 + i * .8) * 26);
        g.restore();
      }
      label(g, 'DOMAIN-WARPED FBM / 4 OCTAVES', 90, 140, C.ink, .8, 18);
      return true;
    }
    // knockout: liquid only lives inside the letters
    const T = TMP.g; T.setTransform(1, 0, 0, 1, 0, 0); T.globalCompositeOperation = 'source-over';
    T.clearRect(0, 0, W, H); T.drawImage(L, 0, 0, W, H);
    T.globalCompositeOperation = 'destination-in';
    const s = lerp(1, 1.18, E.ioC(inv(2, 4, lb)));
    font(T, 'U', 520 * s); T.textAlign = 'center'; T.textBaseline = 'middle'; T.fillStyle = '#fff';
    T.fillText('FLOW', W / 2, H / 2 + 20);
    T.globalCompositeOperation = 'source-over';
    bgFill(g, C.ink);
    g.drawImage(TMP, 0, 0);
    font(g, 'U', 520 * s); g.textAlign = 'center'; g.textBaseline = 'middle';
    g.strokeStyle = withAlpha(C.white, .25); g.lineWidth = 2; g.strokeText('FLOW', W / 2, H / 2 + 20);
    label(g, 'KNOCKOUT / TRACK MATTE', 90, 140, C.white, .7, 18);
    return false;
  }
  bgFill(g, C.ink);
  font(g, 'U', 360); g.textAlign = 'center'; g.textBaseline = 'middle';
  g.strokeStyle = withAlpha(C.white, .14); g.lineWidth = 2;
  g.strokeText('LIQUID', W / 2, H / 2 + 10);
  const M = shader('blobs', { time: t, mode: 1, balls: blobs(lb), hue: .1 });
  g.globalCompositeOperation = 'lighter';
  g.drawImage(M, 0, 0, W, H);
  g.globalCompositeOperation = 'source-over';
  label(g, 'METABALLS × 7 / IRIDESCENT', 90, 140, C.white, .7, 18);
  return false;
}

// ------------------------------------------------------------------ scene 06: DEPTH (3D point cloud)
const NP = 2166;
function buildPoints() {
  const R = rng(7), sh = [];
  const P = () => new Float32Array(NP * 3);
  // 0 scatter
  let a = P(); for (let i = 0; i < NP; i++) { a[i * 3] = (R() - .5) * 14; a[i * 3 + 1] = (R() - .5) * 9; a[i * 3 + 2] = -3 + R() * 10; } sh.push(a);
  // 1 sphere (fibonacci)
  a = P(); for (let i = 0; i < NP; i++) { const y = 1 - 2 * (i + .5) / NP, r = Math.sqrt(1 - y * y), th = i * 2.39996; a[i * 3] = Math.cos(th) * r * 1.1; a[i * 3 + 1] = y * 1.1; a[i * 3 + 2] = Math.sin(th) * r * 1.1; } sh.push(a);
  // 2 torus
  a = P(); for (let i = 0; i < NP; i++) { const u = (i % 57) / 57 * TAU, v = Math.floor(i / 57) / 38 * TAU; a[i * 3] = (1 + .38 * Math.cos(v)) * Math.cos(u); a[i * 3 + 1] = .38 * Math.sin(v); a[i * 3 + 2] = (1 + .38 * Math.cos(v)) * Math.sin(u); } sh.push(a);
  // 3 cube lattice (6 faces × 19 × 19)
  a = P(); for (let i = 0; i < NP; i++) { const f = Math.floor(i / 361), j = i % 361, u = (j % 19) / 18 * 2 - 1, v = Math.floor(j / 19) / 18 * 2 - 1; const p = [[u, v, 1], [u, v, -1], [u, 1, v], [u, -1, v], [1, u, v], [-1, u, v]][f]; a[i * 3] = p[0] * .82; a[i * 3 + 1] = p[1] * .82; a[i * 3 + 2] = p[2] * .82; } sh.push(a);
  // 4 torus knot (2,3)
  a = P(); for (let i = 0; i < NP; i++) { const tt = i / NP * TAU, r = Math.cos(3 * tt) + 2, ang = R() * TAU, rad = .14 * Math.sqrt(R()); a[i * 3] = r * Math.cos(2 * tt) * .42 + Math.cos(ang) * rad; a[i * 3 + 1] = -Math.sin(3 * tt) * .42 + Math.sin(ang) * rad; a[i * 3 + 2] = r * Math.sin(2 * tt) * .42 + Math.cos(ang * 1.7) * rad; } sh.push(a);
  // 5 wave plane (animated in draw)
  a = P(); for (let i = 0; i < NP; i++) { a[i * 3] = ((i % 57) / 56 - .5) * 3.4; a[i * 3 + 1] = 0; a[i * 3 + 2] = (Math.floor(i / 57) / 37 - .5) * 2.4; } sh.push(a);
  // 6 double helix
  a = P(); for (let i = 0; i < NP; i++) { const s = i % 3, u = (i / NP) * 2 - 1, th = u * 9; if (s < 2) { const o = s * Math.PI; a[i * 3] = Math.cos(th + o) * .55; a[i * 3 + 2] = Math.sin(th + o) * .55; } else { const k = R() * 2 - 1; a[i * 3] = Math.cos(th) * .55 * k; a[i * 3 + 2] = Math.sin(th) * .55 * k; } a[i * 3 + 1] = u * 1.4; } sh.push(a);
  // 7 "3D" text sampled from glyph pixels
  const c = mk(1000, 600), g = c.g; font(g, 'U', 430); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#fff'; g.fillText('3D', 500, 320);
  const d = g.getImageData(0, 0, 1000, 600).data, cand = [];
  for (let y = 0; y < 600; y += 3) for (let x = 0; x < 1000; x += 3) if (d[(y * 1000 + x) * 4 + 3] > 128) cand.push([x, y]);
  a = P(); for (let i = 0; i < NP; i++) { const [x, y] = cand[Math.floor(R() * cand.length)]; a[i * 3] = (x - 500) / 330; a[i * 3 + 1] = (y - 300) / 330; a[i * 3 + 2] = (R() - .5) * .25; } sh.push(a);
  // 8 explode past the camera
  a = P(); for (let i = 0; i < NP; i++) { const b = sh[1]; a[i * 3] = b[i * 3] * 7; a[i * 3 + 1] = b[i * 3 + 1] * 7; a[i * 3 + 2] = b[i * 3 + 2] * 7 - 2; } sh.push(a);
  PTS = sh;
}
const PCOL = [C.lime, C.white, C.pink, C.blue];
function sDepth(g, lb, t) {
  bgFill(g, '#07070C');
  const rg = g.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, 1000);
  rg.addColorStop(0, 'rgba(43,69,255,.28)'); rg.addColorStop(1, 'rgba(43,69,255,0)');
  g.fillStyle = rg; g.fillRect(0, 0, W, H);
  const F = 1050, D = 3.4, cx = W / 2, cy = H / 2;
  // tunnel rings rushing toward camera
  g.lineWidth = 1.5;
  for (let k = 0; k < 16; k++) {
    const z = ((k * .6 - lb * 1.3) % 9.6 + 9.6) % 9.6 - 2.6;
    const s = F / (z + D);
    if (s <= 0 || z + D < .3) continue;
    g.strokeStyle = withAlpha(C.white, clamp(.18 - (z + 2.6) / 60) * clamp((z + D - .3) * 2));
    g.beginPath(); g.arc(cx, cy, 2.6 * s, 0, TAU); g.stroke();
  }
  // morph between point targets, one per beat
  const k = clamp(Math.floor(lb), 0, 7);
  const spin = [0, 1, 2, 3, 4, 5, 6, 7].reduce((acc, j) => acc + E.outX(inv(j, j + .8, lb)) * .9, 0);
  const yaw = lb * .45 + spin, pitch = .38 + Math.sin(lb * .5) * .2, roll = Math.sin(lb * .7) * .08;
  const cyw = Math.cos(yaw), syw = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch), cr = Math.cos(roll), sr = Math.sin(roll);
  const A = PTS[k], Bp = PTS[k + 1];
  g.globalCompositeOperation = 'lighter';
  const buckets = [[], [], [], []];
  const textFace = k === 6 ? E.ioC(inv(6, 6.5, lb)) * (1 - inv(6.9, 7.1, lb)) : 0;
  for (let i = 0; i < NP; i++) {
    const del = hash(i * .37) * .25;
    const p = E.ioX(inv(k + del, k + del + .62, lb));
    let x = lerp(A[i * 3], Bp[i * 3], p), y = lerp(A[i * 3 + 1], Bp[i * 3 + 1], p), z = lerp(A[i * 3 + 2], Bp[i * 3 + 2], p);
    const wave = (k === 4 ? p : k === 5 ? 1 - p : 0);
    if (wave > 0) y += Math.sin(x * 2.6 + t * 4) * Math.cos(z * 2.4 + t * 3) * .32 * wave;
    // rotate (the "3D" text faces camera)
    let yw = lerp(yaw, 0, textFace), pt = lerp(pitch, 0, textFace);
    let X = x * Math.cos(yw) + z * Math.sin(yw), Z = -x * Math.sin(yw) + z * Math.cos(yw);
    let Y = y * Math.cos(pt) - Z * Math.sin(pt); Z = y * Math.sin(pt) + Z * Math.cos(pt);
    const X2 = X * cr - Y * sr, Y2 = X * sr + Y * cr;
    if (Z + D < .15) continue;
    const s = F / (Z + D);
    const sx = cx + X2 * s, sy = cy + Y2 * s;
    if (sx < -50 || sx > W + 50 || sy < -50 || sy > H + 50) continue;
    const bi = Z < -.5 ? 0 : Z < .2 ? 1 : Z < .8 ? 2 : 3;
    buckets[bi].push(sx, sy, Math.max(1.2, 2.6 * s / 310));
  }
  for (let b = 0; b < 4; b++) {
    g.fillStyle = PCOL[b]; g.globalAlpha = [1, .75, .7, .55][b];
    const L = buckets[b];
    g.beginPath();
    for (let i = 0; i < L.length; i += 3) { g.moveTo(L[i] + L[i + 2], L[i + 1]); g.arc(L[i], L[i + 1], L[i + 2], 0, TAU); }
    g.fill();
  }
  g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
  // axis gizmo
  const gx = 150, gy = 880;
  for (const [vx, vy, vz, col, nm] of [[1, 0, 0, C.red, 'X'], [0, -1, 0, C.lime, 'Y'], [0, 0, 1, C.blue, 'Z']]) {
    const X = vx * cyw + vz * syw, Z = -vx * syw + vz * cyw, Y = vy * cp - Z * sp;
    g.strokeStyle = col; g.lineWidth = 3; g.beginPath(); g.moveTo(gx, gy); g.lineTo(gx + X * 55, gy + Y * 55); g.stroke();
    label(g, nm, gx + X * 70, gy + Y * 70 + 6, col, 1, 16, 'center');
  }
  const names = ['SPHERE', 'TORUS', 'LATTICE', 'KNOT', 'WAVE', 'HELIX', 'TYPE', 'EXPLODE'];
  label(g, `POINTS ${NP}  ·  FOV 42°  ·  ${names[k]}`, 90, 140, C.white, .7, 18);
  return false;
}

// ------------------------------------------------------------------ scene 07: GLITCH
function sGlitch(g, lb, t) {
  bgFill(g, C.ink);
  const T = TMP.g; T.setTransform(1, 0, 0, 1, 0, 0); T.clearRect(0, 0, W, H);
  const step = Math.floor(t * 20);
  const jit = n => (hash(step * 13.1 + n) - .5);
  T.globalCompositeOperation = 'lighter';
  const rgb = ['#FF0000', '#00FF00', '#0000FF'];
  const drawRGB = (s, f, px, x, y, amp) => {
    font(T, f, px); T.textAlign = 'center'; T.textBaseline = 'middle';
    for (let c = 0; c < 3; c++) { T.fillStyle = rgb[c]; T.fillText(s, x + (c - 1) * amp + jit(c) * amp, y + jit(c + 5) * amp * .4); }
  };
  if (lb < 2) {
    drawRGB('BORING', 'U', 300, W / 2, H / 2 - (lb >= 1 ? 90 : 0), 18);
    if (lb >= 1) drawRGB('NOT FOUND', 'M', 120, W / 2, H / 2 + 160, 10);
  } else {
    drawRGB('404', 'U', 620, W / 2, H / 2 - 20, 26);
  }
  T.globalCompositeOperation = 'source-over';
  if (lb >= 1 && lb < 2) {
    font(T, 'U', 300); const w = T.measureText('BORING').width * E.outX(inv(1, 1.2, lb));
    T.fillStyle = C.lime; T.fillRect(W / 2 - w / 2 - 20, H / 2 - 110, w + 40, 26);
  }
  // slice displacement
  const n = 18;
  for (let j = 0; j < n; j++) {
    const y0 = j * H / n, sh = hash(step * 3.3 + j) < .35 ? jit(j * 7) * 260 : 0;
    g.drawImage(TMP, 0, y0, W, H / n + 1, sh, y0, W, H / n + 1);
  }
  // pixel-sort streaks
  for (let k = 0; k < 6; k++) {
    if (hash(step * 1.7 + k) < .5) continue;
    const sy = H * hash(step + k * 11), sx = W * (.2 + .6 * hash(step * 2 + k));
    g.drawImage(TMP, sx, sy, 180, 2, sx, sy, 180, 120 + 300 * hash(k + step));
  }
  // data blocks
  for (let k = 0; k < 10; k++) {
    if (hash(step * 5.1 + k) < .6) continue;
    g.fillStyle = [C.lime, C.white, C.red][k % 3];
    g.globalAlpha = .85;
    g.fillRect(W * hash(step + k * 3), H * hash(step * 1.1 + k * 7), 40 + 300 * hash(k * 9 + step), 6 + 30 * hash(k + step * 2));
  }
  g.globalAlpha = 1;
  label(g, `ERR_0x${(step * 2654435761 >>> 0).toString(16).toUpperCase().slice(0, 6)} · SIGNAL LOST`, 90, 140, C.red, .95, 18);
  label(g, lb < 2 ? 'boring.exe has stopped responding' : 'boring not found', W / 2, H - 230, C.white, .6, 22, 'center');
  return false;
}

// ------------------------------------------------------------------ scene 08: MONTAGE (rapid recap)
const CUTS = [
  [52, 'title', 1.4, 0], [52.5, 'kinetic', .45, 1], [53, 'shapes', 2.5, 0], [53.5, 'liquid', .9, 0],
  [54, 'depth', 3.35, 0], [54.5, 'kinetic', 2.45, 1], [55, 'depth', 6.3, 0], [55.25, 'shapes', 5.05, 1], [55.5, 'kinetic', 6.9, 0],
];
function montageCut(bt) { let c = null; for (const k of CUTS) if (bt >= k[0]) c = k; return c; }
function sMontage(g, lb, t) {
  const bt = 52 + lb;
  if (bt >= 55.75) { bgFill(g, C.ink); const s = E.outB(inv(55.75, 55.9, bt)); g.fillStyle = C.lime; g.beginPath(); g.arc(W / 2, H / 2, 14 * s, 0, TAU); g.fill(); return false; }
  const [at, name, clb, invt] = montageCut(bt);
  const sc = SCENE_BY_NAME[name];
  const light = sc.fn(g, clb + (bt - at), sc.a * B + (clb + bt - at) * B);
  // cut counter
  const n = CUTS.findIndex(k => k[0] === at) + 1;
  label(g, String(n).padStart(2, '0'), W - 90, 140, light ? C.ink : C.white, .9, 44, 'right');
  return invt ? !light : light;
}

// ------------------------------------------------------------------ scene 09: OUTRO / LOGO
function sOutro(g, lb, t) {
  bgFill(g, C.ink);
  const col = inv(7.05, 7.6, lb), cs = 1 - E.inB(col, 2.2);
  g.save(); g.translate(W / 2, H / 2); g.scale(cs, cs); g.translate(-W / 2, -H / 2);
  const bgA = E.outC(inv(.3, 2.5, lb)) * .5;
  if (bgA > 0) { g.globalAlpha = bgA; g.drawImage(shader('liquid', { time: t * .6, dim: .5, hue: .02 }), 0, 0, W, H); g.globalAlpha = 1; }
  const vg = g.createRadialGradient(W / 2, H / 2, 200, W / 2, H / 2, 1100);
  vg.addColorStop(0, 'rgba(11,11,13,.35)'); vg.addColorStop(1, 'rgba(11,11,13,.95)');
  g.fillStyle = vg; g.fillRect(0, 0, W, H);
  shockwave(g, lb, C.lime); burst(g, lb, C.lime, 110, 11);

  font(g, 'U', 100); const w100 = g.measureText('VIBE EDITING').width;
  const fs = 100 * 1120 / w100, R = 96, gap = 52;
  const total = R * 2 + gap + 1120, x0 = W / 2 - total / 2, cy = H / 2 - 70;
  // pulse rings from the mark
  for (let k = 0; k < 3; k++) {
    const p = fract(lb - k / 3);
    if (lb < 1 + k / 3) continue;
    g.strokeStyle = withAlpha(C.lime, (1 - p) * .25); g.lineWidth = 2;
    g.beginPath(); g.arc(x0 + R, cy, R + p * 380, 0, TAU); g.stroke();
  }
  // mark: lime disc + play glyph
  const ms = E.outB(inv(.05, .55, lb), 2.4);
  if (ms > 0) {
    g.save(); g.translate(x0 + R, cy); g.scale(ms, ms);
    g.fillStyle = C.lime; g.beginPath(); g.arc(0, 0, R, 0, TAU); g.fill();
    const tr = E.outB(inv(.35, .85, lb));
    g.rotate((1 - tr) * -Math.PI / 2); g.scale(tr, tr);
    g.fillStyle = C.ink; g.beginPath(); g.moveTo(-26, -38); g.lineTo(44, 0); g.lineTo(-26, 38); g.closePath();
    g.lineJoin = 'round'; g.lineWidth = 14; g.strokeStyle = C.ink; g.stroke(); g.fill();
    g.restore();
  }
  // wordmark
  font(g, 'U', fs); g.textAlign = 'left'; g.textBaseline = 'middle';
  const gl = glyphs(g, 'VIBE EDITING'), wx = x0 + R * 2 + gap;
  const cap = g.measureText('V').actualBoundingBoxAscent;
  g.save(); g.beginPath(); g.rect(wx - 10, cy - cap, 1200, cap * 2); g.clip();
  for (let i = 0; i < gl.list.length; i++) {
    const q = E.outX(inv(.3 + i * .04, .9 + i * .04, lb));
    g.fillStyle = i < 4 ? C.lime : C.white;
    g.fillText(gl.list[i].c, wx + gl.list[i].x, cy + 8 + (1 - q) * cap * 1.6);
  }
  g.restore();
  // tagline, typed
  const tag = 'DIRECT THE VIBE.  LET AI DO THE KEYFRAMES.';
  const nt = Math.floor(inv(1.4, 2.6, lb) * tag.length);
  if (nt > 0) {
    font(g, 'M', 28, 3); g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    const full = g.measureText(tag).width;
    g.textAlign = 'left'; g.fillStyle = withAlpha(C.white, .85);
    g.fillText(tag.slice(0, nt), W / 2 - full / 2, cy + 175);
    if (nt < tag.length || Math.floor(lb * 4) % 2) { g.fillStyle = C.lime; g.fillRect(W / 2 - full / 2 + g.measureText(tag.slice(0, nt)).width + 4, cy + 150, 14, 30); }
  }
  // CTA
  const cta = E.outB(inv(3, 3.4, lb), 2.2);
  if (cta > 0) {
    g.save(); g.translate(W / 2, cy + 290); g.scale(cta, cta);
    font(g, 'I', 40, 1); const s = 'ENROLL NOW  →', w = g.measureText(s).width + 90;
    rrect(g, -w / 2, -42, w, 84, 42); g.fillStyle = C.lime; g.fill();
    g.fillStyle = C.ink; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(s, 0, 3);
    g.restore();
  }
  const by = E.outC(inv(3.5, 4.2, lb));
  if (by > 0) {
    font(g, 'S', 44); g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    g.fillStyle = withAlpha(C.white, .8 * by); g.fillText('by Ideabro Studio', W / 2, cy + 405 + (1 - by) * 20);
  }
  g.restore();
  // bookend: the dot, then black
  if (col > .5) {
    const s = E.outB(inv(.5, .75, col)) * (1 - E.inB(inv(7.78, 7.95, lb), 3));
    if (s > 0) { g.fillStyle = C.lime; g.beginPath(); g.arc(W / 2, H / 2, 14 * s, 0, TAU); g.fill(); }
  }
  return false;
}

// ------------------------------------------------------------------ timeline
const SCENES = [
  { a: 0, b: 8, fn: sIntro, name: 'intro', label: 'EASE' },
  { a: 8, b: 16, fn: sTitle, name: 'title', label: 'TITLE' },
  { a: 16, b: 24, fn: sKinetic, name: 'kinetic', label: 'KINETIC TYPE' },
  { a: 24, b: 32, fn: sShapes, name: 'shapes', label: 'SHAPE LANGUAGE' },
  { a: 32, b: 40, fn: sLiquid, name: 'liquid', label: 'LIQUID' },
  { a: 40, b: 48, fn: sDepth, name: 'depth', label: 'DEPTH' },
  { a: 48, b: 52, fn: sGlitch, name: 'glitch', label: 'GLITCH' },
  { a: 52, b: 56, fn: sMontage, name: 'montage', label: 'MONTAGE' },
  { a: 56, b: 64, fn: sOutro, name: 'outro', label: 'VIBE EDITING' },
];
const SCENE_BY_NAME = Object.fromEntries(SCENES.map(s => [s.name, s]));
const sceneAt = bt => SCENES.find(s => bt >= s.a && bt < s.b) || SCENES[SCENES.length - 1];

// Prompts typed into a chat bar; the next section drops when "enter" lands on the downbeat.
const PROMPTS = [[5.9, 8, 'make it pop'], [14.5, 16, 'make it kinetic'], [22.7, 24, 'make it geometric'],
  [30.5, 32, 'make it flow'], [38.5, 40, 'make it deep'], [46.5, 48, 'make it glitch'], [50.5, 52, 'make it hit']];
const HITS = [8, 16, 24, 32, 40, 48, 52, 56, 62];
const FLASH = [[8, 1], [16, .45], [24, .3], [32, .45], [40, .55], [48, .5], [52, .4], [56, 1], [62, .5]];

function camera(bt) {
  let z = 1, x = 0, y = 0, r = 0;
  for (const h of HITS) z += .07 * pulseAt(bt, h, .25);
  const amp = bt < 8 ? 0 : bt < 16 ? .035 : bt < 24 ? .028 : bt < 32 ? .012 : bt < 40 ? .01 : bt < 48 ? .02 : bt < 52 ? .045 : 0;
  z += amp * Math.exp(-fract(bt) / .15);
  if (bt >= 52 && bt < 55.75) { const c = montageCut(bt); z += .09 * pulseAt(bt, c[0], .2); r += (hash(c[0]) - .5) * .05; }
  for (const [at, A] of [[8, 30], [40, 12], [48, 16], [56, 34], [62, 12]]) {
    const d = bt - at;
    if (d >= 0 && d < 2.5) { const a = A * Math.exp(-d / .35); x += a * noise1(d * 38 + at); y += a * noise1(d * 38 + at + 50); r += a * .0011 * noise1(d * 30 + at + 99); }
  }
  return { z, x, y, r };
}
function fx(bt) {
  let ab = .3, glitch = 0, flash = 0, bloom = .4, invert = 0;
  for (const [at, f] of FLASH) flash = Math.max(flash, f * pulseAt(bt, at, .12));
  for (const h of HITS) ab += 2.4 * pulseAt(bt, h, .35);
  for (const s of [16, 24, 32, 40, 48, 56]) if (bt > s - .1 && bt < s) glitch = Math.max(glitch, .6);
  if (bt >= 48 && bt < 52) { const st = Math.floor(bt * 6); glitch = Math.max(glitch, .18 + (hash(st) > .55 ? .55 : 0)); ab += 1.2; }
  if (bt >= 52 && bt < 55.75) { const c = montageCut(bt); invert = c[3]; flash = Math.max(flash, .5 * pulseAt(bt, c[0], .06)); ab += 1.5 * pulseAt(bt, c[0], .2); }
  if (bt >= 32 && bt < 40) bloom = .65;
  if (bt >= 40 && bt < 48) bloom = 1.0;
  if (bt >= 56) bloom = .8;
  return { ab, glitch, flash, bloom, invert };
}

// ------------------------------------------------------------------ overlay: HUD + prompt bar
function tc(t) { const f = Math.floor(t * 30); return `00:00:${String(Math.floor(f / 30)).padStart(2, '0')}:${String(f % 30).padStart(2, '0')}`; }
function hud(g, bt, t, light) {
  const a = inv(.3, 1.1, bt) * (1 - inv(62.8, 63.2, bt));
  if (a <= 0) return;
  const col = light ? C.ink : C.white;
  g.save(); g.globalAlpha = a;
  g.strokeStyle = withAlpha(col, .6); g.lineWidth = 2;
  const m = 36, L = 26;
  for (const [x, y, dx, dy] of [[m, m, 1, 1], [W - m, m, -1, 1], [m, H - m, 1, -1], [W - m, H - m, -1, -1]]) {
    g.beginPath(); g.moveTo(x, y + dy * L); g.lineTo(x, y); g.lineTo(x + dx * L, y); g.stroke();
  }
  label(g, 'VIBE EDITING / SHOWREEL 2026', 80, 84, col, .75, 17);
  label(g, 'TC ' + tc(t), W - 80, 84, col, .75, 17, 'right');
  const sc = sceneAt(bt), idx = SCENES.indexOf(sc) + 1;
  label(g, `${String(idx).padStart(2, '0')} — ${sc.label}`, 80, H - 70, col, .75, 17);
  // scrubber
  const x0 = 470, x1 = W - 470, y = H - 76;
  g.strokeStyle = withAlpha(col, .25); g.lineWidth = 2; g.beginPath(); g.moveTo(x0, y); g.lineTo(x1, y); g.stroke();
  g.strokeStyle = withAlpha(col, .8); g.beginPath(); g.moveTo(x0, y); g.lineTo(lerp(x0, x1, bt / BEATS), y); g.stroke();
  g.fillStyle = withAlpha(col, .45);
  for (const s of SCENES) g.fillRect(lerp(x0, x1, s.a / BEATS) - 1, y - 7, 2, 14);
  g.fillStyle = C.lime; diamond(g, lerp(x0, x1, bt / BEATS), y, 8); g.fill();
  // bpm + beat lights
  label(g, '128 BPM', W - 200, H - 70, col, .75, 17, 'right');
  const bi = Math.floor(bt) % 4;
  for (let i = 0; i < 4; i++) {
    g.fillStyle = i === bi ? C.lime : withAlpha(col, .25);
    g.fillRect(W - 180 + i * 24, H - 84, 16, 16);
  }
  g.restore();
}
function promptBar(g, bt) {
  for (const [a, b, s] of PROMPTS) {
    if (bt < a || bt > b + .35) continue;
    const appear = E.outB(inv(a, a + .3, bt)), exit = E.outC(inv(b, b + .35, bt));
    const typeEnd = a + .15 + (b - a) * .6;
    const n = Math.floor(inv(a + .15, typeEnd, bt) * s.length);
    font(g, 'M', 32, 0);
    const tw = g.measureText(s).width;
    const w = tw + 76 + 90, h = 84, x = W / 2 - w / 2, y = H - 230;
    g.save();
    g.globalAlpha = 1 - exit;
    g.translate(W / 2, y + h / 2); g.scale(appear * (1 + exit * .25), appear * (1 + exit * .25)); g.translate(-W / 2, -(y + h / 2));
    g.shadowColor = 'rgba(0,0,0,.45)'; g.shadowBlur = 40; g.shadowOffsetY = 12;
    rrect(g, x, y, w, h, h / 2); g.fillStyle = 'rgba(16,16,19,.94)'; g.fill();
    g.shadowColor = 'transparent';
    g.strokeStyle = 'rgba(255,255,255,.16)'; g.lineWidth = 1.5; g.stroke();
    g.fillStyle = C.lime; sparkle(g, x + 44, y + h / 2, 15, bt * 2); g.fill();
    g.fillStyle = C.white; g.textAlign = 'left'; g.textBaseline = 'middle';
    const typed = s.slice(0, n);
    g.fillText(typed, x + 76, y + h / 2 + 2);
    if (bt < typeEnd || Math.floor(bt * 5) % 2 === 0) { g.fillStyle = C.lime; g.fillRect(x + 78 + g.measureText(typed).width, y + h / 2 - 18, 3, 36); }
    // send button
    const press = inv(b - .3, b - .12, bt) * (1 - inv(b - .12, b, bt));
    const ready = n >= s.length;
    const bx = x + w - 46, by = y + h / 2;
    g.fillStyle = ready ? C.lime : 'rgba(255,255,255,.14)';
    g.beginPath(); g.arc(bx, by, 26 * (1 - press * .18), 0, TAU); g.fill();
    g.strokeStyle = ready ? C.ink : 'rgba(255,255,255,.5)'; g.lineWidth = 4; g.lineCap = 'round'; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(bx, by + 11); g.lineTo(bx, by - 11); g.moveTo(bx - 9, by - 3); g.lineTo(bx, by - 12); g.lineTo(bx + 9, by - 3); g.stroke();
    g.restore();
  }
}

// ------------------------------------------------------------------ frame assembly
const S = mk(), A = mk();
function drawScene(g, t) {
  const bt = t / B;
  const sc = sceneAt(bt);
  const cam = camera(bt);
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'source-over'; g.filter = 'none';
  g.save();
  g.translate(W / 2 + cam.x, H / 2 + cam.y); g.rotate(cam.r); g.scale(cam.z, cam.z); g.translate(-W / 2, -H / 2);
  const light = sc.fn(g, bt - sc.a, t);
  g.restore();
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'source-over'; g.filter = 'none';
  const inverted = fx(bt).invert;
  hud(g, bt, t, inverted ? !light : light);
  promptBar(g, bt);
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
  // post
  const f = fx(t / B), gl = GL;
  gl.useProgram(POST.p); gl.viewport(0, 0, W, H);
  gl.bindTexture(gl.TEXTURE_2D, TEX);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, A);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.uniform1i(POST.U.tex, 0); gl.uniform2f(POST.U.res, W, H);
  gl.uniform1f(POST.U.ab, f.ab); gl.uniform1f(POST.U.glitch, f.glitch); gl.uniform1f(POST.U.grain, .055);
  gl.uniform1f(POST.U.vig, .38); gl.uniform1f(POST.U.bloom, f.bloom); gl.uniform1f(POST.U.flash, f.flash);
  gl.uniform1f(POST.U.invert, f.invert); gl.uniform1f(POST.U.seed, Math.floor(t * 60) * .137 % 97);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  gl.finish();
}

window.READY = (async () => {
  const fams = [['U', 100], ['A', 100], ['S', 100], ['M', 100], ['I', 100]];
  await Promise.all(fams.map(([f]) => document.fonts.load((f === 'S' ? 'italic ' : '') + '100px "' + FONT[f] + '"')));
  init();
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
