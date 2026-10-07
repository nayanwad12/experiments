// lib.js: the IDEABRO STUDIO lockup (B monogram over the wordmark) as Three.js shapes, plus shared helpers
// for the five style scenes. Logo units: x right, y up, lockup centred on the origin.
import { E, canvasTex, THREE, W, H } from '/batch2/lib/stage.js';
import { TTFLoader } from 'three/addons/loaders/TTFLoader.js';
import { Font } from 'three/addons/loaders/FontLoader.js';
import { toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';

const ttf = url => new Promise((res, rej) => new TTFLoader().load(url, d => res(new Font(d)), undefined, rej));

// rebuild shapes through a point transform (also flattens curves to polylines)
function xform(shapes, f, div = 10) {
  return shapes.map(sh => {
    const { shape, holes } = sh.extractPoints(div);
    const s = new THREE.Shape(shape.map(p => new THREE.Vector2(...f(p.x, p.y))));
    holes.forEach(h => s.holes.push(new THREE.Path(h.map(p => new THREE.Vector2(...f(p.x, p.y))))));
    return s;
  });
}
function bbox(shapes) {
  const b = new THREE.Box2(); shapes.forEach(s => s.extractPoints(4).shape.forEach(p => b.expandByPoint(p))); return b;
}
// one word, letter by letter (so styles can animate letters), with tracking
function word(font, str, size, track) {
  const sc = size / font.data.resolution; let x = 0; const letters = [];
  for (const ch of str) {
    const g = font.data.glyphs[ch], x0 = x;
    letters.push(xform(font.generateShapes(ch, size), (px, py) => [px + x0, py]));
    x += g.ha * sc + track;
  }
  return letters;
}

export const COPY = { name: 'IDEABRO', studio: 'STUDIO' };

export async function lockup({ iconH = 1.75, nameW = 3.5, gap1 = 0.4, gap2 = 0.27, studioRatio = 0.34 } = {}) {
  const G = await (await fetch('/logo-b/work/logo.json')).json();
  const fBlack = await ttf('/fonts/Montserrat-Black.ttf'), fBold = await ttf('/fonts/Montserrat-Bold.ttf');
  const shapeOf = pts => new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y)));
  // icon: the measured B, scaled
  const s = iconH / 3.57;
  let icon = xform([shapeOf(G.stem), shapeOf(G.body)], (x, y) => [x * s, y * s]);
  // name: fit to nameW
  let name = word(fBlack, COPY.name, 1, 0.03);
  let nb = bbox(name.flat()), k = nameW / (nb.max.x - nb.min.x);
  name = name.map(L => xform(L, (x, y) => [(x - nb.min.x) * k - nameW / 2, y * k]));
  nb = bbox(name.flat());
  const capN = nb.max.y - nb.min.y;
  // studio: cap height = studioRatio * name cap, letter-spaced to the same width
  const capS = capN * studioRatio;
  let st = word(fBold, COPY.studio, 1, 0);
  let sb = bbox(st.flat()); const ks = capS / (sb.max.y - sb.min.y);
  const w0 = (sb.max.x - sb.min.x) * ks, track = (nameW - w0) / (COPY.studio.length - 1);
  st = st.map((L, i) => xform(L, (x, y) => [(x - sb.min.x) * ks + i * track - nameW / 2, y * ks]));
  sb = bbox(st.flat());
  // stack: icon, gap1, name, gap2, studio; centre the lot vertically
  const total = iconH + gap1 + capN + gap2 + capS, top = total / 2;
  const yIcon = top - iconH / 2, yName = top - iconH - gap1 - capN / 2, yStudio = -top + capS / 2;
  icon = xform(icon, (x, y) => [x, y + yIcon], 1);
  name = name.map(L => xform(L, (x, y) => [x, y - (nb.min.y + nb.max.y) / 2 + yName], 1));
  st = st.map(L => xform(L, (x, y) => [x, y - (sb.min.y + sb.max.y) / 2 + yStudio], 1));
  const all = [...icon, ...name.flat(), ...st.flat()];
  const b = bbox(all);
  return { icon, name, studio: st, all, w: b.max.x - b.min.x, h: b.max.y - b.min.y, y: { icon: yIcon, name: yName, studio: yStudio },
    capN, capS, iconH };
}

// extruded solid: smooth arcs and bevels, hard corners, dead-flat faces. groups: [faces, sides]
// inset = true keeps the silhouette exact (bevel grows inwards); letters with counters look cleaner with inset = false
export function solid(shapes, depth = 0.3, bev = 0.02, segs = 5, inset = true) {
  let g = new THREE.ExtrudeGeometry(shapes, { depth, curveSegments: 1, bevelEnabled: bev > 0, bevelThickness: bev,
    bevelSize: inset ? bev : bev * 0.6, bevelOffset: inset ? -bev : -bev * 0.4, bevelSegments: segs });
  g.translate(0, 0, -depth / 2);
  g = toCreasedNormals(g, Math.PI / 7);
  const caps = g.groups[0], n = g.attributes.normal, p = g.attributes.position;
  for (let i = caps.start; i < caps.start + caps.count; i++) n.setXYZ(i, 0, 0, Math.sign(p.getZ(i)));
  return g;
}

// flat lockup on a 2D canvas (particles sample it; glitch and lock-ups show it). u = px per logo unit
export function lockupCanvas(L, w, h, { u = null, icon = '#ffffff', name = '#ffffff', studio = '#ffffff', bg = null } = {}) {
  const ct = canvasTex(w, h), c = ct.ctx;
  u = u ?? Math.min(w / (L.w * 1.08), h / (L.h * 1.08));
  if (bg) { c.fillStyle = bg; c.fillRect(0, 0, w, h); }
  const draw = (shapes, col) => {
    c.fillStyle = col; const p = new Path2D();
    shapes.forEach(sh => { const { shape, holes } = sh.extractPoints(12);
      [shape, ...holes].forEach(r => r.forEach((q, i) => (i ? p.lineTo : p.moveTo).call(p, w / 2 + q.x * u, h / 2 - q.y * u)));
      p.closePath(); });
    c.fill(p, 'evenodd');
  };
  draw(L.icon, icon); draw(L.name.flat(), name); draw(L.studio.flat(), studio);
  ct.update(); return { ...ct, u };
}

// dark studio: strip lights + horizon wall, for chrome / steel
export function stripEnv(renderer, accent = '#cfe0ff', bright = 0) {
  const sc = new THREE.Scene(); sc.background = new THREE.Color('#010102');
  const strip = (w, h, pos, rot, c, k) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(c).multiplyScalar(k), side: THREE.DoubleSide }));
    m.position.set(...pos); m.rotation.set(...rot); sc.add(m); };
  strip(1.0, 14, [-6, 0, 2], [0, Math.PI / 2, 0], '#ffffff', 2.4);
  strip(0.5, 14, [6, 0, 0], [0, -Math.PI / 2, 0], '#ffffff', 1.8);
  strip(14, 0.7, [0, 6, 2], [Math.PI / 2, 0, 0], '#ffffff', 1.3);
  strip(0.35, 10, [3.5, 0, -6], [0, 0, 0], accent, 1.6);
  strip(3, 3, [-2, 2, 7], [0, Math.PI, 0], '#9fb6ff', 0.5);
  if (bright) {   // big soft boxes: liquid metal needs large bright shapes to reflect
    strip(8, 5, [0, 7, 0], [Math.PI / 2, 0, 0], '#ffffff', 1.4 * bright);
    strip(5, 6, [-7, 1, -2], [0, Math.PI / 2, 0], '#dfe8ff', 1.0 * bright);
    strip(4, 6, [7, -1, 3], [0, -Math.PI / 2, 0], '#ffffff', 0.7 * bright);
  }
  const hz = canvasTex(64, 512), c = hz.ctx, g = c.createLinearGradient(0, 0, 0, 512);
  g.addColorStop(0, '#07080c'); g.addColorStop(0.40, '#4b5266'); g.addColorStop(0.5, '#ffffff'); g.addColorStop(0.53, '#b9c2da');
  g.addColorStop(0.62, '#1d1f27'); g.addColorStop(1, '#0a0a0d'); c.fillStyle = g; c.fillRect(0, 0, 64, 512); hz.update();
  const front = new THREE.Mesh(new THREE.PlaneGeometry(30, 16), new THREE.MeshBasicMaterial({ map: hz.tex, side: THREE.DoubleSide }));
  front.position.set(0, 0, 9); front.rotation.y = Math.PI; sc.add(front);
  return new THREE.PMREMGenerator(renderer).fromScene(sc, 0.02).texture;
}

// camera distance so the final lockup sits comfortably in any aspect
export function fitter(L, fill = 0.62, fillW = 0.8) {
  const asp = W / H, visH = Math.max(L.h / fill, L.w / fillW / asp);
  return fov => visH / (2 * Math.tan(THREE.MathUtils.degToRad(fov) / 2));
}

export function glowTex(n = 128) {
  const g = canvasTex(n, n), c = g.ctx, r = c.createRadialGradient(n / 2, n / 2, 0, n / 2, n / 2, n / 2);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.1, 'rgba(255,255,255,0.6)'); r.addColorStop(0.35, 'rgba(255,255,255,0.1)');
  r.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = r; c.fillRect(0, 0, n, n); g.update(); return g.tex;
}

export const PX = H / 1080;
export { E, THREE, W, H, canvasTex };
