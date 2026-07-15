"""Chapter 3's analysis contract, as code.

Chapter 3 prints no Python, but it is not a prose chapter — it is the contract
ch04, ch05 and ch08 consume. It sets the five-tier signal hierarchy, the 70%
trade threshold, and three rules the author states are already running in his
bots:

* **Liquidity floor** — "I don't let my bots trade anything with average daily
  volume below 1 million shares, and you shouldn't either." (ch03.md:87)
* **Geopolitical filter** — "reduces confidence by 15 points" for Chinese ADRs,
  Russia-exposed names, and companies with >40% of revenue from a single foreign
  government's jurisdiction. (ch03.md:111)
* **Tier-1 / Tier-2 conflict** — "if Tier 1 and Tier 2 signals conflict in
  opposite directions, reduce overall confidence by 20 points and flag for
  manual review." (ch03.md:147)

**None of the three appears in any code the book prints.** This module is where
the repo puts them back. All three are **default-ON** and all three push the bot
toward *fewer* trades, which is the conservative direction. See
`docs/book-deviations.md` (#14) for the full reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from utils.offline import get_yfinance

__all__ = [
    "MIN_AVG_DAILY_VOLUME",
    "GEOPOLITICAL_PENALTY",
    "TIER_CONFLICT_PENALTY",
    "TRADE_THRESHOLD",
    "GEOPOLITICAL_TICKERS",
    "Adjustment",
    "adjust_confidence",
    "average_daily_volume",
    "passes_liquidity_floor",
]

#: ch03.md:87 — no bot trades a name thinner than this.
MIN_AVG_DAILY_VOLUME = 1_000_000

#: ch03.md:111
GEOPOLITICAL_PENALTY = 15

#: ch03.md:147
TIER_CONFLICT_PENALTY = 20

#: ch03.md:141, ch05.md:108 — the gate every bot in the book trades against.
TRADE_THRESHOLD = 70

#: The geopolitical filter needs a list of names it applies to, and ch03 defines
#: the *category* ("any Chinese ADR, any Russian-exposed company, any company
#: with more than 40% revenue from a single foreign government's jurisdiction")
#: without printing a list. There is no free API that answers "is this a Chinese
#: ADR", so the repo ships an explicit, editable, obviously-incomplete roster
#: rather than fabricating a data source. **Edit it for your own universe.**
GEOPOLITICAL_TICKERS: set[str] = {
    "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "TME", "BILI",
    "NTES", "TCOM", "YUMC", "ZTO", "LU", "IQ", "VIPS", "EDU", "TAL",
}


@dataclass
class Adjustment:
    """The result of applying ch03's post-filters to a Claude confidence score."""

    ticker: str
    raw_confidence: float
    confidence: float
    tradeable: bool = True
    manual_review: bool = False
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.notes:
            return ""
        return "; ".join(self.notes)


def average_daily_volume(ticker: str, lookback: str = "1mo") -> float | None:
    """Average daily share volume from yfinance. `None` when unavailable.

    yfinance, not Claude — same argument ch09 makes for sector and earnings
    (ch09.md:469-477): this is a public data field, not a judgment call.
    """
    yf = get_yfinance()
    try:
        hist = yf.Ticker(ticker).history(period=lookback)
    except Exception:
        return None
    if hist is None or getattr(hist, "empty", True) or "Volume" not in hist:
        return None
    try:
        return float(hist["Volume"].mean())
    except Exception:
        return None


def passes_liquidity_floor(ticker: str,
                           floor: int = MIN_AVG_DAILY_VOLUME) -> tuple[bool, str]:
    """ch03.md:87 — reject anything thinner than 1M average daily shares.

    An unknown ADV is treated as a **pass with a warning**, not a silent block:
    refusing to trade every ticker yfinance has never heard of would quietly
    disable the bot rather than protect it.
    """
    adv = average_daily_volume(ticker)
    if adv is None:
        return True, f"ADV unknown for {ticker}; liquidity floor not enforced"
    if adv < floor:
        return False, (f"{ticker} average daily volume {adv:,.0f} is below the "
                       f"{floor:,} floor (ch03)")
    return True, ""


def adjust_confidence(ticker: str, confidence: float, direction: str,
                      dark_pool_read: str | None = None) -> Adjustment:
    """Apply ch03's three rules to a raw Claude confidence score.

    Args:
        ticker: the underlying.
        confidence: Claude's 0-100 score, straight from the analysis call.
        direction: "BULLISH" or "BEARISH" — Claude's Tier-1 (options flow) read.
        dark_pool_read: Claude's Tier-2 read, if the analysis returned one.
            "BULLISH" / "BEARISH" / "UNKNOWN" / None. Anything but a clean
            opposite-direction call is treated as no conflict.

    Returns:
        An `Adjustment`. `tradeable=False` means the trade is blocked outright
        (the liquidity floor), not merely marked down.
    """
    adj = Adjustment(ticker=ticker, raw_confidence=float(confidence),
                     confidence=float(confidence))

    liquid, note = passes_liquidity_floor(ticker)
    if not liquid:
        adj.tradeable = False
        adj.confidence = 0.0
        adj.notes.append(f"LIQUIDITY FLOOR: {note}")
        return adj
    if note:
        adj.notes.append(note)

    if ticker.upper() in GEOPOLITICAL_TICKERS:
        adj.confidence -= GEOPOLITICAL_PENALTY
        adj.notes.append(
            f"GEOPOLITICAL FILTER: -{GEOPOLITICAL_PENALTY} (ch03) — no options "
            f"signal prices a regulatory headline that has not happened yet"
        )

    tier1 = (direction or "").upper()
    tier2 = (dark_pool_read or "UNKNOWN").upper()
    opposed = {("BULLISH", "BEARISH"), ("BEARISH", "BULLISH")}
    if (tier1, tier2) in opposed:
        adj.confidence -= TIER_CONFLICT_PENALTY
        adj.manual_review = True
        adj.notes.append(
            f"TIER1<->TIER2 CONFLICT: -{TIER_CONFLICT_PENALTY} (ch03) — flow says "
            f"{tier1.lower()}, dark pool says {tier2.lower()}; flagged for manual "
            f"review. A sweep against institutional distribution is often the hedge."
        )

    adj.confidence = max(0.0, min(100.0, adj.confidence))
    return adj
