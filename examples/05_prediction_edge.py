"""Example — the ch07 analyzer. Read-only, and it stays that way.

Note what the analyzer refuses to do: the CPI, Bitcoin and S&P contracts all get
LOW confidence and drop out, because a saved script with no web search has no
business claiming to know this week's data. A quiet day with no opportunities is
the correct answer, not a failure.
"""
import _bootstrap  # noqa: F401

from prediction.prediction_analyzer import run_analyzer

if __name__ == "__main__":
    opportunities = run_analyzer()
    print(f"\n{len(opportunities)} opportunity(ies) found.")
    print("The analyzer ranked them and stopped. It has no order-submission path,")
    print("and a test in this repo enforces that it never grows one.")
