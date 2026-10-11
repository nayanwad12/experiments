// OncoXpress overlay: captions + motion graphics, drawn on a transparent page. window.renderFrame(t) is a pure
// function of t (seconds), so the Playwright render is deterministic. Timing comes from work/timeline.js (build.py).
const TL = window.TL;
const root = document.getElementById('root');

// ---------------------------------------------------------------- helpers
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const prog = (t, a, b) => clamp((t - a) / (b - a));
const expo = x => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
const inout = x => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const back = x => { const c = 1.6; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const lerp = (a, b, k) => a + (b - a) * k;
const el = (tag, cls, html, parent = root) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  parent.appendChild(e);
  return e;
};
const css = (e, o) => Object.assign(e.style, o);
// fade + rise + un-blur, Apple-style
function reveal(e, k, { y = 24, blur = 14, scale = 1 } = {}) {
  css(e, {
    opacity: k, filter: k >= 1 ? 'none' : `blur(${(1 - k) * blur}px)`,
    transform: (e.dataset.base || '') + ` translateY(${(1 - k) * y}px) scale(${lerp(scale, 1, k)})`,
  });
}
const shot = name => TL.shots.find(s => s.gfx === name);

const ICON = {
  plan: '<path d="M8 4h12l6 6v18H8z M20 4v6h6 M12 17h10 M12 22h7"/>',
  second: '<circle cx="17" cy="16" r="9"/><path d="M13 16l3 3 5-6"/>',
  ask: '<path d="M5 8h22v14H14l-6 5v-5H5z M12 15h.01 M16 15h.01 M20 15h.01"/>',
  team: '<circle cx="12" cy="12" r="4"/><circle cx="22" cy="13" r="3.2"/><path d="M4 26c0-5 4-8 8-8s8 3 8 8 M20 19c4 0 8 2 8 7"/>',
  heart: '<path d="M16 27s-10-6-10-13a5.5 5.5 0 0110-3 5.5 5.5 0 0110 3c0 7-10 13-10 13z"/>',
};
const icon = (k, size = 30) =>
  `<svg width="${size}" height="${size}" viewBox="0 0 32 32" fill="none" stroke="url(#ig)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${ICON[k]}</svg>`;
el('div', '', `<svg width="0" height="0" style="position:absolute"><defs>
  <linearGradient id="ig" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a48bff"/><stop offset="1" stop-color="#4aa3ff"/></linearGradient>
  <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8b6cff"/><stop offset="1" stop-color="#2f8cff"/></linearGradient>
</defs></svg>`);

// OncoXpress mark: an "O" ring crossed by an "X", drawn with strokes so it can animate on.
function logo(parent, h) {
  const box = el('div', 'abs', '', parent);
  box.innerHTML = `
    <div style="display:flex;align-items:center;gap:${h * 0.32}px">
      <svg width="${h * 1.42}" height="${h}" viewBox="0 0 142 100" fill="none" stroke-linecap="round">
        <circle class="ring" cx="50" cy="50" r="38" stroke="url(#lg)" stroke-width="11" pathLength="1"
                stroke-dasharray="1" transform="rotate(-90 50 50)"/>
        <path class="x1" d="M74 20 L128 80" stroke="url(#lg)" stroke-width="11" pathLength="1" stroke-dasharray="1"/>
        <path class="x2" d="M128 20 L74 80" stroke="#f5f5f7" stroke-width="11" pathLength="1" stroke-dasharray="1"/>
      </svg>
      <div class="word" style="font-size:${h * 0.78}px;font-weight:680;letter-spacing:-0.035em;white-space:nowrap">
        ${[...'Onco'].map(c => `<span>${c}</span>`).join('')}${[...'Xpress'].map(c => `<span class="grad">${c}</span>`).join('')}
      </div>
    </div>`;
  const ring = box.querySelector('.ring'), x1 = box.querySelector('.x1'), x2 = box.querySelector('.x2');
  const letters = [...box.querySelectorAll('.word span')];
  letters.forEach(s => css(s, { display: 'inline-block' }));
  return {
    box,
    draw(k) {            // 0..1 over the whole build
      ring.style.strokeDashoffset = 1 - inout(prog(k, 0, 0.55));
      x1.style.strokeDashoffset = 1 - inout(prog(k, 0.25, 0.6));
      x2.style.strokeDashoffset = 1 - inout(prog(k, 0.35, 0.7));
      letters.forEach((s, i) => reveal(s, expo(prog(k, 0.3 + i * 0.035, 0.62 + i * 0.035)), { y: 18, blur: 10 }));
    },
  };
}

// ---------------------------------------------------------------- G1 questions (over blurred desk footage)
const G1 = shot('questions');
const g1 = el('div', 'layer');
const scrim = el('div', 'layer', '', g1);
css(scrim, { background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,.25), rgba(0,0,0,.7))' });
const qwrap = el('div', 'layer', '', g1);
const QS = [
  ['What does this mean?', 250, 250, 58, 0.15],
  ['What are my options?', 1130, 190, 46, 0.5],
  ['Who do I ask?', 1240, 520, 64, 0.85],
  ['What happens next?', 330, 610, 50, 1.2],
  ['How do I tell my family?', 760, 390, 42, 1.55],
];
const qEls = QS.map(([txt, x, y, size]) => {
  const q = el('div', 'q', txt, qwrap);
  css(q, { left: x + 'px', top: y + 'px', fontSize: size + 'px' });
  return q;
});

// ---------------------------------------------------------------- G2 care options UI
const G2 = shot('options');
const g2 = el('div', 'layer black');
const w2 = el('div', 'win', '', g2);
css(w2, { left: '340px', top: '110px', width: '1240px', height: '720px' });
w2.innerHTML = `<div class="bar"><div class="dot"></div><div class="dot"></div><div class="dot"></div>
  <div class="title">${icon('heart', 24)} OncoXpress <span style="color:#6e6e73;font-weight:500">· Care Plan</span></div></div>`;
const lab2 = el('div', 'label abs', 'Your options, explained', w2);
css(lab2, { left: '44px', top: '100px' });
const CARDS = [
  ['plan', 'Treatment plan', 'Every option, explained clearly'],
  ['second', 'Second opinion', 'Specialist review of your reports'],
  ['ask', 'Questions to ask', 'Prepared for your next visit'],
  ['team', 'Your care team', 'Everyone involved, in one place'],
];
const cEls = CARDS.map(([ic, h, p], i) => {
  const c = el('div', 'card', `<div class="icon">${icon(ic)}</div><h4>${h}</h4><p>${p}</p>`, w2);
  css(c, { left: 44 + (i % 2) * 586 + 'px', top: 150 + Math.floor(i / 2) * 270 + 'px', width: '506px', height: '190px' });
  return c;
});

// ---------------------------------------------------------------- G3 guidance -> care circle
const G3 = shot('guidance');
const g3 = el('div', 'layer black');
const stack = el('div', 'layer', '', g3);
const WORDS = [['Guidance.', 0], ['Thoughtful decisions.', 1], ['Support.', 2]];
const wEls = WORDS.map(([w, i]) => {
  const d = el('div', 'big' + (i === 2 ? ' grad' : ''), w, stack);
  css(d, { top: 250 + i * 150 + 'px' });
  return d;
});
const circle = el('div', 'layer', '', g3);
const CX = 960, CY = 450;
const NODES = [['Oncologist', 520, 290], ['Care coordinator', 520, 620], ['Family', 1400, 290], ['Friends', 1400, 620]];
const svg3 = el('div', 'layer', `<svg width="1920" height="1080">${NODES.map(([, x, y]) =>
  `<line x1="${CX}" y1="${CY}" x2="${x}" y2="${y}" stroke="rgba(255,255,255,.22)" stroke-width="2" pathLength="1" stroke-dasharray="1"/>`).join('')}</svg>`, circle);
const lines3 = [...svg3.querySelectorAll('line')];
const you = el('div', 'node', `<div style="width:190px;height:190px;border-radius:50%;padding:5px;background:linear-gradient(135deg,#8b6cff,#2f8cff);margin:0 auto">
  <div style="width:100%;height:100%;border-radius:50%;background:#000;display:grid;place-items:center;font-size:40px;font-weight:700;letter-spacing:-0.02em">You</div></div>`, circle);
css(you, { left: CX + 'px', top: CY + 'px' });
const nEls = NODES.map(([n, x, y], i) => {
  const d = el('div', 'node', `<div class="ring">${icon(['plan', 'team', 'heart', 'ask'][i], 40)}</div><div class="nm">${n}</div>`, circle);
  css(d, { left: x + 'px', top: y + 'px' });
  d.dataset.base = 'translate(-50%,-50%)';
  return d;
});
you.dataset.base = 'translate(-50%,-50%)';

// ---------------------------------------------------------------- G4 logo reveal
const G4 = shot('logo');
const g4 = el('div', 'layer black');
const glow4 = el('div', 'layer', '', g4);
css(glow4, { background: 'radial-gradient(circle at 50% 50%, rgba(110,90,255,.28), rgba(0,0,0,0) 38%)' });
const L4 = logo(g4, 120);
css(L4.box, { left: '50%', top: '50%' });
L4.box.dataset.base = 'translate(-50%,-50%)';

// ---------------------------------------------------------------- G5 the person behind the diagnosis
const G5 = shot('profile');
const g5 = el('div', 'layer black');
const w5 = el('div', 'win', '', g5);
css(w5, { left: '330px', top: '130px', width: '1260px', height: '700px' });
w5.innerHTML = `<div class="bar"><div class="dot"></div><div class="dot"></div><div class="dot"></div>
  <div class="title">${icon('heart', 24)} OncoXpress <span style="color:#6e6e73;font-weight:500">· Patient profile</span></div></div>`;
const info = el('div', 'abs', '', w5);
css(info, { left: '560px', top: '112px', width: '650px' });
const nm = el('div', '', `<div style="font-size:64px;font-weight:700;letter-spacing:-0.035em">Meera</div>
  <div style="font-size:26px;color:#86868b;margin-top:6px">More than a diagnosis</div>`, info);
const lab5 = el('div', 'label', 'What matters to her', info);
css(lab5, { marginTop: '40px', marginBottom: '18px' });
const chipBox = el('div', '', '', info);
css(chipBox, { display: 'flex', flexWrap: 'wrap', gap: '14px' });
const chips = ['Grandmother of two', 'Loves her garden', 'Morning appointments', 'Family joins every visit']
  .map(c => el('div', 'chip', c, chipBox));
const rows = [['team', 'Care team', '4 people, one plan'], ['plan', 'Next step', 'Consultation · Thu, 10:30']].map(([ic, a, b]) => {
  const r = el('div', '', `<div class="icon" style="width:52px;height:52px">${icon(ic, 28)}</div>
    <div><div style="font-size:20px;color:#86868b">${a}</div><div style="font-size:26px;font-weight:600;margin-top:2px">${b}</div></div>`, info);
  css(r, { display: 'flex', gap: '18px', alignItems: 'center', marginTop: '26px' });
  return r;
});
css(rows[0], { marginTop: '40px' });
const face = el('div', 'face', '', g5);
face.style.backgroundImage = 'url(work/face.jpg)';
const FACE_TO = { x: 384, y: 220, w: 460, h: 560 };

// ---------------------------------------------------------------- G6 end card
const G6 = shot('endcard');
const g6 = el('div', 'layer black');
const glow6 = el('div', 'layer', '', g6);
css(glow6, { background: 'radial-gradient(ellipse at 50% 46%, rgba(110,90,255,.22), rgba(0,0,0,0) 45%)' });
const L6 = logo(g6, 104);
css(L6.box, { left: '50%', top: '380px', transform: 'translate(-50%,-50%)' });
L6.box.dataset.base = 'translate(-50%,-50%)';
const tag = el('div', 'abs', 'See the person behind the diagnosis.', g6);
css(tag, { left: 0, right: 0, top: '480px', textAlign: 'center', fontSize: '42px', fontWeight: 500, color: '#a1a1a6', letterSpacing: '-0.02em' });
const cta = el('div', 'abs', `Take your next step <span style="font-weight:500">→</span>`, g6);
css(cta, { left: '50%', top: '600px', padding: '22px 44px', borderRadius: '999px', background: '#f5f5f7', color: '#000',
  fontSize: '30px', fontWeight: 620, letterSpacing: '-0.015em', whiteSpace: 'nowrap' });
cta.dataset.base = 'translateX(-50%)';

// ---------------------------------------------------------------- captions + fades (on top)
const cap = el('div', '', '');
cap.id = 'cap';
const capPages = TL.captions.map(p => {
  const d = el('div', '', p.words.map(w => `<span>${w.w}</span>`).join(''), cap);
  css(d, { position: 'absolute', left: 0, right: 0, bottom: 0 });
  return { p, d, spans: [...d.querySelectorAll('span')] };
});
const fade = el('div', 'layer black');

// ---------------------------------------------------------------- frame
const show = (e, s, t) => { e.style.display = t >= s.s && t < s.e ? 'block' : 'none'; return t >= s.s && t < s.e; };

window.renderFrame = function (t) {
  // G1
  if (show(g1, G1, t)) {
    const k = t - G1.s;
    scrim.style.opacity = expo(prog(k, 0, 0.5));
    QS.forEach((q, i) => {
      const a = expo(prog(k, q[4], q[4] + 0.7));
      css(qEls[i], { opacity: a * (i % 2 ? 0.62 : 0.92), filter: `blur(${(1 - a) * 16}px)`,
                     transform: `translateY(${(1 - a) * 30 - k * 6}px)` });
    });
    // the questions grow "bigger than the answers"
    const grow = inout(prog(t, 4.8, G1.e));
    css(qwrap, { transform: `scale(${1 + grow * 0.16})`, transformOrigin: '50% 42%', opacity: 1 - prog(t, G1.e - 0.3, G1.e) });
  }
  // G2
  if (show(g2, G2, t)) {
    const k = t - G2.s, a = expo(prog(k, 0, 0.6));
    css(w2, { opacity: a, transform: `translateY(${(1 - a) * 40}px) scale(${lerp(0.94, 1, a)})` });
    reveal(lab2, expo(prog(k, 0.2, 0.7)), { y: 10, blur: 6 });
    cEls.forEach((c, i) => {
      reveal(c, expo(prog(k, 0.3 + i * 0.13, 0.9 + i * 0.13)), { y: 30, blur: 10, scale: 0.97 });
      const hl = i === 0 ? inout(prog(k, 1.1, 1.4)) : 0;
      c.style.borderColor = `rgba(139,108,255,${0.09 + hl * 0.7})`;
      c.style.boxShadow = `0 0 ${hl * 60}px rgba(110,90,255,${hl * 0.35})`;
    });
  }
  // G3
  if (show(g3, G3, t)) {
    const L = TL.lines;
    const starts = [L[10].s, L[11].s, L[12].s];      // "It is guidance," "thoughtful decisions," "and support..."
    const out = inout(prog(t, 23.05, 23.45));
    wEls.forEach((w, i) => {
      const a = expo(prog(t, starts[i] - 0.05, starts[i] + 0.55));
      const next = i < 2 ? inout(prog(t, starts[i + 1] - 0.05, starts[i + 1] + 0.35)) : 0;
      reveal(w, a, { y: 40, blur: 24, scale: 1.04 });
      w.style.opacity = a * lerp(1, 0.32, next) * (1 - out);
    });
    css(stack, { transform: `translateY(${-out * 60}px) scale(${1 - out * 0.06})` });
    const c = expo(prog(t, 23.25, 23.85));
    reveal(you, c, { y: 0, blur: 12, scale: 0.8 });
    lines3.forEach((ln, i) => { ln.style.strokeDashoffset = 1 - inout(prog(t, 23.45 + i * 0.1, 23.95 + i * 0.1)); });
    nEls.forEach((n, i) => {
      const a = prog(t, 23.6 + i * 0.12, 24.05 + i * 0.12);
      css(n, { opacity: clamp(a * 2), transform: `translate(-50%,-50%) scale(${lerp(0.6, 1, back(a))})` });
    });
  }
  // G4
  if (show(g4, G4, t)) {
    const k = t - G4.s;
    L4.draw(prog(k, 0.02, 1.0));
    glow4.style.opacity = expo(prog(k, 0.2, 1.0));
    css(L4.box, { transform: `translate(-50%,-50%) scale(${lerp(1.0, 1.035, prog(k, 0, G4.e - G4.s))})` });
  }
  // G5
  if (show(g5, G5, t)) {
    const k = t - G5.s, m = inout(prog(k, 0.12, 0.95));
    css(face, { left: lerp(0, FACE_TO.x, m) + 'px', top: lerp(0, FACE_TO.y, m) + 'px',
                width: lerp(1920, FACE_TO.w, m) + 'px', height: lerp(1080, FACE_TO.h, m) + 'px',
                borderRadius: lerp(0, 26, m) + 'px', backgroundSize: 'cover',
                backgroundPosition: `${lerp(50, 52, m)}% ${lerp(50, 28, m)}%` });
    const wa = expo(prog(k, 0.55, 1.2));
    css(w5, { opacity: wa, transform: `scale(${lerp(1.04, 1, wa)})` });
    reveal(nm, expo(prog(k, 0.95, 1.5)), { y: 20, blur: 10 });
    reveal(lab5, expo(prog(k, 1.15, 1.6)), { y: 10, blur: 6 });
    chips.forEach((c, i) => reveal(c, expo(prog(k, 1.3 + i * 0.17, 1.8 + i * 0.17)), { y: 16, blur: 8, scale: 0.94 }));
    rows.forEach((r, i) => reveal(r, expo(prog(k, 2.2 + i * 0.2, 2.75 + i * 0.2)), { y: 16, blur: 8 }));
  }
  // G6
  if (show(g6, G6, t)) {
    const k = t - G6.s;
    L6.draw(prog(k, 0.0, 1.1));
    glow6.style.opacity = expo(prog(k, 0.2, 1.2));
    reveal(tag, expo(prog(k, 0.75, 1.35)), { y: 18, blur: 10 });
    reveal(cta, expo(prog(k, 1.35, 1.95)), { y: 20, blur: 8, scale: 0.94 });
  }
  // captions (hidden while the logo itself says the name)
  capPages.forEach(({ p, d, spans }) => {
    const on = t >= p.s && t < p.e && p.words[0].w !== 'OncoXpress.';
    d.style.display = on ? 'block' : 'none';
    if (!on) return;
    d.style.opacity = 1 - prog(t, p.e - 0.12, p.e);
    spans.forEach((s, i) => {
      const a = expo(prog(t, p.words[i].s - 0.08, p.words[i].s + 0.3));
      css(s, { opacity: a, filter: a >= 1 ? 'none' : `blur(${(1 - a) * 8}px)`, transform: `translateY(${(1 - a) * 12}px)` });
    });
  });
  // open from black, close to black
  fade.style.opacity = Math.max(1 - expo(prog(t, 0.0, 0.7)), inout(prog(t, 39.3, 40.0)));
};
window.ready = document.fonts.ready;
