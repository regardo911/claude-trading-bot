# 01 — MCP connection test

> **Source:** Chapter 2, Step 3 (Test the connection from inside Claude Code) · `ch02.md:227`
> Quoted **verbatim** from the manuscript; do not edit the prompt body below.

## The prompt

Open Claude Code in your project directory (`cd ~/ai-trading-bot && claude`) and
paste:

```text
"Using the unusualwhales MCP, what ticker has the highest unusual options activity right now? One ticker symbol only, no narration."
```

## Expected output schema

One US-listed ticker symbol. Nothing else: the prompt asks for "no narration".

## How deterministic code consumes it

Nothing consumes this programmatically. It is a **liveness probe** for the
registered MCP server. If a real ticker comes back, Claude Code is dispatching
through the `unusualwhales` MCP. If Claude says it has no access to that data, or
returns a symbol that does not exist, the MCP is not connected; re-check
`claude mcp list`, which is the source of truth (ch02.md:201-204).

## Offline behaviour in this repo

**Not reproducible offline, and this repo does not fake it.** MCP dispatch only
happens inside an interactive Claude Code session against a live, paid UW server;
a stub that invented a "hottest ticker" would be exactly the hallucination ch02
spends two pages warning about.

What the repo verifies instead is the surface the *saved scripts* actually use:
`setup/verify_setup.py`'s check 3 confirms the UW **REST** data layer answers a
flow-alerts request, and says out loud in its own output that live MCP
registration was not checked.

## Cost notes

$0 for the prompt itself. It requires a paid UW tier: Trial is $50/week and is
the cheapest tier that includes API/MCP access at all. The free "Free Shamu" web
tier does **not**.

---

*Educational software. Not financial advice. Trading carries substantial risk of
loss. See [DISCLAIMER.md](../DISCLAIMER.md).*
