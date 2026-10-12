import asyncio, time, logging
import httpx
from .core import connect, signal, buy, mark

BASE='https://api.dexscreener.com'
log=logging.getLogger(__name__)

async def fetch(client,path):
    response=await client.get(BASE+path,timeout=15)
    response.raise_for_status()
    return response.json()

def normalize(pair,now):
    if pair.get('chainId')!='solana': return None
    base=pair.get('baseToken') or {}
    mint=base.get('address')
    created=pair.get('pairCreatedAt')
    try:
        price=float(pair.get('priceUsd') or 0)
        liquidity=float((pair.get('liquidity') or {}).get('usd') or 0)
        volume=float((pair.get('volume') or {}).get('h24') or 0)
    except (ValueError,TypeError): return None
    if not mint or not created or price<=0: return None
    return {'mint':mint,'symbol':base.get('symbol','?')[:32],'price':price,'liquidity':liquidity,'volume':volume,'age_min':max(0,(now-created/1000)/60)}

async def scan_once(client,con):
    now=time.time()
    profiles=await fetch(client,'/token-profiles/latest/v1')
    addresses=list(dict.fromkeys(p['tokenAddress'] for p in profiles if p.get('chainId')=='solana' and p.get('tokenAddress')))[:60]
    if not addresses: return 0
    count=0
    for i in range(0,len(addresses),30):
        pairs=await fetch(client,'/tokens/v1/solana/'+','.join(addresses[i:i+30]))
        best={}
        for pair in pairs if isinstance(pairs,list) else []:
            t=normalize(pair,now)
            if t and (t['mint'] not in best or t['liquidity']>best[t['mint']]['liquidity']): best[t['mint']]=t
        for t in best.values():
            history=[r['price'] for r in con.execute('SELECT price FROM snapshots WHERE mint=? AND ts<? ORDER BY ts ASC LIMIT 1',(t['mint'],now-300))]
            mark(con,t,now)
            s=signal(t,history)
            con.execute('INSERT OR REPLACE INTO candidates VALUES (?,?,?,?,?,?,?,?)',(t['mint'],t['symbol'],t['price'],t['liquidity'],t['volume'],t['age_min'],s or 'watch',now))
            con.execute('INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?)',(t['mint'],now,t['price'],t['liquidity'],t['volume']))
            if s: buy(con,t,s,now)
            count+=1
        con.commit()
    # Keep database bounded
    con.execute('DELETE FROM snapshots WHERE ts<?',(now-86400,))
    con.commit()
    return count

async def loop():
    logging.basicConfig(level=logging.INFO)
    con=connect()
    async with httpx.AsyncClient(headers={'User-Agent':'SolanaHybridPaperBot/0.1'}) as client:
        while True:
            try:
                count=await scan_once(client,con)
                log.info('scanned %s tokens',count)
            except Exception:
                log.exception('scan failed; paper trading paused until next scan')
            await asyncio.sleep(60)

if __name__=='__main__':
    asyncio.run(loop())
