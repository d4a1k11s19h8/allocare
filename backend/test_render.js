const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  // Set viewport
  await page.setViewport({ width: 1280, height: 800 });
  
  console.log("Navigating to URL...");
  await page.goto('https://allocare-backend.onrender.com/');
  await new Promise(r => setTimeout(r, 2000));
  
  // Login
  console.log("Logging in...");
  await page.type('#login-email', 'superadmin@allocare.org');
  await page.type('#login-password', 'super123');
  await page.keyboard.press('Enter');
  
  // Wait for redirect to api-monitor
  console.log("Waiting for dashboard...");
  try {
    await page.waitForSelector('#view-api-monitor.active', { timeout: 10000 });
    await new Promise(r => setTimeout(r, 2000)); // wait for fetch
  } catch(e) {
    console.log("Dashboard didn't load or timeout");
  }
  
  await page.screenshot({ path: '../render_api_monitor.png' });
  console.log("Screenshot taken.");
  
  await browser.close();
})();
