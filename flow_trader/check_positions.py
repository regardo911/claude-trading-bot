"""Print current Alpaca paper positions with P&L — Chapter 5 (ch05.md:442-460).

    python flow_trader/check_positions.py

Educational software. Not financial advice. See DISCLAIMER.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from utils import banner  # noqa: E402
from utils.offline import get_trading_client, is_live_mode  # noqa: E402

load_dotenv()


def main() -> int:
    banner()
    client = get_trading_client()
    account = client.get_account()
    positions = client.get_all_positions()

    print(f"=== POSITIONS ({'LIVE' if is_live_mode() else 'paper'}) ===")
    print(f"Portfolio value: ${float(account.portfolio_value):,.2f} | "
          f"Cash: ${float(account.cash):,.2f}\n")

    if not positions:
        print("No open positions.")
        return 0

    for pos in positions:
        qty = int(pos.qty)
        pnl = float(pos.unrealized_pl)
        pnl_pct = float(pos.unrealized_plpc) * 100
        side = "SHORT" if qty < 0 else "LONG "
        print(f"{side} {pos.symbol:<6} {abs(qty):>6} shares @ "
              f"${float(pos.avg_entry_price):>9,.2f} | "
              f"now ${float(pos.current_price):>9,.2f} | "
              f"P&L: ${pnl:+,.2f} ({pnl_pct:+.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
