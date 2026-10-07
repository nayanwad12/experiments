// IDEABRO STUDIO / style 3: NEON SIGN.
// Dark brick wall, glass tubes bent to the lockup's outlines. The B (warm "idea" amber) stutters on first,
// then IDEABRO (white), then STUDIO, each with a flicker, a buzz and a glow that spills onto the bricks.
import { stage } from '/batch2/lib/stage.js';
import { lockup, lockupCanvas, fitter, E, THREE, canvasTex } from './lib.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.7, bloomThreshold: 1.0, bloomRadius: 0.5, bg: '#060403', fov: 30, env: false, samples: 4,
  timeline: '/logo-ideabro/work/timeline.json' });
const { scene, camera, film } = S, T = S.TL.neon;
const { clamp, prog, lerp, io, hash, noise } = E;
const L = await lockup(), fit = fitter(L, 0.6, 0.76);
const AMBER = '#FFB547', WHITE = '#EAF3FF';

// ---------------------------------------------------------------- brick wall
const bricks = canvasTex(1024, 1024); {
  const c = bricks.ctx; c.fillStyle = '#140d0b'; c.fillRect(0, 0, 1024, 1024);
  for (let r = 0; r < 16; r++) for (let k = -1; k < 9; k++) {
    const x = k * 128 + (r % 2) * 64, y = r * 64, sh = 0.7 + 0.5 * hash(r, k);
    c.fillStyle = `rgb(${Math.round(64 * sh)},${Math.round(34 * sh)},${Math.round(28 * sh)})`; c.fillRect(x + 4, y + 4, 120, 56);
    for (let n = 0; n < 50; n++) { c.fillStyle = `rgba(0,0,0,${0.18 * hash(r, k, n)})`; c.fillRect(x + 4 + 120 * hash(n, r, k), y + 4 + 56 * hash(k, n, r), 6, 4); }
  }
  bricks.tex.wrapS = bricks.tex.wrapT = THREE.RepeatWrapping; bricks.tex.repeat.set(5, 4); bricks.update();
}
const wall = new THREE.Mesh(new THREE.PlaneGeometry(26, 20), new THREE.MeshStandardMaterial({ map: bricks.tex, roughness: 0.92, metalness: 0 }));
wall.position.z = -0.32; scene.add(wall);
scene.add(new THREE.AmbientLight('#ffffff', 0.05));

// ---------------------------------------------------------------- tubes
function contours(shapes) {
  const out = [];
  shapes.forEach(sh => { const { shape, holes } = sh.extractPoints(16); [shape, ...holes].forEach(r => out.push(r)); });
  return out;
}
function tubes(shapes, radius, hex) {
  const grp = new THREE.Group();
  const on = new THREE.MeshBasicMaterial({ color: new THREE.Color(hex).multiplyScalar(2.4) });
  const dim = new THREE.MeshStandardMaterial({ color: '#3a3330', roughness: 0.25, metalness: 0.1 });
  for (const ring of contours(shapes)) {
    const path = new THREE.CurvePath(), P = ring.map(p => new THREE.Vector3(p.x, p.y, 0.06));
    for (let i = 0; i < P.length; i++) path.add(new THREE.LineCurve3(P[i], P[(i + 1) % P.length]));
    grp.add(new THREE.Mesh(new THREE.TubeGeometry(path, Math.max(24, Math.ceil(path.getLength() * 90)), radius, 8, true), on));
  }
  grp.userData = { on, dim }; scene.add(grp); return grp;
}
// wall glow: a blurred copy of each part, added onto the bricks
function wallGlow(part, hex, blur) {
  const cw = 1024, ch = Math.round(cw * L.h / L.w * 1.5), u = cw / (L.w * 1.5);
  const ct = canvasTex(cw, ch), c = ct.ctx; c.filter = `blur(${blur}px)`;
  const src = lockupCanvas(L, cw, ch, { u, icon: part === 'icon' ? hex : 'rgba(0,0,0,0)', name: part === 'name' ? hex : 'rgba(0,0,0,0)',
    studio: part === 'studio' ? hex : 'rgba(0,0,0,0)' });
  c.drawImage(src.cv, 0, 0); c.drawImage(src.cv, 0, 0); ct.update();
  const m = new THREE.Mesh(new THREE.PlaneGeometry(cw / u, ch / u), new THREE.MeshBasicMaterial({ map: ct.tex, transparent: true,
    blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
  m.position.z = -0.31; scene.add(m); return m;
}
const signs = [
  { g: tubes(L.icon, 0.024, AMBER), glow: wallGlow('icon', AMBER, 28), t0: T.b, seed: 1, col: AMBER, y: L.y.icon },
  { g: tubes(L.name.flat(), 0.011, WHITE), glow: wallGlow('name', WHITE, 22), t0: T.name, seed: 2, col: WHITE, y: L.y.name, k: 0.5 },
  { g: tubes(L.studio.flat(), 0.0065, AMBER), glow: wallGlow('studio', AMBER, 14), t0: T.studio, seed: 3, col: AMBER, y: L.y.studio, k: 0.6 },
];
signs.forEach(s => { s.k = s.k ?? 1; s.light = new THREE.PointLight(s.col, 0, 7, 1.6); s.light.position.set(0, s.y, 1.0); scene.add(s.light); });

// flicker: stutters on, then holds with the odd dropout
const flick = (t, t0, seed) => {
  if (t < t0) return 0; const dt = t - t0, f = Math.floor(t * 40);
  if (dt < 0.6) return hash(f, seed) > 0.62 - dt * 1.0 ? 1 : 0.08 * hash(f, seed + 9);
  return hash(f, seed + 4) > 0.992 ? 0.35 : 1;
};

window.renderFrame = t => {
  signs.forEach(s => {
    const on = flick(t, s.t0, s.seed), hum = 0.96 + 0.04 * noise(t * 30, s.seed);
    s.g.children.forEach(m => (m.material = on > 0.5 ? s.g.userData.on : s.g.userData.dim));
    s.g.userData.on.color.set(s.col).multiplyScalar((1.1 + 1.3 * s.k) * hum * (on > 0.5 ? on : 1));   // thin tubes run cooler
    s.glow.material.opacity = 0.55 * s.k * on * hum; s.light.intensity = 9 * s.k * on * hum;
  });
  const d = fit(30), k = io(prog(t, 0, T.full + 1.2));
  camera.position.set(lerp(-1.6, 0.25, k), lerp(-0.35, 0.05, k), d * lerp(0.86, 1.0, k)); camera.lookAt(lerp(-0.3, 0, k), 0, 0);
  film.uniforms.uGrain.value = 0.045; film.uniforms.uVig.value = 0.5; film.uniforms.uChroma.value = 0.0008;
  film.uniforms.uFade.value = 1 - clamp(prog(t, 0, 0.3));
  S.render(t);
};
resolveReady();
