# Changelog

## 1.1.0

Bug fixes (each with a regression test in `tests/test_bugfixes.py`):
- `BinaryNode`, `NaryNode`: intervals are cut at exact bounds (`Interval.split_at`). Cutting at
  `start + (end - start)` could differ from `end` in the last bit, and the operator then raised
  "Cannot subtract/sum interval with different bounds".
- `BinaryNode`: when one input starts later, the head of the other queue is replaced by a new interval instead of
  being modified in place (the same `Interval` object is shared by every node fed by that signal: another node could
  see it shortened); an interval ending before the other input starts is emitted as undefined and dropped instead of
  being shortened to an empty or reversed interval.
- `VariablePWCNode`, `VariablePWLNode`: the state is updated before notifying, so a sample is not lost (and the next
  interval does not overlap the previous one) when a downstream node raises.
- `MinWindowNode`, `MaxWindowNode`: new `WindowExtremum` operator, exact for piecewise polynomials of degree at most 2.
  `MaxWindowNode` used to raise on irregularly sampled signals; `MinWindowNode` gave wrong values on piecewise-linear
  signals. The output at `t` is the minimum (maximum) over `[t, t + length]`; a window touching undefined values gives
  an undefined output.
- `Interval.min_interval`, `max_interval`, `higher_than`, `lower_than`: without a crossing inside the interval the
  result is decided at the midpoint; deciding at the left end point was wrong when the two functions touch there.

Performance:
- `WindowExtremum` keeps the minima of the window content in a monotonic queue (Lemire's algorithm): amortised O(1)
  per window move instead of O(window size).
- Deques for the input queues of `BinaryNode` and `NaryNode`; `NaryNode` counts its empty queues instead of scanning
  all its inputs.
- Faster `Polynomial` arithmetic (no `isinstance` check against `numbers.Number` on the hot path), `__slots__` on
  `Polynomial` and `Interval`, threshold comparisons without temporary objects.

Removed (broken or unused): `MinOptimalWindowNode`, `MinOptimalWindowNode2`, `Min`, `Max`, `Min2`, `MinLemire`,
`MaxLemire`, `MinMonotonicEdge`, `MaxMonotonicEdge`, `IntervalQueue`, `IntervalValued`, `Intervals`.

Tests: end-to-end regression tests (`tests/test_e2e.py`) compare the signal produced by every node of the RV 2025
case studies and of synthetic scenarios with reference traces in `tests/golden/`.
