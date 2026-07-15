# Chapter 2 lab: setup & connections

Four things have to be live before any strategy code makes sense: Python, the Claude
API, Unusual Whales, and Alpaca. Chapter 2 gates the whole book on one script that
proves all four, because most people who want an AI trading bot never get past setup.

## The prompt
Paste [`prompts/01_mcp_connection_test.md`](../../prompts/01_mcp_connection_test.md)
and [`prompts/02_combined_stack_test.md`](../../prompts/02_combined_stack_test.md)
into Claude Code.

## What you get
[`setup/verify_setup.py`](../../setup/verify_setup.py), plus `test_claude.py` and
`test_alpaca.py` for the individual connections.

## Run the gate
```bash
python setup/verify_setup.py
```
```
=== SETUP VERIFICATION ===
  [PASS] Python version: Python 3.11+
  [PASS] Claude API: OK (offline stub)
  [PASS] Unusual Whales MCP: offline UW data layer OK (13 flow alerts from fixtures) — live MCP registration NOT checked in offline mode
  [PASS] Alpaca paper trading: Status: ACTIVE, Cash: $100,000.00 (offline stub)
Result: 4/4 checks passed
```

## The one honest hedge
Read the Unusual Whales line: "live MCP registration NOT checked in offline mode."
That is deliberate. Offline there is no Claude Code session to interrogate, so the
check verifies the UW REST data layer the saved scripts actually use and says so,
rather than faking a green. Set `CTB_OFFLINE=0` with real keys and it shells out to
`claude mcp list` exactly as the book prints.

---
Reference: [docs/01-setup.md](../../docs/01-setup.md)
