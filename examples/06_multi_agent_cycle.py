"""Example — the ch08 four-agent cycle and its headline moment.

The Analyst finds three good trades. The Risk Manager approves one, cuts one down,
and kills the third. All three were individually sound; together they would have
built dangerous sector concentration. No single agent catches that.
"""
import _bootstrap  # noqa: F401

from multi_agent.multi_agent import run_multi_agent_cycle

if __name__ == "__main__":
    cycle = run_multi_agent_cycle()
    filled = [r for r in cycle["execution"] if r["status"] == "FILLED"]
    print(f"\n{len(filled)} bracket order(s) filled. Each one carries its "
          f"protective legs\nto the broker at entry, so the stops fire even when "
          f"the bot is not running.")
    for r in filled:
        print(f"  {r['ticker']:<6} {r['direction']:<5} {r['shares']:>4} shares  "
              f"stop ${r['bracket_stop_price']:>8,.2f}  "
              f"target ${r['bracket_take_profit_price']:>8,.2f}  "
              f"order_class={r['order_class']}")
