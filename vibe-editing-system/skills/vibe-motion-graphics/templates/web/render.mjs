// Render an HTML scene frame-by-frame with headless Chromium (Playwright) and pipe it into ffmpeg.
//   npm i playwright && npx playwright install chromium      (once)
//   node web/render.mjs web/scene.html --w 1080 --h 1920 --fps 30 --dur 6 -o out/web.mp4 [--audio work/mix.wav]
// The page must define window.renderFrame(t). Use it for WebGL shaders, CSS/SVG/HTML layouts, or JS libraries
// (GSAP, Three.js, Lottie). Every frame is a pure function of t, so renders are deterministic.
import { chromium } from 'playwright';
import { spawn, execSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const html = path.resolve(args[0] || 'scene.html');
const W = +opt('w', 1080), H = +opt('h', 1920), FPS = +opt('fps', 30), DUR = +opt('dur', 6);
const out = path.resolve(args.includes('-o') ? args[args.indexOf('-o') + 1] : 'out/web.mp4');
const audio = opt('audio', null);
let ffmpeg = 'ffmpeg';
try { execSync('ffmpeg -version', { stdio: 'ignore' }); }
catch { ffmpeg = execSync(`python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"`).toString().trim(); }
fs.mkdirSync(path.dirname(out), { recursive: true });

const ffArgs = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'png', '-r', String(FPS), '-i', '-'];
if (audio) ffArgs.push('-i', audio, '-c:a', 'aac', '-b:a', '192k', '-shortest');
ffArgs.push('-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out);
const ff = spawn(ffmpeg, ffArgs, { stdio: ['pipe', 'inherit', 'inherit'] });

const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.goto(`file://${html}?render=1&w=${W}&h=${H}`);
await page.waitForFunction(() => typeof window.renderFrame === 'function');
await page.evaluate(async () => { if (window.ready) await window.ready; if (document.fonts) await document.fonts.ready; });
const n = Math.round(DUR * FPS);
for (let i = 0; i < n; i++) {
  await page.evaluate(t => window.renderFrame(t), i / FPS);
  const buf = await page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: W, height: H } });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % FPS === 0) process.stdout.write(`\r  frame ${i}/${n}`);
}
ff.stdin.end();
await browser.close();
await new Promise(r => ff.on('close', r));
console.log(`\ndone -> ${out}`);
