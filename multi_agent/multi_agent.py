"""Multi-agent trading system — Chapter 8. Four agents, in sequence, on a laptop.

    python multi_agent/multi_agent.py            # one cycle
    python multi_agent/multi_agent.py --loop     # every 30 minutes

    Monitor -> Analyst -> Risk Manager -> Executor

Sequential, with **no loopback**. That is a deliberate design choice, not a
simplification: free-form debate produces circular arguments ("but the signal is
strong" / "but the concentration is too high") and costs 10-15 API calls per
decision instead of 4. "The Risk Manager gets the last word. Period."
(ch08.md:603)

The portfolio snapshot is fetched **once** per cycle and threaded through every
agent. Re-introducing per-agent `get_portfolio_state()` calls is the easiest way
to silently quadruple your Alpaca request rate without buying anything for it
(ch08.md:645).

The Executor places **bracket orders**: one submission, and Alpaca creates the
parent, the take-profit child and the stop-loss child on fill. The protective
legs live at the broker from the moment the trade opens, so they fire even when
the bot is not running. (ch11 mis-cites brackets to "Chapter 9" — they are ch08's.
See docs/book-deviations.md #15.)

DEVIATION #4: `run_multi_agent_cycle()` guards against a `None` from the agent
JSON parsers. Each parser can fall through and return None; the printed
orchestrator then calls `.get()` on it and raises `AttributeError: 'NoneType'
object has no attribute 'get'`. ch04, ch05 and ch07 all guard this — ch08 does
not. The guard here matches the book's own idiom.

Educational software. Not financial advice. Paper mode by default. See DISCLAIMER.md.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from utils import artifact, banner  # noqa: E402
from utils.offline import (  # noqa: E402
    MarketOrderRequest,
    OrderClass,
    OrderSide,
    StockLatestQuoteRequest,
    StopLossRequest,
    TakeProfitRequest,
    TimeInForce,
    get_anthropic,
    get_data_client,
    get_trading_client,
    http_get_json,
    offline_enabled,
)

load_dotenv()

claude = get_anthropic()
alpaca = get_trading_client()
data_client = get_data_client()

UW_API_KEY = os.getenv("UW_API_KEY")
UW_BASE = "https://api.unusualwhales.com/api"

# --- Appendix B Template 5 -------------------------------------------------
CYCLE_INTERVAL = 1800        # 30 minutes between cycles
MAX_RECOMMENDATIONS = 3      # the Analyst returns top 3 max
RISK_OVERRIDE_THRESHOLD = 0.40   # sector concentration limit
DAILY_LOSS_HALT = 0.06       # 6% daily loss triggers a halt
MONITOR_ALERT_THRESHOLD = 0.03   # 3% position loss triggers an alert
REVISION_ENABLED = False     # one-loop revision cycle; doubles the API calls
MODEL = "claude-sonnet-4-6"
# Optional production upgrade for the Analyst + Risk Manager (ch08.md:13):
# ADVANCED_MODEL = "claude-opus-4-7"  # ~1.7x the cost, tighter on edge cases


# --------------------------------------------------------------------------- #
#  Shared data layer — fetched once, threaded through every agent
# --------------------------------------------------------------------------- #
def get_portfolio_state() -> dict:
    """Current portfolio, for risk assessment. Called ONCE per cycle."""
    account = alpaca.get_account()
    positions = alpaca.get_all_positions()
    total = float(account.portfolio_value)

    return {
        "cash": float(account.cash),
        "portfolio_value": total,
        "buying_power": float(account.buying_power),
        "positions": [{
            "symbol": p.symbol,
            "qty": int(p.qty),
            "market_value": float(p.market_value),
            "unrealized_pnl": float(p.unrealized_pl),
            "pnl_pct": float(p.unrealized_plpc) * 100,
            "pct_of_portfolio": (float(p.market_value) / total * 100) if total else 0.0,
        } for p in positions],
    }


def get_recent_flow(min_premium=300_000, min_volume_oi_ratio=3.0, is_sweep=True):
    """Fetch recent unusual options flow from UW REST. Once per cycle.

    Do NOT have the Analyst use a vanilla `messages.create('Using Unusual Whales
    MCP, scan for...')` prompt. It does not invoke MCP and returns hallucinated
    JSON. This fetches real flow and passes the dataset into the Analyst's prompt,
    so the Analyst reasons over real flow instead of pretending to fetch it.
    """
    if not UW_API_KEY and not offline_enabled():
        print("[DATA] UW_API_KEY not set; Analyst will run with empty flow.")
        return []
    headers = {"Authorization": f"Bearer {UW_API_KEY}"}
    params = {
        "min_premium": min_premium,
        "min_volume_oi_ratio": min_volume_oi_ratio,
        "is_sweep": is_sweep,
    }
    try:
        payload = http_get_json(
            f"{UW_BASE}/option-trades/flow-alerts",
            headers=headers, params=params, timeout=15,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[DATA] UW REST error: {e}")
        return []

    flow = []
    for item in payload.get("data", []):
        if not (item.get("has_sweep") or item.get("has_floor")):
            continue
        flow.append({
            "ticker": item.get("ticker", ""),
            "strike": item.get("strike", 0),
            "expiry": item.get("expiry", ""),
            "type": item.get("type", ""),
            "volume": item.get("volume", 0),
            "open_interest": item.get("open_interest", 0),
            "volume_oi_ratio": item.get("volume_oi_ratio", 0.0),
            "total_premium": item.get("total_premium", 0),
            "is_sweep": bool(item.get("has_sweep")),
            "is_floor": bool(item.get("has_floor")),
        })
    return flow[:50]  # cap to keep the Analyst prompt tight


def _parse_agent_json(response):
    """Parse an agent response. Returns None when it isn't JSON.

    Every caller must check for None — that is DEVIATION #4.
    """
    text = response.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if "```" in text:
            body = text.split("```")[1]
            if body.startswith("json"):
                body = body[4:]
            try:
                return json.loads(body.strip())
            except json.JSONDecodeError:
                return None
    return None


# --------------------------------------------------------------------------- #
#  The four agents
# --------------------------------------------------------------------------- #
def agent_monitor(portfolio):
    """Monitor: watch portfolio health. Can halt the cycle."""
    response = claude.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""You are the MONITOR agent. Check portfolio health.

            Current portfolio:
            {json.dumps(portfolio, indent=2)}

            Check for:
            1. Any position down more than 3% (stop-loss territory)
            2. Total portfolio down more than 5% from peak
            3. Any single position above 10% of portfolio value
            4. Total invested above 60% of portfolio (overexposed)

            Return JSON:
            {{
                "status": "HEALTHY" or "WARNING" or "CRITICAL",
                "alerts": ["alert1", "alert2"],
                "actions_needed": [
                    {{"ticker": "SYMBOL", "action": "CLOSE" or "REDUCE" or
                      "MONITOR", "reason": "why"}}
                ]
            }}"""
        }],
    )
    return _parse_agent_json(response)


def agent_analyst(portfolio, market_data=None):
    """Analyst: find opportunities in real flow. Recommends; never sizes or trades."""
    if market_data is None:
        market_data = get_recent_flow(min_premium=300_000)

    response = claude.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""You are the ANALYST agent in a multi-agent trading
            system. Your job: find the best trading opportunities from the
            unusual options flow below.

            Current portfolio:
            {json.dumps(portfolio, indent=2)}

            Recent unusual flow (sweeps and blocks above $300K premium, fetched
            from Unusual Whales REST):
            {json.dumps(market_data, indent=2) if market_data else "[]"}

            From this dataset, identify:
            1. Tickers with unusually aggressive flow worth analyzing
            2. Converging signals (flow shape + your training-data knowledge of
               the ticker, sector, typical IV)
            3. High-confidence setups only (require 3+ signal convergence)

            For each opportunity, return JSON:
            {{
                "recommendations": [
                    {{
                        "ticker": "SYMBOL",
                        "direction": "BUY" or "SELL",
                        "confidence": 0-100,
                        "suggested_shares": N,
                        "reasoning": "2-3 sentences",
                        "signals": ["signal1", "signal2", "signal3"]
                    }}
                ]
            }}

            Return your top {MAX_RECOMMENDATIONS} recommendations max. Quality over
            quantity. Do NOT recommend stocks we already hold unless adding is
            justified by new signals."""
        }],
    )
    return _parse_agent_json(response)


def agent_risk_manager(recommendations, portfolio):
    """Risk Manager: approve, reduce, or reject. Gets the last word."""
    response = claude.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""You are the RISK MANAGER agent. Your job: protect
            capital. You are naturally skeptical.

            Current portfolio:
            {json.dumps(portfolio, indent=2)}

            The Analyst recommends these trades:
            {json.dumps(recommendations, indent=2)}

            For EACH recommendation, evaluate:
            1. Position size: max 2% of portfolio per new position
            2. Sector concentration: no sector above 40% of portfolio
            3. Correlation: don't add highly correlated positions
            4. Daily loss: if today's P&L is already -3%, block all buys

            (Earnings blackout enforcement is delegated to the hard risk module
            from ch09; you don't have a live calendar. You may flag a recalled
            earnings window in reasoning, but don't pretend to check
            authoritatively.)

            Ignore the Analyst's confidence score. Evaluate purely on portfolio
            risk metrics.

            For each, return:
            {{
                "decisions": [
                    {{
                        "ticker": "SYMBOL",
                        "direction": "BUY" or "SELL",
                        "action": "APPROVE" or "REDUCE" or "REJECT",
                        "approved_shares": N (0 if rejected),
                        "stop_loss_pct": 3.0,
                        "profit_target_pct": 6.0,
                        "reasoning": "why you approved, reduced, or rejected"
                    }}
                ]
            }}

            Carry the Analyst's `direction` through to your decision unchanged;
            the Executor needs it to place the right side of the bracket (BUY =
            long bracket, SELL = short bracket with mirrored arms).

            Be conservative. When in doubt, REDUCE or REJECT. Your job is to keep
            us alive, not to make money."""
        }],
    )
    return _parse_agent_json(response)


def agent_executor(approved_trades, portfolio):
    """Executor: place each approved trade as an Alpaca BRACKET order.

    One submission opens three orders on fill: the entry (market), a take-profit
    limit at the Risk Manager's `profit_target_pct`, and a stop-loss stop at
    `stop_loss_pct`. `time_in_force` must be DAY or GTC — a bracket is rejected
    with anything else.

    Long arms:  stop BELOW entry, take-profit ABOVE.
    Short arms: mirrored. Keeps parity with ch05's BUY_SHARES / SELL_SHORT.
    """
    results = []

    for trade in approved_trades:
        if trade.get("action") == "REJECT" or trade.get("approved_shares", 0) == 0:
            results.append({
                "ticker": trade.get("ticker", "?"),
                "status": "SKIPPED",
                "reason": trade.get("reasoning", "Rejected by risk"),
            })
            continue

        ticker = trade["ticker"]
        shares = trade["approved_shares"]
        direction = trade.get("direction", "BUY")
        stop_loss_pct = trade.get("stop_loss_pct", 3.0)
        profit_target_pct = trade.get("profit_target_pct", 6.0)

        # 1. Quote the underlying to compute the bracket prices off the live mid.
        #    Asking Claude for a live price is the hallucinated-price bug from
        #    ch05; use Alpaca's market data instead.
        try:
            quote_req = StockLatestQuoteRequest(symbol_or_symbols=ticker)
            quote = data_client.get_stock_latest_quote(quote_req)
            ask = float(quote[ticker].ask_price or 0)
            bid = float(quote[ticker].bid_price or 0)
            if ask <= 0 or bid <= 0:
                raise RuntimeError(f"No live quote for {ticker}")
            entry_price = (ask + bid) / 2
        except Exception as e:  # noqa: BLE001
            results.append({"ticker": ticker, "status": "FAILED",
                            "error": f"quote: {e}"})
            continue

        # 2. Bracket arms depend on direction.
        if direction == "BUY":
            side = OrderSide.BUY
            stop_price = round(entry_price * (1 - stop_loss_pct / 100.0), 2)
            take_profit_price = round(entry_price * (1 + profit_target_pct / 100.0), 2)
        elif direction == "SELL":
            side = OrderSide.SELL
            stop_price = round(entry_price * (1 + stop_loss_pct / 100.0), 2)
            take_profit_price = round(entry_price * (1 - profit_target_pct / 100.0), 2)
        else:
            results.append({
                "ticker": ticker, "status": "FAILED",
                "error": f"unknown direction {direction!r}; expected BUY or SELL",
            })
            continue

        # 3. A single bracket submission. Alpaca creates the parent + take-profit
        #    child + stop-loss child on fill, and auto-cancels the unfilled child
        #    when either side triggers.
        order = MarketOrderRequest(
            symbol=ticker,
            qty=shares,
            side=side,
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=take_profit_price),
            stop_loss=StopLossRequest(stop_price=stop_price),
        )

        try:
            result = alpaca.submit_order(order)
            results.append({
                "ticker": ticker,
                "status": "FILLED",
                "direction": direction,
                "order_id": str(result.id),
                "order_class": str(result.order_class),
                "shares": shares,
                "entry_price": entry_price,
                "bracket_stop_price": stop_price,
                "bracket_take_profit_price": take_profit_price,
                "stop_loss_pct": stop_loss_pct,
                "profit_target_pct": profit_target_pct,
            })
        except Exception as e:  # noqa: BLE001
            results.append({"ticker": ticker, "status": "FAILED", "error": str(e)})

    return results


# --------------------------------------------------------------------------- #
#  The orchestrator
# --------------------------------------------------------------------------- #
def run_multi_agent_cycle():
    """One complete four-agent decision cycle."""
    banner()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'=' * 60}")
    print(f"MULTI-AGENT TRADING CYCLE - {ts}")
    print(f"{'=' * 60}\n")

    # Shared cycle state: fetch the portfolio ONCE and thread it everywhere.
    portfolio = get_portfolio_state()
    market_data = get_recent_flow(min_premium=300_000)
    print(f"[DATA] Portfolio: ${portfolio['portfolio_value']:,.0f} across "
          f"{len(portfolio['positions'])} position(s) | "
          f"{len(market_data)} flow event(s) this cycle\n")

    results = []

    # Phase 1: Monitor
    print("[MONITOR] Checking portfolio health...")
    health = agent_monitor(portfolio)
    if not health:  # DEVIATION #4 — the printed code calls .get() on this.
        print("[MONITOR] Response was not parseable JSON. Aborting cycle.\n")
        return None
    status = health.get("status", "UNKNOWN")
    print(f"[MONITOR] Status: {status}")
    for alert in health.get("alerts", []):
        print(f"[MONITOR] ALERT: {alert}")

    if status == "CRITICAL":
        print("[MONITOR] CRITICAL status. Executing emergency actions.")
        for action in health.get("actions_needed", []):
            if action.get("action") == "CLOSE":
                print(f"[MONITOR] Emergency close: {action['ticker']}")
        print("[MONITOR] Skipping new trades this cycle.\n")
        return _log_cycle(ts, health, None, None, [])

    # Phase 2: Analyst
    print("\n[ANALYST] Scanning for opportunities...")
    analysis = agent_analyst(portfolio, market_data)
    if not analysis:  # DEVIATION #4
        print("[ANALYST] Response was not parseable JSON. Aborting cycle.\n")
        return _log_cycle(ts, health, None, None, [])
    recs = analysis.get("recommendations", [])
    print(f"[ANALYST] Found {len(recs)} recommendations.")
    for rec in recs:
        print(f"[ANALYST] {rec.get('ticker', '?')}: {rec.get('direction', '?')} | "
              f"Confidence: {rec.get('confidence', 0)}% | "
              f"Shares: {rec.get('suggested_shares', 0)}")

    if not recs:
        print("[ANALYST] No opportunities meet criteria. Cycle complete.\n")
        return _log_cycle(ts, health, analysis, None, [])

    # Phase 3: Risk Manager
    print(f"\n[RISK] Evaluating {len(recs)} recommendations...")
    risk_decisions = agent_risk_manager(recs, portfolio)
    if not risk_decisions:  # DEVIATION #4
        print("[RISK] Response was not parseable JSON. Aborting cycle — no trades.\n")
        return _log_cycle(ts, health, analysis, None, [])
    decisions = risk_decisions.get("decisions", [])

    for dec in decisions:
        action = dec.get("action", "REJECT")
        ticker = dec.get("ticker", "?")
        shares = dec.get("approved_shares", 0)
        reason = dec.get("reasoning", "")
        if action == "APPROVE":
            print(f"[RISK] APPROVED: {ticker} ({shares} shares)")
        elif action == "REDUCE":
            print(f"[RISK] REDUCED: {ticker} to {shares} shares ({reason})")
        else:
            print(f"[RISK] REJECTED: {ticker} ({reason})")

    # Phase 4: Executor
    approved = [d for d in decisions if d.get("action") != "REJECT"]
    if approved:
        print(f"\n[EXECUTOR] Placing {len(approved)} bracket order(s)...")
        results = agent_executor(approved, portfolio)
        for r in results:
            if r["status"] == "FILLED":
                long_side = r.get("direction", "BUY") == "BUY"
                stop_sign = "-" if long_side else "+"
                target_sign = "+" if long_side else "-"
                print(f"[EXECUTOR] FILLED ({r.get('direction', 'BUY')}): "
                      f"{r['ticker']} ({r['shares']} shares @ "
                      f"~${r['entry_price']:.2f}) | order_class="
                      f"{r['order_class']} | "
                      f"Stop @ ${r['bracket_stop_price']:.2f} "
                      f"({stop_sign}{r['stop_loss_pct']}%) | "
                      f"Target @ ${r['bracket_take_profit_price']:.2f} "
                      f"({target_sign}{r['profit_target_pct']}%)")
            elif r["status"] == "SKIPPED":
                print(f"[EXECUTOR] SKIPPED: {r['ticker']}")
            else:
                print(f"[EXECUTOR] FAILED: {r['ticker']} - {r['error']}")
    else:
        print("\n[EXECUTOR] No trades approved. Cycle complete.")

    return _log_cycle(ts, health, analysis, risk_decisions, results)


def _log_cycle(ts, health, analysis, risk_decisions, results) -> dict:
    cycle_log = {
        "timestamp": ts,
        "monitor": health,
        "analyst": analysis,
        "risk": risk_decisions,
        "execution": results,
    }
    log_file = artifact("multi_agent/cycle_log.json")
    try:
        with open(log_file) as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []
    logs.append(cycle_log)
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)
    print(f"\nCycle logged to {log_file}")
    return cycle_log


def run_continuous():
    """A cycle every 30 minutes. Fast enough for intraday, slow enough to be cheap."""
    print("Multi-Agent Trading System started.")
    print(f"Running cycles every {CYCLE_INTERVAL // 60} minutes.\n")
    while True:
        try:
            run_multi_agent_cycle()
            print(f"\nNext cycle in {CYCLE_INTERVAL // 60} minutes...\n")
            time.sleep(CYCLE_INTERVAL)
        except KeyboardInterrupt:
            print("\nSystem stopped by user.")
            break
        except Exception as e:  # noqa: BLE001
            print(f"\nError in cycle: {e}")
            print("Retrying in 5 minutes...\n")
            time.sleep(300)


if __name__ == "__main__":
    if "--loop" in sys.argv:
        run_continuous()
    else:
        run_multi_agent_cycle()
