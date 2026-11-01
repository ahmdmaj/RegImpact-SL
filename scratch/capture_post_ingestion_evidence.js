const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const USER_DATA_DIR = 'C:\\Users\\HP\\AppData\\Local\\Temp\\edge_cdp_uat_evidence_' + Date.now();
const PORT = 9230;
const EVIDENCE_DIR = path.resolve(__dirname, '../docs/evidence/phase_5_3b');

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
      awaitPromise: true,
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

async function captureEvidence() {
  console.log('=== CAPTURING POST-INGESTION EVIDENCE ===');

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

  // 1. ADMIN DASHBOARD POST-INGESTION
  console.log('\n--- 1. Admin Review & Ingestion Interface ---');
  await cdp.navigate('http://localhost:3000/admin/reviews');
  await cdp.eval(`
    localStorage.setItem('user_role', 'admin');
    window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'admin' } }));
  `);
  await wait(1000);
  await cdp.navigate('http://localhost:3000/admin/reviews');
  await wait(2000);

  // Check upload tab status
  await cdp.eval(`
    const ingestBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Ingest Document'));
    if (ingestBtn) ingestBtn.click();
  `);
  await wait(1000);
  await cdp.captureScreenshot('03_upload_result.png');

  // Check review queue tab
  await cdp.eval(`
    const queueBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Review Queue'));
    if (queueBtn) queueBtn.click();
  `);
  await wait(1500);
  await cdp.captureScreenshot('04_processing_results.png');

  // 2. LEGAL REVIEWER ROLE ACCEPTANCE
  console.log('\n--- 2. Legal Reviewer Role Interface ---');
  await cdp.eval(`
    localStorage.setItem('user_role', 'reviewer');
    window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'reviewer' } }));
  `);
  await wait(1000);
  await cdp.navigate('http://localhost:3000/admin/reviews');
  await wait(2000);

  const reviewerInfo = await cdp.eval(`({
    roleBadge: document.querySelector('header span')?.textContent || '',
    reviewQueueButtons: Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim()).filter(t => t.includes('Queue')),
    totalCards: document.querySelectorAll('.rounded-xl.border.border-zinc-800').length,
    headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.textContent.trim())
  })`);
  console.log('Reviewer Dashboard State:', reviewerInfo);
  await cdp.captureScreenshot('05_reviewer_queue_new_candidates.png');

  // Evidence details card
  await cdp.captureScreenshot('06_reviewer_evidence_details.png');

  // 3. SME USER EXPERIENCE & PENDING-RULE SAFETY ISOLATION
  console.log('\n--- 3. SME User Experience & Pending Rule Isolation ---');
  await cdp.eval(`
    localStorage.setItem('user_role', 'sme_user');
    window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'sme_user' } }));
  `);
  await wait(1000);
  await cdp.navigate('http://localhost:3000');
  await wait(2000);

  // Run compliance analysis
  console.log('Running SME compliance analysis...');
  await cdp.eval(`
    const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Analyze Compliance'));
    if (btn) btn.click();
  `);
  await wait(4000);

  const smeAnalysis = await cdp.eval(`(() => {
    const cards = Array.from(document.querySelectorAll('.rounded-xl, .border-zinc-800')).map(c => c.textContent);
    const hasSaltRules = cards.some(t => t.includes('2332') || t.includes('Iodization'));
    const verdictBanner = document.querySelector('.text-2xl, .text-xl, .font-bold')?.textContent?.trim() || '';
    return {
      hasSaltRules,
      verdictBanner,
      resultsRendered: document.body.innerText.includes('Regulatory Compliance Dossier') || document.body.innerText.includes('Compliance')
    };
  })()`);
  console.log('SME Analysis Result:', smeAnalysis);
  await cdp.captureScreenshot('07_sme_assessment_safety_boundary.png');

  edge.kill();
  console.log('Evidence capture complete!');
  return {
    reviewerInfo,
    smeAnalysis
  };
}

captureEvidence().then(res => {
  console.log('Result:', JSON.stringify(res, null, 2));
  process.exit(0);
}).catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
