# Chapter labs

The learner path. One lab per chapter, each a single page: **the prompt → the file
Claude generates → the command → the expected output → the one thing to inspect.**

Follow them in order alongside the book, or jump to the chapter you're on.

| Lab | Build | Run |
|---|---|---|
| [ch02-setup](ch02-setup/) | the 4/4 connection gate | `python setup/verify_setup.py` |
| [ch03-signals](ch03-signals/) | the tiered signal rules | `python screener/screener.py` |
| [ch04-screener](ch04-screener/) | scan flow → ranked watchlist | `python screener/screener.py` |
| [ch05-flow-trader](ch05-flow-trader/) | poll flow, trade at 70%+ | `python flow_trader/flow_trader.py` |
| [ch06-backtester](ch06-backtester/) | Monte Carlo + a verdict | `make demo-ch06-no-edge` |
| [ch07-prediction-markets](ch07-prediction-markets/) | rank mispricings, never bet | `python prediction/prediction_analyzer.py` |
| [ch08-multi-agent](ch08-multi-agent/) | Monitor→Analyst→Risk→Executor | `python multi_agent/multi_agent.py` |
| [ch09-risk](ch09-risk/) | the gatekeeper | `python risk/risk_manager.py` |
| [ch10-go-live](ch10-go-live/) | the 90-day ladder + gate | `python tracking/phase1_assessment.py` |

Every command runs **offline, with no API keys**. Chapters 1, 11, and 12 are
narrative (setup mindset, debugging, scaling) and have no build artifact of their own.

New here? Read [../START_HERE.md](../START_HERE.md) first. Want the full reference
implementation behind these labs? [../reference/README.md](../reference/README.md).
