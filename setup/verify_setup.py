"""One Script, All Four Connections — the 4/4 gate before Chapter 3 (ch02.md:387-468).

Run this before you build anything:

    python setup/verify_setup.py     ->  Result: 4/4 checks passed

Offline (the default) all four checks run against the bundled synthetic
fixtures, so a brand-new clone with no `.env` still prints 4/4. Check 3 is the
one that changes shape offline, and it says so out loud rather than pretending:

* **Live** (`CTB_OFFLINE=0`): shells out to `claude mcp list` and looks for the
  `unusualwhales` server, exactly as ch02 prints. `claude mcp list` is the source
  of truth (ch02.md:201-204).
* **Offline**: there is no Claude Code to interrogate, so it verifies the thing
  the *saved scripts* actually depend on — that the Unusual Whales data layer
  answers a flow-alerts request through the same code path `screener.py` uses.
  The printed label names what was checked. A rationalized PASS would be worse
  than an honest one.

There is deliberately **no `mcp_config.json`** anywhere in this repo. The UW MCP
is registered with Claude Code via `claude mcp add`; Claude Code keeps the
registration in its own config layer (ch02.md:353).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from utils import banner  # noqa: E402
from utils.offline import (  # noqa: E402
    get_anthropic,
    get_trading_client,
    http_get_json,
    offline_enabled,
)

load_dotenv()

UW_BASE = "https://api.unusualwhales.com/api"

MCP_REGISTER_HINT = (
    "unusualwhales not registered. Run: "
    "claude mcp add --transport http unusualwhales "
    "https://api.unusualwhales.com/api/mcp "
    "--header 'Authorization: Bearer $UW_API_KEY'"
)


def check(name, test_fn):
    try:
        result = test_fn()
        print(f"  [PASS] {name}: {result}")
        return True
    except Exception as e:  # noqa: BLE001 - the book prints whatever went wrong
        print(f"  [FAIL] {name}: {e}")
        return False


def check_python():
    v = sys.version_info
    assert v.major == 3 and v.minor >= 11, f"Need 3.11+, got {v.major}.{v.minor}"
    return f"Python {v.major}.{v.minor}.{v.micro}"


def check_claude():
    client = get_anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=50,
        messages=[{"role": "user", "content": "Say OK"}],
    )
    text = msg.content[0].text[:50]
    return f"{text}" + (" (offline stub)" if offline_enabled() else "")


def check_mcp():
    """Live: `claude mcp list`. Offline: the UW data layer the scripts use."""
    if offline_enabled():
        alerts = http_get_json(
            f"{UW_BASE}/option-trades/flow-alerts",
            headers={"Authorization": "Bearer <not-required-offline>"},
            params={"min_premium": 200_000, "min_volume_oi_ratio": 3.0,
                    "is_sweep": True},
        ).get("data", [])
        if not alerts:
            raise RuntimeError("offline UW fixture returned no flow alerts")
        return (f"offline UW data layer OK ({len(alerts)} flow alerts from "
                f"fixtures) — live MCP registration NOT checked in offline mode")

    import subprocess

    result = subprocess.run(
        ["claude", "mcp", "list"], capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"`claude mcp list` failed: {result.stderr.strip()}")
    if "unusualwhales" not in result.stdout:
        raise RuntimeError(MCP_REGISTER_HINT)
    return "unusualwhales MCP registered with Claude Code"


def check_alpaca():
    client = get_trading_client()
    acct = client.get_account()
    suffix = " (offline stub)" if offline_enabled() else ""
    return f"Status: {acct.status}, Cash: ${float(acct.cash):,.2f}{suffix}"


def run() -> int:
    banner()
    print("=== SETUP VERIFICATION ===\n")
    passed = 0
    total = 4

    if check("Python version", check_python):
        passed += 1
    if check("Claude API", check_claude):
        passed += 1
    if check("Unusual Whales MCP", check_mcp):
        passed += 1
    if check("Alpaca paper trading", check_alpaca):
        passed += 1

    print(f"\n{'=' * 40}")
    print(f"Result: {passed}/{total} checks passed")
    if passed == total:
        print("All systems go. You're ready for Chapter 3.")
    else:
        print("Fix the failed checks before proceeding.")
        print("See docs/troubleshooting.md for detailed troubleshooting.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(run())
