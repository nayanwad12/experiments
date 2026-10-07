// Render a Three.js/WebGL page frame-by-frame in headless Chromium (SwiftShader) -> H.264 layer video.
//
//   node render3d.mjs <video-dir>/scene.html --w 1080 --h 1920 --fps 30 --dur 30 -o <video-dir>/work/layer.mp4
//   node render3d.mjs <video-dir>/scene.html --stills 1.2,4.5 -o <video-dir>/out/web_stills
//   options: --workers 4  --from 0 --to <sec>  --q 92 (jpeg quality of the frame grab)
//
// The page must set window.READY (a promise) and window.renderFrame(t) (sync or async; t in seconds).
// Pages are served from the reels/ folder over http, so they can import /batch2/node_modules/three/...
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { spawn } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');                 // reels/
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const page_ = path.resolve(args[0]);
const W = +opt('w', 1080), H = +opt('h', 1920), FPS = +opt('fps', 30), DUR = +opt('dur', 10);
const WORKERS = +opt('workers', 4), Q = +opt('q', 94);
const OUT = path.resolve(args.includes('-o') ? args[args.indexOf('-o') + 1] : 'work/layer.mp4');
const STILLS = opt('stills', null);
const FROM = +opt('from', 0), TO = +opt('to', DUR);

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.ttf': 'font/ttf', '.png': 'image/png', '.jpg': 'image/jpeg', '.wav': 'audio/wav', '.bin': 'application/octet-stream' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const URL = `http://127.0.0.1:${server.address().port}/${path.relative(ROOT, page_)}?w=${W}&h=${H}&fps=${FPS}`;
const GL = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];

async function open() {
  const browser = await chromium.launch({ args: GL, executablePath: undefined });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('page error:', e.message));
  page.on('requestfailed', r => console.error('request failed:', r.url()));
  page.on('response', r => { if (r.status() >= 400) console.error('HTTP', r.status(), r.url()); });
  page.on('console', m => { if (['error', 'warning'].includes(m.type())) console.error('console:', m.text()); });
  await page.goto(URL);
  await page.waitForFunction(() => window.READY !== undefined, null, { timeout: 120000 });
  await Promise.race([
    page.evaluate(async () => { await window.READY; if (document.fonts) await document.fonts.ready; }),
    new Promise((_, rej) => setTimeout(() => rej(new Error('page never became READY (see page errors above)')), 180000))]);
  return { browser, page };
}
const grab = (page, type = 'jpeg') => page.screenshot(type === 'png' ? { type, clip: { x: 0, y: 0, width: W, height: H } }
  : { type, quality: Q, clip: { x: 0, y: 0, width: W, height: H } });

if (STILLS) {
  fs.mkdirSync(OUT, { recursive: true });
  const { browser, page } = await open();
  for (const s of STILLS.split(',').map(Number)) {
    await page.evaluate(t => window.renderFrame(t), s);
    fs.writeFileSync(path.join(OUT, `w_${s.toFixed(2)}.png`), await grab(page, 'png'));
    console.log('still', s);
  }
  await browser.close(); server.close(); process.exit(0);
}

const N0 = Math.round(FROM * FPS), N1 = Math.round(TO * FPS), CH = 45;
const SEG = OUT + '.segs';
fs.mkdirSync(SEG, { recursive: true });
const segPath = c => path.join(SEG, `s${String(c).padStart(5, '0')}.mp4`);
const chunks = []; for (let a = N0; a < N1; a += CH) chunks.push(a);
const todo = chunks.filter(a => !fs.existsSync(segPath(a)));
console.log(`layer: ${N1 - N0} frames, ${todo.length}/${chunks.length} chunks to render, ${WORKERS} workers`);
const t0 = Date.now(); let done = 0;

async function chunk(ctx, a) {
  const b = Math.min(N1, a + CH), part = segPath(a) + '.part.mp4';
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '12', '-pix_fmt', 'yuv420p', '-r', String(FPS), part], { stdio: ['pipe', 'inherit', 'inherit'] });
  const closed = new Promise(r => ff.on('close', r));
  for (let i = a; i < b; i++) {
    await ctx.page.evaluate(t => window.renderFrame(t), i / FPS);
    const buf = await grab(ctx.page);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  if (await closed !== 0) throw new Error('ffmpeg failed');
  fs.renameSync(part, segPath(a));
  done += b - a;
  const el = (Date.now() - t0) / 1000;
  process.stdout.write(`\r  ${done}/${N1 - N0} frames  ${el.toFixed(0)}s  eta ${(el / done * (N1 - N0 - done)).toFixed(0)}s   `);
}

async function worker() {
  let ctx = await open();
  while (todo.length) {
    const a = todo.shift();
    for (let k = 1; ; k++) {
      try { await chunk(ctx, a); break; }
      catch (e) { console.error(`\nchunk ${a} failed (${k}): ${e.message}`); if (k >= 3) throw e;
        await ctx.browser.close().catch(() => {}); ctx = await open(); }
    }
  }
  await ctx.browser.close();
}
await Promise.all([...Array(WORKERS)].map(worker));
const list = path.join(SEG, 'list.txt');
fs.writeFileSync(list, chunks.map(a => `file '${segPath(a)}'`).join('\n'));
await new Promise((r, j) => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', OUT],
  { stdio: 'inherit' }).on('close', c => c ? j(new Error('concat failed')) : r()));
fs.rmSync(SEG, { recursive: true, force: true });
console.log(`\n-> ${OUT}  (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
server.close();
