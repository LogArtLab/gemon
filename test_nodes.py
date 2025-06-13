from elements import Interval, MinMonotonicEdge
from functions import Polynomial
from nodes import MinOptimalWindowNode, MinOptimalWindowNode2


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