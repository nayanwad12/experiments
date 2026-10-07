// B2-03 Five logo reveals: liquid chrome, particle storm, neon sign, glitch, heavy metal.
import { stage, E, canvasTex, rr, THREE, loadFonts } from '/batch2/lib/stage.js';
import { TTFLoader } from 'three/addons/loaders/TTFLoader.js';
import { Font } from 'three/addons/loaders/FontLoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.8, bloomThreshold: 1.0, bloomRadius: 0.5, bg: '#050507', fov: 35, shadows: true,
  timeline: '/batch2/03-logo-reveals/work/timeline.json', fonts: [['Unb', 'Unbounded-Black.ttf']] });
const { scene, camera, renderer } = S, T = S.TL;
const { clamp, prog, lerp, out, io, expo, back, hash, noise } = E;
const LIME = new THREE.Color('#D4FF3F');
S.film.uniforms.uGrain.value = 0.04;

// ---------------------------------------------------------------- logo geometry sources
const font = new Font(await new Promise(r => new TTFLoader().load('/fonts/Unbounded-Black.ttf', r)));
const LAY = { icon: [0, 1.45], vibe: [0, -0.35], edit: [0, -1.12], size: 0.56, isz: 1.05 };
function iconShape(L = LAY.isz, R = 0.3) {
  const sh = new THREE.Shape();
  sh.moveTo(-L + R, -L); sh.lineTo(L - R, -L); sh.quadraticCurveTo(L, -L, L, -L + R); sh.lineTo(L, L - R);
  sh.quadraticCurveTo(L, L, L - R, L); sh.lineTo(-L + R, L); sh.quadraticCurveTo(-L, L, -L, L - R); sh.lineTo(-L, -L + R);
  sh.quadraticCurveTo(-L, -L, -L + R, -L);
  const h = new THREE.Path(); h.moveTo(-0.3 * L, -0.46 * L); h.lineTo(0.5 * L, 0); h.lineTo(-0.3 * L, 0.46 * L); h.lineTo(-0.3 * L, -0.46 * L);
  sh.holes.push(h); return sh;
}
function textGeo(s, size, depth, bevel = true) {
  const g = new TextGeometry(s, { font, size, depth, curveSegments: 6, bevelEnabled: bevel, bevelThickness: 0.03, bevelSize: 0.02, bevelSegments: 3 });
  g.computeBoundingBox(); const bb = g.boundingBox; g.translate(-(bb.max.x + bb.min.x) / 2, -(bb.max.y + bb.min.y) / 2, -depth / 2); return g;
}
function logoMeshes(mat, depth = 0.35) {
  const grp = new THREE.Group();
  const ig = new THREE.ExtrudeGeometry(iconShape(), { depth, bevelEnabled: true, bevelThickness: 0.05, bevelSize: 0.05, bevelSegments: 4, curveSegments: 16 });
  ig.center();
  const icon = new THREE.Mesh(ig, mat); icon.position.set(...LAY.icon, 0); grp.add(icon);
  const v = new THREE.Mesh(textGeo('VIBE', LAY.size, depth * 0.7), mat); v.position.set(...LAY.vibe, 0); grp.add(v);
  const e = new THREE.Mesh(textGeo('EDITING', LAY.size * 0.82, depth * 0.7), mat); e.position.set(...LAY.edit, 0); grp.add(e);
  grp.userData = { icon, v, e }; return grp;
}
// flat 2D logo on a canvas (glitch set + particle sampling)
function logoCanvas(w = 1024, h = 1820, col = '#D4FF3F', text = '#ffffff', bg = null) {
  const ct = canvasTex(w, h), c = ct.ctx, u = w / 4.0;                    // 4 world units across
  if (bg) { c.fillStyle = bg; c.fillRect(0, 0, w, h); }
  const X = x => w / 2 + x * u, Y = y => h / 2 - y * u;
  const L = LAY.isz * u, R = 0.3 * u, cx = X(LAY.icon[0]), cy = Y(LAY.icon[1]);
  c.fillStyle = col; rr(c, cx - L, cy - L, 2 * L, 2 * L, R); c.fill();
  c.globalCompositeOperation = bg ? 'source-over' : 'destination-out'; c.fillStyle = bg || '#000';
  c.beginPath(); c.moveTo(cx - 0.3 * L, cy - 0.46 * L); c.lineTo(cx + 0.5 * L, cy); c.lineTo(cx - 0.3 * L, cy + 0.46 * L); c.closePath(); c.fill();
  c.globalCompositeOperation = 'source-over';
  c.fillStyle = text; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.font = `900 ${Math.round(LAY.size * u * 1.02)}px Unb`; c.fillText('VIBE', X(0), Y(LAY.vibe[1]));
  c.font = `900 ${Math.round(LAY.size * 0.82 * u * 1.02)}px Unb`; c.fillText('EDITING', X(0), Y(LAY.edit[1]));
  ct.update(); return { ...ct, u };
}

// ---------------------------------------------------------------- shared noise (GLSL)
const NOISE = `vec3 mod289(vec3 x){return x-floor(x*(1./289.))*289.;}vec4 mod289(vec4 x){return x-floor(x*(1./289.))*289.;}
vec4 permute(vec4 x){return mod289(((x*34.)+1.)*x);}vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){const vec2 C=vec2(1./6.,1./3.);const vec4 D=vec4(0.,.5,1.,2.);vec3 i=floor(v+dot(v,C.yyy));vec3 x0=v-i+dot(i,C.xxx);
vec3 g=step(x0.yzx,x0.xyz);vec3 l=1.-g;vec3 i1=min(g.xyz,l.zxy);vec3 i2=max(g.xyz,l.zxy);vec3 x1=x0-i1+C.xxx;vec3 x2=x0-i2+C.yyy;vec3 x3=x0-D.yyy;
i=mod289(i);vec4 p=permute(permute(permute(i.z+vec4(0.,i1.z,i2.z,1.))+i.y+vec4(0.,i1.y,i2.y,1.))+i.x+vec4(0.,i1.x,i2.x,1.));
float n_=.142857142857;vec3 ns=n_*D.wyz-D.xzx;vec4 j=p-49.*floor(p*ns.z*ns.z);vec4 x_=floor(j*ns.z);vec4 y_=floor(j-7.*x_);
vec4 x=x_*ns.x+ns.yyyy;vec4 y=y_*ns.x+ns.yyyy;vec4 h=1.-abs(x)-abs(y);vec4 b0=vec4(x.xy,y.xy);vec4 b1=vec4(x.zw,y.zw);
vec4 s0=floor(b0)*2.+1.;vec4 s1=floor(b1)*2.+1.;vec4 sh=-step(h,vec4(0.));vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
vec3 p0=vec3(a0.xy,h.x);vec3 p1=vec3(a0.zw,h.y);vec3 p2=vec3(a1.xy,h.z);vec3 p3=vec3(a1.zw,h.w);
vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
vec4 m=max(.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.);m=m*m;return 42.*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));}`;

// ---------------------------------------------------------------- dark studio env with strip lights (for chrome / steel)
function stripEnv() {
  const sc = new THREE.Scene(); sc.background = new THREE.Color('#020203');
  const strip = (w, h, pos, rot, c, k) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(c).multiplyScalar(k), side: THREE.DoubleSide }));
    m.position.set(...pos); m.rotation.set(...rot); sc.add(m); };
  strip(1.2, 12, [-6, 0, 1], [0, Math.PI / 2, 0], '#ffffff', 2.2);
  strip(0.6, 12, [6, 0, -1], [0, -Math.PI / 2, 0], '#ffffff', 1.6);
  strip(12, 0.8, [0, 6, 2], [Math.PI / 2, 0, 0], '#ffffff', 1.4);
  strip(4, 0.5, [0, -2, -6], [0, 0, 0], '#D4FF3F', 1.2);
  strip(3, 3, [2, 2, 7], [0, Math.PI, 0], '#9fb4ff', 0.6);
  // the chrome 'horizon': a big gradient wall behind the camera (front faces reflect it)
  const hz = canvasTex(64, 512), c = hz.ctx, g = c.createLinearGradient(0, 0, 0, 512);
  g.addColorStop(0, '#0b0d18'); g.addColorStop(0.42, '#6f7896'); g.addColorStop(0.5, '#ffffff'); g.addColorStop(0.53, '#c9d0e6');
  g.addColorStop(0.62, '#2a2c36'); g.addColorStop(1, '#131318'); c.fillStyle = g; c.fillRect(0, 0, 64, 512); hz.update();
  const front = new THREE.Mesh(new THREE.PlaneGeometry(30, 16), new THREE.MeshBasicMaterial({ map: hz.tex, side: THREE.DoubleSide }));
  front.position.set(0, 0, 9); front.rotation.y = Math.PI; sc.add(front);
  const pm = new THREE.PMREMGenerator(renderer); return pm.fromScene(sc, 0.02).texture;
}
const ENV = stripEnv();

// ================================================================= SET 1: liquid chrome
const set1 = new THREE.Group(); scene.add(set1);
const chrome = new THREE.MeshPhysicalMaterial({ color: '#f4f6ff', metalness: 1, roughness: 0.06, envMap: ENV, envMapIntensity: 1.0 });
const blobU = { uT: { value: 0 }, uAmp: { value: 0.35 } };
const blobMat = chrome.clone();
blobMat.onBeforeCompile = sh => {
  Object.assign(sh.uniforms, blobU);
  sh.vertexShader = 'uniform float uT; uniform float uAmp;\n' + NOISE + '\n' + sh.vertexShader
    .replace('#include <beginnormal_vertex>', `#include <beginnormal_vertex>
      float nn = snoise(normal * 1.4 + vec3(0., uT * 0.9, uT * 0.4));`)
    .replace('#include <begin_vertex>', `#include <begin_vertex>
      transformed += normal * nn * uAmp;`);
};
const blob = new THREE.Mesh(new THREE.IcosahedronGeometry(1.7, 40), blobMat); set1.add(blob);
const logo1 = logoMeshes(chrome, 0.38); set1.add(logo1);
const drops = [...Array(14)].map((_, i) => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.06 + 0.07 * hash(i, 1), 16, 12), chrome); set1.add(m); return m; });
const spot1 = canvasTex(256, 256); { const c = spot1.ctx, g = c.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, 'rgba(120,130,170,0.55)'); g.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = g; c.fillRect(0, 0, 256, 256); spot1.update(); }
const bg1 = new THREE.Mesh(new THREE.PlaneGeometry(22, 22), new THREE.MeshBasicMaterial({ map: spot1.tex, transparent: true, depthWrite: false }));
bg1.position.z = -6; set1.add(bg1);

function do1(lt, t) {
  const melt = io(prog(lt, 0.45, 0.9));
  blobU.uT.value = t * 1.6; blobU.uAmp.value = lerp(0.42, 0.9, melt);
  blob.scale.setScalar(Math.max(0.001, 1.15 * (1 - melt)));
  blob.position.y = lerp(0.3, -0.6, melt);
  const k = back(prog(lt, 0.75, 0.75), 1.3);
  logo1.scale.setScalar(Math.max(0.001, k)); logo1.position.y = lerp(-1.2, 0, expo(prog(lt, 0.7, 0.8)));
  logo1.rotation.set(0.25 * Math.sin(t * 0.7) * k, lerp(-1.2, 0, expo(prog(lt, 0.7, 1.1))) + 0.22 * Math.sin(t * 0.6), 0);
  drops.forEach((d, i) => {
    const dt = lt - 0.8; d.visible = dt > 0 && dt < 1.5;
    const a = hash(i, 2) * Math.PI * 2, v = 2.5 + 3 * hash(i, 3);
    d.position.set(Math.cos(a) * v * dt, -0.3 + (2.5 + 2 * hash(i, 4)) * dt - 5 * dt * dt, Math.sin(a) * v * dt * 0.5 + 0.8);
  });
  camera.position.set(0.6 * Math.sin(t * 0.4), 0.3, lerp(11.5, 10.2, io(prog(lt, 0, 2.7)))); camera.lookAt(0, 0.1, 0);
}

// ================================================================= SET 2: particle storm
const set2 = new THREE.Group(); scene.add(set2);
const lc = logoCanvas(512, 910, '#D4FF3F', '#ffffff');
const px = lc.ctx.getImageData(0, 0, 512, 910).data;
const tg = [], col = [];
for (let y = 0; y < 910; y += 2) for (let x = 0; x < 512; x += 2) {
  const i = (y * 512 + x) * 4; if (px[i + 3] > 140) { tg.push((x - 256) / (512 / 4), (455 - y) / (512 / 4), 0); col.push(px[i] / 255, px[i + 1] / 255, px[i + 2] / 255); }
}
const NP = tg.length / 3;
const pg = new THREE.BufferGeometry();
pg.setAttribute('position', new THREE.Float32BufferAttribute(tg, 3));
pg.setAttribute('aCol', new THREE.Float32BufferAttribute(col, 3));
const seeds = new Float32Array(NP * 3); for (let i = 0; i < NP; i++) { seeds[i * 3] = hash(i, 1); seeds[i * 3 + 1] = hash(i, 2); seeds[i * 3 + 2] = hash(i, 3); }
pg.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 3));
const pU = { uK: { value: 0 }, uT: { value: 0 }, uSize: { value: 5.0 } };
const pmat = new THREE.ShaderMaterial({ uniforms: pU, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  vertexShader: `attribute vec3 aCol; attribute vec3 aSeed; uniform float uK, uT, uSize; varying vec3 vC; varying float vA;
    void main(){
      float d = aSeed.x * 0.55; float k = clamp((uK - d) / 0.45, 0., 1.); k = 1. - pow(1. - k, 3.);
      float r = 5. + 9. * aSeed.y; float a = aSeed.z * 6.2832 + uT * (1.6 + aSeed.y) ;
      vec3 start = vec3(cos(a) * r, (aSeed.x - 0.5) * 16. + sin(a * 2.) * 1.5, sin(a) * r - 2.);
      vec3 p = mix(start, position, k);
      p += vec3(sin(uT * 3. + aSeed.y * 40.), cos(uT * 2.6 + aSeed.z * 40.), 0.) * 0.02 * k;
      vec4 mv = modelViewMatrix * vec4(p, 1.);
      gl_Position = projectionMatrix * mv;
      gl_PointSize = uSize * (1.0 + 2.0 * (1. - k)) * (10. / -mv.z);
      vC = mix(vec3(0.6, 0.75, 1.0), aCol, k) * (1.2 + 1.4 * (1. - k)); vA = 0.55 + 0.45 * k;
    }`,
  fragmentShader: `varying vec3 vC; varying float vA; void main(){ vec2 d = gl_PointCoord - .5; float r = length(d); if (r > .5) discard;
      gl_FragColor = vec4(vC, vA * smoothstep(.5, .0, r)); }` });
const points = new THREE.Points(pg, pmat); set2.add(points);
const flat2 = new THREE.Mesh(new THREE.PlaneGeometry(4, 4 * 910 / 512), new THREE.MeshBasicMaterial({ map: lc.tex, transparent: true, toneMapped: false }));
flat2.position.z = 0.01; set2.add(flat2);
function do2(lt, t) {
  pU.uK.value = clamp(lt / 1.55); pU.uT.value = t; flat2.material.opacity = clamp((lt - 1.45) / 0.3);
  points.material.opacity = 1;
  set2.rotation.y = lerp(0.9, 0, expo(prog(lt, 0, 1.6))) + 0.08 * Math.sin(t * 0.7);
  camera.position.set(0, 0.2, lerp(13, 10.4, io(prog(lt, 0, 2.7)))); camera.lookAt(0, 0.1, 0);
}

// ================================================================= SET 3: neon sign on bricks
const set3 = new THREE.Group(); scene.add(set3);
const bricks = canvasTex(1024, 1024); {
  const c = bricks.ctx; c.fillStyle = '#1b1210'; c.fillRect(0, 0, 1024, 1024);
  for (let r = 0; r < 16; r++) for (let k = -1; k < 9; k++) {
    const x = k * 128 + (r % 2) * 64, y = r * 64, sh = 0.75 + 0.5 * hash(r, k);
    c.fillStyle = `rgb(${Math.round(70 * sh)},${Math.round(36 * sh)},${Math.round(30 * sh)})`; c.fillRect(x + 4, y + 4, 120, 56);
    for (let n = 0; n < 40; n++) { c.fillStyle = `rgba(0,0,0,${0.15 * hash(r, k, n)})`; c.fillRect(x + 4 + 120 * hash(n, r, k), y + 4 + 56 * hash(k, n, r), 6, 4); }
  }
  bricks.tex.wrapS = bricks.tex.wrapT = THREE.RepeatWrapping; bricks.tex.repeat.set(3, 5); bricks.update();
}
const wall = new THREE.Mesh(new THREE.PlaneGeometry(14, 24), new THREE.MeshStandardMaterial({ map: bricks.tex, roughness: 0.9, metalness: 0 }));
wall.position.z = -0.35; set3.add(wall);
const tubeOn = (hex, mult) => new THREE.MeshBasicMaterial({ color: new THREE.Color(hex).multiplyScalar(mult), toneMapped: false });
let TUBE_R = 0.03;
const neonGroups = [];
function addNeon(shapes, offset, scale, hex) {
  const grp = new THREE.Group(), on = tubeOn(hex, 1.9), off = new THREE.MeshStandardMaterial({ color: '#2a2a2e', roughness: 0.3 });
  for (const sh of shapes) for (const contour of [sh, ...sh.holes]) {
    const pts = contour.getPoints(48).map(p => new THREE.Vector3(p.x * scale + offset[0], p.y * scale + offset[1], 0.05));
    const curve = new THREE.CatmullRomCurve3(pts, true, 'centripetal');
    grp.add(new THREE.Mesh(new THREE.TubeGeometry(curve, Math.max(40, pts.length * 2), TUBE_R, 8, true), on));
  }
  grp.userData = { on, off }; set3.add(grp); neonGroups.push(grp); return grp;
}
const ng0 = addNeon([iconShape(0.95, 0.28)], [0, 1.45], 1, '#D4FF3F');
TUBE_R = 0.016;
const fsV = font.generateShapes('VIBE', LAY.size), fsE = font.generateShapes('EDITING', LAY.size * 0.82);
const centre = shapes => { const b = new THREE.Box2(); shapes.forEach(s => s.getPoints(8).forEach(p => b.expandByPoint(p))); return [-(b.max.x + b.min.x) / 2, -(b.max.y + b.min.y) / 2]; };
const cV = centre(fsV), cE = centre(fsE);
const ng1 = addNeon(fsV, [cV[0], LAY.vibe[1] + cV[1]], 1, '#FF4FD8');
const ng2 = addNeon(fsE, [cE[0], LAY.edit[1] + cE[1]], 1, '#4FE3FF');
const nl = [new THREE.PointLight('#D4FF3F', 0, 9), new THREE.PointLight('#FF4FD8', 0, 9), new THREE.PointLight('#4FE3FF', 0, 9)];
nl[0].position.set(0, 1.45, 1.2); nl[1].position.set(0, -0.35, 1.2); nl[2].position.set(0, -1.12, 1.2); nl.forEach(l => set3.add(l));
const flick = (lt, t0, seed) => { if (lt < t0) return 0; const dt = lt - t0; if (dt > 0.75) return hash(Math.floor(lt * 30), seed) > 0.985 ? 0.3 : 1;
  return hash(Math.floor(lt * 30), seed) > 0.55 - dt * 0.5 ? 1 : 0; };
function do3(lt, t) {
  [[ng0, 0.15, 1], [ng1, 0.55, 2], [ng2, 0.85, 3]].forEach(([g, t0, sd], i) => {
    const on = flick(lt, t0, sd); g.children.forEach(m => (m.material = on ? g.userData.on : g.userData.off));
    nl[i].intensity = on * 14;
  });
  camera.position.set(lerp(-1.2, 0.4, io(prog(lt, 0, 2.7))), 0.1, 10.2); camera.lookAt(0, 0.1, 0);
}

// ================================================================= SET 4: glitch (shader pass)
const set4 = new THREE.Group(); scene.add(set4);
const lc4 = logoCanvas(1024, 1820, '#D4FF3F', '#ffffff');
const flat4 = new THREE.Mesh(new THREE.PlaneGeometry(4, 4 * 1820 / 1024), new THREE.MeshBasicMaterial({ map: lc4.tex, transparent: true, toneMapped: false }));
set4.add(flat4);
const glitch = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uAmt: { value: 0 }, uT: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uAmt, uT; varying vec2 vUv;
    float h(float x){ return fract(sin(x * 91.17 + floor(uT * 24.) * 13.7) * 43758.5); }
    void main(){
      vec2 uv = vUv;
      float row = floor(uv.y * 38.); float blk = step(1. - uAmt * 0.6, h(row));
      uv.x += (h(row + 3.) - .5) * 0.35 * uAmt * blk;
      float big = step(0.93, h(floor(uv.y * 6.) + 50.)) * uAmt; uv.x += (h(7.) - .5) * 0.25 * big;
      float sp = 0.025 * uAmt * (0.4 + h(row + 9.));
      vec3 c = vec3(texture2D(tDiffuse, uv + vec2(sp, 0.)).r, texture2D(tDiffuse, uv).g, texture2D(tDiffuse, uv - vec2(sp, 0.)).b);
      c *= 1. - 0.25 * uAmt * step(0.5, fract(vUv.y * 480.));
      c = mix(c, floor(c * 4.) / 4., uAmt * 0.6);
      float inv = step(0.97, h(31.)) * step(0.4, uAmt); c = mix(c, 1. - c, inv);
      gl_FragColor = vec4(c, 1.);
    }` });
S.composer.insertPass(glitch, S.composer.passes.length - 1);
function do4(lt, t) {
  const settle = 1 - io(prog(lt, 0.2, 1.4));
  glitch.uniforms.uAmt.value = Math.max(settle, hash(Math.floor(t * 12), 5) > 0.9 ? 0.35 : 0); glitch.uniforms.uT.value = t;
  flat4.scale.setScalar(1 + 0.04 * settle * Math.sin(t * 60));
  camera.position.set(0, 0.2, 10.4); camera.lookAt(0, 0.1, 0);
}

// ================================================================= SET 5: heavy metal (stacking slam)
const set5 = new THREE.Group(); scene.add(set5);
const steel = new THREE.MeshPhysicalMaterial({ color: '#c9ccd4', metalness: 0.95, roughness: 0.3, envMap: ENV, envMapIntensity: 1.0 });
const steelLime = new THREE.MeshPhysicalMaterial({ color: '#b6e02a', metalness: 0.5, roughness: 0.35, envMap: ENV, envMapIntensity: 0.8 });
const conc = canvasTex(512, 512); { const c = conc.ctx; c.fillStyle = '#2a2a2e'; c.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 4000; i++) { c.fillStyle = `rgba(${hash(i, 1) > 0.5 ? 255 : 0},${hash(i, 1) > 0.5 ? 255 : 0},${hash(i, 1) > 0.5 ? 255 : 0},${0.05 * hash(i, 2)})`;
    c.fillRect(512 * hash(i, 3), 512 * hash(i, 4), 3, 3); } conc.tex.wrapS = conc.tex.wrapT = THREE.RepeatWrapping; conc.tex.repeat.set(4, 4); conc.update(); }
const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({ map: conc.tex, roughness: 0.85 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -1.48; floor.receiveShadow = true; set5.add(floor);
const sun = new THREE.DirectionalLight('#ffffff', 1.6); sun.position.set(3, 7, 5); sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024); Object.assign(sun.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: 1, far: 20 }); set5.add(sun);
const logo5 = logoMeshes(steel, 0.5); set5.add(logo5);
logo5.userData.icon.material = steelLime;
Object.values(logo5.userData).forEach(m => (m.castShadow = true));
const dust = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ color: '#9a9aa2', size: 0.08, transparent: true, depthWrite: false }));
const DN = 600, dpos = new Float32Array(DN * 3); dust.geometry.setAttribute('position', new THREE.BufferAttribute(dpos, 3)); set5.add(dust);
const LAND = [0.45, 0.95, 1.45];                       // EDITING, VIBE, icon land (stacking)
function do5(lt, t) {
  const parts = [logo5.userData.e, logo5.userData.v, logo5.userData.icon];
  const homes = [LAY.edit[1], LAY.vibe[1], LAY.icon[1]];
  let shake = 0;
  parts.forEach((m, i) => {
    const tl = LAND[i], fall = 0.32;
    if (lt < tl - fall) { m.position.y = 12; return; }
    if (lt < tl) { const k = (lt - (tl - fall)) / fall; m.position.y = lerp(homes[i] + 7, homes[i], k * k); m.scale.set(1, 1 + 0.12 * k, 1); return; }
    const dt = lt - tl; const sq = 0.22 * Math.exp(-dt * 10) * Math.cos(dt * 30);
    m.scale.set(1 + sq * 0.6, 1 - sq, 1 + sq * 0.6); m.position.y = homes[i] - 0.1 * sq;
    shake += 0.12 * Math.exp(-dt * 9) * (i + 1);
  });
  for (let j = 0; j < DN; j++) {
    const which = j % 3, dt = lt - LAND[which]; const a = hash(j, 1) * Math.PI * 2, v = 0.8 + 2.2 * hash(j, 2);
    const y0 = which === 0 ? -1.45 : homes[which - 1] + 0.35;
    if (dt <= 0 || dt > 1.4) { dpos[j * 3 + 1] = -99; continue; }
    dpos[j * 3] = Math.cos(a) * v * dt * (1.2 + which * 0.3); dpos[j * 3 + 1] = y0 + (0.6 * hash(j, 3)) * dt * 2 - 0.3 * dt * dt;
    dpos[j * 3 + 2] = Math.sin(a) * v * dt * 0.6 + 0.4;
  }
  dust.geometry.attributes.position.needsUpdate = true; dust.material.opacity = 0.7;
  logo5.rotation.y = -0.18 + 0.05 * Math.sin(t * 0.5);
  camera.position.set(0.7 + shake * noise(t * 50, 1), -0.1 + shake * noise(t * 50, 2), 11.2); camera.lookAt(0, 0.2, 0);
}

// ---------------------------------------------------------------- run
const SETS = [set1, set2, set3, set4, set5], DO = [do1, do2, do3, do4, do5];
window.renderFrame = t => {
  let i, lt, flash = 0;
  if (t < T.REV[0]) {                         // teaser: strobe through the final states, one per beat
    const beat = 60 / T.BPM; const n = Math.floor(t / beat); i = n % 5; lt = 2.2 + (t % beat);
    flash = 0.5 * Math.exp(-(t % beat) * 14);
  } else {
    i = T.REV.findLastIndex(r => t >= r); i = Math.min(i, 4); lt = t - T.REV[i];
    if (t >= T.RECAP) lt = Math.min(lt, 2.6) + (t - T.RECAP) * 0.2;
    flash = 0.75 * Math.exp(-(t - T.REV[i]) * 10);
  }
  SETS.forEach((s, j) => (s.visible = j === i));
  scene.background = new THREE.Color(i === 2 ? '#0b0605' : i === 4 ? '#0c0c0f' : '#050507');
  glitch.enabled = i === 3; glitch.uniforms.uAmt.value = 0;
  DO[i](lt, t);
  S.film.uniforms.uFlash.value = flash;
  S.film.uniforms.uFade.value = clamp(1 - t / 0.15);
  S.render(t);
};
resolveReady();
