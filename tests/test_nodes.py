from gemon.elements import Interval, MinMonotonicEdge
from gemon.functions import Polynomial
from gemon.nodes import MinOptimalWindowNode2, NaryNode


def test_receive():
    vout = []
    node = MinOptimalWindowNode2(1.5)
    node.to(vout.append)
    node.receive(Interval(0, 1, Polynomial.constant(2)))
    node.receive(Interval(1, 2, Polynomial.constant(3)))
    node.receive(Interval(2, 3, Polynomial.constant(2.5)))
    node.receive(Interval(3, 4, Polynomial.constant(2.1)))

    print()

def test_monotonic_edge_remove():
    me = MinMonotonicEdge()
    me.add(Interval(0,1,Polynomial.constant(0)))
    me.add(Interval(1,2,Polynomial.constant(1)))
    me.add(Interval(2,3,Polynomial.constant(2)))

    removed_interval = me.remove(1.5)

    assert  removed_interval == [Interval(0,1,Polynomial.constant(0)),Interval(1,1.5,Polynomial.constant(1))]

def test_monotonic_edge_remove2():
    me = MinMonotonicEdge()
    me.add(Interval(0,1,Polynomial.constant(0)))
    me.add(Interval(1,2,Polynomial.constant(1)))
    me.add(Interval(2,3,Polynomial.constant(2)))

    removed_interval = me.remove(1)

    assert  removed_interval == [Interval(0,1,Polynomial.constant(0)),]

def test_monotonic_edge_remove3():
    me = MinMonotonicEdge()
    me.add(Interval(0,1,Polynomial.constant(0)))
    me.add(Interval(1,2,Polynomial.constant(1)))
    me.add(Interval(2,3,Polynomial.constant(2)))

    removed_interval = me.remove(3)

    assert  removed_interval == [Interval(0,1,Polynomial.constant(0)),
                                 Interval(1,2,Polynomial.constant(1)),
                                 Interval(2,3,Polynomial.constant(2)),]

def test_monotonic_edge_remove4():
    me = MinMonotonicEdge()
    me.add(Interval(0,1,Polynomial.constant(0)))
    me.add(Interval(1,2,Polynomial.constant(1)))
    me.add(Interval(2,3,Polynomial.constant(2)))

    removed_interval = me.remove(0.2)

    assert  removed_interval == [Interval(0,0.2,Polynomial.constant(0)),]


def test_monotonic_edge_add():
    me = MinMonotonicEdge()
    me.add(Interval(0,1,Polynomial.constant(0)))
    me.add(Interval(1,2,Polynomial.constant(2)))
    me.add(Interval(2,3,Polynomial.constant(1)))

    removed_interval = me.remove(1.5)

    assert  removed_interval == [Interval(0,1,Polynomial.constant(0)),Interval(1,1.5,Polynomial.constant(1))]

def test_monotonic_edge_add2():
    me = MinMonotonicEdge()
    me.add(Interval(0,1,Polynomial.constant(1)))
    me.add(Interval(1,2,Polynomial.constant(2)))
    me.add(Interval(2,3,Polynomial.constant(0)))

    removed_interval = me.remove(1)

    assert  removed_interval == [Interval(0,1,Polynomial.constant(0)),]

# def test_monotonic_edge_add3():
#     me = MinMonotonicEdge()
#     me.add(Interval(0,1,Polynomial.linear(1,0)))
#     me.add(Interval(1,2,Polynomial.linear(-1,2)))
#     me.add(Interval(2,3,Polynomial.linear(1,-2)))
#
#     removed_interval = me.remove(3)
#
#     assert  removed_interval == [Interval(0,1,Polynomial.constant(0)),]


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