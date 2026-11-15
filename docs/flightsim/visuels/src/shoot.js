const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await p.goto('file://' + process.cwd() + '/visuals.html');
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(500);
  for (const id of ['hero','statics','gsx','safety']) {
    await p.locator('#' + id).screenshot({ path: `out/${id}.png` });
  }
  await b.close();
})();
