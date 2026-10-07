// IDEABRO STUDIO / style 2: PARTICLE STORM.
// ~70k sparks circle in a tilted vortex (warm "idea" gold and white), stream in letter by letter and lock into the
// lockup, which then resolves into crisp flat artwork with a light pulse.
import { stage } from '/batch2/lib/stage.js';
import { lockup, lockupCanvas, fitter, glowTex, E, THREE, PX } from './lib.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.6, bloomThreshold: 0.9, bloomRadius: 0.5, bg: '#030305', fov: 30, env: false, samples: 4,
  timeline: '/logo-ideabro/work/timeline.json' });
const { scene, camera, film, bloom } = S, T = S.TL.particles;
const { clamp, prog, lerp, out, io, expo, hash } = E;
const L = await lockup(), fit = fitter(L);

// ---------------------------------------------------------------- sample the flat lockup
const CW = 1100, CH = Math.round(CW * L.h / L.w * 1.06) + 40;
const lc = lockupCanvas(L, CW, CH, { u: CW / (L.w * 1.04) });
const px = lc.ctx.getImageData(0, 0, CW, CH).data;
const tg = [], seed = [];
for (let y = 0; y < CH; y += 2) for (let x = 0; x < CW; x += 2) {
  const i = (y * CW + x) * 4;
  if (px[i + 3] > 128) {
    const X = (x + (hash(x, y, 1) - 0.5) * 1.6 - CW / 2) / lc.u, Y = (CH / 2 - y + (hash(x, y, 2) - 0.5) * 1.6) / lc.u;
    tg.push(X, Y, 0);
    // arrival order: left to right with a little scatter, so it "writes" itself in
    seed.push(clamp((X + L.w / 2) / L.w * 0.75 + 0.25 * hash(x, y, 3)), hash(x, y, 4), hash(x, y, 5));
  }
}
const N = tg.length / 3;
const g = new THREE.BufferGeometry();
g.setAttribute('position', new THREE.Float32BufferAttribute(tg, 3));
g.setAttribute('aSeed', new THREE.Float32BufferAttribute(seed, 3));
const pU = { uK: { value: 0 }, uT: { value: 0 }, uPx: { value: PX }, uGain: { value: 1 }, uSettle: { value: 0 } };
const pmat = new THREE.ShaderMaterial({ uniforms: pU, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  vertexShader: `attribute vec3 aSeed; uniform float uK, uT, uPx, uSettle; varying vec3 vC; varying float vA;
    void main(){
      float k = clamp((uK - aSeed.x * 0.62) / 0.38, 0., 1.); float ke = 1. - pow(1. - k, 4.);
      // vortex: a tilted disc of orbits around the logo
      float r = 2.2 + 6.5 * aSeed.y, a = aSeed.z * 6.2832 + uT * (2.4 / (0.6 + aSeed.y));
      vec3 orb = vec3(cos(a) * r, 0.35 * sin(a * 3. + aSeed.y * 9.), sin(a) * r);
      orb = vec3(orb.x, orb.y * 0.9 + orb.z * 0.42, -orb.y * 0.42 + orb.z * 0.9 - 1.5);
      // on the way in, particles corkscrew toward their target
      vec3 p = mix(orb, position, ke);
      float sw = (1. - ke) * ke * 4.;
      p += vec3(sin(aSeed.z * 40. + uT * 5.), cos(aSeed.y * 40. + uT * 4.), sin(aSeed.x * 30.)) * 0.35 * sw;
      p += vec3(sin(uT * 2.3 + aSeed.y * 50.), cos(uT * 2.1 + aSeed.z * 50.), 0.) * 0.006 * (1. - uSettle);
      vec4 mv = modelViewMatrix * vec4(p, 1.); gl_Position = projectionMatrix * mv;
      gl_PointSize = uPx * (1.6 + 3.2 * (1. - ke)) * (12. / -mv.z);
      vec3 gold = vec3(1.0, 0.72, 0.28), ice = vec3(0.75, 0.85, 1.0);
      vec3 flight = mix(gold, ice, step(0.62, aSeed.y)) * (1.8 + 1.2 * sw);
      vC = mix(flight, vec3(1.0), ke * ke); vA = mix(0.5, 0.9, ke);
    }`,
  fragmentShader: `uniform float uGain; varying vec3 vC; varying float vA; void main(){ vec2 d = gl_PointCoord - .5; float r = length(d); if (r > .5) discard;
      gl_FragColor = vec4(vC * uGain, vA * smoothstep(.5, .0, r)); }` });
const points = new THREE.Points(g, pmat); points.frustumCulled = false; scene.add(points);

// crisp flat artwork that takes over once everything has landed
const hi = lockupCanvas(L, 2048, Math.round(2048 * CH / CW), { u: 2048 / (L.w * 1.04) });
const flatMat = new THREE.MeshBasicMaterial({ map: hi.tex, transparent: true, opacity: 0, depthWrite: false });
const flat = new THREE.Mesh(new THREE.PlaneGeometry(2048 / hi.u, hi.cv.height / hi.u), flatMat); flat.position.z = 0.01; scene.add(flat);
// light pulse when it locks
const pulse = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color: '#ffd27a', blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }));
scene.add(pulse);
// background dust
const dg = new THREE.BufferGeometry(), DN = 900, dp = new Float32Array(DN * 3);
for (let i = 0; i < DN; i++) dp.set([(hash(i, 1) - 0.5) * 30, (hash(i, 2) - 0.5) * 18, -12 + 10 * hash(i, 3)], i * 3);
dg.setAttribute('position', new THREE.BufferAttribute(dp, 3));
const dust = new THREE.Points(dg, new THREE.PointsMaterial({ color: '#8a7a60', size: 0.035, transparent: true, opacity: 0.5, depthWrite: false }));
scene.add(dust);

window.renderFrame = t => {
  const k = prog(t, T.go, T.land - T.go);
  pU.uK.value = k; pU.uT.value = t; pU.uSettle.value = prog(t, T.land, 0.6);
  const lockK = prog(t, T.flat, 0.45);
  flatMat.opacity = io(lockK);
  pU.uGain.value = lerp(1, 0.0, io(prog(t, T.flat + 0.2, 0.8)));
  points.visible = pU.uGain.value > 0.001;
  const pk = Math.exp(-5 * Math.max(0, t - T.flat)) * +(t >= T.flat);
  pulse.scale.set(L.w * 2.2, L.h * 1.6, 1); pulse.material.opacity = 0.55 * pk;
  bloom.strength = 0.6 + 0.6 * pk - 0.3 * prog(t, T.flat + 0.5, 1.5);
  dust.rotation.y = t * 0.02; dust.position.y = t * 0.05;
  // camera: starts low and oblique on the vortex, swings to the front as the logo forms
  const sw = io(prog(t, 0, T.land + 0.3));
  const az = lerp(-0.55, 0, sw) + 0.05 * Math.sin(t * 0.5) * (1 - prog(t, T.land, 1.5));
  const el = lerp(0.28, 0.02, sw), d = fit(30) * lerp(1.3, 1.0, expo(prog(t, 0, T.land + 0.6)));
  camera.position.set(d * Math.sin(az) * Math.cos(el), d * Math.sin(el), d * Math.cos(az) * Math.cos(el)); camera.lookAt(0, 0, 0);
  film.uniforms.uGrain.value = 0.03; film.uniforms.uChroma.value = 0.0006;
  film.uniforms.uFlash.value = 0.12 * pk;
  film.uniforms.uFade.value = 1 - clamp(prog(t, 0, 0.25));
  S.render(t);
};
resolveReady();
