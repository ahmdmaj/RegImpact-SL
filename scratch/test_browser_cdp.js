const { spawn } = require('child_process');
const http = require('http');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const USER_DATA_DIR = 'C:\\Users\\HP\\AppData\\Local\\Temp\\edge_cdp_audit_' + Date.now();
const PORT = 9224;

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
    await wait(2200); // Wait for page load and client-side hydration
  }
}

async function runAudit() {
  console.log('Launching headless Microsoft Edge on remote port ' + PORT + '...');
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
    console.error('Failed to connect to Edge CDP');
    edge.kill();
    process.exit(1);
  }

  const pageTarget = targets.find(t => t.type === 'page') || targets[0];
  console.log('Connected to target page:', pageTarget.id);

  const cdp = new CDPClient(pageTarget.webSocketDebuggerUrl);
  await cdp.ready();
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');

  const results = [];

  function record(id, name, pass, detail) {
    results.push({ id, name, pass, detail });
    console.log(`[${pass ? 'PASS' : 'FAIL'}] ${id}: ${name} - ${detail}`);
  }

  try {
    // ==========================================
    // TEST SUITE 1: SME User Persona
    // ==========================================
    console.log('\n--- 1. Testing SME User Persona ---');
    await cdp.navigate('http://localhost:3000/');
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'sme_user');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'sme_user' } }));
    `);
    await wait(800);

    const smeNavLinks = await cdp.eval(`
      Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim())
    `);
    const hasAssessor = smeNavLinks.some(t => t.includes('Compliance Assessor'));
    const hasReviewer = smeNavLinks.some(t => t.includes('Reviewer Portal'));
    const hasEval = smeNavLinks.some(t => t.includes('Evaluation Dashboard'));

    record('SME-01-NAV', 'SME Navbar Link Filtering', hasAssessor && !hasReviewer && !hasEval, 
      `Assessor: ${hasAssessor}, Reviewer: ${hasReviewer}, Eval: ${hasEval} | Links: [${smeNavLinks.join(' | ')}]`);

    const smeBanner = await cdp.eval(`
      document.body.innerText.includes('SME Self-Assessment Portal')
    `);
    record('SME-02-BANNER', 'SME Home Presentation Banner', smeBanner, `Banner rendered: ${smeBanner}`);

    // Direct navigation to /admin/reviews as SME
    await cdp.navigate('http://localhost:3000/admin/reviews');
    const smeReviewAccessDenied = await cdp.eval(`
      document.body.innerText.includes('403 FORBIDDEN') ||
      document.body.innerText.includes('Access Restricted to Legal Reviewers') ||
      document.body.innerText.includes('Access Forbidden: SME User role is not authorized')
    `);
    const smeReviewQueueHidden = await cdp.eval(`
      !document.body.innerText.includes('All candidate statutory rules in the review queue have been reviewed')
    `);
    record('SME-03-REVIEW-DENIED', 'SME Direct Access to /admin/reviews', smeReviewAccessDenied && smeReviewQueueHidden, 
      `Access Denied Barrier: ${smeReviewAccessDenied}, False Queue Empty Hidden: ${smeReviewQueueHidden}`);

    // Direct navigation to /evaluation as SME
    await cdp.navigate('http://localhost:3000/evaluation');
    const smeEvalAccessDenied = await cdp.eval(`
      document.body.innerText.includes('403 FORBIDDEN') ||
      document.body.innerText.includes('Access Restricted to Administrators') ||
      document.body.innerText.includes("Access Forbidden: Role 'sme_user' is not authorized")
    `);
    record('SME-04-EVAL-DENIED', 'SME Direct Access to /evaluation', smeEvalAccessDenied, `Access Denied Barrier: ${smeEvalAccessDenied}`);

    // ==========================================
    // TEST SUITE 2: Legal Reviewer Persona
    // ==========================================
    console.log('\n--- 2. Testing Legal Reviewer Persona ---');
    await cdp.navigate('http://localhost:3000/');
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'reviewer');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'reviewer' } }));
    `);
    await wait(800);

    const revNavLinks = await cdp.eval(`
      Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim())
    `);
    const revHasAssessor = revNavLinks.some(t => t.includes('Compliance Assessor'));
    const revHasReviewer = revNavLinks.some(t => t.includes('Reviewer Portal'));
    const revHasEval = revNavLinks.some(t => t.includes('Evaluation Dashboard'));

    record('REV-01-NAV', 'Reviewer Navbar Link Filtering', revHasAssessor && revHasReviewer && !revHasEval,
      `Assessor: ${revHasAssessor}, Reviewer: ${revHasReviewer}, Eval: ${revHasEval}`);

    const revBanner = await cdp.eval(`
      document.body.innerText.includes('Legal Reviewer Workspace')
    `);
    record('REV-02-BANNER', 'Reviewer Home Presentation Banner', revBanner, `Banner rendered: ${revBanner}`);

    // Direct navigation to /admin/reviews as Reviewer
    await cdp.navigate('http://localhost:3000/admin/reviews');
    await wait(2500); // Wait for reviews to load
    const revQueueLoaded = await cdp.eval(`
      document.body.innerText.includes('RULE-COLOURING') || document.body.innerText.includes('Pending Review Queue')
    `);
    const revUploadTabHidden = await cdp.eval(`
      !document.body.innerText.includes('Ingest Document (PDF)')
    `);
    record('REV-03-QUEUE-ACCESS', 'Reviewer Queue Loaded & Ingest Tab Hidden', revQueueLoaded && revUploadTabHidden,
      `Queue Loaded: ${revQueueLoaded}, Ingest Tab Hidden: ${revUploadTabHidden}`);

    // Direct navigation to /evaluation as Reviewer
    await cdp.navigate('http://localhost:3000/evaluation');
    const revEvalAccessDenied = await cdp.eval(`
      document.body.innerText.includes('403 FORBIDDEN') ||
      document.body.innerText.includes('Access Restricted to Administrators') ||
      document.body.innerText.includes("Access Forbidden: Role 'reviewer' is not authorized")
    `);
    record('REV-04-EVAL-DENIED', 'Reviewer Direct Access to /evaluation', revEvalAccessDenied, `Access Denied Barrier: ${revEvalAccessDenied}`);

    // ==========================================
    // TEST SUITE 3: Administrator Persona
    // ==========================================
    console.log('\n--- 3. Testing Administrator Persona ---');
    await cdp.navigate('http://localhost:3000/');
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'admin');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'admin' } }));
    `);
    await wait(800);

    const adminNavLinks = await cdp.eval(`
      Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim())
    `);
    const admHasAssessor = adminNavLinks.some(t => t.includes('Compliance Assessor'));
    const admHasReviewer = adminNavLinks.some(t => t.includes('Reviewer Portal'));
    const admHasEval = adminNavLinks.some(t => t.includes('Evaluation Dashboard'));

    record('ADM-01-NAV', 'Admin Navbar Full Access', admHasAssessor && admHasReviewer && admHasEval,
      `Assessor: ${admHasAssessor}, Reviewer: ${admHasReviewer}, Eval: ${admHasEval}`);

    const adminBanner = await cdp.eval(`
      document.body.innerText.includes('Administrator System Overview')
    `);
    const adminKpiPills = await cdp.eval(`
      document.body.innerText.includes('Engine State') || document.body.innerText.includes('Indexed Regulations')
    `);
    record('ADM-02-BANNER', 'Admin Home KPI Banner', adminBanner && adminKpiPills,
      `Banner: ${adminBanner}, KPI Info: ${adminKpiPills}`);

    // Direct navigation to /admin/reviews as Admin
    await cdp.navigate('http://localhost:3000/admin/reviews');
    await wait(2500);
    const admUploadTabVisible = await cdp.eval(`
      document.body.innerText.includes('Ingest Document (PDF)')
    `);
    record('ADM-03-UPLOAD-TAB', 'Admin Ingest Document Tab Visible', admUploadTabVisible,
      `Ingest Document Tab Visible: ${admUploadTabVisible}`);

    // Direct navigation to /evaluation as Admin
    await cdp.navigate('http://localhost:3000/evaluation');
    await wait(2500);
    const admEvalLoaded = await cdp.eval(`
      document.body.innerText.includes('Evaluation & Benchmark Verification') || 
      document.body.innerText.includes('INVALIDATED_MOCK_DERIVED_RUN') ||
      document.body.innerText.includes('Empirical Evaluation Dashboard')
    `);
    record('ADM-04-EVAL-LOADED', 'Admin Evaluation Dashboard Loaded', admEvalLoaded, `Eval Dashboard Loaded: ${admEvalLoaded}`);

    // ==========================================
    // TEST SUITE 4: Dynamic Switching & Refresh Persistence
    // ==========================================
    console.log('\n--- 4. Testing Dynamic Role Switching & Persistence ---');
    await cdp.navigate('http://localhost:3000/');
    
    // 4.1 Switch to SME
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'sme_user');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'sme_user' } }));
    `);
    await wait(600);
    const dynamicSmeBanner = await cdp.eval(`document.body.innerText.includes('SME Self-Assessment Portal')`);

    // 4.2 Switch to Reviewer dynamically without navigation
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'reviewer');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'reviewer' } }));
    `);
    await wait(600);
    const dynamicRevBanner = await cdp.eval(`document.body.innerText.includes('Legal Reviewer Workspace')`);

    // 4.3 Switch to Admin dynamically without navigation
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'admin');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'admin' } }));
    `);
    await wait(600);
    const dynamicAdmBanner = await cdp.eval(`document.body.innerText.includes('Administrator System Overview')`);

    // 4.4 Switch back to SME
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'sme_user');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'sme_user' } }));
    `);
    await wait(600);
    const dynamicBackSme = await cdp.eval(`document.body.innerText.includes('SME Self-Assessment Portal')`);

    record('DYN-01-SWITCH', 'Dynamic Role Switch without Refresh', 
      dynamicSmeBanner && dynamicRevBanner && dynamicAdmBanner && dynamicBackSme,
      `SME: ${dynamicSmeBanner}, Reviewer: ${dynamicRevBanner}, Admin: ${dynamicAdmBanner}, Back to SME: ${dynamicBackSme}`);

    // 4.5 Page Refresh Persistence Test under Reviewer Role
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'reviewer');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'reviewer' } }));
    `);
    await cdp.send('Page.reload');
    await wait(2500);
    const persistedRevBanner = await cdp.eval(`document.body.innerText.includes('Legal Reviewer Workspace')`);
    const persistedRevNav = await cdp.eval(`
      Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim()).some(t => t.includes('Reviewer Portal'))
    `);
    record('DYN-02-PERSISTENCE', 'Demonstration Role Restored Correctly After Reload',
      persistedRevBanner && persistedRevNav,
      `Banner Persisted: ${persistedRevBanner}, Nav Persisted: ${persistedRevNav}`);

    // ==========================================
    // TEST SUITE 5: Compliance Analysis Regression
    // ==========================================
    console.log('\n--- 5. Testing Compliance Analysis via Browser ---');
    await cdp.navigate('http://localhost:3000/');
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'sme_user');
      window.dispatchEvent(new CustomEvent('regimpact:role_change', { detail: { role: 'sme_user' } }));
    `);
    await wait(1000);

    // Click "Analyze Regulatory Impact" button
    const clickSubmit = await cdp.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const assessBtn = btns.find(b => b.textContent.includes('Analyze Regulatory Impact'));
        if (assessBtn) {
          assessBtn.click();
          return true;
        }
        return false;
      })()
    `);

    console.log(`Clicked Analyze Regulatory Impact: ${clickSubmit}`);
    // Wait for analysis API call to complete and render results
    await wait(7000);

    const analysisDetails = await cdp.eval(`
      (() => {
        const body = document.body.innerText;
        return {
          hasComplianceDossier: body.includes('Regulatory Compliance Dossier'),
          hasExecutiveSummary: body.includes('Executive Compliance Summary'),
          hasMandatoryObligations: body.includes('Mandatory') || body.includes('mandatory statutory obligation'),
          hasActionChecklist: body.includes('Action Item Checklist') || body.includes('Action Items') || body.includes('Action Checklist') || body.includes('Checklist'),
          hasStatutoryCitations: body.includes('Statutory Citation') || body.includes('Citations') || body.includes('Regulation 3') || body.includes('Gazette'),
          bodySample: body.substring(body.indexOf('Regulatory Compliance Dossier'), body.indexOf('Regulatory Compliance Dossier') + 400)
        };
      })()
    `);

    const compAnalysisPass = clickSubmit && analysisDetails.hasComplianceDossier && analysisDetails.hasExecutiveSummary;
    record('ANALYSIS-01-REGRESSION', 'Live Browser SME Compliance Assessment Execution',
      compAnalysisPass,
      `Dossier: ${analysisDetails.hasComplianceDossier}, Summary: ${analysisDetails.hasExecutiveSummary}, Mandatory: ${analysisDetails.hasMandatoryObligations}`);

  } catch (err) {
    console.error('Test execution error:', err);
    record('EXEC-ERR', 'Test Runner Error', false, err.message);
  } finally {
    console.log('\nClosing headless Edge...');
    try {
      edge.kill();
    } catch (e) {}
  }

  console.log('\n=== FINAL LIVE BROWSER INTEGRATION ACCEPTANCE SUMMARY ===');
  const total = results.length;
  const passed = results.filter(r => r.pass).length;
  const failed = results.filter(r => !r.pass).length;
  console.log(`Total Tests: ${total} | Passed: ${passed} | Failed: ${failed}`);
  console.log(`Overall Verdict: ${failed === 0 ? 'PASS' : 'FAIL'}`);
}

runAudit();
