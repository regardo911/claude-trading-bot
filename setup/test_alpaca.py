"""Alpaca paper connectivity smoke test — Chapter 2, Step 4 (ch02.md:252-282).

Expected output (ch02.md:279-281):

    Account status: ACTIVE
    Cash: $100,000.00
    Portfolio value: $100,000.00

Paper mode always. The client this script gets back cannot place a live order
unless someone edited code and called `set_live_mode(True, confirm=...)`.
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
    print(f"Account status: {account.status}")
    print(f"Cash: ${float(account.cash):,.2f}")
    print(f"Portfolio value: ${float(account.portfolio_value):,.2f}")
    print(f"Mode: {'LIVE (real money)' if is_live_mode() else 'paper (simulated)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
