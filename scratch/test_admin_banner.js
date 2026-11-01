const { spawn } = require('child_process');
const http = require('http');

const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
  '--headless=new', '--disable-gpu', '--remote-debugging-port=9225', '--user-data-dir=C:\\Users\\HP\\AppData\\Local\\Temp\\edge_admin_check', 'about:blank'
]);

setTimeout(async () => {
  const targets = await new Promise(r => http.get('http://127.0.0.1:9225/json/list', res => {
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
  await send('Runtime.evaluate', { expression: 'localStorage.setItem("regimpact_user_role", "admin"); window.dispatchEvent(new CustomEvent("regimpact:role_change", { detail: { role: "admin" } }));' });
  await new Promise(r => setTimeout(r, 2000));
  const text = (await send('Runtime.evaluate', { expression: 'document.body.innerText', returnByValue: true })).result.value;
  console.log('--- TEXT FOUND ---');
  console.log('Includes Administrator System Overview:', text.includes('Administrator System Overview'));
  console.log('Includes Engine State:', text.includes('Engine State'));
  const idx = text.indexOf('Administrator System Overview');
  if (idx !== -1) {
    console.log('Snippet:\n', text.substring(idx, idx + 500));
  }
  edge.kill();
  process.exit(0);
}, 2000);

