const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const USER_DATA_DIR = 'C:\\Users\\HP\\AppData\\Local\\Temp\\edge_cdp_final_ui_' + Date.now();
const PORT = 9248;
const EVIDENCE_DIR = path.resolve(__dirname, '../docs/evidence/final_ui');

if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
}

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

  async navigate(url) {
    await this.send('Page.navigate', { url });
    await wait(2500);
  }

  async captureScreenshot(filename) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    const fullPath = path.join(EVIDENCE_DIR, filename);
    fs.writeFileSync(fullPath, Buffer.from(res.data, 'base64'));
    console.log(`[SCREENSHOT] Saved: ${filename}`);
    return fullPath;
  }
}

async function captureAll() {
  console.log('=== STARTING FINAL UI REFINEMENT EVIDENCE CAPTURE ===');

  const edge = spawn(EDGE_PATH, [
    '--headless=new',
    '--disable-gpu',
    '--remote-debugging-port=' + PORT,
    '--user-data-dir=' + USER_DATA_DIR,
    '--window-size=1440,960',
    'about:blank',
  ]);

  let targets = null;
  for (let i = 0; i < 25; i++) {
    await wait(400);
    try {
      targets = await getJson(`http://127.0.0.1:${PORT}/json/list`);
      if (targets && targets.length > 0) break;
    } catch (e) {}
  }

  if (!targets || targets.length === 0) {
    edge.kill();
    throw new Error('Could not connect to Edge CDP on port ' + PORT);
  }

  const pageTarget = targets.find(t => t.type === 'page') || targets[0];
  console.log('Connected to Page WebSocket:', pageTarget.webSocketDebuggerUrl);
  const cdp = new CDPClient(pageTarget.webSocketDebuggerUrl);
  await cdp.ready();
  await cdp.send('Page.enable');
  await cdp.send('DOM.enable');

  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 960,
    deviceScaleFactor: 1,
    mobile: false,
  });

  try {
    // -------------------------------------------------------------
    // SCREENSHOT 01: SME Landing Page
    // -------------------------------------------------------------
    console.log('\n--- 1. Capturing 01_sme_landing_page.png ---');
    await cdp.navigate('http://localhost:3000/');
    await cdp.eval(`(() => {
      localStorage.setItem('user_role', 'sme_user');
      localStorage.setItem('regimpact_user_role', 'sme_user');
      localStorage.setItem('regimpact:role', 'sme_user');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'sme_user' } }));
    })()`);
    await wait(1500);
    await cdp.captureScreenshot('01_sme_landing_page.png');

    // -------------------------------------------------------------
    // SCREENSHOT 02: SME Business Profile Entry
    // -------------------------------------------------------------
    console.log('\n--- 2. Capturing 02_sme_business_profile.png ---');
    await cdp.eval(`(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const presetBtn = buttons.find(b => b.textContent && (b.textContent.includes('Retail Packaged Food') || b.textContent.includes('FMCG Food Manufacturer')));
      if (presetBtn) presetBtn.click();
    })()`);
    await wait(1500);
    await cdp.captureScreenshot('02_sme_business_profile.png');

    // -------------------------------------------------------------
    // SCREENSHOT 03: SME Analysis Results
    // -------------------------------------------------------------
    console.log('\n--- 3. Capturing 03_sme_analysis_results.png ---');
    await cdp.eval(`(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const analyzeBtn = buttons.find(b => b.textContent && (b.textContent.includes('Analyze Regulatory Impact') || b.textContent.includes('Run Regulatory Assessment')));
      if (analyzeBtn) analyzeBtn.click();
    })()`);

    console.log('Waiting for analysis response...');
    for (let i = 0; i < 25; i++) {
      await wait(1000);
      const isDone = await cdp.eval(`(() => {
        return Boolean(document.body.innerText.includes('Executive Compliance Summary') || document.body.innerText.includes('Action Plan'));
      })()`);
      if (isDone) {
        console.log(`Analysis complete in ${i + 1}s.`);
        break;
      }
    }
    await wait(2000);
    await cdp.captureScreenshot('03_sme_analysis_results.png');

    // -------------------------------------------------------------
    // SCREENSHOT 04: Citations & Mandatory Obligation Details
    // -------------------------------------------------------------
    console.log('\n--- 4. Capturing 04_applicable_rule_details.png ---');
    await cdp.eval(`(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const citTab = buttons.find(b => b.textContent && b.textContent.includes('Citations'));
      if (citTab) citTab.click();
    })()`);
    await wait(1500);

    // Expand the first citation card and technical audit accordion
    await cdp.eval(`(() => {
      const cardButtons = Array.from(document.querySelectorAll('button'));
      const techBtn = cardButtons.find(b => b.textContent && b.textContent.includes('Inspect Technical Audit Data'));
      if (techBtn) techBtn.click();
    })()`);
    await wait(1000);
    await cdp.captureScreenshot('04_applicable_rule_details.png');

    // -------------------------------------------------------------
    // SCREENSHOT 05: Coverage Gaps Filtered Citations
    // -------------------------------------------------------------
    console.log('\n--- 5. Capturing 05_coverage_gaps.png ---');
    await cdp.eval(`(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const gapFilterBtn = buttons.find(b => b.textContent && b.textContent.includes('Coverage Gaps'));
      if (gapFilterBtn) gapFilterBtn.click();
    })()`);
    await wait(1500);

    // Expand the first coverage gap card if not expanded
    await cdp.eval(`(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const firstCardHeader = buttons.find(b => b.textContent && b.textContent.includes('COVERAGE GAP'));
      if (firstCardHeader) firstCardHeader.click();
    })()`);
    await wait(1000);
    await cdp.captureScreenshot('05_coverage_gaps.png');

    // -------------------------------------------------------------
    // SCREENSHOT 06: Reviewer Candidate Queue
    // -------------------------------------------------------------
    console.log('\n--- 6. Capturing 06_reviewer_candidate_queue.png ---');
    await cdp.eval(`(() => {
      localStorage.setItem('user_role', 'reviewer');
      localStorage.setItem('regimpact_user_role', 'reviewer');
      localStorage.setItem('regimpact:role', 'reviewer');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'reviewer' } }));
    })()`);
    await wait(500);
    await cdp.navigate('http://localhost:3000/admin/reviews');
    await wait(2500);
    await cdp.captureScreenshot('06_reviewer_candidate_queue.png');

    // -------------------------------------------------------------
    // SCREENSHOT 07: Reviewer Rule Inspection (Side-by-Side Grid)
    // -------------------------------------------------------------
    console.log('\n--- 7. Capturing 07_reviewer_rule_inspection.png ---');
    await cdp.eval(`(() => {
      window.scrollBy(0, 150);
    })()`);
    await wait(1000);
    await cdp.captureScreenshot('07_reviewer_rule_inspection.png');

    // -------------------------------------------------------------
    // SCREENSHOT 08: Admin System Dashboard
    // -------------------------------------------------------------
    console.log('\n--- 8. Capturing 08_admin_dashboard.png ---');
    await cdp.eval(`(() => {
      localStorage.setItem('user_role', 'admin');
      localStorage.setItem('regimpact_user_role', 'admin');
      localStorage.setItem('regimpact:role', 'admin');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'admin' } }));
    })()`);
    await wait(500);
    await cdp.navigate('http://localhost:3000/');
    await wait(2500);
    await cdp.captureScreenshot('08_admin_dashboard.png');

    // -------------------------------------------------------------
    // SCREENSHOT 09: Admin Document Ingestion Portal
    // -------------------------------------------------------------
    console.log('\n--- 9. Capturing 09_admin_document_inventory.png ---');
    await cdp.navigate('http://localhost:3000/admin/reviews');
    await wait(2000);
    await cdp.eval(`(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const uploadTab = buttons.find(b => b.textContent && b.textContent.includes('Ingest Document'));
      if (uploadTab) uploadTab.click();
    })()`);
    await wait(1500);
    await cdp.captureScreenshot('09_admin_document_inventory.png');

    // -------------------------------------------------------------
    // SCREENSHOT 10: Evaluation Dashboard
    // -------------------------------------------------------------
    console.log('\n--- 10. Capturing 10_evaluation_dashboard.png ---');
    await cdp.navigate('http://localhost:3000/evaluation');
    await wait(3000);
    await cdp.captureScreenshot('10_evaluation_dashboard.png');

    console.log('\n=== ALL 10 SCREENSHOTS CAPTURED SUCCESSFULLY! ===');
  } catch (err) {
    console.error('Error during capture:', err);
  } finally {
    edge.kill();
    console.log('Edge process terminated.');
  }
}

captureAll().catch(console.error);
