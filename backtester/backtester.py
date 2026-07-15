"""Monte Carlo backtester — Chapter 6. **Offline, deterministic, and LLM-free.**

This module never calls Claude or any other model, by design: "the reasoning
happens in the Monte Carlo math, not in a model" (ch06.md:64). If you copy this
pattern for a different strategy, resist the urge to add an Anthropic client.

    python backtester/backtester.py

CSV -> ch04 filters -> 5-day forward returns -> in/out-of-sample split ->
1,000 Monte Carlo simulations -> verdict + fan chart.

================================ READ THIS ================================
THE SAMPLER (docs/book-deviations.md #6 — resolved in the 2nd edition)

This module samples **with** replacement:

    resampled = random.choices(returns, k=n_trades)   # ch06.md:205

That is a bootstrap, and it is what the current book does. It is the only sampler
that produces the fan of outcomes the chapter's argument requires. Sampling
*without* replacement (`random.sample`) is a permutation, the equity update is a
product, and a product is invariant under permutation — so every simulation would
land on the identical final value and the fan chart would be a flat line. Earlier
printings had that bug; the 2nd edition and this module both avoid it. A
regression test guards it either way.

Everything this file prints is computed by this code on the committed synthetic
fixture. No illustrative report from the book is reproduced here.
==========================================================================

Illustrative results on synthetic sample data — not indicative of real or
historical performance. Educational software. Not financial advice.
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import artifact, banner, fixture  # noqa: E402
from utils.offline import get_yfinance, offline_enabled  # noqa: E402

# --- Constants (ch06.md:95-97, 187-189) ------------------------------------
CSV_PATH = Path("backtester/historical_flow.csv")
FIXTURE_CSV = fixture("historical_flow.csv")
OVERFIT_GAP_PP = 5.0        # in-sample vs out-of-sample win-rate gap (pp)
OVERFIT_SHARPE_DROP = 0.5   # in -> out Sharpe drop threshold
MIN_TRADES = 30             # ch06.md:253 — below this: INSUFFICIENT DATA
RANDOM_SEED = 42            # deterministic runs; the fan is real, not the seed

# Appendix B's cheat sheet says "Minimum trades: 100" (appendices.md:501) while
# the code gates at 30 (three times over, ch06.md:253/450/676). The worked
# example wins: 30 is the hard gate. Treat 100 as the recommended floor before
# you trust any verdict. See docs/book-deviations.md (#2).
RECOMMENDED_MIN_TRADES = 100

CSV_COLUMNS = ["date", "ticker", "strike", "expiry", "type", "volume",
               "open_interest", "volume_oi_ratio", "total_premium",
               "has_sweep", "has_floor"]

SYNTHETIC_LABEL = ("illustrative results on synthetic sample data — "
                   "not indicative of real or historical performance")


def _resolve_csv(path: Path = CSV_PATH) -> Path:
    """Your CSV if you populated one; otherwise the bundled synthetic fixture."""
    if path.exists():
        return path
    if FIXTURE_CSV.exists():
        print(f"[offline] {path} not found. Falling back to the bundled "
              f"synthetic fixture: {FIXTURE_CSV}")
        print(f"[offline] {SYNTHETIC_LABEL}.\n")
        return FIXTURE_CSV
    raise FileNotFoundError(
        f"{path} not found. Populate it via UW Data Shop (download the "
        "historical-options-trades bundle and save as CSV) OR by looping "
        "`GET /api/option-trades/full-tape/{date}` for each trading day in your "
        "window — there is no 180-day range query. Expected columns: "
        + ", ".join(CSV_COLUMNS)
    )


def load_historical_flow_from_csv(path: Path = CSV_PATH) -> list[dict]:
    """Load historical options flow from a local CSV and apply the ch04 filters.

    There is no single UW REST endpoint that returns a 180-day range of options
    flow. Historical data comes from two places (ch06.md:99-122):
      (1) the UW Data Shop — downloadable CSV/zip bundles (Advanced tier, or the
          $250/mo historical-options-trades add-on);
      (2) a one-time day-by-day loop over `GET /api/option-trades/full-tape/{date}`
          (one date per call), cached to disk.
    """
    df = pd.read_csv(_resolve_csv(path), parse_dates=["date"])
    missing = [c for c in CSV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"historical flow CSV is missing columns: {missing}")
    # Apply the Chapter 4 filters before forward-return enrichment so we don't
    # burn yfinance calls on events the screener would have skipped.
    mask = (
        (df["volume_oi_ratio"] > 3.0)
        & (df["total_premium"] > 200_000)
        & (df["has_sweep"].astype(bool) | df["has_floor"].astype(bool))
    )
    return df[mask].to_dict(orient="records")


def fetch_forward_return(ticker, event_date, horizon_days=5):
    """The underlying's % change from `event_date` to +N trading days.

    Returns None when there is no usable data for the window — a delisted ticker,
    a holiday date, or a symbol yfinance has never heard of. Those events are
    skipped, which is exactly the survivorship-bias hole ch06.md:37 warns about:
    the tickers that vanished are the ones your backtest quietly drops.
    """
    yf = get_yfinance()
    try:
        start = (event_date - timedelta(days=2)).strftime("%Y-%m-%d")
        end = (event_date + timedelta(days=horizon_days + 5)).strftime("%Y-%m-%d")
        hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    except Exception:  # noqa: BLE001
        return None
    if hist is None or hist.empty:
        return None
    closes = hist["Close"]
    entry_idx = closes.index.get_indexer(
        [pd.Timestamp(event_date)], method="bfill")[0]
    exit_idx = entry_idx + horizon_days
    if entry_idx < 0 or exit_idx >= len(closes):
        return None
    entry = float(closes.iloc[entry_idx])
    exit_price = float(closes.iloc[exit_idx])
    if entry <= 0:
        return None
    return (exit_price - entry) / entry


def calculate_trade_returns(flow_records) -> list[dict]:
    """5-day forward return per event, signed by the direction of the bet.

    A call sweep wins when the stock rises. A put sweep wins when it falls, so
    the underlying's move is flipped — the strategy-level return reflects the
    directional bet, not just the stock (ch06.md:159-165).
    """
    trades = []
    for event in flow_records:
        event_date = pd.to_datetime(event["date"]).date()
        ticker = str(event.get("ticker", "")).strip().upper()
        if not ticker:
            continue
        underlying_ret = fetch_forward_return(ticker, event_date)
        if underlying_ret is None:
            continue
        flow_type = str(event.get("type", "call")).lower()
        ret = underlying_ret if flow_type == "call" else -underlying_ret
        trades.append({
            "ticker": ticker,
            "date": str(event_date),
            "return": ret,
            "total_premium": float(event.get("total_premium", 0) or 0),
            "volume_oi_ratio": float(event.get("volume_oi_ratio", 0) or 0),
            "type": flow_type,
        })
    return trades


def monte_carlo_simulation(trades, n_simulations=1000, initial_capital=100000,
                           position_pct=0.02, seed=RANDOM_SEED):
    """Bootstrap the trade sequence `n_simulations` times.

    **`random.choices`, not `random.sample`.** See the module docstring and
    docs/book-deviations.md (#6). Sampling *with* replacement is what makes the
    curves fan out; sampling without it (a permutation) makes every simulation
    land on the same final value, because the equity update is a product and a
    product does not care about order.
    """
    rng = random.Random(seed)
    returns = [t["return"] for t in trades]
    n_trades = len(returns)

    all_curves, final_values, max_drawdowns = [], [], []

    for _ in range(n_simulations):
        # Bootstrap WITH replacement — same as the 2nd-edition book (ch06.md:205).
        resampled = rng.choices(returns, k=n_trades)

        capital = initial_capital
        curve = [capital]
        peak = capital
        max_dd = 0.0

        for ret in resampled:
            position_size = capital * position_pct
            capital += position_size * ret
            curve.append(capital)
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak
            if dd > max_dd:
                max_dd = dd

        all_curves.append(curve)
        final_values.append(capital)
        max_drawdowns.append(max_dd)

    return {
        "curves": all_curves,
        "final_values": final_values,
        "max_drawdowns": max_drawdowns,
        "n_trades": n_trades,
        "n_simulations": n_simulations,
        "initial_capital": initial_capital,
        "position_pct": position_pct,
        "sampler": "random.choices (bootstrap with replacement)",
    }


def calculate_sharpe(returns, risk_free_rate=0.05):
    """Annualized Sharpe, transcribed exactly as the book prints it (ch06.md:234-240).

    A caveat the repo owes you, and does not silently "fix": sqrt(252) annualizes
    *daily* returns, and these are *per-trade* returns on a 5-day horizon. The
    annualizer is wrong in kind, so the number is inflated relative to a properly
    annualized Sharpe. The book's own printed 1.24 is not reachable from its own
    printed strategy stats either (it would need a 13.3% per-trade sigma). The
    formula is kept as printed because ch09 and ch10 both consume "Sharpe" from
    it, and silently re-annualizing here would break their worked examples
    instead. See docs/book-deviations.md (#8). Read it as a relative score across
    runs of this repo, not as a portable Sharpe ratio.
    """
    returns_array = np.array(returns, dtype=float)
    if len(returns_array) == 0:
        return 0.0
    excess = returns_array - (risk_free_rate / 252)
    if np.std(excess) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(excess) * np.sqrt(252))


def in_out_sample_split(trades, gap_pp=OVERFIT_GAP_PP,
                        sharpe_drop=OVERFIT_SHARPE_DROP):
    """Chronological in-sample vs out-of-sample split + the overfit flag.

    A real edge holds up out-of-sample. A flagged strategy was tuned on the
    in-sample window and didn't generalize.
    """
    if len(trades) < MIN_TRADES:
        return {
            "in_sample_n": 0, "out_of_sample_n": 0,
            "in_sample_win_rate": None, "out_of_sample_win_rate": None,
            "win_rate_gap_pp": None, "in_sample_sharpe": None,
            "out_of_sample_sharpe": None, "sharpe_drop": None, "overfit": None,
            "note": f"Fewer than {MIN_TRADES} trades; split too small to be informative.",
        }
    sorted_trades = sorted(trades, key=lambda t: t["date"])
    mid = len(sorted_trades) // 2
    in_sample, out_sample = sorted_trades[:mid], sorted_trades[mid:]
    in_returns = [t["return"] for t in in_sample]
    out_returns = [t["return"] for t in out_sample]
    in_win = sum(1 for r in in_returns if r > 0) / len(in_returns)
    out_win = sum(1 for r in out_returns if r > 0) / len(out_returns)
    in_sharpe = calculate_sharpe(in_returns)
    out_sharpe = calculate_sharpe(out_returns)
    gap = abs(in_win - out_win) * 100
    overfit = gap > gap_pp or (in_sharpe - out_sharpe) > sharpe_drop
    return {
        "in_sample_n": len(in_sample), "out_of_sample_n": len(out_sample),
        "in_sample_win_rate": in_win, "out_of_sample_win_rate": out_win,
        "win_rate_gap_pp": gap, "in_sample_sharpe": in_sharpe,
        "out_of_sample_sharpe": out_sharpe, "sharpe_drop": in_sharpe - out_sharpe,
        "overfit": overfit,
    }


def walk_forward_validation(trades, n_windows=3, underperform_pp=10.0):
    """Walk-forward validation — the ch06.md:607 add-on prompt, implemented.

    Three equal windows. For window N, train on windows 1..N-1 and test on N.
    Flag any test window that underperforms its training period by more than 10
    percentage points of win rate.
    """
    if len(trades) < MIN_TRADES:
        return {"windows": [], "flagged": None,
                "note": f"Fewer than {MIN_TRADES} trades; walk-forward skipped."}
    ordered = sorted(trades, key=lambda t: t["date"])
    size = len(ordered) // n_windows
    windows, flagged = [], False
    for n in range(1, n_windows):
        train = ordered[:size * n]
        test = ordered[size * n: size * (n + 1)] if n < n_windows - 1 else ordered[size * n:]
        if not train or not test:
            continue
        train_win = sum(1 for t in train if t["return"] > 0) / len(train) * 100
        test_win = sum(1 for t in test if t["return"] > 0) / len(test) * 100
        under = train_win - test_win
        hit = under > underperform_pp
        flagged = flagged or hit
        windows.append({
            "window": n + 1, "train_n": len(train), "test_n": len(test),
            "train_win_rate": f"{train_win:.1f}%", "test_win_rate": f"{test_win:.1f}%",
            "underperformance_pp": f"{under:.1f}", "flagged": hit,
        })
    return {"windows": windows, "flagged": flagged,
            "threshold_pp": underperform_pp}


def generate_report(trades, mc_results, overfit_check, walk_forward=None):
    """Assemble the full backtest report."""
    returns = [t["return"] for t in trades]
    final_values = mc_results["final_values"]
    drawdowns = mc_results["max_drawdowns"]

    win_rate = len([r for r in returns if r > 0]) / len(returns)
    avg_win = float(np.mean([r for r in returns if r > 0])) if any(
        r > 0 for r in returns) else 0.0
    avg_loss = float(np.mean([r for r in returns if r < 0])) if any(
        r < 0 for r in returns) else 0.0
    sharpe = calculate_sharpe(returns)

    # Average-based profit factor: R = avg win / avg loss, which is what ch09's
    # Kelly formula consumes (ch09.md:39). ch10 and Appendix D define profit
    # factor as SUM of wins / SUM of losses — a different number on the same
    # data. `tracking/calculate_metrics.py` implements that one under a distinct
    # name (`gross_profit_factor`) so one name never carries two formulas.
    # Formatted to 2dp: the printed code leaves this one stat raw and emits
    # 1.7850467289719627. See docs/book-deviations.md (#7).
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

    p5, p25, p50, p75, p95 = (float(np.percentile(final_values, q))
                              for q in (5, 25, 50, 75, 95))
    initial = mc_results["initial_capital"]

    # EDGE CONFIRMED needs BOTH a positive 5th percentile AND a passing split.
    #  - overfit_flag None  -> fewer than 30 trades. "Not enough data to
    #    validate" is not the same as "validated".
    #  - p5 > initial but overfit True -> the trades came from one regime.
    #  - p5 < initial but overfit False -> consistent, and consistently losing.
    overfit_flag = overfit_check.get("overfit")
    if overfit_flag is None:
        verdict = "INSUFFICIENT DATA"
    elif overfit_flag:
        verdict = "OVERFIT"
    elif p5 > initial:
        verdict = "EDGE CONFIRMED"
    else:
        verdict = "NO EDGE"

    def _pct(x):
        return f"{x:.1%}" if x is not None else "n/a"

    def _f(x):
        return f"{x:.2f}" if x is not None else "n/a"

    report = {
        "data_source": SYNTHETIC_LABEL if offline_enabled() else "live yfinance",
        "strategy_stats": {
            "total_trades": len(trades),
            "win_rate": f"{win_rate:.1%}",
            "avg_winner": f"{avg_win:.2%}",
            "avg_loser": f"{avg_loss:.2%}",
            "profit_factor": f"{profit_factor:.2f}",
            "profit_factor_definition": "average win / average loss (ch06)",
            "sharpe_ratio": f"{sharpe:.2f}",
        },
        "overfit_check": {
            "in_sample_n": overfit_check["in_sample_n"],
            "out_of_sample_n": overfit_check["out_of_sample_n"],
            "in_sample_win_rate": _pct(overfit_check["in_sample_win_rate"]),
            "out_of_sample_win_rate": _pct(overfit_check["out_of_sample_win_rate"]),
            "win_rate_gap_pp": (f"{overfit_check['win_rate_gap_pp']:.1f}"
                                if overfit_check["win_rate_gap_pp"] is not None
                                else "n/a"),
            "in_sample_sharpe": _f(overfit_check["in_sample_sharpe"]),
            "out_of_sample_sharpe": _f(overfit_check["out_of_sample_sharpe"]),
            "sharpe_drop": _f(overfit_check["sharpe_drop"]),
            "overfit_flag": overfit_flag,
            "note": overfit_check.get("note", ""),
        },
        "monte_carlo": {
            "simulations": mc_results["n_simulations"],
            "sampler": mc_results["sampler"],
            "initial_capital": f"${initial:,.0f}",
            "5th_percentile": f"${p5:,.0f} ({(p5 / initial - 1) * 100:+.1f}%)",
            "25th_percentile": f"${p25:,.0f} ({(p25 / initial - 1) * 100:+.1f}%)",
            "median": f"${p50:,.0f} ({(p50 / initial - 1) * 100:+.1f}%)",
            "75th_percentile": f"${p75:,.0f} ({(p75 / initial - 1) * 100:+.1f}%)",
            "95th_percentile": f"${p95:,.0f} ({(p95 / initial - 1) * 100:+.1f}%)",
            "unique_final_values": len({round(v, 6) for v in final_values}),
            "median_max_drawdown": f"{np.median(drawdowns):.1%}",
            "worst_max_drawdown": f"{max(drawdowns):.1%}",
        },
        "verdict": verdict,
    }
    if walk_forward is not None:
        report["walk_forward"] = walk_forward
    return report


def plot_monte_carlo(mc_results, output_path="backtester/monte_carlo.png"):
    """Fan chart of the bootstrapped equity curves.

    matplotlib is the optional `viz` extra, not a core dependency. Without it,
    the backtest still runs and still writes `report.json`; you just don't get
    the PNG. (`pip install -e ".[viz]"`)
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[skip] matplotlib not installed — no fan chart. "
              "Install the viz extra: pip install -e \".[viz]\"")
        return None

    curves = mc_results["curves"]
    fig, ax = plt.subplots(figsize=(12, 6))

    for i in range(min(200, len(curves))):
        ax.plot(curves[i], alpha=0.05, color="#2a78d6", linewidth=0.5)

    arr = np.array(curves, dtype=float)
    p5_line = np.percentile(arr, 5, axis=0)
    p50_line = np.percentile(arr, 50, axis=0)
    p95_line = np.percentile(arr, 95, axis=0)
    x = range(arr.shape[1])

    ax.plot(x, p50_line, color="#2a78d6", linewidth=2, label="Median")
    ax.plot(x, p5_line, color="#d03b3b", linewidth=1.5, linestyle="--",
            label="5th percentile")
    ax.plot(x, p95_line, color="#1baf7a", linewidth=1.5, linestyle="--",
            label="95th percentile")
    ax.fill_between(x, p5_line, p95_line, alpha=0.10, color="#2a78d6")

    initial = mc_results["initial_capital"]
    ax.axhline(y=initial, color="#8a8a85", linestyle=":", label="Starting capital")

    ax.set_xlabel("Trade number")
    ax.set_ylabel("Portfolio value ($)")
    ax.set_title(f"Monte Carlo: {mc_results['n_simulations']:,} bootstrapped "
                 f"equity curves (ch06)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.text(0.99, 0.01, "synthetic sample data — illustrative mechanics only",
             ha="right", va="bottom", fontsize=7, color="#8a8a85")

    fig.tight_layout()
    out = artifact(output_path)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Chart saved to {out}")
    return out


SCENARIOS = ("no_edge", "overfit", "edge_candidate")


def load_scenario(name: str) -> dict:
    """Load a pre-computed teaching scenario (fixtures/scenarios/<name>.json).

    Each scenario is a synthetic trade set engineered to land on a specific
    verdict, so a reader can watch the backtester DIAGNOSE — NO EDGE, OVERFIT,
    and EDGE CONFIRMED — instead of only ever seeing the happy path. The returns
    are pre-computed (not fetched through yfinance) precisely so the verdict is
    deterministic and the lesson is repeatable. It is a property of the fixture,
    never evidence about a real market.
    """
    path = fixture(f"scenarios/{name}.json")
    if not path.exists():
        raise FileNotFoundError(
            f"Unknown scenario {name!r}. Available: {', '.join(SCENARIOS)} "
            f"(looked for {path})")
    return json.loads(path.read_text())


def run_backtest(scenario: str | None = None):
    """Main backtest function.

    With ``scenario`` set to one of SCENARIOS, the backtester runs a synthetic
    teaching set engineered to reach a specific verdict — for learning what the
    tool does when a strategy does NOT work. Without it, the book's ch06 path:
    load the CSV, fetch 5-day forward returns, split, and simulate.
    """
    banner()
    print("=== BACKTEST ENGINE ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if scenario is not None:
        data = load_scenario(scenario)
        trades = data["trades"]
        print(f"\nSCENARIO: {scenario}  (expected verdict: {data['expected_verdict']})")
        print(f"  {data['description']}\n")
        print(f"Loaded {len(trades)} pre-computed synthetic trades "
              f"(no CSV, no yfinance).\n")
    else:
        print(f"Loading historical flow from {CSV_PATH}...\n")
        flow_records = load_historical_flow_from_csv()
        print(f"Loaded {len(flow_records)} filtered historical events.\n")
        print("Fetching 5-day forward returns...")
        trades = calculate_trade_returns(flow_records)
        print(f"Calculated returns for {len(trades)} valid trades.\n")

    # Fail closed on a zero-trade set. Generating a report with no returns would
    # crash on the win-rate division; proceeding silently would risk an
    # underpowered "EDGE CONFIRMED".
    if not trades:
        print("No valid trades after forward-return enrichment.")
        print("Check historical_flow.csv dates, tickers, and price coverage; the "
              "screener filter (vol/OI > 3x, premium > $200K, sweeps/blocks) may "
              "also be too tight for the loaded date window.")
        return None

    if len(trades) < MIN_TRADES:
        print(f"WARNING: Fewer than {MIN_TRADES} valid trades. The in/out split is "
              "too small to be informative and Monte Carlo is under-powered. "
              "Expect VERDICT: INSUFFICIENT DATA.")
    elif len(trades) < RECOMMENDED_MIN_TRADES:
        print(f"NOTE: {len(trades)} trades clears the {MIN_TRADES}-trade hard gate "
              f"but is below the {RECOMMENDED_MIN_TRADES}-trade floor Appendix B "
              f"recommends before you trust a verdict.")

    print("Running in-sample vs out-of-sample split...")
    overfit_check = in_out_sample_split(trades)
    print("Split complete.\n")

    print("Running walk-forward validation (3 windows)...")
    walk_forward = walk_forward_validation(trades)
    print("Walk-forward complete.\n")

    print("Running 1,000 Monte Carlo simulations "
          "(bootstrap WITH replacement)...")
    mc_results = monte_carlo_simulation(trades)
    print("Simulations complete.\n")

    report = generate_report(trades, mc_results, overfit_check, walk_forward)

    print("=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    print("\nStrategy Statistics:")
    for key, value in report["strategy_stats"].items():
        print(f"  {key.replace('_', ' ').title()}: {value}")

    print("\nOverfitting Check (in-sample vs out-of-sample):")
    for key, value in report["overfit_check"].items():
        if value == "" or value is None:
            continue
        print(f"  {key.replace('_', ' ').title()}: {value}")

    if report.get("walk_forward", {}).get("windows"):
        print("\nWalk-Forward Validation (3 windows, flag at >10pp):")
        for w in report["walk_forward"]["windows"]:
            state = "FLAGGED" if w["flagged"] else "ok"
            print(f"  Window {w['window']}: train {w['train_win_rate']} "
                  f"(n={w['train_n']}) -> test {w['test_win_rate']} "
                  f"(n={w['test_n']}) | underperformance "
                  f"{w['underperformance_pp']}pp [{state}]")

    print("\nMonte Carlo Results (1,000 simulations):")
    for key, value in report["monte_carlo"].items():
        print(f"  {key.replace('_', ' ').title()}: {value}")

    print(f"\nVERDICT: {report['verdict']}")

    if report["verdict"] == "EDGE CONFIRMED":
        print("The 5th percentile portfolio value is above starting capital,")
        print("AND the strategy generalizes from in-sample to out-of-sample.")
        print("This is the only verdict that supports going live.")
    elif report["verdict"] == "OVERFIT":
        print("The Monte Carlo math may look fine, but performance dropped")
        print("sharply from in-sample to out-of-sample. Simplify the strategy")
        print("(fewer parameters) and re-backtest. Do NOT go live.")
    elif report["verdict"] == "INSUFFICIENT DATA":
        print(f"Fewer than {MIN_TRADES} valid trades. The in/out split can't tell")
        print("you whether the strategy generalizes and the Monte Carlo numbers")
        print("are under-powered. The fix is more data, not more tuning.")
    else:
        print("The 5th percentile portfolio value is BELOW starting capital.")
        print("Your strategy can lose money depending on trade order.")
        print("Do NOT go live with this strategy without modifications.")

    print(f"\n[{SYNTHETIC_LABEL}]" if offline_enabled() else "")

    if scenario is not None:
        print("\n" + "-" * 60)
        print("DIAGNOSE, don't celebrate. Ask yourself:")
        print("  - Which check produced this verdict — the 5th percentile, the")
        print("    in/out-of-sample split, or the trade count?")
        print("  - If you changed position size, which numbers move together?")
        print("  - What would you need to SEE before trusting this with money?")
        print("A green verdict on a synthetic fixture is a mechanism working, not")
        print("an edge existing. Run the other scenarios and compare.")
    else:
        print("\n" + "-" * 60)
        print("This is the calibrated fixture — engineered to have an edge, so the")
        print("verdict here is a mechanism working, not evidence of one. See what")
        print("the backtester does when a strategy fails:")
        print("  make demo-ch06-no-edge   make demo-ch06-overfit")

    plot_monte_carlo(mc_results)

    suffix = f"_{scenario}" if scenario else ""
    report_file = artifact(f"backtester/report{suffix}.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report saved to {report_file}")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Monte Carlo backtester (ch06). Offline, deterministic, LLM-free.")
    parser.add_argument(
        "--scenario", choices=SCENARIOS, default=os.environ.get("CTB_SCENARIO"),
        help="Run a synthetic teaching scenario instead of the ch06 CSV path: "
             "no_edge, overfit, or edge_candidate.")
    args = parser.parse_args()
    run_backtest(scenario=args.scenario)
