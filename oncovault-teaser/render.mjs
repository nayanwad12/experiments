// Render index.html frame-by-frame in headless Chromium and encode with ffmpeg.
//
//   node render.mjs                         # full video -> out/video.mp4 (no audio)
//   node render.mjs --stills 2.1,9.4,17.8   # preview PNGs -> out/stills/
//   node render.mjs --fps 30 --mb 2         # quick draft
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'out');
fs.mkdirSync(OUT, { recursive: true });

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const FPS = +opt('fps', 60), MBS = +opt('mb', 4), WORKERS = +opt('workers', 4);
const STILLS = opt('stills', null);

let chromium;
try { ({ chromium } = await import('playwright')); }
catch { ({ chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs')); }

const FFMPEG = process.env.FFMPEG || execFileSync('python3', ['-c', 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())']).toString().trim();
const URL = pathToFileURL(path.join(HERE, 'index.html')).href + `?render=1&fps=${FPS}&mb=${MBS}`;
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
const shot = page => page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1920, height: 1080 }, timeout: 180000 });

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
const N = meta.FRAMES, CH = 60;
const SEGDIR = path.join(OUT, `segs_${FPS}fps_mb${MBS}`);
fs.mkdirSync(SEGDIR, { recursive: true });
const segPath = c => path.join(SEGDIR, `seg_${String(c).padStart(4, '0')}.mp4`);
const chunks = [...Array(Math.ceil(N / CH)).keys()];
const todo = chunks.filter(c => !fs.existsSync(segPath(c)));   // resumable: finished chunks are kept
console.log(`rendering ${N} frames @ ${FPS} fps, ${MBS} blur samples, ${WORKERS} workers (${todo.length}/${chunks.length} chunks to do)`);
const t0 = Date.now();
let done = 0;
const total = todo.length * CH;

async function renderChunk(ctx, c) {
  const a = c * CH, b = Math.min(N, a + CH), part = segPath(c) + '.part.mp4';
  const ff = spawn(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-r', String(FPS), part], { stdio: ['pipe', 'inherit', 'inherit'] });
  const closed = new Promise(r => ff.on('close', r));
  try {
    for (let i = a; i < b; i++) {
      await ctx.page.evaluate(n => window.renderFrame(n), i);
      const buf = await ctx.page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1920, height: 1080 }, timeout: 180000 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
  } catch (e) { ff.stdin.destroy(); ff.kill(); await closed; throw e; }
  ff.stdin.end();
  const code = await closed;
  if (code !== 0) throw new Error('ffmpeg exited ' + code);
  fs.renameSync(part, segPath(c));
  done += b - a;
  const el = (Date.now() - t0) / 1000;
  console.log(`${done}/${total} frames  ${el.toFixed(0)}s elapsed  eta ${(el / done * (total - done)).toFixed(0)}s`);
}

async function worker() {
  let ctx = await openPage();
  while (todo.length) {
    const c = todo.shift();
    for (let attempt = 1; ; attempt++) {
      try { await renderChunk(ctx, c); break; }
      catch (e) {
        console.error(`chunk ${c} attempt ${attempt} failed: ${e.message.split('\n')[0]}`);
        if (attempt >= 3) throw e;
        await ctx.browser.close().catch(() => {});
        ctx = await openPage();
      }
    }
  }
  await ctx.browser.close();
}

await Promise.all([...Array(WORKERS)].map(worker));
const list = path.join(SEGDIR, 'list.txt');
fs.writeFileSync(list, chunks.map(c => `file '${segPath(c)}'`).join('\n'));
execFileSync(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(OUT, 'video.mp4')]);
console.log(`done in ${((Date.now() - t0) / 1000).toFixed(0)}s -> out/video.mp4 (segments kept in ${path.basename(SEGDIR)}/ for resume)`);
