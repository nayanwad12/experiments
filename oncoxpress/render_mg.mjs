// Render mg.html to transparent PNG frames (24 fps) for every frame that has motion graphics.
//   node render_mg.mjs                  -> work/mg/f00000.png ...
//   node render_mg.mjs --stills 40,47.5 -> work/stills/mg_40.00.png
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
let chromium;
try { ({ chromium } = await import('playwright')); } catch { ({ chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs')); }
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const FPS = 24, WORKERS = +opt('workers', 4), STILLS = opt('stills', null), ONLY = opt('only', null);
const URL = pathToFileURL(path.join(HERE, 'mg.html')).href;

async function open() {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.goto(URL); await page.evaluate(() => window.READY);
  return { browser, page };
}
const shot = p => p.screenshot({ type: 'png', omitBackground: true, timeout: 120000 });

if (STILLS) {
  const dir = path.join(HERE, 'work', 'stills'); fs.mkdirSync(dir, { recursive: true });
  const { browser, page } = await open();
  for (const s of STILLS.split(',').map(Number)) {
    await page.evaluate(i => window.renderFrame(i), Math.round(s * FPS));
    fs.writeFileSync(path.join(dir, `mg_${s.toFixed(2)}.png`), await shot(page));
  }
  await browser.close(); process.exit(0);
}
const { browser: b0, page: p0 } = await open();
const SC = await p0.evaluate(() => window.META.SC); await b0.close();
const frames = new Set();
for (const [id, [a, b]] of Object.entries(SC)) {
  if (ONLY && !ONLY.split(',').includes(id)) continue;
  for (let f = Math.floor(a * FPS); f <= Math.ceil(b * FPS); f++) frames.add(f);
}
const list = [...frames].sort((a, b) => a - b);
const dir = path.join(HERE, 'work', 'mg'); fs.mkdirSync(dir, { recursive: true });
const todo = list.filter(f => !fs.existsSync(path.join(dir, `f${String(f).padStart(5, '0')}.png`)) || args.includes('--force'));
console.log('frames', list.length, 'todo', todo.length);
let done = 0;
await Promise.all([...Array(WORKERS).keys()].map(async w => {
  const { browser, page } = await open();
  for (let i = w; i < todo.length; i += WORKERS) {
    const f = todo[i];
    await page.evaluate(i => window.renderFrame(i), f);
    fs.writeFileSync(path.join(dir, `f${String(f).padStart(5, '0')}.png`), await shot(page));
    if (++done % 100 === 0) console.log(done);
  }
  await browser.close();
}));
console.log('done');
