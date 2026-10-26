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
