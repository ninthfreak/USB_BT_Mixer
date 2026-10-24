// Screenshots each figure of the guide in both themes so the output can be
// checked by eye. A figure that generates cleanly can still be cropped.
const { chromium } = require('playwright');
const path = require('path');
const GUIDE = 'file://' + path.resolve(__dirname, '../wiring-guide.html');
const OUT = process.argv[2] || '/tmp';
(async () => {
  const b = await chromium.launch();
  for (const theme of ['light', 'dark']) {
    const pg = await b.newPage({ viewport: { width: 880, height: 1100 } });
    await pg.goto(GUIDE);
    await pg.evaluate(t => document.documentElement.setAttribute('data-theme', t), theme);
    await pg.waitForTimeout(250);
    const n = await pg.locator('figure').count();
    for (let i = 0; i < n; i++) {
      const fig = pg.locator('figure').nth(i);
      await fig.scrollIntoViewIfNeeded();
      await fig.screenshot({ path: `${OUT}/fig_${theme}_${i + 1}.png` });
    }
    await pg.close();
  }
  await b.close();
  console.log('wrote figures to ' + OUT);
})();
