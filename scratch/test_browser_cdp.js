const { spawn } = require('child_process');
const http = require('http');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const USER_DATA_DIR = 'C:\\Users\\HP\\AppData\\Local\\Temp\\edge_cdp_test_' + Date.now();
const PORT = 9222;

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
    await wait(2500); // Wait for page load and client-side hydration
  }
}

async function run() {
  console.log('Launching headless Microsoft Edge on remote port ' + PORT + '...');
  const edge = spawn(EDGE_PATH, [
    '--headless=new',
    '--disable-gpu',
    '--remote-debugging-port=' + PORT,
    '--user-data-dir=' + USER_DATA_DIR,
    'about:blank',
  ]);

  edge.stderr.on('data', d => {
    // console.log('Edge err:', d.toString());
  });

  // Wait for Edge to be ready
  let targets = null;
  for (let i = 0; i < 20; i++) {
    await wait(500);
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
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(1000);

    const smeNavLinks = await cdp.eval(`
      Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim())
    `);
    const hasAssessor = smeNavLinks.some(t => t.includes('Compliance Assessor'));
    const hasReviewer = smeNavLinks.some(t => t.includes('Reviewer Portal'));
    const hasEval = smeNavLinks.some(t => t.includes('Evaluation Dashboard'));

    record('SME-01-NAV', 'SME Navbar Links', hasAssessor && !hasReviewer && !hasEval, 
      `Links: [${smeNavLinks.join(', ')}] | Assessor: ${hasAssessor}, Reviewer: ${hasReviewer}, Eval: ${hasEval}`);

    const smeBanner = await cdp.eval(`
      document.body.innerText.includes('SME Self-Assessment Portal')
    `);
    record('SME-02-BANNER', 'SME Home Presentation Banner', smeBanner, `Banner rendered: ${smeBanner}`);

    // Direct navigation to /admin/reviews as SME
    await cdp.navigate('http://localhost:3000/admin/reviews');
    const smeReviewAccessDenied = await cdp.eval(`
      document.body.innerText.includes('Access Denied: Legal Reviewer or Administrator Role Required')
    `);
    const smeReviewQueueHidden = await cdp.eval(`
      !document.body.innerText.includes('All candidate statutory rules in the review queue have been reviewed')
    `);
    record('SME-03-REVIEW-DENIED', 'SME Access to /admin/reviews', smeReviewAccessDenied && smeReviewQueueHidden, 
      `Access Denied Screen: ${smeReviewAccessDenied}, False Queue Empty Hidden: ${smeReviewQueueHidden}`);

    // Direct navigation to /evaluation as SME
    await cdp.navigate('http://localhost:3000/evaluation');
    const smeEvalAccessDenied = await cdp.eval(`
      document.body.innerText.includes('Access Denied: Administrator Role Required')
    `);
    record('SME-04-EVAL-DENIED', 'SME Access to /evaluation', smeEvalAccessDenied, `Access Denied Screen: ${smeEvalAccessDenied}`);

    // ==========================================
    // TEST SUITE 2: Legal Reviewer Persona
    // ==========================================
    console.log('\n--- 2. Testing Legal Reviewer Persona ---');
    await cdp.navigate('http://localhost:3000/');
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'reviewer');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(1000);

    const revNavLinks = await cdp.eval(`
      Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim())
    `);
    const revHasAssessor = revNavLinks.some(t => t.includes('Compliance Assessor'));
    const revHasReviewer = revNavLinks.some(t => t.includes('Reviewer Portal'));
    const revHasEval = revNavLinks.some(t => t.includes('Evaluation Dashboard'));

    record('REV-01-NAV', 'Reviewer Navbar Links', revHasAssessor && revHasReviewer && !revHasEval,
      `Links: [${revNavLinks.join(', ')}] | Assessor: ${revHasAssessor}, Reviewer: ${revHasReviewer}, Eval: ${revHasEval}`);

    const revBanner = await cdp.eval(`
      document.body.innerText.includes('Legal Reviewer Workspace')
    `);
    record('REV-02-BANNER', 'Reviewer Home Presentation Banner', revBanner, `Banner rendered: ${revBanner}`);

    // Direct navigation to /admin/reviews as Reviewer
    await cdp.navigate('http://localhost:3000/admin/reviews');
    await wait(2000); // Wait for reviews to load
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
      document.body.innerText.includes('Access Denied: Administrator Role Required')
    `);
    record('REV-04-EVAL-DENIED', 'Reviewer Access to /evaluation', revEvalAccessDenied, `Access Denied Screen: ${revEvalAccessDenied}`);

    // ==========================================
    // TEST SUITE 3: Administrator Persona
    // ==========================================
    console.log('\n--- 3. Testing Administrator Persona ---');
    await cdp.navigate('http://localhost:3000/');
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'admin');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(1000);

    const adminNavLinks = await cdp.eval(`
      Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim())
    `);
    const admHasAssessor = adminNavLinks.some(t => t.includes('Compliance Assessor'));
    const admHasReviewer = adminNavLinks.some(t => t.includes('Reviewer Portal'));
    const admHasEval = adminNavLinks.some(t => t.includes('Evaluation Dashboard'));

    record('ADM-01-NAV', 'Admin Navbar Links', admHasAssessor && admHasReviewer && admHasEval,
      `Links: [${adminNavLinks.join(', ')}] | Assessor: ${admHasAssessor}, Reviewer: ${admHasReviewer}, Eval: ${admHasEval}`);

    const adminBanner = await cdp.eval(`
      document.body.innerText.includes('Administrator System Overview')
    `);
    const adminKpiPills = await cdp.eval(`
      document.body.innerText.includes('Engine State') && document.body.innerText.includes('Indexed Regulations')
    `);
    record('ADM-02-BANNER', 'Admin Home KPI Banner', adminBanner && adminKpiPills,
      `Banner: ${adminBanner}, KPI Pills: ${adminKpiPills}`);

    // Direct navigation to /admin/reviews as Admin
    await cdp.navigate('http://localhost:3000/admin/reviews');
    await wait(2000);
    const admUploadTabVisible = await cdp.eval(`
      document.body.innerText.includes('Ingest Document (PDF)')
    `);
    record('ADM-03-UPLOAD-TAB', 'Admin Ingest Document Tab Visible', admUploadTabVisible,
      `Ingest Document Tab Visible: ${admUploadTabVisible}`);

    // Direct navigation to /evaluation as Admin
    await cdp.navigate('http://localhost:3000/evaluation');
    await wait(2000);
    const admEvalLoaded = await cdp.eval(`
      document.body.innerText.includes('Evaluation & Benchmark Verification') || 
      document.body.innerText.includes('INVALIDATED_MOCK_DERIVED_RUN') ||
      document.body.innerText.includes('Accuracy')
    `);
    record('ADM-04-EVAL-LOADED', 'Admin Evaluation Dashboard Loaded', admEvalLoaded, `Eval Dashboard Loaded: ${admEvalLoaded}`);

    // ==========================================
    // TEST SUITE 4: Dynamic Switching & Refresh Persistence
    // ==========================================
    console.log('\n--- 4. Testing Dynamic Role Switching & Persistence ---');
    await cdp.navigate('http://localhost:3000/');
    
    // Switch to SME
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'sme_user');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(600);
    const dynamicSmeBanner = await cdp.eval(`document.body.innerText.includes('SME Self-Assessment Portal')`);

    // Switch to Reviewer dynamically without navigation
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'reviewer');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(600);
    const dynamicRevBanner = await cdp.eval(`document.body.innerText.includes('Legal Reviewer Workspace')`);

    // Switch to Admin dynamically without navigation
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'admin');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(600);
    const dynamicAdmBanner = await cdp.eval(`document.body.innerText.includes('Administrator System Overview')`);

    record('DYN-01-SWITCH', 'Dynamic Role Switch without Refresh', 
      dynamicSmeBanner && dynamicRevBanner && dynamicAdmBanner,
      `SME Banner: ${dynamicSmeBanner}, Reviewer Banner: ${dynamicRevBanner}, Admin Banner: ${dynamicAdmBanner}`);

    // Page Refresh Persistence Test under Reviewer Role
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'reviewer');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await cdp.send('Page.reload');
    await wait(2500);
    const persistedRevBanner = await cdp.eval(`document.body.innerText.includes('Legal Reviewer Workspace')`);
    const persistedRevNav = await cdp.eval(`
      Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim()).some(t => t.includes('Reviewer Portal'))
    `);
    record('DYN-02-PERSISTENCE', 'Role Restored Correctly After Reload',
      persistedRevBanner && persistedRevNav,
      `Banner Persisted: ${persistedRevBanner}, Nav Persisted: ${persistedRevNav}`);

    // ==========================================
    // TEST SUITE 5: Compliance Analysis Regression
    // ==========================================
    console.log('\n--- 5. Testing Compliance Analysis via Browser ---');
    await cdp.navigate('http://localhost:3000/');
    await cdp.eval(`
      localStorage.setItem('regimpact_user_role', 'sme_user');
      window.dispatchEvent(new Event('regimpact:role_change'));
    `);
    await wait(1000);

    // Click the "Bottled Mixed Fruit Jam" scenario card if available or fill profile and submit
    const clickedScenario = await cdp.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const jamBtn = btns.find(b => b.textContent.includes('Bottled Mixed Fruit Jam') || b.textContent.includes('Fruit Jam'));
        if (jamBtn) {
          jamBtn.click();
          return true;
        }
        return false;
      })()
    `);

    // Click "Run Compliance Assessment" button
    await wait(1000);
    const clickedSubmit = await cdp.eval(`
      (() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const assessBtn = btns.find(b => b.textContent.includes('Run Compliance Assessment') || b.textContent.includes('Run Assessment'));
        if (assessBtn) {
          assessBtn.click();
          return true;
        }
        return false;
      })()
    `);

    console.log(`Clicked scenario preset: ${clickedScenario}, Clicked Run Assessment: ${clickedSubmit}`);
    // Wait for analysis API call to complete and render results
    await wait(6000);

    const analysisRendered = await cdp.eval(`
      (() => {
        const body = document.body.innerText;
        return {
          hasComplianceReport: body.includes('Compliance Analysis Report') || body.includes('COMPLIANT') || body.includes('NON_COMPLIANT') || body.includes('Assessment Results'),
          hasApplicabilityOrOutcome: body.includes('APPLICABLE') || body.includes('Status') || body.includes('Coverage Gaps') || body.includes('UNSUPPORTED'),
          hasStatutoryCitations: body.includes('Gazette') || body.includes('Regulation') || body.includes('Citation'),
          hasNarrativeExplanation: body.includes('Executive Summary') || body.includes('Analysis Summary') || body.includes('Findings')
        };
      })()
    `);

    const compAnalysisPass = analysisRendered.hasComplianceReport && (analysisRendered.hasApplicabilityOrOutcome || analysisRendered.hasStatutoryCitations);
    record('ANALYSIS-01-REGRESSION', 'Live Browser SME Compliance Assessment Execution',
      compAnalysisPass,
      JSON.stringify(analysisRendered));

  } catch (err) {
    console.error('Test execution error:', err);
    record('EXEC-ERR', 'Test Runner Error', false, err.message);
  } finally {
    console.log('\nClosing headless Edge...');
    try {
      edge.kill();
    } catch (e) {}
  }

  console.log('\n=== BROWSER INTEGRATION ACCEPTANCE SUMMARY ===');
  const allPass = results.every(r => r.pass);
  console.log(`Total Tests: ${results.length} | Passed: ${results.filter(r => r.pass).length} | Failed: ${results.filter(r => !r.pass).length}`);
  console.log(`Overall Result: ${allPass ? 'PASS' : 'FAIL'}`);
}

run();

