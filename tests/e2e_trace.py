"""
End-to-end traces for the regression tests of the monitoring semantics.

Each scenario builds a graph of gemon nodes, streams samples into it and
records, for every node, the signal it produces: the sequence of intervals
(start, end, function) it emits. Each node's sequence is reduced to its length
and a SHA-256 digest; exceptions raised while streaming are recorded too, as
part of the behaviour. Two code versions with the same digests compute exactly
the same semantics, bit for bit, for these inputs.

Scenarios:
  - rv2025_cgm, rv2025_weather: the two case studies of the RV 2025 paper
    (examples/RV2025), on their data.
  - synthetic_*: random, irregularly sampled signals (piecewise-constant and
    piecewise-linear interpolation) through every kind of node: unary, binary,
    n-ary, temporal windows, and compositions of them.

Random signals use random.Random(seed).random() only, whose sequence Python
guarantees across versions.
"""

import csv
import hashlib
import os
import random

from gemon.elements import Interval
from gemon.nodes import (
    VariablePWCNode, VariablePWLNode, HigherThanNode, LowerThanNode, ShiftNode, MultiplyByConst,
    MinNode, MaxNode, SumNode, SubNode, FilterNode, NaryNode,
    IntegralWindowNode, MinWindowNode, MaxWindowNode,
)

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "RV2025")


class Recorder:
    """Records the output signal of named nodes and the exceptions of a scenario."""

    def __init__(self):
        self.signals = {}
        self.errors = []

    def watch(self, name, node):
        sha = hashlib.sha256()
        entry = self.signals[name] = {"sha": sha, "intervals": 0}

        def record(interval):
            entry["intervals"] += 1
            sha.update(f"{interval.start!r}|{interval.end!r}|{interval.function!r}\n".encode())

        node.to(record)
        return node

    def feed(self, label, receive, *args):
        try:
            receive(*args)
        except Exception as error:  # part of the recorded behaviour
            self.errors.append(f"{label}@{args[0]!r}: {type(error).__name__}: {error}")

    def result(self):
        out = {name: {"intervals": e["intervals"], "sha256": e["sha"].hexdigest()}
               for name, e in sorted(self.signals.items())}
        errors = hashlib.sha256("\n".join(self.errors).encode()).hexdigest()
        out["_errors"] = {"count": len(self.errors), "sha256": errors,
                          "first": self.errors[0] if self.errors else None}
        return out


# ── Signals ───────────────────────────────────────────────────────────────────

def random_samples(seed, n=300, start=0.0, step=(0.1, 2.1), value=(-5.0, 5.0), walk=1.5):
    """n samples (time, value) with irregular time steps and a random-walk value."""
    rng = random.Random(seed)
    t, v = start, value[0] + (value[1] - value[0]) * rng.random()
    samples = []
    for _ in range(n):
        samples.append((t, v))
        t += step[0] + (step[1] - step[0]) * rng.random()
        v = min(value[1], max(value[0], v + walk * (2 * rng.random() - 1)))
    return samples


def stream(recorder, sources):
    """Feed several (label, input node, samples) sources in global time order."""
    events = sorted((t, i, label, node, value)
                    for i, (label, node, samples) in enumerate(sources)
                    for t, value in samples)
    for t, _, label, node, value in events:
        recorder.feed(label, node.receive, t, value)


def interval_sum(intervals):
    total = intervals[0]
    for interval in intervals[1:]:
        total = total + interval
    return total


# ── RV 2025 case studies ──────────────────────────────────────────────────────

def _csv_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        return [[float(x) for x in row] for row in reader]


def rv2025_cgm():
    """CGM case study (examples/RV2025/cgm/cgm.py): TAR, TBR, mean glucose, filtered means."""
    rec = Recorder()
    G = rec.watch("G", VariablePWLNode())
    phi_AR = rec.watch("phi_AR", HigherThanNode(180))
    phi_BR = rec.watch("phi_BR", LowerThanNode(70))
    int_TAR = rec.watch("int_TAR", IntegralWindowNode(180))
    int_TBR = rec.watch("int_TBR", IntegralWindowNode(180))
    phi_TAR = rec.watch("phi_TAR", MultiplyByConst(1 / 180))
    phi_TBR = rec.watch("phi_TBR", MultiplyByConst(1 / 180))
    int_G = rec.watch("int_G", IntegralWindowNode(180))
    mean_G = rec.watch("mean_G", MultiplyByConst(1 / 180))
    filter_AR = rec.watch("filter_G_AR", FilterNode())
    int_AR = rec.watch("int_G_filtered_AR", IntegralWindowNode(180))
    mean_AR = rec.watch("mean_G_filtered_AR", MultiplyByConst(1 / 180))
    filter_BR = rec.watch("filter_G_BR", FilterNode())
    int_BR = rec.watch("int_G_filtered_BR", IntegralWindowNode(180))
    mean_BR = rec.watch("mean_G_filtered_BR", MultiplyByConst(1 / 180))
    G.to(phi_AR.receive); phi_AR.to(int_TAR.receive); int_TAR.to(phi_TAR.receive)
    G.to(phi_BR.receive); phi_BR.to(int_TBR.receive); int_TBR.to(phi_TBR.receive)
    G.to(int_G.receive); int_G.to(mean_G.receive)
    G.to(filter_AR.receive_left); phi_AR.to(filter_AR.receive_right)
    filter_AR.to(int_AR.receive); int_AR.to(mean_AR.receive)
    G.to(filter_BR.receive_left); phi_BR.to(filter_BR.receive_right)
    filter_BR.to(int_BR.receive); int_BR.to(mean_BR.receive)
    for time, glucose in _csv_rows(os.path.join(EXAMPLES, "cgm", "data", "data.csv")):
        rec.feed("G", G.receive, time, glucose)
    return rec.result()


def rv2025_weather():
    """Weather case study (examples/RV2025/weather/weather.py): mean CO2 and temperature, conjunction."""
    rec = Recorder()
    co2 = rec.watch("co2", VariablePWLNode())
    int_co2 = rec.watch("int_co2", IntegralWindowNode(5))
    mean_co2 = rec.watch("mean_co2", MultiplyByConst(1 / 5))
    mean_co2_h = rec.watch("mean_co2_h", HigherThanNode(422))
    temp = rec.watch("temp", VariablePWLNode())
    int_temp = rec.watch("int_temp", IntegralWindowNode(5))
    mean_temp = rec.watch("mean_temp", MultiplyByConst(1 / 5))
    mean_temp_h = rec.watch("mean_temp_h", HigherThanNode(0))
    and_spec = rec.watch("and_spec", MinNode())
    co2.to(int_co2.receive); int_co2.to(mean_co2.receive); mean_co2.to(mean_co2_h.receive)
    temp.to(int_temp.receive); int_temp.to(mean_temp.receive); mean_temp.to(mean_temp_h.receive)
    mean_co2_h.to(and_spec.receive_left); mean_temp_h.to(and_spec.receive_right)
    for time, co2_value, temp_value in _csv_rows(os.path.join(EXAMPLES, "weather", "data", "data.csv")):
        rec.feed("co2", co2.receive, time, co2_value)
        rec.feed("temp", temp.receive, time, temp_value)
    return rec.result()


# ── Synthetic scenarios ───────────────────────────────────────────────────────

INTERPOLATIONS = {"pwc": VariablePWCNode, "pwl": VariablePWLNode}


def synthetic_unary(kind):
    rec = Recorder()
    x = rec.watch("x", INTERPOLATIONS[kind]())
    for name, node in [("higher_than_0.3", HigherThanNode(0.3)), ("lower_than_-0.2", LowerThanNode(-0.2)),
                       ("shift_2.5", ShiftNode(2.5)), ("mult_-0.7", MultiplyByConst(-0.7))]:
        x.to(rec.watch(name, node).receive)
    stream(rec, [("x", x, random_samples(1))])
    return rec.result()


def synthetic_binary(kind):
    # two signals with different, unaligned sampling instants
    rec = Recorder()
    x = rec.watch("x", INTERPOLATIONS[kind]())
    y = rec.watch("y", INTERPOLATIONS[kind]())
    for name, node in [("min", MinNode()), ("max", MaxNode()), ("sum", SumNode()), ("sub", SubNode())]:
        rec.watch(name, node)
        x.to(node.receive_left)
        y.to(node.receive_right)
    y_pos = rec.watch("y_higher_than_0", HigherThanNode(0))
    filtered = rec.watch("filter_x_by_y_pos", FilterNode())
    y.to(y_pos.receive)
    x.to(filtered.receive_left)
    y_pos.to(filtered.receive_right)
    stream(rec, [("x", x, random_samples(2)), ("y", y, random_samples(3, start=0.37))])
    return rec.result()


def synthetic_nary(kind):
    # sum over three signals, two of which start later
    rec = Recorder()
    node = rec.watch("nary_sum", NaryNode(interval_sum))
    sources = []
    for i, start in enumerate((0.0, 0.8, 1.9)):
        x = rec.watch(f"x{i}", INTERPOLATIONS[kind]())
        node.add_receiver(f"x{i}")
        x.to(lambda interval, name=f"x{i}": node.receive(name, interval))
        sources.append((f"x{i}", x, random_samples(10 + i, start=start)))
    stream(rec, sources)
    return rec.result()


def synthetic_windows(kind):
    # each window node gets its own input: an exception raised downstream leaves the
    # input node without its last sample, which would corrupt the other nodes too
    rec = Recorder()
    sources = []
    for name, node in [("integral_1.0", IntegralWindowNode(1.0)), ("integral_3.7", IntegralWindowNode(3.7)),
                       ("integral_20", IntegralWindowNode(20)), ("min_window_2.5", MinWindowNode(2.5)),
                       ("max_window_2.5", MaxWindowNode(2.5)), ("min_window_9", MinWindowNode(9)),
                       ("max_window_9", MaxWindowNode(9))]:
        x = rec.watch(f"x_{name}", INTERPOLATIONS[kind]())
        x.to(rec.watch(name, node).receive)
        sources.append((f"x_{name}", x, random_samples(4)))
    stream(rec, sources)
    return rec.result()


def synthetic_long_windows(kind):
    # long windows over dense sampling: many pieces inside each window
    rec = Recorder()
    sources = []
    for name, node in [("min_window_60", MinWindowNode(60)), ("max_window_60", MaxWindowNode(60)),
                       ("min_window_250", MinWindowNode(250)), ("max_window_250", MaxWindowNode(250)),
                       ("integral_250", IntegralWindowNode(250))]:
        x = rec.watch(f"x_{name}", INTERPOLATIONS[kind]())
        x.to(rec.watch(name, node).receive)
        sources.append((f"x_{name}", x, random_samples(8, n=1500, step=(0.05, 0.6))))
    stream(rec, sources)
    return rec.result()


def synthetic_windows_undefined(kind):
    # windows over a filtered signal, undefined where the filter is off
    rec = Recorder()
    sources = []
    for name, cls in [("min", MinWindowNode), ("max", MaxWindowNode), ("integral", IntegralWindowNode)]:
        x = rec.watch(f"x_{name}", INTERPOLATIONS[kind]())
        y = rec.watch(f"y_{name}", VariablePWCNode())
        y_pos = rec.watch(f"y_pos_{name}", HigherThanNode(-1))
        filtered = rec.watch(f"filtered_{name}", FilterNode())
        window = rec.watch(f"{name}_window_3", cls(3))
        y.to(y_pos.receive)
        x.to(filtered.receive_left)
        y_pos.to(filtered.receive_right)
        filtered.to(window.receive)
        sources += [(f"x_{name}", x, random_samples(12)), (f"y_{name}", y, random_samples(13, start=0.3))]
    stream(rec, sources)
    return rec.result()


def synthetic_composite():
    # a monitor in the style of the paper's formulas: smoothed signal, deviation, thresholds, conjunction
    rec = Recorder()
    x = rec.watch("x", VariablePWLNode())
    y = rec.watch("y", VariablePWCNode())
    integral = rec.watch("integral_x_4", IntegralWindowNode(4))
    mean = rec.watch("mean_x_4", MultiplyByConst(1 / 4))
    deviation = rec.watch("x_minus_mean", SubNode())
    high = rec.watch("deviation_higher_than_1", HigherThanNode(1))
    y_low = rec.watch("y_lower_than_0", LowerThanNode(0))
    both = rec.watch("both", MinNode())
    either = rec.watch("either", MaxNode())
    late = rec.watch("both_shifted_3", ShiftNode(3))
    x.to(integral.receive); integral.to(mean.receive)
    x.to(deviation.receive_left); mean.to(deviation.receive_right)
    deviation.to(high.receive)
    y.to(y_low.receive)
    for node in (both, either):
        high.to(node.receive_left)
        y_low.to(node.receive_right)
    both.to(late.receive)
    stream(rec, [("x", x, random_samples(6)), ("y", y, random_samples(7, start=0.2))])
    return rec.result()


def all_traces():
    traces = {"rv2025_cgm": rv2025_cgm(), "rv2025_weather": rv2025_weather(),
              "synthetic_composite": synthetic_composite()}
    for kind in INTERPOLATIONS:
        for scenario in (synthetic_unary, synthetic_binary, synthetic_nary, synthetic_windows,
                         synthetic_long_windows, synthetic_windows_undefined):
            traces[f"{scenario.__name__}_{kind}"] = scenario(kind)
    return traces
