// B2-06 Audio build: every musical layer drives its own visual layer. Features come from the real stems (timeline.json).
import { stage, E, canvasTex, THREE } from '/batch2/lib/stage.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.5, bloomThreshold: 1.05, bloomRadius: 0.45, bg: '#030308', fov: 40, env: false,
  timeline: '/batch2/06-audio-build/work/timeline.json' });
const { scene, camera } = S, T = S.TL;
const { clamp, prog, lerp, out, io, expo, back, hash, noise } = E;
const L = T.L;
S.film.uniforms.uGrain.value = 0.035; S.film.uniforms.uChroma.value = 0.0012;
const F = t => Math.min(T.ENV.kick.length - 1, Math.max(0, Math.round(t * T.FPS)));
const env = (k, t) => (t >= L[k] ? T.ENV[k][F(t)] : 0);
const kickEnv = t => { let e = 0; for (const k of T.KICKS) { if (k > t) break; e = Math.exp(-(t - k) * 9); } return e; };
const PAL = { kick: new THREE.Color('#D4FF3F'), hats: new THREE.Color('#4FE3FF'), bass: new THREE.Color('#FF4FD8'),
  chords: new THREE.Color('#FFB547'), lead: new THREE.Color('#9D7BFF') };

const NOISE = `vec3 m3(vec3 x){return x-floor(x*(1./289.))*289.;}vec4 m4(vec4 x){return x-floor(x*(1./289.))*289.;}vec4 pm(vec4 x){return m4(((x*34.)+1.)*x);}
float sn(vec3 v){const vec2 C=vec2(1./6.,1./3.);const vec4 D=vec4(0.,.5,1.,2.);vec3 i=floor(v+dot(v,C.yyy));vec3 x0=v-i+dot(i,C.xxx);vec3 g=step(x0.yzx,x0.xyz);vec3 l=1.-g;
vec3 i1=min(g.xyz,l.zxy);vec3 i2=max(g.xyz,l.zxy);vec3 x1=x0-i1+C.xxx;vec3 x2=x0-i2+C.yyy;vec3 x3=x0-D.yyy;i=m3(i);vec4 p=pm(pm(pm(i.z+vec4(0.,i1.z,i2.z,1.))+i.y+vec4(0.,i1.y,i2.y,1.))+i.x+vec4(0.,i1.x,i2.x,1.));
float n_=.142857142857;vec3 ns=n_*D.wyz-D.xzx;vec4 j=p-49.*floor(p*ns.z*ns.z);vec4 x_=floor(j*ns.z);vec4 y_=floor(j-7.*x_);vec4 x=x_*ns.x+ns.yyyy;vec4 y=y_*ns.x+ns.yyyy;vec4 h=1.-abs(x)-abs(y);
vec4 b0=vec4(x.xy,y.xy);vec4 b1=vec4(x.zw,y.zw);vec4 s0=floor(b0)*2.+1.;vec4 s1=floor(b1)*2.+1.;vec4 sh=-step(h,vec4(0.));vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
vec3 p0=vec3(a0.xy,h.x);vec3 p1=vec3(a0.zw,h.y);vec3 p2=vec3(a1.xy,h.z);vec3 p3=vec3(a1.zw,h.w);vec4 nm=1.79284291400159-0.85373472095314*vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3));
p0*=nm.x;p1*=nm.y;p2*=nm.z;p3*=nm.w;vec4 m=max(.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.);m=m*m;return 42.*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));}`;

// ---------------------------------------------------------------- core (kick + bass)
const coreU = { uT: { value: 0 }, uKick: { value: 0 }, uBass: { value: 0 }, uCol: { value: new THREE.Color('#D4FF3F') }, uDrop: { value: 0 } };
const core = new THREE.Mesh(new THREE.IcosahedronGeometry(1.3, 64), new THREE.ShaderMaterial({ uniforms: coreU,
  vertexShader: NOISE + `uniform float uT, uKick, uBass, uDrop; varying float vN; varying vec3 vNor;
    void main(){ float n = sn(normal * (1.6 + uDrop) + vec3(uT * .6)); vN = n;
      vec3 p = position * (1. + 0.22 * uKick + 0.25 * uDrop) + normal * n * (0.12 + 0.55 * uBass);
      vNor = normalMatrix * normal; gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.); }`,
  fragmentShader: `uniform vec3 uCol; uniform float uKick, uDrop; varying float vN; varying vec3 vNor;
    void main(){ float fr = pow(1. - abs(normalize(vNor).z), 2.); vec3 c = uCol * (0.25 + 0.9 * fr + 0.6 * uKick) + vec3(1.) * fr * 0.5 * uKick;
      c += mix(vec3(0.), vec3(1.0, 0.3, 0.85), smoothstep(0.2, 0.9, vN)) * uDrop * 0.8; gl_FragColor = vec4(c * 0.95, 1.); }` }));
scene.add(core);
const coreWire = new THREE.Mesh(new THREE.IcosahedronGeometry(1.75, 3), new THREE.MeshBasicMaterial({ color: '#D4FF3F', wireframe: true, transparent: true, opacity: 0.18 }));
scene.add(coreWire);

// ---------------------------------------------------------------- kick shockwave rings on the floor
const rings = [...Array(10)].map(() => { const m = new THREE.Mesh(new THREE.RingGeometry(0.97, 1.0, 128), new THREE.MeshBasicMaterial({ color: '#D4FF3F', transparent: true, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }));
  m.rotation.x = -Math.PI / 2; m.position.y = -2.6; scene.add(m); return m; });

// ---------------------------------------------------------------- bass terrain grid
const gridU = { uT: { value: 0 }, uBass: { value: 0 }, uK: { value: 0 }, uCol: { value: new THREE.Color('#FF4FD8') } };
const grid = new THREE.Mesh(new THREE.PlaneGeometry(60, 60, 140, 140), new THREE.ShaderMaterial({ uniforms: gridU, wireframe: true, transparent: true,
  vertexShader: NOISE + `uniform float uT, uBass, uK; varying float vH; varying float vD;
    void main(){ vec3 p = position; float d = length(p.xy); float w = sin(d * 0.9 - uT * 6.) * exp(-d * 0.06) * uBass * 1.2 + sn(vec3(p.xy * 0.15, uT * 0.4)) * uBass * 0.9;
      p.z = w * uK; vH = w; vD = d; gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.); }`,
  fragmentShader: `uniform vec3 uCol; uniform float uK; varying float vH; varying float vD;
    void main(){ float a = uK * (0.25 + 0.6 * clamp(vH, 0., 1.)) * smoothstep(30., 6., vD); gl_FragColor = vec4(uCol * (1. + vH), a); }` }));
grid.rotation.x = -Math.PI / 2; grid.position.y = -2.6; scene.add(grid);

// ---------------------------------------------------------------- hats: sparkle field
const SN = 1600, spos = new Float32Array(SN * 3), sseed = new Float32Array(SN);
for (let i = 0; i < SN; i++) { const r = 4 + 18 * hash(i, 1), a = hash(i, 2) * 6.283, b = (hash(i, 3) - 0.5) * 2.4;
  spos[i * 3] = Math.cos(a) * Math.cos(b) * r; spos[i * 3 + 1] = Math.sin(b) * r * 0.6 + 1; spos[i * 3 + 2] = Math.sin(a) * Math.cos(b) * r; sseed[i] = hash(i, 4); }
const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(spos, 3)); sg.setAttribute('aS', new THREE.BufferAttribute(sseed, 1));
const sparkU = { uT: { value: 0 }, uHat: { value: 0 }, uK: { value: 0 } };
const sparks = new THREE.Points(sg, new THREE.ShaderMaterial({ uniforms: sparkU, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  vertexShader: `attribute float aS; uniform float uT, uHat, uK; varying float vA;
    void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.); gl_Position = projectionMatrix * mv;
      float tw = step(0.55, fract(aS * 13.7 + floor(uT * 8.) * 0.37)); vA = uK * (0.12 + tw * uHat * 0.9);
      gl_PointSize = (2. + 7. * tw * uHat) * (14. / -mv.z); }`,
  fragmentShader: `varying float vA; void main(){ float d = length(gl_PointCoord - .5); if (d > .5) discard; gl_FragColor = vec4(vec3(0.6, 0.95, 1.2), vA * (1. - d * 2.)); }` }));
scene.add(sparks);

// ---------------------------------------------------------------- chords: spectrum ring
const NB = 64, bars = new THREE.InstancedMesh(new THREE.BoxGeometry(0.09, 1, 0.09), new THREE.MeshBasicMaterial({ toneMapped: false }), NB);
bars.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(NB * 3), 3); scene.add(bars);

// ---------------------------------------------------------------- lead: helix of light
const HN = 900, hpos = new Float32Array(HN * 3), hgeo = new THREE.BufferGeometry(); hgeo.setAttribute('position', new THREE.BufferAttribute(hpos, 3));
const helix = new THREE.Points(hgeo, new THREE.PointsMaterial({ color: new THREE.Color('#9D7BFF').multiplyScalar(1.3), size: 0.07, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
scene.add(helix);

// ---------------------------------------------------------------- drop burst
const BN = 2500, bpos = new Float32Array(BN * 3), bcol = new Float32Array(BN * 3), bgeo = new THREE.BufferGeometry();
bgeo.setAttribute('position', new THREE.BufferAttribute(bpos, 3)); bgeo.setAttribute('color', new THREE.BufferAttribute(bcol, 3));
const cols = [PAL.kick, PAL.hats, PAL.bass, PAL.chords, PAL.lead];
for (let i = 0; i < BN; i++) { const c = cols[i % 5]; bcol[i * 3] = c.r * 1.2; bcol[i * 3 + 1] = c.g * 1.2; bcol[i * 3 + 2] = c.b * 1.2; }
const burst = new THREE.Points(bgeo, new THREE.PointsMaterial({ size: 0.08, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
scene.add(burst);

// ---------------------------------------------------------------- per frame
window.renderFrame = t => {
  const f = F(t), drop = t >= L.drop, inBuild = t >= L.build && t < L.drop;
  const kd = drop ? clamp((t - L.drop) / 0.4) : 0;
  const ke = t >= L.kick && !inBuild ? kickEnv(t) : 0;
  const bass = env('bass', t), hats = env('hats', t), lead = env('lead', t);
  const buildK = inBuild ? (t - L.build) / (L.drop - L.build) : 0;
  // core
  coreU.uT.value = t; coreU.uKick.value = ke; coreU.uBass.value = bass * (t >= L.bass ? 1 : 0) + buildK * 0.6;
  coreU.uDrop.value = drop ? 0.6 + 0.4 * ke : buildK * 0.4;
  const hue = drop ? (t * 0.25) % 1 : 0.2;
  coreU.uCol.value.setHSL(drop ? hue : 0.21, drop ? 0.95 : lerp(0.95, 0.0, buildK), drop ? 0.55 : lerp(0.55, 0.85, buildK));
  core.scale.setScalar(t < L.kick ? 0.4 + 0.3 * clamp(t / L.kick) : 1);
  core.rotation.set(t * 0.3, t * 0.45, 0);
  coreWire.rotation.set(-t * 0.2, t * 0.3, 0); coreWire.scale.setScalar(1 + 0.15 * ke + kd * 0.6); coreWire.material.opacity = t >= L.kick ? 0.18 + 0.3 * ke : 0.05;
  // rings: one per recent kick
  const recent = T.KICKS.filter(k => k <= t && t - k < 1.6 && t >= L.kick && !(k >= L.build && k < L.drop)).slice(-10);
  rings.forEach((r, i) => { const k = recent[i]; r.visible = k !== undefined; if (!r.visible) return; const dt = t - k;
    r.scale.setScalar(1.5 + dt * 14); r.material.opacity = 0.9 * (1 - dt / 1.6); r.material.color.copy(drop ? cols[Math.floor(k * 2) % 5] : PAL.kick); });
  // grid
  gridU.uT.value = t; gridU.uBass.value = bass * 1.3 + (drop ? 0.4 * ke : 0); gridU.uK.value = t >= L.bass ? out(prog(t, L.bass, 0.6)) : 0;
  gridU.uCol.value.copy(drop ? cols[Math.floor(t * 2) % 5] : PAL.bass);
  // sparks
  sparkU.uT.value = t; sparkU.uHat.value = hats + (drop ? 0.4 : 0); sparkU.uK.value = t >= L.hats ? out(prog(t, L.hats, 0.4)) : 0;
  sparks.rotation.y = t * 0.05;
  // spectrum ring
  const kc = t >= L.chords ? out(prog(t, L.chords, 0.5)) : 0;
  const tmp = new THREE.Object3D(), c = new THREE.Color();
  for (let i = 0; i < NB; i++) {
    const a = i / NB * Math.PI * 2 + t * 0.15, band = Math.abs(((i % 32) - 16)) % 24;
    const v = (T.SPEC[f] || [])[Math.min(23, band)] || 0;
    const h = Math.max(0.02, (0.1 + 2.1 * v * v) * kc * (drop ? 1.25 : 1));
    const R = 4.6 + (drop ? 0.4 * ke : 0);
    tmp.position.set(Math.cos(a) * R, -2.6 + h / 2, Math.sin(a) * R); tmp.scale.set(1, h, 1); tmp.rotation.set(0, -a, 0); tmp.updateMatrix(); bars.setMatrixAt(i, tmp.matrix);
    c.copy(drop ? cols[i % 5] : PAL.chords).multiplyScalar(0.75 + v * 0.7); bars.setColorAt(i, c);
  }
  bars.instanceMatrix.needsUpdate = true; bars.instanceColor.needsUpdate = true; bars.visible = kc > 0;
  // helix
  const kl = t >= L.lead ? out(prog(t, L.lead, 0.6)) : 0;
  for (let i = 0; i < HN; i++) { const u = i / HN, a = u * Math.PI * 12 + t * 2.4 * (i % 2 ? 1 : -1), r = 2.3 + 0.4 * Math.sin(u * 20 + t * 3) + lead * 0.6;
    hpos[i * 3] = Math.cos(a) * r; hpos[i * 3 + 1] = (u - 0.5) * 9 * kl; hpos[i * 3 + 2] = Math.sin(a) * r; }
  hgeo.attributes.position.needsUpdate = true; helix.visible = kl > 0; helix.material.opacity = 0.35 + 0.65 * lead;
  // drop burst: particles explode from the core and orbit
  burst.visible = drop;
  if (drop) { const dt = t - L.drop;
    for (let i = 0; i < BN; i++) { const a = hash(i, 1) * 6.283 + dt * (0.3 + hash(i, 4)), b = (hash(i, 2) - 0.5) * 3.0, v = 3 + 9 * hash(i, 3);
      const r = Math.min(v * Math.sqrt(dt) * 1.4, 4 + 9 * hash(i, 3)) * (1 + 0.12 * ke);
      bpos[i * 3] = Math.cos(a) * Math.cos(b) * r; bpos[i * 3 + 1] = Math.sin(b) * r * 0.7; bpos[i * 3 + 2] = Math.sin(a) * Math.cos(b) * r; }
    bgeo.attributes.position.needsUpdate = true; }
  // camera: slow orbit, rises through the build, fast orbit on the drop
  let ang = t * 0.12, rad = lerp(17, 13, out(prog(t, 0, L.lead))), ht = lerp(2.0, 5.5, out(prog(t, L.bass, 4)));
  if (inBuild) { ang += buildK * buildK * 3.5; rad = lerp(13, 8.5, io(buildK)); ht = lerp(5.5, 9, io(buildK)); }
  if (drop) { ang = 0.12 * L.drop + 3.5 + (t - L.drop) * 0.55; rad = lerp(8.5, 15, expo(prog(t, L.drop, 1.2))); ht = lerp(9, 4.5, expo(prog(t, L.drop, 1.2))); }
  const shake = inBuild ? 0.12 * buildK * buildK : drop ? 0.06 * ke : 0;
  camera.position.set(Math.sin(ang) * rad + shake * noise(t * 40, 1), ht + shake * noise(t * 40, 2), Math.cos(ang) * rad);
  camera.lookAt(0, -0.4, 0);
  S.bloom.strength = 0.45 + (drop ? 0.35 * ke : 0) + buildK * 0.4;
  S.film.uniforms.uFlash.value = drop ? 0.9 * Math.exp(-(t - L.drop) * 6) : inBuild ? 0.35 * Math.pow(buildK, 6) : 0;
  S.film.uniforms.uFade.value = clamp(1 - t / 0.3);
  S.render(t);
};
resolveReady();
