# Chapter 8 lab: the multi-agent system

Four specialists, one decision: Monitor, Analyst, Risk, Executor. Each is a separate
Claude call with a narrow job, wired into a single trading cycle with no loopback.

## The prompt
Paste [`prompts/10_multi_agent.md`](../../prompts/10_multi_agent.md) into Claude Code
for [`multi_agent/multi_agent.py`](../../multi_agent/multi_agent.py).

## Run it
```bash
python multi_agent/multi_agent.py
```
```
MULTI-AGENT TRADING CYCLE
[MONITOR] Status: WARNING
[MONITOR] ALERT: NVDA is down 3.0% and is sitting on its stop-loss threshold.
[ANALYST] Found 3 recommendations.
[RISK] ... [EXECUTOR] ...
```

## Bracket orders
The Executor submits bracket orders (`OrderClass.BRACKET`): the entry, the take-profit,
and the stop as one exchange-side order that fires even when your bot is offline. This
is the protective pattern the flow trader's soft stop can't give you. A guard was also
added so an unparseable agent response can't crash the cycle; every agent's parser
returns `None` safely rather than raising
([book-deviations.md #4](../../docs/book-deviations.md#4)).

---
Reference: [docs/06-multi-agent.md](../../docs/06-multi-agent.md)
