"""Example — the ch05 exit rules, including the short-side trap they avoid.

`check_exits()` sells half a position at its +6% profit target — but reducing a
SHORT means BUYing it back, not selling. This example holds a short TSLA position
at +6% and shows the correct cover (an `OrderSide.BUY`), exactly as the 2nd-edition
book does. (Earlier printings submitted `OrderSide.SELL` unconditionally, which on
a short *adds to* it and destroys capital.)

It also demonstrates the breakeven stop and the 5-day time limit.
"""
import _bootstrap  # noqa: F401

from flow_trader import flow_trader as ft
from utils.offline import OfflineTradingClient

if __name__ == "__main__":
    print("=== ch05 exit management ===\n")
    print("Fixture positions: NVDA -3.0% (stop) · AMZN +6.0% long (target) · "
          "TSLA +6.0% SHORT (target) · MU flat\n")

    ft.alpaca = OfflineTradingClient(paper=True)
    ft._load_exit_state = lambda: {}
    ft._save_exit_state = lambda s: None

    actions = ft.check_exits()

    print("\nOrders the bot actually submitted:")
    for order in ft.alpaca.orders:
        print(f"  {order.side.upper():<5} {order.qty:>4.0f} {order.symbol}")

    print("\nThe TSLA line is the one that matters. It is a BUY, because reducing")
    print("a short means buying it back. Earlier printings would have SOLD more.")
