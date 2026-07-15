# The 12 prompts

The book's delivery mechanism is not "type this code." It is:

> **You paste a prompt into Claude Code. Claude writes the Python. Claude runs it.
> You read the output.**

That is Appendix C's entire thesis, and it is why the book claims you can build
everything in it without knowing Python. So the prompts are **first-class artifacts**,
not commentary, and they ship here **verbatim**, extracted programmatically from the
manuscript so no paraphrase can creep in.

Each doc carries the prompt itself, the output schema it produces, how the deterministic
code consumes it, how this repo answers it offline, and what it costs.

| # | Prompt | Chapter | Produces |
|---|---|---|---|
| 01 | [MCP connection test](../prompts/01_mcp_connection_test.md) | ch02.md:227 | one live ticker (a liveness probe) |
| 02 | [Combined stack test](../prompts/02_combined_stack_test.md) | ch02.md:325 | SPY direction + `combined_test.py`, written and run |
| 03 | [The screener](../prompts/03_screener.md) | ch04.md:31 | `screener/screener.py` |
| 04 | [The flow trader](../prompts/04_flow_trader.md) | ch05.md:59 | `flow_trader/flow_trader.py` + `check_positions.py` |
| 05 | [The backtester](../prompts/05_backtester.md) | ch06.md:63 | `backtester/backtester.py` (**no LLM in it**) |
| 06 | [Walk-forward validation](../prompts/06_walk_forward.md) | ch06.md:607 | the 3-window add-on |
| 07 | [The prediction analyzer](../prompts/07_prediction_analyzer.md) | ch07.md:57 | `prediction/prediction_analyzer.py` (**read-only**) |
| 08 | [The Kalshi client](../prompts/08_kalshi_client.md) | ch07.md:490 | `prediction/kalshi_client.py` (RSA-PSS) |
| 09 | [Live-data estimates](../prompts/09_live_data_estimates.md) | ch07.md:420 | `prediction/estimates.json` with **cited sources** |
| 10 | [The 4-agent system](../prompts/10_multi_agent.md) | ch08.md:43 | `multi_agent/multi_agent.py` |
| 11 | [The risk module](../prompts/11_risk_manager.md) | ch09.md:84 | `risk/risk_manager.py` (**no Claude calls**) |
| 12 | [Tracking infrastructure](../prompts/12_tracking_infra.md) | ch10.md:31 | `tracking/calculate_metrics.py` + `phase1_assessment.py` |

## The one instruction that appears in five of them

> "Do NOT use the vanilla `client.messages.create('Using Unusual Whales MCP, …')` pattern
> for the data fetch. **That pattern doesn't actually invoke MCP** through the Anthropic
> Messages API and **returns hallucinated JSON**. Use the REST API directly."

It is in prompts 03, 04, 05 and 10, and it is the most important line in all
twelve. See [architecture.md](architecture.md) for why.

## Three prompts that say "no"

* **05 (backtester):** *"Do NOT import or initialize `anthropic`."* The reasoning happens
  in the Monte Carlo math, not in a model.
* **07 (prediction analyzer):** *"**Do NOT submit any orders.**"* The book refuses to ship
  an unauthenticated trading bot for a CFTC-regulated venue, and this repo honors that
  refusal permanently.
* **11 (risk module):** *"No Claude calls needed for this module; every check is math or
  public data."*

**The prompts that refuse things are the ones worth reading twice.**

---

*Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
