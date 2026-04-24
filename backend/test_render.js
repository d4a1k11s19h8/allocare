const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  // Capture console messages
  page.on('console', msg => {
    console.log('BROWSER CONSOLE:', msg.type().toUpperCase(), msg.text());
  });

  page.on('pageerror', err => {
    console.log('BROWSER ERROR:', err.toString());
  });
  
  // Set viewport
  await page.setViewport({ width: 1280, height: 800 });
  
  console.log("Navigating to URL...");
  await page.goto('https://allocare-backend.onrender.com/');
  await new Promise(r => setTimeout(r, 2000));
  
  await page.screenshot({ path: 'render_home.png' });
  console.log("Screenshot taken.");
  
  await browser.close();
})();
