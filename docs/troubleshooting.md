# Troubleshooting

Appendix A's error tables, plus the ones specific to this repo.

## This repo

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'utils'` | you ran a script from inside its own directory | run from the repo root: `python screener/screener.py` |
| `ModuleNotFoundError: No module named 'anthropic'` / `'alpaca'` / `'yfinance'` | those are **optional extras**, not core deps | you don't need them offline. For live: `pip install -e ".[live]"` |
| `[skip] matplotlib not installed — no fan chart` | matplotlib is the `viz` extra | `pip install -e ".[viz]"`. The backtest still runs and still writes `report.json`. |
| `LiveModeError: live mode is off` | you tried to place a real order | **that is the point.** See [08-going-live.md](08-going-live.md). |
| `Kalshi has no offline fixture in this repo` | `get_kalshi_markets()` offline | deliberate. Inventing event contracts would be the hallucination ch07 warns about. Set `CTB_OFFLINE=0` with real keys. The **signing path is fully tested offline**. |
| The backtest says `INSUFFICIENT DATA` | fewer than 30 valid trades | widen the CSV window. The fix is more data, not more parameter-tuning. |
| The screener's watchlist is empty | everything scored below 65, or ch03's filters bit | that is a normal day. Check the `BLOCKED` / `ADJUSTED` lines. |

## Claude API (Anthropic)

| Error | Cause | Fix |
|---|---|---|
| `AuthenticationError` | wrong or expired key | regenerate at console.anthropic.com. **The most common mistake is an extra space before or after the key.** |
| `RateLimitError` | over your tier's RPM | Tier 1 starts around **50 RPM**. Add `time.sleep(2)` between calls. In a bot, this usually means **your filter is too loose**. Tighten it rather than slowing the poll. |
| `OverloadedError` | Anthropic's servers are busy | retry with exponential backoff: `time.sleep(2 ** attempt)` |
| `InvalidRequestError` | prompt too long | reduce the content or lower `max_tokens` |
| `BadRequestError: model 'claude-sonnet-4-20250514' is deprecated` | an old model alias | use `claude-sonnet-4-6`. The old one **retires June 15, 2026** and appears nowhere in this repo; a test enforces it. |
| `JSONDecodeError` | Claude wrapped its JSON in a markdown fence | every parser in this repo handles it. If you hit it in your own code, split on ``` and strip the `json` tag. |

**The MCP trap.** Do not use `client.messages.create(...)` with a prompt that says
*"Using Unusual Whales MCP, …"* and expect Claude to dispatch the call. **That pattern
does not work.** The vanilla Messages API has no MCP connection, so Claude returns
**hallucinated JSON**. The two correct paths are (a) Claude Code with `claude mcp add`,
or (b) the Anthropic MCP-connector beta. See [architecture.md](architecture.md).

## Claude Code

| Symptom | Fix |
|---|---|
| `claude: command not found` | `brew install --cask claude-code`, or download from claude.com/download |
| MCP server not found | `claude mcp list` is the **source of truth**. If it isn't listed, Claude Code cannot dispatch to it, whatever your config files say. |
| Free tier won't run the CLI | **Pro is $20/month minimum.** The free web/mobile/desktop chat tier does **not** include the Claude Code CLI. |

## Unusual Whales

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | wrong or expired key | re-copy from account settings. Watch for trailing whitespace. |
| `403 Forbidden` | **wrong tier** | Free Shamu / Buffet's Buffet web tiers do **NOT** include API access. **Trial ($50/week) is the floor.** |
| `429` | rate limited | 300 req/min on Trial. The screener never hits this with one run. |
| No rows on a busy day | response shape drifted | print `resp.json()` and confirm the documented fields: `ticker`, `total_premium`, `volume_oi_ratio`, `has_sweep`, `has_floor`, `type`, `expiry` |
| `Connection refused` from MCP | not registered | re-run `claude mcp add --transport http unusualwhales …` |

**There is no 180-day range query.** Historical flow comes from the UW Data Shop, or a
day-by-day loop over `GET /api/option-trades/full-tape/{date}`: **one trading day per
call**.

**Do not `pip install unusual-whales-mcp`.** That PyPI package is a **community fork**,
not the official UW MCP server. The official one is Node-based and registered with
`claude mcp add`.

## Alpaca

| Error | Cause | Fix |
|---|---|---|
| `Forbidden (403)` | paper vs live keys mixed, **or** a DAY order outside market hours | they are **different key pairs**. Don't mix them. |
| `Insufficient buying power` | position exceeds available cash | check `account.buying_power` before ordering |
| `Asset not tradable` | wrong, delisted, or unsupported symbol | verify at alpaca.markets |
| `No module named 'alpaca'` | you installed `alpaca`, not `alpaca-py` | `pip uninstall alpaca && pip install alpaca-py`. The **package** is `alpaca-py`; the **import** is `from alpaca.trading.client import TradingClient`. |
| A bracket order shows only the parent | `order_class` dropped, or wrong TIF | `time_in_force` must be **`DAY` or `GTC`**. Print `result.order_class`; it should say `"bracket"`. |
| Quote returns `(0, 0)` | pre-market/after-hours, or your data tier | **that `(0,0)` is intentional**: skip the trade rather than price it at $0. |

**Pin `alpaca-py>=0.43.0,<0.50.0`.** If you've seen older guides pinning `>=0.13.0`,
that is **30+ versions stale**.

## Polymarket

| Error | Cause | Fix |
|---|---|---|
| Every probability comes out as `0.5` | you read `current_price` | **there is no `current_price` field.** Use `outcomePrices[0]`, cast from string. |
| `outcomePrices` won't parse | it's a JSON-encoded **string** sometimes and a real **array** other times | use `parse_outcome_prices()`; it handles both |
| Booleans rejected | Gamma wants strings | `{"active": "true", "closed": "false"}`, **not** Python booleans |
| `KeyError: 'data'` | Gamma returns a JSON **array** directly | there is no `{"data": [...]}` wrapper |
| "This endpoint doesn't return what the docs say" | you're on the wrong surface | **Gamma** for discovery, **CLOB** for orderbook and trading. Mixing them is the #1 error. |
| `Rate limited` | too fast | add a 1-second delay between calls |

## Kalshi

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | signature doesn't validate | check the payload format: `{ts}{METHOD}{path}` with **no separator**. Check the timestamp is current (**milliseconds**). |
| `422 Unprocessable Entity` | bad order params | `side` must be `yes` or `no` (**lowercase**); `count` a positive integer |
| `403 Forbidden` | account not verified | complete identity verification first |
| An old guide's `kalshi_login()` returns 401 | obsolete | that flow is gone. The current one is **RSA-PSS signed requests**. |

Rate limit ≈ 10 requests/second → `time.sleep(0.15)`.

## Windows

| Symptom | Fix |
|---|---|
| `python` not found after install | you missed the **"Add Python to PATH"** checkbox. It is not checked by default, and you will waste an hour. Reinstall and check it. |
| `running scripts is disabled on this system` | run PowerShell as Administrator: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`, then reopen |
| `SSL Certificate Error` | `pip install certifi` |
| `ModuleNotFoundError` in WSL but not PowerShell (or vice versa) | you have **two Pythons** and they don't share packages. Pick one and stick with it. |
| Mysterious syntax errors after pasting code | invisible carriage returns. Use VS Code or Notepad++, not Windows Notepad. |

## macOS

| Symptom | Fix |
|---|---|
| `python3 --version` shows 3.9 after installing 3.12 | Homebrew's Python isn't on your PATH. `brew link python@3.12`, or call it explicitly: `python3.12 -m venv venv` |

## The debug loop

**Paste the error, ask Claude to fix it, apply the fix, re-run.** That's it. You do not
need to understand every line of Python to run these bots. You need three checks:

1. **Does it print what you asked for when run?**
2. **Did Claude name the files you expected?**
3. **Did Claude flag anything risky?** (Claude Code is loud about API keys and file
   deletions. "I need your `ANTHROPIC_API_KEY`" is normal. Add it to `.env`. **Never
   paste a key into the conversation itself**; it lives in your transcript forever.)

---

*Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
