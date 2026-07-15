"""THE OFFLINE SWITCH — deterministic stand-ins for every keyed/paid surface.

Every artifact in *Use Claude to Build an AI Trading Bot* touches something you
have to pay for: the Anthropic API, Unusual Whales (a $50/week floor), an Alpaca
account, a Kalshi private key. The book is honest about that. A companion repo
that only runs if you hold all four would be useless to almost everyone who buys
the book, so this module inverts the default:

    **Offline is ON unless you turn it off.** No key, no network, no account,
    no `.env` — `make demo` still runs, and every number you see is computed by
    the repo's real code against committed synthetic fixtures.

What that means concretely
--------------------------
* `get_anthropic()`, `get_trading_client()`, `get_data_client()`, `get_yfinance()`
  and `http_get_json()` hand back **deterministic offline stubs** by default.
  Each stub answers the exact request/response schema the book's code expects.
* Set ``CTB_OFFLINE=0`` (plus real keys) to swap in the live clients. That is a
  *read/analysis* upgrade only — it does **not** enable live trading.
* Live trading is a separate, deliberately awkward, **code-level** opt-in:
  ``set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")``. No environment
  variable and no CLI flag can flip it. See `is_live_mode()`.

Fixture dating
--------------
The bundled UW/Gamma fixtures are a frozen synthetic trading day
(``FIXTURE_AS_OF``). The stubs shift their timestamps forward so the data always
looks like *today* — otherwise every ``max_dte`` filter in the book would see a
negative days-to-expiry and quietly drop everything.

Everything here is illustrative synthetic sample data. It is not real market
data and does not predict real results.
"""

from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from utils import fixture

__all__ = [
    "FIXTURE_AS_OF",
    "offline_enabled",
    "announce",
    "is_live_mode",
    "set_live_mode",
    "LiveModeError",
    "get_anthropic",
    "get_trading_client",
    "get_data_client",
    "get_yfinance",
    "http_get_json",
    "MarketOrderRequest",
    "TakeProfitRequest",
    "StopLossRequest",
    "TrailingStopOrderRequest",
    "StockLatestQuoteRequest",
    "OrderSide",
    "TimeInForce",
    "OrderClass",
]

#: The synthetic trading day the bundled UW / Polymarket fixtures were minted on.
#: Stub responses are shifted from this date onto the current date at read time.
FIXTURE_AS_OF = date(2026, 5, 12)

_OFFLINE_ENV = "CTB_OFFLINE"
_ANNOUNCED = False


# --------------------------------------------------------------------------- #
#  The switch
# --------------------------------------------------------------------------- #
def offline_enabled() -> bool:
    """True unless ``CTB_OFFLINE`` is explicitly set to 0/false/no.

    Offline is the default *on purpose*: the headline claim of this repo is that
    it runs with zero keys and zero network. Turning it off is an opt-in upgrade
    that needs real credentials — and it still will not place a live trade.
    """
    raw = os.getenv(_OFFLINE_ENV, "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def announce(stream=sys.stderr) -> None:
    """Say once, loudly, that the numbers you are about to read are synthetic."""
    global _ANNOUNCED
    if _ANNOUNCED or not offline_enabled():
        return
    _ANNOUNCED = True
    print(
        "[offline] No API keys required. Serving deterministic synthetic "
        "fixtures for Anthropic / Unusual Whales / Alpaca / yfinance / "
        "Polymarket Gamma.\n"
        "[offline] Results are illustrative mechanics on synthetic sample "
        "data — not real or historical performance.\n"
        "[offline] Set CTB_OFFLINE=0 (with real keys) to use the live read "
        "APIs. Live *trading* needs a separate code-level opt-in.",
        file=stream,
    )


class LiveModeError(RuntimeError):
    """Raised when something tries to reach a live-money path without the opt-in."""


_LIVE_MODE = False
_LIVE_CONFIRM = "I_HAVE_REVIEWED_THIS"


def is_live_mode() -> bool:
    """True only after an in-process `set_live_mode(True, confirm=...)` call."""
    return _LIVE_MODE


def set_live_mode(enabled: bool, confirm: str | None = None) -> bool:
    """Enable real-money trading. Deliberately awkward. Read this first.

    There is no environment variable and no command-line flag that turns this on,
    and that is the point: an env var is one stray `export` away from trading your
    savings, and a CLI flag is one stray shell-history arrow-up away from the same.
    You have to edit code and pass the confirmation string:

        from utils.offline import set_live_mode
        set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")

    Before you do, you should have finished the ch10 90-day ladder: 30 days of
    paper trading that clears the Phase-1 gate, then $500 of real money, then the
    capital ladder. Not before.

    Raises:
        LiveModeError: if `confirm` is missing or wrong, if offline mode is still
            on, or if the Alpaca credentials are absent.
    """
    global _LIVE_MODE
    if not enabled:
        _LIVE_MODE = False
        return False
    if confirm != _LIVE_CONFIRM:
        raise LiveModeError(
            "Live mode refused: pass confirm=\"I_HAVE_REVIEWED_THIS\" explicitly. "
            "No env var and no CLI flag can enable live trading."
        )
    if offline_enabled():
        raise LiveModeError(
            "Live mode refused: offline mode is still on. Live trading needs real "
            "market data too — set CTB_OFFLINE=0 and supply real credentials."
        )
    if not (os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY")):
        raise LiveModeError(
            "Live mode refused: ALPACA_API_KEY / ALPACA_SECRET_KEY are not set."
        )
    print(
        "\n" + "!" * 72 + "\n"
        "!! LIVE TRADING ENABLED. Orders will be placed with REAL MONEY.\n"
        "!! Trading carries substantial risk of loss. This is educational\n"
        "!! software and not financial advice. See DISCLAIMER.md.\n"
        + "!" * 72 + "\n",
        file=sys.stderr,
    )
    _LIVE_MODE = True
    return True


def _paper() -> bool:
    """Alpaca `paper=` value. True unless the code-level live opt-in ran."""
    return not _LIVE_MODE


# --------------------------------------------------------------------------- #
#  Alpaca request/enum shims — real classes when alpaca-py is installed
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - exercised by whichever extra is installed
    from alpaca.data.requests import StockLatestQuoteRequest
    from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
    from alpaca.trading.requests import (
        MarketOrderRequest,
        StopLossRequest,
        TakeProfitRequest,
        TrailingStopOrderRequest,
    )

    _HAVE_ALPACA = True
except ImportError:  # alpaca-py is the `broker` extra, not a core dependency.
    _HAVE_ALPACA = False

    class _StrEnum(str):
        pass

    class OrderSide(_StrEnum):
        BUY = "buy"
        SELL = "sell"

    class TimeInForce(_StrEnum):
        DAY = "day"
        GTC = "gtc"

    class OrderClass(_StrEnum):
        SIMPLE = "simple"
        BRACKET = "bracket"
        OCO = "oco"
        OTO = "oto"

    OrderSide.BUY = OrderSide("buy")
    OrderSide.SELL = OrderSide("sell")
    TimeInForce.DAY = TimeInForce("day")
    TimeInForce.GTC = TimeInForce("gtc")
    OrderClass.SIMPLE = OrderClass("simple")
    OrderClass.BRACKET = OrderClass("bracket")

    @dataclass
    class TakeProfitRequest:  # type: ignore[no-redef]
        limit_price: float

    @dataclass
    class StopLossRequest:  # type: ignore[no-redef]
        stop_price: float
        limit_price: float | None = None

    @dataclass
    class MarketOrderRequest:  # type: ignore[no-redef]
        symbol: str
        qty: float
        side: Any
        time_in_force: Any = TimeInForce.DAY
        order_class: Any = None
        take_profit: Any = None
        stop_loss: Any = None

    @dataclass
    class TrailingStopOrderRequest:  # type: ignore[no-redef]
        symbol: str
        qty: float
        side: Any
        trail_percent: float
        time_in_force: Any = TimeInForce.GTC

    @dataclass
    class StockLatestQuoteRequest:  # type: ignore[no-redef]
        symbol_or_symbols: Any


# --------------------------------------------------------------------------- #
#  Fixture loading
# --------------------------------------------------------------------------- #
_CACHE: dict[str, Any] = {}


def _load(name: str) -> Any:
    if name not in _CACHE:
        _CACHE[name] = json.loads(fixture(name).read_text())
    return _CACHE[name]


def _shift() -> timedelta:
    """Offset that moves the frozen fixture day onto today."""
    return date.today() - FIXTURE_AS_OF


def _shift_iso(value: str, delta: timedelta) -> str:
    """Shift an ISO date or datetime string by `delta`, preserving its shape."""
    if not value:
        return value
    if "T" in value:
        head, sep, tail = value.partition("T")
        return (date.fromisoformat(head) + delta).isoformat() + sep + tail
    return (date.fromisoformat(value) + delta).isoformat()


# --------------------------------------------------------------------------- #
#  Offline Anthropic
# --------------------------------------------------------------------------- #
@dataclass
class _TextBlock:
    text: str


@dataclass
class _Message:
    content: list


class _OfflineMessages:
    """Answers the exact JSON schemas the book's prompts ask for."""

    def create(self, *, model: str = "", max_tokens: int = 0, messages=None, **_kw):
        announce()
        prompt = ""
        for m in messages or []:
            content = m.get("content", "")
            prompt += content if isinstance(content, str) else json.dumps(content)
        return _Message(content=[_TextBlock(text=self._route(prompt))])

    # -- routing -----------------------------------------------------------
    def _route(self, prompt: str) -> str:
        if "You are the ANALYST agent" in prompt:
            return json.dumps(_strip(_load("claude_responses/multi_agent.json")["analyst"]))
        if "You are the RISK MANAGER agent" in prompt:
            return json.dumps(_strip(_load("claude_responses/multi_agent.json")["risk"]))
        if "You are the MONITOR agent" in prompt:
            return json.dumps(_strip(_load("claude_responses/multi_agent.json")["monitor"]))
        if "Filter this list to ONLY contracts" in prompt:
            return self._filter_markets(prompt)
        if "PREDICTION MARKET ANALYSIS" in prompt:
            return self._estimate(prompt)
        if "URGENT FLOW EVENT" in prompt:
            return self._flow(prompt, "claude_responses/flow_trader.json")
        if "unusual options flow event" in prompt:
            return self._flow(prompt, "claude_responses/screener.json")
        if "Say OK" in prompt:
            return "OK"
        return (
            "This is the deterministic offline Claude stub. It has no live market "
            "data and no model behind it — it replays committed synthetic fixtures "
            "so the book's code paths run with zero API keys."
        )

    def _flow(self, prompt: str, source: str) -> str:
        table = _load(source)
        ticker = _find_ticker(prompt, table)
        entry = dict(table.get(ticker, table["_default"]))
        fenced = entry.pop("_fenced", False)
        entry["ticker"] = ticker
        body = json.dumps(_strip(entry), indent=2)
        # ch04.md:159-165: Claude sometimes wraps its JSON in a markdown fence.
        # One fixture row does exactly that so the fallback parser is exercised.
        return f"Here you go:\n\n```json\n{body}\n```\n" if fenced else body

    def _filter_markets(self, prompt: str) -> str:
        markets = _extract_markets(prompt)
        drop = ("rain", "weather", "storm", "pop star", "album", "celebrity")
        kept = [m for m in markets
                if not any(w in str(m.get("question", "")).lower() for w in drop)]
        return json.dumps(kept)

    def _estimate(self, prompt: str) -> str:
        table = _load("claude_responses/prediction.json")
        question = ""
        for line in prompt.splitlines():
            if line.startswith("Question: "):
                question = line[len("Question: "):].strip()
                break
        entry = dict(table.get(question, table["_default"]))
        entry["question"] = question
        market_price = 0.5
        for line in prompt.splitlines():
            if line.startswith("Current market price: "):
                try:
                    market_price = float(line.split()[3])
                except (IndexError, ValueError):
                    market_price = 0.5
                break
        entry["market_price"] = market_price
        return json.dumps(_strip(entry), indent=2)


def _strip(obj):
    """Drop fixture bookkeeping keys (`_note`, `_fenced`, ...) from a response."""
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def _find_ticker(prompt: str, table: dict) -> str:
    for key in table:
        if key.startswith("_"):
            continue
        if f'"ticker": "{key}"' in prompt or f"on {key}:" in prompt:
            return key
    return "_default"


def _extract_markets(prompt: str) -> list:
    start = prompt.find("[")
    end = prompt.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(prompt[start:end + 1])
    except json.JSONDecodeError:
        return []


class OfflineAnthropic:
    """Drop-in for `anthropic.Anthropic()` — zero keys, zero network, seeded."""

    def __init__(self, *_a, **_kw):
        self.messages = _OfflineMessages()


def get_anthropic():
    """The Anthropic client — real when live, deterministic stub when offline."""
    if offline_enabled():
        announce()
        return OfflineAnthropic()
    from anthropic import Anthropic  # `llm` extra

    return Anthropic()


# --------------------------------------------------------------------------- #
#  Offline Alpaca
# --------------------------------------------------------------------------- #
@dataclass
class _Account:
    status: str
    cash: str
    portfolio_value: str
    buying_power: str
    equity: str


@dataclass
class _Position:
    symbol: str
    qty: str
    avg_entry_price: str
    current_price: str
    market_value: str
    unrealized_pl: str
    unrealized_plpc: str
    side: str


@dataclass
class _Order:
    id: str
    symbol: str
    qty: float
    side: Any
    status: str
    order_class: str
    filled_avg_price: float | None = None


@dataclass
class _Quote:
    bid_price: float
    ask_price: float


class OfflineTradingClient:
    """Drop-in for `alpaca.trading.client.TradingClient` on synthetic state.

    Paper by construction: this client cannot reach a broker at all. Orders are
    recorded in memory and reflected back into the position book so a demo run
    reads coherently end to end.
    """

    def __init__(self, *_a, paper: bool = True, positions: list | None = None, **_kw):
        if not paper:
            raise LiveModeError(
                "The offline Alpaca stub cannot run in live mode. Set CTB_OFFLINE=0 "
                "and install the `broker` extra to trade against the real API."
            )
        state = _load("alpaca_state.json")
        self._account = dict(state["account"])
        # `positions=[]` gives a clean-slate $100K paper account — which is what
        # ch09's worked examples assume when they size NVDA at 72 shares.
        source = state["positions"] if positions is None else positions
        self._positions = [dict(p) for p in source]
        self.orders: list[_Order] = []
        self._seq = 0

    # -- account -----------------------------------------------------------
    def get_account(self) -> _Account:
        a = self._account
        return _Account(
            status=a["status"],
            cash=str(a["cash"]),
            portfolio_value=str(a["portfolio_value"]),
            buying_power=str(a["buying_power"]),
            equity=str(a["equity"]),
        )

    def get_all_positions(self) -> list[_Position]:
        return [
            _Position(
                symbol=p["symbol"], qty=str(p["qty"]),
                avg_entry_price=str(p["avg_entry_price"]),
                current_price=str(p["current_price"]),
                market_value=str(p["market_value"]),
                unrealized_pl=str(p["unrealized_pl"]),
                unrealized_plpc=str(p["unrealized_plpc"]),
                side=p["side"],
            )
            for p in self._positions
        ]

    # -- orders ------------------------------------------------------------
    def submit_order(self, order) -> _Order:
        self._seq += 1
        side = getattr(order, "side", OrderSide.BUY)
        side_str = getattr(side, "value", str(side))
        klass = getattr(order, "order_class", None)
        klass_str = getattr(klass, "value", str(klass)) if klass else "simple"
        qty = float(getattr(order, "qty", 0) or 0)
        symbol = getattr(order, "symbol", "?")
        price = self._price(symbol)
        result = _Order(
            id=f"offline-{self._seq:04d}", symbol=symbol, qty=qty, side=side_str,
            status="accepted", order_class=klass_str, filled_avg_price=price,
        )
        self.orders.append(result)
        self._apply_fill(symbol, qty, side_str, price)
        return result

    def close_position(self, symbol: str) -> _Order:
        self._seq += 1
        self._positions = [p for p in self._positions if p["symbol"] != symbol]
        return _Order(id=f"offline-{self._seq:04d}", symbol=symbol, qty=0,
                      side="sell", status="accepted", order_class="simple")

    def cancel_orders(self):
        return []

    # -- internals ---------------------------------------------------------
    def _price(self, symbol: str) -> float:
        q = _load("alpaca_state.json")["quotes"].get(symbol)
        if not q or not q["ask_price"] or not q["bid_price"]:
            return 0.0
        return round((q["ask_price"] + q["bid_price"]) / 2, 2)

    def _apply_fill(self, symbol, qty, side_str, price):
        if qty <= 0 or price <= 0:
            return
        signed = int(qty) if side_str == "buy" else -int(qty)
        for p in self._positions:
            if p["symbol"] == symbol:
                p["qty"] = int(p["qty"]) + signed
                p["market_value"] = round(p["qty"] * price, 2)
                if p["qty"] == 0:
                    self._positions.remove(p)
                return
        self._positions.append({
            "symbol": symbol, "qty": signed, "avg_entry_price": price,
            "current_price": price, "market_value": round(signed * price, 2),
            "unrealized_pl": 0.0, "unrealized_plpc": 0.0,
            "side": "long" if signed > 0 else "short",
        })


class OfflineDataClient:
    """Drop-in for `StockHistoricalDataClient` — one synthetic quote per symbol."""

    def __init__(self, *_a, **_kw):
        self._quotes = _load("alpaca_state.json")["quotes"]

    def get_stock_latest_quote(self, request) -> dict:
        symbols = getattr(request, "symbol_or_symbols", None)
        if isinstance(symbols, str):
            symbols = [symbols]
        out = {}
        for s in symbols or []:
            q = self._quotes.get(s, {"bid_price": 0.0, "ask_price": 0.0})
            out[s] = _Quote(bid_price=q["bid_price"], ask_price=q["ask_price"])
        return out


def get_trading_client():
    """Alpaca trading client. **Paper unless `set_live_mode()` ran.**"""
    if offline_enabled():
        announce()
        return OfflineTradingClient(paper=True)
    from alpaca.trading.client import TradingClient  # `broker` extra

    return TradingClient(
        os.getenv("ALPACA_API_KEY"),
        os.getenv("ALPACA_SECRET_KEY"),
        paper=_paper(),
    )


def get_data_client():
    """Alpaca market-data client (quotes)."""
    if offline_enabled():
        announce()
        return OfflineDataClient()
    from alpaca.data.historical import StockHistoricalDataClient  # `broker` extra

    return StockHistoricalDataClient(
        os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
    )


# --------------------------------------------------------------------------- #
#  Offline yfinance
# --------------------------------------------------------------------------- #
class _OfflineTicker:
    """Drop-in for `yfinance.Ticker` covering the three surfaces ch06/ch09 use:
    `.info['sector']`, `.calendar['Earnings Date']`, and `.history(...)`."""

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self._meta = _load("yfinance_sectors.json")

    @property
    def info(self) -> dict:
        return {"sector": self._meta["sectors"].get(self.symbol, "Unknown")}

    @property
    def calendar(self) -> dict:
        days = self._meta["earnings_days_ahead"].get(self.symbol)
        if days is None:
            return {}
        return {"Earnings Date": [date.today() + timedelta(days=int(days))]}

    def history(self, start=None, end=None, period=None, auto_adjust=False, **_kw):
        import pandas as pd

        series = _load("yfinance_prices.json").get(self.symbol)
        if series is None:
            return pd.DataFrame()  # delisted / no coverage — ch06's skip path
        idx = pd.bdate_range(start=series["start"], periods=len(series["closes"]))
        frame = pd.DataFrame(
            {"Close": series["closes"],
             "Volume": _synthetic_volume(self.symbol, len(series["closes"]))},
            index=idx,
        )
        if period is not None:
            days = {"1mo": 22, "3mo": 66, "6mo": 132}.get(period, 22)
            return frame.iloc[-days:]
        if start is not None:
            frame = frame[frame.index >= pd.Timestamp(start)]
        if end is not None:
            frame = frame[frame.index < pd.Timestamp(end)]
        return frame


def _synthetic_volume(symbol: str, n: int) -> list:
    meta = _load("yfinance_sectors.json")
    base = meta["avg_daily_volume"].get(symbol, 5_000_000)
    rng = random.Random(f"vol:{symbol}")
    return [int(base * rng.uniform(0.75, 1.25)) for _ in range(n)]


class OfflineYFinance:
    Ticker = _OfflineTicker


def get_yfinance():
    """The yfinance module — real when live, deterministic stub when offline."""
    if offline_enabled():
        announce()
        return OfflineYFinance
    import yfinance as yf  # `data` extra

    return yf


# --------------------------------------------------------------------------- #
#  Offline HTTP — Unusual Whales REST + Polymarket Gamma
# --------------------------------------------------------------------------- #
def http_get_json(url: str, headers: dict | None = None,
                  params: dict | None = None, timeout: int = 15) -> Any:
    """GET a JSON document. Offline, this never opens a socket.

    Offline it routes the URL to the matching committed fixture and applies the
    query params the real service would have applied server-side (`min_premium`,
    `min_volume_oi_ratio`, `max_dte`, `newer_than`, `limit`), so the book's
    client-side filters still have something left to do — and are provably
    exercised, because the fixtures contain rows that fail each one.
    """
    params = params or {}
    if not offline_enabled():
        import requests

        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    announce()
    if "/option-trades/flow-alerts" in url:
        return {"data": _offline_flow_alerts(params)}
    if "/option-trades/full-tape/" in url:
        raise RuntimeError(
            "The offline stub does not serve UW full-tape. The backtester reads a "
            "local CSV by design (ch06.md:99-122); populate it from the UW Data "
            "Shop or a day-by-day full-tape loop, or use the bundled synthetic "
            "fixtures/historical_flow.csv."
        )
    if "/darkpool/" in url:
        ticker = url.rstrip("/").rsplit("/", 1)[-1].upper()
        return {"data": _offline_darkpool(ticker)}
    if "gamma-api.polymarket.com" in url:
        return _offline_gamma(params)
    raise RuntimeError(f"No offline fixture is wired for {url!r}.")


def _offline_flow_alerts(params: dict) -> list:
    delta = _shift()
    today = date.today()
    raw = _load("uw_flow_alerts.json")["data"]
    min_premium = float(params.get("min_premium", 0) or 0)
    min_ratio = float(params.get("min_volume_oi_ratio", 0) or 0)
    max_dte = params.get("max_dte")
    newer_than = params.get("newer_than")

    out = []
    for item in raw:
        item = dict(item)
        item["created_at"] = _shift_iso(item["created_at"], delta)
        item["expiry"] = _shift_iso(item["expiry"], delta)
        if float(item["total_premium"]) < min_premium:
            continue
        if float(item["volume_oi_ratio"]) < min_ratio:
            continue
        if max_dte is not None:
            dte = (date.fromisoformat(item["expiry"]) - today).days
            if dte > int(max_dte):
                continue
        if newer_than is not None:
            created_ms = int(
                datetime.fromisoformat(item["created_at"]).timestamp() * 1000
            )
            if created_ms <= int(newer_than):
                continue
        out.append(item)
    return out


def _offline_darkpool(ticker: str) -> list:
    if ticker != "COIN":
        return []
    delta = _shift()
    prints = []
    for p in _load("uw_darkpool_COIN.json")["data"]:
        p = dict(p)
        p["executed_at"] = _shift_iso(p["executed_at"], delta)
        prints.append(p)
    return prints


def _offline_gamma(params: dict) -> list:
    delta = _shift()
    limit = int(params.get("limit", 100) or 100)
    out = []
    for m in _load("gamma_markets.json"):
        m = dict(m)
        m["endDate"] = _shift_iso(m["endDate"], delta)
        out.append(m)
    return out[:limit]
