"""Regenerate every image in `docs/images/` — one per catalog item, exactly eight.

    python tools/generate_docs_charts.py            # all 8
    python tools/generate_docs_charts.py screener risk    # a named subset

THE RULE THAT MAKES THESE HONEST
---------------------------------
**Every chart is COMPUTED by importing the repo's real modules and running the
actual functions the doc teaches, against the committed synthetic fixtures.**
Nothing here is hand-drawn and nothing is fabricated. A chart may only show what
the repo's own code produces.

That rule is load-bearing, not decorative. The Monte Carlo fan chart fans out
because `backtester.monte_carlo_simulation()` genuinely produces dispersion — not
because someone drew a fan. Under a naive permutation sampler it would be a
straight line (see docs/book-deviations.md #6, resolved in book). A hand-drawn fan
would have hidden the trap.

Every figure is stamped "synthetic sample data — illustrative mechanics only".

matplotlib is the optional `viz` extra:  pip install -e ".[viz]"
The PNGs are committed, so a zero-key clone still shows every image.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from utils import ROOT  # noqa: E402

OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

# --- Palette (dataviz skill; validated for the light chart surface) ---------
S1, S2, S3 = "#2a78d6", "#1baf7a", "#eda100"   # fixed categorical slots, in order
GOOD, CRIT = "#0ca30c", "#d03b3b"              # status only: entry/exit semantics
INK, INK2, MUTED = "#1c1c1a", "#55554f", "#8a8a85"
GRID, SURFACE = "#e6e6e2", "#fcfcfb"
DPI = 200

# The relief rule: several of these hues sit under 3:1 against the surface, so a
# direct text label backs every one of them. Nothing here relies on colour alone.

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.size": 10, "text.color": INK,
    "axes.labelcolor": INK2, "axes.edgecolor": GRID,
    "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True,
})


def frame(ax, title: str, subtitle: str) -> None:
    """Left-aligned title + a plain-English subtitle naming the mechanic."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold",
                 color=INK, pad=30)
    ax.text(0, 1.018, subtitle, transform=ax.transAxes, fontsize=9.5,
            color=INK2, va="bottom")


def caption(fig) -> None:
    fig.text(0.995, 0.008, "synthetic sample data — illustrative mechanics only",
             ha="right", va="bottom", fontsize=7, color=MUTED)


def save(fig, name: str) -> Path:
    path = OUT / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path.relative_to(ROOT)}")
    return path


# --------------------------------------------------------------------------- #
#  1. Setup (ch02) — the 4/4 gate, run against the fixtures
# --------------------------------------------------------------------------- #
def render_setup():
    from setup.verify_setup import check_alpaca, check_claude, check_mcp, check_python

    checks = [
        ("Python 3.11+", check_python),
        ("Claude API", check_claude),
        ("Unusual Whales", check_mcp),
        ("Alpaca paper", check_alpaca),
    ]
    rows = []
    for name, fn in checks:
        try:
            detail = str(fn())
            rows.append((name, True, detail))
        except Exception as e:  # noqa: BLE001
            rows.append((name, False, str(e)))

    passed = sum(1 for _, ok, _ in rows if ok)

    fig, ax = plt.subplots(figsize=(11, 5.0))
    frame(ax, "The setup gate: 4 connections, 1 script (ch02)",
          "verify_setup.py runs each check and refuses to advance until all four pass")

    for i, (name, ok, detail) in enumerate(rows):
        y = len(rows) - 1 - i
        colour = GOOD if ok else CRIT
        ax.barh(y, 1.0, height=0.62, color=colour, alpha=0.16, edgecolor=colour,
                linewidth=1.4)
        ax.text(0.012, y, f"{'PASS' if ok else 'FAIL'}", va="center", ha="left",
                fontsize=10, fontweight="bold", color=colour)
        ax.text(0.085, y, name, va="center", ha="left", fontsize=11,
                fontweight="bold", color=INK)
        import textwrap
        shown = "\n".join(textwrap.wrap(detail, width=64)[:2])
        ax.text(0.315, y, shown, va="center", ha="left", fontsize=8.2, color=INK2)

    ax.set_xlim(0, 1)
    ax.set_ylim(-1.55, len(rows) - 0.30)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.grid(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.text(0.012, -0.72, f"Result: {passed}/4 checks passed", fontsize=12,
            fontweight="bold", color=GOOD if passed == 4 else CRIT, va="center")
    ax.text(0.012, -1.18,
            "Offline, with no .env and no API keys. Check 3 verifies the Unusual "
            "Whales REST data layer the saved scripts actually use, and says so "
            "in its own\noutput — it does not claim to have checked a live MCP "
            "registration.",
            fontsize=8.2, color=MUTED, va="center")
    caption(fig)
    return save(fig, "01-setup")


# --------------------------------------------------------------------------- #
#  2. Screener (ch04) — ranked bar, thresholds at 65 and 70
# --------------------------------------------------------------------------- #
def render_screener():
    from screener.screener import CONFIDENCE_THRESHOLD, analyze_signal, get_unusual_flow
    from utils.signals import TRADE_THRESHOLD, adjust_confidence

    scored = []
    for item in get_unusual_flow():
        analysis = analyze_signal(item)
        if not analysis:
            continue
        adj = adjust_confidence(
            analysis["ticker"], analysis.get("confidence", 0),
            analysis.get("direction", ""), analysis.get("dark_pool_read"))
        scored.append({
            "ticker": analysis["ticker"],
            "direction": analysis.get("direction", ""),
            "confidence": adj.confidence,
            "raw": adj.raw_confidence,
            "blocked": not adj.tradeable,
            "adjusted": adj.confidence != adj.raw_confidence,
        })
    # Rank by the RAW score so a blocked name still shows where it would have
    # ranked — that is the whole point of showing the ch03 floor at work.
    scored.sort(key=lambda r: r["raw"], reverse=True)
    scored = scored[:10]

    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    frame(ax, "Screener: what survives the two gates (ch04)",
          "Claude's confidence per flow event, after Chapter 3's post-filters. "
          "Only the top band is tradeable.")

    ys = np.arange(len(scored))[::-1]
    for y, row in zip(ys, scored, strict=True):
        tradeable = row["confidence"] >= CONFIDENCE_THRESHOLD and not row["blocked"]
        if row["blocked"]:
            colour, alpha = MUTED, 0.30
        elif row["direction"] == "BULLISH":
            colour, alpha = S1, 1.0 if tradeable else 0.30
        else:
            colour, alpha = S3, 1.0 if tradeable else 0.30

        if row["blocked"]:
            # Draw the score it WOULD have had, struck through. A zero-length bar
            # would just vanish, and the reader would never see the rule bite.
            ax.barh(y, row["raw"], height=0.60, color=MUTED, alpha=0.22,
                    hatch="///", edgecolor=MUTED, linewidth=0, zorder=3)
            ax.plot([0, row["raw"]], [y, y], color=CRIT, linewidth=1.6, zorder=5)
        else:
            ax.barh(y, row["confidence"], height=0.60, color=colour, alpha=alpha,
                    zorder=3)

        # Where ch03 marked a score down, tick the raw value it started from.
        if row["adjusted"]:
            ax.plot([row["raw"], row["raw"]], [y - 0.30, y + 0.30],
                    color=MUTED, linewidth=1.6, linestyle="--", zorder=4)

        if row["blocked"]:
            note = f"BLOCKED — ch03 liquidity floor (scored {row['raw']:.0f})"
        elif row["adjusted"]:
            note = f"{row['confidence']:.0f}   (was {row['raw']:.0f}, ch03)"
        else:
            note = f"{row['confidence']:.0f}"
        ax.text(102, y, note, va="center", ha="left", fontsize=9.5,
                color=INK if tradeable else INK2,
                fontweight="bold" if tradeable else "normal", zorder=5)

    ax.axvline(CONFIDENCE_THRESHOLD, color=INK2, linestyle="--", linewidth=1.2,
               zorder=2)
    ax.axvline(TRADE_THRESHOLD, color=CRIT, linestyle="--", linewidth=1.4, zorder=2)
    ax.text(CONFIDENCE_THRESHOLD - 1.1, -0.55,
            f"{CONFIDENCE_THRESHOLD} watchlist floor", rotation=90, ha="center",
            va="bottom", fontsize=8, color=INK2)
    ax.text(TRADE_THRESHOLD + 1.1, -0.55,
            f"{TRADE_THRESHOLD} trade threshold", rotation=90, ha="center",
            va="bottom", fontsize=8, color=CRIT, fontweight="bold")

    ax.set_yticks(ys)
    ax.set_yticklabels([r["ticker"] for r in scored], fontsize=10.5,
                       fontweight="bold")
    for label, row in zip(ax.get_yticklabels(), scored, strict=True):
        label.set_color(INK if (row["confidence"] >= CONFIDENCE_THRESHOLD
                                and not row["blocked"]) else MUTED)
    ax.set_xlim(0, 100)
    ax.set_ylim(-1.35, len(scored) - 0.25)
    ax.set_xlabel("Claude confidence (0-100)")
    ax.grid(axis="y", visible=False)

    ax.legend(handles=[
        Patch(facecolor=S1, label="BULLISH"),
        Patch(facecolor=S3, label="BEARISH"),
        Patch(facecolor=MUTED, alpha=0.22, hatch="///",
              label="blocked by the ch03 liquidity floor"),
        plt.Line2D([], [], color=MUTED, linestyle="--", linewidth=1.6,
                   label="raw score, before the ch03 markdown"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4, frameon=False,
        fontsize=8.8)
    caption(fig)
    return save(fig, "02-screener")


# --------------------------------------------------------------------------- #
#  3. Flow trader (ch05) — session timeline, the 70% line, the silence
# --------------------------------------------------------------------------- #
def render_flow_trader():
    from datetime import datetime

    from flow_trader.flow_trader import (
        CONFIDENCE_THRESHOLD,
        analyze_flow_event,
        get_live_flow,
    )
    from utils.signals import adjust_confidence

    events = []
    for e in get_live_flow():
        analysis = analyze_flow_event(e)
        if not analysis:
            continue
        adj = adjust_confidence(e["ticker"], analysis.get("confidence", 0),
                                analysis.get("direction", ""),
                                analysis.get("dark_pool_read"))
        stamp = datetime.fromisoformat(e["timestamp"])
        events.append({
            "ticker": e["ticker"],
            "hour": stamp.hour + stamp.minute / 60,
            "confidence": adj.confidence,
            "traded": adj.tradeable and adj.confidence >= CONFIDENCE_THRESHOLD,
            "blocked": not adj.tradeable,
        })
    events.sort(key=lambda e: e["hour"])

    fig, ax = plt.subplots(figsize=(11, 5.8))
    frame(ax, "Flow trader: a session is mostly silence (ch05)",
          "Every qualifying alert, plotted at the minute it printed. The bot acts "
          "only above 70. The gaps are the bot working.")

    ax.axhspan(CONFIDENCE_THRESHOLD, 100, color=S2, alpha=0.06, zorder=0)
    ax.axhline(CONFIDENCE_THRESHOLD, color=CRIT, linestyle="--", linewidth=1.4,
               zorder=2)
    ax.text(9.47, CONFIDENCE_THRESHOLD + 0.7,
            f"{CONFIDENCE_THRESHOLD}% trade threshold — above this line the bot acts",
            va="bottom", ha="left", fontsize=8.8, color=CRIT, fontweight="bold")

    for e in events:
        if e["blocked"]:
            ax.scatter(e["hour"], 40, s=110, marker="x", color=MUTED, zorder=4,
                       linewidths=2.0)
            ax.annotate(f"{e['ticker']}\nblocked", (e["hour"], 40),
                        textcoords="offset points", xytext=(0, 10), ha="center",
                        fontsize=8.5, color=MUTED)
            continue
        traded = e["traded"]
        ax.scatter(e["hour"], e["confidence"],
                   s=140 if traded else 80,
                   marker="^" if traded else "o",
                   color=S1 if traded else "none",
                   edgecolor=S1 if traded else MUTED,
                   linewidths=1.6, zorder=4)
        ax.annotate(e["ticker"], (e["hour"], e["confidence"]),
                    textcoords="offset points", xytext=(0, 11 if traded else 9),
                    ha="center", fontsize=8.5,
                    color=INK if traded else INK2,
                    fontweight="bold" if traded else "normal")

    ax.set_xlim(9.42, 16.2)
    ax.set_ylim(30, 100)
    ax.set_xticks([9.5, 10, 11, 12, 13, 14, 15, 16])
    ax.set_xticklabels(["9:30", "10:00", "11:00", "12:00", "13:00", "14:00",
                        "15:00", "16:00"])
    ax.set_xlabel("Session clock (ET)")
    ax.set_ylabel("Confidence after ch03 adjustment")
    ax.legend(handles=[
        plt.Line2D([], [], marker="^", color=S1, linestyle="none", markersize=10,
                   label="TRADED (>= 70)"),
        plt.Line2D([], [], marker="o", color="none", markeredgecolor=MUTED,
                   linestyle="none", markersize=9, label="PASSED (logged only)"),
        plt.Line2D([], [], marker="x", color=MUTED, linestyle="none", markersize=9,
                   label="BLOCKED (ch03 liquidity floor)"),
    ], loc="lower left", frameon=False, fontsize=8.5)
    caption(fig)
    return save(fig, "03-flow-trader")


# --------------------------------------------------------------------------- #
#  4. Backtester (ch06) — the fan chart + the overfit check
# --------------------------------------------------------------------------- #
def render_backtester():
    from backtester import backtester as bt

    trades = bt.calculate_trade_returns(bt.load_historical_flow_from_csv())
    split = bt.in_out_sample_split(trades)
    mc = bt.monte_carlo_simulation(trades)
    report = bt.generate_report(trades, mc, split)

    curves = np.array(mc["curves"], dtype=float)
    initial = mc["initial_capital"]
    finals = mc["final_values"]
    p5, p50, p95 = (np.percentile(finals, q) for q in (5, 50, 95))

    fig = plt.figure(figsize=(14.5, 6.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.8, 1], hspace=0.85, wspace=0.22)
    ax1 = fig.add_subplot(gs[:, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 1])

    # -- left: the fan --------------------------------------------------------
    frame(ax1, "Monte Carlo: 1,000 bootstrapped equity curves (ch06)",
          "Resampled WITH replacement. A naive permutation would land every "
          "curve on the same value.")
    for i in range(0, min(400, len(curves))):
        ax1.plot(curves[i], color=S1, alpha=0.03, linewidth=0.6, zorder=1)

    x = np.arange(curves.shape[1])
    p5_line = np.percentile(curves, 5, axis=0)
    p50_line = np.percentile(curves, 50, axis=0)
    p95_line = np.percentile(curves, 95, axis=0)
    ax1.fill_between(x, p5_line, p95_line, color=S1, alpha=0.10, zorder=2)
    ax1.plot(x, p50_line, color=S1, linewidth=2.2, zorder=4, label="Median")
    ax1.plot(x, p5_line, color=CRIT, linewidth=1.6, linestyle="--", zorder=4,
             label="5th percentile")
    ax1.plot(x, p95_line, color=S2, linewidth=1.6, linestyle="--", zorder=4,
             label="95th percentile")
    ax1.axhline(initial, color=MUTED, linestyle=":", linewidth=1.4, zorder=3,
                label="Starting capital")

    n = curves.shape[1] - 1
    for value, colour, name in ((p95, S2, "95th"), (p50, S1, "median"),
                                (p5, CRIT, "5th")):
        ax1.annotate(f"{name}  ${value:,.0f}", (n, value),
                     textcoords="offset points", xytext=(8, 0), va="center",
                     fontsize=9, color=colour, fontweight="bold")

    ax1.set_xlabel("Trade number")
    ax1.set_ylabel("Portfolio value ($)")
    ax1.set_xlim(0, n * 1.22)
    ax1.legend(loc="upper left", frameon=False, fontsize=9)
    ax1.text(0.02, 0.03,
             f"{len(trades)} trades  ·  {mc['n_simulations']:,} sims  ·  "
             f"{len({round(v, 6) for v in finals}):,} distinct final values",
             transform=ax1.transAxes, fontsize=8.5, color=INK2)

    verdict = report["verdict"]
    ax1.text(0.98, 0.09, verdict, transform=ax1.transAxes, ha="right",
             fontsize=12, fontweight="bold",
             color=GOOD if verdict == "EDGE CONFIRMED" else CRIT,
             bbox={"boxstyle": "round,pad=0.45", "facecolor": SURFACE,
                   "edgecolor": GOOD if verdict == "EDGE CONFIRMED" else CRIT,
                   "linewidth": 1.4})

    # -- right: does it generalize? Two panels, because a win rate and a Sharpe
    #    are not the same quantity and do not belong on one scale.
    flagged = split["overfit"]
    panels = [
        (ax2, "Win rate (%)",
         split["in_sample_win_rate"] * 100, split["out_of_sample_win_rate"] * 100,
         f"gap {split['win_rate_gap_pp']:.1f}pp   (flag at > 5.0pp)", "{:.1f}"),
        (ax3, "Sharpe ratio",
         split["in_sample_sharpe"], split["out_of_sample_sharpe"],
         f"drop {split['sharpe_drop']:.2f}   (flag at > 0.50)", "{:.2f}"),
    ]
    for i, (ax, label, in_v, out_v, note, fmt) in enumerate(panels):
        title = "Does it generalize? (ch06)" if i == 0 else ""
        sub = ("First half vs second half. A real edge holds up out-of-sample."
               if i == 0 else "")
        frame(ax, title, sub)
        bars = ax.bar([0, 1], [in_v, out_v], width=0.55, color=[S1, S2])
        for bar, value in zip(bars, (in_v, out_v), strict=True):
            ax.annotate(fmt.format(value),
                        (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        textcoords="offset points", xytext=(0, 4), ha="center",
                        fontsize=9.5, color=INK, fontweight="bold")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["In-sample", "Out-of-sample"], fontsize=9)
        ax.set_ylim(0, max(in_v, out_v) * 1.30)
        ax.set_ylabel(label, fontsize=9.5)
        ax.text(0.5, -0.30, note, transform=ax.transAxes, ha="center",
                fontsize=8.5, color=INK2)

    ax3.text(0.5, -0.52, f"overfit_flag: {flagged}", transform=ax3.transAxes,
             ha="center", fontsize=10.5, fontweight="bold",
             color=CRIT if flagged else GOOD)

    caption(fig)
    return save(fig, "04-backtester")


# --------------------------------------------------------------------------- #
#  5. Prediction (ch07) — scatter + the no-bet band
# --------------------------------------------------------------------------- #
def render_prediction():
    from prediction import prediction_analyzer as pa

    markets = pa.filter_analyzable(pa.filter_liquid(pa.get_active_markets()))
    points = []
    for m in markets:
        est = pa.estimate_probability(m)
        if not est:
            continue
        ev = pa.calculate_expected_value(est)
        qualifies = (ev["side"] != "SKIP"
                     and abs(ev["gap"]) >= pa.MIN_PROBABILITY_GAP
                     and est.get("confidence") in ("HIGH", "MEDIUM"))
        points.append({
            "market": est["market_price"],
            "ours": est["estimated_probability"],
            "confidence": est.get("confidence", "LOW"),
            "qualifies": qualifies,
            "question": m.get("question", "")[:34],
            "bet": pa.suggested_bet(ev["gap"]) if qualifies else 0.0,
        })

    fig, ax = plt.subplots(figsize=(10.5, 7.4))
    frame(ax, "Prediction markets: the edge is the gap (ch07)",
          "Claude's base-rate estimate vs the market price. Inside the shaded band "
          "the gap is too small to bet.")

    grid = np.linspace(0, 1, 100)
    ax.fill_between(grid, grid - pa.MIN_PROBABILITY_GAP,
                    grid + pa.MIN_PROBABILITY_GAP,
                    color=MUTED, alpha=0.13, zorder=1)
    ax.plot(grid, grid, color=INK2, linewidth=1.2, linestyle="--", zorder=2)
    ax.text(0.70, 0.63, "market is right\n(no bet)", fontsize=9, color=INK2,
            ha="center", rotation=45)

    for p in points:
        if p["qualifies"]:
            ax.scatter(p["market"], p["ours"], s=190, color=S2, zorder=5,
                       edgecolor=INK, linewidths=0.9)
            ax.annotate(f"{p['question']}...\nBUY YES · bet ${p['bet']:.2f}",
                        (p["market"], p["ours"]), textcoords="offset points",
                        xytext=(14, -4), fontsize=9, color=INK, fontweight="bold")
            ax.annotate("", xy=(p["market"], p["ours"]),
                        xytext=(p["market"], p["market"]),
                        arrowprops={"arrowstyle": "-|>", "color": S2, "linewidth": 1.6})
        elif p["confidence"] == "LOW":
            ax.scatter(p["market"], p["ours"], s=95, facecolor="none",
                       edgecolor=MUTED, linewidths=1.5, zorder=4)
        else:
            ax.scatter(p["market"], p["ours"], s=95, color=S1, alpha=0.75, zorder=4)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Market-implied probability (outcomePrices[0])")
    ax.set_ylabel("Claude's estimate")
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.legend(handles=[
        plt.Line2D([], [], marker="o", color=S2, linestyle="none", markersize=11,
                   markeredgecolor=INK, label="opportunity (gap >= 10pp, HIGH/MEDIUM)"),
        plt.Line2D([], [], marker="o", color=S1, linestyle="none", markersize=9,
                   label="analyzed, inside the no-bet band"),
        plt.Line2D([], [], marker="o", color="none", markeredgecolor=MUTED,
                   linestyle="none", markersize=9,
                   label="LOW confidence (time-sensitive) — excluded"),
    ], loc="upper left", frameon=False, fontsize=8.5)
    ax.text(0.5, -0.115,
            "The analyzer is READ-ONLY. It ranks the opportunity and stops. "
            "You place the bet, after KYC.",
            transform=ax.transAxes, ha="center", fontsize=8.5, color=INK2,
            style="italic")
    caption(fig)
    return save(fig, "05-prediction")


# --------------------------------------------------------------------------- #
#  6. Multi-agent (ch08) — the funnel
# --------------------------------------------------------------------------- #
def render_multi_agent():
    from multi_agent.multi_agent import run_multi_agent_cycle

    cycle = run_multi_agent_cycle()
    recs = cycle["analyst"]["recommendations"]
    decisions = cycle["risk"]["decisions"]
    filled = [r for r in cycle["execution"] if r["status"] == "FILLED"]

    approved = [d for d in decisions if d["action"] == "APPROVE"]
    reduced = [d for d in decisions if d["action"] == "REDUCE"]
    rejected = [d for d in decisions if d["action"] == "REJECT"]

    shares_in = sum(r.get("suggested_shares", 0) for r in recs)
    shares_out = sum(r["shares"] for r in filled)

    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    frame(ax, "Multi-agent: the Risk Manager gets the last word (ch08)",
          "One cycle. The Analyst finds three trades; the Risk Manager approves "
          "one, cuts one, and kills one.")

    # A one-hue ordinal ramp for the funnel stages.
    ramp = ["#bcd6f2", "#7fb2e5", "#2a78d6"]
    stages = [
        (f"ANALYST\n{len(recs)} recommendations", len(recs), ramp[0]),
        (f"RISK MANAGER\n{len(approved)} approved · {len(reduced)} reduced · "
         f"{len(rejected)} rejected", len(approved) + len(reduced), ramp[1]),
        (f"EXECUTOR\n{len(filled)} bracket orders filled", len(filled), ramp[2]),
    ]

    top = len(recs)
    for i, (label, value, colour) in enumerate(stages):
        half = value / 2
        left, right = i, i + 0.72
        ax.fill_between([left, right], [top / 2 - half] * 2, [top / 2 + half] * 2,
                        color=colour, zorder=3)
        ax.text((left + right) / 2, top / 2, str(value), ha="center", va="center",
                fontsize=22, fontweight="bold",
                color=INK if i < 2 else SURFACE, zorder=4)
        ax.text((left + right) / 2, -0.42, label, ha="center", va="top",
                fontsize=9.5, color=INK, fontweight="bold")
        if i < len(stages) - 1:
            nxt = stages[i + 1][1] / 2
            ax.fill_between([right, i + 1], [top / 2 - half, top / 2 - nxt],
                            [top / 2 + half, top / 2 + nxt],
                            color=colour, alpha=0.30, zorder=2)

    notes = []
    for d in reduced:
        notes.append(("REDUCED", d["ticker"],
                      f"{d['approved_shares']} shares approved of the "
                      f"{next((r['suggested_shares'] for r in recs if r['ticker'] == d['ticker']), '?')} "
                      f"the Analyst asked for", S3))
    for d in rejected:
        notes.append(("REJECTED", d["ticker"], d["reasoning"][:78] + "...", CRIT))

    for j, (kind, ticker, why, colour) in enumerate(notes):
        y = top + 0.85 + j * 0.52
        ax.text(0.0, y, f"{kind}  {ticker}", fontsize=9.5, fontweight="bold",
                color=colour, va="center")
        ax.text(0.86, y, why, fontsize=8.5, color=INK2, va="center")

    ax.text(1.36, -1.42,
            f"{shares_in} shares requested   ->   {shares_out} shares actually "
            f"bought",
            fontsize=10, color=INK2, ha="center", fontweight="bold")

    ax.set_xlim(-0.08, 2.80)
    ax.set_ylim(-1.72, top + 0.9 + max(len(notes), 1) * 0.52)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    caption(fig)
    return save(fig, "06-multi-agent")


# --------------------------------------------------------------------------- #
#  7. Risk (ch09) — where Kelly binds, where the cap binds, where zero binds
# --------------------------------------------------------------------------- #
def render_risk():
    from risk.risk_manager import DEFAULT_STOP_LOSS, RiskManager
    from utils.offline import OfflineTradingClient

    rm = RiskManager(client=OfflineTradingClient(paper=True, positions=[]))

    prices = np.linspace(10, 1000, 200)
    edge = [rm.calculate_position_size("NVDA", float(p)) for p in prices]
    no_edge = [rm.calculate_position_size("NVDA", float(p),
                                          win_rate=0.48, profit_factor=0.9)
               for p in prices]
    # A genuinely quarter-Kelly-bound case. 52%/1.3 would NOT be one: its
    # quarter-Kelly is 3.8%, which is above the 2% cap, so the cap binds and the
    # curve sits on top of the first one. 51%/1.1 gives quarter-Kelly 1.6% — under
    # the cap, so Kelly is what actually sizes the trade.
    thin = [rm.calculate_position_size("NVDA", float(p),
                                       win_rate=0.51, profit_factor=1.1)
            for p in prices]

    fig, ax = plt.subplots(figsize=(11, 6.4))
    frame(ax, "Risk: the answer is often smaller, and sometimes zero (ch09)",
          "Approved shares vs entry price on a $100K account at a 3% stop. "
          "Quarter-Kelly, capped at 2% risk, floored at zero.")

    ax.plot(prices, edge, color=S1, linewidth=2.4, zorder=4,
            label="53.7% win / 1.79 PF  (Kelly +27.8% -> the 2% cap binds)")
    ax.plot(prices, thin, color=S2, linewidth=2.2, linestyle="--", zorder=4,
            label="51% win / 1.1 PF  (Kelly +6.4% -> quarter-Kelly 1.6% binds)")
    ax.plot(prices, no_edge, color=CRIT, linewidth=2.6, zorder=5,
            label="48% win / 0.9 PF  (Kelly -9.8% -> ZERO SHARES)")

    ax.set_yscale("symlog", linthresh=10)
    ax.set_xlim(10, 1000)
    ax.set_ylim(-0.5, 30000)
    ax.set_xlabel("Entry price ($)")
    ax.set_ylabel("Approved shares (log scale)")

    for ticker, price in [("NVDA", 925.0), ("TSLA", 240.0), ("F", 12.0)]:
        shares = rm.calculate_position_size(ticker, price)
        ax.scatter([price], [shares], s=110, color=INK, zorder=6)
        ax.annotate(f"{ticker} ${price:,.0f}\n{shares:,} shares",
                    (price, shares), textcoords="offset points", xytext=(10, 10),
                    fontsize=9, color=INK, fontweight="bold")

    ax.axhline(0, color=CRIT, linewidth=1.0, linestyle=":", zorder=3)
    ax.text(1000, 0.35, "  REJECTED-NO-EDGE: zero is the right answer,\n"
                        "  not “round up to 1 share”",
            fontsize=9, color=CRIT, va="bottom", ha="right", fontweight="bold")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.text(0.005, -0.145,
            f"Stop width {DEFAULT_STOP_LOSS:.0%}. The 2% cap is on RISK "
            f"(position x stop width), not notional — so a \\$100K account "
            f"supports a \\$66,600 position at a 3% stop.\n"
            f"That is why the gatekeeper's 40% sector cap, not Rule 1, is what "
            f"finally cuts NVDA down.",
            transform=ax.transAxes, fontsize=8.5, color=INK2)
    caption(fig)
    return save(fig, "07-risk")


# --------------------------------------------------------------------------- #
#  8. Go-live (ch10) — the phased ladder and its two gates
# --------------------------------------------------------------------------- #
def render_going_live():
    from tracking.calculate_metrics import calculate_metrics, load_metrics
    from tracking.phase1_assessment import assess

    entries = load_metrics("daily_metrics_go.json")
    metrics = calculate_metrics(entries)
    result = assess(metrics)

    closes = np.array([e["portfolio_value_close"] for e in entries], dtype=float)
    days = np.arange(1, len(closes) + 1)
    peak = np.maximum.accumulate(closes)
    dd = (peak - closes) / peak * 100

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11.5, 7.6), sharex=True,
        gridspec_kw={"height_ratios": [2.5, 1]})

    frame(ax1, "Going live: 90 days, two gates, one ladder (ch10)",
          "Phase 1 is paper. The Day-30 gate decides whether real money is even "
          "on the table.")

    ax1.plot(days, closes, color=S1, linewidth=2.2, zorder=4)
    ax1.fill_between(days, closes.min() * 0.995, closes, color=S1, alpha=0.08,
                     zorder=2)

    ax1.axvline(30, color=INK2, linestyle="--", linewidth=1.5, zorder=3)
    ax1.axvline(60, color=INK2, linestyle="--", linewidth=1.5, zorder=3)
    ax1.text(30, closes.max(), " DAY 30\n Phase-1 gate", fontsize=9,
             fontweight="bold", color=INK, va="top")
    ax1.text(60, closes.max(), " DAY 60\n Phase-2 gate", fontsize=9,
             fontweight="bold", color=INK2, va="top")

    ax1.axvspan(0, 30, color=S1, alpha=0.05, zorder=1)
    ax1.axvspan(30, 60, color=S2, alpha=0.06, zorder=1)
    ax1.axvspan(60, 90, color=S3, alpha=0.06, zorder=1)
    for x, label in [(15, "PHASE 1\npaper · $100K virtual"),
                     (45, "PHASE 2\nlive · $500"),
                     (75, "PHASE 3\n$2K -> $5K -> $10K")]:
        ax1.text(x, closes.min() * 0.997, label, ha="center", va="bottom",
                 fontsize=9, color=INK2, fontweight="bold")

    verdict = result["verdict"]
    ax1.text(0.46, 0.50, f"DAY-30 GATE\n{verdict}",
             transform=ax1.transAxes, fontsize=11.5, ha="center", va="center",
             fontweight="bold", color=GOOD if verdict == "GO" else CRIT,
             bbox={"boxstyle": "round,pad=0.55", "facecolor": SURFACE,
                   "edgecolor": GOOD if verdict == "GO" else CRIT,
                   "linewidth": 1.6})
    ax1.text(0.46, 0.36,
             "No live data beyond Day 30: this repo\nships Phase 1 only. "
             "Phases 2 and 3 are\nyour real money, on your real broker.",
             transform=ax1.transAxes, fontsize=8.5, ha="center", va="center",
             color=INK2)

    rows = "   ".join(f"{n}: {v} [{s}]" for n, v, s in result["rows"])
    ax1.text(0.0, -0.055, rows, transform=ax1.transAxes, fontsize=8.2,
             color=INK2)
    ax1.set_ylabel("Portfolio value ($)")
    ax1.set_xlim(1, 90)

    frame(ax2, "", "")
    ax2.fill_between(days, 0, dd, color=CRIT, alpha=0.28, zorder=3)
    ax2.plot(days, dd, color=CRIT, linewidth=1.4, zorder=4)
    ax2.axhline(15, color=CRIT, linestyle="--", linewidth=1.2, zorder=2)
    ax2.text(89, 15, " 15% max-drawdown gate", ha="right", va="bottom",
             fontsize=8.5, color=CRIT, fontweight="bold")
    ax2.set_ylim(0, 18)
    ax2.invert_yaxis()
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Day")
    ax2.set_xticks([1, 15, 30, 45, 60, 75, 90])

    caption(fig)
    fig.subplots_adjust(hspace=0.30)
    return save(fig, "08-going-live")


REGISTRY = {
    "setup": render_setup,
    "screener": render_screener,
    "flow-trader": render_flow_trader,
    "backtester": render_backtester,
    "prediction": render_prediction,
    "multi-agent": render_multi_agent,
    "risk": render_risk,
    "going-live": render_going_live,
}


def main(argv: list[str]) -> int:
    wanted = argv[1:] or list(REGISTRY)
    unknown = [w for w in wanted if w not in REGISTRY]
    if unknown:
        print(f"Unknown item(s): {', '.join(unknown)}")
        print(f"Known: {', '.join(REGISTRY)}")
        return 1

    print(f"Rendering {len(wanted)} figure(s) from the repo's own code + "
          f"synthetic fixtures...\n")
    for key in wanted:
        print(f"[{key}]")
        REGISTRY[key]()
    print(f"\nDone. {len(wanted)} figure(s) in {OUT.relative_to(ROOT)}/")
    print("Every one of them is computed, stamped synthetic, and committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
