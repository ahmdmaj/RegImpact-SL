const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const USER_DATA_DIR = 'C:\\Users\\HP\\AppData\\Local\\Temp\\edge_cdp_uat_5_4_' + Date.now();
const PORT = 9232;
const EVIDENCE_DIR = path.resolve(__dirname, '..', 'docs', 'evidence', 'phase_5_4');

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
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
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    });
    if (res.exceptionDetails) {
      throw new Error(JSON.stringify(res.exceptionDetails));
    }
    return res.result ? res.result.value : undefined;
  }

  async captureScreenshot(filePath) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(filePath, Buffer.from(res.data, 'base64'));
    console.log(`Saved screenshot: ${filePath}`);
  }
}

async function runUAT() {
  if (!fs.existsSync(EVIDENCE_DIR)) {
    fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
  }

  console.log('Launching Microsoft Edge headless...');
  const edgeProc = spawn(EDGE_PATH, [
    `--remote-debugging-port=${PORT}`,
    '--headless=new',
    '--disable-gpu',
    `--user-data-dir=${USER_DATA_DIR}`,
    '--window-size=1280,950',
    'about:blank'
  ]);

  edgeProc.stderr.on('data', d => {});
  
  let connected = false;
  let pageWsUrl = '';
  for (let i = 0; i < 20; i++) {
    await wait(500);
    try {
      const list = await getJson(`http://127.0.0.1:${PORT}/json/list`);
      if (list && list.length > 0 && list[0].webSocketDebuggerUrl) {
        pageWsUrl = list[0].webSocketDebuggerUrl;
        connected = true;
        break;
      }
    } catch (e) {}
  }

  if (!connected) {
    throw new Error('Failed to connect to Edge CDP endpoint.');
  }

  console.log('Connected to CDP. Connecting WebSocket:', pageWsUrl);
  const client = new CDPClient(pageWsUrl);
  await client.ready();
  await client.send('Page.enable');
  await client.send('Runtime.enable');
  await client.send('DOM.enable');

  try {
    // -------------------------------------------------------------
    // STAGE 1: SME Portal Landing & Role Verification
    // -------------------------------------------------------------
    console.log('Navigating to http://localhost:3000 as SME user...');
    await client.send('Page.navigate', { url: 'http://localhost:3000' });
    await wait(3000);

    // Set role to sme_user
    await client.eval(`
      localStorage.setItem('user_role', 'sme_user');
      localStorage.setItem('regimpact:role', 'sme_user');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(1000);

    const s1Path = path.join(EVIDENCE_DIR, '01_sme_landing_page.png');
    await client.captureScreenshot(s1Path);

    // -------------------------------------------------------------
    // STAGE 2: SME Business Profile Entry
    // -------------------------------------------------------------
    console.log('Selecting Retail Preset scenario...');
    await client.eval(`
      // Find preset button for retail or click it
      const buttons = Array.from(document.querySelectorAll('button'));
      const retailBtn = buttons.find(b => b.textContent && b.textContent.includes('Retail Packaged Food'));
      if (retailBtn) {
        retailBtn.click();
      }
    `);
    await wait(1000);

    const s2Path = path.join(EVIDENCE_DIR, '02_sme_profile_entry.png');
    await client.captureScreenshot(s2Path);

    // -------------------------------------------------------------
    // STAGE 3: Run Regulatory Assessment
    // -------------------------------------------------------------
    console.log('Triggering Regulatory Assessment...');
    await client.eval(`
      const buttons = Array.from(document.querySelectorAll('button'));
      const runBtn = buttons.find(b => b.textContent && (b.textContent.includes('Run Regulatory Assessment') || b.textContent.includes('Analyze Impact')));
      if (runBtn) {
        runBtn.click();
      }
    `);

    // Wait for analysis result to appear (poll up to 15 seconds)
    console.log('Waiting for assessment results...');
    let resultAppeared = false;
    for (let i = 0; i < 30; i++) {
      await wait(1000);
      const hasReport = await client.eval(`
        Boolean(document.querySelector('.shadow-xl') || document.body.textContent.includes('Applicable Requirements') || document.body.textContent.includes('Total Rules Evaluated'))
      `);
      if (hasReport) {
        resultAppeared = true;
        console.log(`Assessment results arrived at ${i + 1}s`);
        break;
      }
    }

    await wait(2000);
    const s3Path = path.join(EVIDENCE_DIR, '03_sme_assessment_results.png');
    await client.captureScreenshot(s3Path);

    // -------------------------------------------------------------
    // STAGE 4: Inspect Applicable Rule & Evidence
    // -------------------------------------------------------------
    console.log('Inspecting Applicable Rule Details...');
    await client.eval(`
      // Click on applicable rule card or expand details
      const cards = Array.from(document.querySelectorAll('[data-testid="rule-card"], .cursor-pointer, details, summary'));
      const reg3Card = cards.find(c => c.textContent && (c.textContent.includes('RULE-FCAU-2494-47-REG-3') || c.textContent.includes('Regulation 3')));
      if (reg3Card) reg3Card.click();
    `);
    await wait(1500);

    const s4Path = path.join(EVIDENCE_DIR, '04_sme_applicable_rule_details.png');
    await client.captureScreenshot(s4Path);

    // -------------------------------------------------------------
    // STAGE 5: Inspect Coverage Gaps & Exemptions
    // -------------------------------------------------------------
    console.log('Scrolling to and inspecting Coverage Gaps and Non-Applicable Rules...');
    await client.eval(`
      window.scrollBy(0, 600);
    `);
    await wait(1000);

    const s5Path = path.join(EVIDENCE_DIR, '05_sme_coverage_gaps.png');
    await client.captureScreenshot(s5Path);

    // -------------------------------------------------------------
    // STAGE 6: Reviewer Queue Inspection (/admin/reviews)
    // -------------------------------------------------------------
    console.log('Switching to Reviewer role and navigating to /admin/reviews...');
    await client.eval(`
      localStorage.setItem('user_role', 'reviewer');
      localStorage.setItem('regimpact:role', 'reviewer');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(500);

    await client.send('Page.navigate', { url: 'http://localhost:3000/admin/reviews' });
    await wait(3000);

    const s6Path = path.join(EVIDENCE_DIR, '06_reviewer_candidate_queue.png');
    await client.captureScreenshot(s6Path);

    // -------------------------------------------------------------
    // STAGE 7: Reviewer Rule Inspection Modal / Drawer
    // -------------------------------------------------------------
    console.log('Opening Reviewer inspection for first candidate...');
    await client.eval(`
      const buttons = Array.from(document.querySelectorAll('button'));
      const reviewBtn = buttons.find(b => b.textContent && b.textContent.trim().includes('Review Rule'));
      if (reviewBtn) reviewBtn.click();
    `);
    await wait(1500);

    const s7Path = path.join(EVIDENCE_DIR, '07_reviewer_rule_inspection.png');
    await client.captureScreenshot(s7Path);

    // -------------------------------------------------------------
    // STAGE 8: Benchmark & Evaluation Dashboard (/evaluation)
    // -------------------------------------------------------------
    console.log('Navigating to /evaluation dashboard as admin...');
    await client.eval(`
      localStorage.setItem('user_role', 'admin');
      localStorage.setItem('regimpact:role', 'admin');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(500);

    await client.send('Page.navigate', { url: 'http://localhost:3000/evaluation' });
    await wait(3000);

    const s8Path = path.join(EVIDENCE_DIR, '08_admin_system_dashboard.png');
    await client.captureScreenshot(s8Path);

    // -------------------------------------------------------------
    // STAGE 9: Admin Document Inventory & Regulations Catalog
    // -------------------------------------------------------------
    console.log('Navigating back to main Admin page to inspect catalog & document inventory...');
    await client.send('Page.navigate', { url: 'http://localhost:3000' });
    await wait(2500);

    await client.eval(`
      window.scrollBy(0, 300);
    `);
    await wait(1000);

    const s9Path = path.join(EVIDENCE_DIR, '09_admin_document_inventory.png');
    await client.captureScreenshot(s9Path);

    console.log('All 9 acceptance screenshots captured successfully!');

  } catch (err) {
    console.error('UAT error:', err);
  } finally {
    edgeProc.kill();
    console.log('Edge process stopped.');
  }
}

runUAT().catch(console.error);
