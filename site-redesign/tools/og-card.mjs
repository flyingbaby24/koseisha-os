// Renders og-card.html to docs/assets/img/og-jinn-project.jpg.
// Run from the repository root with Playwright available: node site-redesign/tools/og-card.mjs
import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await page.goto(pathToFileURL(path.join(here, 'og-card.html')).href);
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: path.join(here, '../../docs/assets/img/og-jinn-project.jpg'), type: 'jpeg', quality: 86 });
await browser.close();
