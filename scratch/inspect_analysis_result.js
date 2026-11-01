const { spawn } = require('child_process');
const http = require('http');

const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
  '--headless=new', '--disable-gpu', '--remote-debugging-port=9226', '--user-data-dir=C:\\Users\\HP\\AppData\\Local\\Temp\\edge_analysis_inspect', 'about:blank'
]);

setTimeout(async () => {
  const targets = await new Promise(r => http.get('http://127.0.0.1:9226/json/list', res => {
    let d = ''; res.on('data', c => d += c); res.on('end', () => r(JSON.parse(d)));
  }));
  const ws = new WebSocket(targets[0].webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 1;
  const send = (m, p={}) => new Promise(r => {
    const curId = id++;
    const handler = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.id === curId) { ws.removeEventListener('message', handler); r(msg.result); }
    };
    ws.addEventListener('message', handler);
    ws.send(JSON.stringify({ id: curId, method: m, params: p }));
  });
  await send('Page.navigate', { url: 'http://localhost:3000/' });
  await new Promise(r => setTimeout(r, 2000));
  await send('Runtime.evaluate', { expression: 'localStorage.setItem("regimpact_user_role", "sme_user"); window.dispatchEvent(new CustomEvent("regimpact:role_change", { detail: { role: "sme_user" } }));' });
  await new Promise(r => setTimeout(r, 1000));
  
  // Click Analyze Regulatory Impact
  await send('Runtime.evaluate', { expression: `
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const btn = btns.find(b => b.textContent.includes('Analyze Regulatory Impact'));
      if (btn) btn.click();
    })()
  `});

  console.log('Clicked button. Waiting 8 seconds for analysis API...');
  await new Promise(r => setTimeout(r, 8000));

  const text = (await send('Runtime.evaluate', { expression: 'document.body.innerText', returnByValue: true })).result.value;
  console.log('--- ANALYSIS RESULT SNIPPET (right side) ---');
  console.log('Text length:', text.length);
  // Find where results start
  const words = ['Impact Report', 'Dossier', 'Obligation', 'APPLICABLE', 'Summary', 'Compliance', 'Evaluating'];
  for (const w of words) {
    console.log(`Includes "${w}":`, text.includes(w));
  }

  // Print snippet after "Active Persona"
  const idx = text.indexOf('Active Persona');
  if (idx !== -1) {
    console.log('\nSnippet from Active Persona:\n', text.substring(idx, idx + 1500));
  }

  edge.kill();
  process.exit(0);
}, 2000);
