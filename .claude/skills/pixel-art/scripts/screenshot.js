// Render a scene once in headless Chromium, save a PNG and report JS errors.
// Usage: NODE_PATH=$(npm root -g) node screenshot.js <file.html> <out.png> [waitMs=4000] [selector=#stage]
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const [file, out = 'shot.png', wait = '4000', sel = '#stage'] = process.argv.slice(2);
  if (!file) { console.error('usage: node screenshot.js <file.html> <out.png> [waitMs] [selector]'); process.exit(2); }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/CERT|fonts\.g/.test(m.text())) errors.push(m.text()); });
  await page.goto('file://' + path.resolve(file));
  await page.waitForTimeout(Number(wait));
  const target = (await page.$(sel)) ? page.locator(sel) : page;
  await target.screenshot({ path: out });
  console.log(errors.length ? 'errors:\n' + errors.join('\n') : 'no errors');
  await browser.close();
})();
