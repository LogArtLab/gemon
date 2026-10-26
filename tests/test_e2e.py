"""
End-to-end regression test of the monitoring semantics.

Every node of every scenario in e2e_trace.py must produce exactly the signal
recorded in tests/golden/e2e.json (same intervals, same functions, bit for bit),
and the same exceptions must be raised. A failure means that a change altered
what the tool computes, not only how fast.
"""

import json
import os

import pytest

import e2e_trace

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden", "e2e.json")) as f:
    GOLDEN = json.load(f)

SCENARIOS = {"rv2025_cgm": e2e_trace.rv2025_cgm, "rv2025_weather": e2e_trace.rv2025_weather,
             "synthetic_composite": e2e_trace.synthetic_composite}
for _kind in e2e_trace.INTERPOLATIONS:
    for _scenario in (e2e_trace.synthetic_unary, e2e_trace.synthetic_binary, e2e_trace.synthetic_nary,
                      e2e_trace.synthetic_windows):
        SCENARIOS[f"{_scenario.__name__}_{_kind}"] = (lambda s=_scenario, k=_kind: s(k))


def test_golden_covers_every_scenario():
    assert sorted(SCENARIOS) == sorted(GOLDEN)


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_semantics_unchanged(name):
    assert SCENARIOS[name]() == GOLDEN[name]
