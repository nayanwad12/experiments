// Render complex-script text (Devanagari etc.) to transparent PNGs with Chromium's shaping (HarfBuzz).
//   node textpng.mjs jobs.json        jobs = [{ "text": "नमस्ते", "out": "work/hi.png", "size": 120, "color": "#fff",
//                                              "weight": 800, "family": "deva" }]
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const deva = pathToFileURL(path.join(HERE, 'node_modules/@fontsource/noto-sans-devanagari/files/noto-sans-devanagari-devanagari-800-normal.woff2')).href;
const inter = pathToFileURL(path.join(HERE, '../fonts/InterTight-900.ttf')).href;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 2400, height: 600 } });
for (const j of jobs) {
  const fam = j.family === 'latin' ? "'IT'" : "'deva', 'IT'";
  await page.setContent(`<html><head><style>
    @font-face { font-family: 'deva'; src: url('${deva}'); }
    @font-face { font-family: 'IT'; src: url('${inter}'); }
    html,body{margin:0;background:transparent}
    #t{display:inline-block;padding:${Math.round(j.size * 0.25)}px ${Math.round(j.size * 0.15)}px;font-family:${fam};font-weight:${j.weight || 800};
       font-size:${j.size}px;color:${j.color || '#fff'};white-space:nowrap;line-height:1.25}
  </style></head><body><span id="t">${j.text}</span></body></html>`);
  await page.evaluate(() => document.fonts.ready);
  const el = await page.$('#t');
  fs.mkdirSync(path.dirname(path.resolve(j.out)), { recursive: true });
  await el.screenshot({ path: j.out, omitBackground: true });
  console.log('->', j.out);
}
await browser.close();
