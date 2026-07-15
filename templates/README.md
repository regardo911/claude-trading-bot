# Strategy templates: Appendix B

Copy-paste parameter blocks for the four core strategies in the book plus the
multi-agent configuration, with the defaults the author recommends starting
from.

**Change one parameter at a time and re-run the Chapter 6 backtest after each
change.** Never change several at once: you will not know which one moved the
number, and you will be fitting noise inside a week.

| File | Strategy | Ships as code? |
|---|---|---|
| [`01_momentum_screener.py`](01_momentum_screener.py) | Daily unusual-options-activity scan | Yes, `screener/screener.py` |
| [`02_mean_reversion.py`](02_mean_reversion.py) | Price reverting to a 20-day mean | **No**, template only |
| [`03_options_flow_follower.py`](03_options_flow_follower.py) | Real-time flow follower | Yes, `flow_trader/flow_trader.py` |
| [`04_prediction_market_analyzer.py`](04_prediction_market_analyzer.py) | Mispriced event contracts | Yes, `prediction/prediction_analyzer.py` |
| [`05_multi_agent_config.py`](05_multi_agent_config.py) | 4-agent orchestration | Yes, `multi_agent/multi_agent.py` |
| [`parameter_cheat_sheet.md`](parameter_cheat_sheet.md) | Every starting value on one page | — |

Template 2 (mean reversion) is the one the book describes but never builds. It
is here as parameters and prose, exactly as Appendix B has it. The repo does not
ship a mean-reversion bot, because the book does not, and inventing one would
make this repo something other than a faithful companion.

*Educational software. Not financial advice. See [DISCLAIMER.md](../DISCLAIMER.md).*
