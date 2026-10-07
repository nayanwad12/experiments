// IDEABRO STUDIO / style 5: HEAVY METAL.
// Machined steel pieces drop onto a concrete floor: the B slams first (sparks, dust, shake), the IDEABRO letters
// hammer down one by one, STUDIO lands as one plate. Then the camera cranes up to a top-down hero view.
import { stage } from '/batch2/lib/stage.js';
import { lockup, solid, stripEnv, fitter, E, THREE, canvasTex, PX } from './lib.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.4, bloomThreshold: 1.0, bloomRadius: 0.4, bg: '#08080a', fov: 32, env: false, samples: 4, shadows: true,
  timeline: '/logo-ideabro/work/timeline.json' });
const { scene, camera, renderer, film } = S, T = S.TL.metal;
const { clamp, prog, lerp, out, io, expo, hash, noise } = E;
const L = await lockup(), fit = fitter(L, 0.6, 0.78);
const ENV = stripEnv(renderer, '#ffd59a');

// ---------------------------------------------------------------- floor
const conc = canvasTex(1024, 1024); { const c = conc.ctx; c.fillStyle = '#26262a'; c.fillRect(0, 0, 1024, 1024);
  for (let i = 0; i < 16000; i++) { const w = hash(i, 1) > 0.5 ? 255 : 0;
    c.fillStyle = `rgba(${w},${w},${w},${0.05 * hash(i, 2)})`; c.fillRect(1024 * hash(i, 3), 1024 * hash(i, 4), 1 + 3 * hash(i, 5), 1 + 3 * hash(i, 6)); }
  for (let i = 0; i < 30; i++) { c.strokeStyle = `rgba(0,0,0,${0.15 + 0.2 * hash(i, 7)})`; c.lineWidth = 1 + 2 * hash(i, 8); c.beginPath();
    let x = 1024 * hash(i, 9), y = 1024 * hash(i, 10); c.moveTo(x, y);
    for (let k = 0; k < 8; k++) { x += (hash(i, k, 1) - 0.5) * 90; y += (hash(i, k, 2) - 0.5) * 90; c.lineTo(x, y); } c.stroke(); }
  conc.tex.wrapS = conc.tex.wrapT = THREE.RepeatWrapping; conc.tex.repeat.set(3, 3); conc.update(); }
const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({ map: conc.tex, roughness: 0.88, metalness: 0.05 }));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

const key = new THREE.DirectionalLight('#fff3e2', 2.4); key.position.set(-4, 9, 3); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.02;
Object.assign(key.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: 1, far: 25 }); scene.add(key);
scene.add(new THREE.HemisphereLight('#9fb0d0', '#201a14', 0.35));
const warm = new THREE.SpotLight('#ffb35c', 30, 14, 0.7, 0.6, 1.4); warm.position.set(3, 5, 3); warm.target.position.set(0, 0, 0); scene.add(warm, warm.target);

// ---------------------------------------------------------------- steel pieces (lying on the floor: lockup y -> world -z)
const steel = new THREE.MeshPhysicalMaterial({ color: '#c3c7cf', metalness: 1, roughness: 0.32, envMap: ENV, envMapIntensity: 1.1, clearcoat: 0.3 });
const edge = new THREE.MeshPhysicalMaterial({ color: '#e6e9ef', metalness: 1, roughness: 0.12, envMap: ENV, envMapIntensity: 1.4 });
const gun = new THREE.MeshPhysicalMaterial({ color: '#8a8f99', metalness: 1, roughness: 0.38, envMap: ENV, envMapIntensity: 1.0 });
const board = new THREE.Group(); board.rotation.x = -Math.PI / 2; scene.add(board);
function piece(shapes, depth, bev, mats, tl) {
  const m = new THREE.Mesh(solid(shapes, depth, bev, 4, false), mats);
  m.castShadow = m.receiveShadow = true;
  const b = new THREE.Box3().setFromObject(m), c = b.getCenter(new THREE.Vector3());
  m.geometry.translate(-c.x, -c.y, 0); m.position.set(c.x, c.y, depth / 2 + bev);
  m.userData = { tl, depth, bev, home: m.position.clone(), seed: hash(c.x, c.y) };
  board.add(m); return m;
}
const pieces = [piece(L.icon, 0.42, 0.03, [steel, edge], T.b)];
L.name.forEach((letter, i) => pieces.push(piece(letter, 0.26, 0.02, [gun, edge], T.name[i])));
pieces.push(piece(L.studio.flat(), 0.08, 0.01, [gun, edge], T.studio));
// where each piece lands, in world space (for dust)
const landAt = m => new THREE.Vector3(m.userData.home.x, 0.02, -m.userData.home.y);

// ---------------------------------------------------------------- dust + sparks (time-driven particles)
function particles(n, fill, { grav = 0, drag = 2.5, col = '#d6e6ff', gain = 1, soft = 0.6, add = true } = {}) {
  const pos = new Float32Array(n * 3), vel = new Float32Array(n * 3), life = new Float32Array(n * 2), size = new Float32Array(n);
  for (let i = 0; i < n; i++) fill(i, pos, vel, life, size);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('aVel', new THREE.BufferAttribute(vel, 3));
  g.setAttribute('aLife', new THREE.BufferAttribute(life, 2)); g.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
  const u = { uT: { value: 0 }, uPx: { value: PX * 900 }, uGrav: { value: grav }, uDrag: { value: drag }, uGain: { value: gain },
    uCol: { value: new THREE.Color(col) }, uSoft: { value: soft } };
  const m = new THREE.ShaderMaterial({ uniforms: u, transparent: true, depthWrite: false, blending: add ? THREE.AdditiveBlending : THREE.NormalBlending,
    vertexShader: `attribute vec3 aVel; attribute vec2 aLife; attribute float aSize; uniform float uT, uPx, uGrav, uDrag; varying float vA;
      void main(){ float age = uT - aLife.x, k = age / aLife.y;
        vec3 p = position + aVel * (uDrag > 0. ? (1. - exp(-uDrag * age)) / uDrag : age) + vec3(0., -0.5 * uGrav * age * age, 0.);
        p.y = max(p.y, 0.01);
        vA = (age < 0. || k > 1.) ? 0. : smoothstep(0., 0.08, k) * (1. - k) * (1. - k);
        vec4 mv = modelViewMatrix * vec4(p, 1.); gl_Position = projectionMatrix * mv;
        gl_PointSize = vA > 0. ? max(1.5, uPx * aSize * (1. + 2. * k) / -mv.z) : 0.; }`,
    fragmentShader: `uniform vec3 uCol; uniform float uGain, uSoft; varying float vA;
      void main(){ float r = length(gl_PointCoord - 0.5) * 2.; if (r > 1.) discard;
        float a = mix(1. - smoothstep(0.5, 1., r), exp(-r * r * 3.), uSoft) * vA;
        gl_FragColor = vec4(uCol * uGain, a); }` });
  const p = new THREE.Points(g, m); p.frustumCulled = false; scene.add(p); return u;
}
const dust = particles(2600, (i, pos, vel, life, size) => {
  const m = pieces[i % pieces.length], c = landAt(m), big = m === pieces[0] ? 2.2 : 1;
  const a = hash(i, 1) * Math.PI * 2, s = (0.6 + 1.8 * hash(i, 2)) * big;
  pos.set([c.x + Math.cos(a) * 0.3 * big, 0.03, c.z + Math.sin(a) * 0.2 * big], i * 3);
  vel.set([Math.cos(a) * s, 0.25 + 0.6 * hash(i, 3), Math.sin(a) * s * 0.8], i * 3);
  life.set([m.userData.tl, 0.9 + 1.4 * hash(i, 4)], i * 2); size[i] = 0.05 + 0.12 * hash(i, 5);
}, { grav: 0.15, drag: 2.6, col: '#8f8a84', gain: 0.55, soft: 1, add: false });
const sparks = particles(500, (i, pos, vel, life, size) => {
  const c = landAt(pieces[0]); const a = hash(i, 11) * Math.PI * 2, s = 1.5 + 4 * Math.pow(hash(i, 12), 2);
  pos.set([c.x + (hash(i, 13) - 0.5) * 1.6, 0.05, c.z + (hash(i, 14) - 0.5) * 1.6], i * 3);
  vel.set([Math.cos(a) * s, 1.5 + 3 * hash(i, 15), Math.sin(a) * s], i * 3);
  life.set([T.b + 0.01 * hash(i, 16), 0.3 + 0.6 * hash(i, 17)], i * 2); size[i] = 0.01 + 0.02 * hash(i, 18);
}, { grav: 9, drag: 0.8, col: '#ffb24a', gain: 5, soft: 0.2 });

// ---------------------------------------------------------------- frame
const FALL = 0.34;
window.renderFrame = t => {
  let shake = 0;
  pieces.forEach(m => {
    const { tl, home, seed } = m.userData;
    if (t < tl - FALL) { m.visible = false; return; }
    m.visible = true;
    if (t < tl) {
      const k = (t - (tl - FALL)) / FALL;
      m.position.set(home.x, home.y, home.z + 6 * (1 - k * k));
      m.rotation.set((seed - 0.5) * 0.5 * (1 - k), (hash(seed, 2) - 0.5) * 0.5 * (1 - k), (hash(seed, 3) - 0.5) * 0.4 * (1 - k));
      m.scale.set(1, 1, 1 + 0.15 * k);
      return;
    }
    const dt = t - tl, sq = 0.25 * Math.exp(-dt * 12) * Math.cos(dt * 34);
    m.position.copy(home); m.rotation.set(0, 0, 0); m.scale.set(1 + 0.25 * sq, 1 + 0.25 * sq, 1 - sq);
    shake += (m === pieces[0] ? 0.5 : m === pieces[pieces.length - 1] ? 0.22 : 0.12) * Math.exp(-dt * 10);
  });
  dust.uT.value = sparks.uT.value = t;
  // camera: low and close while things land, then crane up to a near top-down hero view
  const rise = io(prog(t, T.rise, T.rise1 - T.rise));
  const el = THREE.MathUtils.degToRad(lerp(30, 82, rise)), az = lerp(-0.32, 0, rise) + 0.04 * Math.sin(t * 0.4) * (1 - rise);
  const d = fit(32) * lerp(0.68, 1.0, rise);
  const look = new THREE.Vector3(0, 0, lerp(0.4, 0.04, rise));
  const sx = shake * noise(t * 45, 1), sy = shake * noise(t * 45, 2);
  camera.position.set(look.x + d * Math.sin(az) * Math.cos(el) + sx, d * Math.sin(el) + sy, look.z + d * Math.cos(az) * Math.cos(el));
  camera.lookAt(look);
  warm.intensity = 30 + 40 * Math.exp(-6 * Math.max(0, t - T.b)) * +(t > T.b);
  film.uniforms.uGrain.value = 0.04; film.uniforms.uVig.value = 0.45; film.uniforms.uChroma.value = 0.0006;
  film.uniforms.uFlash.value = 0.1 * Math.exp(-16 * Math.max(0, t - T.b)) * +(t >= T.b);
  film.uniforms.uFade.value = 1 - clamp(prog(t, 0, 0.25));
  S.render(t);
};
resolveReady();
