// B2-01 Start Here: wall of live screens -> tunnel flight -> shattering "No" tiles -> glass prompt -> sphere -> logo
import { stage, E, canvasTex, rr, frameSeq, THREE } from '/batch2/lib/stage.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const BASE = '/batch2/01-start-here';
const S = await stage({ bloom: 0.5, bloomThreshold: 1.0, bloomRadius: 0.45, bg: '#04040a', timeline: `${BASE}/work/timeline.json`,
  fonts: [['IT8', 'InterTight-800.ttf'], ['IT5', 'InterTight-500.ttf'], ['JBM', 'JetBrainsMono-500.ttf']] });
const { scene, camera } = S, T = S.TL;
const { clamp, prog, lerp, out, io, expo, back, hash, noise } = E;
scene.fog = new THREE.FogExp2('#04040a', 0.028);
S.film.uniforms.uGrain.value = 0.035;

// ---------------------------------------------------------------- footage textures
const FR = {};
for (const s of T.SRC) FR[s.name] = await frameSeq(`${BASE}/work/tex/${s.name}`, T.NTEX);
const VERT = Object.fromEntries(T.SRC.map(s => [s.name, s.vertical]));
const texAt = (name, t, off = 0) => FR[name][(Math.floor(t * 8) + off) % T.NTEX];

// ---------------------------------------------------------------- screens
const N = 72;
const names = T.SRC.map(s => s.name);
const bezelGeoV = new RoundedBoxGeometry(1.2, 2.06, 0.06, 3, 0.06), bezelGeoH = new RoundedBoxGeometry(2.06, 1.2, 0.06, 3, 0.06);
const planeV = new THREE.PlaneGeometry(1.08, 1.92), planeH = new THREE.PlaneGeometry(1.92, 1.08);
const bezelMat = new THREE.MeshPhysicalMaterial({ color: '#0d0d12', metalness: 0.6, roughness: 0.3, clearcoat: 1 });
const screens = [];
for (let i = 0; i < N; i++) {
  const name = names[Math.floor(hash(i, 3) * names.length)];
  const v = VERT[name];
  const g = new THREE.Group();
  const bz = new THREE.Mesh(v ? bezelGeoV : bezelGeoH, bezelMat); bz.position.z = -0.035; g.add(bz);
  const mat = new THREE.MeshBasicMaterial({ map: FR[name][0], toneMapped: false });
  const sc = new THREE.Mesh(v ? planeV : planeH, mat); g.add(sc);
  scene.add(g);
  screens.push({ g, mat, name, off: Math.floor(hash(i, 9) * T.NTEX) });
}

// wall formation (curved)
function wallPose(i, t) {
  const col = i % 9, row = Math.floor(i / 9);
  const th = (col - 4) * 0.16, R = 16;
  const p = new THREE.Vector3(R * Math.sin(th), (row - 3.5) * 2.3 + 0.25 * Math.sin(t * 1.3 + i), R * (1 - Math.cos(th)) + 0.4 * noise(t * 0.6, i));
  return { p, ry: -th, rx: 0, rz: 0, s: 1 };
}
// tunnel formation (camera flies down -z)
function tunnelPose(i, t) {
  const ring = Math.floor(i / 8), a = (i % 8) / 8 * Math.PI * 2 + ring * 0.45;
  const r = 3.3, z = 4 - ring * 6.2;
  return { p: new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, z), look: new THREE.Vector3(0, 0, z), s: 1 };
}
// sphere formation (facing out)
function spherePose(i) {
  const k = i + 0.5, phi = Math.acos(1 - 2 * k / N), th = Math.PI * (1 + Math.sqrt(5)) * k;
  const R = 7.2;
  const p = new THREE.Vector3(R * Math.sin(phi) * Math.cos(th), R * Math.cos(phi), R * Math.sin(phi) * Math.sin(th));
  return { p, look: p.clone().multiplyScalar(2), s: 1.05 };
}

// ---------------------------------------------------------------- hero screen (fills the frame on each category)
const hero = new THREE.Mesh(new THREE.PlaneGeometry(1.08, 1.92), new THREE.MeshBasicMaterial({ map: FR.clay[0], toneMapped: false, fog: false }));
camera.add(hero); scene.add(camera);
const FILL_D = 1.92 / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));

// ---------------------------------------------------------------- "No" tiles that shatter
const tiles = [];
const LABELS = [['After Effects', 'motion graphics app'], ['Premiere Pro', 'timeline editor'], ['AI video tools', 'text-to-video generators']];
LABELS.forEach(([title, sub], k) => {
  const ct = canvasTex(1200, 600), c = ct.ctx;
  const gr = c.createLinearGradient(0, 0, 0, 600); gr.addColorStop(0, '#20202a'); gr.addColorStop(1, '#0c0c12');
  c.fillStyle = gr; rr(c, 6, 6, 1188, 588, 70); c.fill();
  c.strokeStyle = 'rgba(255,255,255,0.25)'; c.lineWidth = 6; rr(c, 6, 6, 1188, 588, 70); c.stroke();
  c.fillStyle = '#e9e9ef'; c.font = '800 118px IT8'; c.textAlign = 'center'; c.fillText(title, 600, 300);
  c.fillStyle = '#8a8a96'; c.font = '500 52px IT5'; c.fillText(sub, 600, 400);
  ct.update();
  const grp = new THREE.Group(); scene.add(grp);
  const shards = [], nx = 8, ny = 4, w = 3.3, h = 1.65;
  for (let a = 0; a < nx; a++) for (let b = 0; b < ny; b++) {
    const geo = new THREE.PlaneGeometry(w / nx, h / ny);
    const uv = geo.attributes.uv;
    for (let j = 0; j < uv.count; j++) uv.setXY(j, (a + uv.getX(j)) / nx, (b + uv.getY(j)) / ny);
    const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: ct.tex, transparent: true, side: THREE.DoubleSide, fog: false }));
    const home = new THREE.Vector3(-w / 2 + (a + 0.5) * w / nx, -h / 2 + (b + 0.5) * h / ny, 0);
    m.position.copy(home); grp.add(m);
    shards.push({ m, home, v: new THREE.Vector3((home.x) * 2.2 + (hash(a, b, k) - 0.5) * 3, home.y * 2.5 + (hash(b, a, k) - 0.3) * 3, 3 + hash(a + b, k) * 5),
      rot: new THREE.Vector3(hash(a, k, 1) - 0.5, hash(b, k, 2) - 0.5, hash(a, b, 3) - 0.5).multiplyScalar(14) });
  }
  tiles.push({ grp, shards, y: 2.0 - k * 2.0, t: T.NO[k] + 0.15 });
});

// ---------------------------------------------------------------- glass prompt bar
const prompt = new THREE.Group(); scene.add(prompt);
const pbody = new THREE.Mesh(new RoundedBoxGeometry(5.6, 1.7, 0.22, 6, 0.4),
  new THREE.MeshPhysicalMaterial({ color: '#14141c', metalness: 0.2, roughness: 0.12, clearcoat: 1, clearcoatRoughness: 0.05 }));
prompt.add(pbody);
const pt = canvasTex(2048, 622);
const pface = new THREE.Mesh(new THREE.PlaneGeometry(5.6, 1.7), new THREE.MeshBasicMaterial({ map: pt.tex, transparent: true, toneMapped: false }));
pface.position.z = 0.115; prompt.add(pface);
const glowT = canvasTex(256, 256); { const c = glowT.ctx; const g = c.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, 'rgba(212,255,63,0.55)'); g.addColorStop(0.5, 'rgba(212,255,63,0.15)'); g.addColorStop(1, 'rgba(212,255,63,0)'); c.fillStyle = g; c.fillRect(0, 0, 256, 256); glowT.update(); }
const pglow = new THREE.Mesh(new THREE.PlaneGeometry(9, 4.5), new THREE.MeshBasicMaterial({ map: glowT.tex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
pglow.position.z = -0.3; prompt.add(pglow);
const shock = new THREE.Mesh(new THREE.RingGeometry(0.96, 1.0, 96), new THREE.MeshBasicMaterial({ color: '#D4FF3F', transparent: true, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, depthWrite: false }));
scene.add(shock);

function drawPrompt(t) {
  const c = pt.ctx, Wc = 2048, Hc = 622;
  c.clearRect(0, 0, Wc, Hc);
  const s = T.PROMPT, n = Math.floor(s.length * clamp((t - T.TYPE0) / (T.TYPE1 - T.TYPE0)));
  c.font = '500 118px IT5'; c.textBaseline = 'alphabetic'; c.textAlign = 'left';
  // wrap into two lines at the full prompt's break point
  const words = s.split(' '); let l1 = '';
  for (const w of words) { if (c.measureText((l1 + ' ' + w).trim()).width > 1560) break; l1 = (l1 + ' ' + w).trim(); }
  const shown = s.slice(0, n), a1 = shown.slice(0, l1.length), a2 = shown.slice(l1.length).trimStart();
  let cx = 120, cy = 250;
  if (n === 0) { c.fillStyle = '#5c5c66'; c.fillText('Describe your video…', 120, 250); }
  else {
    c.fillStyle = '#f2f2f6'; c.fillText(a1, 120, 250); cx = 120 + c.measureText(a1).width;
    if (a2.length) { c.fillText(a2, 120, 410); cx = 120 + c.measureText(a2).width; cy = 410; }
  }
  if (Math.floor(t * 3) % 2 === 0 || (t > T.TYPE0 && t < T.TYPE1)) { c.fillStyle = '#D4FF3F'; c.fillRect(cx + 10, cy - 100, 12, 128); }
  const ready = t >= T.TYPE1, press = Math.exp(-Math.max(0, t - T.ENTER) * 9) * (t >= T.ENTER);
  const bx = 1880, by = 470;
  c.fillStyle = ready ? '#D4FF3F' : '#2a2a33'; c.beginPath(); c.arc(bx, by, 88 * (1 - 0.15 * press), 0, Math.PI * 2); c.fill();
  c.strokeStyle = ready ? '#0E0E11' : '#6a6a74'; c.lineWidth = 16; c.lineCap = 'round'; c.lineJoin = 'round';
  c.beginPath(); c.moveTo(bx, by + 45); c.lineTo(bx, by - 45); c.moveTo(bx - 35, by - 10); c.lineTo(bx, by - 45); c.lineTo(bx + 35, by - 10); c.stroke();
  pt.update();
}

// ---------------------------------------------------------------- logo (extruded rounded square with a play cut-out)
const sh = new THREE.Shape(); const L = 1.1, Rr = 0.32;
sh.moveTo(-L + Rr, -L); sh.lineTo(L - Rr, -L); sh.quadraticCurveTo(L, -L, L, -L + Rr); sh.lineTo(L, L - Rr);
sh.quadraticCurveTo(L, L, L - Rr, L); sh.lineTo(-L + Rr, L); sh.quadraticCurveTo(-L, L, -L, L - Rr); sh.lineTo(-L, -L + Rr);
sh.quadraticCurveTo(-L, -L, -L + Rr, -L);
const hole = new THREE.Path(); hole.moveTo(-0.32, -0.5); hole.lineTo(0.55, 0); hole.lineTo(-0.32, 0.5); hole.lineTo(-0.32, -0.5); sh.holes.push(hole);
const logo = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 0.42, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.07, bevelSegments: 5, curveSegments: 18 }),
  new THREE.MeshPhongMaterial({ color: '#c6f032', specular: '#666666', shininess: 70 }));
logo.geometry.center(); scene.add(logo);
const halo = new THREE.Mesh(new THREE.PlaneGeometry(7, 7), new THREE.MeshBasicMaterial({ map: glowT.tex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0.4 }));
scene.add(halo);
const key = new THREE.DirectionalLight('#ffffff', 1.6); key.position.set(3, 4, 6); scene.add(key); scene.add(new THREE.AmbientLight('#ffffff', 0.35));
const rim = new THREE.PointLight('#8f7bff', 40, 30); rim.position.set(-4, 2, -3); scene.add(rim);

// ---------------------------------------------------------------- dust + waveform ring
const DN = 2500, dpos = new Float32Array(DN * 3);
for (let i = 0; i < DN; i++) { dpos[i * 3] = (hash(i, 1) - 0.5) * 60; dpos[i * 3 + 1] = (hash(i, 2) - 0.5) * 60; dpos[i * 3 + 2] = 10 - hash(i, 3) * 90; }
const dgeo = new THREE.BufferGeometry(); dgeo.setAttribute('position', new THREE.BufferAttribute(dpos, 3));
const spr = canvasTex(64, 64); { const c = spr.ctx, g = c.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = g; c.fillRect(0, 0, 64, 64); spr.update(); }
const dust = new THREE.Points(dgeo, new THREE.PointsMaterial({ size: 0.09, map: spr.tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: '#b8c4ff' }));
scene.add(dust);
const WB = 120, bars = new THREE.InstancedMesh(new THREE.BoxGeometry(0.08, 1, 0.08), new THREE.MeshBasicMaterial({ color: '#D4FF3F', toneMapped: false }), WB);
scene.add(bars);
const kickEnv = t => { let e = 0; for (const k of T.KICKS) { if (k > t) break; e = Math.max(e, Math.exp(-(t - k) * 7)); } return e; };

// ---------------------------------------------------------------- per-frame
const tmp = new THREE.Object3D(), V = new THREE.Vector3();
function place(scr, pose, scale = 1) {
  scr.g.position.copy(pose.p);
  if (pose.look) scr.g.lookAt(pose.look); else scr.g.rotation.set(pose.rx || 0, pose.ry || 0, pose.rz || 0);
  scr.g.scale.setScalar((pose.s || 1) * scale);
}

window.renderFrame = t => {
  const P1 = T.DROP, P2 = 7.0, P3 = T.BREAK + 0.2, P4 = T.DROP2, P5 = T.LOGO - 0.35;
  for (const s of screens) s.mat.map = texAt(s.name, t, s.off);
  screens.forEach(s => (s.g.visible = true));
  tiles.forEach(tl => (tl.grp.visible = false)); prompt.visible = false; shock.visible = false; logo.visible = false; halo.visible = false; hero.visible = false; bars.visible = false;
  camera.up.set(0, 1, 0); camera.rotation.set(0, 0, 0);
  let flash = 0;

  if (t < P1) {                                                     // the wall
    const k = io(prog(t, 0, P1));
    const shake = 0.12 * Math.max(0, (t - (P1 - 0.45)) / 0.45) * noise(t * 40, 2);
    screens.forEach((s, i) => { const p = wallPose(i, t); p.p.x += shake * hash(i, 1); p.p.y += shake * hash(i, 2); place(s, p); });
    camera.position.set(0.6 * Math.sin(t * 0.7), 0.4, lerp(27, 15, k)); camera.lookAt(0, 0, 0); camera.rotation.z = lerp(0.06, 0, k);
  } else if (t < P2) {                                              // tunnel flight + hero screens
    const k = (t - P1) / (P2 - P1);
    screens.forEach((s, i) => place(s, tunnelPose(i, t)));
    camera.position.set(0, 0, lerp(8, -46, k)); camera.lookAt(0, 0, camera.position.z - 10); camera.rotation.z = t * 0.5;
    T.CATS.forEach((tc, ci) => {
      if (t >= tc - 0.12 && t < tc + T.HOLD[1] + 0.12) {
        hero.visible = true;
        hero.material.map = texAt(T.FEAT[ci], t, 0);
        const a = expo(prog(t, tc - 0.12, T.HOLD[0] + 0.12));
        const d = lerp(42, FILL_D, a);
        const wh = io(prog(t, tc + T.HOLD[1], 0.12));
        hero.position.set(-wh * 3.2 * (ci % 2 ? -1 : 1), 0, -d);
        hero.rotation.set(0, 0, -camera.rotation.z * (1 - a) + 0);
        hero.rotation.z = 0;
      }
    });
    // keep the hero screen square to the frame: counter-rotate the camera roll while it holds
    if (hero.visible) hero.rotation.z = 0;
    flash = Math.exp(-(t - P1) * 9) * 0.7;
  } else if (t < P3) {                                              // "No" tiles shatter
    screens.forEach((s, i) => { const p = wallPose(i, t); p.p.z -= 26; place(s, p, 1); });
    camera.position.set(0.3 * Math.sin(t), 0, 10); camera.lookAt(0, 0, 0);
    tiles.forEach((tl, k) => {
      tl.grp.visible = true;
      const kin = back(prog(t, P2 + 0.08 * k, 0.4), 1.5);
      tl.grp.position.set(0, tl.y, lerp(-6, 0, kin));
      tl.grp.rotation.set(0.12 * Math.sin(t * 1.3 + k), 0.18 * Math.sin(t * 0.9 + k), 0);
      tl.grp.scale.setScalar(Math.max(0.001, kin));
      const dt = t - tl.t;
      tl.shards.forEach(sd => {
        if (dt <= 0) { sd.m.position.copy(sd.home); sd.m.rotation.set(0, 0, 0); sd.m.material.opacity = 1; return; }
        sd.m.position.set(sd.home.x + sd.v.x * dt, sd.home.y + sd.v.y * dt - 4.5 * dt * dt, sd.home.z + sd.v.z * dt);
        sd.m.rotation.set(sd.rot.x * dt, sd.rot.y * dt, sd.rot.z * dt);
        sd.m.material.opacity = clamp(1 - dt / 1.1);
      });
      if (dt > 0 && dt < 0.12) flash = Math.max(flash, 0.25 * (1 - dt / 0.12));
    });
    flash = Math.max(flash, Math.exp(-(t - P2) * 12) * 0.5);
  } else if (t < P4) {                                              // glass prompt
    screens.forEach(s => (s.g.visible = false));
    prompt.visible = true; drawPrompt(t);
    const k = io(prog(t, P3, P4 - P3));
    prompt.rotation.set(0.1 * Math.sin(t * 0.8), lerp(-0.35, 0.12, k), 0);
    prompt.position.set(0, 0.6, 0);
    camera.position.set(lerp(2.0, 0, k), lerp(-1.0, 0.3, k), lerp(19, 15.5, k)); camera.lookAt(0, 0.5, 0);
    pglow.material.opacity = 0.35 + 0.65 * clamp((t - T.TYPE1) / 0.3);
  } else if (t < P5) {                                              // the build: screens burst out into a sphere
    prompt.visible = t < P4 + 0.25; if (prompt.visible) { drawPrompt(t); prompt.scale.setScalar(1 + (t - P4) * 6); }
    shock.visible = true; const sk = (t - P4); shock.scale.setScalar(0.5 + sk * 18); shock.material.opacity = clamp(1 - sk / 0.7);
    shock.position.set(0, 0.6, 0);
    const rotY = (t - P4) * 0.45;
    screens.forEach((s, i) => {
      const pose = spherePose(i), kk = expo(prog(t, P4 + 0.012 * i, 0.55));
      const p = pose.p.clone().multiplyScalar(kk).applyAxisAngle(new THREE.Vector3(0, 1, 0), rotY);
      const look = pose.look.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), rotY);
      const fl = (t >= T.FRAME_W && t < T.FRAME_W + 0.5) ? 1 + 0.25 * Math.exp(-(t - T.FRAME_W) * 6) * (hash(i, 5) > 0.5) : 1;
      place(s, { p, look, s: pose.s * Math.max(0.01, kk) * fl });
    });
    const k = io(prog(t, P4, P5 - P4));
    camera.position.set(lerp(0, 3, k), lerp(0.5, 2.5, k), lerp(9, 21, k)); camera.lookAt(0, 0, 0);
    if (t >= T.SOUND_W - 0.2) {
      bars.visible = true;
      const kb = out(prog(t, T.SOUND_W - 0.2, 0.4)), ke = kickEnv(t);
      for (let i = 0; i < WB; i++) {
        const a = i / WB * Math.PI * 2 + t * 0.2;
        const hgt = (0.2 + 2.6 * ke * (0.4 + 0.6 * Math.abs(noise(i * 0.35 + t * 3, 7)))) * kb;
        tmp.position.set(Math.cos(a) * 9.5, 0, Math.sin(a) * 9.5); tmp.scale.set(1, Math.max(0.01, hgt), 1); tmp.rotation.set(0, -a, 0);
        tmp.updateMatrix(); bars.setMatrixAt(i, tmp.matrix);
      }
      bars.instanceMatrix.needsUpdate = true;
    }
    flash = Math.exp(-(t - P4) * 7) * 0.9;
  } else {                                                          // logo + orbit ring of screens
    const k = expo(prog(t, P5, 0.6));
    const rotY = (t - P4) * 0.45;
    screens.forEach((s, i) => {
      const sp = spherePose(i), a = i / N * Math.PI * 2 + (t - P5) * 0.35;
      const ring = new THREE.Vector3(Math.cos(a) * 5.6, 1.05 - 1.5 * Math.sin(a) + 0.25 * Math.sin(a * 3 + t), Math.sin(a) * 5.6 - 1.5);
      const from = sp.p.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), rotY);
      const p = from.lerp(ring, k);
      place(s, { p, look: new THREE.Vector3(0, 1.0, -1).add(p.clone().sub(new THREE.Vector3(0, 1, -1)).multiplyScalar(2)), s: lerp(1.05, 0.42, k) });
    });
    logo.visible = true; halo.visible = true;
    halo.position.set(0, 1.05, -1.6); halo.scale.setScalar(Math.max(0.001, out(prog(t, T.LOGO, 0.8))) * 1.3 * (1 + 0.05 * Math.sin(t * 3)));
    const kl = back(prog(t, T.LOGO, 0.7), 1.4);
    logo.scale.setScalar(Math.max(0.001, kl) * 1.0);
    logo.position.set(0, 1.05 + 0.08 * Math.sin(t * 1.6), 0);
    logo.rotation.set(0.15 * Math.sin(t * 0.9), lerp(-Math.PI * 1.5, 0, expo(prog(t, T.LOGO, 1.1))) + 0.18 * Math.sin(t * 0.7), 0);
    camera.position.set(0.4 * Math.sin(t * 0.5), 1.2, lerp(16, 12.5, io(prog(t, P5, 2.5)))); camera.lookAt(0, 0.35, 0);
    flash = Math.exp(-Math.max(0, t - T.LOGO) * 9) * 0.35 * (t >= T.LOGO);
  }
  dust.position.z = (t * 3) % 30 - 15 + (t < P2 ? 0 : 0);
  S.film.uniforms.uFlash.value = flash;
  S.film.uniforms.uFade.value = clamp(1 - t / 0.25);
  S.render(t);
};
resolveReady();
