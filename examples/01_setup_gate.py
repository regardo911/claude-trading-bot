"""Example — the ch02 setup gate, offline.

Four connections, one script, zero keys.
"""
import _bootstrap  # noqa: F401

from setup.verify_setup import run

if __name__ == "__main__":
    raise SystemExit(run())
