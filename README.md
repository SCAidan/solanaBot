# Solana Hybrid Paper Bot — Stage 1

**Research-only. No wallet support, no private keys, no transaction signing, no live trading.**

## Architecture
DEX Screener latest token profiles -> Solana token pairs -> normalization -> liquidity/age/volume filters -> new-pool or momentum signal -> simulated fills -> SQLite -> FastAPI dashboard.

This is a **polling-based discovery prototype**, not a direct Solana WebSocket listener or first-block sniper. DEX Screener's latest profiles are not an exhaustive feed of all new pools. A token can be missed entirely. Momentum compares the earliest snapshot older than 5 minutes with the latest price, not a precise rolling-window bar. Historical backtesting and security verification are NOT implemented yet.

## Local installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m bot.scanner
```
In another terminal:
```bash
source .venv/bin/activate
uvicorn bot.dashboard:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000

## Docker VPS
```bash
docker compose up --build -d
docker compose logs -f scanner
```
Dashboard binds to localhost only: use an SSH tunnel (`ssh -L 8000:127.0.0.1:8000 user@server`) or configure authenticated HTTPS reverse proxy. Never expose the dashboard unauthenticated.

## Simulation assumptions and limitations
- Starting balance $500, maximum two positions, each up to $25 or 5% of equity.
- Paper entry 1% adverse slippage, exit 1% adverse slippage; fees 0.3% of notional plus $0.02 per side.
- Exit triggers: 10% stop, 20% profit target, one hour holding time, or liquidity below $10,000.
- Daily loss gate: 3% equity drawdown from first trade of UTC day. Overall equity gate: 6% from starting capital. These gates prevent new entries, not losses on existing positions.
- Paper fills are assumed possible at last observed prices; no actual sellability or price impact verification. Losses in real memecoins may be much larger.
- New-pool signals are only candidate discovery based on reported pair creation times, not real-time launch sniping.
- Token mint authority, freeze authority, holder concentration, honeypot restrictions and liquidity locks are NOT checked; do not enable real trading without these.
- Missing market data means positions cannot be marked or exited reliably; a stale-feed watchdog and external alerts are needed before production paper evaluation.
- SQLite uses single-file storage for prototype use; use Postgres for larger deployments.
- Live execution deliberately has no implementation.

## Next stage
Add authenticated Solana WebSocket pool-create decoder, independent risk/sellability verification, historical event replay, durable candle storage, trade execution realism, monitoring/alerts, and security reviews. Paper results are not evidence of a profitable strategy.
