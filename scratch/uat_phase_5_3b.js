const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const USER_DATA_DIR = 'C:\\Users\\HP\\AppData\\Local\\Temp\\edge_cdp_uat_' + Date.now();
const PORT = 9229;
const CANDIDATE_PDF = path.resolve(__dirname, '../backend/data/candidates/2332-03_E.pdf');
const EVIDENCE_DIR = path.resolve(__dirname, '../docs/evidence/phase_5_3b');

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

async function runFullUAT() {
  console.log('=== STARTING REGIMPACT-SL PHASE 5.3B LIVE UAT ===');
  console.log('Target Candidate PDF:', CANDIDATE_PDF);

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

  // -------------------------------------------------------------
  // STAGE A: BASELINE
  // -------------------------------------------------------------
  console.log('\n--- [STAGE A] Pre-UAT Baseline ---');
  await cdp.navigate('http://localhost:3000/admin/reviews');
  await cdp.eval(`
    localStorage.setItem('user_role', 'admin');
    window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'admin' } }));
  `);
  await wait(1000);
  await cdp.navigate('http://localhost:3000/admin/reviews');
  await wait(1500);

  const baseline = await cdp.eval(`({
    url: window.location.href,
    role: localStorage.getItem('user_role'),
    pendingBadge: document.querySelector('button')?.textContent || '',
    buttons: Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim()).filter(t => t.includes('Queue') || t.includes('Ingest'))
  })`);
  console.log('Pre-UAT Baseline State:', baseline);
  await cdp.captureScreenshot('01_pre_upload_admin_dashboard.png');

  // -------------------------------------------------------------
  // STAGE B: ACTUAL ADMIN UI UPLOAD
  // -------------------------------------------------------------
  console.log('\n--- [STAGE B] Actual Admin UI Upload ---');
  // Click "Ingest Document (PDF)" tab
  console.log('Clicking "Ingest Document (PDF)" tab...');
  await cdp.eval(`
    const ingestBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Ingest Document'));
    if (ingestBtn) ingestBtn.click();
  `);
  await wait(1000);

  // Set file via CDP DOM.setFileInputFiles
  console.log('Setting candidate PDF in file input...');
  const doc = await cdp.send('DOM.getDocument');
  const fileInputNode = await cdp.send('DOM.querySelector', {
    nodeId: doc.root.nodeId,
    selector: 'input[type="file"]'
  });

  if (!fileInputNode || !fileInputNode.nodeId) {
    throw new Error('Could not find file input node in DOM');
  }

  await cdp.send('DOM.setFileInputFiles', {
    files: [CANDIDATE_PDF],
    nodeId: fileInputNode.nodeId
  });

  // Trigger change event and fill metadata
  console.log('Populating statutory metadata into UI form...');
  const formFillResult = await cdp.eval(`(() => {
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
      fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const titleInput = document.querySelector('input[placeholder="e.g. Food (Labelling) Regulations 2024"]');
    if (titleInput) {
      titleInput.value = "Food (Iodization of Salt) Regulations 2023";
      titleInput.dispatchEvent(new Event('input', { bubbles: true }));
      titleInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const gazetteInput = document.querySelector('input[placeholder="e.g. 2443/27"]');
    if (gazetteInput) {
      gazetteInput.value = "2332/03";
      gazetteInput.dispatchEvent(new Event('input', { bubbles: true }));
      gazetteInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const dateInput = document.querySelector('input[type="date"]');
    if (dateInput) {
      dateInput.value = "2023-05-15";
      dateInput.dispatchEvent(new Event('input', { bubbles: true }));
      dateInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const submitBtn = document.querySelector('button[type="submit"]');
    return {
      fileInputFilesCount: fileInput?.files?.length || 0,
      fileName: fileInput?.files?.[0]?.name || '',
      title: titleInput?.value,
      gazetteNo: gazetteInput?.value,
      date: dateInput?.value,
      submitDisabled: submitBtn?.disabled,
      submitText: submitBtn?.textContent?.trim()
    };
  })()`);
  console.log('Form State Prior to Submission:', formFillResult);

  await cdp.captureScreenshot('02_selected_document_upload_interface.png');

  // Submit form via UI
  console.log('Submitting upload form through the UI...');
  await cdp.eval(`
    const form = document.querySelector('form');
    if (form) {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.click();
      else form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }
  `);

  // Wait for processing
  console.log('Awaiting document ingestion, clause segmentation, and live Gemini rule compilation...');
  let uploadFinished = false;
  let uploadStatusText = '';
  const startTime = Date.now();

  for (let attempt = 0; attempt < 90; attempt++) {
    await wait(2000);
    const status = await cdp.eval(`(() => {
      const submitBtn = document.querySelector('button[type="submit"]');
      const toast = document.querySelector('.fixed.top-20');
      const successBox = document.querySelector('.border-emerald-800\\\\/60');
      const errorBox = document.querySelector('.border-rose-800\\\\/60');
      return {
        btnText: submitBtn ? submitBtn.textContent.trim() : '',
        btnDisabled: submitBtn ? submitBtn.disabled : null,
        toastText: toast ? toast.textContent.trim() : '',
        successBoxText: successBox ? successBox.textContent.trim() : '',
        errorBoxText: errorBox ? errorBox.textContent.trim() : '',
      };
    })()`);

    const elapsed = Math.round((Date.now() - startTime) / 1000);
    process.stdout.write(`\rWaiting for upload pipeline... elapsed: ${elapsed}s | btn: ${status.btnText} | toast: ${status.toastText.slice(0, 40)}`);

    if (status.successBoxText || (status.toastText && status.toastText.includes('ingested')) || (status.btnText && status.btnText.includes('Upload and Process') && !status.btnDisabled && elapsed > 5)) {
      uploadFinished = true;
      uploadStatusText = status.successBoxText || status.toastText;
      console.log('\nUpload and compilation finished in ' + elapsed + 's!');
      console.log('Result text:', uploadStatusText);
      break;
    }

    if (status.errorBoxText || (status.toastText && status.toastText.includes('Failed'))) {
      uploadFinished = true;
      uploadStatusText = status.errorBoxText || status.toastText;
      console.log('\nUpload failed after ' + elapsed + 's: ' + uploadStatusText);
      break;
    }
  }

  await wait(2000);
  await cdp.captureScreenshot('03_upload_result.png');

  // -------------------------------------------------------------
  // STAGE C: DOCUMENT PROCESSING VERIFICATION
  // -------------------------------------------------------------
  console.log('\n--- [STAGE C] Document Processing Verification ---');
  // Switch back to Review Queue tab in Admin
  await cdp.eval(`
    const queueBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Review Queue'));
    if (queueBtn) queueBtn.click();
  `);
  await wait(2500);

  const queueInfo = await cdp.eval(`(() => {
    const queueTab = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Review Queue'));
    const cards = Array.from(document.querySelectorAll('.rounded-xl.border.border-zinc-800')).map(c => {
      const text = c.textContent;
      const ruleId = c.querySelector('span.font-mono')?.textContent?.trim() || '';
      return {
        ruleId,
        containsSalt: text.includes('Salt') || text.includes('salt') || text.includes('2332'),
        title: c.querySelector('h3, .font-semibold')?.textContent?.trim() || '',
        snippet: text.slice(0, 150).replace(/\\s+/g, ' ')
      };
    });
    return {
      queueTabText: queueTab ? queueTab.textContent.trim() : '',
      totalCards: cards.length,
      saltCards: cards.filter(c => c.containsSalt)
    };
  })()`);
  console.log('Review Queue State:', queueInfo);

  await cdp.captureScreenshot('04_processing_results.png');

  // -------------------------------------------------------------
  // STAGE D: REVIEWER UI ACCEPTANCE
  // -------------------------------------------------------------
  console.log('\n--- [STAGE D] Reviewer Role Acceptance ---');
  // Switch role to Legal Reviewer
  await cdp.eval(`
    localStorage.setItem('user_role', 'reviewer');
    window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'reviewer' } }));
  `);
  await wait(1000);
  await cdp.navigate('http://localhost:3000/admin/reviews');
  await wait(2000);

  const reviewerState = await cdp.eval(`(() => {
    const roleBadge = document.querySelector('header span')?.textContent || '';
    const tabs = Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim());
    const cards = Array.from(document.querySelectorAll('.rounded-xl.border.border-zinc-800'));
    return {
      currentRole: localStorage.getItem('user_role'),
      tabs,
      totalCards: cards.length,
    };
  })()`);
  console.log('Legal Reviewer Portal State:', reviewerState);
  await cdp.captureScreenshot('05_reviewer_queue_new_candidates.png');

  // Inspect the first salt candidate rule card and expand raw details if available
  const candidateDetail = await cdp.eval(`(() => {
    const saltCard = Array.from(document.querySelectorAll('.rounded-xl.border.border-zinc-800'))
      .find(c => c.textContent.includes('2332') || c.textContent.includes('Salt') || c.textContent.includes('salt'));
    if (!saltCard) return null;

    // Scroll card into view
    saltCard.scrollIntoView({ behavior: 'instant', block: 'center' });

    const ruleId = saltCard.querySelector('span.font-mono')?.textContent?.trim() || '';
    const gazetteRef = saltCard.querySelector('.text-amber-400, .text-zinc-200')?.textContent?.trim() || '';
    const quoteSpan = saltCard.querySelector('.legal-quote-text')?.textContent?.trim() || '';
    const obligation = saltCard.querySelector('.font-serif, .text-zinc-100')?.textContent?.trim() || '';
    const buttons = Array.from(saltCard.querySelectorAll('button')).map(b => b.textContent.trim());

    return {
      ruleId,
      gazetteRef,
      quoteSpan: quoteSpan.slice(0, 200),
      obligation: obligation.slice(0, 200),
      buttons
    };
  })()`);
  console.log('Candidate Rule Detail:', candidateDetail);
  await wait(1000);
  await cdp.captureScreenshot('06_reviewer_evidence_details.png');

  // -------------------------------------------------------------
  // STAGE E: PENDING-RULE SAFETY ISOLATION
  // -------------------------------------------------------------
  console.log('\n--- [STAGE E] Pending-Rule Safety Isolation in SME Experience ---');
  // Switch role to SME User
  await cdp.eval(`
    localStorage.setItem('user_role', 'sme_user');
    window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'sme_user' } }));
  `);
  await wait(1000);
  await cdp.navigate('http://localhost:3000');
  await wait(2500);

  // Run compliance analysis on existing product
  console.log('Running compliance assessment as SME User...');
  await cdp.eval(`
    const analyzeBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Analyze Compliance'));
    if (analyzeBtn) analyzeBtn.click();
  `);
  await wait(4000);

  const smeState = await cdp.eval(`(() => {
    const heading = document.querySelector('h1, h2')?.textContent?.trim() || '';
    const cards = Array.from(document.querySelectorAll('.rounded-xl.border, .border-zinc-800')).map(c => c.textContent);
    const mentionsSalt = cards.some(t => t.includes('2332') || t.includes('Iodization'));
    const badge = document.querySelector('header span')?.textContent || '';
    const navLinks = Array.from(document.querySelectorAll('header a')).map(a => a.textContent.trim());
    return {
      heading,
      badge,
      navLinks,
      mentionsSaltPendingRules: mentionsSalt,
      resultsVisible: document.querySelector('.bg-zinc-900') !== null
    };
  })()`);
  console.log('SME Compliance Assessment Safety State:', smeState);
  await cdp.captureScreenshot('07_sme_assessment_safety_boundary.png');

  edge.kill();
  console.log('\n=== UAT AUTOMATION COMPLETE ===');
  return {
    formFillResult,
    uploadStatusText,
    queueInfo,
    reviewerState,
    candidateDetail,
    smeState
  };
}

runFullUAT().then(res => {
  console.log('\nFinal UAT Output:', JSON.stringify(res, null, 2));
  process.exit(0);
}).catch(err => {
  console.error('\nUAT Execution Failed:', err);
  process.exit(1);
});
