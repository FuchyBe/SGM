const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 2560, height: 1440 } });
  await p.goto('file://' + process.cwd() + '/annotated.html');
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(400);
  await p.locator('#guide').screenshot({ path: 'out/interface.png' });
  await b.close();
})();
