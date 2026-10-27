"""Tests of the compiler of the gemon specification language.

The conversion text -> graph of nodes is checked in three independent ways:

1. Structure: for a battery of formulas, the graph compiled from the text is the same
   graph (same nodes, parameters, wiring and sharing; gemon.lang.graph) as a monitor
   built by hand with the gemon nodes, as in examples/RV2025.
2. Behaviour: the two monitors, fed with the same random signals, produce the same
   intervals, bit for bit; the RV 2025 case studies written as text reproduce the
   reference traces of tests/golden/e2e.json.
3. Random formulas: random syntax trees are printed, parsed back (same tree) and
   compiled; the result must be the graph a direct, independent translation of the
   tree builds, and must produce the same intervals.
"""

import hashlib
import json
import os
import random
import sys

import pytest

from gemon.lang import LangError, compile_file, compile_program, parse
from gemon.lang.graph import describe
from gemon.lang.printer import unparse
from gemon.lang import syntax as S
from gemon.nodes import (AbsNode, AddConstNode, AndNode, FilterNode, HigherThanNode, IntegralWindowNode,
                         LowerThanNode, MaxNode, MaxWindowNode, MinNode, MinWindowNode, MultiplyByConst, NotNode,
                         OrNode, ShiftNode, SubNode, SumNode, VariablePWCNode, VariablePWLNode)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e2e_trace  # noqa: E402

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden", "e2e.json")


# ── helpers ───────────────────────────────────────────────────────────────────

def samples(seed, n=400):
    return e2e_trace.random_samples(seed, n=n)


def stream(inputs, data):
    """Feed {input name: [(t, v)]} to {input name: node} in global time order."""
    events = sorted((t, i, name, v) for i, (name, points) in enumerate(sorted(data.items())) for t, v in points)
    for t, _, name, v in events:
        inputs[name].receive(t, v)


def record(outputs):
    traces = {name: [] for name in outputs}
    for name, node in outputs.items():
        node.to(lambda iv, trace=traces[name]: trace.append((iv.start, iv.end, repr(iv.function))))
    return traces


def run(inputs, outputs, data):
    traces = record(outputs)
    stream(inputs, data)
    return traces


def assert_same_monitor(source, hand_inputs, hand_outputs, data=None):
    """The program compiled from source and the hand-built graph are the same graph
    and give the same intervals on random signals."""
    monitor = compile_program(source)
    assert set(monitor.inputs) == set(hand_inputs)
    assert set(monitor.outputs) == set(hand_outputs)
    compiled = describe(monitor.inputs, monitor.outputs)
    hand = describe(hand_inputs, hand_outputs)
    assert compiled[1] == hand[1], "the outputs differ"
    assert compiled[0] == hand[0], "the graphs differ (nodes, parameters, wiring or sharing)"
    if data is None:
        data = {name: samples(seed) for seed, name in enumerate(sorted(hand_inputs), start=11)}
    compiled_traces = run(monitor.inputs, monitor.outputs, data)
    hand_traces = run(hand_inputs, hand_outputs, data)
    assert compiled_traces == hand_traces
    assert any(compiled_traces.values())


def unary(node, source):
    source.to(node.receive)
    return node


def binary(node, left, right):
    left.to(node.receive_left)
    right.to(node.receive_right)
    return node


# ── 1 + 2: hand-built monitors ───────────────────────────────────────────────

def test_cgm():
    source = """
        input G : linear
        param T = 180
        TAR     := On[0, T] Int(G > 180) / T          # fraction of time above 180 mg/dL
        TBR     := On[0, T] Int(G < 70) / T
        mean    := On[0, T] Int(G) / T
        mean_AR := On[0, T] Int(G | G > 180) / T      # mean where G > 180
        mean_BR := On[0, T] Int(G | G < 70) / T
    """
    G = VariablePWLNode()
    phi_AR = unary(HigherThanNode(180), G)
    phi_BR = unary(LowerThanNode(70), G)
    TAR = unary(MultiplyByConst(1 / 180), unary(IntegralWindowNode(180), phi_AR))
    TBR = unary(MultiplyByConst(1 / 180), unary(IntegralWindowNode(180), phi_BR))
    mean = unary(MultiplyByConst(1 / 180), unary(IntegralWindowNode(180), G))
    mean_AR = unary(MultiplyByConst(1 / 180), unary(IntegralWindowNode(180), binary(FilterNode(), G, phi_AR)))
    mean_BR = unary(MultiplyByConst(1 / 180), unary(IntegralWindowNode(180), binary(FilterNode(), G, phi_BR)))
    data = {"G": [(t, 40 + 200 * abs(v) / 5) for t, v in samples(1, n=600)]}
    assert_same_monitor(source, {"G": G},
                        {"TAR": TAR, "TBR": TBR, "mean": mean, "mean_AR": mean_AR, "mean_BR": mean_BR}, data)


def test_weather():
    source = """
        input co2  : linear
        input temp : linear
        mean_co2  := On[0, 5] Int(co2) / 5
        mean_temp := On[0, 5] Int(temp) / 5
        spec      := mean_co2 > 422 and mean_temp > 0
    """
    co2, temp = VariablePWLNode(), VariablePWLNode()
    mean_co2 = unary(MultiplyByConst(1 / 5), unary(IntegralWindowNode(5), co2))
    mean_temp = unary(MultiplyByConst(1 / 5), unary(IntegralWindowNode(5), temp))
    spec = binary(AndNode(), unary(HigherThanNode(422), mean_co2), unary(HigherThanNode(0), mean_temp))
    data = {"co2": [(t, 422 + v) for t, v in samples(2)], "temp": samples(3)}
    assert_same_monitor(source, {"co2": co2, "temp": temp},
                        {"mean_co2": mean_co2, "mean_temp": mean_temp, "spec": spec}, data)


def test_deviation_spikes_and_windows():
    source = """
        input x : linear
        input y : const
        dev   := |x - On[0, 30s] Int(x) / 30|
        spike := x - On[0, 15s] Max(x) > 1 or dev >= 3
        ok    := On[0, 1min] Min(x > -4 and x < 4)
        alarm := On[0, 1min] Max(spike)
        cover := On[0, 1min] Int(x > 2 | y > 0) / 60
        gap   := min(x, y) - max(x, y)
    """
    x, y = VariablePWLNode(), VariablePWCNode()
    dev = unary(AbsNode(), binary(SubNode(), x, unary(MultiplyByConst(1 / 30), unary(IntegralWindowNode(30), x))))
    spike = binary(OrNode(),
                   unary(HigherThanNode(1), binary(SubNode(), x, unary(MaxWindowNode(15), x))),
                   unary(NotNode(), unary(LowerThanNode(3), dev)))
    ok = unary(MinWindowNode(60), binary(AndNode(), unary(HigherThanNode(-4), x), unary(LowerThanNode(4), x)))
    alarm = unary(MaxWindowNode(60), spike)
    cover = unary(MultiplyByConst(1 / 60),
                  unary(IntegralWindowNode(60), binary(FilterNode(), unary(HigherThanNode(2), x),
                                                       unary(HigherThanNode(0), y))))
    gap = binary(SubNode(), binary(MinNode(), x, y), binary(MaxNode(), x, y))
    assert_same_monitor(source, {"x": x, "y": y},
                        {"dev": dev, "spike": spike, "ok": ok, "alarm": alarm, "cover": cover, "gap": gap})


def test_constants_on_either_side():
    source = """
        input x : linear
        a := 3 - x
        b := x * 2 + 1
        c := -(x / 4)
        d := 2 * x - 0.5
        e := (x + 1) / 2
        f := x + 0 * 5        # folded: x + 0 is x
    """
    x = VariablePWLNode()
    neg = unary(MultiplyByConst(-1), x)
    a = unary(AddConstNode(3), neg)
    twice = unary(MultiplyByConst(2), x)
    b = unary(AddConstNode(1), twice)
    c = unary(MultiplyByConst(-1), unary(MultiplyByConst(1 / 4), x))
    d = unary(AddConstNode(-0.5), twice)
    e = unary(MultiplyByConst(1 / 2), unary(AddConstNode(1), x))
    assert_same_monitor(source, {"x": x}, {"a": a, "b": b, "c": c, "d": d, "e": e, "f": x})


def test_comparisons():
    source = """
        input x : linear
        input y : linear
        gt  := x > y
        le  := x <= y          # not (x - y > 0): shares x - y > 0 with gt
        ge  := x >= 1
        rev := 2 < x           # x > 2
        nl  := not x < 1       # the same node as ge
    """
    x, y = VariablePWLNode(), VariablePWLNode()
    gt = unary(HigherThanNode(0), binary(SubNode(), x, y))
    le = unary(NotNode(), gt)
    ge = unary(NotNode(), unary(LowerThanNode(1), x))
    rev = unary(HigherThanNode(2), x)
    assert_same_monitor(source, {"x": x, "y": y}, {"gt": gt, "le": le, "ge": ge, "rev": rev, "nl": ge})


def test_shifted_window_and_sharing_across_definitions():
    source = """
        input x : linear
        a := x > 1
        b := On[0, 5] Int(a)
        c := On[0, 5] Int(x > 1)      # the same node as b
        d := On[2, 10] Max(x)         # On[0, 8] Max(x), shifted by 2
        e := On[2, 10] Max(x) + d     # shares d
    """
    x = VariablePWLNode()
    a = unary(HigherThanNode(1), x)
    b = unary(IntegralWindowNode(5), a)
    d = unary(ShiftNode(-2), unary(MaxWindowNode(8), x))
    e = binary(SumNode(), d, d)
    assert_same_monitor(source, {"x": x}, {"a": a, "b": b, "c": b, "d": d, "e": e})


def test_a_different_graph_is_detected():
    # the structural comparison is not vacuous: a wrong threshold, a swapped operand
    # or a duplicated sub-formula make it fail
    monitor = compile_program("input x : linear\ninput y : linear\nd := x - y\ne := x > 1 and x > 1\n")
    target = describe(monitor.inputs, monitor.outputs)
    for variant in range(3):
        x, y = VariablePWLNode(), VariablePWLNode()
        d = binary(SubNode(), y, x) if variant == 0 else binary(SubNode(), x, y)
        if variant == 1:
            e = binary(AndNode(), unary(HigherThanNode(1), x), unary(HigherThanNode(1), x))  # not shared
        else:
            shared = unary(HigherThanNode(1.5 if variant == 2 else 1), x)
            e = binary(AndNode(), shared, shared)
        assert describe({"x": x, "y": y}, {"d": d, "e": e}) != target


# ── RV 2025 case studies against the reference traces ────────────────────────

def _digests(monitor, names):
    entries = {}
    for out, golden_name in names.items():
        sha, count = hashlib.sha256(), [0]

        def watch(iv, sha=sha, count=count):
            count[0] += 1
            sha.update(f"{iv.start!r}|{iv.end!r}|{iv.function!r}\n".encode())
        monitor.to(out, watch)
        entries[golden_name] = (sha, count)
    return entries


def _check(entries, golden):
    for name, (sha, count) in entries.items():
        assert {"intervals": count[0], "sha256": sha.hexdigest()} == golden[name], name


def test_rv2025_cgm_reproduces_the_reference_traces():
    with open(GOLDEN) as f:
        golden = json.load(f)["rv2025_cgm"]
    monitor = compile_file(os.path.join(e2e_trace.EXAMPLES, "cgm", "cgm.gemon"))
    entries = _digests(monitor, {"G": "G", "TAR": "phi_TAR", "TBR": "phi_TBR", "mean": "mean_G",
                                 "mean_AR": "mean_G_filtered_AR", "mean_BR": "mean_G_filtered_BR"})
    for t, g in e2e_trace._csv_rows(os.path.join(e2e_trace.EXAMPLES, "cgm", "data", "data.csv")):
        monitor.receive("G", t, g)
    _check(entries, golden)
    assert len(monitor.nodes) == 15   # as in examples/RV2025/cgm/cgm.py


def test_rv2025_weather_reproduces_the_reference_traces():
    with open(GOLDEN) as f:
        golden = json.load(f)["rv2025_weather"]
    monitor = compile_file(os.path.join(e2e_trace.EXAMPLES, "weather", "weather.gemon"))
    entries = _digests(monitor, {"co2": "co2", "temp": "temp", "mean_co2": "mean_co2", "mean_temp": "mean_temp",
                                 "spec": "and_spec"})
    for t, co2, temp in e2e_trace._csv_rows(os.path.join(e2e_trace.EXAMPLES, "weather", "data", "data.csv")):
        monitor.receive("co2", t, co2)
        monitor.receive("temp", t, temp)
    _check(entries, golden)


# ── semantics of the shifted window ──────────────────────────────────────────

@pytest.mark.parametrize("tag, extremum", [("Min", min), ("Max", max)])
def test_shifted_window_matches_brute_force(tag, extremum):
    # On[a, b] Tag(x) at t is Tag of x over [t + a, t + b]
    a, b = 2.5, 9
    monitor = compile_program(f"input x : linear\nw := On[{a}, {b}] {tag}(x)\n")
    out = monitor.observe("w")
    points = samples(5, n=200)
    for t, v in points:
        monitor.receive("x", t, v)

    def x_at(t):
        for (t0, v0), (t1, v1) in zip(points, points[1:]):
            if t0 <= t <= t1:
                return v0 + (v1 - v0) * (t - t0) / (t1 - t0)

    checked = 0
    for iv in out.intervals:
        if iv.end - iv.start < 1e-9:
            continue
        t = (iv.start + iv.end) / 2
        grid = [t + a + (b - a) * k / 2000 for k in range(2001)]
        inner = [p for p, _ in points if t + a < p < t + b]
        expected = extremum(x_at(s) for s in grid + inner)
        assert iv.function(t) == pytest.approx(expected, abs=1e-6)
        checked += 1
    assert checked > 50


# ── compile errors ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("body, message", [
    ("e := w + 1", "undefined name 'w'"),
    ("e := x * y", "product of two signals"),
    ("e := 2 / x", "division by a signal"),
    ("e := x / 0", "division by zero"),
    ("e := 3 + 4", "a definition must be a signal"),
    ("e := x > 1\ne := x", "'e' is already defined"),
    ("param p = x", "parameter 'p' must be a constant"),
    ("e := On[0, x] Int(x)", "bounds of a time window must be constants"),
    ("e := On[5, 2] Int(x)", "invalid time window"),
    ("e := On[0, 2] Int(On[0, 2] Int(x))", "degree 3"),
    ("e := x and y > 0", "expected a boolean signal"),
    ("e := On[0, 2] Int(x | y)", "expected a boolean signal"),
    ("e := min(x, 3)", "min(signal, constant)"),
    ("e := 1 < 2", "comparison between constants"),
    ("e := x + true", "expected a number"),
    ("e := On[0, 2] Max(3)", "time window over the constant 3"),
])
def test_compile_errors(body, message):
    with pytest.raises(LangError, match=message.replace("(", r"\(").replace(")", r"\)")):
        compile_program("input x : linear\ninput y : linear\ninput z : const\n" + body + "\n")


def test_int_of_int_over_piecewise_constant_signals_is_allowed():
    compile_program("input z : const\ne := On[0, 2] Int(On[0, 2] Int(z))\n")  # degree 2


def test_boolean_constants_are_folded():
    monitor = compile_program("input x : linear\na := x > 1 and true\nb := false or x > 1\n")
    assert monitor.outputs["a"] is monitor.outputs["b"]
    with pytest.raises(LangError, match="boolean constant false"):
        compile_program("input x : linear\na := x > 1 and false\n")


def test_monitor_interface():
    monitor = compile_program("input x : const\ne := x > 1\n")
    seen = []
    monitor.to("e", seen.append)
    signal = monitor.observe("e")
    for t, v in [(0, 0.0), (1, 2.0), (2, 2.0)]:
        monitor.receive("x", t, v)
    assert [iv.function.c for iv in seen] == [0, 1] and len(signal.intervals) == 2
    with pytest.raises(KeyError, match="not an input"):
        monitor.receive("e", 3, 1.0)
    with pytest.raises(KeyError):
        monitor.observe("nothing")


# ── 3: random formulas ───────────────────────────────────────────────────────

INPUTS = {"x": "linear", "y": "linear", "z": "const"}


class RandomFormula:
    """Random surface syntax in the canonical forms (signal op signal, signal op
    positive constant), with its type: (expr, boolean, degree)."""

    def __init__(self, seed):
        self.rng = random.Random(seed)

    def constant(self):
        if self.rng.random() < 0.5:
            return Number(self.rng.choice([2, 3, 4, 5, 7]))
        return Number(round(self.rng.uniform(0.1, 6), 2))

    def numeric(self, depth):
        r = self.rng.random()
        if depth == 0 or r < 0.2:
            name = self.rng.choice(sorted(INPUTS))
            return S.Ref(name), False, 1 if INPUTS[name] == "linear" else 0
        choice = self.rng.choice(["sum", "sub", "scale", "div", "addc", "neg", "abs", "min", "max", "window"])
        if choice in ("sum", "sub", "min", "max"):
            (a, _, da), (b, _, db) = self.numeric(depth - 1), self.numeric(depth - 1)
            op = {"sum": "+", "sub": "-", "min": "min", "max": "max"}[choice]
            return S.Binary(op, a, b), False, max(da, db)
        if choice in ("scale", "div", "addc"):
            a, _, d = self.numeric(depth - 1)
            op = {"scale": "*", "div": "/", "addc": "+"}[choice]
            return S.Binary(op, a, self.constant()), False, d
        if choice in ("neg", "abs"):
            a, _, d = self.numeric(depth - 1)
            return S.Unary(choice, a), False, d
        return self.window(depth, boolean=False)

    def boolean(self, depth):
        r = self.rng.random()
        if depth == 0 or r < 0.35:
            a, _, _ = self.numeric(max(depth - 1, 0))
            if self.rng.random() < 0.3:
                b, _, _ = self.numeric(max(depth - 1, 0))
                return S.Compare(self.rng.choice(["<", ">"]), a, b), True, 0
            return S.Compare(self.rng.choice(["<", ">", "<=", ">="]), a, self.constant()), True, 0
        choice = self.rng.choice(["and", "or", "not", "window"])
        if choice in ("and", "or"):
            return S.Binary(choice, self.boolean(depth - 1)[0], self.boolean(depth - 1)[0]), True, 0
        if choice == "not":
            return S.Unary("not", self.boolean(depth - 1)[0]), True, 0
        return self.window(depth, boolean=True)

    def window(self, depth, boolean):
        tag = self.rng.choice(["Min", "Max"] if boolean else ["Int", "Min", "Max"])
        operand, _, degree = self.boolean(depth - 1) if boolean else self.numeric(depth - 1)
        if tag == "Int" and degree >= 2:
            tag = "Max"
        lower = self.rng.choice([0, 0, 1, 2.5])
        upper = lower + self.rng.choice([1, 3, 6.5])
        condition = self.boolean(depth - 1)[0] if self.rng.random() < 0.3 else None
        out_degree = degree + 1 if tag == "Int" else degree
        return S.Window(tag, Number(lower), Number(upper), operand, condition), boolean and tag != "Int", out_degree


def Number(value):
    return S.Number(value)


class DirectBuilder:
    """An independent translation of the canonical surface syntax into gemon nodes,
    with hash-consing on (class, parameters, inputs): the reference for the compiler."""

    def __init__(self):
        self.inputs = {name: (VariablePWLNode() if kind == "linear" else VariablePWCNode())
                       for name, kind in INPUTS.items()}
        self.cache = {}

    def node(self, cls, params, *sources):
        key = (cls, params, tuple(id(s) for s in sources))
        if key not in self.cache:
            node = cls(*params)
            if len(sources) == 1:
                sources[0].to(node.receive)
            elif len(sources) == 2:
                sources[0].to(node.receive_left)
                sources[1].to(node.receive_right)
            self.cache[key] = node
        return self.cache[key]

    def build(self, e):
        if isinstance(e, S.Ref):
            return self.inputs[e.name]
        if isinstance(e, S.Unary):
            x = self.build(e.operand)
            if e.op == "neg":
                return self.node(MultiplyByConst, (-1,), x)
            return self.node({"abs": AbsNode, "not": NotNode}[e.op], (), x)
        if isinstance(e, S.Binary):
            a = self.build(e.left)
            if isinstance(e.right, S.Number):
                c = e.right.value
                if e.op == "*":
                    return self.node(MultiplyByConst, (c,), a)
                if e.op == "/":
                    return self.node(MultiplyByConst, (1 / c,), a)
                return self.node(AddConstNode, (c,), a)
            b = self.build(e.right)
            cls = {"+": SumNode, "-": SubNode, "min": MinNode, "max": MaxNode, "and": AndNode, "or": OrNode}[e.op]
            return self.node(cls, (), a, b)
        if isinstance(e, S.Compare):
            a = self.build(e.left)
            if isinstance(e.right, S.Number):
                c = e.right.value
            else:
                a, c = self.node(SubNode, (), a, self.build(e.right)), 0
            if e.op == ">":
                return self.node(HigherThanNode, (c,), a)
            if e.op == "<":
                return self.node(LowerThanNode, (c,), a)
            if e.op == ">=":
                return self.node(NotNode, (), self.node(LowerThanNode, (c,), a))
            return self.node(NotNode, (), self.node(HigherThanNode, (c,), a))
        if isinstance(e, S.Window):
            x = self.build(e.operand)
            if e.condition is not None:
                x = self.node(FilterNode, (), x, self.build(e.condition))
            a, b = e.lower.value, e.upper.value
            cls = {"Int": IntegralWindowNode, "Min": MinWindowNode, "Max": MaxWindowNode}[e.tag]
            w = self.node(cls, (b - a,), x)
            return self.node(ShiftNode, (-a,), w) if a != 0 else w
        raise TypeError(e)


@pytest.mark.parametrize("seed", range(60))
def test_random_formulas(seed):
    generator = RandomFormula(seed)
    formulas = [generator.boolean(4)[0] if k % 2 else generator.numeric(4)[0] for k in range(3)]
    source = "".join(f"input {n} : {k}\n" for n, k in INPUTS.items())
    source += "".join(f"f{k} := {unparse(e)}\n" for k, e in enumerate(formulas))
    # 1. printing and parsing give back the same trees
    assert [item.expr for item in parse(source).items[len(INPUTS):]] == formulas
    # 2. the compiled graph is the graph of the direct translation
    direct = DirectBuilder()
    outputs = {f"f{k}": direct.build(e) for k, e in enumerate(formulas)}
    monitor = compile_program(source)
    assert describe(monitor.inputs, monitor.outputs) == describe(direct.inputs, outputs), source
    # 3. and gives the same intervals
    data = {name: samples(100 * seed + i, n=250) for i, name in enumerate(sorted(INPUTS))}
    assert run(monitor.inputs, monitor.outputs, data) == run(direct.inputs, outputs, data), source


def test_parameters_given_by_the_caller():
    source = "input x : linear\nparam T = 10\nparam H = T / 2\ne := On[0, T] Int(x) / H\n"
    default, other = compile_program(source), compile_program(source, params={"T": 4})
    assert [type(n).__name__ for n in default.nodes] == [type(n).__name__ for n in other.nodes]
    window = next(n for n in other.nodes if isinstance(n, IntegralWindowNode))
    scale = next(n for n in other.nodes if isinstance(n, MultiplyByConst))
    assert window.window.length == 4 and scale.value == 1 / 2   # H = T / 2 follows the new T
    with pytest.raises(LangError, match="unknown parameter"):
        compile_program(source, params={"Z": 1})
    with pytest.raises(LangError, match="expected a number"):
        compile_program(source, params={"T": "4"})

