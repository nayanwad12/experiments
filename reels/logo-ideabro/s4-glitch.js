// IDEABRO STUDIO / style 4: GLITCH.
// The lockup boots up through a corrupted signal: torn scanlines, RGB split, block displacement, posterised frames
// and inverted flashes. It snaps clean, then glitches twice more while it holds.
import { stage } from '/batch2/lib/stage.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { lockup, lockupCanvas, fitter, E, THREE } from './lib.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.25, bloomThreshold: 0.9, bloomRadius: 0.35, bg: '#000000', fov: 30, env: false, samples: 0,
  timeline: '/logo-ideabro/work/timeline.json' });
const { scene, camera, film, composer } = S, T = S.TL.glitch;
S.renderer.toneMapping = THREE.NoToneMapping;             // flat artwork: pure white, pure black
const { clamp, prog, lerp, io, hash } = E;
const L = await lockup(), fit = fitter(L);

const CW = 2400, CH = Math.round(CW * L.h / L.w * 1.08);
const lc = lockupCanvas(L, CW, CH, { u: CW / (L.w * 1.08) });
const flat = new THREE.Mesh(new THREE.PlaneGeometry(CW / lc.u, CH / lc.u),
  new THREE.MeshBasicMaterial({ map: lc.tex, transparent: true, toneMapped: false }));
scene.add(flat);

const glitch = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uAmt: { value: 0 }, uT: { value: 0 }, uReveal: { value: 1 }, uAsp: { value: 1 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uAmt, uT, uReveal, uAsp; varying vec2 vUv;
    float h(float x){ return fract(sin(x * 91.17 + floor(uT * 30.) * 13.7) * 43758.5); }
    float hs(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + floor(uT * 30.) * 3.1) * 43758.5); }
    void main(){
      vec2 uv = vUv;
      float row = floor(uv.y * 44.), row2 = floor(uv.y * 9.);
      float tear = step(1. - uAmt * 0.65, h(row));
      uv.x += (h(row + 3.) - .5) * 0.3 * uAmt * tear;
      float big = step(0.88, h(row2 + 50.)) * uAmt; uv.x += (h(row2 + 7.) - .5) * 0.22 * big;
      // block displacement
      vec2 cell = floor(vec2(uv.x * 14. * uAsp, uv.y * 14.));
      float blk = step(1. - uAmt * 0.35, hs(cell)); uv += (vec2(hs(cell + 1.), hs(cell + 2.)) - .5) * 0.08 * blk;
      float sp = 0.03 * uAmt * (0.3 + h(row + 9.));
      vec3 c;
      c.r = texture2D(tDiffuse, uv + vec2(sp, 0.)).r;
      c.g = texture2D(tDiffuse, uv + vec2(0., sp * 0.25)).g;
      c.b = texture2D(tDiffuse, uv - vec2(sp, 0.)).b;
      // cyan / magenta fringes on torn rows
      c += vec3(0., 0.9, 1.) * texture2D(tDiffuse, uv + vec2(sp * 2.4, 0.)).g * tear * uAmt * 0.6;
      c += vec3(1., 0.1, 0.8) * texture2D(tDiffuse, uv - vec2(sp * 2.4, 0.)).g * big * 0.6;
      // reveal: whole rows appear as the signal locks
      c *= step(h(row + 77.) * 0.999, uReveal);
      // scanlines, posterise, noise, inversions
      c *= 1. - 0.3 * uAmt * step(0.5, fract(vUv.y * 360.));
      c = mix(c, floor(c * 3.) / 3., uAmt * 0.5 * step(0.6, h(5.)));
      c += (hs(vUv * 700.) - 0.5) * 0.22 * uAmt;
      c += vec3(0.85) * step(0.995, hs(vec2(floor(vUv.y * 220.), 1.))) * uAmt;
      float inv = step(0.95, h(31.)) * step(0.45, uAmt); c = mix(c, 1. - c, inv);
      gl_FragColor = vec4(c, 1.);
    }` });
composer.insertPass(glitch, composer.passes.length - 1);
glitch.uniforms.uAsp.value = innerWidth / innerHeight;

window.renderFrame = t => {
  // heavy corruption while it boots, settling into the clean lockup
  const boot = 1 - io(prog(t, T.in, T.settle - T.in));
  const burst = hash(Math.floor(t * 14), 5) > 0.72 ? 0.5 : 0;
  let amt = t < T.in ? 0 : Math.min(1, boot * (0.55 + burst + 0.45 * hash(Math.floor(t * 30), 2)));
  for (const b of T.blips) { const dt = t - b; if (dt > 0 && dt < 0.22) amt = Math.max(amt, 0.75 * (hash(Math.floor(t * 30), 8) > 0.3 ? 1 : 0.2)); }
  glitch.uniforms.uAmt.value = amt; glitch.uniforms.uT.value = t;
  glitch.uniforms.uReveal.value = t < T.in ? 0 : clamp(prog(t, T.in, (T.settle - T.in) * 0.75) * 1.05);
  flat.scale.setScalar(1 + 0.03 * amt * Math.sin(t * 90));
  flat.position.x = 0.06 * amt * (hash(Math.floor(t * 30), 3) - 0.5);
  camera.position.set(0, 0, fit(30) * lerp(1.04, 1.0, io(prog(t, 0, T.dur)))); camera.lookAt(0, 0, 0);
  film.uniforms.uGrain.value = 0.03 + 0.05 * amt; film.uniforms.uVig.value = 0.3; film.uniforms.uChroma.value = 0.0005;
  film.uniforms.uFlash.value = 0.25 * Math.exp(-18 * Math.max(0, t - T.settle)) * +(t >= T.settle);
  film.uniforms.uFade.value = 0;
  S.render(t);
};
resolveReady();
