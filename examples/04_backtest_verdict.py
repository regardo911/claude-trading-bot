"""Example — the ch06 Monte Carlo, and the permutation trap it avoids.

Runs the same trade set through BOTH samplers and prints the number of distinct
final values each produces. A naive permutation (`random.sample`) keeps the trade
set identical; the equity update is a product; a product does not care about order.
Every simulation therefore lands on the same number — no fan, no percentiles, no
5th-percentile gate. The 2nd-edition book and this repo both bootstrap WITH
replacement (`random.choices`), which is the only sampler that fans out. (Earlier
printings used the permutation; see docs/book-deviations.md #6, resolved in book.)
"""
import random

import _bootstrap  # noqa: F401

from backtester import backtester as bt

if __name__ == "__main__":
    trades = bt.calculate_trade_returns(bt.load_historical_flow_from_csv())
    returns = [t["return"] for t in trades]
    print(f"\n{len(trades)} trades from the synthetic fixture.\n")

    # The naive permutation (what earlier printings used).
    finals = []
    rng = random.Random(42)
    for _ in range(200):
        capital = 100_000.0
        for r in rng.sample(returns, len(returns)):
            capital += capital * 0.02 * r
        finals.append(round(capital, 4))
    print(f"random.sample  (the naive permutation): "
          f"{len(set(finals)):>4} distinct final values out of 200 sims")

    # What the book and this repo actually use.
    mc = bt.monte_carlo_simulation(trades, n_simulations=200)
    unique = {round(v, 6) for v in mc["final_values"]}
    print(f"random.choices (book + this repo):      "
          f"{len(unique):>4} distinct final values out of 200 sims")

    print("\nOnly one of those two can produce a fan chart. Now the full backtest:\n")
    bt.run_backtest()
