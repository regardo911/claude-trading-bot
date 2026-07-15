# Chapter 5 lab: the flow trader

Where the screener is a morning newspaper, this is a police scanner. It watches
options flow every 30 seconds and places a paper trade only when confidence clears
70%, then manages the exit.

## The prompt
Paste [`prompts/04_flow_trader.md`](../../prompts/04_flow_trader.md) into Claude Code
for [`flow_trader/flow_trader.py`](../../flow_trader/flow_trader.py) and
`check_positions.py`.

## Run it
```bash
python flow_trader/flow_trader.py          # one cycle
python flow_trader/flow_trader.py --loop   # the real polling loop
```
```
[..] === OPTIONS FLOW TRADER STARTED ===
[..] Confidence threshold: 70%
[..] Mode: single cycle
[..] Listening for whale activity...
```

## The exit is the lesson
Look at the exit logic. Reducing a short at its +6% profit target means buying it back
(`OrderSide.BUY`), not selling; selling would double the short. The 2nd-edition book
gets this right and so does this repo. Earlier printings did not. Run
[`examples/03_flow_trader_exits.py`](../../examples/03_flow_trader_exits.py) to watch a
short covered with a BUY, plus the breakeven-stop move and the 5-day time limit. See
[book-deviations.md #13](../../docs/book-deviations.md#13).

---
Reference: [docs/03-flow-trader.md](../../docs/03-flow-trader.md)
