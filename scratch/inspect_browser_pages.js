const { spawn } = require('child_process');
const http = require('http');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const USER_DATA_DIR = 'C:\\Users\\HP\\AppData\\Local\\Temp\\edge_inspect_' + Date.now();
const PORT = 9223;

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
      this.ws.onerror = reject;
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
    if (res.exceptionDetails) throw new Error(JSON.stringify(res.exceptionDetails));
    return res.result ? res.result.value : undefined;
  }
  async navigate(url) {
    await this.send('Page.navigate', { url });
    await wait(2000);
  }
}

async function inspect() {
  const edge = spawn(EDGE_PATH, [
    '--headless=new',
    '--disable-gpu',
    '--remote-debugging-port=' + PORT,
    '--user-data-dir=' + USER_DATA_DIR,
    'about:blank',
  ]);

  let targets = null;
  for (let i = 0; i < 20; i++) {
    await wait(400);
    try {
      targets = await getJson(`http://127.0.0.1:${PORT}/json/list`);
      if (targets && targets.length > 0) break;
    } catch (e) {}
  }
  const pageTarget = targets.find(t => t.type === 'page') || targets[0];
  const cdp = new CDPClient(pageTarget.webSocketDebuggerUrl);
  await cdp.ready();
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');

  console.log('=== STEP 1: SET ROLE TO SME_USER ===');
  await cdp.navigate('http://localhost:3000/');
  await cdp.eval(`
    localStorage.setItem('regimpact_user_role', 'sme_user');
    window.dispatchEvent(new Event('regimpact:role_change'));
  `);
  await wait(1000);
  let navLinks = await cdp.eval(`Array.from(document.querySelectorAll('nav a')).map(a => a.innerText.trim())`);
  console.log('Nav links after setting sme_user:', navLinks);
  let bodySnippet = await cdp.eval(`document.body.innerText.substring(0, 500)`);
  console.log('Body snippet:\n', bodySnippet);

  console.log('\n=== STEP 2: NAVIGATE TO /admin/reviews AS SME ===');
  await cdp.navigate('http://localhost:3000/admin/reviews');
  await wait(1500);
  let reviewSnippet = await cdp.eval(`document.body.innerText.substring(0, 800)`);
  console.log('Review page snippet as SME:\n', reviewSnippet);

  console.log('\n=== STEP 3: NAVIGATE TO /evaluation AS SME ===');
  await cdp.navigate('http://localhost:3000/evaluation');
  await wait(1500);
  let evalSnippet = await cdp.eval(`document.body.innerText.substring(0, 800)`);
  console.log('Eval page snippet as SME:\n', evalSnippet);

  edge.kill();
}

inspect();

