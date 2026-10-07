// IDEABRO STUDIO / style 1: LIQUID CHROME.
// A mercury blob churns, collapses with a splash, and the lockup grows out of it in polished chrome.
import { stage } from '/batch2/lib/stage.js';
import { lockup, solid, stripEnv, fitter, E, THREE, canvasTex } from './lib.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.45, bloomThreshold: 1.0, bloomRadius: 0.4, bg: '#040406', fov: 30, env: false, samples: 4,
  timeline: '/logo-ideabro/work/timeline.json' });
const { scene, camera, renderer, film } = S, T = S.TL.chrome;
const { clamp, prog, lerp, out, io, expo, back, hash } = E;
const L = await lockup(), fit = fitter(L);
const ENV = stripEnv(renderer, '#cfe0ff', 1);

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

// ---------------------------------------------------------------- chrome
const chrome = new THREE.MeshPhysicalMaterial({ color: '#f2f4fa', metalness: 1, roughness: 0.05, envMap: ENV, envMapIntensity: 1.15 });
const chromeSide = new THREE.MeshPhysicalMaterial({ color: '#dfe3ec', metalness: 1, roughness: 0.1, envMap: ENV, envMapIntensity: 1.3 });
const blobU = { uT: { value: 0 }, uAmp: { value: 0.35 } };
const blobMat = chrome.clone();
blobMat.onBeforeCompile = sh => {
  Object.assign(sh.uniforms, blobU);
  sh.vertexShader = 'uniform float uT; uniform float uAmp;\n' + NOISE + '\n' + sh.vertexShader
    .replace('#include <beginnormal_vertex>', `#include <beginnormal_vertex>
      float nn = snoise(normal * 1.3 + vec3(0., uT * 0.8, uT * 0.35)) + 0.35 * snoise(normal * 3.1 + uT * 1.3);`)
    .replace('#include <begin_vertex>', `#include <begin_vertex>
      transformed += normal * nn * uAmp;`);
};
const blob = new THREE.Mesh(new THREE.IcosahedronGeometry(1.25, 48), blobMat); scene.add(blob);

const logo = new THREE.Group(); scene.add(logo);
const parts = [
  new THREE.Mesh(solid(L.icon, 0.34, 0.03), [chrome, chromeSide]),
  new THREE.Mesh(solid(L.name.flat(), 0.2, 0.016, 4, false), [chrome, chromeSide]),
  new THREE.Mesh(solid(L.studio.flat(), 0.08, 0.008, 3, false), [chrome, chromeSide]),
];
parts.forEach(p => logo.add(p));
const drops = [...Array(26)].map((_, i) => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.035 + 0.06 * hash(i, 1), 20, 14), chrome); scene.add(m); return m; });

// back plate: soft cool pool of light
const spot = canvasTex(512, 512); { const c = spot.ctx, g = c.createRadialGradient(256, 256, 0, 256, 256, 256);
  g.addColorStop(0, 'rgba(70,82,112,0.9)'); g.addColorStop(0.5, 'rgba(18,20,30,0.6)'); g.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = g; c.fillRect(0, 0, 512, 512); spot.update(); }
const plate = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.MeshBasicMaterial({ map: spot.tex, transparent: true, depthWrite: false }));
plate.position.z = -7; scene.add(plate);

window.renderFrame = t => {
  const melt = io(prog(t, T.melt, 0.8));
  blobU.uT.value = t * 1.5; blobU.uAmp.value = lerp(0.3, 0.85, melt) * (0.8 + 0.2 * Math.sin(t * 2));
  blob.scale.setScalar(Math.max(0.001, lerp(0.9, 1.1, io(prog(t, 0, T.melt))) * (1 - melt)));
  blob.rotation.set(t * 0.3, t * 0.45, 0);
  blob.visible = melt < 1;
  // lockup grows out of the splash: icon first, then the words
  const grow = (t0, d) => Math.max(0.001, back(prog(t, t0, d), 1.25));
  parts[0].scale.setScalar(grow(T.form, 0.75));
  parts[1].scale.setScalar(grow(T.form + 0.18, 0.7)); parts[1].position.y = lerp(-0.6, 0, expo(prog(t, T.form + 0.18, 0.8)));
  parts[2].scale.setScalar(grow(T.form + 0.36, 0.6)); parts[2].position.y = lerp(-0.4, 0, expo(prog(t, T.form + 0.36, 0.7)));
  parts.forEach(p => (p.visible = t > T.form - 0.02));
  const spin = expo(prog(t, T.form, 1.4));
  logo.rotation.set(0.12 * Math.sin(t * 0.7) * (1 - 0.6 * prog(t, T.settle, 2)), lerp(-1.3, 0, spin) + 0.16 * Math.sin(t * 0.55 + 0.6), 0);
  const er = lerp(-0.6, 0.9, io(prog(t, T.form, T.dur - T.form)));
  [chrome, chromeSide, blobMat].forEach(m => m.envMapRotation.set(0, er, 0));
  drops.forEach((d, i) => {
    const dt = t - T.melt - 0.35 - 0.12 * hash(i, 9); d.visible = dt > 0 && dt < 1.8;
    const a = hash(i, 2) * Math.PI * 2, v = 1.6 + 3.4 * hash(i, 3);
    d.position.set(Math.cos(a) * v * dt, -0.2 + (2.2 + 2.4 * hash(i, 4)) * dt - 4.9 * dt * dt, Math.sin(a) * v * dt * 0.6 + 0.6);
  });
  const d = fit(30) * lerp(0.92, 1.0, io(prog(t, 0, T.dur)));
  camera.position.set(0.5 * Math.sin(t * 0.4), 0.25 + 0.15 * Math.sin(t * 0.3), d); camera.lookAt(0, 0, 0);
  film.uniforms.uGrain.value = 0.03; film.uniforms.uChroma.value = 0.0005;
  film.uniforms.uFlash.value = 0.18 * Math.exp(-14 * Math.max(0, t - T.form)) * +(t >= T.form);
  film.uniforms.uFade.value = 1 - clamp(prog(t, 0, 0.2));
  S.render(t);
};
resolveReady();
