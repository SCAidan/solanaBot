from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from .core import connect,account
app=FastAPI(title='Solana Hybrid Paper Bot')

@app.get('/api/status')
def status():
    con=connect()
    try:
        a=account(con)
        a['mode']='PAPER ONLY — NO WALLET OR LIVE EXECUTION'
        a['candidates']=[dict(r) for r in con.execute('SELECT * FROM candidates ORDER BY updated DESC LIMIT 30')]
        a['trades']=[dict(r) for r in con.execute('SELECT * FROM trades ORDER BY id DESC LIMIT 30')]
        return a
    finally: con.close()

@app.get('/',response_class=HTMLResponse)
def home():
    return '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Solana Hybrid | Paper Bot</title><style>body{font:15px system-ui;background:#f4f6fa;color:#17243a;margin:0}main{max-width:1100px;margin:auto;padding:26px}h1{margin-bottom:4px}.tag{background:#d9f6e5;padding:7px 12px;border-radius:20px;color:#155c3c}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin:25px 0}.card,section{background:white;padding:20px;border-radius:14px;box-shadow:0 2px 12px #d9dfe7}.value{font-size:26px;font-weight:750;margin-top:8px}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #e8edf3;padding:10px;font-size:13px}section{overflow:auto;margin:18px 0}small{color:#69778a}</style></head><body><main><h1>Solana Hybrid Bot</h1><p><span class="tag">PAPER ONLY</span> &nbsp; New pools + momentum research</p><div class="cards" id="cards"></div><section><h2>Open positions</h2><div id="positions"></div></section><section><h2>Scanned candidates</h2><div id="candidates"></div></section><section><h2>Recent simulated trades</h2><div id="trades"></div></section><small>Prices and fills are simulated. DEX Screener is delayed market data, not a direct blockchain sniper feed. Refreshes every 15 seconds.</small></main><script>
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=x=>'$'+Number(x||0).toFixed(2);
function table(rows,cols){if(!rows.length)return '<p>No records yet.</p>';return '<table><thead><tr>'+cols.map(c=>'<th>'+esc(c)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+cols.map(c=>'<td>'+esc(r[c])+'</td>').join('')+'</tr>').join('')+'</tbody></table>'}
async function refresh(){try{const r=await fetch('/api/status');if(!r.ok)throw Error('status '+r.status);const d=await r.json();document.getElementById('cards').innerHTML=[['Equity',money(d.equity)],['Cash',money(d.cash)],['Paper P/L',money(d.pnl)],['Positions',d.positions.length]].map(x=>'<div class="card">'+esc(x[0])+'<div class="value">'+esc(x[1])+'</div></div>').join('');document.getElementById('positions').innerHTML=table(d.positions,['symbol','qty','entry','last','strategy']);document.getElementById('candidates').innerHTML=table(d.candidates,['symbol','price','liquidity','volume','age_min','strategy']);document.getElementById('trades').innerHTML=table(d.trades,['symbol','side','qty','price','fee','realized']);}catch(e){document.getElementById('cards').textContent='Unable to load status: '+e.message}}
refresh();setInterval(refresh,15000);
</script></body></html>'''
