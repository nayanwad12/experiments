// ACID CHROME: "Vibe Editing" hype reel. 1080x1920, 128 BPM, 18 bars (33.75 s).
// Every frame is a pure function of t (seconds). Art direction: references/vibe-crazy/BRIEF.md
//   black void + mirror chrome lit by strip lights + one acid lime + brutal repeated type + a HUD on every frame.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { TTFLoader } from 'three/addons/loaders/TTFLoader.js';
import { Font } from 'three/addons/loaders/FontLoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { E, W, H, loadFonts, rr } from '/batch2/lib/stage.js';

// ---------------------------------------------------------------- time grid
const BPM = 128, BEAT = 60 / BPM, BAR = 4 * BEAT;
const A0 = 0, B0 = 2 * BAR, C0 = 4 * BAR, D0 = 6 * BAR, E0 = 8 * BAR, F0 = 12 * BAR, G0 = 14 * BAR, END = 18 * BAR;
const SECTIONS = [[A0, '01', 'PROMPT'], [B0, '02', 'TYPE TUNNEL'], [C0, '03', 'MORPH'], [D0, '04', 'NO'],
  [E0, '05', 'DROP'], [F0, '06', 'MONTAGE'], [G0, '07', 'VIBE EDITING']];
const LIME = '#D4FF3F', LIME3 = new THREE.Color(LIME), INK = '#050505';
const { clamp, prog, lerp, out, io, ioexpo, expo, back, spring, hash, noise } = E;
const ein = E.in;

// ---------------------------------------------------------------- renderer + post
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(W, H); renderer.setPixelRatio(1);
renderer.toneMapping = THREE.NoToneMapping;            // brand-exact lime; highlights clip to white like real chrome
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(INK);
const camera = new THREE.PerspectiveCamera(35, W / H, 0.05, 600);
const BASE_FOV = 35;

const hud = document.createElement('canvas'); hud.width = W; hud.height = H;
const hx = hud.getContext('2d');
const hudTex = new THREE.CanvasTexture(hud);

const Film = {
  uniforms: { tDiffuse: { value: null }, tHud: { value: hudTex }, uTime: { value: 0 }, uGrain: { value: 0.05 },
    uVig: { value: 0.45 }, uChroma: { value: 0.006 }, uFlash: { value: 0 }, uInv: { value: 0 }, uLime: { value: 0 },
    uFade: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `uniform sampler2D tDiffuse, tHud; uniform float uTime, uGrain, uVig, uChroma, uFlash, uInv, uLime, uFade;
    varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)) + uTime*7.13) * 43758.5453); }
    void main(){
      vec2 d = vUv - 0.5; float r = length(d * vec2(0.5625, 1.));
      vec3 c;
      c.r = texture2D(tDiffuse, vUv + d * uChroma * (0.4 + r * 3.)).r;
      c.g = texture2D(tDiffuse, vUv).g;
      c.b = texture2D(tDiffuse, vUv - d * uChroma * (0.4 + r * 3.)).b;
      c *= 1. - uVig * smoothstep(0.25, 0.75, r);
      vec3 lime = vec3(0.831, 1.0, 0.247);
      float l = dot(c, vec3(0.299, 0.587, 0.114));
      c = mix(c, mix(lime, vec3(0.02), smoothstep(0.08, 0.6, l)), uInv);   // acid duotone invert
      vec4 hd = texture2D(tHud, vUv);
      c = mix(c, hd.rgb, hd.a);
      c = mix(c, lime, uLime);
      c = mix(c, vec3(1.), uFlash);
      c += (h(floor(vUv * vec2(540., 960.))) - 0.5) * uGrain;
      c = mix(c, vec3(0.), uFade);
      gl_FragColor = vec4(c, 1.);
    }`,
};
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), 0.45, 0.4, 0.95);
composer.addPass(bloom);
composer.addPass(new OutputPass());
const film = new ShaderPass(Film);
film.uniforms.tHud.value = hudTex;          // ShaderPass clones uniforms: point it back at the live HUD
composer.addPass(film);

// ---------------------------------------------------------------- chrome: dynamic cube map + an invisible strip-light studio
const cubeRT = new THREE.WebGLCubeRenderTarget(256, { type: THREE.HalfFloatType, generateMipmaps: true,
  minFilter: THREE.LinearMipmapLinearFilter });
const cubeCam = new THREE.CubeCamera(0.05, 300, cubeRT);
cubeCam.children.forEach(c => c.layers.enable(1));
scene.add(cubeCam);
const chrome = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 1, roughness: 0.05, envMap: cubeRT.texture });

const studio = new THREE.Group(); scene.add(studio);
function strip(w, h, color, k, pos) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(k), side: THREE.DoubleSide }));
  m.position.set(...pos); m.lookAt(0, 0, 0); m.layers.set(1); studio.add(m); return m;
}
strip(9, 2.4, '#ffffff', 1.4, [0, 7, 1.5]);           // top softbox
strip(0.9, 16, '#ffffff', 1.25, [-6.5, 0, 3]);         // key strip left
strip(0.45, 16, '#ffffff', 1.1, [6.5, 1, -1]);        // rim strip right
strip(16, 0.8, LIME, 1.0, [0, -2.5, -7]);             // lime back strip
strip(0.4, 12, LIME, 0.9, [-4.5, -1, -6]);
strip(7, 0.35, '#ffffff', 1.15, [0, 2.2, 9]);          // front strips (flat faces of the logo catch these)
strip(7, 0.25, LIME, 0.95, [0, -2.6, 9]);
strip(40, 1.1, '#ffffff', 1.1, [0, 1.1, 10]);         // horizon band
strip(40, 0.5, LIME, 0.9, [0, -1.3, 10]);
const sweep = strip(1.3, 22, LIME, 1.6, [-14, 0, 6]);  // moving lime bar for the logo light sweep
const sweepW = strip(0.5, 22, '#ffffff', 1.6, [-14, 0, 6]);
const floor = strip(40, 40, '#151515', 1, [0, -7, 0]);
// chrome-type horizon: a gradient wall in front of the logo (flat faces reflect a narrow band of it)
const horizon = (() => {
  const cv = document.createElement('canvas'); cv.width = 16; cv.height = 512;
  const c = cv.getContext('2d'), g = c.createLinearGradient(0, 0, 0, 512);
  // stop = (1.85 - y) / 3.2 for a ray that lands at height y: VIBE reads around y 0, EDITING around y -0.85
  [[0, '#ffffff'], [0.48, '#ffffff'], [0.58, '#9a9a9a'], [0.66, '#1a1a1a'], [0.705, '#050505'], [0.72, LIME],
   [0.735, '#050505'], [0.79, '#2a2a2a'], [0.84, '#9a9a9a'], [0.9, '#151515'], [1, '#000000']]
    .forEach(([k, c_]) => g.addColorStop(k, c_));
  c.fillStyle = g; c.fillRect(0, 0, 16, 512);
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(60, 3.2),
    new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide, color: new THREE.Color(1.25, 1.25, 1.25) }));
  m.position.set(0, 0.25, 11); m.lookAt(0, 0.25, 0); m.layers.set(1); studio.add(m); return m;
})();

// ---------------------------------------------------------------- helpers
function texCanvas(w, h) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const ctx = cv.getContext('2d');
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  return { cv, ctx, tex };
}
function wordTex(word, { font = 'Unbounded', size = 300, color = '#fff', w = 2048, h = 512, stroke = 0 } = {}) {
  const T = texCanvas(w, h), c = T.ctx;
  let s = size;
  c.font = `${s}px ${font}`;
  while (c.measureText(word).width > w * 0.94) { s *= 0.95; c.font = `${s}px ${font}`; }
  c.textAlign = 'center'; c.textBaseline = 'middle';
  if (stroke) { c.lineWidth = stroke; c.strokeStyle = color; c.strokeText(word, w / 2, h / 2 + s * 0.04); }
  else { c.fillStyle = color; c.fillText(word, w / 2, h / 2 + s * 0.04); }
  T.tex.needsUpdate = true;
  return T.tex;
}
function plane(tex, w, h, extra = {}) {
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, side: THREE.DoubleSide, ...extra }));
}
// pulse that decays after each beat in [a, b)
function beatEnv(t, a, b, k = 9) {
  if (t < a || t >= b) return 0;
  return Math.exp(-((t - a) % BEAT) * k);
}
function hits(t, list, k = 10) {
  let s = 0;
  for (const h of list) if (t >= h) s += Math.exp(-(t - h) * k);
  return s;
}
const beatsIn = (a, n, step = BEAT) => [...Array(n)].map((_, i) => a + i * step);

// ---------------------------------------------------------------- the blob (chrome, morphs between shape functions)
let bg = new THREE.IcosahedronGeometry(1, 64);
bg.deleteAttribute('uv'); bg.deleteAttribute('normal');
bg = mergeVertices(bg);
const BASE = bg.attributes.position.array.slice();
for (let i = 0; i < BASE.length; i += 3) {
  const l = Math.hypot(BASE[i], BASE[i + 1], BASE[i + 2]); BASE[i] /= l; BASE[i + 1] /= l; BASE[i + 2] /= l;
}
const blob = new THREE.Mesh(bg, chrome); scene.add(blob);
const WAVES = [...Array(5)].map((_, i) => {
  const a = hash(i, 1) * Math.PI * 2, z = hash(i, 2) * 2 - 1, s = Math.sqrt(1 - z * z);
  return { x: s * Math.cos(a), y: s * Math.sin(a), z, f: 1.6 + i * 0.85, s: 0.7 + 0.45 * i, a: 1 / (1 + i * 0.7), p: hash(i, 3) * 6 };
});
const SPK = [];
for (let i = 0; i < 18; i++) {   // fibonacci sphere directions for the spikes
  const y = 1 - (i + 0.5) / 18 * 2, r = Math.sqrt(1 - y * y), th = i * 2.39996;
  SPK.push([r * Math.cos(th), y, r * Math.sin(th)]);
}
const ell = (x, y, z, a, b) => 1 / Math.sqrt((x * x + z * z) / (a * a) + (y * y) / (b * b));
const SHAPES = [
  () => 1,                                                                            // 0 sphere
  (x, y, z) => { let s = 0; for (const d of SPK) { const c = x * d[0] + y * d[1] + z * d[2]; if (c > 0.9) s += Math.pow(c, 60); }
    return 0.78 + 0.85 * s; },                                                         // 1 spikes
  (x, y, z) => 0.92 / Math.pow(Math.abs(x) ** 6 + Math.abs(y) ** 6 + Math.abs(z) ** 6, 1 / 6), // 2 rounded cube
  (x, y, z) => 1 + 0.17 * Math.sin(9 * Math.atan2(z, x) + 5 * y),                     // 3 twisted ridges
  (x, y, z) => 0.82 + 0.5 * Math.pow(Math.abs(Math.sin(3 * Math.atan2(z, x))), 1.5) * (1 - Math.abs(y)), // 4 petals
  (x, y, z) => ell(x, y, z, 1.45, 0.42),                                              // 5 saucer
  (x, y, z) => ell(x, y, z, 0.62, 1.55),                                              // 6 capsule
  (x, y, z) => 1 + 0.32 * Math.sin(3 * x + 1) * Math.sin(2.6 * y + 2) * Math.sin(3.4 * z), // 7 lumpy
];
function wob(x, y, z, t) {
  let s = 0;
  for (const w of WAVES) s += w.a * Math.sin((x * w.x + y * w.y + z * w.z) * w.f + t * w.s + w.p);
  return s;
}
function shapeBlob(t, sa, sb, k, amp) {
  const P = bg.attributes.position.array, fa = SHAPES[sa], fb = SHAPES[sb];
  for (let i = 0; i < P.length; i += 3) {
    const x = BASE[i], y = BASE[i + 1], z = BASE[i + 2];
    const r0 = sa === sb ? fa(x, y, z) : lerp(fa(x, y, z), fb(x, y, z), k);
    const r = r0 + amp * wob(x, y, z, t);
    P[i] = x * r; P[i + 1] = y * r; P[i + 2] = z * r;
  }
  bg.attributes.position.needsUpdate = true;
  bg.computeVertexNormals();
}

// ---------------------------------------------------------------- [02] type tunnel
const TUN_R = 4.2, TUN_L = 90;
const tun = texCanvas(2048, 4096);
tun.tex.wrapS = tun.tex.wrapT = THREE.RepeatWrapping;
const tunGeo = new THREE.CylinderGeometry(TUN_R, TUN_R, TUN_L, 96, 1, true);
tunGeo.rotateX(Math.PI / 2);
const tunnel = new THREE.Mesh(tunGeo, new THREE.MeshBasicMaterial({ map: tun.tex, side: THREE.BackSide }));
tunnel.position.z = -TUN_L / 2 + 12;
scene.add(tunnel);
const LANES = 8;
function drawTunnel(t) {
  const c = tun.ctx, w = 2048, h = 4096, lw = w / LANES;
  c.fillStyle = INK; c.fillRect(0, 0, w, h);
  const word = t < B0 + BAR ? 'VIBE EDITING / ' : 'DIRECT THE VIBE / ';
  const nb = Math.floor((t - B0) / BEAT);
  const limeLane = ((nb * 3) % LANES + LANES) % LANES;
  c.font = `${lw * 0.86}px Anton`;
  c.textBaseline = 'middle';
  const tw = c.measureText(word).width;
  for (let i = 0; i < LANES; i++) {
    const dir = i % 2 ? 1 : -1;
    // lanes drift, then jump a step on every beat
    const step = nb + out(prog((t - B0) % BEAT, 0, 0.18));
    const off = ((dir * (t * 140 + step * 260)) % tw + tw) % tw;
    const isLime = i === limeLane && t >= B0;
    if (isLime) { c.fillStyle = LIME; c.fillRect(i * lw, 0, lw, h); }
    c.save();
    c.translate(i * lw + lw / 2, 0); c.rotate(Math.PI / 2);
    c.fillStyle = isLime ? INK : (i % 3 === 1 ? '#3a3a3a' : '#f2f2f2');
    for (let x = -off; x < h + tw; x += tw) c.fillText(word, x, 0);
    c.restore();
    c.fillStyle = '#000'; c.fillRect(i * lw - 3, 0, 6, h);
  }
  tun.tex.needsUpdate = true;
}

// ---------------------------------------------------------------- [03] morph: giant word behind + lime ring
const MORPH_WORDS = ['EASE', 'TIMING', 'FEEL', 'FLOW', 'COLOR', 'TYPE', 'DEPTH', 'VIBE'];
const ORDER = [1, 2, 3, 4, 5, 6, 7, 0];
let morphTex = [];
const morphWord = plane(null, 3.7, 7.4); scene.add(morphWord);
const ring = new THREE.Mesh(new THREE.TorusGeometry(1.95, 0.018, 8, 160),
  new THREE.MeshBasicMaterial({ color: LIME3.clone().multiplyScalar(1.15) }));
const ring2 = new THREE.Mesh(new THREE.TorusGeometry(2.3, 0.008, 8, 160),
  new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffffff').multiplyScalar(1.1) }));
scene.add(ring, ring2);

// ---------------------------------------------------------------- [04] NO ...: split words + chrome blade
const NO_WORDS = ['TIMELINE', 'KEYFRAMES', 'PLUGINS'];
// a word stacked in 7 rows (kinetic-poster style): outlined rows around one solid row in the middle
function stackTex(word, color) {
  const T = texCanvas(1024, 2048), c = T.ctx, rows = 7, rh = 2048 / rows;
  let z = 300; c.font = `${z}px Anton`;
  while (c.measureText(word).width > 1000) { z *= 0.96; c.font = `${z}px Anton`; }
  z = Math.min(z, rh * 1.05); c.font = `${z}px Anton`;
  c.textAlign = 'center'; c.textBaseline = 'middle';
  for (let r = 0; r < rows; r++) {
    const y = rh * (r + 0.5) + z * 0.04;
    if (r === 3) { c.fillStyle = color; c.fillText(word, 512, y); }
    else { c.globalAlpha = 1 - Math.abs(r - 3) * 0.22; c.lineWidth = 4; c.strokeStyle = color; c.strokeText(word, 512, y); c.globalAlpha = 1; }
  }
  T.tex.needsUpdate = true;
  return T.tex;
}
const noSlots = NO_WORDS.map((_, i) => D0 + i * 2 * BEAT * 1.0 + i * 0);   // half a bar each
for (let i = 0; i < 3; i++) noSlots[i] = D0 + i * 2 * BEAT;
const noJust = D0 + 6 * BEAT;   // JUST THE VIBE on beat 3 of bar 7
const noHalves = [];
function halfPlane(tex, w, h, top) {
  const g = new THREE.PlaneGeometry(w, h / 2);
  const uv = g.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setY(i, top ? 0.5 + uv.getY(i) * 0.5 : uv.getY(i) * 0.5);
  g.translate(0, top ? h / 4 : -h / 4, 0);
  return new THREE.Mesh(g, new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, side: THREE.DoubleSide }));
}
const blade = new THREE.Mesh(new THREE.BoxGeometry(9, 0.07, 0.25), chrome);
scene.add(blade);
let justPlane;

// ---------------------------------------------------------------- [05] drop tunnel: chrome rings, lime strips, streaks, word panels
const RINGS = 64, RING_GAP = 3.2;
const rings = new THREE.InstancedMesh(new THREE.TorusGeometry(3, 0.1, 16, 120), chrome, RINGS);
{
  const m = new THREE.Matrix4();
  for (let i = 0; i < RINGS; i++) { m.makeTranslation(0, 0, -i * RING_GAP - 4); rings.setMatrixAt(i, m); }
}
scene.add(rings);
const strips = new THREE.Group(); scene.add(strips);
for (let i = 0; i < 6; i++) {
  const a = i / 6 * Math.PI * 2, lime = i % 2 === 0;
  const s = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.05, 260),
    new THREE.MeshBasicMaterial({ color: (lime ? LIME3.clone() : new THREE.Color('#fff')).multiplyScalar(lime ? 2.4 : 1.5) }));
  s.position.set(Math.cos(a) * 2.55, Math.sin(a) * 2.55, -120);
  strips.add(s);
}
const NSTREAK = 1400;
const streakPos = new Float32Array(NSTREAK * 6);
const streakSeed = [...Array(NSTREAK)].map((_, i) => {
  const a = hash(i, 11) * Math.PI * 2, r = 0.6 + hash(i, 12) * 2.1;
  return [Math.cos(a) * r, Math.sin(a) * r, -hash(i, 13) * 220 + 10];
});
const streakGeo = new THREE.BufferGeometry();
streakGeo.setAttribute('position', new THREE.BufferAttribute(streakPos, 3));
const streaks = new THREE.LineSegments(streakGeo, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.55 }));
scene.add(streaks);
const PANELS = [[E0, 'DIRECT', '#fff'], [E0 + 2 * BEAT, 'THE', '#fff'], [E0 + BAR, 'VIBE.', LIME],
  [E0 + 2 * BAR, 'AI', '#fff'], [E0 + 2 * BAR + 2 * BEAT, 'DOES THE', '#fff'], [E0 + 3 * BAR, 'KEYFRAMES.', LIME]];
let panels = [];
function camZ(t) {      // drop tunnel camera position: steady speed + a surge on every kick
  const dt = t - E0;
  let surge = 0;
  const nb = Math.floor(dt / BEAT);
  for (let b = 0; b <= nb; b++) surge += 1 - Math.exp(-(dt - b * BEAT) * 9);
  return 2 - (15 * dt + 1.6 * surge);
}

// ---------------------------------------------------------------- [07] chrome logo
const letters = [];
let editing;
const logoBack = texCanvas(2048, 2048);
const backPlane = plane(logoBack.tex, 16, 16);
logoBack.tex.wrapS = logoBack.tex.wrapT = THREE.RepeatWrapping;
scene.add(backPlane);

async function buildLogo() {
  const json = await new Promise((res, rej) => new TTFLoader().load('/fonts/Unbounded-Black.ttf', res, undefined, rej));
  const font = new Font(json);
  const opts = s => ({ font, size: s, depth: s * 0.32, curveSegments: 10, bevelEnabled: true, bevelThickness: s * 0.05,
    bevelSize: s * 0.03, bevelSegments: 5 });
  const word = 'VIBE', size = 1.0, gap = 0.06;
  const geos = [...word].map(ch => {
    const g = new TextGeometry(ch, opts(size)); g.computeBoundingBox();
    const b = g.boundingBox; const w = b.max.x - b.min.x;
    g.translate(-b.min.x - w / 2, -size * 0.5, -size * 0.16);
    return { g, w };
  });
  const total = geos.reduce((s, x) => s + x.w, 0) + gap * (geos.length - 1);
  let x = -total / 2;
  for (const { g, w } of geos) {
    const m = new THREE.Mesh(g, chrome); m.userData.x = x + w / 2; x += w + gap;
    scene.add(m); letters.push(m);
  }
  const g2 = new TextGeometry('EDITING', opts(0.42)); g2.computeBoundingBox();
  const b2 = g2.boundingBox;
  g2.translate(-(b2.min.x + b2.max.x) / 2, -0.21, -0.07);
  editing = new THREE.Mesh(g2, chrome); scene.add(editing);
  editing.userData.w = b2.max.x - b2.min.x;
  return total;
}
let LOGO_W = 4;

// ---------------------------------------------------------------- per-section scene setup (pure function of ts)
const ALL = () => [blob, tunnel, morphWord, ring, ring2, blade, rings, strips, streaks, backPlane, editing, justPlane,
  ...letters, ...noHalves.flat(), ...panels];
let cubeAt = new THREE.Vector3(), cubeHide = [];
let shakeAmt = 0;

function setScene(ts) {
  for (const o of ALL()) if (o) o.visible = false;
  camera.up.set(0, 1, 0); camera.fov = BASE_FOV; camera.rotation.set(0, 0, 0);
  studio.position.set(0, 0, 0); sweep.position.x = -14; sweepW.position.x = -14; horizon.visible = false;
  shakeAmt = 0;
  if (ts < B0) secA(ts);
  else if (ts < C0) secB(ts);
  else if (ts < D0) secC(ts);
  else if (ts < E0) secD(ts);
  else if (ts < F0) secE(ts);
  else secG(Math.max(ts, G0));
  if (shakeAmt > 0) {
    camera.position.x += noise(ts * 40, 1) * shakeAmt * 0.08;
    camera.position.y += noise(ts * 40, 2) * shakeAmt * 0.08;
  }
  camera.updateProjectionMatrix();
}

const PROMPT = 'make it crazy.';
const T_TYPE = 0.3, CPS = BEAT / 4, T_ENTER = 1.5 * BAR;
const keyTimes = [...PROMPT].map((_, i) => T_TYPE + i * CPS);

function secA(t) {
  blob.visible = true;
  const keyPulse = hits(t, keyTimes, 12);
  const k = ein(prog(t, T_ENTER, B0 - T_ENTER - 0.04));
  const sc = 1.05 * (1 - 0.985 * k) * (1 + 0.04 * keyPulse);
  shapeBlob(t * 1.3, 0, 0, 0, 0.07 + 0.05 * keyPulse + 0.25 * k);
  blob.scale.setScalar(sc);
  blob.position.set(0, 0.25, 0);
  blob.rotation.set(t * 0.3, t * 0.45 + k * k * 14, 0);
  const a = t * 0.25;
  camera.position.set(Math.sin(a) * 0.8, 0.15 + Math.sin(t * 0.7) * 0.1, 6.2 - 1.2 * io(prog(t, T_ENTER, 0.9)));
  camera.lookAt(0, 0.25, 0);
  cubeAt.copy(blob.position); cubeHide = [blob];
  studio.position.copy(blob.position);
}

function secB(t) {
  tunnel.visible = blob.visible = true;
  drawTunnel(t);
  const dt = t - B0, nb = Math.floor(dt / BEAT);
  let surge = 0;
  for (let b = 0; b <= nb; b++) surge += 1 - Math.exp(-(dt - b * BEAT) * 8);
  const z = 6 - 3.2 * dt - 0.9 * surge;
  const bz = z - 5.2;
  const pop = spring(dt, 14, 0.35);
  shapeBlob(t * 1.6, 7, 7, 0, 0.06 + 0.06 * beatEnv(t, B0, C0));
  blob.scale.setScalar(Math.max(0.01, 1.15 * pop) * (1 + 0.08 * beatEnv(t, B0, C0)));
  blob.position.set(Math.sin(dt * 1.7) * 0.5, Math.cos(dt * 1.3) * 0.35, bz);
  blob.rotation.set(dt * 0.9, dt * 1.2, 0);
  camera.position.set(0, 0, z);
  camera.lookAt(blob.position.x * 0.4, blob.position.y * 0.4, bz);
  // roll: slow spin + a snap of 45 deg on every second beat
  const snaps = Math.floor(dt / (2 * BEAT)) + ioexpo(prog(dt % (2 * BEAT), 0, 0.3));
  camera.rotateZ(dt * 0.25 + snaps * Math.PI / 4);
  camera.fov = BASE_FOV + 10 + 6 * beatEnv(t, B0, C0) + 30 * ein(prog(t, C0 - 0.5, 0.5));
  // in the last half-beat the camera dives into the blob
  if (t > C0 - 0.5) camera.position.z = lerp(z, bz + 1.0, ein(prog(t, C0 - 0.5, 0.5)));
  cubeAt.copy(blob.position); cubeHide = [blob];
  studio.position.copy(blob.position);
  shakeAmt = beatEnv(t, B0, C0) * 0.6;
}

function secC(t) {
  blob.visible = morphWord.visible = ring.visible = ring2.visible = true;
  const dt = t - C0, i = Math.min(7, Math.floor(dt / BEAT)), kb = dt - i * BEAT;
  const sa = i === 0 ? 0 : ORDER[i - 1], sb = ORDER[i];
  const k = clamp(spring(kb, 22, 0.45), 0, 1.15);
  shapeBlob(t * 1.2, sa, sb, k, 0.035);
  const punch = Math.exp(-kb * 10);
  blob.scale.setScalar(1.0 + 0.1 * punch);
  blob.position.set(0, 0.1, 0);
  blob.rotation.set(dt * 0.6 + i * 0.4, dt * 0.9 + i * 0.9, 0);
  const ang = dt * 0.35 + i * 0.22 + 0.25 * ioexpo(prog(kb, 0, 0.25));
  camera.position.set(Math.sin(ang) * 7.2, 0.6 + Math.sin(dt) * 0.4, Math.cos(ang) * 7.2);
  camera.lookAt(0, 0.1, 0);
  camera.fov = BASE_FOV - 3 * punch + 4 * (1 - out(prog(dt, 0, 0.6)));
  // word behind the blob, facing the camera
  morphWord.material.map = morphTex[i]; morphWord.material.needsUpdate = true;
  const back = camera.position.clone().normalize().multiplyScalar(-2.6);
  morphWord.position.copy(back).add(new THREE.Vector3(0, 0.1, 0));
  morphWord.quaternion.copy(camera.quaternion);
  morphWord.scale.setScalar(1 + 0.12 * Math.exp(-kb * 12));
  morphWord.material.opacity = 0.35 + 0.65 * out(prog(kb, 0, 0.08));
  ring.rotation.set(Math.PI / 2 + Math.sin(dt * 1.3) * 0.5 + i * 0.5, dt * 0.8, 0);
  ring2.rotation.set(Math.PI / 2 - Math.cos(dt) * 0.6, -dt * 0.5 + i, 0.3);
  ring.scale.setScalar(1 + 0.12 * punch);
  cubeAt.copy(blob.position); cubeHide = [blob];
  shakeAmt = punch * 0.4;
}

function secD(t) {
  camera.position.set(0, 0, 9); camera.lookAt(0, 0, 0);
  blade.visible = false;
  for (let i = 0; i < 3; i++) {
    const s = t - noSlots[i];
    if (s < 0 || s >= 2 * BEAT) continue;
    const [top, bot] = noHalves[i];
    top.visible = bot.visible = true;
    const slam = out(prog(s, 0, 0.12));
    const sc = lerp(2.4, 1, slam);
    const cut = BEAT;                        // the blade crosses on the second beat
    const sp = out(prog(s, cut + 0.05, 0.5));
    for (const [m, sg] of [[top, 1], [bot, -1]]) {
      m.scale.setScalar(sc);
      m.position.set(sg * 0.25 * sp, sg * (0.05 + 0.9 * sp), 0);
      m.rotation.set(0, 0, sg * -0.12 * sp);
      m.material.opacity = slam * (1 - ein(prog(s, cut + 0.25, 0.45)));
    }
    if (s > cut - 0.08 && s < cut + 0.2) {
      blade.visible = true;
      const kx = prog(s, cut - 0.08, 0.2);
      blade.position.set(lerp(-9, 9, kx), 0, 0.3);
      blade.rotation.set(0.3, 0, -0.06);
    }
    shakeAmt = Math.max(shakeAmt, 1.6 * Math.exp(-s * 12) + 1.4 * (s > cut ? Math.exp(-(s - cut) * 10) : 0));
  }
  if (t >= noJust) {
    const s = t - noJust;
    justPlane.visible = true;
    justPlane.scale.setScalar(lerp(2.0, 1, out(prog(s, 0, 0.14))) * (1 + 0.12 * ein(prog(s, 0.2, 0.7))));
    justPlane.material.opacity = out(prog(s, 0, 0.1));
    justPlane.position.set(0, 0, 0);
    shakeAmt = 0.5 + 1.8 * ein(prog(s, 0.1, 0.84));
  }
  cubeAt.set(0, 0, 0); cubeHide = [blade];
}

function secE(t) {
  rings.visible = strips.visible = streaks.visible = true;
  const z = camZ(t), dt = t - E0;
  const v = 15 + 14 * beatEnv(t, E0, F0, 9);
  camera.position.set(Math.sin(dt * 0.9) * 0.35, Math.cos(dt * 0.7) * 0.3, z);
  camera.lookAt(Math.sin(dt * 0.9 + 0.6) * 0.2, 0, z - 10);
  // barrel roll through bar 11, plus a slow drift roll
  const roll = dt * 0.15 + Math.PI * 2 * ioexpo(prog(t, E0 + 3 * BAR, BAR));
  camera.rotateZ(roll);
  camera.fov = BASE_FOV + 14 + 9 * beatEnv(t, E0, F0, 9);
  strips.rotation.z = dt * 0.5 + 0.4 * Math.floor(dt / BAR);
  // streaks: world-static particles, drawn as lines stretched by camera speed; wrap so the tunnel never runs out
  const len = v * 0.05;
  for (let i = 0; i < NSTREAK; i++) {
    const [x, y, z0] = streakSeed[i];
    let pz = z0;
    const rel = ((pz - z) % 220 + 220) % 220 - 200;   // keep in [z-200, z+20]
    pz = z + rel;
    streakPos.set([x, y, pz, x, y, pz + len], i * 6);
  }
  streakGeo.attributes.position.needsUpdate = true;
  for (const p of panels) {
    const { t0 } = p.userData;
    const pz = camZ(Math.min(t0 + 0.95, F0 - 0.01));
    p.position.set(0, 0, pz);
    p.quaternion.copy(camera.quaternion);
    p.visible = t >= t0 - 0.05 && z > pz - 0.2;
    p.material.opacity = out(prog(t, t0 - 0.05, 0.12)) * clamp((z - pz - 0.6) / 2.5);
  }
  cubeAt.copy(camera.position); cubeHide = [rings];
  shakeAmt = beatEnv(t, E0, F0, 9) * 0.5;
}

function secG(t) {
  const dt = t - G0;
  for (const m of letters) m.visible = true;
  editing.visible = backPlane.visible = horizon.visible = true;
  const dist = LOGO_W / (2 * Math.tan(THREE.MathUtils.degToRad(BASE_FOV / 2)) * (W / H)) / 0.8;
  const push = out(prog(dt, 0, 4 * BAR));
  camera.position.set(Math.sin(dt * 0.35) * 0.9, 0.35 + Math.sin(dt * 0.5) * 0.12, dist * (1.12 - 0.12 * push));
  camera.lookAt(0, 0.05, 0);
  letters.forEach((m, i) => {
    const s = t - (G0 + i * BEAT);
    const k = s < 0 ? 0 : 1;
    const e = back(prog(s, 0, 0.32), 1.4);
    m.visible = s >= 0;
    m.position.set(m.userData.x + (1 - e) * (i - 1.5) * 1.5, 0.35 + (1 - e) * 0.6, lerp(-26, 0, e));
    m.rotation.set((1 - e) * 1.6 + 0.05 * Math.sin(dt * 0.9 + i * 1.3) * k, (1 - e) * (i % 2 ? -2.2 : 2.2) + Math.sin(dt * 0.6 + i) * 0.07 * k, 0);
    shakeAmt = Math.max(shakeAmt, s >= 0 ? 1.4 * Math.exp(-s * 9) : 0);
  });
  const se = t - (G0 + BAR);
  editing.visible = se >= 0;
  const ee = out(prog(se, 0, 0.45));
  editing.position.set(0, -0.78 - 0.4 * (1 - ee), 0.15);
  editing.rotation.set(-(1 - ee) * Math.PI / 2, Math.sin(dt * 0.6) * 0.03, 0);
  editing.scale.setScalar(LOGO_W * 0.94 / editing.userData.w * 0.42 / 0.42);
  // lime light sweep across the chrome, twice
  const sw = prog(t, G0 + 1.5 * BAR, BAR * 0.9), sw2 = prog(t, G0 + 3 * BAR, BAR * 0.9);
  sweep.position.x = sw < 1 ? lerp(-14, 14, io(sw)) : lerp(-14, 14, io(sw2));
  sweepW.position.x = sweep.position.x - 2.5;
  backPlane.position.set(0, 0, -6);
  logoBack.tex.offset.set(dt * 0.03, 0);
  cubeAt.set(0, 0, 0.5); cubeHide = [...letters, editing];
  studio.position.set(0, 0, 0);
}

// ---------------------------------------------------------------- [06] montage: re-render earlier moments on a cut grid
const CUTS = (() => {
  const src = [1.0, 5.1, 9.05, 16.4, 12.0, 4.3, 19.6, 8.25, 13.0, 21.0, 6.6, 10.4];
  const out_ = []; let t0 = F0;
  src.forEach((s, i) => { const d = i < 4 ? BEAT : BEAT / 2; out_.push([t0, d, s]); t0 += d; });
  return out_;
})();
const CUT_WORDS = ['EVERY', 'CUT', 'ON', 'THE BEAT', 'NO', 'AFTER', 'EFFECTS', 'NO', 'PREMIERE', 'JUST', 'ONE', 'PROMPT'];
function montage(t) {
  for (let i = CUTS.length - 1; i >= 0; i--) {
    const [c0, d, s] = CUTS[i];
    if (t >= c0) return { ts: s + (t - c0) * 1.4, inv: i % 2 === 1 ? 1 : 0, cut: i, c0 };
  }
  return { ts: t, inv: 0, cut: -1, c0: F0 };
}

// ---------------------------------------------------------------- HUD (2D, composited after the grade so it stays crisp)
function mono(size, w = 500) { return `${w} ${size}px Mono`; }
function txt(s, x, y, font, color, a = 1, align = 'left', base = 'alphabetic') {
  const g = hx.globalAlpha;                 // multiply with any fade already set by the caller
  hx.globalAlpha = g * a; hx.font = font; hx.fillStyle = color; hx.textAlign = align; hx.textBaseline = base;
  hx.fillText(s, x, y); hx.globalAlpha = g;
}
function fitFont(s, family, max, maxW) {
  let z = max; hx.font = `${z}px ${family}`;
  while (hx.measureText(s).width > maxW) { z *= 0.96; hx.font = `${z}px ${family}`; }
  return `${z}px ${family}`;
}
function tc(t) {
  const f = Math.floor(t * 30) % 30, s = Math.floor(t);
  return `00:00:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
}
function frameHud(t, sec) {
  const m = 46, L = 46;
  hx.strokeStyle = 'rgba(255,255,255,0.85)'; hx.lineWidth = 3;
  for (const [x, y, sx, sy] of [[m, m, 1, 1], [W - m, m, -1, 1], [m, H - m, 1, -1], [W - m, H - m, -1, -1]]) {
    hx.beginPath(); hx.moveTo(x, y + sy * L); hx.lineTo(x, y); hx.lineTo(x + sx * L, y); hx.stroke();
  }
  txt('VIBE://EDITOR', 84, 112, mono(26), '#fff', 0.85);
  txt(`[${sec[1]}] ${sec[2]}`, 84, 152, mono(30, 700), LIME);
  const live = Math.floor(t / (BEAT / 2)) % 2 === 0;
  hx.fillStyle = LIME; hx.globalAlpha = live ? 1 : 0.25;
  hx.beginPath(); hx.arc(W - 214, 103, 9, 0, Math.PI * 2); hx.fill(); hx.globalAlpha = 1;
  txt('LIVE', W - 84, 112, mono(26), '#fff', 0.85, 'right');
  txt(`${BPM} BPM`, W - 84, 152, mono(26), '#fff', 0.6, 'right');
  txt(tc(t), 84, H - 104, mono(24), '#fff', 0.7);
  const bar = Math.floor(t / BAR) + 1, beat = Math.floor((t % BAR) / BEAT) + 1;
  txt(`BAR ${String(bar).padStart(2, '0')}.${beat}`, W - 84, H - 104, mono(24), '#fff', 0.7, 'right');
  // progress + beat ticks
  const x0 = 84, x1 = W - 84, y = H - 80;
  hx.fillStyle = 'rgba(255,255,255,0.18)'; hx.fillRect(x0, y, x1 - x0, 3);
  hx.fillStyle = LIME; hx.fillRect(x0, y, (x1 - x0) * clamp(t / END), 3);
  for (let b = 0; b <= 18; b++) {
    const x = lerp(x0, x1, b / 18);
    hx.fillStyle = b * BAR <= t ? LIME : 'rgba(255,255,255,0.4)';
    hx.fillRect(x - 1, y - 8, 2, 19);
  }
}

function drawHud(t, mt) {
  hx.clearRect(0, 0, W, H);
  const sec = [...SECTIONS].reverse().find(s => t >= s[0]);
  // ---- [01] hook title + prompt bar
  if (t < B0) {
    const fade = 1 - out(prog(t, T_ENTER, 0.3));
    hx.save(); hx.globalAlpha = fade;
    txt('ONE PROMPT.', W / 2, 400, '150px Anton', '#fff', 1, 'center');
    txt('ZERO KEYFRAMES.', W / 2, 560, '150px Anton', LIME, 1, 'center');
    hx.restore();
    const n = keyTimes.filter(k => t >= k).length;
    const sent = t >= T_ENTER;
    const ks = out(prog(t, T_ENTER + 0.12, 0.5));
    const pw = 900 * (1 - 0.7 * ks), ph = 124, px = W / 2 - pw / 2, py = lerp(1330, 1020, ks);
    hx.save(); hx.globalAlpha = 1 - ein(prog(t, T_ENTER + 0.2, 0.5));
    const flash = sent ? Math.exp(-(t - T_ENTER) * 6) : 0;
    rr(hx, px, py, pw, ph, ph / 2);
    hx.fillStyle = flash > 0.05 ? `rgba(212,255,63,${0.2 + 0.8 * flash})` : 'rgba(18,18,18,0.88)'; hx.fill();
    hx.lineWidth = 3; hx.strokeStyle = LIME; hx.stroke();
    if (ks < 0.5) {
      txt('>', px + 52, py + 80, mono(46, 700), LIME);
      const typed = PROMPT.slice(0, n);
      txt(typed, px + 100, py + 80, mono(46), flash > 0.4 ? INK : '#fff');
      hx.font = mono(46);
      const cw = hx.measureText(typed).width;
      if (!sent && Math.floor(t / (BEAT / 2)) % 2 === 0) { hx.fillStyle = LIME; hx.fillRect(px + 104 + cw, py + 38, 26, 54); }
      txt(sent ? 'SENT ✓' : 'ENTER ⏎', px + pw - 52, py + 78, mono(26, 700), sent ? INK : 'rgba(255,255,255,0.55)', 1, 'right');
    }
    hx.restore();
  }
  // ---- [03] morph: index + word label
  if (sec[0] === C0 && mt.cut < 0) {
    const dt = t - C0, i = Math.min(7, Math.floor(dt / BEAT));
    txt(`SHAPE ${String(i + 1).padStart(2, '0')}/08`, W / 2, 1560, mono(34, 700), LIME, 1, 'center');
  }
  // ---- [04] NO
  if (t >= D0 && t < E0) {
    for (let i = 0; i < 3; i++) {
      const s = t - noSlots[i];
      if (s < 0 || s >= 2 * BEAT) continue;
      const k = out(prog(s, 0, 0.1));
      const z = lerp(1.8, 1, k);
      hx.save(); hx.translate(W / 2, 700); hx.scale(z, z);
      txt('NO', 0, 0, '230px Anton', LIME, k * (1 - ein(prog(s, BEAT + 0.25, 0.45))), 'center');
      hx.restore();
    }
  }
  // ---- [06] montage words
  if (mt.cut >= 0) {
    const w = CUT_WORDS[mt.cut];
    const inv = mt.inv;
    const k = out(prog(t, mt.c0, 0.06));
    hx.save(); hx.translate(W / 2, H / 2 + 60); hx.scale(1.25 - 0.25 * k, 1.25 - 0.25 * k);
    txt(w, 0, 0, fitFont(w, 'Anton', 330, W - 160), inv ? INK : '#fff', 1, 'center', 'middle');
    hx.restore();
    txt(`CUT ${String(mt.cut + 1).padStart(2, '0')}/12`, W / 2, 1560, mono(34, 700), inv ? INK : LIME, 1, 'center');
  }
  // ---- [07] tagline + CTA
  if (t >= G0) {
    const a1 = out(prog(t, G0 + 1.5 * BAR, 0.4)), a2 = out(prog(t, G0 + 1.5 * BAR + 2 * BEAT, 0.4));
    const a3 = out(prog(t, G0 + 2.5 * BAR, 0.4));
    txt('DIRECT THE VIBE.', W / 2, 1300 + 30 * (1 - a1), '108px Anton', LIME, a1, 'center');
    txt('LET AI DO THE KEYFRAMES.', W / 2, 1385 + 30 * (1 - a2), '64px Anton', '#fff', a2, 'center');
    if (a3 > 0) {
      hx.save(); hx.globalAlpha = a3;
      const bw = 520, bx = W / 2 - bw / 2, by = 1450 + 20 * (1 - a3);
      rr(hx, bx, by, bw, 92, 46); hx.fillStyle = LIME; hx.fill();
      txt('FOLLOW FOR MORE  →', W / 2, by + 60, mono(36, 700), INK, 1, 'center');
      hx.restore();
      txt('IDEABRO STUDIO', W / 2, 1610, mono(28, 700), '#fff', 0.7 * a3, 'center');
    }
    // the hook words that open the logo section, one per letter slam
    const tops = ['V', 'I', 'B', 'E'];
    void tops;
  }
  frameHud(t, sec);
  hudTex.needsUpdate = true;
}

// ---------------------------------------------------------------- flashes / grade per real time
const FLASH = [B0, C0, E0, F0, G0];
function grade(t, mt) {
  let flash = 0;
  for (const f of FLASH) if (t >= f && t < f + 0.2) flash = Math.max(flash, 1 - (t - f) / 0.2);
  for (let i = 0; i < 4; i++) if (t >= G0 + i * BEAT) flash = Math.max(flash, 0.45 * Math.exp(-(t - G0 - i * BEAT) * 14));
  let lime = 0;
  for (let i = 0; i < 3; i++) { const c = noSlots[i] + BEAT; if (t >= c && t < c + 0.07) lime = 0.85; }
  if (t >= D0 + 2 * BAR - 0.07 && t < E0) lime = 0.9;
  if (mt.cut >= 0 && t < mt.c0 + 0.035) flash = Math.max(flash, 0.6);
  film.uniforms.uFlash.value = clamp(flash);
  film.uniforms.uLime.value = lime;
  film.uniforms.uInv.value = mt.inv || 0;
  film.uniforms.uFade.value = ein(prog(t, END - 0.35, 0.35));
  film.uniforms.uChroma.value = 0.006 + 0.03 * shakeAmt * 0.3 + (mt.cut >= 0 ? 0.02 : 0);
  bloom.strength = 0.45 + 0.4 * flash;
}

// ---------------------------------------------------------------- frame
function drawLogoBack() {
  const c = logoBack.ctx;
  c.fillStyle = '#000'; c.fillRect(0, 0, 2048, 2048);
  c.font = '170px Anton'; c.textBaseline = 'top'; c.fillStyle = '#0f0f0f';
  for (let r = 0; r < 12; r++) {
    const s = 'VIBE EDITING  VIBE EDITING  VIBE EDITING  ';
    c.fillText(s, (r % 2) * -400, r * 172);
  }
  logoBack.tex.needsUpdate = true;
}

window.renderFrame = (t) => {
  t = Math.min(t, END - 1e-4);
  const mt = (t >= F0 && t < G0) ? montage(t) : { ts: t, inv: 0, cut: -1 };
  setScene(mt.ts);
  grade(t, mt);
  drawHud(t, mt);
  film.uniforms.uTime.value = t;
  // reflections: render the scene into the cube map from the chrome object's point of view (without itself)
  for (const o of cubeHide) o.visible = false;
  cubeCam.position.copy(cubeAt);
  cubeCam.update(renderer, scene);
  for (const o of cubeHide) o.visible = true;
  composer.render();
};

window.READY = (async () => {
  await loadFonts([['Anton', 'Anton.ttf'], ['Unbounded', 'Unbounded-Black.ttf'], ['Mono', 'JetBrainsMono-500.ttf']]);
  {
    const f = new FontFace('Mono', 'url(/fonts/JetBrainsMono-400.ttf)', { weight: '400' }); await f.load(); document.fonts.add(f);
  }
  morphTex = MORPH_WORDS.map((w, i) => stackTex(w, i % 2 ? LIME : '#e8e8e8'));
  NO_WORDS.forEach(w => {
    const tex = wordTex(w, { font: 'Unbounded', size: 260, color: '#e8e8e8', h: 512 });
    const top = halfPlane(tex, 2.9, 0.725, true), bot = halfPlane(tex, 2.9, 0.725, false);
    scene.add(top, bot); noHalves.push([top, bot]);
  });
  justPlane = plane(wordTex('JUST THE VIBE.', { font: 'Anton', size: 400, color: LIME, h: 512 }), 3.1, 0.775);
  scene.add(justPlane);
  panels = PANELS.map(([t0, w, col]) => {
    const p = plane(wordTex(w, { font: 'Anton', size: 460, color: col === '#fff' ? '#ececec' : col, h: 512 }), 4.2, 1.05);
    p.userData.t0 = t0; scene.add(p); return p;
  });
  LOGO_W = await buildLogo();
  drawLogoBack();
  renderer.compile(scene, camera);
})();
