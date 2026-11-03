const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const USER_DATA_DIR = 'C:\\Users\\HP\\AppData\\Local\\Temp\\edge_click_' + Date.now();
const PORT = 9241;
const EVIDENCE_DIR = path.resolve(__dirname, '../docs/evidence/phase_5_4');

function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.callbacks = new Map();
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    };
  }
  ready() {
    return new Promise((resolve, reject) => {
      if (this.ws.readyState === WebSocket.OPEN) return resolve();
      this.ws.onopen = () => resolve();
      this.ws.onerror = (e) => reject(e);
    });
  }
  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async eval(expression) {
    const res = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    return res.result ? res.result.value : undefined;
  }
  async captureScreenshot(filename) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    const fullPath = path.join(EVIDENCE_DIR, filename);
    fs.writeFileSync(fullPath, Buffer.from(res.data, 'base64'));
    console.log(`[SCREENSHOT] Saved: ${filename}`);
    return fullPath;
  }
}

async function run() {
  const edge = spawn(EDGE_PATH, ['--headless=new', '--disable-gpu', `--remote-debugging-port=${PORT}`, `--user-data-dir=${USER_DATA_DIR}`, 'about:blank']);
  await wait(1500);
  const targets = await getJson(`http://127.0.0.1:${PORT}/json/list`);
  const pageTarget = targets.find(t => t.type === 'page') || targets[0];
  const cdp = new CDPClient(pageTarget.webSocketDebuggerUrl);
  await cdp.ready();
  await cdp.send('Page.enable');
  await cdp.send('DOM.enable');
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });

  await cdp.send('Page.navigate', { url: 'http://localhost:3000' });
  await wait(3000);

  // Switch role to SME
  await cdp.eval(`(() => {
    localStorage.setItem('user_role', 'sme_user');
    localStorage.setItem('regimpact_user_role', 'sme_user');
    localStorage.setItem('regimpact:role', 'sme_user');
    window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'sme_user' } }));
  })()`);
  await wait(1000);
  await cdp.captureScreenshot('01_sme_landing_page.png');

  // Click retail preset
  await cdp.eval(`(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find(x => x.innerText.includes('Retail Packaged Food'));
    if (b) b.click();
  })()`);
  await wait(1000);
  await cdp.captureScreenshot('02_sme_profile_entry.png');

  // Click 'Analyze Regulatory Impact'
  console.log('Clicking Analyze Regulatory Impact...');
  const clicked = await cdp.eval(`(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find(x => x.innerText.includes('Analyze Regulatory Impact'));
    if (b) {
      b.click();
      return true;
    }
    return false;
  })()`);
  console.log('Clicked button:', clicked);

  // Wait for results
  console.log('Waiting for results to load...');
  for (let i = 0; i < 25; i++) {
    await wait(1000);
    const bodyText = await cdp.eval(`document.body.innerText`);
    if (bodyText.includes('TOTAL RULES EVALUATED') || bodyText.includes('Applicable Requirements') || bodyText.includes('Action Checklist') || bodyText.includes('Structured Impact Report')) {
      console.log(`Results appeared at ${i + 1}s!`);
      break;
    }
  }

  await wait(2000);
  // Scroll to results section
  await cdp.eval(`(() => {
    window.scrollBy(0, 500);
  })()`);
  await wait(1000);
  await cdp.captureScreenshot('03_sme_assessment_results.png');

  // Scroll down more to see applicable requirement details
  await cdp.eval(`(() => {
    window.scrollBy(0, 500);
  })()`);
  await wait(1000);
  await cdp.captureScreenshot('04_sme_applicable_rule_details.png');

  // Scroll down to see coverage gaps & exemptions
  await cdp.eval(`(() => {
    window.scrollBy(0, 600);
  })()`);
  await wait(1000);
  await cdp.captureScreenshot('05_sme_coverage_gaps.png');

  edge.kill();
  console.log('Finished capturing SME flow screenshots!');
}

run().catch(console.error);
