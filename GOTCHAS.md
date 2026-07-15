# Gotchas

Things that actually bit while building this, written down so they don't bite you. None of
these are hypothetical. Each one cost an afternoon.

## The offline fixtures are a frozen day, and the dates have to be moved to "today"

The bundled Unusual Whales and Polymarket fixtures were minted on one synthetic trading day
(`FIXTURE_AS_OF` in `utils/offline.py`). If you serve them verbatim, every `max_dte` filter in
the book sees an expiry that is now in the past, computes a **negative** days-to-expiry, and
silently drops every option. The screener finds nothing and looks broken.

The stubs shift each fixture's timestamps from `FIXTURE_AS_OF` onto the current date at read
time, so the data always looks like today. If you add a fixture with dates in it, it has to go
through the same shift, or it will quietly filter itself to nothing.

## An absolute path in the tests would have broken every clone

Four test files once resolved paths from an absolute developer directory instead of from the
repo. On the author's machine everything passed. On any other machine (a fresh clone, a CI
runner) those paths don't exist, so the suite would have failed on the first pull, and the
whole "clone it and it works" claim with it. (An absolute home path in a public repo is also a
small privacy leak.)

Tests now derive the repo root from `__file__` (see `tests/conftest.py`). The lesson: a green
suite on the machine that wrote it proves nothing about a clone. Run it from somewhere else.

## A committed chart once claimed something the code didn't do

The risk figure's legend said a line was "quarter-Kelly bound" when that point was actually
capped by the 2% hard limit: a false statement, baked into a PNG, that no test could catch
because the number itself was fine. It was only visible by opening the image.

Every figure in `docs/images/` is now computed by importing the real modules and running the
functions the docs teach (`make figures`), and each render gets eyeballed. "Computed, not
hand-drawn" is necessary but not sufficient. You still have to look at the picture.

## A synthetic "edge" fixture kept flagging itself OVERFIT

`fixtures/scenarios/edge_candidate.json` has to reach the `EDGE CONFIRMED` verdict, which means
passing the in/out-of-sample split. The first cut gave both chronological halves the same win
rate but drew their return *magnitudes* from noise, and the Sharpe-drop leg of the overfit
check fired anyway, correctly, on that noise.

The fix was to build both halves from the **same** return multiset (same values, shuffled
order), so in- and out-of-sample agree by construction. If you hand-author a scenario fixture,
make the two halves statistically identical or the backtester will call your "edge" overfit,
which is the backtester doing its job.

## `$` in a matplotlib label silently turns into math

matplotlib treats `$...$` as mathtext. An unescaped dollar sign in a chart label doesn't
error; it renders as a mangled math expression, so `$100,000` comes out wrong. Escape it
(`\$`) in any figure label that prints money.

## matplotlib is optional, and the backtester has to survive without it

`matplotlib` is the `viz` extra, not a core dependency: a zero-key clone installs neither it
nor any keyed client. `backtester.py` still runs and still writes `report.json` when it's
absent; it just skips the fan chart and says so. If you add a module that imports matplotlib at
top level, you break the zero-key install. Import it lazily, inside the function that plots.
