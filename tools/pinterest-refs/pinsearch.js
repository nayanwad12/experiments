// Collect Pinterest pins as style references (mood, palette, composition).
// They're for study only. Never ship them as assets.
//
// usage: node pinsearch.js "<search terms or pinterest.com URL>" <outdir> [count]
const { chromium } = require('playwright-core');
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');

const CHROME = process.env.CHROME_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

(async () => {
  const [q, out, n = '12'] = process.argv.slice(2);
  if (!q || !out) { console.error('usage: node pinsearch.js "<query|url>" <outdir> [count]'); process.exit(2); }
  const url = /^https?:\/\//.test(q) ? q : 'https://www.pinterest.com/search/pins/?q=' + encodeURIComponent(q);
  fs.mkdirSync(out, { recursive: true });

  const browser = await chromium.launch({ executablePath: CHROME });
  const page = await browser.newPage({ viewport: { width: 1400, height: 2000 } });
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(6000);
  await page.mouse.wheel(0, 3000);
  await page.waitForTimeout(2500);

  const imgs = await page.$$eval('img[src*="i.pinimg.com"]', els => els.map(i => ({ src: i.src, alt: i.alt })));
  await page.screenshot({ path: path.join(out, '_grid.png') });
  await browser.close();

  // Thumbnails are /236x/; the /736x/ size is the same image at a usable resolution.
  const seen = new Set(), pins = [];
  for (const p of imgs) {
    if (!/\/\d+x\//.test(p.src)) continue;
    const src = p.src.replace(/\/\d+x\//, '/736x/');
    if (!seen.has(src)) { seen.add(src); pins.push({ ...p, src }); }
  }
  const list = pins.slice(0, +n);
  for (const [i, p] of list.entries()) {
    p.file = `${String(i + 1).padStart(2, '0')}.jpg`;
    try { execFileSync('curl', ['-sSf', '--max-time', '20', '-o', path.join(out, p.file), p.src]); }
    catch { p.file = null; }
  }
  fs.writeFileSync(path.join(out, 'pins.json'), JSON.stringify({ query: q, url, pins: list }, null, 2));
  console.log(`${imgs.length} images on page, saved ${list.filter(p => p.file).length} to ${out}`);
})().catch(e => { console.error(e.message); process.exit(1); });
