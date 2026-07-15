"""Risk management — Chapter 9. Five hard rules nothing can override.

    python risk/risk_manager.py

This is not a bot. It is the gatekeeper that sits between every bot's decision
and Alpaca's order API (ch09.md:423). **No Claude calls anywhere in this module**
— every check is math or public data (ch09.md:99).

    Rule 1  Never risk more than 2% of the account on one trade.
    Rule 2  Never lose more than 6% of the account in one day.
    Rule 3  Every position gets a stop-loss at entry. Default 3%.
    Rule 4  No single sector above 40% of portfolio value.
    Rule 5  No trading within 3 days of earnings.

Sizing is quarter-Kelly, capped by the 2% rule, with a **zero floor**: when Kelly
is zero or negative there is no edge, and zero shares is the right answer. It
never rounds up to one share.

FOUR DEVIATIONS FROM THE PRINTED MODULE (docs/book-deviations.md)
-----------------------------------------------------------------
* **#10** — `evaluate_trade()` gains `stop_loss_pct`. The printed signature has
  none, so the chapter's own "widen TSLA to 5%" advice (ch09.md:417-419, "Use
  it.") is unreachable through the gatekeeper the book tells every bot to call.
  `checks["stop_loss"]` and `checks["max_loss"]` also hard-code the default and
  would misreport a custom stop. The arithmetic in ch09 is all correct — only the
  plumbing was missing.
* **#11** — Rule 4 promises REDUCE ("reduces the position to fit within the 40%
  cap, or rejects it entirely", ch09.md:23); the printed code only ever BLOCKS,
  and `remaining_capacity` is computed, returned as a *formatted string*, and
  never read. The REDUCE path is implemented, `remaining_capacity` is a float,
  and there is a `REDUCED` verdict. (ch08's Risk agent already has REDUCE, so
  this is the book's own idiom.)
* **#12** — `check_sector_concentration()` ignored the *proposed* position and
  summed only existing holdings, so the module's own worked example approves a
  $66,600 NVDA position on a $100K account (66.6% in one tech name) because
  concentration is 0 at the time of the check. The chapter's own
  `check_correlation()` (ch09.md:519-524) *does* include the proposed trade. This
  module does too.
* **#5 (NOT a bug — do not "fix" it)** — ch05's `MAX_POSITION_PCT = 0.02` is 2% as
  *notional*. `MAX_RISK_PER_TRADE = 0.02` here is 2% as *risk* (position x stop
  width), so a $100K account supports a $66,600 position at a 3% stop. Same
  number, different quantity. The book reconciles them deliberately: this module
  is the override. Both ship.

Educational software. Not financial advice. Paper mode by default. See DISCLAIMER.md.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from utils import banner  # noqa: E402
from utils.offline import (  # noqa: E402
    OfflineTradingClient,
    OrderSide,
    TimeInForce,
    TrailingStopOrderRequest,
    get_trading_client,
    get_yfinance,
    offline_enabled,
)

load_dotenv()
alpaca = get_trading_client()

# --- Hard limits - DO NOT MODIFY WITHOUT BACKTESTING (ch09.md:120-127) ------
MAX_RISK_PER_TRADE = 0.02        # 2% of account, as RISK (position x stop width)
MAX_DAILY_LOSS = 0.06            # 6% of account
DEFAULT_STOP_LOSS = 0.03         # 3% stop-loss
MAX_SECTOR_CONCENTRATION = 0.40  # 40% sector cap
EARNINGS_BLACKOUT_DAYS = 3       # No trading 3 days before earnings
USE_KELLY = True                 # Use Kelly Criterion for sizing
KELLY_FRACTION = 0.25            # Quarter-Kelly

#: ch09.md:547-552 — the 6% default assumes a $10K-$100K account. This table is a
#: REFERENCE, not an automatic override: the chapter says "Adjust the
#: MAX_DAILY_LOSS constant in risk_manager.py as your capital grows"
#: (ch09.md:554), i.e. you edit the constant, the code does not scale it for you.
#: `check_daily_loss_limit()` uses MAX_DAILY_LOSS exactly as printed.
CIRCUIT_BREAKER_BY_ACCOUNT_SIZE = [
    (2_000, 0.10),          # under $2K: you need room to learn
    (10_000, 0.08),
    (50_000, 0.06),         # the default
    (float("inf"), 0.04),   # above $50K: tighter
]

#: ch09.md:541-543 — the other two circuit breakers.
CONSECUTIVE_LOSS_LIMIT = 5       # 5 losses in a row -> 24h pause
UNPARSEABLE_JSON_LIMIT = 3       # 3 bad model responses in a row -> pause + alert

SECTOR_CACHE: dict[str, str] = {}


def daily_loss_limit_for(account_value: float) -> float:
    """The threshold ch09.md:549-552 RECOMMENDS for this account size.

    Advisory only. `check_daily_loss_limit()` enforces `MAX_DAILY_LOSS` as
    printed; edit the constant yourself when your capital changes.
    """
    for ceiling, limit in CIRCUIT_BREAKER_BY_ACCOUNT_SIZE:
        if account_value < ceiling:
            return limit
    return MAX_DAILY_LOSS


class RiskManager:
    """The gatekeeper. Every bot calls `evaluate_trade()` before it orders."""

    def __init__(self, client=None):
        # Dependency-injected broker client so tests (and the demo's clean-slate
        # worked examples) can run against a portfolio of their choosing.
        self.client = client if client is not None else alpaca
        self.daily_start_value: float | None = None
        self.daily_pnl = 0.0
        self.trades_today: list = []
        self.blocked_trades: list = []
        self.consecutive_losses = 0
        self._sector_cache: dict[str, str] = {}

    # -- day bookkeeping ---------------------------------------------------
    def initialize_day(self) -> float:
        """Set the starting portfolio value for daily-loss tracking."""
        account = self.client.get_account()
        self.daily_start_value = float(account.portfolio_value)
        self.daily_pnl = 0.0
        self.trades_today = []
        self.blocked_trades = []
        return self.daily_start_value

    def get_current_portfolio(self) -> dict:
        account = self.client.get_account()
        positions = self.client.get_all_positions()
        total = float(account.portfolio_value)
        return {
            "cash": float(account.cash),
            "value": total,
            "positions": [{
                "symbol": p.symbol,
                "qty": int(p.qty),
                "market_value": float(p.market_value),
                "pct": float(p.market_value) / total * 100 if total else 0.0,
            } for p in positions],
        }

    # -- Rule 1: position sizing ------------------------------------------
    def calculate_position_size(self, ticker, entry_price, stop_loss_pct=None,
                                win_rate=0.537, profit_factor=1.79) -> int:
        """Quarter-Kelly, capped by the 2% risk rule, floored at ZERO.

        Kelly % = W - (1-W)/R. On the ch06 backtest (53.7% / 1.79) that is 27.8%
        full Kelly, 6.95% at quarter-Kelly — which on a $100K account at a 3% stop
        would size 1,158 shares of a $200 stock. The 2% cap binds instead.

        There is **no hard floor**. If Kelly returns 0 (Scenario 3: 48% win rate,
        0.9 profit factor -> -9.8%), shares stays 0 and the caller skips the trade.
        Rounding "no edge" up to one share would defeat the entire rule.
        """
        account = self.client.get_account()
        account_value = float(account.portfolio_value)

        sl = stop_loss_pct or DEFAULT_STOP_LOSS
        risk_per_share = entry_price * sl
        if risk_per_share <= 0:
            return 0

        max_risk_dollars = account_value * MAX_RISK_PER_TRADE
        max_shares_cap = int(max_risk_dollars / risk_per_share)

        if USE_KELLY and win_rate > 0 and profit_factor > 0:
            kelly = win_rate - (1 - win_rate) / profit_factor
            kelly = max(0, kelly * KELLY_FRACTION)
            kelly_risk = account_value * kelly
            kelly_shares = int(kelly_risk / risk_per_share)
            shares = min(max_shares_cap, kelly_shares)
        else:
            shares = max_shares_cap

        return max(0, shares)

    # -- Rule 2: daily loss ------------------------------------------------
    def check_daily_loss_limit(self) -> dict:
        if self.daily_start_value is None:
            self.initialize_day()

        account = self.client.get_account()
        current_value = float(account.portfolio_value)
        daily_change = ((current_value - self.daily_start_value)
                        / self.daily_start_value)
        limit = MAX_DAILY_LOSS   # as printed; see CIRCUIT_BREAKER_BY_ACCOUNT_SIZE

        if daily_change <= -limit:
            return {
                "allowed": False,
                "reason": (f"Daily loss limit hit: {daily_change:.1%} "
                           f"(limit: -{limit:.0%})"),
            }
        return {"allowed": True, "daily_pnl": f"{daily_change:.2%}",
                "limit": f"-{limit:.0%}"}

    # -- Rule 4: sector concentration -------------------------------------
    def _get_sector(self, ticker: str) -> str:
        """yfinance, with an instance cache. Not Claude.

        Sector is a public data field, not a judgment call. Asking Claude costs
        real money on every multi-agent cycle for an answer yfinance gives free
        (ch09.md:469-477).
        """
        if ticker in self._sector_cache:
            return self._sector_cache[ticker]
        yf = get_yfinance()
        try:
            sector = yf.Ticker(ticker).info.get("sector", "Unknown")
        except Exception:  # noqa: BLE001
            sector = "Unknown"
        self._sector_cache[ticker] = sector
        return sector

    def check_sector_concentration(self, ticker, proposed_value: float = 0.0) -> dict:
        """Would this trade push its sector past 40% of the portfolio?

        DEVIATION #12: `proposed_value` is included in the sector total. The
        printed version sums only *existing* holdings, so with an empty portfolio
        concentration is 0 and a $66,600 single-name position sails through a 40%
        cap. The chapter's own `check_correlation()` includes the proposed trade;
        so does this.
        """
        sector = self._get_sector(ticker)
        portfolio = self.get_current_portfolio()
        total_value = portfolio["value"]

        existing = sum(pos["market_value"] for pos in portfolio["positions"]
                       if self._get_sector(pos["symbol"]) == sector)
        sector_total = proposed_value + existing
        concentration = sector_total / total_value if total_value > 0 else 0.0

        # Capacity left in this sector AFTER existing holdings. Returned as a
        # float, not a formatted string, because the REDUCE path actually reads it
        # (DEVIATION #11).
        remaining_capacity = max(
            0.0, MAX_SECTOR_CONCENTRATION * total_value - existing)

        if concentration >= MAX_SECTOR_CONCENTRATION:
            return {
                "allowed": False,
                "sector": sector,
                "current_concentration": existing / total_value if total_value else 0.0,
                "projected_concentration": concentration,
                "remaining_capacity": remaining_capacity,
                "reason": (f"Sector {sector} would be {concentration:.0%} with this "
                           f"trade (limit: {MAX_SECTOR_CONCENTRATION:.0%}); "
                           f"${remaining_capacity:,.0f} of capacity remains"),
            }
        return {
            "allowed": True,
            "sector": sector,
            "current_concentration": existing / total_value if total_value else 0.0,
            "projected_concentration": concentration,
            "remaining_capacity": remaining_capacity,
        }

    # -- Rule 5: earnings blackout ----------------------------------------
    def check_earnings_blackout(self, ticker) -> dict:
        """yfinance's calendar, not Claude.

        The vanilla Messages API has no live earnings calendar — Claude either
        refuses or guesses from training data that is months stale by publication
        (ch09.md:255-262).
        """
        yf = get_yfinance()
        try:
            cal = yf.Ticker(ticker).calendar
        except Exception:  # noqa: BLE001
            cal = None

        next_earnings = None
        if isinstance(cal, dict) and cal.get("Earnings Date"):
            ed = cal["Earnings Date"]
            next_earnings = ed[0] if isinstance(ed, list) and ed else ed
        elif cal is not None and hasattr(cal, "loc"):
            try:
                if "Earnings Date" in cal.index:
                    ed = cal.loc["Earnings Date"]
                    next_earnings = (ed.iloc[0] if hasattr(ed, "iloc")
                                     else ed[0] if hasattr(ed, "__getitem__") else ed)
            except Exception:  # noqa: BLE001
                next_earnings = None

        if next_earnings is None:
            return {"allowed": True, "earnings": "unknown"}

        next_date = (next_earnings.date() if hasattr(next_earnings, "date")
                     else next_earnings)
        try:
            days_until = (next_date - date.today()).days
        except Exception:  # noqa: BLE001
            return {"allowed": True, "earnings": "unparseable"}

        if 0 <= days_until <= EARNINGS_BLACKOUT_DAYS:
            return {
                "allowed": False,
                "reason": (f"{ticker} has earnings in {days_until} day(s). "
                           f"Blackout period active."),
            }
        return {"allowed": True, "earnings_in_days": days_until}

    # -- the gate ----------------------------------------------------------
    def evaluate_trade(self, ticker, entry_price, direction="BUY",
                       stop_loss_pct=None, win_rate=0.537,
                       profit_factor=1.79) -> dict:
        """Run all five checks. The only verdict that trades is APPROVED/REDUCED.

        Order (ch09.md:310-357): daily loss -> earnings blackout -> sector
        concentration -> position sizing -> positive-edge gate.

        `stop_loss_pct` is DEVIATION #10: without it, the chapter's own advice to
        widen TSLA's stop to 5% cannot be reached through the sanctioned path.

        Verdicts:
            APPROVED           trade it at `approved_shares`
            REDUCED            trade it, but smaller — the sector cap bound first
            BLOCKED            a hard rule said no
            REJECTED-NO-EDGE   Kelly <= 0, or the risk budget can't buy one share
        """
        sl = stop_loss_pct or DEFAULT_STOP_LOSS
        checks = {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "entry_price": entry_price,
        }

        # rule 1: daily loss limit (halts new trades before we size anything)
        daily = self.check_daily_loss_limit()
        checks["daily_loss"] = daily
        if not daily["allowed"]:
            return self._block(checks, daily["reason"])

        # rule 2: earnings blackout
        earnings = self.check_earnings_blackout(ticker)
        checks["earnings"] = earnings
        if not earnings["allowed"]:
            return self._block(checks, earnings["reason"])

        # rule 4 runs before rule 3: the sector cap needs the proposed size first
        shares = self.calculate_position_size(
            ticker, entry_price, stop_loss_pct=sl,
            win_rate=win_rate, profit_factor=profit_factor,
        )

        # rule 3: sector concentration, counting the proposed position too (#12)
        sector = self.check_sector_concentration(
            ticker, proposed_value=shares * entry_price)
        checks["sector"] = sector

        reduced = False
        if not sector["allowed"]:
            # DEVIATION #11: Rule 4 promises REDUCE before it rejects. Cap the
            # position at whatever capacity is left in the sector; only block when
            # nothing fits.
            capacity_shares = int(sector["remaining_capacity"] / entry_price) \
                if entry_price > 0 else 0
            if capacity_shares <= 0:
                return self._block(checks, sector["reason"])
            shares = min(shares, capacity_shares)
            reduced = True
            checks["reduce_reason"] = (
                f"Capped at {shares} shares to keep {sector['sector']} under the "
                f"{MAX_SECTOR_CONCENTRATION:.0%} cap "
                f"(${sector['remaining_capacity']:,.0f} of capacity left)")
            if shares <= 0:
                return self._block(checks, sector["reason"])

        # rule 5: positive-edge gate. Kelly returned 0, so there is nothing to
        # approve. Reject explicitly rather than logging an APPROVED trade with
        # zero shares.
        if shares <= 0:
            checks["approved_shares"] = 0
            checks["verdict"] = "REJECTED-NO-EDGE"
            checks["block_reason"] = (
                "Position sizing returned 0 shares; Kelly is non-positive (no "
                "edge) or the 2% risk budget is too small at this price + "
                "stop-loss combination."
            )
            self.blocked_trades.append(checks)
            return checks

        checks["approved_shares"] = shares
        checks["stop_loss"] = f"{sl:.0%}"
        checks["stop_loss_pct"] = sl
        checks["max_loss"] = f"${entry_price * shares * sl:,.2f}"
        checks["position_value"] = f"${entry_price * shares:,.2f}"
        checks["verdict"] = "REDUCED" if reduced else "APPROVED"
        self.trades_today.append(checks)
        return checks

    def _block(self, checks: dict, reason: str) -> dict:
        checks["verdict"] = "BLOCKED"
        checks["block_reason"] = reason
        checks["approved_shares"] = 0
        self.blocked_trades.append(checks)
        return checks

    # -- trailing stop -----------------------------------------------------
    def trailing_stop_order(self, ticker: str, qty: int, trail_percent: float = 3.0):
        """Native Alpaca trailing stop (ch09.md:454-465).

        Set this after a position reaches 2% profit. Below 2%, the fixed
        stop-loss protects the downside; above it, the trailing stop ratchets up
        while giving the trade room to run.
        """
        return TrailingStopOrderRequest(
            symbol=ticker, qty=qty, side=OrderSide.SELL,
            trail_percent=trail_percent, time_in_force=TimeInForce.GTC,
        )


# --------------------------------------------------------------------------- #
#  Standalone helpers (ch09.md:481-529) — drop into any module without the class
# --------------------------------------------------------------------------- #
def get_sector(ticker: str) -> str:
    if ticker in SECTOR_CACHE:
        return SECTOR_CACHE[ticker]
    yf = get_yfinance()
    try:
        sector = yf.Ticker(ticker).info.get("sector", "Unknown")
    except Exception:  # noqa: BLE001
        sector = "Unknown"
    SECTOR_CACHE[ticker] = sector
    return sector


def has_earnings_within(ticker: str, days: int = 3) -> bool:
    """Earnings check via a real calendar source, not Claude."""
    yf = get_yfinance()
    try:
        cal = yf.Ticker(ticker).calendar
    except Exception:  # noqa: BLE001
        return False
    if not isinstance(cal, dict) or "Earnings Date" not in cal:
        return False
    ed = cal["Earnings Date"]
    next_earnings = ed[0] if isinstance(ed, list) and ed else None
    if next_earnings is None:
        return False
    next_date = (next_earnings.date() if hasattr(next_earnings, "date")
                 else next_earnings)
    days_until = (next_date - datetime.now().date()).days
    return 0 <= days_until <= days


def check_correlation(ticker: str, proposed_value: float, portfolio: dict):
    """The pairwise correlation guard, if you want one beyond sector.

    Note this printed helper always included the proposed position — which is
    exactly the guard `check_sector_concentration()` was missing (#12).
    """
    sector = get_sector(ticker)
    sector_total = proposed_value
    for pos in portfolio["positions"]:
        if get_sector(pos["symbol"]) == sector:
            sector_total += pos["market_value"]
    concentration = sector_total / portfolio["value"]
    if concentration > MAX_SECTOR_CONCENTRATION:
        return False, f"{sector} would be {concentration:.0%} (limit 40%)"
    return True, f"{sector} at {concentration:.0%}"


# --------------------------------------------------------------------------- #
#  Demo
# --------------------------------------------------------------------------- #
def clean_slate_client():
    """A $100K paper account with NO open positions.

    This is the portfolio ch09's worked examples silently assume when they size
    NVDA at 72 shares. Offline you get the stub; live you get your real account,
    positions and all — which is the whole point of DEVIATION #12.
    """
    if offline_enabled():
        return OfflineTradingClient(paper=True, positions=[])
    return alpaca


def demo_risk_check():
    """Run sample trades through the module and show what gets blocked.

    Part 1 reproduces ch09's printed position-sizing arithmetic exactly.
    Part 2 sends the same trades through `evaluate_trade()`, the gatekeeper every
    bot is told to call — and the 40% sector cap cuts two of them down, because a
    $66,600 position in one tech name on a $100K account is 66.6% concentration.
    That gap between Part 1 and Part 2 IS deviation #12.
    """
    banner()
    client = clean_slate_client()
    rm = RiskManager(client=client)
    rm.initialize_day()

    print("=== RISK MANAGEMENT MODULE ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Daily start value: ${rm.daily_start_value:,.2f} (no open positions)")
    print(f"Max risk per trade: {MAX_RISK_PER_TRADE:.0%} (as RISK, not notional)")
    print(f"Max daily loss: {MAX_DAILY_LOSS:.0%}")
    print(f"Kelly fraction: {KELLY_FRACTION:.0%} (quarter-Kelly)\n")

    print("--- Kelly Criterion (ch09.md:59-77) ---")
    for label, w, pf in [("S1 screener strategy", 0.537, 1.79),
                         ("S2 weaker strategy  ", 0.52, 1.3),
                         ("S3 no edge          ", 0.48, 0.9)]:
        kelly = w - (1 - w) / pf
        quarter = max(0.0, kelly * KELLY_FRACTION)
        verdict = "bet ZERO" if kelly <= 0 else f"quarter-Kelly {quarter:.2%}"
        print(f"  {label}: {w:.1%} win / {pf} PF -> Kelly {kelly:+.3f} -> {verdict}")

    print("\n--- Part 1: position sizing (Rule 1 only) ---")
    sizes = [
        ("NVDA", 925.00, None), ("F", 12.00, None), ("TSLA", 240.00, 0.05),
    ]
    for ticker, price, sl in sizes:
        shares = rm.calculate_position_size(ticker, price, stop_loss_pct=sl)
        width = sl or DEFAULT_STOP_LOSS
        print(f"  {ticker:<5} ${price:>7,.2f} @ {width:.0%} stop -> "
              f"${price * width:>6,.2f}/share risk -> {shares:>6,} shares "
              f"(${shares * price:,.0f} position)")

    print("\n--- Part 2: the same trades through evaluate_trade() ---")
    cases = [
        ("NVDA at $925, default 3% stop", {"ticker": "NVDA", "entry_price": 925.00}),
        ("F at $12, default 3% stop", {"ticker": "F", "entry_price": 12.00}),
        ("TSLA at $240, WIDENED 5% stop (ch09.md:417 -- 'Use it.')",
         {"ticker": "TSLA", "entry_price": 240.00, "stop_loss_pct": 0.05}),
        ("NVDA with no-edge inputs (48% win / 0.9 PF)",
         {"ticker": "NVDA", "entry_price": 925.00, "win_rate": 0.48,
          "profit_factor": 0.9}),
        ("MU at $118 (earnings inside the 3-day blackout)",
         {"ticker": "MU", "entry_price": 118.00}),
    ]
    for label, kwargs in cases:
        result = rm.evaluate_trade(**kwargs)
        print(f"  {label}")
        print(f"    Verdict: {result['verdict']}")
        if result["verdict"] in ("APPROVED", "REDUCED"):
            print(f"    Approved shares: {result['approved_shares']:,}  "
                  f"| Position: {result['position_value']}  "
                  f"| Stop: {result['stop_loss']}  "
                  f"| Max loss: {result['max_loss']}")
            if result["verdict"] == "REDUCED":
                print(f"    Reduced: {result['reduce_reason']}")
        else:
            print(f"    Reason: {result['block_reason']}")
        print()

    print(f"Approved/reduced: {len(rm.trades_today)} | "
          f"Blocked/rejected: {len(rm.blocked_trades)}")
    print("\nWhy NVDA and F come out smaller in Part 2 than Part 1: a $66,600 "
          "position\nin one name is 66.6% of a $100K account. The 40% sector cap "
          "binds first.\nThe printed check ignores the proposed position and would "
          "have waved both through.")
    return rm


if __name__ == "__main__":
    demo_risk_check()
