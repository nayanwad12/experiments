// ideabro studio · Vibe Editing System, glassmorphism Reel (1080x1920).
// Every frame is a pure function of t: window.renderFrame(t) sets the DOM, render3d.mjs screenshots it.
// Cue times come from work/timeline.json (narration word timings + music grid), written by build.py prep.
'use strict';
const W = 1080, H = 1920;
let TL;

// ---------------------------------------------------------------- helpers
const cl = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const P = (t, a, d) => cl((t - a) / d);
const lerp = (a, b, k) => a + (b - a) * k;
const eo = x => 1 - Math.pow(1 - x, 3);
const eo5 = x => 1 - Math.pow(1 - x, 5);
const ex = x => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
const ei = x => x * x * x;
const eio = x => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const back = (x, s = 1.7) => (x <= 0 ? 0 : 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2));
const L0 = id => TL.lines[id][0], L1 = id => TL.lines[id][1];
const wt = (id, i) => TL.words[id][i][1], we = (id, i) => TL.words[id][i][2];

function el(parent, cls, html, css) {
  const e = document.createElement('div');
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  if (css) e.style.cssText = css;
  parent.appendChild(e);
  return e;
}
function op(e, o) {
  o = cl(o);
  e.style.opacity = o.toFixed(3);
  e.style.visibility = o < 0.003 ? 'hidden' : 'visible';
}
const tf = (e, s) => { e.style.transform = s; };
function blur(e, px) { e.style.filter = px > 0.25 ? `blur(${px.toFixed(1)}px)` : 'none'; }
function sheen(e) { return el(e, 'sheen'); }
function sweep(sh, k) { tf(sh, `translateX(${lerp(-160, 330, k)}%) skewX(-18deg)`); op(sh, k > 0 && k < 1 ? 1 : 0); }

// words that rise out of a blur as they are spoken. parts: [[text, time, cls]]
function words(parent, parts, css = '') {
  const box = el(parent, 'L', '', css);
  const spans = parts.map(([txt, t, cls], i) => {
    const s = document.createElement('span');
    s.className = 'w ' + (cls || '');
    s.textContent = txt + (i < parts.length - 1 && !(parts[i + 1][3]) ? ' ' : '');
    box.appendChild(s);
    return [s, t];
  });
  box.update = (t, dy = 0.42) => {
    for (const [s, t0] of spans) {
      const k = eo5(P(t, t0 - 0.1, 0.46));
      op(s, k);
      tf(s, `translateY(${((1 - k) * dy).toFixed(3)}em)`);
      blur(s, (1 - k) * 16);
    }
  };
  return box;
}

const SVG = (w, h, inner, css = '') => `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="${css}" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;

// ---------------------------------------------------------------- background
const bg = document.getElementById('bg').getContext('2d');
const ORBS = [
  { x: 230, y: 430, r: 640, c: [124, 92, 255], ax: 150, ay: 130, fx: .21, fy: .17, p: 0, a: .95 },
  { x: 880, y: 760, r: 600, c: [47, 110, 255], ax: 170, ay: 190, fx: .18, fy: .23, p: 1.3, a: .9 },
  { x: 260, y: 1280, r: 660, c: [255, 70, 200], ax: 190, ay: 150, fx: .15, fy: .2, p: 2.1, a: .75 },
  { x: 850, y: 1560, r: 600, c: [40, 215, 255], ax: 150, ay: 170, fx: .24, fy: .14, p: 3.3, a: .85 },
  { x: 560, y: 980, r: 420, c: [255, 150, 110], ax: 240, ay: 320, fx: .11, fy: .13, p: 4.0, a: .32 },
];
let dots;
function mkDots() {
  dots = document.createElement('canvas');
  dots.width = W; dots.height = H + 60;
  const d = dots.getContext('2d');
  d.fillStyle = 'rgba(255,255,255,.07)';
  for (let y = 0; y < H + 60; y += 60) for (let x = 30; x < W; x += 60) { d.beginPath(); d.arc(x, y, 1.6, 0, 7); d.fill(); }
}
function kick(t) {
  let v = 0;
  for (const k of TL.kicks) { if (k > t) break; if (t - k < 0.6) v = Math.max(v, Math.exp(-(t - k) / 0.14)); }
  return v;
}
function drawBg(t) {
  const g = bg.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#06061a'); g.addColorStop(.5, '#05040f'); g.addColorStop(1, '#070514');
  bg.globalCompositeOperation = 'source-over';
  bg.fillStyle = g; bg.fillRect(0, 0, W, H);
  const intro = eo(P(t, 0, 1.1));
  const kk = kick(t) * 0.16;
  const brand = eio(P(t, 30.4, 1.2));
  bg.globalCompositeOperation = 'lighter';
  ORBS.forEach((o, i) => {
    let x = o.x + Math.sin(t * o.fx * 2 + o.p) * o.ax, y = o.y + Math.cos(t * o.fy * 2 + o.p * 1.7) * o.ay;
    // the brand card pulls the light in toward the logo
    x = lerp(x, 540 + (i - 2) * 120, brand * 0.55); y = lerp(y, 900 + (i % 2 ? 260 : -200), brand * 0.55);
    const r = o.r * (1 + 0.05 * Math.sin(t * 0.9 + i));
    const a = o.a * intro * (0.62 + kk) * (i === 4 ? 1 : 1);
    const rg = bg.createRadialGradient(x, y, 0, x, y, r);
    rg.addColorStop(0, `rgba(${o.c},${a})`);
    rg.addColorStop(.45, `rgba(${o.c},${a * 0.35})`);
    rg.addColorStop(1, `rgba(${o.c},0)`);
    bg.fillStyle = rg; bg.fillRect(x - r, y - r, 2 * r, 2 * r);
  });
  bg.globalCompositeOperation = 'source-over';
  // fine dot grid, drifting up
  bg.globalAlpha = 0.9 * intro;
  bg.drawImage(dots, 0, -((t * 14) % 60));
  bg.globalAlpha = 1;
  // slow light streaks
  bg.save(); bg.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 3; i++) {
    const p = ((t * 0.045 + i / 3) % 1);
    const x = lerp(-600, W + 600, p);
    bg.translate(x, H / 2); bg.rotate(-0.42);
    const sg = bg.createLinearGradient(-60, 0, 60, 0);
    sg.addColorStop(0, 'rgba(255,255,255,0)'); sg.addColorStop(.5, `rgba(200,210,255,${0.05 * intro})`); sg.addColorStop(1, 'rgba(255,255,255,0)');
    bg.fillStyle = sg; bg.fillRect(-60, -1400, 120, 2800);
    bg.setTransform(1, 0, 0, 1, 0, 0);
  }
  bg.restore();
}

// grain: a few precomputed noise frames
const grainCv = document.getElementById('grain'), gctx = grainCv.getContext('2d');
let grains = [];
function mkGrain() {
  for (let k = 0; k < 6; k++) {
    const im = gctx.createImageData(540, 960);
    let s = 1234567 + k * 7919;
    for (let i = 0; i < im.data.length; i += 4) {
      s = (s * 1103515245 + 12345) & 0x7fffffff;
      const v = 128 + ((s >> 8) % 120) - 60;
      im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255;
    }
    grains.push(im);
  }
}

// ---------------------------------------------------------------- build
const world = document.getElementById('world'), stage = document.getElementById('stage');
const shapesBox = document.getElementById('shapes'), chromeBox = document.getElementById('chrome');
const leak = document.getElementById('leak');
const S = {};   // scene parts

function buildShapes() {
  const defs = [
    { x: 800, y: 300, w: 250, h: 250, r: '50%', f: .33, p: 0, ax: 22, ay: 34 },
    { x: 40, y: 1500, w: 210, h: 210, r: '60px', f: .27, p: 1.7, rot: 18, ax: 18, ay: 30 },
    { x: -70, y: 640, w: 190, h: 190, r: '50%', f: .22, p: 3.0, ax: 14, ay: 40 },
    { x: 840, y: 1330, w: 280, h: 124, r: '62px', f: .29, p: 2.4, rot: -24, ax: 20, ay: 26 },
    { x: 330, y: 1690, w: 330, h: 330, r: '50%', f: .2, p: 4.2, ring: true, ax: 30, ay: 20 },
  ];
  S.shapes = defs.map(d => {
    const e = el(shapesBox, 'glass soft', '', `left:0;top:0;width:${d.w}px;height:${d.h}px;border-radius:${d.r}`);
    if (d.ring) e.style.cssText += ';-webkit-mask:radial-gradient(circle,transparent 52%,#000 53%);mask:radial-gradient(circle,transparent 52%,#000 53%)';
    return [e, d];
  });
}

function buildChrome() {
  const rec = el(chromeBox, 'glass soft pill', '', 'left:56px;top:150px;height:68px;padding:0 30px;border-radius:34px');
  rec.innerHTML = `<div class="row" style="height:68px;gap:16px">
    <div id="recdot" style="width:16px;height:16px;border-radius:50%;background:#ff4d6d;box-shadow:0 0 18px #ff4d6d"></div>
    <div class="mono" style="font-size:24px;letter-spacing:.14em">REC</div>
    <div style="width:1px;height:28px;background:rgba(255,255,255,.3)"></div>
    <div id="tc" class="mono" style="font-size:24px;letter-spacing:.06em;opacity:.9">00:00:00:00</div></div>`;
  const tag = el(chromeBox, 'glass soft pill', '', 'right:56px;top:150px;height:68px;padding:0 28px 0 18px;border-radius:34px');
  tag.innerHTML = `<div class="row" style="height:68px;gap:12px">${bulb(38, 3.2)}
    <div style="font-size:27px;font-weight:700;letter-spacing:-.01em">ideabro<span class="serif gt" style="font-size:30px;margin-left:6px">studio</span></div></div>`;
  S.chrome = { rec, tag, dot: rec.querySelector('#recdot'), tc: rec.querySelector('#tc') };
}

function bulb(size, sw = 6, glow = false) {
  return SVG(size, size, `<g transform="scale(${size / 100})" fill="none" stroke="url(#gg)" stroke-width="${sw * 100 / size}" stroke-linecap="round" stroke-linejoin="round">
    <path d="M50 10c-17 0-30 13-30 29 0 11 6 19 12 25 3 3 5 7 5 11v4h26v-4c0-4 2-8 5-11 6-6 12-14 12-25 0-16-13-29-30-29z"/>
    <path d="M38 88h24M42 96h16"/></g><path transform="scale(${size / 100})" d="M50 24c1.4 9.5 7.5 15.6 17 17-9.5 1.4-15.6 7.5-17 17-1.4-9.5-7.5-15.6-17-17 9.5-1.4 15.6-7.5 17-17z" fill="${glow ? '#fff' : 'url(#gg)'}"/>`);
}

// -------- scene 1: hook card
function buildHook() {
  const c = el(stage, 'glass', '', 'left:80px;top:430px;width:920px;height:1030px;border-radius:64px');
  const corners = [[0, 0, 'border-left', 'border-top'], [1, 0, 'border-right', 'border-top'], [0, 1, 'border-left', 'border-bottom'], [1, 1, 'border-right', 'border-bottom']]
    .map(([x, y, a, b]) => el(c, 'L', '', `${x ? 'right' : 'left'}:44px;${y ? 'bottom' : 'top'}:44px;width:58px;height:58px;${a}:3px solid rgba(255,255,255,.75);${b}:3px solid rgba(255,255,255,.75);border-radius:${x ? (y ? '0 0 18px 0' : '0 18px 0 0') : (y ? '0 0 0 18px' : '18px 0 0 0')}`));
  el(c, 'L mono', 'SCENE 01 &nbsp;·&nbsp; HOOK', 'left:128px;top:62px;font-size:22px;letter-spacing:.2em;opacity:.6');
  el(c, 'L mono', '4K &nbsp;·&nbsp; 9:16', 'right:128px;top:62px;font-size:22px;letter-spacing:.2em;opacity:.6');
  const hw = i => wt('hook', i);
  const b1 = el(c, 'L', '', 'left:0;top:290px;width:920px;text-align:center');
  const l1 = words(b1, [['The', hw(0)], ['video', hw(1)]], 'position:relative;font-size:104px;line-height:1.12');
  l1.className = 'b'; l1.style.position = 'relative';
  const l2 = words(b1, [["you're", hw(2)], ['watching', hw(3)]], 'position:relative;font-size:104px;line-height:1.12');
  l2.className = 'b'; l2.style.position = 'relative';
  const l3 = words(b1, [['right', hw(4), 'serif gt'], ['now', hw(5), 'serif gt']], 'position:relative;font-size:168px;line-height:1.1;margin-top:6px');
  l3.style.position = 'relative';
  const h2 = i => wt('hook2', i);
  const b2 = el(c, 'L', '', 'left:0;top:300px;width:920px;text-align:center');
  const m1 = words(b2, [['was', h2(0)], ['edited', h2(1)]], 'position:relative;font-size:100px;line-height:1.12');
  m1.className = 'b'; m1.style.position = 'relative';
  const m2 = words(b2, [['entirely', h2(2)], ['by', h2(3)]], 'position:relative;font-size:100px;line-height:1.12');
  m2.className = 'b'; m2.style.position = 'relative';
  m1.style.opacity = m2.style.opacity = 1;
  const badge = el(c, 'L pill', '', `left:60px;top:650px;width:800px;height:150px;border-radius:75px;
    background:linear-gradient(120deg,rgba(124,92,255,.38),rgba(61,123,255,.22) 50%,rgba(47,216,255,.28));
    box-shadow:0 0 0 1.5px rgba(255,255,255,.45) inset,0 20px 60px rgba(90,80,255,.45);overflow:hidden`);
  badge.innerHTML = `<div class="row" style="height:150px;justify-content:center;gap:22px">
    ${SVG(56, 56, '<path d="M28 2c2 14 12 24 26 26-14 2-24 12-26 26-2-14-12-24-26-26 14-2 24-12 26-26z" fill="url(#gg)"/>')}
    <div class="b" style="font-size:62px;letter-spacing:-.025em">Vibe Editing <span class="serif gt" style="font-size:72px">System</span></div></div>`;
  const bsh = sheen(badge);
  const foot = el(c, 'L', '', 'left:70px;right:70px;bottom:64px;height:60px');
  foot.innerHTML = `<div style="position:absolute;left:0;right:0;top:0;height:3px;border-radius:2px;background:rgba(255,255,255,.14)"></div>
    <div id="hbar" style="position:absolute;left:0;top:0;height:3px;border-radius:2px;background:var(--grad2);box-shadow:0 0 14px #5a7bff"></div>
    <div id="hfr" class="mono" style="position:absolute;left:0;top:24px;font-size:22px;letter-spacing:.14em;opacity:.7">FRAME 0000</div>
    <div class="mono" style="position:absolute;right:0;top:24px;font-size:22px;letter-spacing:.14em;opacity:.7">LIVE RENDER</div>`;
  const csh = sheen(c);
  S.hook = { c, corners, b1, l1, l2, l3, b2, m1, m2, badge, bsh, csh, bar: foot.querySelector('#hbar'), fr: foot.querySelector('#hfr') };
}

// -------- scene 2: "No timeline. No keyframes. No After Effects."
const ICONS = [
  SVG(110, 110, `<g fill="none" stroke="url(#gg)" stroke-width="6" stroke-linecap="round"><path d="M14 30h56M30 55h66M14 80h44"/><path d="M78 16v80" stroke="#fff" stroke-width="4"/></g>`),
  SVG(110, 110, `<g fill="url(#gg)"><path d="M22 55l12-12 12 12-12 12z"/><path d="M55 55l12-12 12 12-12 12z" opacity=".75"/><path d="M88 55l10-10 10 10-10 10z" opacity=".5"/></g><path d="M6 55h100" stroke="rgba(255,255,255,.35)" stroke-width="3"/>`),
  SVG(110, 110, `<g fill="none" stroke="url(#gg)" stroke-width="6" stroke-linejoin="round"><rect x="14" y="14" width="56" height="56" rx="14"/><rect x="28" y="28" width="56" height="56" rx="14" opacity=".7"/><rect x="42" y="42" width="56" height="56" rx="14" opacity=".45"/></g>`),
];
function buildNo() {
  const lab = el(stage, 'L mono center', "YOU DON'T NEED", 'top:470px;font-size:28px;letter-spacing:.42em;opacity:0');
  const ws = TL.words.no, nos = [0, 2, 4], ends = [1, 3, 6];
  const names = ['timeline.', 'keyframes.', 'After Effects.'];
  const tiles = names.map((n, i) => {
    const g = el(stage, 'glass', '', `left:110px;top:${590 + i * 270}px;width:860px;height:228px;border-radius:46px`);
    const ic = el(g, 'L', ICONS[i], 'left:38px;top:39px;width:150px;height:150px;border-radius:40px;background:rgba(255,255,255,.07);box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.22);display:flex;align-items:center;justify-content:center');
    const x = el(g, 'L', SVG(150, 150, `<g stroke="#FF6B9A" stroke-width="7" stroke-linecap="round" fill="none"><path class="x1" d="M34 34L116 116" stroke-dasharray="116" stroke-dashoffset="116"/><path class="x2" d="M116 34L34 116" stroke-dasharray="116" stroke-dashoffset="116"/></g>`), 'left:38px;top:39px;width:150px;height:150px;filter:drop-shadow(0 0 10px #ff4d8a)');
    el(g, 'L b', `<span><span class="gt">No</span> ${n}</span>`, 'left:226px;top:0;height:228px;display:flex;align-items:center;font-size:78px;white-space:pre');
    return { g, ic, x1: x.querySelector('.x1'), x2: x.querySelector('.x2'), sh: sheen(g), tin: ws[nos[i]][1], tx: ws[ends[i]][2] };
  });
  S.no = { lab, tiles };
}

// -------- scene 3: "One workflow. Any motion video." + orbiting tiles
const GLYPHS = [
  `<div class="b gt" style="font-size:92px">Aa</div>`,
  SVG(96, 96, `<path d="M30 18l50 30-50 30z" fill="url(#gg)"/>`),
  SVG(96, 96, `<path d="M48 8l40 40-40 40-40-40z" fill="none" stroke="url(#gg)" stroke-width="7"/>`),
  SVG(96, 96, `<g fill="url(#gg)"><rect x="10" y="52" width="16" height="34" rx="5"/><rect x="40" y="30" width="16" height="56" rx="5"/><rect x="70" y="12" width="16" height="74" rx="5"/></g>`),
  SVG(96, 96, `<g fill="none" stroke="url(#gg)" stroke-width="6" stroke-linejoin="round"><path d="M48 8l36 20v40L48 88 12 68V28z"/><path d="M12 28l36 20 36-20M48 48v40"/></g>`),
  SVG(96, 96, `<g fill="url(#gg)"><circle cx="26" cy="72" r="13"/><circle cx="72" cy="62" r="13"/><path d="M33 72V20l46-10v52h-7V20L40 27v45z"/></g>`),
  SVG(96, 96, `<path d="M48 4c3 22 18 37 40 40-22 3-37 18-40 40-3-22-18-37-40-40 22-3 37-18 40-40z" fill="url(#gg)"/>`),
  SVG(96, 96, `<g fill="none" stroke="url(#gg)" stroke-width="7"><circle cx="48" cy="48" r="36"/></g><circle cx="48" cy="48" r="12" fill="#fff"/>`),
];
function buildAny() {
  const a = i => wt('any', i);
  const h1 = words(stage, [['One', a(0)], ['workflow.', a(1)]], 'left:0;width:1080px;text-align:center;top:330px;font-size:116px');
  h1.classList.add('b', 'shadow');
  const h2 = words(stage, [['Any', a(4), 'serif gt']], 'left:0;width:1080px;text-align:center;top:420px;font-size:310px;line-height:1.1');
  h2.classList.add('shadow');
  const h3 = words(stage, [['motion', a(7)], ['video.', a(8)]], 'left:0;width:1080px;text-align:center;top:770px;font-size:116px');
  h3.classList.add('b', 'shadow');
  const tiles = GLYPHS.map(gl => {
    const g = el(stage, 'glass', '', 'left:0;top:0;width:210px;height:210px;border-radius:52px');
    el(g, 'ink row', gl, 'justify-content:center');
    return g;
  });
  S.any = { h1, h2, h3, tiles };
}

// -------- scene 4: coverflow of formats
const CATS = [['Kinetic', 'type'], ['Product', 'ads'], ['3D', 'worlds'], ['Explainer', 'videos'], ['Logo', 'reveals']];
function buildList() {
  const head = el(stage, 'L', '', 'left:0;top:300px;width:1080px;height:200px');
  const counter = el(head, 'L mono center', '', 'top:0;font-size:26px;letter-spacing:.3em;opacity:.75');
  const clip = el(head, 'L', '', 'left:0;top:44px;width:1080px;height:160px;overflow:hidden');
  const titles = CATS.map(([a, b]) => el(clip, 'L center b', `${a} <span class="serif gt" style="font-size:132px;letter-spacing:0">${b}</span>`, 'top:4px;font-size:116px;line-height:150px'));
  const cards = CATS.map((_, i) => {
    const g = el(stage, 'glass', '', 'left:220px;top:560px;width:640px;height:860px;border-radius:60px');
    const pv = el(g, 'L', '', 'left:28px;top:28px;width:584px;height:700px;border-radius:40px;overflow:hidden;background:radial-gradient(ellipse at 50% 30%,rgba(255,255,255,.1),rgba(0,0,0,.18))');
    el(g, 'L mono', `${String(i + 1).padStart(2, '0')} &nbsp;·&nbsp; ${CATS[i].join(' ').toUpperCase()}`, 'left:50px;bottom:48px;font-size:22px;letter-spacing:.18em;opacity:.75');
    el(g, 'L mono', '▶ PLAY', 'right:50px;bottom:48px;font-size:22px;letter-spacing:.18em;opacity:.75');
    return { g, pv, sh: sheen(g) };
  });
  // previews
  const k = cards[0].pv;
  S.kin = ['MAKE', 'IT', 'MOVE.'].map((w, i) => el(k, 'L center', w, `left:0;width:584px;top:${90 + i * 180}px;font-size:${i === 1 ? 200 : 150}px;line-height:1;font-weight:900;letter-spacing:-.05em;${i === 1 ? '' : ''}`));
  S.kin[1].className = 'L center serif gt'; S.kin[1].style.fontWeight = 400;
  S.kinBar = el(k, 'L', '', 'left:92px;top:640px;height:8px;border-radius:4px;background:var(--grad2);box-shadow:0 0 18px #4c7cff');
  const p = cards[1].pv;
  S.spot = el(p, 'L', '', 'left:-200px;top:-200px;width:984px;height:1100px;background:conic-gradient(from 0deg at 50% 45%,rgba(124,92,255,.0),rgba(124,92,255,.35),rgba(47,216,255,.0) 30%,rgba(255,120,220,.3) 55%,rgba(124,92,255,0) 75%)');
  el(p, 'L', '', 'left:142px;top:560px;width:300px;height:60px;border-radius:50%;background:radial-gradient(rgba(150,170,255,.55),rgba(0,0,0,0) 70%);filter:blur(6px)');
  const bottle = el(p, 'L', '', 'left:197px;top:170px;width:190px;height:400px');
  el(bottle, 'L', '', 'left:40px;top:0;width:110px;height:80px;border-radius:24px 24px 10px 10px;background:linear-gradient(90deg,#141226,#4b4670 35%,#9a95c0 48%,#2a2744 70%,#0f0d1d)');
  S.body = el(bottle, 'L', '', 'left:0;top:70px;width:190px;height:330px;border-radius:60px;background:linear-gradient(90deg,#1f1640,#6d55ff 22%,#d9d2ff 44%,#8b7bff 58%,#3a2bb0 80%,#160f33);box-shadow:0 30px 60px rgba(0,0,0,.5)');
  el(S.body, 'L center', '<div class="b" style="font-size:44px;letter-spacing:.12em;width:190px">VIBE</div><div class="mono" style="font-size:16px;letter-spacing:.3em;opacity:.8;width:190px">NO.09</div>', 'left:0;width:190px;top:120px;color:#fff;mix-blend-mode:overlay');
  S.bodyHi = el(S.body, 'L', '', 'top:0;left:0;width:60px;height:330px;background:linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,.55),rgba(255,255,255,0));border-radius:30px');
  el(p, 'L pill', '<span class="mono" style="font-size:20px;letter-spacing:.2em">NEW DROP</span>', 'left:34px;top:34px;padding:12px 22px;border-radius:30px;background:rgba(255,255,255,.12);box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.35)');
  el(p, 'L b gt', '$49', 'right:40px;bottom:30px;font-size:84px');
  const d3 = cards[2].pv;
  el(d3, 'L', '', 'left:92px;top:470px;width:400px;height:90px;border-radius:50%;background:radial-gradient(rgba(124,92,255,.5),rgba(0,0,0,0) 70%);filter:blur(10px)');
  const cw = el(d3, 'L', '', 'left:0;top:0;width:584px;height:700px;perspective:1100px');
  S.cube = el(cw, 'L', '', 'left:162px;top:180px;width:260px;height:260px;transform-style:preserve-3d');
  const faces = ['rotateY(0deg)', 'rotateY(90deg)', 'rotateY(180deg)', 'rotateY(-90deg)', 'rotateX(90deg)', 'rotateX(-90deg)'];
  faces.forEach((f, i) => el(S.cube, 'L', '', `left:0;top:0;width:260px;height:260px;border-radius:30px;transform:${f} translateZ(130px);
    background:linear-gradient(${40 + i * 50}deg,rgba(124,92,255,.55),rgba(47,216,255,.25) 60%,rgba(255,150,230,.35));box-shadow:inset 0 0 0 2px rgba(255,255,255,.6),inset 0 0 40px rgba(255,255,255,.18)`));
  S.orbit = el(d3, 'L', '', 'left:42px;top:200px;width:500px;height:220px;border-radius:50%;border:2px solid rgba(255,255,255,.35)');
  S.orbDot = el(d3, 'L', '', 'left:0;top:0;width:22px;height:22px;border-radius:50%;background:#fff;box-shadow:0 0 20px #8fb4ff,0 0 40px #7c5cff');
  const ex_ = cards[3].pv;
  el(ex_, 'L b gt', '+248%', 'left:44px;top:40px;font-size:96px');
  el(ex_, 'L mono', 'GROWTH · Q1–Q4', 'left:48px;top:156px;font-size:20px;letter-spacing:.2em;opacity:.7');
  el(ex_, 'L', '', 'left:44px;top:610px;width:496px;height:2px;background:rgba(255,255,255,.3)');
  S.bars = [.3, .46, .4, .66, .9].map((h, i) => el(ex_, 'L', '', `left:${66 + i * 96}px;bottom:90px;width:64px;height:${h * 360}px;border-radius:16px 16px 6px 6px;transform-origin:bottom;
    background:linear-gradient(180deg,${i === 4 ? '#86F0FF' : 'rgba(210,196,255,.9)'},rgba(124,92,255,.35));box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.4)`));
  S.bars.h = [.3, .46, .4, .66, .9];
  ex_.insertAdjacentHTML('beforeend', SVG(584, 700, `<path id="xl" d="M98 470 L194 410 L290 430 L386 330 L482 230" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="520" stroke-dashoffset="520"/><circle id="xd" cx="482" cy="230" r="13" fill="#fff"/>`, 'position:absolute;left:0;top:0'));
  S.xl = ex_.querySelector('#xl'); S.xd = ex_.querySelector('#xd');
  const lg = cards[4].pv;
  lg.insertAdjacentHTML('beforeend', SVG(584, 700, `<circle id="lr" cx="292" cy="330" r="170" fill="none" stroke="url(#gg)" stroke-width="10" stroke-linecap="round" stroke-dasharray="1068" stroke-dashoffset="1068" transform="rotate(-90 292 330)"/>
    <circle id="lr2" cx="292" cy="330" r="200" fill="none" stroke="rgba(255,255,255,.3)" stroke-width="2" stroke-dasharray="6 14"/>`, 'position:absolute;left:0;top:0'));
  S.lr = lg.querySelector('#lr'); S.lr2 = lg.querySelector('#lr2');
  S.lmono = el(lg, 'L', bulb(200, 7), 'left:192px;top:230px;width:200px;height:200px');
  S.lname = el(lg, 'L center b', 'ideabro', 'left:0;width:584px;top:560px;font-size:64px');
  S.spark = [0, 1, 2, 3].map(i => el(lg, 'L', SVG(40, 40, '<path d="M20 0c1.5 10 8.5 17 20 20-11.5 3-18.5 10-20 20-1.5-10-8.5-17-20-20 11.5-3 18.5-10 20-20z" fill="#fff"/>'), `left:${[120, 430, 460, 90][i]}px;top:${[150, 140, 470, 450][i]}px`));
  S.list = { head, counter, titles, cards };
}

// -------- scene 5 + 6: process title, stepper, step panel
const STEP_TITLES = [
  [[0, 1, 2], [3, 4, 5], 'Describe the vibe', 'in one prompt.'],
  [[0, 1, 2, 3], [4, 5], 'It writes every scene', 'in code.'],
  [[0, 1, 2], [3, 4, 5], 'Adds the motion,', 'music and voice.'],
  [[0, 1, 2], [3, 4, 5], 'And renders it,', 'in every format.'],
];
const PROMPT = [['Make a premium ', ''], ['glassmorphism', 'gt'], [' reel for ', ''], ['ideabro studio', 'gt'], ['. 9:16, 35 seconds, million-dollar feel.', '']];
const CODE = [
  [['k', 'scene'], ['p', '('], ['s', '"hook"'], ['p', ', { '], ['k2', 'glass'], ['p', ': '], ['n', 'true'], ['p', ', '], ['k2', 'blur'], ['p', ': '], ['n', '34'], ['p', ' })']],
  [['p', '  .'], ['f', 'text'], ['p', '('], ['s', '"The video you\'re watching"'], ['p', ')']],
  [['p', '  .'], ['f', 'badge'], ['p', '('], ['s', '"Vibe Editing System"'], ['p', ')']],
  [['k', 'scene'], ['p', '('], ['s', '"formats"'], ['p', ', { '], ['k2', 'flow'], ['p', ': '], ['s', '"coverflow"'], ['p', ' })']],
  [['p', '  .'], ['f', 'cards'], ['p', '(['], ['s', '"type"'], ['p', ', '], ['s', '"ads"'], ['p', ', '], ['s', '"3D"'], ['p', ', …])']],
  [['k', 'scene'], ['p', '('], ['s', '"process"'], ['p', ', { '], ['k2', 'steps'], ['p', ': '], ['n', '4'], ['p', ' })']],
  [['p', '  .'], ['f', 'stepper'], ['p', '({ '], ['k2', 'glow'], ['p', ': '], ['s', '"aurora"'], ['p', ' })']],
  [['k', 'scene'], ['p', '('], ['s', '"cta"'], ['p', ')']],
  [['p', '  .'], ['f', 'button'], ['p', '('], ['s', '"Comment VIBE"'], ['p', ')']],
  [['p', '  .'], ['f', 'brand'], ['p', '('], ['s', '"ideabro studio"'], ['p', ')']],
  [['k', 'render'], ['p', '({ '], ['k2', 'ratio'], ['p', ': '], ['s', '"9:16"'], ['p', ', '], ['k2', 'fps'], ['p', ': '], ['n', '30'], ['p', ' })']],
];
const CODE_C = { k: '#C9A8FF', k2: '#9DB6FF', s: '#FFC2F1', n: '#86F0FF', p: 'rgba(255,255,255,.6)', f: '#86F0FF' };
function buildProcess() {
  const p = i => wt('proc', i);
  const h1 = words(stage, [["Here's", p(0)], ['the', p(1)]], 'left:0;width:1080px;text-align:center;top:500px;font-size:112px');
  h1.classList.add('b', 'shadow');
  const h2 = words(stage, [['process.', p(2), 'serif gt']], 'left:0;width:1080px;text-align:center;top:600px;font-size:250px;line-height:1.1');
  h2.classList.add('shadow');
  const line = el(stage, 'L', '', 'left:0;top:0;height:4px;border-radius:2px;background:rgba(255,255,255,.16)');
  const lineFill = el(stage, 'L', '', 'left:0;top:0;height:4px;border-radius:2px;background:var(--grad2);box-shadow:0 0 16px #5a7bff');
  const chips = [0, 1, 2, 3].map(i => {
    const g = el(stage, 'glass', '', 'left:0;top:0;width:170px;height:170px;border-radius:46px');
    const fill = el(g, 'ink', '', 'background:linear-gradient(135deg,rgba(124,92,255,.95),rgba(61,123,255,.85) 55%,rgba(47,216,255,.9));opacity:0');
    const n = el(g, 'ink row mono', `0${i + 1}`, 'justify-content:center;font-size:46px;letter-spacing:.04em');
    return { g, fill, n };
  });
  S.proc = { h1, h2, chips, line, lineFill };

  // step titles
  const titles = STEP_TITLES.map(([ia, ib, a, b], si) => {
    const id = 's' + (si + 1);
    const box = el(stage, 'L', '', 'left:0;top:440px;width:1080px;height:260px');
    const lab = el(box, 'L mono center gt', `STEP 0${si + 1}`, 'top:0;font-size:26px;letter-spacing:.4em');
    const aw = a.split(' '), bw = b.split(' ');
    const A = words(box, aw.map((w, j) => [w, wt(id, ia[j])]), 'left:0;width:1080px;text-align:center;top:44px;font-size:78px');
    A.classList.add('b', 'shadow');
    const B = words(box, bw.map((w, j) => [w, wt(id, ib[j]), 'serif gt']), 'left:0;width:1080px;text-align:center;top:126px;font-size:108px');
    return { box, lab, A, B, id };
  });
  // panel
  const panel = el(stage, 'glass', '', 'left:80px;top:720px;width:920px;height:780px;border-radius:60px');
  const psh = sheen(panel);
  const pages = [0, 1, 2, 3].map(() => el(panel, 'ink'));
  // page 1: prompt
  const p1 = pages[0];
  el(p1, 'L row', '<div style="width:16px;height:16px;border-radius:50%;background:rgba(255,255,255,.35)"></div><div style="width:16px;height:16px;border-radius:50%;background:rgba(255,255,255,.25);margin-left:10px"></div><div style="width:16px;height:16px;border-radius:50%;background:rgba(255,255,255,.18);margin-left:10px"></div><div class="mono" style="font-size:22px;letter-spacing:.12em;opacity:.6;margin-left:24px">VIBE EDITING SYSTEM — NEW PROJECT</div>', 'left:48px;top:44px');
  const box = el(p1, 'L', '', 'left:40px;top:104px;width:840px;height:400px;border-radius:36px;background:rgba(5,5,20,.22);box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.16)');
  el(box, 'L mono', '✦ PROMPT', 'left:36px;top:30px;font-size:20px;letter-spacing:.24em;opacity:.55');
  const typed = el(box, 'L', '', 'left:36px;top:76px;width:768px;font-size:50px;font-weight:500;line-height:1.3;letter-spacing:-.01em');
  const chipsRow = el(p1, 'L row', '', 'left:40px;top:536px;gap:14px');
  const tags = ['9:16', '35s', 'Glassmorphism', 'Premium'].map(s => el(chipsRow, 'pill', s, 'position:relative;padding:14px 26px;border-radius:30px;font-size:28px;font-weight:600;background:rgba(255,255,255,.1);box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.28)'));
  const gen = el(p1, 'L pill row', `<span style="font-size:36px;font-weight:700">Generate</span>${SVG(34, 34, '<path d="M17 1c1.2 8.6 7.4 14.8 16 16-8.6 1.2-14.8 7.4-16 16-1.2-8.6-7.4-14.8-16-16 8.6-1.2 14.8-7.4 16-16z" fill="#fff"/>')}`,
    'right:40px;top:630px;height:100px;padding:0 42px;gap:14px;border-radius:50px;background:linear-gradient(120deg,#7C5CFF,#3D7BFF 55%,#2FD8FF);box-shadow:0 18px 50px rgba(80,100,255,.55),inset 0 2px 0 rgba(255,255,255,.45)');
  const ripple = el(p1, 'L', '', 'left:0;top:0;width:10px;height:10px;border-radius:50%;border:3px solid #fff;opacity:0');
  // page 2: code
  const p2 = pages[1];
  el(p2, 'L row mono', '<span style="padding:12px 22px;border-radius:16px;background:rgba(255,255,255,.12)">scene.js</span><span style="padding:12px 22px;opacity:.45">timeline.json</span><span style="padding:12px 22px;opacity:.45">sound.py</span>', 'left:36px;top:34px;font-size:22px');
  const hl = el(p2, 'L', '', 'left:24px;width:872px;height:50px;border-radius:12px;background:rgba(255,255,255,.08)');
  const codeLines = CODE.map((ln, i) => el(p2, 'L mono', `<span style="opacity:.35;display:inline-block;width:46px">${i + 1}</span>` +
    ln.map(([c, s]) => `<span style="color:${CODE_C[c]}">${s.replace(/</g, '&lt;')}</span>`).join(''), `left:40px;top:${116 + i * 50}px;font-size:25px;line-height:50px;white-space:pre`));
  const status = el(p2, 'L row', `${SVG(34, 34, '<circle cx="17" cy="17" r="16" fill="url(#gv)"/><path d="M10 17l5 5 9-10" stroke="#fff" stroke-width="3.5" fill="none" stroke-linecap="round"/>')}<span class="mono" style="font-size:24px;letter-spacing:.08em;margin-left:14px">8 scenes written · 0 errors</span>`, 'left:40px;bottom:40px');
  // page 3: timeline
  const p3 = pages[2];
  const ruler = el(p3, 'L', '', 'left:200px;top:52px;width:680px;height:40px');
  for (let i = 0; i <= 34; i++) el(ruler, 'L', '', `left:${i * 20}px;top:${i % 5 ? 22 : 10}px;width:2px;height:${i % 5 ? 12 : 24}px;background:rgba(255,255,255,${i % 5 ? .2 : .45})`);
  for (let i = 0; i <= 6; i++) el(ruler, 'L mono', `00:${String(i * 5).padStart(2, '0')}`, `left:${i * 100 + 6}px;top:-14px;font-size:16px;opacity:.5`);
  const tracks = ['MOTION', 'MUSIC', 'VOICE'].map((n, i) => {
    const r = el(p3, 'L', '', `left:40px;top:${130 + i * 196}px;width:840px;height:168px`);
    el(r, 'L mono', `<span style="display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:12px;background:${['#C9A8FF', '#86F0FF', '#FFC2F1'][i]}"></span>${n}`, 'left:0;top:68px;font-size:20px;letter-spacing:.16em;opacity:.85');
    const lane = el(r, 'L', '', 'left:160px;top:0;width:680px;height:168px;border-radius:26px;background:rgba(255,255,255,.06);box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.12);overflow:hidden');
    const rev = el(lane, 'ink', '', 'clip-path:inset(0 100% 0 0)');
    return { r, lane, rev };
  });
  tracks[0].rev.innerHTML = SVG(680, 168, `<path d="M20 130 C120 130 140 40 240 40 S360 120 440 120 S560 30 660 34" fill="none" stroke="url(#gg)" stroke-width="6"/>
    ${[[20, 130], [240, 40], [440, 120], [660, 34]].map(([x, y]) => `<path d="M${x} ${y - 14}l14 14-14 14-14-14z" fill="#fff"/>`).join('')}`);
  let bars = '';
  for (let i = 0; i < 56; i++) { const h = 20 + 110 * Math.abs(Math.sin(i * 1.7) * Math.sin(i * 0.37 + 1)) * (i % 4 === 0 ? 1 : 0.7); bars += `<rect x="${14 + i * 12}" y="${84 - h / 2}" width="7" height="${h}" rx="3.5" fill="url(#gv)"/>`; }
  tracks[1].rev.innerHTML = SVG(680, 168, bars);
  let up = '', dn = '';
  for (let x = 10; x <= 670; x += 6) { const a = 8 + 52 * Math.abs(Math.sin(x * 0.045) * Math.sin(x * 0.011 + 2) * (0.6 + 0.4 * Math.sin(x * 0.13))); up += `${x},${84 - a} `; dn = `${x},${84 + a} ` + dn; }
  tracks[2].rev.innerHTML = SVG(680, 168, `<polygon points="${up}${dn}" fill="url(#gw)"/>`);
  const head_ = el(p3, 'L', '<div style="position:absolute;left:-11px;top:-6px;width:24px;height:24px;border-radius:7px;background:#fff;transform:rotate(45deg)"></div>', 'left:0;top:96px;width:3px;height:640px;background:linear-gradient(#fff,rgba(255,255,255,.1));box-shadow:0 0 16px #fff');
  // page 4: formats
  const p4 = pages[3];
  const F = [[180, 320, '9:16 · REELS'], [250, 250, '1:1 · FEED'], [320, 180, '16:9 · YOUTUBE']];
  let fx = 55;
  const frames = F.map(([w, h, lab]) => {
    const f = el(p4, 'L', '', `left:${fx}px;top:${470 - h}px;width:${w}px;height:${h}px;border-radius:26px;overflow:hidden;background:rgba(255,255,255,.05);box-shadow:inset 0 0 0 2px rgba(255,255,255,.45)`);
    const fill = el(f, 'L', '', `left:0;bottom:0;width:${w}px;height:0;background:linear-gradient(0deg,rgba(124,92,255,.85),rgba(47,216,255,.6) 70%,rgba(255,194,241,.6))`);
    el(f, 'ink row', bulb(Math.min(w, h) * 0.42, 5), 'justify-content:center');
    const ck = el(p4, 'L', SVG(52, 52, '<circle cx="26" cy="26" r="24" fill="url(#gv)" stroke="#fff" stroke-width="2"/><path d="M15 26l7 7 14-15" stroke="#fff" stroke-width="4.5" fill="none" stroke-linecap="round"/>'), `left:${fx + w - 34}px;top:${470 - h - 18}px`);
    el(p4, 'L mono', lab, `left:${fx}px;top:494px;width:${w}px;text-align:center;font-size:19px;letter-spacing:.12em;opacity:.75`);
    fx += w + 60;
    return { f, fill, ck, h };
  });
  el(p4, 'L', '', 'left:60px;top:620px;width:800px;height:14px;border-radius:7px;background:rgba(255,255,255,.12)');
  const pbar = el(p4, 'L', '', 'left:60px;top:620px;width:0;height:14px;border-radius:7px;background:var(--grad2);box-shadow:0 0 20px #4c7cff');
  const plab = el(p4, 'L', '', 'left:60px;top:664px;font-size:32px;font-weight:600');
  const ppct = el(p4, 'L mono', '', 'right:60px;top:668px;font-size:28px');
  S.steps = { titles, panel, psh, pages, typed, tags, gen, ripple, hl, codeLines, status, tracks, head: head_, frames, pbar, plab, ppct };
}

// -------- scene 7: CTA
function buildCta() {
  const c = i => wt('cta', i), d = i => wt('cta2', i);
  const h1 = words(stage, [['Want', c(0)], ['this', c(1)]], 'left:0;width:1080px;text-align:center;top:330px;font-size:124px');
  h1.classList.add('b', 'shadow');
  const h2 = words(stage, [['exact', c(2), 'serif gt'], ['workflow?', c(3), 'serif gt']], 'left:0;width:1080px;text-align:center;top:450px;font-size:168px;line-height:1.1');
  h2.classList.add('shadow');
  const glow = el(stage, 'L', '', 'left:150px;top:760px;width:780px;height:240px;border-radius:120px;background:linear-gradient(120deg,#7C5CFF,#3D7BFF 50%,#2FD8FF);filter:blur(60px);opacity:0');
  const btn = el(stage, 'glass pill', '', 'left:110px;top:760px;width:860px;height:240px;border-radius:120px');
  el(btn, 'ink row', '<span style="font-size:80px;font-weight:600;letter-spacing:-.02em">Comment</span><span class="gt" style="font-size:120px;font-weight:900;letter-spacing:.02em;margin-left:30px">VIBE</span>', 'justify-content:center');
  const bsh = sheen(btn);
  const sub = words(stage, [['and', d(2)], ["I'll", d(3)], ['send', d(4)], ['it', d(5)], ['to', d(6)], ['you.', d(7), 'serif gt']], 'left:0;width:1080px;text-align:center;top:1050px;font-size:72px');
  sub.style.fontWeight = 600;
  const ripple = el(stage, 'L', '', 'left:0;top:0;width:10px;height:10px;border-radius:50%;border:4px solid rgba(255,255,255,.9);opacity:0');
  const cursor = el(stage, 'L', SVG(110, 130, '<path d="M14 6l78 62-36 6 22 42-18 9-22-43-26 26z" fill="#fff" stroke="rgba(0,0,0,.35)" stroke-width="3" stroke-linejoin="round"/>'), 'left:0;top:0;filter:drop-shadow(0 14px 22px rgba(0,0,0,.5))');
  const CM = ['VIBE 🔥', 'VIBE ✨', 'vibe!!', 'VIBE 🙌', 'need this', 'VIBE 💜'];
  const AV = ['#7C5CFF,#2FD8FF', '#FF6BB5,#7C5CFF', '#2FD8FF,#3D7BFF', '#FFB36B,#FF6BB5', '#86F0FF,#7C5CFF', '#C9A8FF,#FF6BB5'];
  const bubbles = CM.map((s, i) => {
    const g = el(stage, 'glass soft pill', '', 'left:0;top:0;height:96px;padding:0 34px 0 16px;border-radius:48px');
    el(g, '', `<div class="row" style="height:96px;gap:18px"><div style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,${AV[i]})"></div><span style="font-size:40px;font-weight:600;white-space:nowrap">${s}</span></div>`);
    return g;
  });
  S.cta = { h1, h2, glow, btn, bsh, sub, ripple, cursor, bubbles };
}

// -------- scene 8: brand
function buildBrand() {
  const halo = el(stage, 'L', '', 'left:340px;top:520px;width:400px;height:400px;border-radius:50%;background:radial-gradient(rgba(140,120,255,.95),rgba(47,216,255,.45) 45%,rgba(0,0,0,0) 70%);filter:blur(30px);opacity:0');
  const logo = el(stage, 'glass', '', 'left:395px;top:575px;width:290px;height:290px;border-radius:80px');
  el(logo, 'ink row', bulb(170, 6.5, true), 'justify-content:center');
  const lsh = sheen(logo);
  const word = el(stage, 'L center', '', 'top:930px;font-size:196px;font-weight:800;letter-spacing:-.055em;line-height:1.1');
  const letters = [...'ideabro'].map(ch => {
    const s = document.createElement('span');
    s.className = 'w'; s.textContent = ch;
    s.style.cssText = 'background:linear-gradient(100deg,#fff 0%,#fff 42%,#C9B8FF 47%,#86F0FF 50%,#fff 56%,#fff 100%);background-size:420% 100%;-webkit-background-clip:text;background-clip:text;color:transparent';
    word.appendChild(s); return s;
  });
  const studio = el(stage, 'L row', '<div style="width:110px;height:2px;background:linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,.8))"></div><span style="font-size:46px;font-weight:500;letter-spacing:.62em;margin:0 10px 0 34px">STUDIO</span><div style="width:110px;height:2px;background:linear-gradient(90deg,rgba(255,255,255,.8),rgba(255,255,255,0))"></div>', 'left:0;width:1080px;top:1160px;justify-content:center');
  const tag = el(stage, 'glass soft pill', '', 'left:170px;top:1290px;width:740px;height:104px;border-radius:52px');
  el(tag, 'ink row', '<span style="font-size:36px;font-weight:500">Comment</span><span class="gt" style="font-size:40px;font-weight:900;margin:0 14px">VIBE</span><span style="font-size:36px;font-weight:500">to get the workflow</span>', 'justify-content:center');
  const tsh = sheen(tag);
  const foll = el(stage, 'L mono center', 'FOLLOW FOR MORE  ✦', 'top:1430px;font-size:24px;letter-spacing:.32em;opacity:0');
  S.brand = { halo, logo, lsh, word, letters, studio, tag, tsh, foll };
}

// ---------------------------------------------------------------- frame
function punch(t) {
  let k = 0;
  for (const [T, A] of [[5.0, .9], [8.0, 1.25], [16.05, .85], [26.2, .85], [30.55, 1.1]]) k += A * Math.exp(-Math.pow((t - T) / 0.11, 2));
  return k;
}

function render(t) {
  drawBg(t);
  const pk = punch(t), kk = kick(t);
  const kickOn = (t > 8 && t < 16) || t > 24 ? 1 : 0;
  const sc = 1.022 + 0.055 * pk + 0.007 * kk * kickOn;
  tf(world, `translate(${Math.sin(t * .37) * 5}px,${Math.sin(t * .29) * 7}px) rotate(${Math.sin(t * .21) * .18}deg) scale(${sc.toFixed(4)})`);
  world.style.filter = pk > 0.03 ? `blur(${(pk * 14).toFixed(1)}px) brightness(${(1 + pk * .25).toFixed(3)})` : 'none';
  op(leak, pk * 0.38);
  gctx.putImageData(grains[Math.floor(t * 30) % grains.length], 0, 0);

  // ambient glass shapes
  const shIn = eo(P(t, 0.2, 1.4));
  S.shapes.forEach(([e, d], i) => {
    const x = d.x + Math.sin(t * d.f * 2 + d.p) * d.ax, y = d.y + Math.cos(t * d.f * 1.6 + d.p) * d.ay - (1 - shIn) * 140;
    tf(e, `translate(${x}px,${y}px) rotate(${(d.rot || 0) + Math.sin(t * .3 + i) * 6}deg)`);
    op(e, shIn * (t > 30.3 ? 1 - eo(P(t, 30.3, .5)) * 0.6 : 1));
  });

  // chrome
  const ch = eo(P(t, 0.35, 0.6)) * (1 - P(t, 30.25, 0.3));
  op(S.chrome.rec, ch); op(S.chrome.tag, ch);
  tf(S.chrome.rec, `translateY(${(1 - eo(P(t, .35, .6))) * -40}px)`); tf(S.chrome.tag, `translateY(${(1 - eo(P(t, .45, .6))) * -40}px)`);
  const fr = Math.floor(t * 30);
  S.chrome.tc.textContent = `00:00:${String(Math.floor(t)).padStart(2, '0')}:${String(fr % 30).padStart(2, '0')}`;
  op(S.chrome.dot, (t % 1) < 0.6 ? 1 : 0.25);

  hookFrame(t, fr); noFrame(t); anyFrame(t); listFrame(t); procFrame(t); stepsFrame(t); ctaFrame(t); brandFrame(t);
}

function hookFrame(t, fr) {
  const h = S.hook;
  const kin = ex(P(t, 0.05, 1.0)), kout = eio(P(t, 4.86, 0.26));
  const vis = t < 5.2;
  op(h.c, vis ? kin * (1 - kout) : 0);
  if (!vis) return;
  tf(h.c, `translateY(${(1 - kin) * 120 - kout * 40}px) scale(${(0.9 + 0.1 * kin + 0.08 * kout).toFixed(4)})`);
  h.corners.forEach((c, i) => tf(c, `scale(${1 + 0.08 * Math.sin(t * 3 + i)})`));
  h.l1.update(t); h.l2.update(t); h.l3.update(t);
  const o1 = eio(P(t, 1.82, 0.36));
  tf(h.b1, `translateY(${-o1 * 90}px)`); op(h.b1, 1 - o1); blur(h.b1, o1 * 18);
  h.m1.update(t); h.m2.update(t);
  const kb = back(P(t, wt('hook2', 5) - 0.12, 0.5), 1.4);
  op(h.badge, cl(kb * 1.4)); tf(h.badge, `scale(${(0.7 + 0.3 * kb).toFixed(4)})`);
  sweep(h.bsh, P(t, wt('hook2', 7) - 0.05, 0.75));
  sweep(h.csh, P(t, 0.6, 1.2));
  h.bar.style.width = `${(t / TL.DUR) * 780}px`;
  h.fr.textContent = `FRAME ${String(fr).padStart(4, '0')} / ${Math.round(TL.DUR * 30)}`;
}

function noFrame(t) {
  const n = S.no;
  const vis = t > 4.9 && t < 8.4;
  op(n.lab, vis ? eo(P(t, 5.0, .4)) * (1 - P(t, 7.6, .25)) * 0.7 : 0);
  n.tiles.forEach((tl, i) => {
    if (!vis) { op(tl.g, 0); return; }
    const k = ex(P(t, tl.tin - 0.12, 0.55));
    const f = P(t, 7.62 + i * 0.07, 0.5), fk = f * f;
    op(tl.g, cl(k * 1.3) * (1 - fk));
    tf(tl.g, `perspective(1400px) translateX(${(1 - k) * 320}px) translateY(${fk * 900}px) rotateY(${-(1 - k) * 35}deg) rotate(${(i - 1) * 16 * fk}deg)`);
    const x = eo(P(t, tl.tx - 0.05, 0.3));
    tl.x1.setAttribute('stroke-dashoffset', 116 * (1 - cl(x * 2)));
    tl.x2.setAttribute('stroke-dashoffset', 116 * (1 - cl(x * 2 - 1)));
    op(tl.ic, 1 - 0.55 * x);
    sweep(tl.sh, P(t, tl.tin, 0.8));
  });
}

function anyFrame(t) {
  const a = S.any;
  const vis = t > 7.9 && t < 11.5;
  const out = eio(P(t, 10.95, 0.35));
  for (const h of [a.h1, a.h2, a.h3]) {
    if (!vis) { op(h, 0); continue; }
    op(h, 1 - out); h.update(t); tf(h, `translateY(${-out * 120}px)`);
  }
  a.tiles.forEach((g, i) => {
    if (!vis) { op(g, 0); return; }
    const kin = ex(P(t, 8.0 + i * 0.045, 0.8));
    const th = i * Math.PI / 4 + (t - 8) * 0.62 + (1 - kin) * 1.2;
    const R = 470 * kin + out * 500;
    const x = 540 + Math.sin(th) * R, z = Math.cos(th) * R, y = 1250 + Math.cos(th) * 70;
    const s = (0.62 + 0.38 * (z + 470) / 940) * (0.4 + 0.6 * kin);
    tf(g, `translate(${(x - 105).toFixed(1)}px,${(y - 105).toFixed(1)}px) scale(${s.toFixed(4)}) rotate(${Math.sin(th) * -8}deg)`);
    g.style.zIndex = Math.round(1000 + z);
    op(g, kin * (0.5 + 0.5 * (z + 470) / 940) * (1 - out));
  });
}

function listFrame(t) {
  const L = S.list;
  const vis = t > 10.9 && t < 16.3;
  const T = [0, 2, 4, 5, 6].map(i => wt('list', i));
  let act = 0;
  for (let k = 1; k < 5; k++) act += eio(P(t, T[k] - 0.2, 0.42));
  const out = eio(P(t, 15.82, 0.3));
  const hin = eo(P(t, 11.05, 0.45));
  op(L.head, vis ? hin * (1 - out) : 0);
  L.counter.innerHTML = `<span class="gt">${String(Math.round(act) + 1).padStart(2, '0')}</span> &nbsp;/&nbsp; 05`;
  L.titles.forEach((e, i) => {
    const d = i - act;
    tf(e, `translateY(${d * 150}px)`); op(e, 1 - Math.abs(d) * 1.2); blur(e, Math.abs(d) * 14);
  });
  L.cards.forEach((c, i) => {
    if (!vis) { op(c.g, 0); return; }
    const d = i - act, ad = Math.abs(d), sg = Math.sign(d);
    const kin = ex(P(t, 11.0 + ad * 0.06, 0.7));
    const x = sg * (ad < 1 ? ad * 440 : 440 + (ad - 1) * 160);
    const z = -ad * 330 + out * 600 * (ad < .5 ? 1 : 0);
    const ry = -sg * Math.min(ad, 1) * 42;
    tf(c.g, `perspective(1700px) translateX(${x.toFixed(1)}px) translateY(${(1 - kin) * 700}px) translateZ(${z.toFixed(1)}px) rotateY(${ry.toFixed(2)}deg)`);
    c.g.style.zIndex = 100 - Math.round(ad * 10);
    op(c.g, cl(1.9 - ad) * cl(kin * 1.5) * (1 - out));
    sweep(c.sh, P(t, T[i] - 0.1, 0.8));
  });
  if (!vis) return;
  const u = t - 11;
  // kinetic type
  S.kin.forEach((e, i) => {
    const k = eo(P((u * 1.1 + i * 0.18) % 1.6, 0, 0.5));
    tf(e, `translateX(${(1 - k) * (i % 2 ? -260 : 260)}px) scale(${0.85 + 0.15 * k})`); op(e, k);
  });
  S.kinBar.style.width = `${400 * eio((u * 0.7) % 1)}px`;
  // product
  tf(S.spot, `rotate(${u * 40}deg)`);
  tf(S.bodyHi, `translateX(${40 + Math.sin(u * 2.2) * 70}px)`);
  // cube
  tf(S.cube, `rotateX(-22deg) rotateY(${u * 70}deg)`);
  const oa = u * 2.6; tf(S.orbDot, `translate(${281 + Math.cos(oa) * 250}px,${299 + Math.sin(oa) * 110}px)`);
  op(S.orbDot, Math.sin(oa) > -0.2 ? 1 : 0.35);
  // explainer
  const eu = P((u - 0.9) % 3, 0, 1.4);
  S.bars.forEach((b, i) => tf(b, `scaleY(${eo(cl(eu * 1.6 - i * 0.12))})`));
  S.xl.setAttribute('stroke-dashoffset', 520 * (1 - eio(cl(eu * 1.3 - 0.25))));
  op(S.xd, cl(eu * 1.3 - 1.05) > 0 ? 1 : 0);
  // logo
  const lu = P((u - 2) % 3, 0, 1.3);
  S.lr.setAttribute('stroke-dashoffset', 1068 * (1 - eio(lu)));
  S.lr2.setAttribute('transform', `rotate(${u * 30} 292 330)`);
  const lb = back(cl(lu * 1.4 - 0.45), 1.6);
  tf(S.lmono, `scale(${(0.5 + 0.5 * lb).toFixed(4)})`); op(S.lmono, cl(lb * 1.5));
  op(S.lname, eo(cl(lu * 2 - 1)));
  S.spark.forEach((s, i) => { const v = Math.max(0, Math.sin(u * 5 + i * 1.7)); op(s, v * cl(lu * 2 - 0.6)); tf(s, `scale(${0.4 + 0.8 * v}) rotate(${u * 60}deg)`); });
}

function procFrame(t) {
  const p = S.proc;
  const vis = t > 15.9 && t < 26.6;
  const hOut = eio(P(t, 17.5, 0.4));
  for (const h of [p.h1, p.h2]) {
    if (!vis || t > 18.2) { op(h, 0); continue; }
    op(h, 1 - hOut); h.update(t); tf(h, `translateY(${-hOut * 160}px)`); blur(h, hOut * 10);
  }
  const mv = eio(P(t, 17.55, 0.5));
  const out = eio(P(t, 26.0, 0.35));
  const S_ = ['s1', 's2', 's3', 's4'].map(L0);
  let prog = 0;
  p.chips.forEach((c, i) => {
    if (!vis) { op(c.g, 0); return; }
    const kin = back(P(t, 16.75 + i * 0.09, 0.55), 1.5);
    const size = lerp(170, 116, mv);
    const x = lerp(540 + (i - 1.5) * 210 - 85, 540 + (i - 1.5) * 232 - 58, mv);
    const y = lerp(1120, 292, mv) - out * 260;
    c.g.style.width = c.g.style.height = `${size}px`;
    c.g.style.borderRadius = `${size * 0.28}px`;
    c.n.style.fontSize = `${lerp(46, 32, mv)}px`;
    tf(c.g, `translate(${x}px,${y}px) scale(${(0.6 + 0.4 * kin).toFixed(4)})`);
    op(c.g, cl(kin * 1.4) * (1 - out));
    const a = eo(P(t, S_[i] - 0.12, 0.3));
    op(c.fill, a);
    tf(c.g, c.g.style.transform + ` scale(${1 + 0.08 * a * (1 - eo(P(t, S_[i] + 0.2, 0.4)))})`);
    prog = Math.max(prog, i * a);
  });
  const lw = 3 * 232;
  op(p.line, mv * (1 - out)); op(p.lineFill, mv * (1 - out));
  const ly = 292 + 58 - 2 - out * 260;
  tf(p.line, `translate(${540 - lw / 2}px,${ly}px)`); p.line.style.width = `${lw}px`;
  tf(p.lineFill, `translate(${540 - lw / 2}px,${ly}px)`);
  let pf = 0;
  for (let i = 1; i < 4; i++) pf += eio(P(t, S_[i] - 0.4, 0.4));
  p.lineFill.style.width = `${pf * 232}px`;
}

function stepsFrame(t) {
  const st = S.steps;
  const vis = t > 17.6 && t < 26.6;
  const S_ = ['s1', 's2', 's3', 's4'].map(L0);
  const out = eio(P(t, 26.0, 0.35));
  st.titles.forEach((ti, i) => {
    if (!vis) { op(ti.box, 0); return; }
    const a = S_[i] - 0.18, b = i < 3 ? S_[i + 1] - 0.2 : 99;
    const kin = eo(P(t, a, 0.4)), ko = eio(P(t, b, 0.3));
    op(ti.box, (t < a ? 0 : 1) * (1 - ko) * (1 - out));
    tf(ti.box, `translateY(${-ko * 70 - out * 120}px)`);
    op(ti.lab, kin); ti.A.update(t); ti.B.update(t);
  });
  // panel
  const pin = ex(P(t, 17.75, 0.7));
  op(st.panel, vis ? pin * (1 - out) : 0);
  if (!vis) return;
  tf(st.panel, `perspective(1600px) translateY(${(1 - pin) * 600 - out * 200}px) rotateX(${(1 - pin) * 18}deg) scale(${1 - out * 0.08})`);
  sweep(st.psh, P(t, 17.9, 1.1));
  st.pages.forEach((pg, i) => {
    const a = S_[i] - 0.25, b = i < 3 ? S_[i + 1] - 0.25 : 99;
    const kin = eo5(P(t, a, 0.45)), ko = eio(P(t, b, 0.32));
    op(pg, i === 0 ? (1 - ko) : kin * (1 - ko));
    tf(pg, `translateX(${(i === 0 ? 0 : (1 - kin) * 160) - ko * 160}px)`);
    blur(pg, (i === 0 ? 0 : (1 - kin) * 10) + ko * 10);
  });
  // page 1: typing
  const s1 = S_[0];
  const total = PROMPT.reduce((n, [s]) => n + s.length, 0);
  let n = Math.floor(total * P(t, s1 + 0.2, 1.45)), html = '';
  for (const [s, c] of PROMPT) { const k = Math.min(n, s.length); if (k > 0) html += c ? `<span class="${c}">${s.slice(0, k)}</span>` : s.slice(0, k); n -= k; }
  const caretOn = t < s1 + 1.65 || (t * 2) % 1 < 0.55;
  html += `<span style="display:inline-block;width:4px;height:56px;margin-left:4px;vertical-align:-10px;border-radius:2px;background:var(--grad2);opacity:${caretOn ? 1 : 0}"></span>`;
  st.typed.innerHTML = html;
  st.tags.forEach((e, i) => { const k = back(P(t, s1 + 1.0 + i * 0.09, 0.4), 1.6); op(e, cl(k * 1.5)); tf(e, `scale(${0.6 + 0.4 * k})`); });
  const press = Math.exp(-Math.pow((t - (s1 + 1.85)) / 0.07, 2));
  const gk = back(P(t, s1 + 1.25, 0.45), 1.5);
  op(st.gen, cl(gk * 1.5)); tf(st.gen, `scale(${(0.7 + 0.3 * gk) * (1 - 0.07 * press)})`);
  st.gen.style.boxShadow = `0 18px ${50 + 60 * press}px rgba(80,100,255,${.55 + .4 * press}),inset 0 2px 0 rgba(255,255,255,.45)`;
  const rp = P(t, s1 + 1.85, 0.6);
  op(st.ripple, rp > 0 && rp < 1 ? 1 - rp : 0);
  const rr = 20 + 260 * eo(rp);
  tf(st.ripple, `translate(${730 - rr / 2}px,${680 - rr / 2}px)`); st.ripple.style.width = st.ripple.style.height = `${rr}px`;
  // page 2: code
  const s2 = S_[1];
  let last = 0;
  st.codeLines.forEach((e, i) => { const k = eo(P(t, s2 + 0.05 + i * 0.12, 0.3)); op(e, k); tf(e, `translateX(${(1 - k) * 40}px)`); if (k > 0.5) last = i; });
  tf(st.hl, `translateY(${116 + last * 50}px)`); op(st.hl, P(t, s2, 0.2));
  const sk = eo(P(t, s2 + 1.35, 0.4)); op(st.status, sk); tf(st.status, `translateY(${(1 - sk) * 20}px)`);
  // page 3: timeline (tracks reveal on "motion", "music", "voice")
  const s3w = [2, 3, 5].map(j => wt('s3', j));
  st.tracks.forEach((tr, i) => {
    const k = eio(P(t, s3w[i] - 0.15, 0.7));
    tr.rev.style.clipPath = `inset(0 ${(100 - k * 100).toFixed(1)}% 0 0)`;
    op(tr.r, eo(P(t, S_[2] - 0.1 + i * 0.08, 0.35)));
  });
  tf(st.head, `translateX(${200 + 680 * eio(P(t, S_[2] + 0.1, 1.9))}px)`);
  // page 4: formats
  const s4 = S_[3];
  let all = 0;
  st.frames.forEach((f, i) => {
    const k = eio(P(t, s4 + 0.15 + i * 0.12, 1.05));
    f.fill.style.height = `${k * f.h}px`;
    const c = back(P(t, s4 + 1.2 + i * 0.12, 0.4), 2);
    op(f.ck, cl(c * 1.5)); tf(f.ck, `scale(${0.3 + 0.7 * c})`);
    all += k / 3;
  });
  st.pbar.style.width = `${800 * all}px`;
  st.ppct.textContent = `${Math.round(all * 100)}%`;
  st.plab.innerHTML = all < 0.999 ? 'Rendering…' : '<span class="gt">Export complete</span> · 4K';
}

function ctaFrame(t) {
  const c = S.cta;
  const vis = t > 26.1 && t < 30.9;
  const out = eio(P(t, 30.42, 0.3));
  for (const h of [c.h1, c.h2, c.sub]) { if (!vis) { op(h, 0); continue; } op(h, 1 - out); h.update(t); tf(h, `translateY(${-out * 100}px)`); }
  if (!vis) { [c.glow, c.btn, c.ripple, c.cursor, ...c.bubbles].forEach(e => op(e, 0)); return; }
  const tv = wt('cta2', 1), t0 = L0('cta2') - 0.2;
  const kb = back(P(t, t0, 0.55), 1.5);
  const press = Math.exp(-Math.pow((t - tv - 0.05) / 0.08, 2));
  op(c.btn, cl(kb * 1.5) * (1 - out));
  tf(c.btn, `scale(${((0.7 + 0.3 * kb) * (1 - 0.06 * press)).toFixed(4)}) translateY(${-out * 100}px)`);
  op(c.glow, cl(kb) * (0.5 + 0.25 * Math.sin(t * 5) + 0.4 * press) * (1 - out));
  sweep(c.bsh, P(t, tv + 0.1, 0.8));
  // cursor glides in and taps
  const ci = eio(P(t, t0 + 0.1, tv - t0 - 0.05)), co = eio(P(t, tv + 0.35, 0.5));
  const cx = lerp(980, 700, ci) + co * 300, cy = lerp(1500, 880, ci) + co * 400;
  op(c.cursor, ci > 0 ? (1 - co) * (1 - out) : 0);
  tf(c.cursor, `translate(${cx}px,${cy}px) scale(${1 - 0.15 * press})`);
  const rp = P(t, tv + 0.05, 0.7), rr = 30 + 420 * eo(rp);
  op(c.ripple, rp > 0 && rp < 1 ? (1 - rp) * 0.9 : 0);
  tf(c.ripple, `translate(${712 - rr / 2}px,${888 - rr / 2}px)`); c.ripple.style.width = c.ripple.style.height = `${rr}px`;
  const XS = [110, 520, 210, 590, 140, 480];
  c.bubbles.forEach((b, i) => {
    const u = t - (tv + 0.45 + 0.22 * i);
    if (u < 0) { op(b, 0); return; }
    const k = eo(P(u, 0, 0.45));
    tf(b, `translate(${XS[i]}px,${1560 - 300 * eo(P(u, 0, 1.2)) - 50 * u}px) scale(${0.7 + 0.3 * back(P(u, 0, 0.4))})`);
    op(b, k * (1 - P(u, 1.5, 0.5)) * (1 - out));
  });
}

function brandFrame(t) {
  const b = S.brand;
  const t0 = 30.55;
  if (t < t0 - 0.1) { [b.halo, b.logo, b.word, b.studio, b.tag, b.foll].forEach(e => op(e, 0)); return; }
  const lk = back(P(t, t0, 0.8), 1.4);
  op(b.logo, cl(lk * 1.6));
  tf(b.logo, `perspective(1200px) rotateY(${(1 - eo(P(t, t0, 0.9))) * -80}deg) scale(${(0.5 + 0.5 * lk).toFixed(4)}) translateY(${Math.sin(t * 1.4) * 6}px)`);
  op(b.halo, eo(P(t, t0 + 0.1, 0.8)) * (0.75 + 0.2 * Math.sin(t * 2.2)));
  tf(b.halo, `scale(${0.8 + 0.2 * eo(P(t, t0, 1)) + 0.04 * Math.sin(t * 2.2)})`);
  sweep(b.lsh, P(t, t0 + 0.7, 0.9));
  op(b.word, 1);
  b.letters.forEach((s, i) => {
    const k = eo5(P(t, wt('brand', 0) - 0.05 + i * 0.045, 0.55));
    op(s, k); tf(s, `translateY(${(1 - k) * 0.4}em)`); blur(s, (1 - k) * 18);
    s.style.backgroundPosition = `${lerp(100, 0, eio(P(t, t0 + 1.3, 1.3)))}% 0`;
  });
  const sk = eo(P(t, wt('brand', 1) - 0.05, 0.6));
  op(b.studio, sk); tf(b.studio, `translateY(${(1 - sk) * 30}px)`); b.studio.style.letterSpacing = `${(1 - sk) * 10}px`;
  const tk = back(P(t, wt('brand', 1) + 0.5, 0.6), 1.5);
  op(b.tag, cl(tk * 1.5)); tf(b.tag, `scale(${0.75 + 0.25 * tk})`);
  sweep(b.tsh, P(t, wt('brand', 1) + 1.1, 1.0));
  op(b.foll, eo(P(t, wt('brand', 1) + 0.9, 0.6)) * 0.7);
}

// ---------------------------------------------------------------- boot
window.READY = (async () => {
  TL = await (await fetch('./work/timeline.json')).json();
  mkDots(); mkGrain();
  buildShapes(); buildChrome(); buildHook(); buildNo(); buildAny(); buildList(); buildProcess(); buildCta(); buildBrand();
  await Promise.all(["700 100px 'Inter Display'", "800 100px 'Inter Display'", "900 100px 'Inter Display'", "600 100px 'Inter Display'",
    "500 100px 'Inter Display'", "italic 400 100px ISerif", "500 30px JBM", "40px 'Noto Color Emoji'"].map(f => document.fonts.load(f, 'VIBE ✨🔥')));
  render(0);
})();
window.renderFrame = t => render(t);
