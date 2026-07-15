"""Options-flow trading bot — Chapter 5. Polls UW flow every 30s; trades only at
70+ confidence.

Five stages per event (ch05.md:41-51): Poll -> Filter -> Analyze -> Decide ->
Execute. The bot uses options flow as the *signal* and executes in **shares of
the underlying** — placing real options contracts needs contract-symbol lookup,
strike/expiry selection and liquidity checks, and is out of scope for the chapter.

Run one cycle and exit (what the book itself does, ch05.md:74):

    python flow_trader/flow_trader.py            # one cycle
    python flow_trader/flow_trader.py --loop     # the real polling loop

`check_exits()` matches the 2nd-edition book (see docs/book-deviations.md #13,
status: resolved in book). Three behaviours worth calling out — all three are in
the current book and in this module; earlier printings had none of them:

* **Shorts are covered, not doubled.** Reducing a short means `OrderSide.BUY`
  (ch05.md:530). Earlier printings submitted `OrderSide.SELL` unconditionally,
  which on a short at +6% P&L *adds to* the short and destroys capital.
* **The breakeven stop.** After scaling out, the stop on the remainder sits at
  breakeven (ch05.md:507).
* **The 5-day time limit.** A position that hasn't hit its stop or target in 5
  trading days is closed at market (ch05.md:544).

Educational software. Not financial advice. Paper mode by default. See DISCLAIMER.md.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from datetime import time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from utils import artifact, banner  # noqa: E402
from utils.offline import (  # noqa: E402
    MarketOrderRequest,
    OrderSide,
    StockLatestQuoteRequest,
    TimeInForce,
    get_anthropic,
    get_data_client,
    get_trading_client,
    http_get_json,
    offline_enabled,
)
from utils.signals import adjust_confidence  # noqa: E402

load_dotenv()

claude = get_anthropic()
alpaca = get_trading_client()
data_client = get_data_client()

# --- Configuration (ch05.md:105-111, Appendix B Template 3) ----------------
UW_API_KEY = os.getenv("UW_API_KEY")
UW_BASE = "https://api.unusualwhales.com/api"
CONFIDENCE_THRESHOLD = 70     # ch05.md:108
MIN_PREMIUM = 500000          # ch05.md:109 — $500K minimum for real-time trading
MAX_POSITION_PCT = 0.02       # ch05.md:110 — 2% of account per trade, NOTIONAL.
POLL_INTERVAL = 30            # ch05.md:111 — seconds between checks
MAX_DTE = 14                  # ch05.md:45  — option must expire within 14 days
MODEL = "claude-sonnet-4-6"

# ch05.md:550 — ignore any flow event timestamped before 9:35 AM Eastern.
SESSION_START = dtime(9, 35)

# Exit rules (ch05.md:489-514)
STOP_LOSS_PCT = -3.0          # close the position
PROFIT_TARGET_PCT = 6.0       # scale out half, then trail the stop to breakeven
TIME_LIMIT_DAYS = 5           # the flow signal has a shelf life

# MAX_POSITION_PCT is 2% of the account as *notional*. ch09's MAX_RISK_PER_TRADE
# is 2% as *risk* (position x stop width), which on a $100K account at a 3% stop
# supports a $66,600 position. Same number, different quantity. The book
# reconciles them deliberately: ch09's risk module is the gatekeeper that
# overrides this naive sizing (ch05.md:422, ch09.md:423). Do not unify them.

EXIT_STATE_FILE = "flow_trader/exit_state.json"
TRADE_LOG_FILE = "flow_trader/trade_log.json"


# --------------------------------------------------------------------------- #
#  Stage 1-2: poll + filter
# --------------------------------------------------------------------------- #
def get_live_flow(newer_than_ms: int | None = None):
    """Pull recent unusual flow events from UW REST.

    `newer_than` (Unix ms) is the documented UW polling param. The book's prose
    says the bot asks "for events from the last 5 minutes" (ch05.md:43) but the
    printed `get_live_flow()` passes no time window at all — freshness comes from
    the `seen_events` dedup set instead. This module passes `newer_than` when the
    caller has a last-seen timestamp, which is what the prose describes and what
    the API actually supports. See docs/book-deviations.md (#3).
    """
    if not UW_API_KEY and not offline_enabled():
        raise RuntimeError(
            "UW_API_KEY not set in .env. The flow trader requires a paid UW tier "
            "(Trial $50/wk minimum). Or leave CTB_OFFLINE on to run against the "
            "bundled synthetic fixtures."
        )
    headers = {"Authorization": f"Bearer {UW_API_KEY}"}
    params = {
        "min_premium": MIN_PREMIUM,
        "min_volume_oi_ratio": 3.0,
        "max_dte": MAX_DTE,
        "is_sweep": True,
    }
    if newer_than_ms is not None:
        params["newer_than"] = newer_than_ms

    try:
        payload = http_get_json(
            f"{UW_BASE}/option-trades/flow-alerts",
            headers=headers, params=params, timeout=15,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[{timestamp()}] UW REST error: {e}")
        return []

    raw = payload.get("data", [])
    events = []
    for item in raw:
        # The server filters to sweeps via is_sweep=True and max_dte=14; keep
        # floor (large institutional) prints that came through too.
        if not (item.get("has_sweep") or item.get("has_floor")):
            continue
        created = item.get("created_at", "")
        if not _is_after_session_start(created):
            print(f"[{timestamp()}] IGNORED {item.get('ticker')}: flow timestamped "
                  f"before 9:35 AM ET (ch05.md:550)")
            continue
        events.append({
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
            "timestamp": created or timestamp(),
        })
    return events


def _is_after_session_start(created_at: str) -> bool:
    """ch05.md:550 — pre-9:35 flow references stale underlying prices. Skip it."""
    if not created_at:
        return True
    try:
        stamp = datetime.fromisoformat(created_at)
    except ValueError:
        return True
    return stamp.time() >= SESSION_START


# --------------------------------------------------------------------------- #
#  Stage 3: analyze
# --------------------------------------------------------------------------- #
def analyze_flow_event(event):
    """Deep analysis of a single flow event. Returns a dict or None."""
    ticker = event["ticker"]
    response = claude.messages.create(
        model=MODEL,
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""URGENT FLOW EVENT on {ticker}:
            {json.dumps(event)}

            Run rapid analysis. Reason from the event data + your training-data
            knowledge of {ticker}, sector, and typical IV behavior. Be honest
            when a dimension is unknown.

            1. Is this flow consistent with how {ticker} is usually traded
               (typical sweep size, strike preference)?
            2. What does dark pool tend to look like for this float and sector?
               Any signal in the trade timing?
            3. Where would IV likely be sitting for this strike + expiration?
               Cheap or rich?
            4. Sector momentum context (training-data baseline; you don't have
               today's tape)?
            5. Any recalled catalyst window for {ticker} (earnings, Fed, news)?

            Return JSON:
            {{
                "ticker": "{ticker}",
                "direction": "BULLISH" or "BEARISH",
                "confidence": 0-100,
                "dark_pool_read": "BULLISH" or "BEARISH" or "UNKNOWN",
                "reasoning": "one paragraph",
                "suggested_action": "BUY_SHARES" or "SELL_SHORT" or "NO_TRADE"
            }}

            Note: this bot trades shares of the underlying, not options contracts.
            BUY_SHARES = long the stock; SELL_SHORT = short the stock; NO_TRADE =
            skip. The options-flow event is the SIGNAL; the execution is stock."""
        }],
    )
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
#  Stage 4-5: decide + execute
# --------------------------------------------------------------------------- #
def calculate_position_size(ticker):
    """Shares to buy at 2% of account value (notional).

    Asking Claude for the current price returns either a refusal or a
    hallucinated number that mis-sizes the trade — the vanilla Messages API has
    no live market data. Quote comes from Alpaca (ch05.md:223-231).

    Returns `(0, 0)` when there is no usable quote: skip the trade rather than
    guess a price.
    """
    account = alpaca.get_account()
    account_value = float(account.portfolio_value)
    max_position = account_value * MAX_POSITION_PCT

    try:
        quote_req = StockLatestQuoteRequest(symbol_or_symbols=ticker)
        quote = data_client.get_stock_latest_quote(quote_req)
        ask = float(quote[ticker].ask_price or 0)
        bid = float(quote[ticker].bid_price or 0)
        if ask > 0 and bid > 0:
            price = (ask + bid) / 2
        elif ask > 0:
            price = ask
        elif bid > 0:
            price = bid
        else:
            return 0, 0  # no live quote: skip rather than guess
        shares = int(max_position / price)
        return shares, price
    except Exception as e:  # noqa: BLE001
        print(f"[{timestamp()}] Quote fetch failed for {ticker}: {e}")
        return 0, 0


def execute_trade(analysis, event):
    """Place a paper trade based on the analysis."""
    ticker = analysis["ticker"]
    action = analysis.get("suggested_action", "NO_TRADE")

    if action == "NO_TRADE":
        print(f"[{timestamp()}] Skipping {ticker}: NO_TRADE")
        return None

    shares, price = calculate_position_size(ticker)
    if shares <= 0:
        print(f"[{timestamp()}] Skipping {ticker}: position size 0")
        return None

    if action == "BUY_SHARES":
        side = OrderSide.BUY
    elif action == "SELL_SHORT":
        side = OrderSide.SELL
    else:
        print(f"[{timestamp()}] Unknown action {action} for {ticker}; skipping")
        return None

    order = MarketOrderRequest(
        symbol=ticker, qty=shares, side=side, time_in_force=TimeInForce.DAY,
    )
    try:
        result = alpaca.submit_order(order)
        log_trade(analysis, event, result, shares, price)
        return result
    except Exception as e:  # noqa: BLE001
        print(f"[{timestamp()}] ORDER FAILED: {e}")
        return None


def log_trade(analysis, event, order_result, shares, price):
    """Log every decision to `flow_trader/trade_log.json` — traded or passed.

    This log is also the bot's own ledger of *when* it opened each position,
    which is what the 5-day time limit in `check_exits()` reads.
    """
    entry = {
        "timestamp": timestamp(),
        "ticker": analysis["ticker"],
        "direction": analysis.get("direction"),
        "confidence": analysis.get("confidence"),
        "reasoning": analysis.get("reasoning"),
        "shares": shares,
        "price": price,
        "order_id": str(getattr(order_result, "id", "")) if order_result else None,
        "order_status": str(getattr(order_result, "status", "")) if order_result else "PASSED",
        "flow_event": event,
    }
    log_file = artifact(TRADE_LOG_FILE)
    try:
        with open(log_file) as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []
    logs.append(entry)
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)
    return entry


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------- #
#  Exit management (ch05.md:485-517) — the three fixes live here
# --------------------------------------------------------------------------- #
def _load_exit_state() -> dict:
    try:
        with open(artifact(EXIT_STATE_FILE)) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_exit_state(state: dict) -> None:
    with open(artifact(EXIT_STATE_FILE), "w") as f:
        json.dump(state, f, indent=2)


def position_age_days(symbol: str) -> int | None:
    """Trading days since the bot opened this position, from its own trade log.

    Returns None for positions the bot did not open (or opened before the log
    existed). Those are exempt from the time limit — the bot will not close a
    position whose age it cannot establish.
    """
    try:
        with open(artifact(TRADE_LOG_FILE)) as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    stamps = [entry["timestamp"] for entry in logs
              if entry.get("ticker") == symbol and entry.get("order_id")]
    if not stamps:
        return None
    opened = datetime.strptime(max(stamps), "%Y-%m-%d %H:%M:%S")
    delta = datetime.now() - opened
    # Trading days, not calendar days: ~5 sessions per 7 calendar days.
    return int(delta.days * 5 / 7)


def check_exits():
    """Stop-loss, profit target, breakeven stop, and the 5-day time limit.

    Called at the top of every polling cycle, before flow detection.

    This is a **soft stop in code**, not a hard stop order with the broker: if
    the bot is not running, nothing fires. ch08's multi-agent Executor submits
    Alpaca *bracket* orders instead, so the protective legs live at the broker
    from the moment the trade opens. If you need protection during disconnects
    in this single-bot version, migrate to the ch08 bracket pattern.
    """
    state = _load_exit_state()
    actions = []
    for pos in alpaca.get_all_positions():
        symbol = pos.symbol
        qty = int(pos.qty)
        is_short = qty < 0
        pnl_pct = float(pos.unrealized_plpc) * 100

        # Once half is scaled out, the stop on the remainder sits at breakeven.
        stop_level = 0.0 if state.get(symbol, {}).get("breakeven") else STOP_LOSS_PCT

        if pnl_pct <= stop_level:
            label = "BREAKEVEN STOP" if stop_level == 0.0 else "STOP-LOSS"
            print(f"[{timestamp()}] {label}: {symbol} at {pnl_pct:+.1f}%")
            alpaca.close_position(symbol)   # side-agnostic: covers shorts too
            state.pop(symbol, None)
            actions.append((symbol, label))
            continue

        if pnl_pct >= PROFIT_TARGET_PCT and not state.get(symbol, {}).get("scaled"):
            half = abs(qty) // 2
            if half > 0:
                # Reducing a short means BUYing it back (ch05.md:530). Selling
                # a short at +6% would ADD to it. Earlier printings submitted
                # OrderSide.SELL unconditionally; the 2nd edition fixed this.
                side = OrderSide.BUY if is_short else OrderSide.SELL
                print(f"[{timestamp()}] PROFIT TARGET: Scaling out {half} of "
                      f"{abs(qty)} {symbol} ({'cover' if is_short else 'sell'}) "
                      f"at {pnl_pct:+.1f}%")
                alpaca.submit_order(MarketOrderRequest(
                    symbol=symbol, qty=half, side=side,
                    time_in_force=TimeInForce.DAY,
                ))
                # ch05.md:493 — move the stop to breakeven on the remaining half.
                state.setdefault(symbol, {})["scaled"] = True
                state[symbol]["breakeven"] = True
                print(f"[{timestamp()}] STOP -> BREAKEVEN on the remaining "
                      f"{abs(qty) - half} {symbol}")
                actions.append((symbol, "SCALE_OUT"))
                continue

        # ch05.md:495 — the flow signal has a shelf life. Five sessions, then out.
        age = position_age_days(symbol)
        if age is not None and age >= TIME_LIMIT_DAYS:
            print(f"[{timestamp()}] TIME LIMIT: {symbol} open {age} trading days "
                  f"without hitting stop or target. Closing at market.")
            alpaca.close_position(symbol)
            state.pop(symbol, None)
            actions.append((symbol, "TIME_LIMIT"))

    _save_exit_state(state)
    return actions


# --------------------------------------------------------------------------- #
#  The loop
# --------------------------------------------------------------------------- #
def run_flow_trader(single_cycle: bool = True):
    """Main loop. Defaults to ONE cycle — what the book itself runs (ch05.md:74).

    Pass `single_cycle=False` (or `--loop`) for the real 30-second polling loop.
    """
    banner()
    print(f"[{timestamp()}] === OPTIONS FLOW TRADER STARTED ===")
    print(f"[{timestamp()}] Confidence threshold: {CONFIDENCE_THRESHOLD}%")
    print(f"[{timestamp()}] Min premium: ${MIN_PREMIUM:,}")
    print(f"[{timestamp()}] Max position: {MAX_POSITION_PCT * 100}% of account")
    print(f"[{timestamp()}] Max DTE: {MAX_DTE} days")
    print(f"[{timestamp()}] Polling every {POLL_INTERVAL}s")
    print(f"[{timestamp()}] Mode: {'single cycle' if single_cycle else 'continuous'}")
    print(f"[{timestamp()}] Listening for whale activity...\n")

    seen_events = set()
    traded = []

    while True:
        try:
            check_exits()
            events = get_live_flow()

            for event in events:
                event_key = (f"{event.get('ticker', '')}_"
                             f"{event.get('strike', '')}_"
                             f"{event.get('timestamp', '')}")
                if event_key in seen_events:
                    continue
                seen_events.add(event_key)

                ticker = event.get("ticker", "???")
                premium = event.get("total_premium", 0)
                vol_oi = event.get("volume_oi_ratio", 0)
                kind = "SWEEP" if event.get("is_sweep") else (
                    "FLOOR" if event.get("is_floor") else "TRADE")

                print(f"[{timestamp()}] ALERT: Unusual {kind} detected")
                print(f"[{timestamp()}] Ticker: {ticker} | "
                      f"Strike: ${event.get('strike', 0)} | "
                      f"Exp: {event.get('expiry', 'N/A')}")
                print(f"[{timestamp()}] Volume: {event.get('volume', 0):,} | "
                      f"OI: {event.get('open_interest', 0):,} | Ratio: {vol_oi}x")
                print(f"[{timestamp()}] Premium: ${premium:,} | "
                      f"Option type: {event.get('type', '').upper()}")
                print(f"[{timestamp()}] Analyzing with Claude...")

                analysis = analyze_flow_event(event)
                if not analysis:
                    print(f"[{timestamp()}] Analysis failed. Skipping.\n")
                    continue

                adj = adjust_confidence(
                    ticker=ticker,
                    confidence=analysis.get("confidence", 0),
                    direction=analysis.get("direction", ""),
                    dark_pool_read=analysis.get("dark_pool_read"),
                )
                if not adj.tradeable:
                    print(f"[{timestamp()}] BLOCKED: {adj.summary()}\n")
                    log_trade(analysis, event, None, 0, 0)
                    continue
                if adj.confidence != adj.raw_confidence:
                    print(f"[{timestamp()}] CHAPTER 3 ADJUSTMENT: "
                          f"{adj.raw_confidence:.0f} -> {adj.confidence:.0f} "
                          f"({adj.summary()})")
                analysis["confidence"] = adj.confidence

                direction = analysis.get("direction", "N/A")
                print(f"[{timestamp()}] Direction: {direction} | "
                      f"Confidence: {adj.confidence:.0f}%")

                if adj.confidence >= CONFIDENCE_THRESHOLD:
                    print(f"[{timestamp()}] TRADING: Confidence above threshold. "
                          f"Executing...")
                    result = execute_trade(analysis, event)
                    if result:
                        print(f"[{timestamp()}] Order filled. Position opened.\n")
                        traded.append(ticker)
                else:
                    print(f"[{timestamp()}] PASS: Confidence below threshold "
                          f"({CONFIDENCE_THRESHOLD}%). Logged only.\n")
                    log_trade(analysis, event, None, 0, 0)

            if len(seen_events) > 1000:
                seen_events = set(list(seen_events)[-500:])

            if single_cycle:
                print(f"[{timestamp()}] Cycle complete. "
                      f"{len(traded)} trade(s) placed: {traded or 'none'}")
                print(f"[{timestamp()}] Trade log: {artifact(TRADE_LOG_FILE)}")
                return traded

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n[{timestamp()}] Bot stopped by user.")
            return traded
        except Exception as e:  # noqa: BLE001
            print(f"[{timestamp()}] ERROR: {e}")
            if single_cycle:
                raise
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_flow_trader(single_cycle="--loop" not in sys.argv)
