from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json, os, sqlite3, time

DB = os.getenv('BOT_DB', 'data/bot.sqlite3')
CAPITAL = float(os.getenv('PAPER_CAPITAL', '500'))

def connect():
    os.makedirs(os.path.dirname(DB) or '.', exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute('CREATE TABLE IF NOT EXISTS positions (mint TEXT PRIMARY KEY, symbol TEXT, qty REAL, entry REAL, last REAL, opened REAL, strategy TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, mint TEXT, symbol TEXT, side TEXT, qty REAL, price REAL, fee REAL, realized REAL, strategy TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS snapshots (mint TEXT, ts REAL, price REAL, liquidity REAL, volume REAL, PRIMARY KEY(mint,ts))')
    con.execute('CREATE TABLE IF NOT EXISTS candidates (mint TEXT PRIMARY KEY, symbol TEXT, price REAL, liquidity REAL, volume REAL, age_min REAL, strategy TEXT, updated REAL)')
    con.execute('CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT)')
    con.commit()
    return con

def get_state(con, key, default):
    row = con.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
    return json.loads(row['value']) if row else default

def set_state(con, key, value):
    con.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key,json.dumps(value)))

def account(con):
    cash = get_state(con, 'cash', CAPITAL)
    positions = [dict(x) for x in con.execute('SELECT * FROM positions')]
    equity = cash + sum(p['qty'] * p['last'] for p in positions)
    return {'cash':round(cash,4),'equity':round(equity,4),'positions':positions,'pnl':round(equity-CAPITAL,4)}

def fee(notional):
    return notional * 0.003 + 0.02  # illustrative 0.3% plus $0.02 network/priority overhead

def buy(con, token, strategy, now=None):
    now = now or time.time()
    acc = account(con)
    if con.execute('SELECT 1 FROM positions WHERE mint=?',(token['mint'],)).fetchone(): return False
    if len(acc['positions']) >= 2 or acc['equity'] < CAPITAL*0.94: return False
    day = datetime.fromtimestamp(now,timezone.utc).strftime('%Y-%m-%d')
    if get_state(con,'day',day) != day:
        set_state(con,'day',day); set_state(con,'day_start',acc['equity'])
    if acc['equity'] < get_state(con,'day_start',acc['equity'])*0.97: return False
    notional = min(25.0, acc['equity']*0.05, max(0,acc['cash']-2)/1.01)
    if notional < 5 or token['price'] <= 0: return False
    entry = token['price']*1.01  # adverse 1% entry slippage
    qty = notional/entry
    cost = notional+fee(notional)
    if cost > acc['cash']: return False
    con.execute('INSERT INTO positions VALUES (?,?,?,?,?,?,?)',(token['mint'],token['symbol'],qty,entry,entry,now,strategy))
    con.execute('INSERT INTO trades (ts,mint,symbol,side,qty,price,fee,realized,strategy) VALUES (?,?,?,?,?,?,?,?,?)',(now,token['mint'],token['symbol'],'BUY',qty,entry,fee(notional),0,strategy))
    set_state(con,'cash',acc['cash']-cost)
    con.commit(); return True

def mark(con, token, now=None):
    now = now or time.time()
    p = con.execute('SELECT * FROM positions WHERE mint=?',(token['mint'],)).fetchone()
    if not p: return
    if token['price'] <= 0: return
    con.execute('UPDATE positions SET last=? WHERE mint=?',(token['price'],token['mint']))
    change = token['price']/p['entry']-1
    if change <= -0.10 or change >= 0.20 or now-p['opened'] >= 3600 or token['liquidity'] < 10000:
        sell(con,token['mint'],token['price'],now)
    con.commit()

def sell(con,mint,price,now=None):
    now = now or time.time()
    p=con.execute('SELECT * FROM positions WHERE mint=?',(mint,)).fetchone()
    if not p: return False
    exit_price=price*0.99
    gross=p['qty']*exit_price
    costs=fee(gross)
    realized=gross-p['qty']*p['entry']-costs
    cash=get_state(con,'cash',CAPITAL)
    set_state(con,'cash',cash+gross-costs)
    con.execute('INSERT INTO trades (ts,mint,symbol,side,qty,price,fee,realized,strategy) VALUES (?,?,?,?,?,?,?,?,?)',(now,mint,p['symbol'],'SELL',p['qty'],exit_price,costs,realized,p['strategy']))
    con.execute('DELETE FROM positions WHERE mint=?',(mint,))
    con.commit(); return True

def signal(token,history):
    if token['price']<=0 or token['liquidity']<20000 or token['volume']<30000: return None
    if token['age_min'] < 10: return None
    if token['age_min'] <= 60 and token['liquidity'] >= 30000 and token['volume'] >= 50000:
        return 'new_pool_watch'  # delayed discovery, NOT on-chain sniping
    if len(history)>=2 and history[0]>0 and token['price']/history[0]>=1.04 and token['volume']>=100000 and token['liquidity']>=50000:
        return 'momentum'
    return None
