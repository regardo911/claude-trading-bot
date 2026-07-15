"""Prediction-market analyzer — Chapter 7. **Read-only. It never submits a bet.**

    python prediction/prediction_analyzer.py

Gamma discovery -> liquidity + analyzability filter -> base-rate probability
estimate -> expected value -> ranked opportunities written to disk. *You* place
the bet, manually, through Polymarket's UI after KYC (or via `py-clob-client` if
you wired a Polygon wallet yourself).

WHY THERE IS NO ORDER PATH IN THIS FILE
---------------------------------------
"The book is not going to ship an unauthenticated trading bot for a
CFTC-regulated venue." (ch07.md:39) and, in the build prompt itself, "**Do NOT
submit any orders.**" (ch07.md:64). That refusal is deliberate and this repo
honors it: `prediction_analyzer.py` imports nothing that can place an order, and
a test enforces that it never will. `prediction/kalshi_client.py` is a separate
module, is not imported here, and refuses to place an order without an explicit
code-level live opt-in.

TWO DEVIATIONS (docs/book-deviations.md)
----------------------------------------
* **#1** — `MIN_VOLUME = 10000` is declared in the chapter and then referenced by
  nothing. Appendix B lists it as a live tunable. This module actually filters on
  it; without it, the analyzer happily scores $0-volume markets you could never
  get filled in.
* **#9** — `suggested_bet` is a three-way contradiction between the code, the
  prose, and the two printed examples. This module ships the **code as printed**
  (`min(MAX_BET_SIZE, MAX_BET_SIZE * abs(gap))`) — the only formula that
  reproduces any printed output exactly. Read the erratum: under it, `min()`
  binds only at a 100% gap, so **MAX_BET_SIZE is a scaling coefficient, not a
  cap**, which contradicts both its own comment and the word "cap" in the prose.
  A qualifying 10% gap sizes a $5 bet, not the $25 the prose promises.

Educational software. Not financial advice. See DISCLAIMER.md.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from utils import artifact, banner  # noqa: E402
from utils.offline import get_anthropic, http_get_json  # noqa: E402

load_dotenv()
claude = get_anthropic()

# --- Constants (ch07.md:85-88, Appendix B Template 4) ----------------------
POLYMARKET_GAMMA = "https://gamma-api.polymarket.com"   # discovery, no auth
MIN_PROBABILITY_GAP = 0.10   # 10% minimum gap to bet
MAX_BET_SIZE = 50            # see the #9 erratum above: a coefficient, not a cap
MIN_VOLUME = 10000           # minimum market volume — ENFORCED here (see #1)
MODEL = "claude-sonnet-4-6"

# Polymarket exposes two API surfaces. Gamma (above) is the canonical *discovery*
# endpoint. The CLOB is for orderbook + trading, and this module never touches it
# — not even to read. Mixing the two is the number-one Polymarket integration
# error (appendices.md:200); shipping an order path here would be worse than an
# error. See docs/05-prediction.md.


def parse_outcome_prices(raw):
    """Gamma's `outcomePrices` — a JSON-encoded string in the docs, a real array
    in live responses. Handle both.

    Always returns exactly `[yes_price, no_price]` as floats; defaults to
    `[0.5, 0.5]` on parse failure, missing data, or unexpected length, so callers
    can safely unpack without a ValueError. Index 0 is YES, index 1 is NO. There
    is **no `current_price` field** (appendices.md:205).
    """
    DEFAULT = [0.5, 0.5]
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return DEFAULT
    if isinstance(raw, list) and len(raw) == 2:
        try:
            return [float(raw[0]), float(raw[1])]
        except (ValueError, TypeError):
            return DEFAULT
    return DEFAULT


def get_active_markets():
    """Fetch active Polymarket contracts from the Gamma Markets API.

    No Claude fallback here on purpose: a `messages.create('list the top 20
    Polymarket contracts')` call returns hallucinated contracts — fake questions
    at fake prices — that the rest of this script would then process as truth. If
    Gamma is down, the right answer is no data, not fake data.
    """
    try:
        # Gamma expects string "true"/"false", not Python booleans.
        markets = http_get_json(
            f"{POLYMARKET_GAMMA}/markets",
            params={"active": "true", "closed": "false", "limit": 100},
            timeout=15,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Gamma REST error: {e}; skipping cycle.")
        return []
    # Gamma returns a JSON array directly, not a {"data": [...]} wrapper.
    return markets if isinstance(markets, list) else []


def filter_liquid(markets):
    """DEVIATION #1 — the liquidity floor the chapter declares and never uses.

    `volume` arrives as a stringified float, so it needs the cast
    (`polymarket-gamma-truth.md`, migration note 6).
    """
    kept = []
    for m in markets:
        try:
            volume = float(m.get("volume", 0) or 0)
        except (TypeError, ValueError):
            volume = 0.0
        if volume >= MIN_VOLUME:
            kept.append(m)
    dropped = len(markets) - len(kept)
    if dropped:
        print(f"Dropped {dropped} market(s) below the ${MIN_VOLUME:,} volume floor.")
    return kept


def filter_analyzable(markets):
    """Keep only contracts public data can inform an estimate on."""
    if not markets:
        return []
    response = claude.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Here are prediction market contracts:
            {json.dumps(markets[:50], indent=2)}

            Filter this list to ONLY contracts where public data can inform a
            probability estimate. Keep contracts about:
            - Economic indicators (CPI, jobs, GDP, Fed decisions)
            - Corporate events (earnings, product launches)
            - Political events with polling data
            - Financial market levels (S&P targets, crypto prices)

            Remove contracts about:
            - Weather
            - Random events
            - Things requiring insider knowledge
            - Celebrity gossip with no data basis

            Return the filtered list as JSON array with the same fields."""
        }],
    )
    parsed = _parse_json(response)
    if parsed is None:
        return markets[:20]
    return parsed


def estimate_probability(contract):
    """Ask Claude for the true probability — from base rates only.

    The vanilla Messages API has no web search, no live polls and no current
    news. Asking it to "research" a current event in a saved script invites
    hallucinated citations. The prompt constrains it to historical base rates and
    structural reasoning, and forces LOW confidence on anything clearly
    time-sensitive. For estimates that need live research, use the interactive
    Claude Code workflow (see docs/05-prediction.md) and `rank_estimates_file()`.
    """
    question = contract.get("question", "")
    yes_price, _no_price = parse_outcome_prices(contract.get("outcomePrices", []))
    market_price = yes_price

    response = claude.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""PREDICTION MARKET ANALYSIS

Question: {question}
Current market price: {market_price} (market thinks {market_price * 100:.0f}% likely)

You have no web search and no live data in this call. Reason ONLY from your
training-data knowledge:
1. What is the historical base rate for similar events?
2. What structural factors (regulatory, calendrical, statistical) bear on the
   question independent of current news?
3. Where is the market price relative to that base rate?

Do NOT invent current polls, recent headlines, or specific dated events you
cannot verify. If the question is clearly time-sensitive (needs current polls /
breaking news / today's price), return confidence="LOW" and say so in reasoning.

Return JSON:
{{
    "question": "{question}",
    "market_price": {market_price},
    "estimated_probability": 0.XX,
    "confidence": "HIGH" or "MEDIUM" or "LOW",
    "reasoning": "2-3 sentences anchored in base rates and structural factors only",
    "key_data_points": ["base rate or structural factor 1", "..."]
}}

Be calibrated. Don't disagree with the market for the sake of it. If the market
price looks correct given base rates, say so."""
        }],
    )
    return _parse_json(response)


def calculate_expected_value(estimate):
    """EV of buying YES vs NO at the current market price (ch07.md:240-258)."""
    prob = estimate.get("estimated_probability", 0.5)
    price = estimate.get("market_price", 0.5)

    ev_yes = (prob * 1.0) - price
    ev_no = ((1 - prob) * 1.0) - (1 - price)

    if ev_yes > ev_no and ev_yes > 0:
        return {"side": "YES", "ev": ev_yes, "price": price,
                "prob": prob, "gap": prob - price}
    if ev_no > ev_yes and ev_no > 0:
        return {"side": "NO", "ev": ev_no, "price": 1 - price,
                "prob": 1 - prob, "gap": (1 - prob) - (1 - price)}
    return {"side": "SKIP", "ev": 0, "price": price, "prob": prob, "gap": 0}


def suggested_bet(gap: float) -> float:
    """`min(MAX_BET_SIZE, MAX_BET_SIZE * abs(gap))` — the code as printed.

    ERRATUM (docs/book-deviations.md #9). Three claimants disagree:

    | gap | this formula | the prose ladder | the book prints |
    |-----|--------------|------------------|-----------------|
    | 10% | $5.00        | $25.00           | --              |
    | 17% | $8.50        | $42.50           | **$50.00**      |
    | 49% | **$24.50**   | $50.00           | **$24.50**      |

    No single formula produces both printed examples. This one reproduces the
    49% example digit-for-digit, and it is the only formula any printed output
    reproduces exactly, so it is what ships. The consequence you must know:
    `min()` only binds at a **100%** gap, so MAX_BET_SIZE is a scaling
    coefficient, not a cap. The prose's "$50 max per contract" is unreachable in
    practice. If you want the prose ladder instead, it is
    `min(MAX_BET_SIZE, MAX_BET_SIZE * abs(gap) / 0.20)` — and note it reproduces
    *neither* printed example.
    """
    return min(MAX_BET_SIZE, MAX_BET_SIZE * abs(gap))


def _parse_json(response):
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


def rank_estimates_file(path="prediction/estimates.json"):
    """Rank a Claude-Code-produced `estimates.json` through the same EV math.

    This is the live-data path (ch07.md:427-437): the interactive Claude Code
    session has web search, so it can cite real dated sources. It writes
    `estimates.json`; this function scores it. `suggested_bet` is applied here
    too, which the printed `rank_estimates_file()` does not do.
    """
    with open(artifact(path)) as f:
        estimates = json.load(f)
    opportunities = []
    for est in estimates:
        ev = calculate_expected_value(est)
        if ev["side"] != "SKIP" and abs(ev["gap"]) >= MIN_PROBABILITY_GAP:
            opportunities.append({
                **est, **ev, "suggested_bet": suggested_bet(ev["gap"]),
            })
    opportunities.sort(key=lambda x: x["ev"], reverse=True)
    return opportunities


def run_analyzer():
    """Main prediction-market analysis. Writes an artifact on every run."""
    banner()
    print("=== PREDICTION MARKET ANALYZER ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Min probability gap: {MIN_PROBABILITY_GAP * 100:.0f}%")
    print(f"Min market volume: ${MIN_VOLUME:,}")
    print(f"Bet size coefficient: ${MAX_BET_SIZE} (see erratum #9)")
    print("Read-only: this script never submits an order.\n")

    print("Fetching active markets...")
    markets = get_active_markets()
    print(f"Found {len(markets)} active markets.\n")

    print("Applying the liquidity floor...")
    liquid = filter_liquid(markets)
    print(f"Kept {len(liquid)} markets above the volume floor.\n")

    print("Filtering for analyzable contracts...")
    filtered = filter_analyzable(liquid)
    print(f"Kept {len(filtered)} analyzable contracts.\n")

    # The interactive live-data path (docs/05-prediction.md) reads this file.
    with open(artifact("prediction/markets.json"), "w") as f:
        json.dump(filtered, f, indent=2)

    opportunities = []
    for i, contract in enumerate(filtered):
        question = contract.get("question", "Unknown")[:60]
        print(f"Analyzing ({i + 1}/{len(filtered)}): {question}...")

        estimate = estimate_probability(contract)
        if not estimate:
            continue

        ev_result = calculate_expected_value(estimate)

        if (ev_result["side"] != "SKIP"
                and abs(ev_result["gap"]) >= MIN_PROBABILITY_GAP
                and estimate.get("confidence") in ["HIGH", "MEDIUM"]):
            opportunities.append({
                "question": contract.get("question", ""),
                "market_price": estimate.get("market_price", 0),
                "our_estimate": estimate.get("estimated_probability", 0),
                "gap": ev_result["gap"],
                "side": ev_result["side"],
                "expected_value": ev_result["ev"],
                "confidence": estimate.get("confidence", "LOW"),
                "reasoning": estimate.get("reasoning", ""),
                "key_data": estimate.get("key_data_points", []),
                "suggested_bet": suggested_bet(ev_result["gap"]),
            })

    opportunities.sort(key=lambda x: x["expected_value"], reverse=True)

    # Save FIRST, so every run lands an artifact on disk — including the
    # calibrated "no contracts found" no-op day. A quiet day should still be
    # auditable later.
    output_file = artifact(
        f"prediction/opportunities_{datetime.now().strftime('%Y%m%d')}.json")
    with open(output_file, "w") as f:
        json.dump(opportunities, f, indent=2)

    print(f"\n{'=' * 60}")
    print("PREDICTION MARKET OPPORTUNITIES (base-rate reasoning only)")
    print(f"{'=' * 60}\n")

    if not opportunities:
        print("No contracts found with sufficient edge today.")
        print("This is normal. Not every day has mispriced contracts.")
        print(f"\nResults saved to {output_file}")
        return opportunities

    for rank, opp in enumerate(opportunities, 1):
        print(f"{rank}. {opp['question'][:70]}")
        print(f"   Market: {opp['market_price']:.0%} | "
              f"Our estimate: {opp['our_estimate']:.0%} | "
              f"Gap: {opp['gap']:+.0%}")
        print(f"   Side: BUY {opp['side']} | "
              f"EV: ${opp['expected_value']:.2f}/share | "
              f"Confidence: {opp['confidence']}")
        print(f"   Reasoning: {opp['reasoning']}")
        print(f"   Suggested bet: ${opp['suggested_bet']:.2f}")
        print()

    print("This script does not place bets. Place them yourself, after KYC, and "
          "check your state's legal status first.")
    print(f"Results saved to {output_file}")
    return opportunities


if __name__ == "__main__":
    run_analyzer()
