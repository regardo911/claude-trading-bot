# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] (2026-07-14)

The repo's first post-launch update. The book is a fixed snapshot; this repo is live, and
this release brings it in line with the current (2nd-edition) manuscript, makes the
backtester teach diagnosis instead of celebrating a verdict, and reorganizes around a
chapter-by-chapter learner path. Corrections to the printed book now live in
[`ERRATA.md`](ERRATA.md); this file tracks the code and layout.

### Added

* **[`ERRATA.md`](ERRATA.md)**: the reader-facing tie-breaker: corrections to the printed
  book (including the current unrebuilt printing) and book↔repo reconciliation.
* **[`GOTCHAS.md`](GOTCHAS.md)**: the pitfalls that actually bit while building this repo.
* **[`START_HERE.md`](START_HERE.md) + `chapters/chNN-*/` labs**: a learner path, one lab per
  chapter (the prompt → the file it generates → the command → the expected output → the one
  thing to inspect).
* **[`reference/README.md`](reference/README.md)**: the reference-implementation surface,
  positioned behind the labs.
* **Mixed backtester scenarios**: `fixtures/scenarios/{no_edge,overfit,edge_candidate}.json`
  and a `--scenario` flag, so the tool can be watched telling strategies apart. New make
  targets: `check`, `tour`, `demo-ch06-no-edge` / `-overfit` / `-edge-candidate`.
* **[`docs/deviation-manifest.json`](docs/deviation-manifest.json)**: machine-readable
  deviation status, hash-pinned to the manuscript snapshot it tracks.

### Changed

* **README** rewritten to lead with the learner path (276 → 176 lines); the reference
  implementation now sits behind it.
* **`make demo`** no longer ends on a lone "EDGE CONFIRMED": it runs the no-edge, overfit and
  edge-candidate scenarios and ends on a diagnostic question. The full-system tour moved to
  `make tour`.
* **Deviations #6 (Monte Carlo sampler) and #13 (`check_exits()` short handling)** reframed as
  *resolved in the 2nd edition*: the repo already matched, so no code changed, only the
  framing. Both stay in `ERRATA.md` for anyone holding an earlier printing.
* **Package status → Beta** (was Production/Stable); **version → 1.1.0**.

### Removed

* The internal build report, not part of the shipped companion.

## [1.0.0] (2026-07-13)

First public release. The companion code to *Use Claude to Build an AI Trading Bot: 90 Days
with Stocks, Options, and Prediction Markets*.

### Added

**The eight catalog items**, every one runnable offline with zero API keys:

* `setup/`: the ch02 4/4 verification gate (`verify_setup.py`, `test_claude.py`,
  `test_alpaca.py`)
* `screener/`: the ch04 daily watchlist bot and its outcome tracker
* `flow_trader/`: the ch05 real-time options-flow trader and position checker
* `backtester/`: the ch06 Monte Carlo backtester, in/out-of-sample split and walk-forward
  validation. **No LLM anywhere in it**, by design.
* `prediction/`: the ch07 Polymarket analyzer (**read-only, permanently**), the calibration
  tracker, and the Kalshi RSA-PSS client
* `multi_agent/`: the ch08 four-agent system with Alpaca bracket orders
* `risk/`: the ch09 gatekeeper: five hard rules, quarter-Kelly, a zero floor
* `tracking/`: the ch10 90-day go-live ladder and its Day-30 gate

**The offline switch** (`utils/offline.py`): deterministic, seeded stubs for Anthropic,
Unusual Whales, Alpaca, yfinance and Polymarket Gamma. The default path opens no sockets.

**Chapter 3's analysis contract, as code** (`utils/signals.py`): the 1M-share liquidity
floor, the −15 geopolitical penalty and the −20 Tier1/Tier2 conflict penalty. All three are
stated as running in the book and appear in **no code it prints**.

**The 12 verbatim `PASTE TO CLAUDE CODE` prompts** (`prompts/`), extracted programmatically
from the manuscript, each with its output schema, its consumer, its offline behaviour and its
cost.

**Appendix B's five strategy templates + the parameter cheat sheet** (`templates/`).

**Eight computed figures** (`docs/images/`): one per catalog item, each rendered by importing
the repo's real modules and running the actual functions the doc teaches. Every one is stamped
*"synthetic sample data — illustrative mechanics only"*.

**Tests**: the book's worked examples as assertions, a no-network guard, a
"safe-mode-cannot-be-flipped-by-a-flag" test, the Kalshi signature verified against a throwaway
in-test keypair, and **a regression test for every documented deviation**.

### Fixed (relative to the book's printed code)

Every item below is documented with its chapter cite and arithmetic in
[`docs/book-deviations.md`](docs/book-deviations.md) and pinned by a regression test.

* **Monte Carlo sampler** (#6): bootstraps **with** replacement (`random.choices`), never a
  permutation. The printed code sampled `random.sample`, which collapses every simulation to
  the identical final value. (Reclassified in 1.1.0; see above.)
* **`check_exits()` short handling** (#13): covers a short with `OrderSide.BUY`, plus the
  breakeven-stop move and 5-day time limit. The printed profit-target branch submitted
  `OrderSide.SELL` unconditionally, doubling a short at +6% P&L. (Reclassified in 1.1.0.)
* **The sector cap ignored the position you were about to open** (#12), so the module's own
  worked example approved a 66.6% single-name concentration on a 40% cap.
* **Rule 4 promised REDUCE and only ever BLOCKED** (#11). `remaining_capacity` was computed,
  returned as a *string*, and never read.
* **`evaluate_trade()` couldn't take a custom stop width** (#10), making ch09's own "widen TSLA
  to 5%. **Use it.**" advice unreachable through the gatekeeper the book tells every bot to call.
* **`profit_factor` was unformatted, and two different formulas shared one name** (#7). The
  sum-based one is now `gross_profit_factor`.
* **`MIN_VOLUME` was a dead constant** (#1). It now filters.
* **The multi-agent orchestrator crashed on an unparseable agent response** (#4).
* **The `newer_than` polling param** the prose describes and the code omits (#3).

### Documented, not changed

* `suggested_bet` (#9): a three-way contradiction between the code, the prose and the two
  printed examples. **No single formula produces both printed examples.** Ships as printed, with
  the erratum stated loudly: `MAX_BET_SIZE` is a scaling coefficient, not a cap.
* The Sharpe formula (#8): transcribed exactly as printed, including the `√252` annualizer that
  is wrong in kind for per-trade 5-day returns. Silently re-annualizing would break ch09 and ch10
  instead of fixing anything.
* The minimum-trades gate (#2): 30 in code, 100 in Appendix B. 30 is the hard gate.
* Bracket orders are ch08's, not ch09's (#15).
* Two prose-arithmetic errata with no code path (#16): the repo deliberately computes neither.
* **ch05's `MAX_POSITION_PCT` and ch09's `MAX_RISK_PER_TRADE` are NOT the same thing** (#5) and
  must not be unified. Both ship, unchanged.

[1.1.0]: https://github.com/regardo911/claude-trading-bot/releases/tag/v1.1.0
[1.0.0]: https://github.com/regardo911/claude-trading-bot/releases/tag/v1.0.0
