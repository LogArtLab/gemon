"""Regression tests for semantic bugs fixed on branch iot."""

import random

from gemon.elements import Interval
from gemon.functions import Polynomial
from gemon.nodes import NaryNode, SubNode


def _sum(intervals):
    total = intervals[0]
    for interval in intervals[1:]:
        total = total + interval
    return total


def test_binary_node_cuts_at_exact_bounds():
    # The node used to cut at start + (end - start), which may differ from end in the
    # last bit; the operator then rejected the pair ("different bounds").
    rng = random.Random(0)
    for _ in range(20000):
        node = SubNode()
        out = []
        node.to(out.append)
        a = rng.uniform(0, 1000)
        c = a + rng.uniform(0.02, 20)
        m = rng.uniform(a + 0.001, c - 0.001)
        node.receive_left(Interval(a, c, Polynomial.constant(1)))
        node.receive_right(Interval(a, m, Polynomial.constant(2)))
        node.receive_right(Interval(m, c + 1, Polynomial.constant(3)))
        assert [(i.start, i.end, i.function.c) for i in out] == [(a, m, -1), (m, c, -2)]


def test_nary_node_cuts_at_exact_bounds():
    rng = random.Random(1)
    for _ in range(20000):
        node = NaryNode(_sum)
        out = []
        node.to(out.append)
        node.add_receiver("x")
        node.add_receiver("y")
        a = rng.uniform(0, 1000)
        c = a + rng.uniform(0.03, 30)
        b = rng.uniform(a + 0.001, c - 0.002)
        m = rng.uniform(b + 0.001, c - 0.001)
        node.receive("x", Interval(a, c, Polynomial.constant(1)))
        node.receive("y", Interval(b, m, Polynomial.constant(2)))
        node.receive("y", Interval(m, c + 1, Polynomial.constant(3)))
        assert [(i.start, i.end) for i in out] == [(a, b), (b, m), (m, c)]


def test_input_nodes_keep_their_sample_when_downstream_raises():
    # The input nodes updated their state after notifying: when a downstream node
    # raised, the sample was lost and the next interval overlapped the previous one.
    from gemon.nodes import VariablePWCNode, VariablePWLNode
    for cls in (VariablePWCNode, VariablePWLNode):
        node = cls()
        out = []
        node.to(out.append)
        failures = iter([False, True, False, False])

        def flaky(interval):
            if next(failures):
                raise RuntimeError("downstream failure")

        node.to(flaky)
        for t, v in [(0, 1.0), (1, 2.0), (2, 3.0)]:
            try:
                node.receive(t, v)
            except RuntimeError:
                pass
        node.receive(3, 4.0)
        assert [(i.start, i.end) for i in out] == [(0, 1), (1, 2), (2, 3)]


def _window_inputs(kind, seed, n=120):
    """Intervals of a random signal: piecewise constant, linear, or quadratic (integral of a linear one)."""
    from e2e_trace import random_samples
    from gemon.nodes import VariablePWCNode, VariablePWLNode, IntegralWindowNode
    source = VariablePWCNode() if kind == "pwc" else VariablePWLNode()
    intervals = []
    if kind == "quadratic":
        integral = IntegralWindowNode(1.7)
        source.to(integral.receive)
        integral.to(intervals.append)
    else:
        source.to(intervals.append)
    for t, v in random_samples(seed, n=n):
        source.receive(t, v)
    return intervals


def _true_extremum(intervals, a, b, pick):
    values = []
    for interval in intervals:
        lo, hi = max(a, interval.start), min(b, interval.end)
        if hi <= lo:
            continue
        f = interval.function
        values += [f(lo), f(hi)]
        if f.a != 0 and lo < -f.b / (2 * f.a) < hi:
            values.append(f(-f.b / (2 * f.a)))
    return pick(values)


def test_window_min_and_max_are_exact():
    # MaxWindowNode used to raise ("Cannot remove an interval that is not a left subset")
    # and MinWindowNode gave wrong values on piecewise-linear signals.
    from gemon.nodes import MinWindowNode, MaxWindowNode
    for kind in ("pwc", "pwl", "quadratic"):
        intervals = _window_inputs(kind, seed=4)
        for length in (0.5, 2.5, 9.0):
            for cls, pick in ((MinWindowNode, min), (MaxWindowNode, max)):
                node = cls(length)
                out = []
                node.to(out.append)
                for interval in intervals:
                    node.receive(interval)
                assert out and all(p.end == q.start for p, q in zip(out, out[1:]))
                for piece in out:
                    if piece.end - piece.start < 1e-9:  # sliver from the window's float arithmetic
                        continue
                    for k in (1, 2, 3):
                        t = piece.start + k * (piece.end - piece.start) / 4
                        assert abs(piece.function(t) - _true_extremum(intervals, t, t + length, pick)) < 1e-6


def test_window_min_ignores_undefined_values():
    # Undefined is ignored by every time aggregator: the window used to give undefined
    # as soon as it touched an undefined piece. Window [t, t + 1]: on [0, 1] it sees
    # 3 then (from t = 1 on) only undefined up to 2, where the value 1 starts.
    from gemon.nodes import MinWindowNode
    node = MinWindowNode(1.0)
    out = []
    node.to(out.append)
    node.receive(Interval(0, 1, Polynomial.constant(3)))
    node.receive(Interval(1, 2, Polynomial.undefined()))
    node.receive(Interval(2, 5, Polynomial.constant(1)))
    node.receive(Interval(5, 6, Polynomial.undefined()))
    node.receive(Interval(6, 9, Polynomial.constant(2)))

    def at(t):
        return next(i.function(t) for i in out if i.start <= t < i.end)
    assert at(0.5) == 3          # [0.5, 1.5]: 3 and undefined
    assert at(1.0) == 1          # [1, 2]: undefined, then 1 at 2
    assert at(1.5) == 1
    assert at(4.5) == 1          # [4.5, 5.5]: 1 and undefined
    assert at(5.0) == 2          # [5, 6]: undefined, then 2 at 6


def test_window_min_is_undefined_where_the_window_holds_no_defined_value():
    from gemon.nodes import MinWindowNode, MaxWindowNode
    for cls in (MinWindowNode, MaxWindowNode):
        node = cls(1.0)
        out = []
        node.to(out.append)
        node.receive(Interval(0, 1, Polynomial.constant(3)))
        node.receive(Interval(1, 4, Polynomial.undefined()))
        node.receive(Interval(4, 6, Polynomial.constant(1)))
        assert all(i.is_undefined() for i in out if 1 <= i.start and i.end <= 3)
        assert any(i.is_undefined() for i in out)


def test_window_extremum_matches_brute_force_with_undefined_pieces():
    from gemon.nodes import MinWindowNode, MaxWindowNode
    for seed in range(6):
        rng = random.Random(seed)
        t, pieces = 0.0, []
        for _ in range(40):
            d = rng.uniform(0.1, 1.5)
            if rng.random() < 0.3:
                f = Polynomial.undefined()
            else:
                f = Polynomial.linear(rng.uniform(-3, 3), rng.uniform(-5, 5))
            pieces.append(Interval(t, t + d, f))
            t += d
        for cls, extremum in ((MinWindowNode, min), (MaxWindowNode, max)):
            for length in (0.5, 2.0, 5.0):
                node = cls(length)
                out = []
                node.to(out.append)
                for piece in pieces:
                    node.receive(piece)
                for o in out:
                    if o.end - o.start < 1e-9:
                        continue
                    x = (o.start + o.end) / 2
                    values = []
                    for p in pieces:  # pieces are [start, end), the window [x, x + length]
                        if p.is_undefined() or p.end <= x or p.start > x + length:
                            continue
                        a, b = max(p.start, x), min(p.end, x + length)
                        values += [p.function(a + (b - a) * k / 200) for k in range(201)]
                    if not values:
                        assert o.is_undefined()
                    else:
                        assert abs(o.function(x) - extremum(values)) < 1e-9


def test_undefined_propagates_through_pointwise_operators():
    # Strict propagation: an undefined operand gives an undefined result. The right
    # operand used to be read as its zero coefficients (20 - undefined = 20).
    from gemon.elements import IntervalOperators
    u = Interval(0, 10, Polynomial.undefined())
    x = Interval(0, 10, Polynomial.constant(20.0))
    for left, right in ((x, u), (u, x)):
        assert (left - right).is_undefined()
        assert (left + right).is_undefined()
        assert all(i.is_undefined() for i in left.min_interval(right))
        assert all(i.is_undefined() for i in left.max_interval(right))
    assert [i.is_undefined() for i in u.higher_than(5)] == [True]
    assert [i.is_undefined() for i in u.lower_than(5)] == [True]
    assert IntervalOperators.mult_const(2)(u)[0].is_undefined()
    assert u.abs()[0].is_undefined()
    assert IntervalOperators.negation()(u)[0].is_undefined()
    assert Polynomial.constant(0) != Polynomial.undefined()


def test_sub_node_propagates_undefined_right_operand():
    node, out = SubNode(), []
    node.to(out.append)
    node.receive_left(Interval(0, 10, Polynomial.constant(20.0)))
    node.receive_right(Interval(0, 10, Polynomial.undefined()))
    assert out[0].is_undefined()


def test_window_integral_ignores_undefined_values():
    # Undefined adds nothing to the integral (ignored by the time aggregators).
    from gemon.nodes import IntegralWindowNode
    node, out = IntegralWindowNode(2.0), []
    node.to(out.append)
    node.receive(Interval(0, 1, Polynomial.constant(3)))
    node.receive(Interval(1, 2, Polynomial.undefined()))
    node.receive(Interval(2, 6, Polynomial.constant(1)))
    assert next(i.function(0) for i in out if i.start <= 0 < i.end) == 3
    assert next(i.function(1) for i in out if i.start <= 1 < i.end) == 1


def test_abs_not_and_or():
    from gemon.nodes import AbsNode, NotNode, AndNode, OrNode
    node, out = AbsNode(), []
    node.to(out.append)
    node.receive(Interval(0, 4, Polynomial.linear(1, -1)))  # t - 1: negative on [0, 1)
    assert [(i.start, i.end) for i in out] == [(0, 1), (1, 4)]
    assert out[0].function(0.5) == 0.5 and out[1].function(3) == 2
    node, out = NotNode(), []
    node.to(out.append)
    node.receive(Interval(0, 1, Polynomial.constant(1)))
    node.receive(Interval(1, 2, Polynomial.constant(0)))
    assert [i.function(0) for i in out] == [0, 1]
    for cls, expected in ((AndNode, [0, 0, 1]), (OrNode, [1, 1, 1])):
        node, out = cls(), []
        node.to(out.append)
        for s, e, a, b in ((0, 1, 1, 0), (1, 2, 0, 1), (2, 3, 1, 1)):
            node.receive_left(Interval(s, e, Polynomial.constant(a)))
            node.receive_right(Interval(s, e, Polynomial.constant(b)))
        assert [i.function(0) for i in out] == expected


def test_comparisons_without_inner_crossing_are_decided_inside_the_interval():
    # A signal starting exactly at the threshold and rising: the root of f - threshold
    # falls just outside the interval because of rounding, and the old code decided
    # the whole interval by comparing the values at the left end point, where they
    # are equal: higher_than gave 0 and min_interval picked the threshold.
    s, e = 15.482683736469738, 20.340652830337653
    f = Polynomial.linear(2.7252650356287864, -38.05282518329322)
    threshold = 4.1415914614062075
    assert f(s) == threshold
    rising = Interval(s, e, f)
    level = Interval(s, e, Polynomial.constant(threshold))
    assert [i.function.c for i in rising.higher_than(threshold)] == [1]
    assert [i.function.c for i in rising.lower_than(threshold)] == [0]
    assert [i.function for i in rising.min_interval(level)] == [level.function]
    assert [i.function for i in rising.max_interval(level)] == [f]
    falling = Interval(s, e, f.mult_by_const(-1) + Polynomial.constant(2 * threshold))  # starts at the threshold, falls
    assert [i.function for i in falling.min_interval(level)] == [falling.function]
    assert [i.function.c for i in falling.higher_than(threshold)] == [0]


def test_binary_node_does_not_modify_shared_intervals():
    # When one input starts later, the node shortened the head of the other queue by
    # modifying the Interval in place. The same object is delivered to every node fed
    # by that signal: here b = x + z, still holding x's first interval in its queue,
    # saw it shortened by a = y - x and reported b undefined on [0, 2].
    from gemon.nodes import VariablePWCNode, SumNode
    x, y, z = VariablePWCNode(), VariablePWCNode(), VariablePWCNode()
    a, b = SubNode(), SumNode()
    out_a, out_b = [], []
    a.to(out_a.append)
    b.to(out_b.append)
    x.to(a.receive_right)
    y.to(a.receive_left)
    x.to(b.receive_left)
    z.to(b.receive_right)
    nodes = {"x": x, "y": y, "z": z}
    for name, t, v in [("x", 0, 1.0), ("z", 0, 10.0), ("x", 2, 1.0), ("y", 2, 5.0), ("y", 4, 5.0),
                       ("z", 4, 20.0), ("x", 4, 3.0), ("y", 6, 5.0), ("z", 6, 20.0), ("x", 6, 3.0)]:
        nodes[name].receive(t, v)
    assert [(i.start, i.end, i.function.c) for i in out_b] == [(0, 2, 11.0), (2, 4, 11.0), (4, 6, 23.0)]
    assert out_a[0].is_undefined() and (out_a[0].start, out_a[0].end) == (0, 2)


def test_binary_node_drops_intervals_ending_before_the_other_input_starts():
    # An interval of the early input ending at or before the start of the other
    # input was shortened to an empty or reversed interval, which then produced
    # empty or reversed output pieces.
    for late_start in (2, 3.5):
        node = SubNode()
        out = []
        node.to(out.append)
        for s, e, c in [(0, 1, 1.0), (1, 2, 2.0), (2, 5, 3.0)]:
            node.receive_right(Interval(s, e, Polynomial.constant(c)))
        node.receive_left(Interval(late_start, 5, Polynomial.constant(10.0)))
        assert all(i.end > i.start for i in out)
        assert all(p.end == q.start for p, q in zip(out, out[1:]))
        assert out[0].start == 0 and out[-1].end == 5
        assert all(i.is_undefined() for i in out if i.end <= late_start)
        assert [i.function.c for i in out if i.start >= late_start] == [7.0]
