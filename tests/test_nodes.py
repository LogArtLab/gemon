from gemon.elements import Interval
from gemon.functions import Polynomial
from gemon.nodes import NaryNode


def test_nary_node_synchronized_starts():
    """No gap: all inputs start at the same time, no undefined interval emitted."""
    results = []
    node = NaryNode(lambda intervals: intervals[0] + intervals[1])
    node.add_receiver("a")
    node.add_receiver("b")
    node.to(results.append)

    node.receive("a", Interval(0, 2, Polynomial.constant(1)))
    node.receive("b", Interval(0, 2, Polynomial.constant(2)))

    assert results == [Interval(0, 2, Polynomial.constant(3))]


def test_nary_node_offset_starts():
    """Two inputs with different starts: emits undefined gap then merges aligned portions."""
    results = []
    node = NaryNode(lambda intervals: intervals[0] + intervals[1])
    node.add_receiver("a")
    node.add_receiver("b")
    node.to(results.append)

    node.receive("a", Interval(0, 3, Polynomial.constant(1)))
    node.receive("b", Interval(1, 3, Polynomial.constant(2)))

    assert results[0] == Interval(0, 1, Polynomial.undefined())
    assert results[1] == Interval(1, 3, Polynomial.constant(3))


def test_nary_node_three_inputs_one_already_aligned():
    """Three inputs where one is already at max_start: it must not be split."""
    results = []
    node = NaryNode(lambda intervals: intervals[0] + intervals[1] + intervals[2])
    node.add_receiver("a")
    node.add_receiver("b")
    node.add_receiver("c")
    node.to(results.append)

    node.receive("a", Interval(0, 3, Polynomial.constant(1)))
    node.receive("b", Interval(1, 3, Polynomial.constant(2)))
    node.receive("c", Interval(2, 3, Polynomial.constant(3)))

    assert results[0] == Interval(0, 2, Polynomial.undefined())
    assert results[1] == Interval(2, 3, Polynomial.constant(6))