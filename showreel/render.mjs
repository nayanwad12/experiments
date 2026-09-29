// Render reel.html frame-by-frame in headless Chromium (WebGL via SwiftShader) and encode with ffmpeg.
//
//   node render.mjs                         # full video -> out/video.mp4 (no audio)
//   node render.mjs --stills 2.1,9.4,17.8   # preview PNGs -> out/stills/
//   node render.mjs --fps 30 --mb 4 --workers 4
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'out');
fs.mkdirSync(OUT, { recursive: true });

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const FPS = +opt('fps', 60), MBS = +opt('mb', 6), WORKERS = +opt('workers', 4);
const STILLS = opt('stills', null);

let chromium;
try { ({ chromium } = await import('playwright')); }
catch { ({ chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs')); }

const FFMPEG = process.env.FFMPEG || execFileSync('python3', ['-c', 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())']).toString().trim();
const URL = pathToFileURL(path.join(HERE, 'reel.html')).href + `?render=1&fps=${FPS}&mb=${MBS}`;
const GL_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'];

async function openPage() {
  const browser = await chromium.launch({ args: GL_ARGS });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', e => console.error('page error:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
  await page.goto(URL);
  await page.evaluate(() => window.READY);
  const meta = await page.evaluate(() => window.META);
  return { browser, page, meta };
}
const shot = page => page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1920, height: 1080 } });

if (STILLS) {
  const dir = path.join(OUT, 'stills'); fs.mkdirSync(dir, { recursive: true });
  const { browser, page } = await openPage();
  for (const s of STILLS.split(',').map(Number)) {
    const f = Math.round(s * FPS);
    await page.evaluate(i => window.renderFrame(i), f);
    fs.writeFileSync(path.join(dir, `still_${s.toFixed(2)}.png`), await shot(page));
    console.log('still', s);
  }
  await browser.close();
  process.exit(0);
}

const { browser: probe, meta } = await openPage();
await probe.close();
const N = meta.FRAMES, per = Math.ceil(N / WORKERS);
console.log(`rendering ${N} frames @ ${FPS} fps, ${MBS} blur samples, ${WORKERS} workers`);
const t0 = Date.now();
let done = 0;

async function worker(k) {
  const a = k * per, b = Math.min(N, a + per);
  if (a >= b) return null;
  const seg = path.join(OUT, `seg_${k}.mp4`);
  const ff = spawn(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-r', String(FPS), seg], { stdio: ['pipe', 'inherit', 'inherit'] });
  const closed = new Promise(r => ff.on('close', r));
  const { browser, page } = await openPage();
  for (let i = a; i < b; i++) {
    await page.evaluate(n => window.renderFrame(n), i);
    const buf = await shot(page);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    done++;
    if (done % 60 === 0) {
      const el = (Date.now() - t0) / 1000;
      console.log(`${done}/${N} frames  ${el.toFixed(0)}s elapsed  eta ${(el / done * (N - done)).toFixed(0)}s`);
    }
  }
  ff.stdin.end();
  await closed;
  await browser.close();
  return seg;
}

const segs = (await Promise.all([...Array(WORKERS).keys()].map(worker))).filter(Boolean);
const list = path.join(OUT, 'segs.txt');
fs.writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
execFileSync(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(OUT, 'video.mp4')]);
for (const s of segs) fs.unlinkSync(s);
fs.unlinkSync(list);
console.log(`done in ${((Date.now() - t0) / 1000).toFixed(0)}s -> out/video.mp4`);
