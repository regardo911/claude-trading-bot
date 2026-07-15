"""Kalshi RSA-PSS auth helper — Chapter 7 (ch07.md:467-501, appendices.md:247-310).

Kalshi signs every request with an RSA-PSS signature. If you have seen an older
guide showing a `kalshi_login(email, password)` POST to `/login`, that pattern is
obsolete and returns 401 against the current API.

The signed payload is `{timestamp_ms}{HTTP_METHOD}{request_path}`, concatenated
with **no separator**, signed RSA-PSS / SHA-256 / MGF1-SHA256 / salt length =
digest length, and sent as three headers:

    KALSHI-ACCESS-KEY        your Key ID (a UUID)
    KALSHI-ACCESS-SIGNATURE  base64 of the signature
    KALSHI-ACCESS-TIMESTAMP  milliseconds since epoch

ORDER SUBMISSION IS GATED
-------------------------
`place_kalshi_order()` exists because the chapter's build prompt names it
(ch07.md:496). It **refuses to run** unless someone has edited code and called
`utils.offline.set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")`. There is no
env var and no CLI flag that enables it.

`prediction/prediction_analyzer.py` does not import this module and never will —
the book explicitly refuses to ship an order path for a CFTC-regulated venue
(ch07.md:39), and `tests/test_no_order_path.py` enforces that.

No PEM file is ever committed to this repo. The test suite generates a throwaway
keypair in-process.

Educational software. Not financial advice. See DISCLAIMER.md.
"""

from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.offline import LiveModeError, is_live_mode, offline_enabled  # noqa: E402

KALSHI_BASE = "https://trading-api.kalshi.com/trade-api/v2"

#: appendices.md:302 — roughly 10 requests per second.
RATE_LIMIT_SLEEP = 0.15


def load_private_key(path: str | None = None):
    """Load the RSA private key from the PEM Kalshi gave you.

    Download the private key immediately when you create the API key pair.
    Kalshi cannot retrieve it later (ch07.md:475).
    """
    from cryptography.hazmat.primitives import serialization

    pem_path = path or os.getenv("KALSHI_PRIVATE_KEY_PATH")
    if not pem_path:
        raise RuntimeError(
            "KALSHI_PRIVATE_KEY_PATH is not set. Point it at the PEM file Kalshi "
            "gave you when you generated the API key pair."
        )
    with open(pem_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def sign_payload(private_key, timestamp_ms: str, method: str, path: str) -> str:
    """RSA-PSS / SHA-256 / MGF1-SHA256 / salt = digest length. Base64 out.

    Kept as a free function so tests can sign against a throwaway keypair without
    a client, a key file, or a network.
    """
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    payload = f"{timestamp_ms}{method}{path}".encode()  # no separator
    signature = private_key.sign(
        payload,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode()


def kalshi_headers(method: str, path: str, key_id: str, private_key) -> dict:
    """The three headers every Kalshi request needs (appendices.md:273-288)."""
    ts = str(int(time.time() * 1000))
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": sign_payload(private_key, ts, method, path),
        "KALSHI-ACCESS-TIMESTAMP": ts,
    }


class KalshiClient:
    """Thin signed-request client. Reads are free; writes are gated."""

    def __init__(self, key_id: str | None = None, private_key_path: str | None = None):
        self.key_id = key_id or os.getenv("KALSHI_KEY_ID")
        self._key_path = private_key_path or os.getenv("KALSHI_PRIVATE_KEY_PATH")
        self._private_key = None

    @property
    def private_key(self):
        if self._private_key is None:
            self._private_key = load_private_key(self._key_path)
        return self._private_key

    def _sign(self, method: str, path: str) -> dict:
        if not self.key_id:
            raise RuntimeError("KALSHI_KEY_ID is not set.")
        return kalshi_headers(method, path, self.key_id, self.private_key)

    def get_kalshi_markets(self, status: str = "open", limit: int = 100) -> list:
        """`GET /markets` -> the `markets` array.

        Offline this raises rather than inventing market data: there is no Kalshi
        fixture in this repo, and a stub that made up event contracts would be
        exactly the hallucination the book keeps warning about. Set CTB_OFFLINE=0
        with a real key pair to use it.
        """
        if offline_enabled():
            raise RuntimeError(
                "Kalshi has no offline fixture in this repo — inventing event "
                "contracts would be the hallucination ch07 warns about. Set "
                "CTB_OFFLINE=0 with KALSHI_KEY_ID + KALSHI_PRIVATE_KEY_PATH to "
                "query the live API. The signing path itself is fully tested "
                "offline against a throwaway keypair (tests/test_kalshi.py)."
            )
        import requests

        path = "/trade-api/v2/markets"
        resp = requests.get(
            f"{KALSHI_BASE}/markets",
            headers=self._sign("GET", path),
            params={"status": status, "limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        time.sleep(RATE_LIMIT_SLEEP)
        return resp.json().get("markets", [])

    def place_kalshi_order(self, ticker: str, side: str, count: int,
                           yes_price: int) -> dict:
        """`POST /portfolio/orders` — **REAL MONEY. Gated.**

        Refuses unless `utils.offline.set_live_mode(True, confirm=...)` has run in
        this process. No environment variable and no CLI flag can enable it.

        Args:
            ticker: the Kalshi market ticker.
            side: "yes" or "no" (lowercase — a 422 otherwise).
            count: positive integer number of contracts.
            yes_price: price in cents (1-99).
        """
        if not is_live_mode():
            raise LiveModeError(
                "place_kalshi_order() refused: live mode is off.\n"
                "Kalshi orders spend real money. To enable, edit your own code "
                "and call:\n"
                '    from utils.offline import set_live_mode\n'
                '    set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")\n'
                "There is deliberately no flag and no env var for this.\n"
                "Trading carries substantial risk of loss. See DISCLAIMER.md."
            )
        if side not in ("yes", "no"):
            raise ValueError("side must be 'yes' or 'no' (lowercase)")
        if count <= 0:
            raise ValueError("count must be a positive integer")

        import requests

        path = "/trade-api/v2/portfolio/orders"
        body = {
            "ticker": ticker, "action": "buy", "side": side,
            "count": int(count), "type": "limit", "yes_price": int(yes_price),
        }
        resp = requests.post(
            f"{KALSHI_BASE}/portfolio/orders",
            headers={**self._sign("POST", path),
                     "Content-Type": "application/json"},
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        time.sleep(RATE_LIMIT_SLEEP)
        return resp.json()


if __name__ == "__main__":
    print(__doc__)
    print("This module is a library. It places no orders without a code-level "
          "opt-in, and the analyzer never imports it.")
