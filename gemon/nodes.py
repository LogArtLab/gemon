from gemon.elements import Interval, WindowOperator, Integral, Max, IntervalOperators, WindowInterval, \
    Min2, WindowExtremum
from gemon.functions import Polynomial
from gemon.notifiers import IntervalNotifier


class VariablePWLNode(IntervalNotifier):

    def __init__(self):
        super().__init__()
        self.time = None
        self.value = None

    def receive(self, time, value):
        # the state is updated before notifying: if a downstream node raises, the
        # sample is not lost and the next interval still starts at this one
        previous_time, previous_value = self.time, self.value
        self.time = time
        self.value = value
        if previous_time is not None:
            m = (value - previous_value) / (time - previous_time)
            q = previous_value - previous_time * m
            self.notify(Interval(previous_time, time, Polynomial.linear(m, q)))


class VariablePWCNode(IntervalNotifier):

    def __init__(self):
        super().__init__()
        self.time = None
        self.value = None

    def receive(self, time, value):
        # state updated before notifying, as in VariablePWLNode
        previous_time, previous_value = self.time, self.value
        self.time = time
        self.value = value
        if previous_time is not None:
            self.notify(Interval(previous_time, time, Polynomial.constant(previous_value)))


class VariableNode(IntervalNotifier):

    def __init__(self):
        super().__init__()

    def receive(self, interval: 'Interval'):
        self.notify(interval)


class UnaryNode(IntervalNotifier):

    def __init__(self, operator):
        super().__init__()
        self.operator = operator

    def receive(self, input_interval: 'Interval'):
        output_intervals = self.operator(input_interval)
        self.notify_multiple(output_intervals)


class BinaryNode(IntervalNotifier):

    def __init__(self, operator):
        super().__init__()
        self.left = []
        self.right = []
        self.operator = operator

    def __merge(self):
        right = self.right[0]
        left = self.left[0]
        if right.start < left.start:
            self.notify(Interval(right.start, left.start, Polynomial.undefined()))
            right.start = left.start
        elif left.start < right.start:
            self.notify(Interval(left.start, right.start, Polynomial.undefined()))
            left.start = right.start
        elif left.end < right.end:
            right_left, right_right = right.split_at(left.end)
            self.right[0] = right_right
            self.left.pop(0)
            self.notify_multiple(self.operator(left, right_left))
            # self.notify(left.apply_binary_operator(self.operator, right_left))
        elif right.end < left.end:
            left_left, left_right = left.split_at(right.end)
            self.left[0] = left_right
            self.right.pop(0)
            self.notify_multiple(self.operator(left_left, right))
            # self.notify(left_left.apply_binary_operator(self.operator, right))
        else:
            self.left.pop(0)
            self.right.pop(0)
            self.notify_multiple(self.operator(left, right))
            # self.notify(left.apply_binary_operator(self.operator, right))

    def receive_left(self, interval: 'Interval'):
        self.left.append(interval)
        while len(self.left) > 0 and len(self.right) > 0:
            self.__merge()

    def receive_right(self, interval: 'Interval'):
        self.right.append(interval)
        while len(self.left) > 0 and len(self.right) > 0:
            self.__merge()


class NaryNode(IntervalNotifier):

    def __init__(self, operator):
        super().__init__()
        self.locations = dict()
        self.operator = operator

    # def __get_location_from_name(self, location_name):
    #     if location_name not in self.locations:
    #         self.locations[location_name] = []
    #     return self.locations[location_name]

    def __should_merge(self):
        for locations in self.locations.values():
            if not locations:
                return False
        return True

    def add_receiver(self, location_name):
        self.locations[location_name] = []

    def receive(self, location_name, interval):
        locations = self.locations[location_name]
        locations.append(interval)
        while self.__should_merge():
            self.__merge()

    def __merge(self):
        starts = [l[0].start for l in self.locations.values()]
        min_starts = min(starts)
        max_starts = max(starts)
        if min_starts != max_starts:
            self.notify(Interval(min_starts, max_starts, Polynomial.undefined()))
            for l in self.locations.values():
                if l[0].start < max_starts:
                    l[0] = l[0].split_at(max_starts)[1]
        min_end = min(l[0].end for l in self.locations.values())
        cut = []
        for l in self.locations.values():
            l_end = l[0].end
            if l_end > min_end:
                l_left, l_right = l[0].split_at(min_end)
                cut.append(l_left)
                l[0] = l_right
            else:
                cut.append(l.pop(0))
        self.notify(self.operator(cut))


class WindowNode(IntervalNotifier):
    def __init__(self, window: WindowInterval, window_operator: WindowOperator):
        super().__init__()
        window.to(self)
        self.window = window
        self.window_operator = window_operator

    def add(self, interval: Interval):
        self.window_operator.add(interval)

    def move(self, removed: Interval, added: Interval):
        results = self.window_operator.move(removed, added)
        for result in results:
            self.notify(result)

    def receive(self, interval: Interval):
        self.window.add(interval)


# class IntegralNode(IntervalNotifier):
#     def __init__(self, window: WindowInterval):
#         super().__init__()
#         window.to(self)
#         self.window = window
#         self.integral = Integral()
#
#     def add(self, interval: Interval):
#         self.integral.add(interval)
#
#     def move(self, removed: Interval, added: Interval):
#         results = self.integral.move(removed, added)
#         for result in results:
#             self.notify(result)
#
#     def receive(self, interval: Interval):
#         self.window.add(interval)
#
#     def get_name(self):
#         return f"INTEGRAL[{self.window.length}]"


# class MinNode(IntervalNotifier):
#     def __init__(self, window: WindowInterval):
#         super().__init__()
#         window.to(self)
#         self.window = window
#         self.min = Min()
#
#     def add(self, interval: Interval):
#         self.min.add(interval)
#
#     def move(self, removed: Interval, added: Interval):
#         results = self.min.move(removed, added)
#         for result in results:
#             self.notify(result)
#
#     def receive(self, interval: Interval):
#         self.window.add(interval)


# class ShiftNode(IntervalNotifier):
#     def __init__(self, delta: float):
#         super().__init__()
#         self.delta = delta
#
#     def receive(self, interval: Interval):
#         self.notify(interval.shift(self.delta))

#
# class FilterNode(BinaryNode):
#
#     def __init__(self):
#         operator = lambda signal, filter_signal: signal if filter_signal == Polynomial.constant(
#             1) else Polynomial.undefined()
#         super().__init__(operator)


# class HigherThanNode(IntervalNotifier):
#
#     def __init__(self, threshold):
#         super().__init__()
#         self.threshold = threshold
#
#     def receive(self, interval: Interval):
#         if not isinstance(interval.function, UndefinedFunction):  # TODO: fix me
#             filtered_intervals = interval.higher_than(self.threshold)
#             for filtered_interval in filtered_intervals:
#                 self.notify(filtered_interval)
#
#     def get_name(self):
#         return f"HIGHER_THAN[{self.threshold}]"


# class AndNode(BinaryNode):
#     def __init__(self):
#         super().__init__(max)
#
#
# class OrNode(BinaryNode):
#     def __init__(self):
#         super().__init__(min)
#
#
# class NotNode(UnaryNode):
#     def __init__(self):
#         super().__init__(lambda value: -value)
#
#
# class Finally(WindowNode):
#
#     def __init__(self, length):
#         super().__init__(WindowInterval(length), Max())
#
#
# class Globally(WindowNode):
#
#     def __init__(self, length):
#         super().__init__(WindowInterval(length), Min())


class IntegralWindowNode(WindowNode):
    def __init__(self, length: float):
        super().__init__(WindowInterval(length), Integral())


class MinWindowNode(WindowNode):
    def __init__(self, length: float):
        super().__init__(WindowInterval(length), WindowExtremum(minimum=True))


class MaxWindowNode(WindowNode):
    def __init__(self, length: float):
        super().__init__(WindowInterval(length), WindowExtremum(minimum=False))


class MinNode(BinaryNode):
    def __init__(self):
        super().__init__(IntervalOperators.min())


class MaxNode(BinaryNode):
    def __init__(self):
        super().__init__(IntervalOperators.max())


class SumNode(BinaryNode):
    def __init__(self):
        super().__init__(IntervalOperators.add())


class SubNode(BinaryNode):
    def __init__(self):
        super().__init__(IntervalOperators.sub())


class HigherThanNode(UnaryNode):
    def __init__(self, threshold):
        super().__init__(IntervalOperators.higher_than(threshold))


class LowerThanNode(UnaryNode):
    def __init__(self, threshold):
        super().__init__(IntervalOperators.lower_than(threshold))


class ShiftNode(UnaryNode):
    def __init__(self, delta):
        super().__init__(IntervalOperators.shift(delta))


class MultiplyByConst(UnaryNode):
    def __init__(self, value):
        super().__init__(IntervalOperators.mult_const(value))


class FilterNode(BinaryNode):
    def __init__(self):
        super().__init__(IntervalOperators.filter())
