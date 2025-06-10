from collections import namedtuple
from typing import Tuple, List

from functions import Polynomial, UndefinedFunction
from notifiers import WindowIntervalNotifier

TimedValue = namedtuple('TimedValue', ['time', 'value'])
EPS = 1e-5


def are_numerically_equivalent(a, b):
    return abs(a - b) < EPS


class IntervalValued:

    def __init__(self, left_extreme: TimedValue, right_extreme: TimedValue):
        self.left_extreme = left_extreme
        self.right_extreme = right_extreme

    def is_left_subset(self, other):
        return other.left_extreme == self.left_extreme and self.right_extreme.time < other.right_extreme.time

    def left_minus(self, other):  # TODO: add test for exception
        if other.right_extreme > self.right_extreme:
            raise Exception("other should be lower than self")
        return IntervalValued(other.right_extreme, self.right_extreme)

    def get_value(self, operator):
        return operator(self.left_extreme[1], self.right_extreme[1])

    def is_prolong_of(self, other):
        return self.left_extreme.time == other.right_extreme.time and self.left_extreme.value == self.right_extreme.value == \
            other.right_extreme.value

    def join_left_of(self, other):
        return IntervalValued(self.left_extreme, other.right_extreme)

    def __eq__(self, other):
        return self.left_extreme == other.left_extreme and self.right_extreme == other.right_extreme


class IntervalQueue:  # TODO: add tests

    def __init__(self):
        self.intervals = []

    def add(self, first: TimedValue, second: TimedValue):
        interval = IntervalValued(first, second)
        if self.is_full() and interval.is_prolong_of(self.intervals[-1]):
            self.intervals[-1] = self.intervals[0].join_left_of(interval)
        else:
            self.intervals.append(interval)

    def remove(self, first, second):
        to_be_removed_interval = IntervalValued(first, second)
        if self.intervals[0] == to_be_removed_interval:
            self.intervals.pop(0)
            return
        if not to_be_removed_interval.is_left_subset(self.intervals[0]):
            raise Exception("Cannot remove an interval that is not a left subset")
        self.intervals[0] = self.intervals[0].left_minus(to_be_removed_interval)

    def is_full(self):
        return len(self.intervals) > 0

    def evaluate(self, operator):
        return operator([interval.get_value(operator) for interval in self.intervals])


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
            if self_left_value < other_left_value:
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
            if self_left_value < other_left_value:
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
        if not zeros:
            return [Interval(self.start, self.end,
                             Polynomial.constant(int(self.function(self.start) > threshold))), ]
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
        if not zeros:
            return [Interval(self.start, self.end,
                             Polynomial.constant(int(self.function(self.start) < threshold))), ]
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


class Intervals:

    def __init__(self):
        self.intervals = []

    def append(self, interval: 'Interval'):
        if len(self.intervals) > 0:
            last_interval = self.intervals[-1]
            if last_interval.function == interval.function:
                self.intervals[-1] = Interval(last_interval.start, interval.end, last_interval.function)
                return
        self.intervals.append(interval)

    def get_first(self):
        return self.intervals[0]

    def remove_first(self):
        return self.intervals.pop(0)

    def replace_first(self, interval: Interval):
        self.intervals[0] = interval


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

    # def __move_old(self):
    #     if self.intervals[0].end - self.wl <= self.intervals[-1].end - self.wr:
    #         delta = self.intervals[0].end - self.wl
    #         to_be_removed = self.intervals.pop(0)
    #         to_be_added = self.intervals[-1].subset(self.wr, self.wr + delta)
    #         self.wr = self.wr + delta
    #         self.wl = self.intervals[0].start
    #         self.notify_move(to_be_removed, to_be_added)
    #     else:
    #         delta = self.intervals[-1].end - self.wr
    #         to_be_removed, to_be_substitute = self.intervals[0].split(delta)
    #         to_be_added = self.intervals[-1].subset(self.wr, self.intervals[-1].end)
    #         self.intervals[0] = to_be_substitute
    #         self.wr = self.intervals[-1].end
    #         self.wl = self.intervals[0].start
    #         self.notify_move(to_be_removed, to_be_added)


# class WindowIntervalOld(WindowIntervalNotifier):
#
#     def __init__(self, length):
#         super().__init__()
#         self.intervals = Intervals()
#         self.acc_length = 0
#         self.right_interval = None
#         self.length = length
#         self.undefined_counter = 0
#
#     def add(self, interval: 'Interval'):
#         interval_length = interval.length()
#         remaining_length = self.length - self.acc_length
#         if interval_length <= remaining_length:
#             self.intervals.append(interval)
#             self.acc_length += interval_length
#             self.notify_addition(interval)
#             return
#         elif remaining_length > 0:
#             to_be_added, interval_to_move = interval.split(remaining_length)
#             self.intervals.append(to_be_added)
#             self.acc_length += to_be_added.length()
#             self.right_interval = interval_to_move
#             self.notify_addition(to_be_added)
#         else:
#             self.right_interval = interval
#         while self.right_interval is not None:
#             self.__move()
#
#     def __move(self):
#         left_interval = self.intervals.get_first()
#         left_interval_length = left_interval.length()
#         right_interval_length = self.right_interval.length()
#         right_minus_left_length = right_interval_length - left_interval_length
#         if right_minus_left_length > 0:
#             to_be_added, self.right_interval = self.right_interval.split(left_interval_length)
#             to_be_removed = self.intervals.remove_first()
#             self.intervals.append(to_be_added)
#             self.notify_move(to_be_removed, to_be_added)
#         elif right_minus_left_length == 0:
#             to_be_added = self.right_interval
#             to_be_removed = self.intervals.remove_first()
#             self.right_interval = None
#             self.intervals.append(to_be_added)
#             self.notify_move(to_be_removed, to_be_added)
#         else:
#             to_be_removed, to_replace_first_of_intervals = left_interval.split(right_interval_length)
#             self.intervals.replace_first(to_replace_first_of_intervals)
#             to_be_added = self.right_interval
#             self.right_interval = None
#             self.intervals.append(to_be_added)
#             self.notify_move(to_be_removed, to_be_added)


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

    def __step(self, added, removed):
        intervals = (added.integral() - (removed.integral()) + Interval(removed.start, removed.end,
                                                                        Polynomial.constant(
                                                                            self.value)),)
        self.value += added.integrate() - removed.integrate()
        return intervals

    def move(self, removed: Interval, added: Interval):
        added_above = added.move_above(removed)
        zeros = removed.zeros(added_above)
        if zeros and removed.end > zeros[0] > removed.start:
            removed_left, removed_right = removed.split(zeros[0] - removed.start)
            added_above_left, added_above_right = added_above.split(zeros[0] - added_above.start)
            return self.__step(added_above_left, removed_left) + self.__step(added_above_right, removed_right)
            # left = added_above_left.integral() - (removed_left.integral()) + Interval(removed_left.start,
            #                                                                           removed_left.end,
            #                                                                           Polynomial.constant(
            #                                                                               self.value))
            # right = added_above_right.integral() - (removed_right.integral()) + Interval(removed_right.start,
            #                                                                              removed_right.end,
            #                                                                              Polynomial.constant(
            #                                                                                  self.value))
            # intervals =  (left, right)

        else:
            return self.__step(added_above, removed)


class Min(WindowOperator):

    def __init__(self):
        self.values = IntervalQueue()

    def add(self, interval: Interval):
        new_values = interval.get_extreme_value_with_time()
        self.values.add(new_values[0], new_values[1])

    def remove(self, removed):
        to_be_removed = removed.get_extreme_value_with_time()
        self.values.remove(to_be_removed[0], to_be_removed[1])

    def move(self, removed: Interval, added: Interval):
        self.remove(removed)
        if self.values.is_full():
            other_minimum = self.values.evaluate(min)
            constant_interval = Interval(removed.start, removed.end, Polynomial.constant(other_minimum))
            first_chunk_intervals = removed.min_interval(constant_interval)
        else:
            first_chunk_intervals = [removed, ]
        min_intervals = []
        added_shifted = added.move_above(removed)
        for interval in first_chunk_intervals:
            min_intervals.extend(interval.min_interval(added_shifted.project_onto(interval)))
        self.add(added)
        return min_intervals

class Min2(WindowOperator):

    def __init__(self):
        self.times = []
        self.values = []

    def add(self, interval: Interval):
        self.times.append(interval.start)
        self.times.append(interval.end)
        self.values.append(interval.function(interval.start))
        self.values.append(interval.function(interval.end))
        pass

    def remove(self, removed):
        c = 0
        while c < len(self.times) and self.times[c] <= removed.end:
            c += 1
        for i in range(c):
            self.times.pop(0)
            self.values.pop(0)

    def move(self, removed: Interval, added: Interval):
        self.remove(removed)
        if removed.is_decreasing():
            removed = Interval(removed.start, removed.end, Polynomial.constant(removed.function(removed.end)))
        if added.is_increasing():
            added = Interval(added.start, added.end, Polynomial.constant(added.function(added.start)))
        if self.times:
            minimum = min(self.values)
            first_chunk_intervals = removed.min_interval(
                Interval(removed.start, removed.end, Polynomial.constant(minimum)))
        else:
            first_chunk_intervals = [removed, ]
        min_intervals = []
        added_shifted = added.move_above(removed)
        for interval in first_chunk_intervals:
            min_intervals.extend(interval.min_interval(added_shifted.project_onto(interval)))
        self.add(added)
        return min_intervals

    # def move_old(self, removed: Interval, added: Interval):
    #     added_left, added_right = added.get_extreme_value()
    #     removed_left, removed_right = removed.get_extreme_value()
    #     if self.min < min(removed_left, removed_right) and self.min < min(added_left, added_right):
    #         self.values.pop(0)
    #         self.values.pop(0)
    #         self.values.append(added_left)
    #         self.values.append(added_right)
    #         self.min = min(self.min, min(added_left, added_right))
    #         return Interval(removed.start, removed.end, Polynomial.constant(self.min))
    #     if self.min == removed_left and removed_right < min(added_left, added_right):
    #         other_minimum = min(self.values[1:])
    #         self.values.pop(0)
    #         self.values.pop(0)
    #         self.values.append(added_left)
    #         self.values.append(added_right)
    #         self.min = min(self.values)
    #         if other_minimum == removed_right:
    #             return removed
    #         else:
    #             return removed.min_interval(Interval(removed.start, removed.end, Polynomial.constant(other_minimum)))
    #
    #     if self.min == removed_left and removed_right > min(added_left, added_right):
    #         # TBD problem.
    #         self.values.pop(0)
    #         self.values.pop(0)
    #         self.values.append(added_left)
    #         self.values.append(added_right)
    #         self.min = min(self.values)
    #         return removed
    #     if self.min == removed_right and self.min < min(added_left, added_right):
    #         self.values.pop(0)
    #         self.values.pop(0)
    #         self.values.append(added_left)
    #         self.values.append(added_right)
    #         self.min = min(self.values)
    #         return Interval(removed.start, removed.end, Polynomial.constant(removed_right))
    #     if self.min > max(added_left, added_right):
    #         self.values.pop(0)
    #         self.values.pop(0)
    #         self.values.append(added_left)
    #         self.values.append(added_right)
    #         self.min = min(self.values)
    #         if added_left < added_right:
    #             return Interval(removed.start, removed.end, added.function)
    #         else:
    #             return Interval(removed.start, removed.end, Polynomial.constant(added_right))
    #     if (self.min < min(removed_left, removed_right) or self.min == removed_right) and min(added_left,
    #                                                                                           added_right) < self.min < max(
    #         added_left,
    #         added_right):
    #         zero = (Polynomial.constant(self.min) - added.function).zeros()[0]  # PASS
    #         if added_left < added_right:
    #             return Interval(removed.start, zero, added.function), Interval(zero, removed.end,
    #                                                                            Polynomial.constant(self.min))
    #         else:
    #             return Interval(removed.start, zero, Polynomial.constant(self.min)), Interval(zero, removed.end,
    #                                                                                           added.function)
    #     if self.min == removed_left and min(added_left, added_right) < self.min < max(added_left, added_right):
    #         pass


# class Max(WindowOperator):  # TODO: unify with min operator
#
#     def __init__(self):
#         self.max = -float('inf')
#         self.values = []
#
#     def add(self, interval: Interval):
#         new_values = interval.get_extreme_value()
#         self.values.append(new_values[0])
#         self.values.append(new_values[1])
#         self.max = max(self.max, max(new_values))
#
#     def move(self, removed: Interval, added: Interval):
#         if len(self.values) > 2:
#             other_maximum = max(self.values[2:])
#             constant_interval = Interval(removed.start, removed.end, Polynomial.constant(other_maximum))
#             first_chunk_intervals = removed.max_interval(constant_interval)
#         else:
#             first_chunk_intervals = [removed, ]
#         min_intervals = []
#         added_shifted = added.move_above(removed)
#         for interval in first_chunk_intervals:
#             min_intervals.extend(interval.max_interval(added_shifted.project_onto(interval)))
#         return min_intervals

class Max(WindowOperator):

    def __init__(self):
        self.values = IntervalQueue()

    def add(self, interval: Interval):
        new_values = interval.get_extreme_value_with_time()
        self.values.add(new_values[0], new_values[1])

    def remove(self, removed):
        to_be_removed = removed.get_extreme_value_with_time()
        self.values.remove(to_be_removed[0], to_be_removed[1])

    def move(self, removed: Interval, added: Interval):
        self.remove(removed)
        if self.values.is_full():
            other_maximum = self.values.evaluate(max)
            constant_interval = Interval(removed.start, removed.end, Polynomial.constant(other_maximum))
            first_chunk_intervals = removed.max_interval(constant_interval)
        else:
            first_chunk_intervals = [removed, ]
        max_intervals = []
        added_shifted = added.move_above(removed)
        for interval in first_chunk_intervals:
            max_intervals.extend(interval.max_interval(added_shifted.project_onto(interval)))
        self.add(added)
        return max_intervals
