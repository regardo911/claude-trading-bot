# Examples

One runnable offline demo per catalog item. Each one imports the repo's real
modules (no copies, no simplified re-implementations) and runs them against the
committed synthetic fixtures.

```bash
python examples/01_setup_gate.py
python examples/02_screener_watchlist.py
python examples/03_flow_trader_exits.py     # incl. the short-side fix
python examples/04_backtest_verdict.py
python examples/05_prediction_edge.py
python examples/06_multi_agent_cycle.py
python examples/07_risk_gatekeeper.py
python examples/08_phase1_gate.py
```

Or run the whole tour at once:

```bash
make demo
```

*Illustrative results on synthetic sample data, not indicative of real or
historical performance. Educational software. Not financial advice.*
