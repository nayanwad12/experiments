// B2-05 Ariane 5 Flight 501 documentary: pad -> liftoff -> inside the computer -> 64 into 16 -> overflow -> break-up.
import { stage, E, canvasTex, rr, THREE } from '/batch2/lib/stage.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.6, bloomThreshold: 1.0, bloomRadius: 0.55, bg: '#0b0f16', fov: 38, envIntensity: 0.6,
  timeline: '/batch2/05-faceless-ariane/work/timeline.json',
  fonts: [['IT8', 'InterTight-800.ttf'], ['JBM', 'JetBrainsMono-500.ttf'], ['ANT', 'Anton.ttf']] });
const { scene, camera } = S, T = S.TL;
const { clamp, prog, lerp, out, io, expo, back, hash, noise } = E;
S.film.uniforms.uGrain.value = 0.055; S.film.uniforms.uVig.value = 0.5;
S.film.uniforms.uLift.value.set(0.004, 0.012, 0.022); S.film.uniforms.uGain.value.set(1.04, 1.0, 0.94);

// ---------------------------------------------------------------- sprites
function puffTex(r, g, b) { const ct = canvasTex(128, 128), c = ct.ctx;
  for (let k = 0; k < 7; k++) { const x = 64 + 22 * (hash(k, 1) - 0.5), y = 64 + 22 * (hash(k, 2) - 0.5), rad = 30 + 20 * hash(k, 3);
    const gr = c.createRadialGradient(x, y, 0, x, y, rad); gr.addColorStop(0, `rgba(${r},${g},${b},0.35)`); gr.addColorStop(1, `rgba(${r},${g},${b},0)`);
    c.fillStyle = gr; c.fillRect(0, 0, 128, 128); } ct.update(); return ct.tex; }
const SMOKE = puffTex(235, 228, 218), FIRE = puffTex(255, 190, 90);
function particleSystem(n, tex, additive) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  g.setAttribute('aSize', new THREE.BufferAttribute(new Float32Array(n), 1));
  g.setAttribute('aAlpha', new THREE.BufferAttribute(new Float32Array(n), 1));
  g.setAttribute('aCol', new THREE.BufferAttribute(new Float32Array(n * 3).fill(1), 3));
  const m = new THREE.ShaderMaterial({ uniforms: { map: { value: tex }, uScale: { value: H_ / 2 } }, transparent: true, depthWrite: false,
    blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    vertexShader: `attribute float aSize; attribute float aAlpha; attribute vec3 aCol; uniform float uScale; varying float vA; varying vec3 vC;
      void main(){ vec4 mv = modelViewMatrix * vec4(position,1.); gl_Position = projectionMatrix * mv; gl_PointSize = min(900., aSize * uScale / -mv.z); vA = aAlpha; vC = aCol; }`,
    fragmentShader: `uniform sampler2D map; varying float vA; varying vec3 vC; void main(){ vec4 t = texture2D(map, gl_PointCoord); gl_FragColor = vec4(t.rgb * vC, t.a * vA); }` });
  const p = new THREE.Points(g, m); p.frustumCulled = false; scene.add(p); return p;
}
const H_ = 1920 * 0.9;

// ---------------------------------------------------------------- sky + ground
const skyT = canvasTex(16, 512); { const c = skyT.ctx, g = c.createLinearGradient(0, 0, 0, 512);
  g.addColorStop(0, '#24467a'); g.addColorStop(0.45, '#6f97c2'); g.addColorStop(0.62, '#f0c9a0'); g.addColorStop(1, '#f6dcbc'); c.fillStyle = g; c.fillRect(0, 0, 16, 512); skyT.update(); }
const sky = new THREE.Mesh(new THREE.SphereGeometry(300, 32, 16), new THREE.MeshBasicMaterial({ map: skyT.tex, side: THREE.BackSide, fog: false, toneMapped: false }));
scene.add(sky);
const groundT = canvasTex(512, 512); { const c = groundT.ctx; c.fillStyle = '#3f4a35'; c.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 3000; i++) { c.fillStyle = `rgba(${20 + 60 * hash(i, 1)},${40 + 60 * hash(i, 2)},${20 + 30 * hash(i, 3)},0.5)`; c.fillRect(512 * hash(i, 4), 512 * hash(i, 5), 6, 6); }
  groundT.tex.wrapS = groundT.tex.wrapT = THREE.RepeatWrapping; groundT.tex.repeat.set(30, 30); groundT.update(); }
const ground = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), new THREE.MeshStandardMaterial({ map: groundT.tex, roughness: 1 }));
ground.rotation.x = -Math.PI / 2; scene.add(ground);
scene.fog = new THREE.Fog('#d9c6ad', 40, 260);
const sunL = new THREE.DirectionalLight('#ffe2bd', 2.2); sunL.position.set(-30, 25, 20); scene.add(sunL);
scene.add(new THREE.HemisphereLight('#a9c4e8', '#3f4a35', 0.8));

// ---------------------------------------------------------------- pad + rocket
const pad = new THREE.Group(); scene.add(pad);
const concrete = new THREE.MeshStandardMaterial({ color: '#9a978f', roughness: 0.95 });
pad.add(Object.assign(new THREE.Mesh(new THREE.BoxGeometry(14, 0.6, 14), concrete), {}));
const towerMat = new THREE.MeshStandardMaterial({ color: '#c04a2a', roughness: 0.7, metalness: 0.3 });
for (const [x, z] of [[-4.2, -1], [-4.2, 1], [-6.2, -1], [-6.2, 1]]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.2, 22, 0.2), towerMat); p.position.set(x, 11, z); pad.add(p); }
for (let y = 1; y < 22; y += 1.6) for (const z of [-1, 1]) { const b = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.12, 0.12), towerMat); b.position.set(-5.2, y, z); pad.add(b); }
const rocket = new THREE.Group(); scene.add(rocket);
const white = new THREE.MeshStandardMaterial({ color: '#f1f0ec', roughness: 0.45, metalness: 0.1 });
const dark = new THREE.MeshStandardMaterial({ color: '#2b2b30', roughness: 0.6, metalness: 0.5 });
const core = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.1, 14, 40), white); core.position.y = 7.6; rocket.add(core);
const fair = new THREE.Mesh(new THREE.CylinderGeometry(1.15, 1.15, 5, 40), white); fair.position.y = 17.1; rocket.add(fair);
const nose = new THREE.Mesh(new THREE.SphereGeometry(1.15, 40, 20, 0, Math.PI * 2, 0, Math.PI / 2), white); nose.scale.y = 2.2; nose.position.y = 19.6; rocket.add(nose);
const band = new THREE.Mesh(new THREE.CylinderGeometry(1.12, 1.12, 0.3, 40), dark); band.position.y = 14.6; rocket.add(band);
const nozC = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.8, 1.2, 24, 1, true), dark); nozC.position.y = 0.2; rocket.add(nozC);
const boosters = [-1, 1].map(sx => { const g = new THREE.Group(); g.position.set(sx * 1.95, 0, 0); rocket.add(g);
  const b = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.75, 13, 32), white); b.position.y = 7.1; g.add(b);
  const n = new THREE.Mesh(new THREE.ConeGeometry(0.75, 2.2, 32), white); n.position.y = 14.7; g.add(n);
  for (const y of [2.5, 5.8, 9.1]) { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.77, 0.77, 0.18, 32), dark); r.position.y = y; g.add(r); }
  const nz = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.65, 1.0, 24, 1, true), dark); nz.position.y = 0.2; g.add(nz); return g; });
rocket.position.y = 0.3;
const flameMat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { uT: { value: 0 }, uK: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `uniform float uT, uK; varying vec2 vUv; void main(){ float y = 1. - vUv.y; float flick = 0.85 + 0.15 * sin(uT * 60. + vUv.x * 30.);
    vec3 c = mix(vec3(2.6, 2.3, 1.6), vec3(1.6, 0.55, 0.12), smoothstep(0., .7, y)); float a = (1. - y) * uK * flick * smoothstep(0.,.08,vUv.y);
    gl_FragColor = vec4(c * a, a); }` });
const flames = [[0, 0.8, 4.5], [-1.95, 0.6, 6.5], [1.95, 0.6, 6.5]].map(([x, r, h]) => { const f = new THREE.Mesh(new THREE.ConeGeometry(r, h, 24, 1, true), flameMat);
  f.rotation.x = Math.PI; f.position.set(x, -h / 2 - 0.2, 0); rocket.add(f); return f; });
const glowL = new THREE.PointLight('#ffb35a', 0, 60); glowL.position.set(0, -2, 0); rocket.add(glowL);
const smoke = particleSystem(700, SMOKE, false);
const fire = particleSystem(500, FIRE, true);
const blast = particleSystem(320, SMOKE, false);

// ---------------------------------------------------------------- computer world (PCB, bits, gauge, monitors)
const lab = new THREE.Group(); scene.add(lab); lab.position.set(0, 500, 0);
const pcbT = canvasTex(1024, 1024); { const c = pcbT.ctx; c.fillStyle = '#0b3d2a'; c.fillRect(0, 0, 1024, 1024);
  c.strokeStyle = '#1f7a52'; c.lineWidth = 6; for (let i = 0; i < 90; i++) { c.beginPath(); let x = 1024 * hash(i, 1), y = 1024 * hash(i, 2); c.moveTo(x, y);
    for (let k = 0; k < 4; k++) { if (k % 2) x += 300 * (hash(i, k, 3) - 0.5); else y += 300 * (hash(i, k, 4) - 0.5); c.lineTo(x, y); } c.stroke(); }
  c.fillStyle = '#c9a54a'; for (let i = 0; i < 200; i++) { c.beginPath(); c.arc(1024 * hash(i, 7), 1024 * hash(i, 8), 6, 0, 7); c.fill(); } pcbT.update(); }
const pcb = new THREE.Mesh(new THREE.BoxGeometry(14, 0.2, 14), new THREE.MeshStandardMaterial({ map: pcbT.tex, roughness: 0.6, metalness: 0.2 })); lab.add(pcb);
const chipT = canvasTex(512, 512); { const c = chipT.ctx; c.fillStyle = '#16161a'; c.fillRect(0, 0, 512, 512); c.fillStyle = '#d8d8d8';
  c.font = '700 70px JBM'; c.textAlign = 'center'; c.fillText('SRI', 256, 230); c.font = '500 34px JBM'; c.fillText('inertial reference', 256, 300); c.fillText('system', 256, 345); chipT.update(); }
const chip = new THREE.Mesh(new THREE.BoxGeometry(3, 0.4, 3), [dark, dark, new THREE.MeshStandardMaterial({ map: chipT.tex, roughness: 0.4 }), dark, dark, dark]);
chip.position.y = 0.3; lab.add(chip);
for (let i = 0; i < 12; i++) for (const s of [-1, 1]) { const pin = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.12, 0.5), new THREE.MeshStandardMaterial({ color: '#d7c27a', metalness: 1, roughness: 0.3 }));
  pin.position.set(-1.35 + i * 0.245, 0.15, s * 1.7); lab.add(pin); }
const labLight = new THREE.PointLight('#7dffb8', 30, 30); labLight.position.set(2, 6, 4); lab.add(labLight);

// bits: 64 cubes -> a 16-slot register
const bitsG = new THREE.Group(); scene.add(bitsG); bitsG.position.set(0, 1000, 0);
const bitMat = new THREE.MeshStandardMaterial({ color: '#e9eef7', roughness: 0.3, metalness: 0.2, emissive: '#6f8cff', emissiveIntensity: 0.25 });
const fitMat = new THREE.MeshStandardMaterial({ color: '#2bff88', roughness: 0.3, emissive: '#2bff88', emissiveIntensity: 0.6 });
const redMat = new THREE.MeshStandardMaterial({ color: '#ff3b3b', roughness: 0.3, emissive: '#ff3b3b', emissiveIntensity: 0.5 });
const bits = [...Array(64)].map((_, i) => { const m = new THREE.Mesh(new RoundedBoxGeometry(0.22, 0.22, 0.22, 2, 0.04), bitMat); bitsG.add(m); return m; });
const reg = new THREE.Mesh(new RoundedBoxGeometry(16 * 0.27 + 0.25, 0.5, 0.5, 2, 0.08), new THREE.MeshPhysicalMaterial({ color: '#9fb4d8', transparent: true, opacity: 0.25, roughness: 0.1 }));
bitsG.add(reg);
function label(txt, col, w = 6, h = 1) { const ct = canvasTex(1024, Math.round(1024 * h / w)), c = ct.ctx; c.fillStyle = col; c.font = `700 ${Math.round(ct.cv.height * 0.6)}px JBM`;
  c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(txt, 512, ct.cv.height / 2); ct.update();
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: ct.tex, transparent: true, toneMapped: false })); }
const l64 = label('64-BIT FLOAT', '#c9d6ff', 4.2, 0.5); bitsG.add(l64);
const l16 = label('16-BIT INTEGER', '#2bff88', 4.2, 0.5); bitsG.add(l16);

// gauge
const gauge = new THREE.Group(); scene.add(gauge); gauge.position.set(0, 1500, 0);
const tube = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, 9, 48, 1, true), new THREE.MeshPhysicalMaterial({ color: '#cfe0ff', transparent: true, opacity: 0.18, roughness: 0.05, side: THREE.DoubleSide }));
tube.position.y = 4.5; gauge.add(tube);
const liquid = new THREE.Mesh(new THREE.CylinderGeometry(0.82, 0.82, 1, 48), new THREE.MeshStandardMaterial({ color: '#4d8dff', emissive: '#2a5cff', emissiveIntensity: 0.6, roughness: 0.2 }));
gauge.add(liquid);
const maxRing = new THREE.Mesh(new THREE.TorusGeometry(1.05, 0.05, 12, 64), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ff3b3b').multiplyScalar(2.5), toneMapped: false }));
maxRing.rotation.x = Math.PI / 2; maxRing.position.y = 6.2; gauge.add(maxRing);
const maxLbl = label('MAX  32,767', '#ff6b6b', 4.2, 0.6); maxLbl.position.set(0, 6.75, 0.95); gauge.add(maxLbl);
const valT = canvasTex(1024, 256); const valM = new THREE.Mesh(new THREE.PlaneGeometry(5, 1.25), new THREE.MeshBasicMaterial({ map: valT.tex, transparent: true, toneMapped: false }));
valM.position.set(0, -1.1, 0.6); valM.visible = false; gauge.add(valM);   // the counter is drawn crisp in 2D (build.py)
const shards = [...Array(40)].map((_, i) => { const m = new THREE.Mesh(new THREE.TetrahedronGeometry(0.15 + 0.2 * hash(i, 1)), tube.material); gauge.add(m); return m; });
const drops = [...Array(120)].map(() => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 6), liquid.material); gauge.add(m); return m; });

// monitors (SRI 1 / SRI 2)
const mons = new THREE.Group(); scene.add(mons); mons.position.set(0, 2000, 0);
const monScreens = [0, 1].map(i => { const g = new THREE.Group(); g.position.set(0, i ? -2.3 : 2.3, 0); mons.add(g);
  g.add(new THREE.Mesh(new RoundedBoxGeometry(5.2, 3.6, 0.3, 3, 0.12), dark));
  const ct = canvasTex(1040, 700); const face = new THREE.Mesh(new THREE.PlaneGeometry(4.9, 3.3), new THREE.MeshBasicMaterial({ map: ct.tex, toneMapped: false }));
  face.position.z = 0.16; g.add(face); return { g, ct }; });
function drawMon(m, name, failed, t) { const c = m.ct.ctx; c.fillStyle = failed ? '#2a0606' : '#03110a'; c.fillRect(0, 0, 1040, 700);
  c.fillStyle = failed ? '#ff4a4a' : '#2bff88'; c.font = '700 64px JBM'; c.textAlign = 'left'; c.fillText(name, 60, 110);
  c.font = '500 44px JBM';
  const lines = failed ? ['OPERAND ERROR', 'E_BH overflow', 'shutting down…'] : ['ALIGNMENT  OK', 'H_BIAS  nominal', 'attitude  OK'];
  lines.forEach((l, i) => { if (!failed || Math.floor(t * 4) % 2 === 0 || i < 2) c.fillText(l, 60, 250 + i * 90); });
  if (failed) { c.strokeStyle = '#ff4a4a'; c.lineWidth = 10; c.strokeRect(20, 20, 1000, 660); }
  m.ct.update(); }

// ---------------------------------------------------------------- explosion debris
const debris = [...Array(36)].map((_, i) => { const m = new THREE.Mesh(new THREE.BoxGeometry(0.3 + hash(i, 1), 0.2 + hash(i, 2) * 0.6, 0.3 + hash(i, 3) * 0.8), i % 3 ? white : dark); scene.add(m); return m; });

// ---------------------------------------------------------------- wireframe (tail)
const wireMat = new THREE.MeshBasicMaterial({ color: '#2bff88', wireframe: true, transparent: true, opacity: 0.7 });
const wireRocket = rocket.clone(true); wireRocket.traverse(o => { if (o.isMesh) o.material = o.material === flameMat ? flameMat : wireMat; }); scene.add(wireRocket);

// ---------------------------------------------------------------- per frame
function setSmoke(t, liftT, h) {
  const P = smoke.geometry.attributes, F = fire.geometry.attributes, n = 700, nf = 500;
  for (let i = 0; i < n; i++) {
    const born = liftT - 0.6 + i * 0.02, age = t - born; let a = 0;
    if (age > 0 && age < 9) {
      const hb = h(born); const spread = 1 + age * 1.6;
      const ground = hb < 3;
      const dir = ground ? [Math.cos(i * 2.4), 0, Math.sin(i * 2.4)] : [hash(i, 1) - 0.5, -0.4, hash(i, 2) - 0.5];
      P.position.setXYZ(i, dir[0] * spread * (ground ? 3.2 : 1.2) + noise(age, i) * 0.6, Math.max(0.5, hb - 1 + dir[1] * age * 2 + age * 0.5), dir[2] * spread * (ground ? 3 : 1.2));
      P.aSize.setX(i, 2.5 + age * 2.2); a = clamp(age / 0.2) * clamp(1 - age / 9) * 0.55;
    } else P.position.setXYZ(i, 0, -999, 0);
    P.aAlpha.setX(i, a);
  }
  for (let i = 0; i < nf; i++) {
    const born = t - (i / nf) * 0.5, age = t - born; const hb = h(born);
    if (born < liftT - 0.3) { F.aAlpha.setX(i, 0); continue; }
    F.position.setXYZ(i, (hash(i, 1) - 0.5) * 1.2, hb - 1 - age * 14, (hash(i, 2) - 0.5) * 1.2);
    F.aSize.setX(i, 1.2 + age * 3); F.aAlpha.setX(i, 0.8 * (1 - age / 0.5));
  }
  P.position.needsUpdate = P.aSize.needsUpdate = P.aAlpha.needsUpdate = true;
  F.position.needsUpdate = F.aSize.needsUpdate = F.aAlpha.needsUpdate = true;
}
const height = t => t < T.LIFTOFF ? 0 : 0.9 * Math.pow(t - T.LIFTOFF, 2.1) * 1.6;

window.renderFrame = t => {
  flameMat.uniforms.uT.value = t;
  [pad, rocket, lab, bitsG, gauge, mons, wireRocket].forEach(o => (o.visible = false));
  smoke.visible = fire.visible = blast.visible = false; debris.forEach(d => (d.visible = false));
  sky.visible = ground.visible = true; scene.fog.near = 40; scene.fog.far = 260;
  rocket.rotation.set(0, 0, 0); rocket.position.set(0, 0.3, 0); boosters.forEach((b, i) => { b.position.set(i ? 1.95 : -1.95, 0, 0); b.rotation.set(0, 0, 0); });
  let flash = 0;

  if (t < T.INSIDE) {                                                    // pad + liftoff
    pad.visible = rocket.visible = true; smoke.visible = fire.visible = true;
    const ign = clamp((t - (T.LIFTOFF - 0.5)) / 0.5);
    flameMat.uniforms.uK.value = ign; glowL.intensity = 400 * ign;
    const h = height(t); rocket.position.y = 0.3 + h;
    setSmoke(t, T.LIFTOFF, height);
    if (t < T.LIFT_LINE) {
      const k = io(prog(t, 0, T.LIFT_LINE));
      camera.position.set(lerp(30, 22, k), lerp(4, 6, k), lerp(34, 26, k)); camera.lookAt(0, 10, 0);
    } else {
      const k = io(prog(t, T.LIFT_LINE, T.INSIDE - T.LIFT_LINE));
      camera.position.set(26, 3, 44); camera.lookAt(0, 9 + h * 0.75, 0);
      flash = 0.25 * Math.exp(-Math.max(0, t - T.LIFTOFF) * 6) * (t >= T.LIFTOFF);
    }
    if (t > T.INSIDE - 0.6) {                                            // dive into the rocket
      const kd = expo(prog(t, T.INSIDE - 0.6, 0.6));
      const target = new THREE.Vector3(0, rocket.position.y + 15, 0);
      camera.position.lerp(target.clone().add(new THREE.Vector3(0, 0, 1.4)), kd); camera.lookAt(target);
      flash = Math.max(flash, kd * 0.9);
    }
  } else if (t < T.SQUEEZE) {                                            // inside: the SRI chip
    lab.visible = true; sky.visible = ground.visible = false; scene.fog.near = 500; scene.fog.far = 900;
    const k = io(prog(t, T.INSIDE, T.SQUEEZE - T.INSIDE));
    camera.position.set(lerp(6, 2.5, k), 500 + lerp(9, 5.5, k), lerp(9, 5.5, k)); camera.lookAt(0, 500.2, 0.5);
    flash = 0.8 * Math.exp(-(t - T.INSIDE) * 8);
  } else if (t < T.MAX) {                                                // 64 bits -> 16 slots
    bitsG.visible = true; sky.visible = ground.visible = false;
    l64.position.set(0, 1001.7 - 1000, 0); l16.position.set(0, -1.3, 0.4);
    reg.position.set(0, -0.6, 0);
    bits.forEach((b, i) => {
      const k = expo(prog(t, T.BITS16 + 0.03 * i, 0.5));
      const row = new THREE.Vector3(-2.025 + (i % 16) * 0.27, 1.0 + (1.5 - Math.floor(i / 16)) * 0.3, 0);
      let target;
      if (i < 16) target = new THREE.Vector3(-2.025 + i * 0.27, -0.6, 0);
      else { const j = i - 16; target = new THREE.Vector3(-2.2 + (j % 12) * 0.4 + 0.15 * hash(j, 1), -0.2 + Math.floor(j / 12) * 0.3 + 0.15 * hash(j, 2), 0.7 + 0.5 * hash(j, 3)); }
      b.position.lerpVectors(row, target, k);
      b.rotation.set(i >= 16 ? k * hash(i, 4) * 2 : 0, i >= 16 ? k * hash(i, 5) * 2 : 0, 0);
      b.material = i < 16 ? (k > 0.95 ? fitMat : bitMat) : (k > 0.95 ? redMat : bitMat);
    });
    l64.position.set(0, 1.95, 0);
    const k = io(prog(t, T.SQUEEZE, T.MAX - T.SQUEEZE));
    camera.position.set(lerp(-0.8, 0.8, k), 999.9 + lerp(0.3, 0.0, k), lerp(12.8, 11.8, k)); camera.lookAt(0, 999.6, 0);
    flash = 0.6 * Math.exp(-(t - T.SQUEEZE) * 9);
  } else if (t < T.CRASH) {                                              // gauge: value climbs past 32,767, then bursts
    gauge.visible = true; sky.visible = ground.visible = false;
    const vk = t < T.OVER ? 0.85 * out(prog(t, T.MAXNUM - 0.8, 1.4)) : lerp(0.85, 1.25, io(prog(t, T.OVER, T.OVERFLOW - T.OVER)));
    const level = 9 * clamp(vk * 6.2 / 9 / 0.85 * 0.85 / 0.85 * 0.85);
    const lv = Math.min(9, vk * 7.3);
    const burst = t >= T.OVERFLOW;
    liquid.visible = !burst; tube.visible = !burst;
    liquid.scale.y = Math.max(0.01, lv); liquid.position.y = lv / 2;
    liquid.material.color.set(vk > 0.85 ? '#ff4a4a' : '#4d8dff'); liquid.material.emissive.set(vk > 0.85 ? '#ff2020' : '#2a5cff');
    const val = Math.round(vk / 0.85 * 32767 * (vk > 0.85 ? 1.0 + (vk - 0.85) * 3.2 : 1));
    const c = valT.ctx; c.clearRect(0, 0, 1024, 256); c.font = '400 190px ANT'; c.textAlign = 'center'; c.fillStyle = val > 32767 ? '#ff4a4a' : '#ffffff';
    c.fillText(val.toLocaleString('en-US'), 512, 200); valT.update();
    const shake = t > T.OVER ? 0.08 * io(prog(t, T.OVER, T.OVERFLOW - T.OVER)) : 0;
    gauge.position.set(shake * noise(t * 40, 1), 1500 + shake * noise(t * 40, 2), 0);
    shards.forEach((s, i) => { s.visible = burst; if (!burst) return; const dt = t - T.OVERFLOW; const a = hash(i, 1) * 6.28;
      s.position.set(Math.cos(a) * (0.9 + 7 * dt), 2 + 7 * hash(i, 2) + 4 * dt - 6 * dt * dt, Math.sin(a) * (0.9 + 7 * dt)); s.rotation.set(dt * 9, dt * 7, 0); });
    drops.forEach((d, i) => { d.visible = burst; if (!burst) return; const dt = t - T.OVERFLOW; const a = hash(i, 3) * 6.28, v = 3 + 6 * hash(i, 4);
      d.position.set(Math.cos(a) * v * dt, 4 + 8 * hash(i, 5) + 7 * dt - 9 * dt * dt, Math.sin(a) * v * dt); });
    const k = io(prog(t, T.MAX, T.CRASH - T.MAX));
    camera.position.set(lerp(-2, 2, k), 1500 + 4.0, lerp(17, 15.5, k)); camera.lookAt(0, 1500 + 3.8, 0);
    flash = burst ? 0.9 * Math.exp(-(t - T.OVERFLOW) * 7) : 0.5 * Math.exp(-(t - T.MAX) * 9);
  } else if (t < T.VEER) {                                               // both computers fail
    mons.visible = true; sky.visible = ground.visible = false;
    drawMon(monScreens[0], 'SRI 1  (active)', t >= T.CRASH + 0.25, t);
    drawMon(monScreens[1], 'SRI 2  (backup)', t >= T.BACKUP + 0.15, t);
    const k = io(prog(t, T.CRASH, T.VEER - T.CRASH));
    camera.position.set(lerp(1.0, -0.6, k), 2000, lerp(15.5, 14.0, k)); camera.lookAt(0, 2000, 0);
    flash = 0.4 * Math.exp(-(t - T.CRASH) * 9) + (t >= T.BACKUP + 0.15 && t < T.BACKUP + 0.25 ? 0.3 : 0);
  } else if (t < T.LOST) {                                               // veer + break-up
    const boom = t >= T.EXPLODE;
    rocket.visible = !boom; smoke.visible = fire.visible = true;
    const tv = t - T.VEER, alt = 900 + tv * 60;
    rocket.position.set(tv * 6, alt, 0); rocket.rotation.z = -lerp(0.05, 1.25, io(prog(t, T.VEER + 0.3, T.EXPLODE - T.VEER - 0.3)));
    flameMat.uniforms.uK.value = 1; glowL.intensity = 300;
    // trail smoke from the rocket's path
    const P = smoke.geometry.attributes;
    for (let i = 0; i < 700; i++) { const born = T.VEER - 1.5 + i * 0.008, age = t - born; let a = 0;
      if (age > 0 && born < Math.min(t, T.EXPLODE)) { const tb = born - T.VEER; P.position.setXYZ(i, tb * 6 + (hash(i, 1) - 0.5) * age * 2, 900 + tb * 60 - 8 + (hash(i, 2) - 0.5) * age * 2, (hash(i, 3) - 0.5) * age * 2);
        P.aSize.setX(i, 2 + age * 1.5); a = 0.45 * clamp(1 - age / 6); } else P.position.setXYZ(i, 0, -999, 0);
      P.aAlpha.setX(i, a); }
    P.position.needsUpdate = P.aSize.needsUpdate = P.aAlpha.needsUpdate = true;
    const F = fire.geometry.attributes;
    for (let i = 0; i < 500; i++) {
      if (!boom) { F.aAlpha.setX(i, 0); continue; }
      const dt = t - T.EXPLODE, a = hash(i, 1) * 6.28, b = (hash(i, 2) - 0.5) * 3.1, v = 6 + 18 * hash(i, 3);
      const ex = (T.EXPLODE - T.VEER) * 6, ey = 900 + (T.EXPLODE - T.VEER) * 60 + 10;
      F.position.setXYZ(i, ex + Math.cos(a) * Math.cos(b) * v * Math.sqrt(dt), ey + Math.sin(b) * v * Math.sqrt(dt) - dt * 2, Math.sin(a) * Math.cos(b) * v * Math.sqrt(dt));
      const core = i < 60;
      F.aSize.setX(i, (core ? 5 : 6) + dt * (core ? 8 : 12)); F.aAlpha.setX(i, (core ? 0.5 : 0.22) * clamp(1 - dt / (core ? 0.8 : 1.6)));
      F.aCol.setXYZ(i, 1, core ? 0.85 : lerp(0.62, 0.3, clamp(dt / 1.2)), core ? 0.6 : lerp(0.28, 0.1, clamp(dt / 0.8)));
    }
    F.position.needsUpdate = F.aSize.needsUpdate = F.aAlpha.needsUpdate = F.aCol.needsUpdate = true;
    blast.visible = boom;
    if (boom) { const B = blast.geometry.attributes, dt = t - T.EXPLODE, ex0 = (T.EXPLODE - T.VEER) * 6, ey0 = 900 + (T.EXPLODE - T.VEER) * 60 + 10;
      for (let i = 0; i < 320; i++) { const a = hash(i, 11) * 6.28, b = (hash(i, 12) - 0.5) * 3.1, v = 5 + 13 * hash(i, 13), r = v * Math.pow(dt, 0.45);
        B.position.setXYZ(i, ex0 + Math.cos(a) * Math.cos(b) * r, ey0 + Math.sin(b) * r + dt * 1.5, Math.sin(a) * Math.cos(b) * r);
        B.aSize.setX(i, 6 + dt * 9); B.aAlpha.setX(i, clamp(dt / 0.25) * 0.85 * clamp(1 - dt / 9));
        const heat = clamp(1 - dt / 0.9) * (hash(i, 14) > 0.5 ? 1 : 0.6);
        B.aCol.setXYZ(i, lerp(0.22, 1.0, heat), lerp(0.2, 0.42, heat), lerp(0.19, 0.12, heat)); }
      B.position.needsUpdate = B.aSize.needsUpdate = B.aAlpha.needsUpdate = B.aCol.needsUpdate = true; }
    debris.forEach((d, i) => { d.visible = boom; if (!boom) return; const dt = t - T.EXPLODE, a = hash(i, 5) * 6.28, v = 8 + 16 * hash(i, 6);
      const ex = (T.EXPLODE - T.VEER) * 6, ey = 900 + (T.EXPLODE - T.VEER) * 60 + 10;
      d.position.set(ex + Math.cos(a) * v * dt, ey + (hash(i, 7) - 0.3) * v * dt - 9.8 * dt * dt, Math.sin(a) * v * dt); d.rotation.set(dt * 5 * hash(i, 8), dt * 4, dt * 3); });
    const ex = (T.EXPLODE - T.VEER) * 6, ey = 900 + (T.EXPLODE - T.VEER) * 60;
    camera.position.set(-26 + tv * 4, 885 + tv * 55, 48); camera.lookAt(boom ? ex : rocket.position.x, boom ? ey + 10 : alt + 8, 0);
    flash = boom ? 0.55 * Math.exp(-(t - T.EXPLODE) * 9) : 0;
    scene.fog.near = 400; scene.fog.far = 1200;
  } else if (t < T.TAIL) {                                               // aftermath: smoke cloud drifting
    smoke.visible = fire.visible = true; debris.forEach(d => (d.visible = true)); scene.fog.near = 400; scene.fog.far = 1200;
    const dt = t - T.EXPLODE, ex = (T.EXPLODE - T.VEER) * 6, ey = 900 + (T.EXPLODE - T.VEER) * 60 + 10;
    const P = smoke.geometry.attributes;
    for (let i = 0; i < 700; i++) { const a = hash(i, 1) * 6.28, b = (hash(i, 2) - 0.5) * 3, v = 4 + 10 * hash(i, 3);
      P.position.setXYZ(i, ex + Math.cos(a) * Math.cos(b) * v * Math.sqrt(dt) + dt * 2, ey + Math.sin(b) * v * Math.sqrt(dt) - dt * 1.5, Math.sin(a) * Math.cos(b) * v * Math.sqrt(dt));
      P.aSize.setX(i, 8 + dt * 5); P.aAlpha.setX(i, 0.7 * clamp(1 - dt / 14)); P.aCol.setXYZ(i, 0.32, 0.3, 0.29); }
    P.position.needsUpdate = P.aSize.needsUpdate = P.aAlpha.needsUpdate = P.aCol.needsUpdate = true;
    const F = fire.geometry.attributes; for (let i = 0; i < 500; i++) F.aAlpha.setX(i, 0); F.aAlpha.needsUpdate = true;
    debris.forEach((d, i) => { const a = hash(i, 5) * 6.28, v = 8 + 16 * hash(i, 6);
      d.position.set(ex + Math.cos(a) * v * dt, ey + (hash(i, 7) - 0.3) * v * dt - 9.8 * dt * dt * 0.35, Math.sin(a) * v * dt); });
    const k = io(prog(t, T.LOST, T.TAIL - T.LOST));
    camera.position.set(ex - 38 + 8 * k, ey - 18, 60); camera.lookAt(ex, ey - 4 - 8 * k, 0);
  } else {                                                               // tail: it's all code (wireframe)
    sky.visible = ground.visible = false; wireRocket.visible = true;
    wireRocket.position.set(0, 0, 0); wireRocket.rotation.y = (t - T.TAIL) * 0.6;
    camera.position.set(0, 10, 34); camera.lookAt(0, 9, 0);
    flash = 0.5 * Math.exp(-(t - T.TAIL) * 8);
  }
  sky.position.copy(camera.position);
  scene.background = new THREE.Color(sky.visible ? '#cdb89a' : '#05080c');
  S.film.uniforms.uFlash.value = flash;
  S.film.uniforms.uFade.value = clamp(1 - t / 0.4);
  S.render(t);
};
resolveReady();
