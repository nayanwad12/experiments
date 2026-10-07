// stage.js: shared Three.js setup for the batch-2 Reels. Every frame is a pure function of t (seconds).
//   import { stage, E, TL } from '/batch2/lib/stage.js';
//   const S = await stage({ bloom: 0.8 });   S.scene, S.camera, S.renderer
//   window.renderFrame = t => { ...; S.render(t); };   window.READY is set by stage().
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const q = new URLSearchParams(location.search);
export const W = +(q.get('w') || 1080), H = +(q.get('h') || 1920), FPS = +(q.get('fps') || 30);

// ---------------------------------------------------------------- easing
export const E = {
  clamp: (x, a = 0, b = 1) => Math.min(b, Math.max(a, x)),
  prog: (t, t0, d) => d > 0 ? Math.min(1, Math.max(0, (t - t0) / d)) : +(t >= t0),
  lerp: (a, b, k) => a + (b - a) * k,
  out: k => 1 - Math.pow(1 - Math.min(1, Math.max(0, k)), 3),
  in: k => Math.pow(Math.min(1, Math.max(0, k)), 3),
  io: k => { k = Math.min(1, Math.max(0, k)); return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; },
  expo: k => k >= 1 ? 1 : 1 - Math.pow(2, -10 * Math.max(0, k)),
  ioexpo: k => { k = Math.min(1, Math.max(0, k)); if (k === 0 || k === 1) return k;
    return k < 0.5 ? Math.pow(2, 20 * k - 10) / 2 : (2 - Math.pow(2, -20 * k + 10)) / 2; },
  back: (k, s = 1.7) => { k = Math.min(1, Math.max(0, k)) - 1; return 1 + (s + 1) * k * k * k + s * k * k; },
  spring: (x, w = 18, z = 0.4) => x <= 0 ? 0 : 1 - Math.exp(-z * w * x) * Math.cos(w * Math.sqrt(1 - z * z) * x),
  hash: (...k) => { let h = 2166136261; for (const v of k) { h ^= Math.floor(v * 1000) | 0; h = Math.imul(h, 16777619); }
    h ^= h >>> 13; h = Math.imul(h, 0x5bd1e995); h ^= h >>> 15; return (h >>> 0) / 4294967295; },
  noise: (x, s = 0) => { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
    return E.lerp(E.hash(i, s) * 2 - 1, E.hash(i + 1, s) * 2 - 1, u); },
};

// timeline written by build.py (work/timeline.json): key times, words, colours
export let TL = {};

// ---------------------------------------------------------------- film-look shader (grain, vignette, chroma, grade)
const FilmShader = {
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uGrain: { value: 0.045 }, uVig: { value: 0.35 },
    uChroma: { value: 0.0012 }, uLift: { value: new THREE.Vector3(0, 0, 0) }, uGain: { value: new THREE.Vector3(1, 1, 1) },
    uFlash: { value: 0 }, uFade: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uTime, uGrain, uVig, uChroma, uFlash, uFade;
    uniform vec3 uLift, uGain; varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)) + uTime*7.13) * 43758.5453); }
    void main(){
      vec2 d = vUv - 0.5; float r = length(d);
      vec3 c;
      c.r = texture2D(tDiffuse, vUv + d * uChroma * 8.).r;
      c.g = texture2D(tDiffuse, vUv).g;
      c.b = texture2D(tDiffuse, vUv - d * uChroma * 8.).b;
      c = uLift + c * uGain;
      c *= 1. - uVig * smoothstep(0.35, 0.95, r * 1.25);
      c += (h(vUv * 1000.) - 0.5) * uGrain;
      c = mix(c, vec3(1.), uFlash);
      c = mix(c, vec3(0.), uFade);
      gl_FragColor = vec4(c, 1.);
    }`,
};

export async function stage(opts = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setSize(W, H); renderer.setPixelRatio(1);
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = opts.exposure ?? 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  if (opts.shadows) { renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; }
  document.body.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(opts.bg ?? '#050508');
  if (opts.env !== false) {
    const pm = new THREE.PMREMGenerator(renderer);
    scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environmentIntensity = opts.envIntensity ?? 1.0;
  }
  const camera = new THREE.PerspectiveCamera(opts.fov ?? 35, W / H, 0.05, 400);
  // opts.samples > 0: multisampled composer target (clean edges on hard geometry such as logos)
  const composer = opts.samples ? new EffectComposer(renderer, new THREE.WebGLRenderTarget(W, H,
    { type: THREE.HalfFloatType, samples: opts.samples })) : new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  let bloom = null;
  if (opts.bloom) { bloom = new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), opts.bloom, opts.bloomRadius ?? 0.55,
    opts.bloomThreshold ?? 0.82); composer.addPass(bloom); }
  composer.addPass(new OutputPass());
  const film = new ShaderPass(FilmShader); composer.addPass(film);
  if (opts.timeline) TL = await (await fetch(opts.timeline + '?' + Math.random())).json();
  await loadFonts(opts.fonts || []);
  const S = { THREE, renderer, scene, camera, composer, bloom, film, TL,
    render(t) { film.uniforms.uTime.value = t; composer.render(); } };
  return S;
}

// fonts from reels/fonts (used by canvas textures)
export async function loadFonts(list) {
  for (const [family, file] of list) {
    const f = new FontFace(family, `url(/fonts/${file})`); await f.load(); document.fonts.add(f);
  }
}

// ---------------------------------------------------------------- canvas textures (UI, labels, screens)
export function canvasTex(w, h) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const ctx = cv.getContext('2d');
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
  return { cv, ctx, tex, update() { tex.needsUpdate = true; } };
}

export function rr(ctx, x, y, w, h, r) {
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}

// image sequence (jpg frames extracted by build.py) -> one texture per frame, cached
export async function frameSeq(dir, n, ext = 'jpg') {
  const loader = new THREE.TextureLoader();
  const frames = await Promise.all([...Array(n).keys()].map(i => new Promise(res =>
    loader.load(`${dir}/${String(i).padStart(4, '0')}.${ext}`, t => { t.colorSpace = THREE.SRGBColorSpace; res(t); }))));
  return frames;
}

export { THREE };
