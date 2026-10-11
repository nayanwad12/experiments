// Render scene.html frame by frame with headless Chromium into a transparent overlay (.mov, PNG codec, RGBA).
//   NODE_PATH=$(npm root -g) node render.cjs scene.html --w 1920 --h 1080 --fps 24 --dur 40 -o work/overlay.mov
//   add --at 12.5 --still work/still.png to grab a single frame for checking
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const path = require('node:path');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const html = path.resolve(args[0] || 'scene.html');
const W = +opt('w', 1920), H = +opt('h', 1080), FPS = +opt('fps', 24), DUR = +opt('dur', 40);
const out = path.resolve(opt('o', null) || args[args.indexOf('-o') + 1]);

(async () => {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto('file://' + html);
  await page.waitForFunction(() => typeof window.renderFrame === 'function');
  await page.evaluate(async () => { await window.ready; await document.fonts.ready; });
  await page.evaluate(() => Promise.all([...document.querySelectorAll('img')].map(i => i.decode())));
  const stills = opt('stills', null);
  if (stills) {       // comma-separated times -> PNGs next to -o
    for (const t of stills.split(',').map(Number)) {
      await page.evaluate(t => window.renderFrame(t), t);
      await page.waitForTimeout(30);
      await page.screenshot({ path: out.replace(/\.png$/, '') + `_${t.toFixed(2)}.png`, omitBackground: true });
    }
    await browser.close();
    return;
  }
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'png', '-r', String(FPS), '-i', '-',
    '-c:v', 'png', '-pix_fmt', 'rgba', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n = Math.round(DUR * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.renderFrame(t), i / FPS);
    const buf = await page.screenshot({ type: 'png', omitBackground: true });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % FPS === 0) process.stdout.write(`\r  frame ${i}/${n}`);
  }
  ff.stdin.end();
  await browser.close();
  await new Promise(r => ff.on('close', r));
  console.log(`\n  done -> ${out}`);
})();
