from collections import deque, namedtuple
from typing import Tuple, List

from gemon.functions import Polynomial, UndefinedFunction
from gemon.notifiers import WindowIntervalNotifier

TimedValue = namedtuple('TimedValue', ['time', 'value'])
EPS = 1e-5


def are_numerically_equivalent(a, b):
    return abs(a - b) < EPS


class IntervalOperators:
    @staticmethod
    def add():
        return lambda left, right: (left + right,)

    @staticmethod
    def sub():
        return lambda left, right: (left - right,)

    @staticmethod
    def shift(delta):
        return lambda interval: (interval.shift(delta),)

    @staticmethod
    def higher_than(threshold):
        return lambda interval: interval.higher_than(threshold)

    @staticmethod
    def lower_than(threshold):
        return lambda interval: interval.lower_than(threshold)

    @staticmethod
    def max():
        return lambda left, right: left.max_interval(right)

    @staticmethod
    def min():
        return lambda left, right: left.min_interval(right)

    @staticmethod
    def mult_const(value):
        return lambda interval: [Interval(interval.start, interval.end, interval.function.mult_by_const(value)), ]

    @staticmethod
    def filter():
        return lambda left, right: [left if right.function == Polynomial.constant(1) else Interval(left.start, left.end,
                                                                                                   Polynomial.undefined()), ]


class Interval:

    def __init__(self, start: float, end: float, function: Polynomial):
        self.start = start
        self.end = end
        self.function = function

    def length(self) -> float:
        return self.end - self.start

    def split(self, time) -> Tuple['Interval', 'Interval']:
        split_time = self.start + time
        return Interval(self.start, split_time, self.function), Interval(split_time, self.end, self.function)

    def split_at(self, time) -> Tuple['Interval', 'Interval']:
        """Split at the absolute instant time.

        split(time - start) cuts at start + (time - start), which may differ from time
        in the last bit; then intervals that should share a bound do not, and binary
        operators reject them. The cut here is exactly time; when the two agree, the
        value of start + (time - start) is kept (it may be a float where time is an int).
        """
        cut = self.start + (time - self.start)
        if cut != time:
            cut = time
        return Interval(self.start, cut, self.function), Interval(cut, self.end, self.function)

    def subset(self, start, end) -> 'Interval':
        return Interval(start, end, self.function)

    def __repr__(self):
        return f"[{self.start} - {self.end}] | {self.function}"

    def __add__(self, other: 'Interval') -> 'Interval':
        if (self.start, self.end) != (other.start, other.end):
            raise Exception("Cannot sum interval with different bounds")
        return Interval(self.start, self.end, self.function + other.function)

    def __sub__(self, other: 'Interval') -> 'Interval':
        if (self.start, self.end) != (other.start, other.end):
            raise Exception("Cannot subtract interval with different bounds")
        return Interval(self.start, self.end, self.function - other.function)

    def __eq__(self, other: 'Interval'):
        return (are_numerically_equivalent(self.start, other.start)
                and are_numerically_equivalent(self.end, other.end)
                and self.function == other.function
                )

    def integrate(self) -> float:
        integral_function = self.function.integral()
        return integral_function(self.end) - integral_function(self.start)

    def integral(self) -> 'Interval':
        value_in_start = self.function.integral()(self.start)
        return Interval(self.start, self.end, self.function.integral() - Polynomial.constant(value_in_start))

    def move_above(self, interval: 'Interval'):
        delta = self.start - interval.start
        return Interval(interval.start, interval.end, self.function.add_to_x(delta))

    def shift(self, delta: float):
        return Interval(self.start + delta, self.end + delta, self.function.add_to_x(-delta))

    def project_onto(self, other: 'Interval'):
        if self.start > other.start or self.end < other.end:
            raise Exception("Cannot project onto bigger intervals")
        return Interval(other.start, other.end, self.function)

    def zeros(self, interval: 'Interval'):
        zeros = (self.function - interval.function).zeros()
        return [zero for zero in zeros if self.start <= zero <= self.end]

    def apply_operator(self, operator) -> 'Interval':
        return Interval(self.start, self.end, operator(self.function))

    def apply_binary_operator(self, operator, other: 'Interval') -> 'Interval':
        if (self.start, self.end) != (other.start, other.end):
            raise Exception("Cannot apply binary operator between intervals with different bounds")
        return Interval(self.start, self.end, operator(self.function, other.function))

    def get_extreme_value(self) -> Tuple[float, float]:
        return self.function(self.start), self.function(self.end)

    def get_extreme_value_with_time(self) -> Tuple[TimedValue, TimedValue]:
        return TimedValue(self.start, self.function(self.start)), TimedValue(self.end, self.function(self.end))

    def is_increasing(self):
        left_value, right_value = self.get_extreme_value()
        return left_value < right_value

    def is_decreasing(self):
        left_value, right_value = self.get_extreme_value()
        return right_value < left_value

    def is_constant(self):
        left_value, right_value = self.get_extreme_value()
        return right_value == left_value

    def is_undefined(self):
        return isinstance(self.function, UndefinedFunction)

    def min_interval(self, other):
        if (self.start, self.end) != (other.start, other.end):
            raise Exception("Cannot compute the minimum interval of intervals with different bounds")
        self_left_value, self_right_value = self.get_extreme_value()
        other_left_value, other_right_value = other.get_extreme_value()
        zeros = self.zeros(other)
        if not zeros:
            # no crossing: the order is the same on the whole interval; decide at the
            # midpoint (at the left end point the two functions may touch)
            mid_point = (self.start + self.end) / 2
            if self.function(mid_point) < other.function(mid_point):
                return [self, ]
            else:
                return [other, ]
        extended_zeros = []
        if self.start not in zeros:
            extended_zeros += [self.start, ] + zeros
        else:
            extended_zeros.extend(zeros)
        if self.end not in zeros:
            extended_zeros.append(self.end)
        min_interval = []
        for i in range(len(extended_zeros) - 1):
            mid_point = (extended_zeros[i] + extended_zeros[i + 1]) / 2
            if self.function(mid_point) < other.function(mid_point):
                function = self.function
            else:
                function = other.function
            min_interval.append(Interval(extended_zeros[i], extended_zeros[i + 1], function))
        return min_interval

    def max_interval(self, other):  # TODO: unify with min interval
        if (self.start, self.end) != (other.start, other.end):
            raise Exception("Cannot compute the maximum interval of intervals with different bounds")
        self_left_value, self_right_value = self.get_extreme_value()
        other_left_value, other_right_value = other.get_extreme_value()
        zeros = self.zeros(other)
        if not zeros:
            mid_point = (self.start + self.end) / 2  # see min_interval
            if self.function(mid_point) < other.function(mid_point):
                return [other, ]
            else:
                return [self, ]
        extended_zeros = []
        if self.start not in zeros:
            extended_zeros += [self.start, ] + zeros
        else:
            extended_zeros.extend(zeros)
        if self.end not in zeros:
            extended_zeros.append(self.end)
        min_interval = []
        for i in range(len(extended_zeros) - 1):
            mid_point = (extended_zeros[i] + extended_zeros[i + 1]) / 2
            if self.function(mid_point) < other.function(mid_point):
                function = other.function
            else:
                function = self.function
            min_interval.append(Interval(extended_zeros[i], extended_zeros[i + 1], function))
        return min_interval

    def higher_than(self, threshold: float):  # TODO: unify with min interval
        interval = Interval(self.start, self.end, Polynomial.constant(threshold))
        zeros = self.zeros(interval)
        if not zeros:  # decided at the midpoint, see min_interval
            return [Interval(self.start, self.end,
                             Polynomial.constant(int(self.function((self.start + self.end) / 2) > threshold))), ]
        extended_zeros = []
        if self.start not in zeros:
            extended_zeros += [self.start, ] + zeros
        else:
            extended_zeros.extend(zeros)
        if self.end not in zeros:
            extended_zeros.append(self.end)
        filtered_interval = []
        for i in range(len(extended_zeros) - 1):
            mid_point = (extended_zeros[i] + extended_zeros[i + 1]) / 2
            filtered_interval.append(
                Interval(extended_zeros[i], extended_zeros[i + 1],
                         Polynomial.constant(int(self.function(mid_point) > threshold))))
        return filtered_interval

    def lower_than(self, threshold: float):  # TODO: unify with min interval
        interval = Interval(self.start, self.end, Polynomial.constant(threshold))
        zeros = self.zeros(interval)
        if not zeros:  # decided at the midpoint, see min_interval
            return [Interval(self.start, self.end,
                             Polynomial.constant(int(self.function((self.start + self.end) / 2) < threshold))), ]
        extended_zeros = []
        if self.start not in zeros:
            extended_zeros += [self.start, ] + zeros
        else:
            extended_zeros.extend(zeros)
        if self.end not in zeros:
            extended_zeros.append(self.end)
        filtered_interval = []
        for i in range(len(extended_zeros) - 1):
            mid_point = (extended_zeros[i] + extended_zeros[i + 1]) / 2
            filtered_interval.append(
                Interval(extended_zeros[i], extended_zeros[i + 1],
                         Polynomial.constant(int(self.function(mid_point) < threshold))))
        return filtered_interval


class Memory:

    def __init__(self):
        super().__init__()
        self.observers = dict()
        self.memory = dict()

    def add_computation(self, from_variable, computation):
        if from_variable in self.observers:
            self.observers[from_variable].append(computation)
        else:
            self.observers[from_variable] = [computation, ]

    def receive(self, variable, interval):
        self.memory[variable] = interval
        for computation in self.observers.get(variable, []):
            computation(interval)

    def get_value(self, variable):
        return self.memory.get(variable, None)

    def add_unary_node(self, from_variable, to_variable, node):
        self.add_computation(from_variable, node.receive)
        node.to(lambda interval: self.receive(to_variable, interval))

    def add_binary_node(self, from_variable_left, from_variable_right, to_variable, node):
        self.add_computation(from_variable_left, node.receive_left)
        self.add_computation(from_variable_right, node.receive_right)
        node.to(lambda interval: self.receive(to_variable, interval))

    def add_nary_node(self, from_variable_list: List[str], to_variable, node):
        for from_variable in from_variable_list:
            node.add_receiver(from_variable)
            self.add_computation(from_variable,
                                 lambda interval, variable=from_variable: node.receive(variable, interval))
        node.to(lambda interval: self.receive(to_variable, interval))


class WindowInterval(WindowIntervalNotifier):

    def __init__(self, length: float):
        super().__init__()
        self.wr = None
        self.wl = None
        self.length = length
        self.intervals = []

    def add(self, interval: 'Interval'):
        self.intervals.append(interval)
        if self.wr is None:
            self.wr = interval.start
            self.wl = interval.start
        if self.wr - self.wl + interval.length() <= self.length:
            self.wr += interval.length()
            self.notify_addition(interval)
        else:
            self.notify_addition(interval.subset(self.wr, self.wl + self.length))
            self.wr = self.wl + self.length
            while not are_numerically_equivalent(self.wr, self.intervals[-1].end):
                self.__move()

    def __move(self):
        delta = min(self.intervals[0].end - self.wl, self.intervals[-1].end - self.wr, self.length)
        if delta < self.intervals[0].end - self.wl:
            to_be_removed, to_be_substitute = self.intervals[0].split(delta)
            to_be_added = self.intervals[-1].subset(self.wr, self.wr + delta)
            self.intervals[0] = to_be_substitute
        else:
            to_be_removed = self.intervals.pop(0)
            to_be_added = self.intervals[-1].subset(self.wr, self.wr + delta)
        self.wr = self.wr + delta
        self.wl = self.intervals[0].start
        self.notify_move(to_be_removed, to_be_added)


class WindowOperator:
    def add(self, interval: Interval):
        pass

    def move(self, removed: Interval, added: Interval):
        pass


class Integral(WindowOperator):
    def __init__(self):
        super().__init__()
        self.value = 0

    def add(self, interval: Interval):
        self.value += interval.integrate()

    def move(self, removed: Interval, added: Interval):
        added_above = added.move_above(removed)
        removed_integral = removed.function.integral()
        added_integral = added_above.function.integral()
        function = Polynomial.constant(self.value + removed_integral(removed.start) - added_integral(
            added_above.start)) + added_integral - removed_integral
        self.value = function(removed.end)
        return (Interval(removed.start, removed.end, function),)


# ── Sliding-window minimum / maximum ──────────────────────────────────────────
# Exact for piecewise polynomials of degree <= 2. The output at t is the minimum
# (maximum) of the signal over the window [t, t + length], like Integral.

def _vertex(f: Polynomial):
    return -f.b / (2 * f.a)


def _min_on(f: Polynomial, start, end):
    """Minimum of f on [start, end]."""
    values = [f(start), f(end)]
    if f.a > 0 and start < _vertex(f) < end:
        values.append(f(_vertex(f)))
    return min(values)


def _min_pair(left: Interval, right: Interval) -> List[Interval]:
    """Pointwise minimum of two functions on the same interval. Cuts at the crossings
    strictly inside and picks each piece by its midpoint (deciding at the left end
    point is wrong when the functions touch there)."""
    start, end = left.start, left.end
    crossings = sorted(z for z in (left.function - right.function).zeros() if start < z < end)
    points = [start] + crossings + [end]
    result = []
    for t0, t1 in zip(points, points[1:]):
        mid = (t0 + t1) / 2
        function = left.function if left.function(mid) <= right.function(mid) else right.function
        result.append(Interval(t0, t1, function))
    return result


def _suffix_min(f: Polynomial, start, end) -> List[Interval]:
    """h(t) = min of f on [t, end], for t in [start, end]."""
    if f.a == 0:
        if f.b >= 0:  # non-decreasing: the minimum is at t
            return [Interval(start, end, f)]
        return [Interval(start, end, Polynomial.constant(f(end)))]
    if f.a < 0:  # concave: the minimum is at an end point
        return _min_pair(Interval(start, end, f), Interval(start, end, Polynomial.constant(f(end))))
    v = _vertex(f)  # convex
    if v >= end:
        return [Interval(start, end, Polynomial.constant(f(end)))]
    if v <= start:
        return [Interval(start, end, f)]
    return [Interval(start, v, Polynomial.constant(f(v))), Interval(v, end, f)]


def _prefix_min(f: Polynomial, start, end) -> List[Interval]:
    """h(t) = min of f on [start, t], for t in [start, end]."""
    if f.a == 0:
        if f.b <= 0:  # non-increasing: the minimum is at t
            return [Interval(start, end, f)]
        return [Interval(start, end, Polynomial.constant(f(start)))]
    if f.a < 0:
        return _min_pair(Interval(start, end, f), Interval(start, end, Polynomial.constant(f(start))))
    v = _vertex(f)
    if v <= start:
        return [Interval(start, end, Polynomial.constant(f(start)))]
    if v >= end:
        return [Interval(start, end, f)]
    return [Interval(start, v, f), Interval(v, end, Polynomial.constant(f(v)))]


def _pointwise_min(left: List[Interval], right: List[Interval]) -> List[Interval]:
    """Pointwise minimum of two piecewise functions on the same domain."""
    cuts = sorted({i.start for i in left} | {i.end for i in left} | {i.start for i in right} | {i.end for i in right})
    result = []
    li = ri = 0
    for t0, t1 in zip(cuts, cuts[1:]):
        while left[li].end <= t0:
            li += 1
        while right[ri].end <= t0:
            ri += 1
        result.extend(_min_pair(Interval(t0, t1, left[li].function), Interval(t0, t1, right[ri].function)))
    return result


class WindowExtremum(WindowOperator):
    """Minimum (minimum=True) or maximum of the signal over the window [t, t + length].

    The window content is kept as a queue of pieces. When the window moves, the output
    on the time span of the removed piece is the minimum of three terms: the minimum
    of the removed piece from t to its end, the minimum of the content in between,
    and the minimum of the added piece from its start to t + length. The maximum is
    computed as the opposite of the minimum of the opposite signal. A window touching
    an undefined piece gives an undefined output.

    The minimum of the content in between comes from a monotonic queue (Lemire's
    sliding-window minimum): the minima of the pieces after the first one, increasing
    from front to back, so that the front holds their minimum. The first piece is
    kept out of it because it is the one that gets shortened as the window moves.
    Each piece enters and leaves the queue once: amortised O(1) per move.
    """

    def __init__(self, minimum: bool = True):
        self.sign = 1 if minimum else -1
        self.pieces = deque()   # window content
        self.minima = deque()   # (piece, minimum) for pieces[1:], minima increasing
        self.undefined = 0      # undefined pieces in the content

    def _signed(self, function: Polynomial) -> Polynomial:
        return function if self.sign == 1 else function.mult_by_const(-1)

    def _append(self, piece: Interval):
        if piece.is_undefined():
            self.undefined += 1
        elif self.pieces:
            value = _min_on(self._signed(piece.function), piece.start, piece.end)
            while self.minima and self.minima[-1][1] >= value:
                self.minima.pop()
            self.minima.append((piece, value))
        self.pieces.append(piece)

    def _pop_front(self):
        if self.pieces.popleft().is_undefined():
            self.undefined -= 1
        if self.pieces and self.minima and self.minima[0][0] is self.pieces[0]:
            self.minima.popleft()  # the new first piece leaves the monotonic queue

    def add(self, interval: Interval):
        self._append(interval)

    def move(self, removed: Interval, added: Interval):
        start, end = removed.start, removed.end
        tolerance = 1e-9 * max(1.0, abs(end))
        while self.pieces and self.pieces[0].end <= end + tolerance:
            self._pop_front()
        if self.pieces and self.pieces[0].start < end - tolerance:
            first = self.pieces[0]
            self.pieces[0] = Interval(end, first.end, first.function)
        # self.pieces is now the content between the removed and the added piece
        if removed.is_undefined() or added.is_undefined() or self.undefined:
            self._append(added)
            return [Interval(start, end, Polynomial.undefined())]
        outgoing = _suffix_min(self._signed(removed.function), start, end)
        incoming = _prefix_min(self._signed(added.move_above(removed).function), start, end)
        result = _pointwise_min(outgoing, incoming)
        if self.pieces:
            first = self.pieces[0]
            m = _min_on(self._signed(first.function), first.start, first.end)
            if self.minima:
                m = min(m, self.minima[0][1])
            result = [piece for r in result
                      for piece in _min_pair(r, Interval(r.start, r.end, Polynomial.constant(m)))]
        self._append(added)
        if self.sign == -1:
            result = [Interval(r.start, r.end, r.function.mult_by_const(-1)) for r in result]
        return result
