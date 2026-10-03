// Transparent 1080x1920 PNG with the top caption, overlaid on the render by build.sh (out/caption.png).
//   node caption.mjs "Claude cooked 😮‍💨"
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
let chromium;
try { ({ chromium } = await import('playwright')); }
catch { ({ chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs')); }
const HERE = path.dirname(fileURLToPath(import.meta.url));
const text = process.argv[2] || 'Claude cooked 😮‍💨';
const font = '../fonts/InterTight-VF.ttf';
const html = `<html><head><style>
@font-face { font-family: IT; src: url(${font}); font-weight: 100 900; }
html, body { margin: 0; background: transparent; width: 1080px; height: 1920px; }
div { position: absolute; top: 470px; width: 100%; text-align: center; color: #fff;
  font: 700 62px IT, "Noto Color Emoji"; letter-spacing: -0.5px; text-shadow: 0 2px 18px rgba(0,0,0,.55); }
</style></head><body><div></div></body></html>`;
const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
const tmp = path.join(HERE, 'out/caption.html');
fs.writeFileSync(tmp, html);
await p.goto(pathToFileURL(tmp).href);
await p.evaluate(t => { document.querySelector('div').textContent = t; return document.fonts.ready; }, text);
await p.screenshot({ path: path.join(HERE, 'out/caption.png'), omitBackground: true });
await b.close();
console.log('-> out/caption.png');
