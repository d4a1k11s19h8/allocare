const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  // Set viewport
  await page.setViewport({ width: 1280, height: 800 });
  
  // Go to mock server
  await page.goto('http://localhost:8001');
  await new Promise(r => setTimeout(r, 1000));
  
  // Login
  await page.type('#login-email', 'superadmin@allocare.org');
  await page.type('#login-password', 'super123');
  await page.keyboard.press('Enter');
  
  // Wait for redirect to api-monitor
  await page.waitForSelector('#view-api-monitor.active', { timeout: 5000 });
  await new Promise(r => setTimeout(r, 1500));
  
  // Screenshot
  await page.screenshot({ path: '../api_monitor_test.png' });
  
  await browser.close();
})();
