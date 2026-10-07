// B monogram logo animation.
//   0.35-2.25  light trace: comet heads race round both outlines (front + back edge) from the 45° notch
//   1.95-3.30  scan: the solid fills in along the 45° diagonal behind a hot scan edge, camera swings to the front
//   3.30       impact: flash, shockwave, spark burst
//   3.90-5.30  hero: light sweep across the ceramic face, reflections slide over the chrome sides
//   5.60-6.55  dolly zoom flattens the perspective and the 3D B resolves into the exact flat white logo
import { stage, E, canvasTex, THREE, W, H } from '/batch2/lib/stage.js';
import { toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.5, bloomThreshold: 1.0, bloomRadius: 0.35, bg: '#000000', fov: 30, env: false, samples: 4,
  timeline: '/logo-b/work/timeline.json' });
const { scene, camera, renderer, film, bloom } = S, T = S.TL;
const { clamp, prog, lerp, out, io, ioexpo, expo, hash, noise } = E;
const PX = H / 1080;                                        // resolution scale for point sizes

// ---------------------------------------------------------------- geometry
const G = await (await fetch('/logo-b/work/logo.json?' + Math.random())).json();
const DEPTH = 0.42, BEV = 0.022, ZF = DEPTH / 2;            // ZF: front edge of the side walls
const LOGO_W = 3.615, LOGO_H = 3.57;
const shapeOf = pts => { const s = new THREE.Shape(); pts.forEach(([x, y], i) => i ? s.lineTo(x, y) : s.moveTo(x, y)); s.closePath(); return s; };
const shapes = [shapeOf(G.stem), shapeOf(G.body)];

function solid(shape) {
  let g = new THREE.ExtrudeGeometry(shape, { depth: DEPTH, curveSegments: 1, bevelEnabled: true, bevelThickness: BEV,
    bevelSize: BEV, bevelOffset: -BEV, bevelSegments: 6 });
  g.translate(0, 0, -DEPTH / 2);
  g = toCreasedNormals(g, Math.PI / 7);                     // smooth arcs + bevel, keep the hard corners
  const caps = g.groups[0], n = g.attributes.normal, p = g.attributes.position;
  for (let i = caps.start; i < caps.start + caps.count; i++) n.setXYZ(i, 0, 0, Math.sign(p.getZ(i)));   // dead-flat faces
  return g;
}

// ---------------------------------------------------------------- studio env: strip lights + horizon wall (chrome needs something to reflect)
function stripEnv() {
  const sc = new THREE.Scene(); sc.background = new THREE.Color('#010102');
  const strip = (w, h, pos, rot, c, k) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(c).multiplyScalar(k), side: THREE.DoubleSide }));
    m.position.set(...pos); m.rotation.set(...rot); sc.add(m); };
  strip(1.0, 14, [-6, 0, 2], [0, Math.PI / 2, 0], '#ffffff', 2.4);
  strip(0.5, 14, [6, 0, 0], [0, -Math.PI / 2, 0], '#ffffff', 1.8);
  strip(14, 0.7, [0, 6, 2], [Math.PI / 2, 0, 0], '#ffffff', 1.3);
  strip(0.35, 10, [3.5, 0, -6], [0, 0, 0], '#cfe0ff', 1.6);
  strip(3, 3, [-2, 2, 7], [0, Math.PI, 0], '#9fb6ff', 0.5);
  const hz = canvasTex(64, 512), c = hz.ctx, g = c.createLinearGradient(0, 0, 0, 512);
  g.addColorStop(0, '#07080c'); g.addColorStop(0.40, '#4b5266'); g.addColorStop(0.5, '#ffffff'); g.addColorStop(0.53, '#b9c2da');
  g.addColorStop(0.62, '#1d1f27'); g.addColorStop(1, '#0a0a0d'); c.fillStyle = g; c.fillRect(0, 0, 64, 512); hz.update();
  const front = new THREE.Mesh(new THREE.PlaneGeometry(30, 16), new THREE.MeshBasicMaterial({ map: hz.tex, side: THREE.DoubleSide }));
  front.position.set(0, 0, 9); front.rotation.y = Math.PI; sc.add(front);
  return new THREE.PMREMGenerator(renderer).fromScene(sc, 0.02).texture;
}
const ENV = stripEnv();

// ---------------------------------------------------------------- materials: white ceramic face, polished chrome sides
const U = { uScan: { value: -9 }, uScanW: { value: 0.06 }, uScanCol: { value: new THREE.Color(0, 0, 0) },
  uSweep: { value: -9 }, uSweepCol: { value: new THREE.Color(0, 0, 0) } };
function scanned(mat) {
  mat.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, U);
    sh.vertexShader = 'varying vec3 vLP;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n vLP = position;');
    sh.fragmentShader = `varying vec3 vLP; uniform float uScan, uScanW, uSweep; uniform vec3 uScanCol, uSweepCol;\n` + sh.fragmentShader
      .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
        float sd = dot(vLP.xy, vec2(0.70710678, -0.70710678));        // along the logo's 45° cut
        if (sd > uScan) discard;
        float edge = exp(-pow((uScan - sd) / uScanW, 2.0)) + 0.25 * exp(-(uScan - sd) / (uScanW * 6.0));`)
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
        float sw = dot(vLP.xy, vec2(0.8660254, 0.5)) - uSweep;
        totalEmissiveRadiance += uScanCol * edge + uSweepCol * (exp(-sw * sw / 0.05) + 0.35 * exp(-sw * sw / 0.6));`);
  };
  return mat;
}
const face = scanned(new THREE.MeshPhysicalMaterial({ color: '#e9ebef', metalness: 0, roughness: 0.3, clearcoat: 1,
  clearcoatRoughness: 0.05, envMap: ENV, envMapIntensity: 1.1 }));
const side = scanned(new THREE.MeshPhysicalMaterial({ color: '#e3e7ee', metalness: 1, roughness: 0.07, envMap: ENV, envMapIntensity: 1.35 }));

const logo = new THREE.Group(); scene.add(logo);
const solids = shapes.map(sh => { const m = new THREE.Mesh(solid(sh), [face, side]); logo.add(m); return m; });

scene.add(new THREE.AmbientLight('#ffffff', 0.15));
const key = new THREE.DirectionalLight('#ffffff', 1.1); key.position.set(-4, 5, 8); scene.add(key);
const pool = new THREE.PointLight('#ffffff', 22, 0, 1.6); pool.position.set(-2.2, 2.4, 3.2); scene.add(pool);   // falloff across the face
const fill = new THREE.DirectionalLight('#bcd0ff', 0.8); fill.position.set(6, -1, 5); scene.add(fill);
const rim = new THREE.DirectionalLight('#ffffff', 2.0); rim.position.set(2, 3, -6); scene.add(rim);

// ---------------------------------------------------------------- flat logo (the final frame: exactly the supplied artwork)
const flatMat = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0, depthWrite: false });
const flat = new THREE.Mesh(new THREE.ShapeGeometry(shapes, 1), flatMat);
flat.position.z = ZF + BEV + 0.002; flat.renderOrder = 5; scene.add(flat);

// ---------------------------------------------------------------- light-trace outlines
// each outline starts at the middle of its 45° cut, two heads race round in opposite directions and meet halfway
const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
function loop(pts, cutIndex) {          // segment pts[cutIndex] -> pts[cutIndex+1] is the 45° cut
  const n = pts.length, a = pts[cutIndex], b = pts[(cutIndex + 1) % n], m = mid(a, b), seq = [m];
  for (let k = 1; k <= n; k++) seq.push(pts[(cutIndex + k) % n]);
  seq.push(m); return seq;
}
const loops = [loop(G.stem, 0), loop(G.body, G.body.length - 1)];
const traceU = { uHead: { value: 0 }, uGain: { value: 1 }, uTail: { value: 1 } };
const traceMat = new THREE.ShaderMaterial({ uniforms: traceU, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  vertexShader: `varying float vU; void main(){ vU = uv.x; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `varying float vU; uniform float uHead, uGain, uTail;
    void main(){ float a = min(vU, 1. - vU); if (a > uHead) discard;
      float d = uHead - a; float k = uTail * (1.05 + 9. * exp(-d * 60.));
      gl_FragColor = vec4(vec3(0.82, 0.9, 1.0) * k * uGain, 1.); }` });
const curves = [];
for (const L of loops) for (const z of [ZF, -ZF]) {
  const path = new THREE.CurvePath();
  for (let i = 0; i < L.length - 1; i++) path.add(new THREE.LineCurve3(new THREE.Vector3(L[i][0], L[i][1], z), new THREE.Vector3(L[i + 1][0], L[i + 1][1], z)));
  curves.push(path);
  const len = path.getLength();
  scene.add(new THREE.Mesh(new THREE.TubeGeometry(path, Math.ceil(len * 160), 0.0075, 6, false), traceMat));
}
const headAt = t => 0.5 * io(prog(t, T.trace0, T.trace1 - T.trace0));

// glow sprites (comet heads, flares)
function glowTex(n = 128, hard = 0.0) {
  const g = canvasTex(n, n), c = g.ctx, r = c.createRadialGradient(n / 2, n / 2, 0, n / 2, n / 2, n / 2);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.08 + hard, 'rgba(255,255,255,0.7)'); r.addColorStop(0.3, 'rgba(255,255,255,0.12)');
  r.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = r; c.fillRect(0, 0, n, n); g.update(); return g.tex;
}
function streakTex() {
  const g = canvasTex(512, 32), c = g.ctx, img = c.createImageData(512, 32);
  for (let y = 0; y < 32; y++) for (let x = 0; x < 512; x++) {
    const dx = (x - 255.5) / 256, dy = (y - 15.5) / 16, v = Math.exp(-dy * dy * 14) * Math.pow(1 - Math.abs(dx), 2.2);
    const i = (y * 512 + x) * 4; img.data[i] = img.data[i + 1] = img.data[i + 2] = 255; img.data[i + 3] = 255 * v;
  }
  c.putImageData(img, 0, 0); g.update(); return g.tex;
}
const GLOW = glowTex(), STREAK = streakTex();
const sprite = (tex, col) => { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, color: new THREE.Color(col),
  blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, depthTest: false })); scene.add(s); return s; };
const heads = curves.flatMap(() => [0, 1].map(() => ({ glow: sprite(GLOW, '#cfe2ff'), streak: sprite(STREAK, '#9fc4ff') })));

// ---------------------------------------------------------------- particles: sparks off the heads, impact burst, dust
function particles(n, fill, { grav = 0, drag = 2.5, col = '#d6e6ff', gain = 3, soft = 0.35 } = {}) {
  const pos = new Float32Array(n * 3), vel = new Float32Array(n * 3), life = new Float32Array(n * 2), size = new Float32Array(n);
  for (let i = 0; i < n; i++) fill(i, pos, vel, life, size);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('aVel', new THREE.BufferAttribute(vel, 3));
  g.setAttribute('aLife', new THREE.BufferAttribute(life, 2)); g.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
  const u = { uT: { value: 0 }, uPx: { value: PX * 900 }, uGrav: { value: grav }, uDrag: { value: drag }, uGain: { value: gain },
    uCol: { value: new THREE.Color(col) }, uSoft: { value: soft } };
  const m = new THREE.ShaderMaterial({ uniforms: u, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `attribute vec3 aVel; attribute vec2 aLife; attribute float aSize; uniform float uT, uPx, uGrav, uDrag; varying float vA;
      void main(){ float age = uT - aLife.x, k = age / aLife.y;
        vec3 p = position + aVel * (uDrag > 0. ? (1. - exp(-uDrag * age)) / uDrag : age) + vec3(0., -0.5 * uGrav * age * age, 0.);
        vA = (age < 0. || k > 1.) ? 0. : smoothstep(0., 0.06, k) * (1. - k) * (1. - k);
        vec4 mv = modelViewMatrix * vec4(p, 1.); gl_Position = projectionMatrix * mv;
        gl_PointSize = vA > 0. ? max(1.5, uPx * aSize / -mv.z) : 0.; }`,
    fragmentShader: `uniform vec3 uCol; uniform float uGain, uSoft; varying float vA;
      void main(){ float r = length(gl_PointCoord - 0.5) * 2.; if (r > 1.) discard;
        float a = mix(1. - smoothstep(0.5, 1., r), exp(-r * r * 4.), uSoft) * vA;
        gl_FragColor = vec4(uCol * uGain * a, 1.); }` });
  const p = new THREE.Points(g, m); p.frustumCulled = false; scene.add(p); return u;
}
const V = new THREE.Vector3();
const sparks = particles(900, (i, pos, vel, life, size) => {
  const tb = lerp(T.trace0 + 0.05, T.trace1 - 0.1, Math.pow(hash(i, 1), 0.9)), c = curves[Math.floor(hash(i, 2) * curves.length)];
  const h = headAt(tb), u = hash(i, 3) < 0.5 ? h : 1 - h;
  c.getPointAt(clamp(u, 0, 1), V); pos.set([V.x, V.y, V.z], i * 3);
  const a = hash(i, 4) * Math.PI * 2, s = 0.4 + 1.6 * Math.pow(hash(i, 5), 2);
  vel.set([Math.cos(a) * s, Math.sin(a) * s + 0.5, (hash(i, 6) - 0.4) * s * 1.4], i * 3);
  life.set([tb, 0.25 + 0.6 * hash(i, 7)], i * 2); size[i] = 0.01 + 0.025 * hash(i, 8);
}, { grav: 2.2, drag: 2.0, gain: 5, soft: 0.2 });
const burst = particles(1600, (i, pos, vel, life, size) => {
  const c = curves[Math.floor(hash(i, 12) * curves.length)]; c.getPointAt(hash(i, 13), V);
  pos.set([V.x, V.y, V.z * 2.5], i * 3);
  const d = Math.hypot(V.x, V.y) + 0.3, s = 1.2 + 4.5 * Math.pow(hash(i, 14), 2.5);
  vel.set([V.x / d * s + (hash(i, 15) - 0.5), V.y / d * s + (hash(i, 16) - 0.5), (hash(i, 17) - 0.3) * s * 1.2], i * 3);
  life.set([T.impact + 0.02 * hash(i, 18), 0.5 + 1.4 * Math.pow(hash(i, 19), 1.5)], i * 2); size[i] = 0.008 + 0.03 * Math.pow(hash(i, 20), 3);
}, { grav: 0.4, drag: 2.2, gain: 4, soft: 0.3 });
const dust = particles(1400, (i, pos, vel, life, size) => {
  pos.set([(hash(i, 21) - 0.5) * 22, (hash(i, 22) - 0.5) * 13, -9 + 15 * hash(i, 23)], i * 3);
  vel.set([(hash(i, 24) - 0.5) * 0.12, 0.05 + 0.08 * hash(i, 25), (hash(i, 26) - 0.5) * 0.1], i * 3);
  life.set([-1 - 4 * hash(i, 27), 12], i * 2); size[i] = 0.008 + 0.03 * Math.pow(hash(i, 28), 4);
}, { grav: 0, drag: 0, gain: 0.5, col: '#9fb2d6', soft: 1 });

// ---------------------------------------------------------------- atmosphere: back plate, backlight halo, shockwave ring, streak flare
const plateT = canvasTex(512, 512); { const c = plateT.ctx, g = c.createRadialGradient(256, 256, 0, 256, 256, 256);
  g.addColorStop(0, '#1c2230'); g.addColorStop(0.45, '#0b0d13'); g.addColorStop(1, '#000000'); c.fillStyle = g; c.fillRect(0, 0, 512, 512); plateT.update(); }
const plate = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshBasicMaterial({ map: plateT.tex, transparent: true, depthWrite: false }));
plate.position.z = -10; scene.add(plate);
const halo = new THREE.Mesh(new THREE.PlaneGeometry(10, 10), new THREE.MeshBasicMaterial({ map: GLOW, color: '#7f9dd6', transparent: true,
  blending: THREE.AdditiveBlending, depthWrite: false })); halo.position.z = -1.6; scene.add(halo);
const ringT = canvasTex(512, 512); { const c = ringT.ctx, g = c.createRadialGradient(256, 256, 0, 256, 256, 256);
  g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.86, 'rgba(255,255,255,0)'); g.addColorStop(0.95, 'rgba(255,255,255,1)');
  g.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = g; c.fillRect(0, 0, 512, 512); ringT.update(); }
const ring = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: ringT.tex, color: '#cfe0ff', transparent: true,
  blending: THREE.AdditiveBlending, depthWrite: false })); ring.position.z = -0.4; scene.add(ring);
const flare = sprite(STREAK, '#a9c8ff'), flareCore = sprite(GLOW, '#ffffff');

// ---------------------------------------------------------------- camera: fit the final logo to the frame for any aspect
const ASP = W / H, VIS_H = Math.max(LOGO_H / 0.40, LOGO_W / 0.60 / ASP);
const fitDist = fov => VIS_H / (2 * Math.tan(THREE.MathUtils.degToRad(fov) / 2));
const deg = THREE.MathUtils.degToRad;
function cameraAt(t) {
  const sw = io(prog(t, T.scan0, T.impact - T.scan0));                  // swing to the front, lands on the impact
  const settle = prog(t, T.impact, 2.3), dz = ioexpo(prog(t, T.flat0, T.flat1 - T.flat0));
  let az = lerp(lerp(-64, -40, io(prog(t, 0, T.trace1))), 15, sw);
  az = lerp(az, lerp(15, 9, io(settle)), +(t > T.impact)); az = lerp(az, 0, dz);
  let el = lerp(lerp(17, 11, io(prog(t, 0, T.trace1))), 7, sw); el = lerp(el, lerp(7, 4, io(settle)), +(t > T.impact)); el = lerp(el, 0, dz);
  let m = lerp(lerp(0.4, 0.66, io(prog(t, 0, T.trace1))), 1.1, sw); m = lerp(m, lerp(1.1, 1.0, out(settle)), +(t > T.impact));
  m = lerp(m, 1.0, dz);
  const fov = lerp(30, 5, dz);
  const lp = io(prog(t, 0, T.trace1));
  const look = new THREE.Vector3(lerp(lerp(-0.85, -0.2, lp), 0, sw), lerp(lerp(1.2, 0.45, lp), 0, sw), 0);   // opens on the 45° notch
  const d = m * fitDist(fov);
  // handheld drift (fades out for the lock-up) + a kick on the impact
  const live = 1 - dz, kick = Math.exp(-9 * Math.max(0, t - T.impact)) * +(t > T.impact);
  const jx = (noise(t * 0.6, 1) * 0.6 + 6 * kick * noise(t * 30, 3)) * live, jy = (noise(t * 0.5, 2) * 0.5 + 6 * kick * noise(t * 30, 4)) * live;
  const a = deg(az + jx), e = deg(el + jy);
  camera.fov = fov; camera.updateProjectionMatrix();
  camera.position.set(look.x + d * Math.sin(a) * Math.cos(e), look.y + d * Math.sin(e), d * Math.cos(a) * Math.cos(e));
  camera.lookAt(look);
}

// ---------------------------------------------------------------- frame
const SCAN0 = -2.65, SCAN1 = 2.75;                                       // range of the 45° scan coordinate over the logo
window.renderFrame = t => {
  cameraAt(t);
  const dz = ioexpo(prog(t, T.flat0, T.flat1 - T.flat0)), live = 1 - dz;
  // trace
  const h = headAt(t), hit = Math.exp(-7 * Math.max(0, t - T.impact)) * +(t >= T.impact);
  traceU.uHead.value = h;
  traceU.uGain.value = clamp(prog(t, T.trace0 - 0.05, 0.12)) * (1 - prog(t, T.impact + 0.05, 0.45)) * (1 + 3 * hit);
  traceU.uTail.value = lerp(1, 0.35, prog(t, T.scan0, T.impact - T.scan0));
  let hi = 0;
  curves.forEach((c, ci) => [h, 1 - h].forEach(u => {
    const H_ = heads[hi++]; c.getPointAt(clamp(u, 0, 1), V);
    const on = clamp(prog(t, T.trace0 - 0.05, 0.1)) * (1 - prog(t, T.trace1 - 0.15, 0.25)) * (ci % 2 ? 0.55 : 1);
    H_.glow.position.copy(V); H_.glow.scale.setScalar(0.22); H_.glow.material.color.set('#cfe2ff').multiplyScalar(2.2 * on);
    H_.streak.position.copy(V); H_.streak.scale.set(1.6, 0.05, 1); H_.streak.material.color.set('#9fc4ff').multiplyScalar(1.6 * on);
    H_.glow.visible = H_.streak.visible = on > 0.001;
  }));
  // scan + sweep on the solid
  const sp = prog(t, T.scan0, T.impact - T.scan0 - 0.05);
  U.uScan.value = sp <= 0 ? -9 : lerp(SCAN0, SCAN1, io(sp));
  U.uScanCol.value.setRGB(0.75, 0.88, 1).multiplyScalar(6 * (1 - prog(t, T.impact - 0.1, 0.25)));
  const swp = prog(t, T.sweep0, T.sweep1 - T.sweep0);
  U.uSweep.value = lerp(-3.4, 3.4, io(swp)); U.uSweepCol.value.setScalar(1.1 * Math.sin(Math.PI * swp));
  logo.visible = t >= T.scan0 && t < T.flat1 + 0.05;
  const er = deg(lerp(-70, 30, io(prog(t, T.scan0, T.sweep1 - T.scan0))) + 25 * io(prog(t, T.sweep1, 1.5)));
  face.envMapRotation.set(0, er, 0); side.envMapRotation.set(0, er, 0);
  // flat lock-up: ACES for the 3D section, untonemapped pure white for the final artwork
  const lock = t >= T.flat1;
  renderer.toneMapping = lock ? THREE.NoToneMapping : THREE.ACESFilmicToneMapping;
  flatMat.opacity = io(prog(t, T.flat0 + 0.45, T.flat1 - T.flat0 - 0.45));
  flatMat.color.setScalar(lock ? 1 : 7);
  // particles + atmosphere
  sparks.uT.value = burst.uT.value = dust.uT.value = t;
  dust.uGain.value = 0.55 * clamp(prog(t, 0, 0.8)) * live;
  plate.material.opacity = 0.9 * clamp(prog(t, 0.0, 1.2)) * live * (1 + 0.3 * hit);
  halo.material.opacity = live * (0.10 * clamp(prog(t, T.scan0, 1)) + 0.5 * hit + 0.08 * Math.sin(Math.PI * swp));
  halo.scale.setScalar(1 + 0.3 * hit);
  const rp = prog(t, T.impact, 1.0); ring.visible = rp > 0 && rp < 1;
  ring.scale.setScalar(lerp(2, 16, out(rp))); ring.material.opacity = 0.7 * Math.pow(1 - rp, 2);
  flare.position.set(0, 0, 0.6); flare.scale.set(lerp(9, 16, out(rp)), 0.18, 1); flare.material.color.set('#a9c8ff').multiplyScalar(3 * hit);
  flareCore.position.set(0, 0, 0.6); flareCore.scale.setScalar(2.4); flareCore.material.color.set('#ffffff').multiplyScalar(1.2 * hit);
  flare.visible = flareCore.visible = hit > 0.002;
  // post: bloom, film look
  bloom.strength = lerp(0.5, 0.35, prog(t, T.impact + 0.4, 1.5)) + 0.5 * hit;
  bloom.strength = lerp(bloom.strength, 0.07, dz); bloom.threshold = lock ? 0.9 : 1.0;
  film.uniforms.uGrain.value = 0.035 * live; film.uniforms.uVig.value = 0.35 * live;
  film.uniforms.uChroma.value = 0.0004 * live + 0.0025 * hit;
  film.uniforms.uFlash.value = 0.12 * Math.exp(-14 * Math.max(0, t - T.impact)) * +(t >= T.impact);
  film.uniforms.uFade.value = 1 - clamp(prog(t, 0, 0.25));
  S.render(t);
};
resolveReady();
