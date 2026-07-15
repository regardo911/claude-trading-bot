"""Anthropic connectivity smoke test — Chapter 2, Step 2 (ch02.md:126-142).

Offline (the default) this talks to the deterministic Claude stub, so it runs
with no API key at all. Set CTB_OFFLINE=0 with a real ANTHROPIC_API_KEY to hit
the live Messages API.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from utils import banner  # noqa: E402
from utils.offline import get_anthropic  # noqa: E402

load_dotenv()


def main() -> int:
    banner()
    client = get_anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": "What is the current price of AAPL? Just say you don't "
                       "have live data access yet if that's the case.",
        }],
    )
    print(message.content[0].text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
