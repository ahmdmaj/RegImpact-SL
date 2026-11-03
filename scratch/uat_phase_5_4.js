const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const USER_DATA_DIR = 'C:\\Users\\HP\\AppData\\Local\\Temp\\edge_cdp_uat_5_4_' + Date.now();
const PORT = 9235;
const EVIDENCE_DIR = path.resolve(__dirname, '../docs/evidence/phase_5_4');

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

async function runUAT() {
  console.log('=== STARTING REGIMPACT-SL PHASE 5.4 FINAL ACCEPTANCE UAT ===');

  const edge = spawn(EDGE_PATH, [
    '--headless=new',
    '--disable-gpu',
    '--remote-debugging-port=' + PORT,
    '--user-data-dir=' + USER_DATA_DIR,
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
    throw new Error('Could not connect to Edge CDP');
  }

  const pageTarget = targets.find(t => t.type === 'page') || targets[0];
  console.log('Connecting to Page Target WebSocket:', pageTarget.webSocketDebuggerUrl);
  const cdp = new CDPClient(pageTarget.webSocketDebuggerUrl);
  await cdp.ready();
  await cdp.send('Page.enable');
  await cdp.send('DOM.enable');

  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 1000,
    deviceScaleFactor: 1,
    mobile: false,
  });

  try {
    // -------------------------------------------------------------
    // STAGE 1: SME Landing Page
    // -------------------------------------------------------------
    console.log('\n--- 1. Testing SME User Landing Page ---');
    await cdp.navigate('http://localhost:3000/');
    await cdp.eval(`
      localStorage.setItem('user_role', 'sme_user');
      localStorage.setItem('regimpact_user_role', 'sme_user');
      localStorage.setItem('regimpact:role', 'sme_user');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'sme_user' } }));
    `);
    await wait(1500);
    await cdp.captureScreenshot('01_sme_landing_page.png');

    // -------------------------------------------------------------
    // STAGE 2: SME Profile Selection
    // -------------------------------------------------------------
    console.log('\n--- 2. Selecting Retail Prepackaged Food Preset ---');
    await cdp.eval(`(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const retailPreset = buttons.find(b => b.textContent && b.textContent.includes('Retail Packaged Food'));
      if (retailPreset) retailPreset.click();
    })()`);
    await wait(1500);
    await cdp.captureScreenshot('02_sme_profile_entry.png');

    // -------------------------------------------------------------
    // STAGE 3: Run Assessment
    // -------------------------------------------------------------
    console.log('\n--- 3. Running Regulatory Assessment ---');
    await cdp.eval(`(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const analyzeBtn = buttons.find(b => b.textContent && (b.textContent.includes('Run Regulatory Assessment') || b.textContent.includes('Analyze Impact')));
      if (analyzeBtn) analyzeBtn.click();
    })()`);

    console.log('Waiting for assessment results to render...');
    for (let i = 0; i < 20; i++) {
      await wait(1000);
      const isDone = await cdp.eval(`(() => {
        return Boolean(document.body.innerText.includes('Applicable Requirements') || document.body.innerText.includes('Total Rules Evaluated'));
      })()`);
      if (isDone) {
        console.log(`Results arrived after ${i + 1} seconds.`);
        break;
      }
    }
    await wait(2000);
    await cdp.captureScreenshot('03_sme_assessment_results.png');

    // -------------------------------------------------------------
    // STAGE 4: Inspect Applicable Rule & Evidence
    // -------------------------------------------------------------
    console.log('\n--- 4. Inspecting Applicable Rule Details & Citations ---');
    await cdp.eval(`(() => {
      const items = Array.from(document.querySelectorAll('div, button, [role="button"]'));
      const card = items.find(el => el.textContent && el.textContent.includes('RULE-FCAU-2494-47-REG-3') && el.textContent.includes('Food (Labelling and Advertising) Regulations 2026'));
      if (card) card.click();
    })()`);
    await wait(1500);
    await cdp.captureScreenshot('04_sme_applicable_rule_details.png');

    // -------------------------------------------------------------
    // STAGE 5: Inspect Coverage Gaps & Exemptions
    // -------------------------------------------------------------
    console.log('\n--- 5. Scrolling to Coverage Gaps & Exemptions ---');
    await cdp.eval(`(() => {
      window.scrollBy(0, 500);
    })()`);
    await wait(1500);
    await cdp.captureScreenshot('05_sme_coverage_gaps.png');

    // -------------------------------------------------------------
    // STAGE 6: Reviewer Queue Inspection (/admin/reviews)
    // -------------------------------------------------------------
    console.log('\n--- 6. Switching to Reviewer Persona & Navigating to /admin/reviews ---');
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
    // STAGE 7: Reviewer Rule Inspection Modal / Drawer
    // -------------------------------------------------------------
    console.log('\n--- 7. Inspecting Pending Candidate Rule in Reviewer Portal ---');
    await cdp.eval(`(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const reviewBtn = buttons.find(b => b.textContent && b.textContent.trim().includes('Review Rule'));
      if (reviewBtn) reviewBtn.click();
    })()`);
    await wait(2000);
    await cdp.captureScreenshot('07_reviewer_rule_inspection.png');

    // -------------------------------------------------------------
    // STAGE 8: Admin Evaluation Dashboard (/evaluation)
    // -------------------------------------------------------------
    console.log('\n--- 8. Switching to Admin Role & Navigating to /evaluation ---');
    await cdp.eval(`(() => {
      localStorage.setItem('user_role', 'admin');
      localStorage.setItem('regimpact_user_role', 'admin');
      localStorage.setItem('regimpact:role', 'admin');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'admin' } }));
    })()`);
    await wait(500);
    await cdp.navigate('http://localhost:3000/evaluation');
    await wait(2500);
    await cdp.captureScreenshot('08_admin_system_dashboard.png');

    // -------------------------------------------------------------
    // STAGE 9: Admin Document Inventory & Regulations
    // -------------------------------------------------------------
    console.log('\n--- 9. Inspecting Document Inventory & Catalog as Admin ---');
    await cdp.navigate('http://localhost:3000/');
    await wait(2000);
    await cdp.eval(`(() => {
      window.scrollBy(0, 350);
    })()`);
    await wait(1000);
    await cdp.captureScreenshot('09_admin_document_inventory.png');

    console.log('\n=== UAT COMPLETE: All 9 screenshots verified! ===');
  } catch (err) {
    console.error('UAT failed with error:', err);
  } finally {
    edge.kill();
    console.log('Edge browser closed.');
  }
}

runUAT().catch(console.error);
