# 02 — Combined stack test

> **Source:** Chapter 2 (Putting It All Together) · `ch02.md:325`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Using the unusualwhales MCP, look at SPY's current options flow. Is the smart money bullish or bearish right now? Give me a one-word answer (BULLISH or BEARISH) and a confidence as a percentage. Then write a small Python file `combined_test.py` that uses alpaca-py to print my paper account status and cash balance, and run it for me."
```

## Expected output schema

A one-word directional call on SPY (`BULLISH` or `BEARISH`) plus a confidence
percentage, and a file `combined_test.py` written to your project directory and
executed, printing `Status: ACTIVE` and `Cash: $100,000.00`.

## How deterministic code consumes it

It is the whole workflow of the book in one paste: live flow through MCP, Claude
writing the Python, Claude running it, you reading the output. The file it writes
stays in your project directory and re-runs from a normal shell.

## Offline behaviour in this repo

The MCP half is not reproducible offline (see prompt 01). The Alpaca half is:
`python setup/test_alpaca.py` prints exactly the account status and cash balance
this prompt asks for, against the deterministic offline stub, with no keys.

## Cost notes

One Anthropic call plus one UW MCP dispatch. Cents.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
