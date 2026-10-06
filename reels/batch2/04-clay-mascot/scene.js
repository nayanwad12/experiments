// B2-04 Clay mascot: 3D plasticine character on a tabletop set, stop-motion on twos, lip-synced to the voice.
import { stage, E, canvasTex, rr, THREE } from '/batch2/lib/stage.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.2, bloomThreshold: 1.2, bg: '#f2d9c9', fov: 30, shadows: true, envIntensity: 0.35, exposure: 1.05,
  timeline: '/batch2/04-clay-mascot/work/timeline.json', fonts: [['IT8', 'InterTight-800.ttf'], ['IT5', 'InterTight-500.ttf']] });
const { scene, camera, renderer } = S, T = S.TL;
const { clamp, prog, lerp, out, io, expo, back, hash, noise } = E;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
S.film.uniforms.uGrain.value = 0.03; S.film.uniforms.uVig.value = 0.45; S.film.uniforms.uChroma.value = 0.0006;

// ---------------------------------------------------------------- clay material (thumbprint bump + per-drawing boil)
const clayTex = await new THREE.TextureLoader().loadAsync('/batch2/04-clay-mascot/work/clay_tex.png');
clayTex.wrapS = clayTex.wrapT = THREE.RepeatWrapping; clayTex.repeat.set(2, 2);
const boil = { uSeed: { value: 0 }, uAmp: { value: 0.012 } };
const mats = [];
function clay(hex, rough = 0.82, bump = 0.035) {
  const m = new THREE.MeshStandardMaterial({ color: hex, roughness: rough, metalness: 0, bumpMap: clayTex, bumpScale: bump });
  m.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, boil);
    sh.vertexShader = 'uniform float uSeed; uniform float uAmp;\n' + sh.vertexShader.replace('#include <begin_vertex>',
      `#include <begin_vertex>
       vec3 q = position * 3.1 + vec3(uSeed * 7.13, uSeed * 3.71, uSeed * 5.19);
       transformed += normal * uAmp * (sin(q.x) * sin(q.y * 1.3) + sin(q.z * 0.9 + q.x));`);
  };
  mats.push(m); return m;
}
const wireMat = new THREE.MeshBasicMaterial({ color: '#D4FF3F', wireframe: true });

// ---------------------------------------------------------------- set: cyclorama + tabletop
const cycTex = canvasTex(32, 512); { const c = cycTex.ctx, g = c.createLinearGradient(0, 0, 0, 512);
  g.addColorStop(0, '#f6c9b8'); g.addColorStop(1, '#fbe8dc'); c.fillStyle = g; c.fillRect(0, 0, 32, 512); cycTex.update(); }
const cyc = new THREE.Mesh(new THREE.PlaneGeometry(40, 30), new THREE.MeshStandardMaterial({ map: cycTex.tex, roughness: 1 }));
cyc.position.set(0, 6, -6); cyc.receiveShadow = true; scene.add(cyc);
const table = new THREE.Mesh(new RoundedBoxGeometry(14, 0.5, 8, 4, 0.2), clay('#c98a55', 0.85, 0.05));
table.position.set(0, -0.25, -0.5); table.receiveShadow = true; table.userData.mat = table.material; scene.add(table);

const hemi = new THREE.HemisphereLight('#fff4ea', '#a8806a', 0.9); scene.add(hemi);
const key = new THREE.DirectionalLight('#fff1e0', 2.3); key.position.set(3.5, 6, 5); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 6; key.shadow.bias = -0.0005;
Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -3, near: 1, far: 25 }); scene.add(key);
const rim = new THREE.DirectionalLight('#c7d8ff', 1.1); rim.position.set(-4, 3, -4); scene.add(rim);

// ---------------------------------------------------------------- the mascot
const M = new THREE.Group(); scene.add(M);
const LIMEC = '#9fd43a', DARK = '#3d6b1c';
const sph = (r, hex, ws = 48, hs = 32) => { const m = new THREE.Mesh(new THREE.SphereGeometry(r, ws, hs), clay(hex)); m.castShadow = true; return m; };
const bodyG = new THREE.Group(); M.add(bodyG);
const body = sph(1, LIMEC, 72, 54); body.scale.set(1, 1.06, 0.94); bodyG.add(body);
const head = new THREE.Group(); head.position.set(0, 0.15, 0); bodyG.add(head);
const eyes = [-1, 1].map(sx => {
  const g = new THREE.Group(); g.position.set(sx * 0.33, 0.3, 0.76); head.add(g);
  const white = sph(0.25, '#fbfbf5'); g.add(white);
  const pupil = sph(0.11, '#141414'); pupil.position.z = 0.18; g.add(pupil);
  const glint = sph(0.035, '#ffffff', 12, 8); glint.position.set(0.04, 0.05, 0.28); g.add(glint);
  const lid = sph(0.27, LIMEC); lid.scale.set(1.04, 0.5, 1.04); lid.position.set(0, 0.2, 0.0); g.add(lid);
  const brow = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.22, 6, 12), clay(DARK)); brow.rotation.z = Math.PI / 2; brow.position.set(0, 0.38, 0.12); g.add(brow);
  return { g, pupil, glint, lid, brow, sx };
});
const mouth = new THREE.Group(); mouth.position.set(0, -0.2, 0.9); head.add(mouth);
const mOuter = sph(0.2, '#4a1520'); mOuter.scale.set(1, 0.5, 0.35); mouth.add(mOuter);
const tongue = sph(0.12, '#e2667a'); tongue.scale.set(1, 0.45, 0.5); tongue.position.set(0, -0.06, 0.04); mouth.add(tongue);
const teeth = new THREE.Mesh(new RoundedBoxGeometry(0.22, 0.05, 0.05, 2, 0.02), clay('#fbfbf5')); teeth.position.set(0, 0.06, 0.06); mouth.add(teeth);
const lipLine = new THREE.Mesh(new THREE.CapsuleGeometry(0.03, 0.26, 6, 12), clay(DARK)); lipLine.rotation.z = Math.PI / 2; mouth.add(lipLine);
for (const sx of [-1, 1]) { const ch = sph(0.11, '#f48b9e'); ch.scale.set(1, 0.6, 0.4); ch.position.set(sx * 0.58, -0.08, 0.72); head.add(ch); }
const ant = new THREE.Mesh(new THREE.CapsuleGeometry(0.035, 0.45, 6, 12), clay(DARK)); ant.position.set(0.12, 1.25, 0); ant.rotation.z = -0.25; bodyG.add(ant);
const antBall = sph(0.1, '#ff6b6b'); antBall.position.set(0.2, 1.52, 0); bodyG.add(antBall);
const arms = [-1, 1].map(sx => { const piv = new THREE.Group(); piv.position.set(sx * 0.9, -0.15, 0.1); bodyG.add(piv);
  const a = new THREE.Mesh(new THREE.CapsuleGeometry(0.12, 0.45, 8, 16), clay(LIMEC)); a.castShadow = true; a.position.set(sx * 0.18, -0.25, 0); a.rotation.z = sx * 0.5; piv.add(a);
  const hnd = sph(0.15, LIMEC); hnd.position.set(sx * 0.36, -0.55, 0); piv.add(hnd); return { piv, sx }; });
const feet = [-1, 1].map(sx => { const f = sph(0.26, DARK); f.scale.set(1.1, 0.5, 1.3); f.position.set(sx * 0.42, -1.0, 0.25); M.add(f); return f; });
M.position.set(0, 1.08, 0.4);
M.traverse(o => { if (o.isMesh) { o.castShadow = true; o.userData.mat = o.material; } });

// ---------------------------------------------------------------- the giant finger
const finger = new THREE.Group(); scene.add(finger);
const fBody = new THREE.Mesh(new THREE.CapsuleGeometry(0.42, 3.2, 12, 24), clay('#e7b48c', 0.8, 0.05)); fBody.castShadow = true; finger.add(fBody);
const nail = sph(0.3, '#f5d5c4'); nail.scale.set(1, 1.3, 0.35); nail.position.set(0, -1.55, 0.3); finger.add(nail);

// ---------------------------------------------------------------- world pieces (drop in on "One prompt built my whole world")
const world = [];
function piece(obj, x, y, z, delay) { obj.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; o.userData.mat = o.material; } });
  scene.add(obj); world.push({ obj, home: new THREE.Vector3(x, y, z), delay }); return obj; }
// back wall with a window and a sun
const wallG = new THREE.Group();
const wall = new THREE.Mesh(new RoundedBoxGeometry(12, 7, 0.4, 3, 0.15), clay('#9ccbe8', 0.9, 0.04)); wallG.add(wall);
const win = new THREE.Mesh(new RoundedBoxGeometry(2.8, 2.2, 0.5, 3, 0.15), clay('#fff3d6')); win.position.set(-2.4, 0.7, 0.05); wallG.add(win);
const sky = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 1.8), new THREE.MeshBasicMaterial({ color: '#8fd3ff' })); sky.position.set(-2.4, 0.7, 0.31); wallG.add(sky);
const sunM = sph(0.35, '#ffcf3a'); sunM.position.set(-1.9, 1.05, 0.35); wallG.add(sunM);
const mull = new THREE.Mesh(new RoundedBoxGeometry(0.12, 1.9, 0.12, 2, 0.04), clay('#fff3d6')); mull.position.set(-2.4, 0.7, 0.36); wallG.add(mull);
piece(wallG, 0, 3.0, -3.6, 0.0);
// plant
const plant = new THREE.Group();
const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.32, 0.7, 32), clay('#d4704a')); plant.add(pot);
for (let i = 0; i < 6; i++) { const lf = sph(0.32, '#4fae4a'); lf.scale.set(0.6, 1.3, 0.35); const a = i / 6 * Math.PI * 2;
  lf.position.set(Math.cos(a) * 0.25, 0.75 + 0.15 * (i % 2), Math.sin(a) * 0.25); lf.rotation.set(Math.sin(a) * 0.5, 0, -Math.cos(a) * 0.5); plant.add(lf); }
piece(plant, -2.3, 0.35, 0.2, 0.28);
// laptop with a tiny timeline on screen
const lap = new THREE.Group();
const lbase = new THREE.Mesh(new RoundedBoxGeometry(1.7, 0.1, 1.1, 2, 0.05), clay('#d9dde3')); lap.add(lbase);
const lscr = new THREE.Group(); lscr.position.set(0, 0.05, -0.52); lscr.rotation.x = -0.25; lap.add(lscr);
{ const lid = new THREE.Mesh(new RoundedBoxGeometry(1.7, 1.1, 0.08, 2, 0.05), clay('#d9dde3')); lid.position.set(0, 0.55, 0); lscr.add(lid); }
const lt = canvasTex(512, 320);
const lface = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.92), new THREE.MeshBasicMaterial({ map: lt.tex, toneMapped: false })); lface.position.set(0, 0.55, 0.045); lscr.add(lface);
piece(lap, 2.2, 0.06, 0.6, 0.55);
// lamp
const lamp = new THREE.Group();
const lb = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.4, 0.12, 32), clay('#2f3138')); lamp.add(lb);
const lp = new THREE.Mesh(new THREE.CapsuleGeometry(0.06, 1.6, 6, 12), clay('#2f3138')); lp.position.set(0, 0.85, 0); lamp.add(lp);
const shade = new THREE.Mesh(new THREE.ConeGeometry(0.45, 0.55, 32, 1, true), clay('#ff8a3d')); shade.material.side = THREE.DoubleSide; shade.position.set(0.25, 1.75, 0.1); shade.rotation.z = -0.6; lamp.add(shade);
const bulb = new THREE.PointLight('#ffcf8a', 0, 5); bulb.position.set(0.35, 1.55, 0.2); lamp.add(bulb);
piece(lamp, 3.6, 0.06, -1.4, 0.8);
// mug + books
const mug = new THREE.Group(); mug.add(new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.25, 0.55, 32), clay('#f2f2ee')));
const handle = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.05, 10, 24), clay('#f2f2ee')); handle.position.set(0.3, 0, 0); mug.add(handle);
piece(mug, -1.3, 0.28, 1.4, 1.05);
const books = new THREE.Group(); [['#e05d5d', 0], ['#5d8ee0', 0.26], ['#f2c14e', 0.5]].forEach(([c, y], i) => {
  const b = new THREE.Mesh(new RoundedBoxGeometry(1.2, 0.24, 0.85, 2, 0.05), clay(c)); b.position.set(0.05 * i, y, 0); b.rotation.y = 0.1 * i; books.add(b); });
piece(books, -3.4, 0.12, -1.0, 1.3);

function drawLaptop(t) {
  const c = lt.ctx; c.fillStyle = '#16181f'; c.fillRect(0, 0, 512, 320);
  const commentMode = t >= T.NEXT;
  if (!commentMode) {
    const cols = ['#ff6b6b', '#ffd93d', '#6bcB77', '#4d96ff', '#c77dff'];
    for (let r = 0; r < 4; r++) for (let k = 0; k < 6; k++) { c.fillStyle = cols[(r + k) % 5]; rr(c, 20 + k * 80 + (r % 2) * 20, 40 + r * 60, 66, 40, 8); c.fill(); }
    c.fillStyle = '#ffffff'; c.fillRect(20 + ((t * 120) % 470), 20, 4, 270);
  } else {
    c.fillStyle = '#ffffff'; rr(c, 30, 110, 452, 100, 20); c.fill();
    c.fillStyle = '#0e0e11'; c.font = '700 40px IT8'; const s = 'make a dragon!'; const n = Math.floor(clamp((t - T.COMMENTS) / 1.0) * s.length);
    c.fillText(s.slice(0, n) + (Math.floor(t * 3) % 2 ? '|' : ''), 60, 175);
  }
  lt.update();
}

// ---------------------------------------------------------------- per-frame (stop motion: everything on twos)
const MOUTH = T.MOUTH;
function setWire(on) {
  const all = [M, ...world.map(w => w.obj), table];
  all.forEach(g => g.traverse(o => { if (o.isMesh && o.userData.mat) o.material = on ? wireMat : o.userData.mat; }));
}
window.renderFrame = t => {
  const ts = Math.floor(t * 12) / 12, drawing = Math.floor(t * 12);
  boil.uSeed.value = drawing % 7;
  drawLaptop(ts);
  const f = Math.min(MOUTH.length - 1, Math.round(ts * T.FPS));
  const [mo, mw] = MOUTH[f] || [0, 0.5];
  // --- mascot acting
  const hop = ts < 0.5 ? Math.abs(Math.sin(ts / 0.5 * Math.PI)) * 0.8 * (1 - ts / 0.5) : 0;
  const poke = ts >= T.HAND - 0.05 && ts < T.HAND + 0.7 ? Math.exp(-(ts - T.HAND) * 5) * Math.sin((ts - T.HAND) * 30) : 0;
  const talk = mo;
  bodyG.scale.set(1 + 0.03 * talk + 0.12 * poke, 1 - 0.02 * talk - 0.15 * poke, 1);
  bodyG.rotation.z = 0.25 * poke + 0.04 * Math.sin(ts * 2.1);
  bodyG.position.y = hop;
  M.position.x = lerp(-3.5, 0, out(prog(ts, 0, 0.55)));
  // head tilt & look
  const sort = ts >= T.SORT && ts < T.SORT + 1.1;
  head.rotation.z = sort ? 0.18 : 0.05 * Math.sin(ts * 1.3);
  head.rotation.y = 0.08 * Math.sin(ts * 0.9);
  let look = [0, 0];
  if (sort) look = [0.6, 0.4];
  if (ts >= T.HAND - 0.6 && ts < T.HAND) look = [0.7, 0.8];                              // eyes up at the finger
  if (ts >= T.NOBODY && ts < T.NOBODY + 1.2) look = [Math.sin(ts * 6) * 0.8, 0.1];         // looks around
  if (ts >= T.WORLD && ts < T.WORLD + 1.8) look = [Math.sin((ts - T.WORLD) * 3) * 0.7, 0.35];
  const blink = (drawing % 37 === 0 || drawing % 53 === 0);
  eyes.forEach(e => {
    e.pupil.position.set(look[0] * 0.09, look[1] * 0.09, 0.18);
    e.glint.position.set(0.04 + look[0] * 0.09, 0.05 + look[1] * 0.09, 0.28);
    e.lid.visible = blink; e.lid.position.y = 0.02; e.lid.scale.y = 1.0;
    e.brow.position.y = 0.38 + (sort ? 0.06 * e.sx : 0) + (ts >= T.CODE && ts < T.CODE_END ? 0.07 : 0);
    e.brow.rotation.z = Math.PI / 2 + (ts >= T.NOBODY && ts < T.NOBODY + 1.2 ? -0.25 * e.sx : 0);
  });
  // mouth: open + wide/round, on twos
  const open = Math.max(0.12, mo);
  mOuter.scale.set(lerp(0.75, 1.25, mw) * (0.9 + 0.3 * mo), 0.18 + 0.85 * open, 0.35);
  tongue.visible = mo > 0.25; teeth.visible = mo > 0.35; lipLine.visible = mo < 0.12;
  mouth.scale.setScalar(ts >= T.LIPS && ts < T.LIPS + 1.2 ? 1.25 : 1);
  // arms
  const waving = ts >= T.NEXT + 0.8;
  arms.forEach(a => {
    let z = 0.1 * Math.sin(ts * 3 + a.sx) * talk;
    if (a.sx > 0 && waving) z = 2.2 + 0.5 * Math.sin(ts * 14);
    if (sort) z = a.sx * -0.5 + (a.sx > 0 ? 0.4 : -0.4);                                   // shrug
    if (ts >= T.CODE && ts < T.CODE_END) z = a.sx * 1.4;                                   // ta-da
    a.piv.rotation.z = z * (a.sx > 0 ? 1 : -1) * (a.sx > 0 ? 1 : 1);
  });
  // giant finger
  finger.visible = ts >= T.WEEKS + 0.6 && ts < T.NOBODY + 0.05;
  if (finger.visible) {
    const kin = out(prog(ts, T.WEEKS + 0.6, T.HAND - T.WEEKS - 0.75));
    const back_ = prog(ts, T.HAND + 0.25, 0.6);
    finger.position.set(lerp(5.5, 2.15, kin) + 2.5 * back_, lerp(6.5, 3.0, kin) + 2.5 * back_, 0.9);
    finger.rotation.z = -0.7;
  }
  // world pieces drop in
  const wk = ts >= T.WORLD;
  world.forEach(w => {
    const td = T.WORLD + 0.1 + w.delay, k = clamp((ts - td) / 0.3);
    w.obj.visible = wk && ts >= td;
    if (!w.obj.visible) return;
    w.obj.position.set(w.home.x, w.home.y + (k < 1 ? (1 - k * k) * 6 : 0), w.home.z);
    const sq = ts >= td + 0.3 ? 0.18 * Math.exp(-(ts - td - 0.3) * 9) * Math.cos((ts - td - 0.3) * 30) : 0;
    w.obj.scale.set(1 + sq * 0.5, 1 - sq, 1 + sq * 0.5);
  });
  bulb.intensity = ts >= T.WORLD + 1.1 ? 6 : 0;
  // wireframe twist
  setWire(ts >= T.CODE && ts < T.CODE_END);
  scene.background = new THREE.Color(ts >= T.CODE && ts < T.CODE_END ? '#07090c' : '#f2d9c9');
  cyc.visible = !(ts >= T.CODE && ts < T.CODE_END);
  // --- camera (stepped too, like a real stop-motion rig)
  let cp, cl;
  if (ts < T.WEEKS) { cp = [0.3, 2.1, 10.2]; cl = [0, 1.25, 0]; }
  else if (ts < T.NOBODY) { const k = io(prog(ts, T.WEEKS, T.NOBODY - T.WEEKS)); cp = [lerp(0.3, 1.2, k), lerp(2.1, 2.7, k), lerp(10.2, 11.0, k)]; cl = [0.4, 1.7, 0]; }
  else if (ts < T.CODE) { cp = [0.1, 1.7, 6.4]; cl = [0, 1.3, 0]; }
  else if (ts < T.CODE_END) { const k = io(prog(ts, T.CODE, T.CODE_END - T.CODE)); const a = lerp(-0.2, 1.1, k); cp = [Math.sin(a) * 8.2, 2.0, Math.cos(a) * 8.2]; cl = [0, 1.1, 0]; }
  else if (ts < T.LIPS) { const k = io(prog(ts, T.WORLD, 1.8)); cp = [lerp(0.4, 0.2, k), lerp(2.2, 3.4, k), lerp(7.0, 11.8, k)]; cl = [0, lerp(1.2, 1.6, k), 0]; }
  else if (ts < T.NEXT) { cp = [0.05, 1.35, 4.4]; cl = [0, 1.2, 0.6]; }
  else { const k = io(prog(ts, T.NEXT, 3)); cp = [lerp(1.2, 0.6, k), 2.6, lerp(11.5, 10.6, k)]; cl = [0.3, 1.5, 0]; }
  camera.position.set(...cp); camera.lookAt(...cl);
  // exposure flicker per drawing (stop-motion feel)
  const fl = 1 + 0.02 * (hash(drawing, 4) - 0.5);
  S.film.uniforms.uGain.value.set(fl, fl, fl);
  S.film.uniforms.uFlash.value = (ts >= T.CODE && ts < T.CODE + 0.1) || (ts >= T.CODE_END && ts < T.CODE_END + 0.1) ? 0.5 : 0;
  S.film.uniforms.uFade.value = clamp(1 - t / 0.2);
  S.render(t);
};
window.DBG = { scene, cyc, S };
resolveReady();
