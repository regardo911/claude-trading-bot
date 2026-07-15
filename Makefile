.PHONY: help check setup demo tour test lint figures clean \
        demo-ch04 demo-ch06-no-edge demo-ch06-overfit demo-ch06-edge-candidate
.DEFAULT_GOAL := help

PY ?= python3

help:  ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

check:  ## Environment + imports only — the fastest "is this installed right?"
	@$(PY) -c "import sys; assert sys.version_info >= (3, 11), 'needs Python 3.11+'; \
	import numpy, pandas, requests; \
	import backtester.backtester, screener.screener, flow_trader.flow_trader, \
	prediction.prediction_analyzer, multi_agent.multi_agent, risk.risk_manager, \
	tracking.phase1_assessment, utils.offline, utils.signals; \
	print('OK: Python', '.'.join(map(str, sys.version_info[:3])), '+ core imports + all 8 modules')"

setup:  ## Install the core stack (no API keys needed)
	$(PY) -m pip install -e ".[dev]"

demo:  ## Diagnostic demo: the backtester on no-edge vs overfit vs edge (start here)
	@$(PY) tools/demo.py

tour:  ## Full offline tour — every bot, end to end, zero keys
	@$(PY) tools/demo.py --tour

demo-ch04:  ## Just the screener (ch04)
	@$(PY) screener/screener.py

demo-ch06-no-edge:  ## Backtester on a strategy with no edge -> NO EDGE
	@CTB_SCENARIO=no_edge $(PY) backtester/backtester.py --scenario no_edge

demo-ch06-overfit:  ## Backtester on an overfit strategy -> OVERFIT
	@CTB_SCENARIO=overfit $(PY) backtester/backtester.py --scenario overfit

demo-ch06-edge-candidate:  ## Backtester on an edge candidate -> EDGE CONFIRMED
	@CTB_SCENARIO=edge_candidate $(PY) backtester/backtester.py --scenario edge_candidate

test:  ## Run the full test suite, offline
	CTB_OFFLINE=1 $(PY) -m pytest tests/ -q

lint:  ## Ruff
	$(PY) -m ruff check .

figures:  ## Regenerate every docs image from the repo's own code + fixtures
	$(PY) tools/generate_docs_charts.py

clean:  ## Remove caches and generated run artifacts
	rm -rf .pytest_cache .ruff_cache **/__pycache__ __pycache__ *.egg-info
	rm -f screener/watchlist_*.json screener/tracking.json
	rm -f flow_trader/trade_log.json flow_trader/exit_state.json
	rm -f backtester/report.json backtester/report_*.json backtester/monte_carlo.png
	rm -f prediction/opportunities_*.json prediction/markets.json
	rm -f prediction/calibration.json multi_agent/cycle_log.json
