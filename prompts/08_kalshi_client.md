# 08 — Build the Kalshi RSA-PSS client

> **Source:** Chapter 7 (Kalshi: The Regulated Alternative) · `ch07.md:490`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Write me `prediction/kalshi_client.py`. It should:

1. Load `KALSHI_KEY_ID` and `KALSHI_PRIVATE_KEY_PATH` from `.env`. Use `cryptography` to load the private key from the PEM file.
2. Implement a `_sign(method, path)` helper that returns the three headers (`KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-SIGNATURE`, `KALSHI-ACCESS-TIMESTAMP`). Sign `{timestamp_ms}{METHOD}{path}` with RSA-PSS, SHA-256, MGF1-SHA256, salt-length=digest-length.
3. Implement `get_kalshi_markets(status='open', limit=100)` that calls `GET /markets`, returns `markets` array.
4. Implement `place_kalshi_order(ticker, side, count, yes_price)` that POSTs to `/portfolio/orders`.
5. Reference: https://docs.kalshi.com/getting_started/api_keys

Save as `prediction/kalshi_client.py`."
```

## Expected output schema

No model output. The artifact is `prediction/kalshi_client.py`: `_sign(method, path)`
returning the three headers, `get_kalshi_markets(status, limit)`, and
`place_kalshi_order(ticker, side, count, yes_price)`.

## How deterministic code consumes it

The signed payload is `{timestamp_ms}{HTTP_METHOD}{request_path}` concatenated with
**no separator**, signed RSA-PSS / SHA-256 / MGF1-SHA256 / salt length = digest
length. Headers: `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-SIGNATURE` (base64),
`KALSHI-ACCESS-TIMESTAMP` (ms).

`place_kalshi_order()` spends real money, so in this repo it **refuses to run**
unless you have edited code and called
`set_live_mode(True, confirm="I_HAVE_REVIEWED_THIS")`. No env var and no CLI flag
enables it. `prediction_analyzer.py` does not import this module.

## Offline behaviour in this repo

The **signing path is fully tested offline**: `tests/test_kalshi.py` generates a
throwaway RSA keypair in-process, signs a known payload, and verifies the
signature and all three headers. No PEM file is ever committed to this repo.

`get_kalshi_markets()` raises offline rather than inventing event contracts. A
stub that made up markets would be the hallucination the chapter keeps warning
about.

## Cost notes

$0 for API access after KYC. Minimum deposit $1. Rate limit is roughly 10 requests
per second; the client sleeps 0.15s between calls.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
