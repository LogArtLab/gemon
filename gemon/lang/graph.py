"""Canonical description of a graph of gemon nodes, to compare two graphs.

A gemon graph is wired with node.to(other.receive...): every edge is a bound method
of the receiving node. Starting from the input nodes, the graph is walked along
these edges; each node gets a signature

    (class name, parameters, ((port, signature of the input), ...))

computed from its inputs, recursively. Two graphs are the same graph when they have
the same multiset of node signatures (same nodes, same parameters, same wiring, and
the same sharing: a sub-formula built twice instead of once gives one signature
twice) and their named outputs have the same signatures. The order in which nodes
were created or connected does not matter.
"""

from collections import Counter

from gemon.nodes import (AddConstNode, HigherThanNode, LowerThanNode, MultiplyByConst, ShiftNode, VariablePWCNode,
                         VariablePWLNode, WindowNode)
from gemon.notifiers import IntervalNotifier

PORTS = {"receive": "in", "receive_left": "left", "receive_right": "right"}


def _number_key(value):
    return type(value).__name__, repr(value)


def parameters(node):
    """The parameters that define a node besides its class and inputs."""
    if isinstance(node, (HigherThanNode, LowerThanNode)):
        return (_number_key(node.threshold),)
    if isinstance(node, (MultiplyByConst, AddConstNode)):
        return (_number_key(node.value),)
    if isinstance(node, ShiftNode):
        return (_number_key(node.delta),)
    if isinstance(node, WindowNode):
        return (type(node.window_operator).__name__, getattr(node.window_operator, "sign", None),
                _number_key(node.window.length))
    return ()


def _edges(node):
    """(receiving node, port) for every node fed by node."""
    for observer in node.observers:
        target = getattr(observer, "__self__", None)
        if isinstance(target, IntervalNotifier) and observer.__name__ in PORTS:
            yield target, PORTS[observer.__name__]


def describe(inputs, outputs=None):
    """inputs: {name: input node}; outputs: {name: node}. Returns (signatures, outputs):
    a Counter of the signatures of all the nodes reachable from the inputs, and a dict
    output name -> signature."""
    incoming = {}   # id(node) -> [(port, source node)]
    nodes = {}      # id(node) -> node
    stack = list(inputs.values())
    for node in stack:
        nodes[id(node)] = node
    while stack:
        node = stack.pop()
        for target, port in _edges(node):
            incoming.setdefault(id(target), []).append((port, node))
            if id(target) not in nodes:
                nodes[id(target)] = target
                stack.append(target)
    names = {id(node): name for name, node in inputs.items()}
    memo = {}

    def signature(node):
        key = id(node)
        if key not in memo:
            if isinstance(node, (VariablePWLNode, VariablePWCNode)):
                memo[key] = (type(node).__name__, (names.get(key),), ())
            else:
                sources = tuple(sorted((port, signature(source)) for port, source in incoming.get(key, [])))
                memo[key] = (type(node).__name__, parameters(node), sources)
        return memo[key]

    signatures = Counter(signature(node) for node in nodes.values())
    named = {name: signature(node) for name, node in (outputs or {}).items()}
    return signatures, named


def same_graph(inputs_a, outputs_a, inputs_b, outputs_b):
    """True when the two graphs are the same (see the module docstring)."""
    return describe(inputs_a, outputs_a) == describe(inputs_b, outputs_b)
