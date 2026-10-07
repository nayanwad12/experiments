// B2-02 Launch ad: phone falls in, boots, Saveo UI comes alive, coins -> jar, bars rise out of the screen,
// app icon, wireframe reveal, then the ad in four formats.
import { stage, E, canvasTex, rr, THREE } from '/batch2/lib/stage.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

let resolveReady; window.READY = new Promise(r => (resolveReady = r));
const S = await stage({ bloom: 0.45, bloomThreshold: 0.95, bg: '#06080f', fov: 32, envIntensity: 0.9,
  timeline: '/batch2/02-launch-ad/work/timeline.json',
  fonts: [['IT9', 'InterTight-900.ttf'], ['IT8', 'InterTight-800.ttf'], ['IT5', 'InterTight-500.ttf'], ['JBM', 'JetBrainsMono-500.ttf']] });
const { scene, camera } = S, T = S.TL;
const { clamp, prog, lerp, out, io, expo, back, hash, noise } = E;
const MINT = T.MINT, VIOLET = T.VIOLET;
S.film.uniforms.uGrain.value = 0.03;

// ---------------------------------------------------------------- backdrop glow + lights
const glow = canvasTex(512, 512); { const c = glow.ctx, g = c.createRadialGradient(256, 256, 0, 256, 256, 256);
  g.addColorStop(0, 'rgba(124,92,255,0.55)'); g.addColorStop(0.45, 'rgba(52,227,160,0.16)'); g.addColorStop(1, 'rgba(0,0,0,0)');
  c.fillStyle = g; c.fillRect(0, 0, 512, 512); glow.update(); }
const back_ = new THREE.Mesh(new THREE.PlaneGeometry(26, 26), new THREE.MeshBasicMaterial({ map: glow.tex, transparent: true, depthWrite: false }));
back_.position.z = -8; scene.add(back_);
const rimA = new THREE.PointLight(MINT, 60, 30); rimA.position.set(4, 3, -2); scene.add(rimA);
const rimB = new THREE.PointLight(VIOLET, 60, 30); rimB.position.set(-4, -2, -1); scene.add(rimB);
const key = new THREE.DirectionalLight('#ffffff', 1.2); key.position.set(2, 3, 6); scene.add(key);

// ---------------------------------------------------------------- phone
const phone = new THREE.Group(); scene.add(phone);
const bodyMat = new THREE.MeshPhysicalMaterial({ color: '#2b2e35', metalness: 0.95, roughness: 0.28, clearcoat: 0.6 });
const body = new THREE.Mesh(new RoundedBoxGeometry(2.2, 4.6, 0.24, 8, 0.32), bodyMat); phone.add(body);
for (const [y, h] of [[1.2, 0.5], [0.55, 0.5]]) { const b = new THREE.Mesh(new RoundedBoxGeometry(0.05, h, 0.08, 2, 0.02), bodyMat);
  b.position.set(-1.115, y, 0); phone.add(b); }
const bump = new THREE.Mesh(new RoundedBoxGeometry(0.9, 0.9, 0.08, 4, 0.2), bodyMat); bump.position.set(0.45, 1.65, -0.15); phone.add(bump);
for (const [x, y] of [[0.26, 1.85], [0.64, 1.85], [0.26, 1.45]]) {
  const l = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.06, 32), new THREE.MeshPhysicalMaterial({ color: '#0a0a0e', metalness: 0.2, roughness: 0.05, clearcoat: 1 }));
  l.rotation.x = Math.PI / 2; l.position.set(x, y, -0.2); phone.add(l);
}
const UI = canvasTex(900, 1944);
const screenMat = new THREE.MeshBasicMaterial({ map: UI.tex, transparent: true, toneMapped: false });
const screen = new THREE.Mesh(new THREE.PlaneGeometry(2.06, 4.45), screenMat); screen.position.z = 0.122; phone.add(screen);
// wireframe twins (for the "it's all code" reveal)
const wireMat = new THREE.LineBasicMaterial({ color: '#D4FF3F', transparent: true });
const wire = new THREE.LineSegments(new THREE.EdgesGeometry(body.geometry, 20), wireMat); phone.add(wire);
const wireFill = new THREE.Mesh(body.geometry, new THREE.MeshBasicMaterial({ color: '#D4FF3F', wireframe: true, transparent: true, opacity: 0.25 })); phone.add(wireFill);

// ---------------------------------------------------------------- UI drawing (canvas, 900 x 1944)
function txt(c, s, x, y, font, color, align = 'left') { c.font = font; c.fillStyle = color; c.textAlign = align; c.fillText(s, x, y); }
const inr = v => '₹' + Math.round(v).toLocaleString('en-IN');
function uiFrame(c, blueprint) {
  c.clearRect(0, 0, 900, 1944);
  c.save(); rr(c, 0, 0, 900, 1944, 120); c.clip();
  if (blueprint) { c.fillStyle = '#04060a'; c.fillRect(0, 0, 900, 1944); }
  else { const g = c.createLinearGradient(0, 0, 0, 1944); g.addColorStop(0, '#0d1226'); g.addColorStop(1, '#070a14'); c.fillStyle = g; c.fillRect(0, 0, 900, 1944); }
}
function statusBar(c) {
  txt(c, '9:41', 90, 92, '600 44px IT8', '#ffffff'); c.fillStyle = '#000'; rr(c, 330, 34, 240, 72, 36); c.fill();
  c.fillStyle = '#fff'; for (let i = 0; i < 4; i++) c.fillRect(690 + i * 16, 86 - i * 9, 10, 10 + i * 9); rr(c, 770, 60, 64, 30, 8); c.fill();
}
function card(c, x, y, w, h, r, fillStyle, stroke) { rr(c, x, y, w, h, r); c.fillStyle = fillStyle; c.fill(); if (stroke) { c.strokeStyle = stroke; c.lineWidth = 3; c.stroke(); } }
function logoMark(c, x, y, s, a = 1) {
  c.save(); c.globalAlpha = a; c.translate(x, y); c.scale(s, s);
  const g = c.createLinearGradient(-100, -100, 100, 100); g.addColorStop(0, MINT); g.addColorStop(1, VIOLET);
  rr(c, -100, -100, 200, 200, 56); c.fillStyle = g; c.fill();
  c.fillStyle = '#ffffff'; c.font = '900 170px IT9'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('S', 0, 8);
  c.textBaseline = 'alphabetic';
  c.restore();
}

function drawUI(t) {
  const c = UI.ctx, blue = t >= T.WIRE && t < T.FMT;
  uiFrame(c, blue);
  if (t < T.BOOT) { c.restore(); UI.update(); return; }                         // screen off
  if (blue) {                                                                   // blueprint: layout boxes + labels
    c.strokeStyle = '#D4FF3F'; c.lineWidth = 3; c.setLineDash([14, 10]);
    const boxes = [[60, 160, 780, 120, 'header'], [60, 320, 780, 420, 'balance_card'], [60, 780, 380, 200, 'goal[0]'],
      [460, 780, 380, 200, 'goal[1]'], [60, 1020, 780, 520, 'chart'], [60, 1580, 780, 260, 'tx_list']];
    const k = clamp((t - T.WIRE) / 1.2);
    boxes.forEach(([x, y, w, h, n], i) => { if (k * boxes.length > i) { c.strokeRect(x, y, w, h); txt(c, n, x + 18, y + 44, '500 34px JBM', '#D4FF3F'); } });
    c.setLineDash([]); c.restore(); UI.update(); return;
  }
  statusBar(c);
  const boot = clamp((t - T.BOOT) / 0.6);
  if (t < T.DROP + 0.45) {                                                      // splash
    const k = back(boot, 2.2);
    logoMark(c, 450, 900, 1.6 * Math.max(0.01, k));
    txt(c, 'Saveo', 450, 1180, '900 120px IT9', `rgba(255,255,255,${clamp(boot * 2 - 0.6)})`, 'center');
    c.restore(); UI.update(); return;
  }
  // home
  const kin = out(prog(t, T.DROP + 0.45, 0.5));
  c.globalAlpha = kin;
  txt(c, 'Good morning,', 70, 230, '500 44px IT5', '#9aa3c0'); txt(c, 'Aisha', 70, 295, '800 64px IT8', '#ffffff');
  logoMark(c, 790, 250, 0.42);
  // balance card
  const g = c.createLinearGradient(60, 340, 840, 740); g.addColorStop(0, '#1d2a52'); g.addColorStop(1, '#3a2a7a');
  card(c, 60, 340, 780, 400, 48, g);
  txt(c, 'Saved this month', 110, 430, '500 40px IT5', '#c9cff0');
  const saved = 8480 + 4000 * out(prog(t, T.ROUND + 0.5, 1.6)) + 36000 * expo(prog(t, T.GROW + 0.3, 2.2));
  txt(c, inr(saved), 110, 560, '900 120px IT9', '#ffffff');
  card(c, 110, 610, 330, 76, 38, 'rgba(52,227,160,0.18)');
  c.fillStyle = MINT; c.beginPath(); c.arc(150, 648, 12, 0, 7); c.fill(); txt(c, 'Autopilot ON', 180, 662, '700 36px IT8', MINT);
  // goals
  const goals = [['Goa trip', 0.68, MINT], ['New laptop', 0.41, VIOLET]];
  goals.forEach(([n, p, col], i) => {
    const x = 60 + i * 400, y = 780, kk = out(prog(t, T.GOALS + 0.2 + i * 0.15, 0.9));
    card(c, x, y, 380, 200, 40, '#121833');
    txt(c, n, x + 36, y + 70, '700 40px IT8', '#ffffff'); txt(c, Math.round(p * 100 * kk) + '%', x + 344, y + 70, '700 40px IT8', col, 'right');
    card(c, x + 36, y + 120, 308, 26, 13, '#232a4a'); card(c, x + 36, y + 120, Math.max(26, 308 * p * kk), 26, 13, col);
  });
  // chart
  card(c, 60, 1020, 780, 520, 48, '#0f1530');
  txt(c, 'Savings growth', 110, 1100, '700 40px IT8', '#ffffff');
  const kc = expo(prog(t, T.GROW + 0.2, 1.8));
  const pts = [0.12, 0.18, 0.16, 0.3, 0.36, 0.48, 0.55, 0.7, 0.78, 0.93];
  c.beginPath(); pts.forEach((v, i) => { const x = 110 + i * 75, y = 1480 - v * 320 * kc; i ? c.lineTo(x, y) : c.moveTo(x, y); });
  c.strokeStyle = MINT; c.lineWidth = 8; c.lineJoin = 'round'; c.stroke();
  c.lineTo(110 + 9 * 75, 1480); c.lineTo(110, 1480); c.closePath();
  const fg = c.createLinearGradient(0, 1150, 0, 1480); fg.addColorStop(0, 'rgba(52,227,160,0.35)'); fg.addColorStop(1, 'rgba(52,227,160,0)'); c.fillStyle = fg; c.fill();
  // transactions
  const tx = [['Blue Tokai Coffee', 193, 7], ['Metro card', 46, 4], ['Groceries', 1288, 12]];
  tx.forEach(([n, a, r], i) => {
    const y = 1600 + i * 100;
    txt(c, n, 80, y + 50, '600 38px IT8', '#ffffff'); txt(c, inr(a), 650, y + 50, '600 38px IT8', '#c9cff0', 'right');
    card(c, 680, y + 8, 150, 60, 30, 'rgba(52,227,160,0.18)'); txt(c, '+' + inr(r), 755, y + 50, '700 34px IT8', MINT, 'center');
  });
  // purchase notification sliding in
  const kn = out(prog(t, T.ROUND, 0.35)) * (1 - out(prog(t, T.GOALS - 0.3, 0.3)));
  if (kn > 0) {
    const y = lerp(-260, 130, kn);
    card(c, 40, y, 820, 210, 50, 'rgba(30,34,56,0.97)', 'rgba(255,255,255,0.12)');
    logoMark(c, 120, y + 105, 0.36);
    txt(c, 'Coffee · ₹193', 190, y + 85, '700 42px IT8', '#ffffff');
    const kr = clamp((t - T.ROUND - 0.5) / 0.3);
    txt(c, kr < 1 ? 'Rounding up…' : 'Rounded to ₹200 · +₹7 saved', 190, y + 145, '600 36px IT5', kr < 1 ? '#9aa3c0' : MINT);
  }
  // final hero screen
  const kh = out(prog(t, T.HERO, 0.4));
  if (kh > 0) {
    c.globalAlpha = kh; c.fillStyle = '#070a14'; c.fillRect(0, 0, 900, 1944);
    logoMark(c, 450, 820, 1.5 * back(kh, 1.8));
    txt(c, 'Saveo', 450, 1110, '900 120px IT9', '#ffffff', 'center');
    txt(c, 'Money that saves itself.', 450, 1200, '500 46px IT5', MINT, 'center');
  }
  c.globalAlpha = 1; c.restore(); UI.update();
}

// ---------------------------------------------------------------- coins + jar
const coinGeo = new THREE.CylinderGeometry(0.2, 0.2, 0.05, 40);
const coinMat = new THREE.MeshStandardMaterial({ color: '#f2c24b', metalness: 1.0, roughness: 0.25 });
const coins = T.COIN_T.map(() => { const m = new THREE.Mesh(coinGeo, coinMat); scene.add(m); return m; });
const jar = new THREE.Group(); scene.add(jar);
const glass = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.58, 1.35, 48, 1, true), new THREE.MeshPhysicalMaterial({
  color: '#cfe8ff', metalness: 0, roughness: 0.05, transparent: true, opacity: 0.22, side: THREE.DoubleSide, clearcoat: 1 }));
jar.add(glass);
const rim = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.035, 12, 48), new THREE.MeshPhysicalMaterial({ color: '#e8f4ff', roughness: 0.05, transparent: true, opacity: 0.6 }));
rim.rotation.x = Math.PI / 2; rim.position.y = 0.675; jar.add(rim);
const base = new THREE.Mesh(new THREE.CylinderGeometry(0.58, 0.58, 0.05, 48), glass.material); base.position.y = -0.675; jar.add(base);

// ---------------------------------------------------------------- 3D bars rising out of the screen
const barGroup = new THREE.Group(); phone.add(barGroup);
const bars = [0.25, 0.35, 0.3, 0.5, 0.6, 0.78, 0.95].map((v, i) => {
  const m = new THREE.Mesh(new RoundedBoxGeometry(0.16, 0.16, 1, 2, 0.04),
    new THREE.MeshStandardMaterial({ color: i === 6 ? '#D4FF3F' : MINT, roughness: 0.35, metalness: 0.1, emissive: i === 6 ? '#D4FF3F' : MINT, emissiveIntensity: 0.06 }));
  m.userData.v = v; m.position.set(-0.72 + i * 0.24, -0.62, 0); barGroup.add(m); return m;
});

// ---------------------------------------------------------------- 3D app icon
const ic = canvasTex(512, 512); { const c = ic.ctx; logoMark(c, 256, 256, 2.4); ic.update(); }
const icon = new THREE.Group(); scene.add(icon);
icon.add(new THREE.Mesh(new RoundedBoxGeometry(1.15, 1.15, 0.22, 6, 0.28), new THREE.MeshPhysicalMaterial({ color: '#1b1f2e', metalness: 0.5, roughness: 0.3, clearcoat: 1 })));
const iconFace = new THREE.Mesh(new THREE.PlaneGeometry(1.05, 1.05), new THREE.MeshBasicMaterial({ map: ic.tex, transparent: true, toneMapped: false }));
iconFace.position.z = 0.115; icon.add(iconFace);

// ---------------------------------------------------------------- four formats
const FORMATS = [['9:16', 1.35, 2.4], ['1:1', 1.9, 1.9], ['4:5', 1.65, 2.06], ['16:9', 2.5, 1.41]];
const fcards = FORMATS.map(([label, w, h], i) => {
  const px = 600, ct = canvasTex(Math.round(px * w / Math.max(w, h)), Math.round(px * h / Math.max(w, h)));
  const c = ct.ctx, Wc = ct.cv.width, Hc = ct.cv.height;
  const g = c.createLinearGradient(0, 0, Wc, Hc); g.addColorStop(0, '#0d1226'); g.addColorStop(1, '#2b1f66'); c.fillStyle = g; c.fillRect(0, 0, Wc, Hc);
  const s = Math.min(Wc, Hc) / 600;
  const wide = Wc > Hc * 1.2;
  logoMark(c, wide ? Wc * 0.22 : Wc / 2, wide ? Hc * 0.5 : Hc * 0.34, 0.9 * s);
  c.textAlign = wide ? 'left' : 'center';
  c.fillStyle = '#ffffff'; c.font = `900 ${Math.round(64 * s)}px IT9`;
  c.fillText('Money that', wide ? Wc * 0.42 : Wc / 2, wide ? Hc * 0.45 : Hc * 0.62);
  c.fillStyle = MINT; c.fillText('saves itself.', wide ? Wc * 0.42 : Wc / 2, wide ? Hc * 0.45 + 70 * s : Hc * 0.62 + 70 * s);
  c.fillStyle = '#D4FF3F'; rr(c, 24 * s, 24 * s, 130 * s, 54 * s, 27 * s); c.fill();
  c.fillStyle = '#0E0E11'; c.font = `700 ${Math.round(32 * s)}px JBM`; c.textAlign = 'center'; c.fillText(label, 89 * s, 62 * s);
  ct.update();
  const grp = new THREE.Group(); scene.add(grp);
  grp.add(new THREE.Mesh(new RoundedBoxGeometry(w + 0.1, h + 0.1, 0.06, 3, 0.08), new THREE.MeshPhysicalMaterial({ color: '#16161c', metalness: 0.6, roughness: 0.3 })));
  const face = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: ct.tex, toneMapped: false })); face.position.z = 0.035; grp.add(face);
  return grp;
});
const FPOS = [[-1.15, 1.25], [1.2, 1.7], [1.15, -0.6], [-0.1, -2.4]];

// ---------------------------------------------------------------- per frame
window.renderFrame = t => {
  drawUI(t);
  let flash = 0;
  const vis = (o, v) => (o.visible = v);
  coins.forEach(c => vis(c, false)); vis(jar, false); vis(icon, false); vis(barGroup, false); fcards.forEach(f => vis(f, false));
  vis(phone, true); vis(wire, false); vis(wireFill, false); body.visible = true; screen.visible = true;
  phone.position.set(0, 0, 0); phone.rotation.set(0, 0, 0); phone.scale.setScalar(1);
  const D = 11;

  if (t < T.DROP) {                                                         // falls in, settles, boots
    const k = expo(prog(t, 0.05, 1.2));
    phone.position.set(0, lerp(9, 0, k), 0);
    phone.rotation.set(lerp(-1.2, 0.08, k), lerp(Math.PI * 2.3, -0.35, k) + 0.08 * Math.sin(t), lerp(0.6, 0.05, k));
    camera.position.set(0.6, 0.3, D + 1.5 - 1.2 * prog(t, 0, T.DROP)); camera.lookAt(0, 0, 0);
    flash = 0.55 * Math.exp(-Math.max(0, t - T.BOOT) * 8) * (t >= T.BOOT);
  } else if (t < T.GOALS) {                                                 // meet + round-up coins
    const k = io(prog(t, T.DROP, T.GOALS - T.DROP));
    phone.position.set(lerp(0, -0.7, out(prog(t, T.ROUND, 0.5))), 0, 0);
    phone.rotation.set(0.04, lerp(-0.25, 0.22, k), 0.02);
    camera.position.set(lerp(-0.4, 0.5, k), lerp(0.3, -0.1, k), lerp(D, D - 1.2, k)); camera.lookAt(0, 0, 0);
    flash = 0.7 * Math.exp(-(t - T.DROP) * 8);
    if (t >= T.ROUND) {
      vis(jar, true);
      const kj = back(prog(t, T.ROUND + 0.1, 0.45), 1.6);
      jar.position.set(1.3, -0.85, 1.3); jar.scale.setScalar(Math.max(0.01, kj)); jar.rotation.y = t * 0.3;
      T.COIN_T.forEach((ct, i) => {
        if (t < ct) return;
        const c = coins[i]; vis(c, true);
        const dt = t - ct, fly = 0.55;
        const sx = -0.7 + 0.1 * Math.sin(i), sy = 0.2, sz = 0.3;                 // out of the phone's screen
        const ex = 1.3 + 0.18 * Math.sin(i * 2.1), ey = -1.35 + 0.045 * i, ez = 1.3 + 0.12 * Math.cos(i * 1.7);
        if (dt < fly) { const k2 = dt / fly;
          c.position.set(lerp(sx, ex, k2), lerp(sy, ey, k2) + 1.6 * Math.sin(Math.PI * k2), lerp(sz, ez, k2) + 0.8 * Math.sin(Math.PI * k2));
          c.rotation.set(dt * 14, dt * 9, dt * 5);
        } else { c.position.set(ex, ey, ez); c.rotation.set(0.15 * Math.sin(i), 0, 0.15 * Math.cos(i)); }
      });
    }
  } else if (t < T.GROW) {                                                  // goals: close tilt
    const k = io(prog(t, T.GOALS, T.GROW - T.GOALS));
    phone.rotation.set(lerp(-0.35, -0.15, k), lerp(0.55, 0.3, k), 0.08);
    camera.position.set(0, lerp(0.8, 0.2, k), lerp(8.2, 7.4, k)); camera.lookAt(0, 0.3, 0);
    flash = 0.35 * Math.exp(-(t - T.GOALS) * 10);
  } else if (t < T.HERO) {                                                  // chart: bars rise out of the screen
    const k = io(prog(t, T.GROW, T.HERO - T.GROW));
    vis(barGroup, true);
    bars.forEach((b, i) => { const kb = expo(prog(t, T.GROW + 0.35 + i * 0.12, 0.7)); const h = Math.max(0.01, b.userData.v * 1.3 * kb);
      b.scale.set(1, 1, h); b.position.z = 0.13 + h / 2; });
    phone.rotation.set(lerp(-0.42, -0.3, k), lerp(-0.62, -0.42, k), 0.06);
    camera.position.set(lerp(0.4, 0, k), lerp(-0.4, -0.2, k), lerp(9.5, 8.6, k)); camera.lookAt(0, -0.3, 0);
    flash = 0.35 * Math.exp(-(t - T.GROW) * 10);
  } else if (t < T.WIRE) {                                                  // hero: app icon floats out
    const k = io(prog(t, T.HERO, T.WIRE - T.HERO));
    phone.rotation.set(0.05, lerp(-0.2, 0.25, k), 0);
    vis(icon, true);
    const ki = back(prog(t, T.HERO + 0.35, 0.7), 1.4);
    icon.position.set(lerp(0, 1.25, ki), lerp(0, 1.9, ki), lerp(0.2, 2.2, ki)); icon.rotation.set(-0.1, lerp(-Math.PI, -0.35, expo(prog(t, T.HERO + 0.35, 1.0))), 0.12);
    camera.position.set(lerp(-0.6, 0.3, k), 0.2, lerp(D + 0.5, D - 0.6, k)); camera.lookAt(0.2, 0.3, 0);
    flash = 0.4 * Math.exp(-(t - T.HERO) * 10);
  } else if (t < T.FMT) {                                                   // wireframe reveal
    const k = io(prog(t, T.WIRE, T.FMT - T.WIRE));
    const kw = clamp((t - T.WIRE) / 0.5);
    body.visible = kw < 1; vis(wire, true); vis(wireFill, true); wireMat.opacity = kw; wireFill.material.opacity = 0.18 * kw;
    bodyMat.opacity = 1 - kw; bodyMat.transparent = true;
    phone.position.set(0, 1.4, 0); phone.rotation.set(0.25 * Math.sin(t * 0.8), lerp(-0.6, 0.9, k), 0.1);
    camera.position.set(0, 1.0, lerp(12.5, 11.0, k)); camera.lookAt(0, 1.1, 0);
    flash = 0.5 * Math.exp(-(t - T.WIRE) * 10);
  } else {                                                                  // formats
    bodyMat.opacity = 1; bodyMat.transparent = false;
    vis(phone, false);
    fcards.forEach((f, i) => {
      vis(f, true);
      const kf = back(prog(t, T.FMT + 0.1 + i * 0.13, 0.55), 1.5);
      f.position.set(FPOS[i][0], FPOS[i][1] + lerp(-6, 0, expo(prog(t, T.FMT + 0.1 + i * 0.13, 0.6))), lerp(-4, 0, kf));
      f.rotation.set(0.08 * Math.sin(t + i), 0.12 * Math.sin(t * 0.8 + i * 2), 0.03 * Math.sin(t * 1.1 + i));
      f.scale.setScalar(Math.max(0.01, kf));
    });
    const k = io(prog(t, T.FMT, T.END - T.FMT));
    camera.position.set(lerp(0.5, -0.25, k), 0.1, lerp(14.4, 13.4, k)); camera.lookAt(0, -0.2, 0);
    flash = 0.6 * Math.exp(-(t - T.FMT) * 8);
  }
  back_.position.set(camera.position.x * 0.5, camera.position.y * 0.5, -8);
  S.film.uniforms.uFlash.value = flash;
  S.film.uniforms.uFade.value = clamp(1 - t / 0.2);
  S.render(t);
};
resolveReady();
