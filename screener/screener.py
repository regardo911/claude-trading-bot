"""Stock screener bot — Chapter 4. Scans the options market each morning and
produces a ranked watchlist of the 5-10 names where smart money is moving.

Four stages (ch04.md:13-23):

    1. Pull today's unusual options flow from UW REST.
    2. Filter: volume/OI > 3.0, premium > $200K, sweeps and floor prints only.
    3. Send each survivor to Claude for a per-event read (0-100 confidence).
    4. Apply Chapter 3's post-filters, rank, print the top 10, save the JSON.

Stage 4's post-filters are the repo's addition — ch03 states three rules the
author's bots run (a 1M-share liquidity floor, a -15 geopolitical penalty, and a
-20 Tier1/Tier2 conflict penalty) that appear in **no code the book prints**.
All three are default-ON here and all three make the bot trade *less*. See
`docs/book-deviations.md` (#14).

A vanilla `messages.create("Using Unusual Whales MCP, ...")` prompt does NOT
dispatch MCP from a saved script — it returns hallucinated JSON (ch02.md:34-50).
This module hits UW REST directly, which is why it runs standalone.

Educational software. Not financial advice. See DISCLAIMER.md.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from utils import artifact, banner  # noqa: E402
from utils.offline import get_anthropic, http_get_json, offline_enabled  # noqa: E402
from utils.signals import adjust_confidence  # noqa: E402

load_dotenv()
client = get_anthropic()

UW_API_KEY = os.getenv("UW_API_KEY")
UW_BASE = "https://api.unusualwhales.com/api"

# --- ch04 filters (Appendix B, Template 1) ---------------------------------
VOL_OI_THRESHOLD = 3.0        # ch04.md:17,77-81 — today's volume >= 3x open interest
MIN_PREMIUM = 200_000         # ch04.md:17,78   — $200K floor filters out retail
CONFIDENCE_THRESHOLD = 65     # ch04.md:328, appendices.md:428 — watchlist floor
MAX_TOKENS = 800              # ch04.md:119
MODEL = "claude-sonnet-4-6"


def get_unusual_flow():
    """Pull today's unusual options flow from UW REST directly.

    `GET /api/option-trades/flow-alerts` — plural `option-trades`, hyphenated
    `flow-alerts`. Bearer token in the `Authorization` header, not a query
    param (ch02.md:37, ch04.md:76).
    """
    if not UW_API_KEY and not offline_enabled():
        raise RuntimeError(
            "UW_API_KEY not set in .env. The screener needs a paid UW tier "
            "(Trial $50/wk minimum). Free Shamu does NOT include API access. "
            "Or unset CTB_OFFLINE to run against the bundled synthetic fixtures."
        )
    headers = {"Authorization": f"Bearer {UW_API_KEY}"}
    params = {
        "min_premium": MIN_PREMIUM,
        "min_volume_oi_ratio": VOL_OI_THRESHOLD,
        "is_sweep": True,
    }
    try:
        payload = http_get_json(
            f"{UW_BASE}/option-trades/flow-alerts",
            headers=headers, params=params, timeout=30,
        )
    except Exception as e:  # noqa: BLE001
        # 403 = your tier doesn't include this endpoint. Trial $50/wk is the
        # minimum tier with API access. Degrade to an empty day, don't crash.
        if "403" in str(e):
            print("Tier limitation: UW returned 403 on flow-alerts. "
                  "Trial $50/wk is the minimum tier with API access.")
            return []
        raise

    raw = payload.get("data", [])
    # Re-filter in Python; UW's query params vary by tier and the response field
    # names occasionally drift between versions.
    flow_data = []
    for item in raw:
        # The server already filters to sweeps via is_sweep=True; also keep floor
        # (large institutional) prints that came through.
        if not (item.get("has_sweep") or item.get("has_floor")):
            continue
        flow_data.append({
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
    return flow_data


def analyze_signal(flow_item):
    """Send a single flow item to Claude for multi-signal analysis.

    Returns the parsed JSON dict, or None when Claude's response can't be parsed.
    Missing a signal is always better than crashing (ch04.md:233).
    """
    ticker = flow_item["ticker"]
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": f"""I've got this unusual options flow event:
            {json.dumps(flow_item)}

            Reason across these dimensions, using what's in the event JSON plus
            your training-data knowledge of {ticker}'s sector, typical IV
            behavior, and any major catalysts you recall. Be honest when a
            dimension is unknown rather than guessing.

            1. OPTIONS FLOW: How aggressive is this sweep/block? Is the vol/OI
               ratio + premium combination unusual for {ticker}?
            2. DARK POOL CONTEXT: What's typical dark pool activity for
               {ticker}'s float and sector?
            3. IMPLIED VOLATILITY: Given the strike, expiration, and ticker, is
               the trade chasing IV expansion or directional movement?
            4. SECTOR: What sector is {ticker} in, and is the sector typically
               responsive to this kind of flow?
            5. CATALYST: Any catalyst window (earnings, Fed, sector news) you can
               recall? If unknown, say so.

            Based on ALL signals, give me:
            - Direction: BULLISH or BEARISH
            - Confidence: 0-100 (require 3+ converging signals for 70+)
            - Dark pool read: BULLISH, BEARISH or UNKNOWN (your Tier-2 call)
            - Reasoning: One paragraph, plain English

            Format as JSON:
            {{
                "ticker": "{ticker}",
                "direction": "BULLISH" or "BEARISH",
                "confidence": 00,
                "dark_pool_read": "BULLISH" or "BEARISH" or "UNKNOWN",
                "reasoning": "..."
            }}"""
        }],
    )
    return parse_claude_json(response)


def parse_claude_json(response):
    """Parse Claude's JSON, tolerating a markdown code fence (ch04.md:157-165).

    Sometimes Claude returns clean JSON. Sometimes it wraps it in triple
    backticks. Sometimes it adds a preamble. The fallback handles about 98% of
    the variations; the remaining 2% returns None and the caller skips the event.
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


def apply_chapter3_rules(analysis, item):
    """ch03's three post-filters. Returns None when the trade is blocked outright.

    See `utils.signals` and docs/book-deviations.md (#14).
    """
    adj = adjust_confidence(
        ticker=analysis.get("ticker", item.get("ticker", "")),
        confidence=analysis.get("confidence", 0),
        direction=analysis.get("direction", ""),
        dark_pool_read=analysis.get("dark_pool_read"),
    )
    if not adj.tradeable:
        print(f"   BLOCKED: {adj.summary()}")
        return None
    if adj.confidence != adj.raw_confidence:
        print(f"   ADJUSTED: {adj.raw_confidence:.0f} -> {adj.confidence:.0f} "
              f"({adj.summary()})")
    analysis["raw_confidence"] = adj.raw_confidence
    analysis["confidence"] = adj.confidence
    analysis["manual_review"] = adj.manual_review
    analysis["confidence_adjustments"] = adj.notes
    return analysis


def run_screener():
    """Main screener function."""
    banner()
    print("=== AI Stock Screener ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("Pulling unusual options flow...\n")

    # Step 1: get unusual flow
    flow_data = get_unusual_flow()
    print(f"Found {len(flow_data)} unusual transactions after filtering.\n")

    if not flow_data:
        print("No unusual activity meets our criteria today.")
        return []

    # Step 2: analyze each signal
    results = []
    for i, item in enumerate(flow_data):
        print(f"Analyzing {item['ticker']} ({i + 1}/{len(flow_data)})...")
        analysis = analyze_signal(item)
        if not analysis:
            continue
        analysis = apply_chapter3_rules(analysis, item)
        if not analysis:
            continue
        # Use the documented UW field names (total_premium / volume_oi_ratio).
        analysis["premium"] = item.get("total_premium", 0)
        analysis["vol_oi_ratio"] = item.get("volume_oi_ratio", 0)
        results.append(analysis)

    # Step 3: rank by confidence
    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    # Step 4: output the watchlist. In practice only signals above 65 are worth
    # trading (ch04.md:325-328); everything else still lands in the JSON.
    watchlist = [r for r in results if r.get("confidence", 0) >= CONFIDENCE_THRESHOLD]

    print(f"\n{'=' * 60}")
    print(f"DAILY WATCHLIST - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"(confidence >= {CONFIDENCE_THRESHOLD}, after Chapter 3 adjustments)")
    print(f"{'=' * 60}\n")

    if not watchlist:
        print("Nothing cleared the confidence floor today. That is a normal day.")

    for rank, r in enumerate(watchlist[:10], 1):
        direction = r.get("direction", "N/A")
        confidence = r.get("confidence", 0)
        ticker = r.get("ticker", "N/A")
        reasoning = r.get("reasoning", "No reasoning provided")
        marker = "[BULL]" if direction == "BULLISH" else "[BEAR]"
        flag = "  [MANUAL REVIEW]" if r.get("manual_review") else ""
        print(f"{rank}. {marker} {ticker} | {direction} | "
              f"Confidence: {confidence:.0f}%{flag}")
        print(f"   {reasoning}")
        print()

    output_file = artifact(
        f"screener/watchlist_{datetime.now().strftime('%Y%m%d')}.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Watchlist saved to {output_file}")
    print(f"({len(results)} scored events; {len(watchlist)} cleared "
          f"{CONFIDENCE_THRESHOLD}%.)")
    return watchlist


if __name__ == "__main__":
    run_screener()
