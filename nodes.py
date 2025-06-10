from elements import Interval, WindowOperator, Integral, Min, Max, IntervalOperators, WindowInterval, \
    Min2
from functions import Polynomial, UndefinedFunction
from notifiers import IntervalNotifier


class VariablePWLNode(IntervalNotifier):

    def __init__(self):
        super().__init__()
        self.time = None
        self.value = None

    def receive(self, time, value):
        if self.time is not None:
            m = (value - self.value) / (time - self.time)
            q = self.value - self.time * m
            self.notify(Interval(self.time, time, Polynomial.linear(m, q)))
        self.time = time
        self.value = value


class VariablePWCNode(IntervalNotifier):

    def __init__(self):
        super().__init__()
        self.time = None
        self.value = None

    def receive(self, time, value):
        if self.time is not None:
            self.notify(Interval(self.time, time, Polynomial.constant(self.value)))
        self.time = time
        self.value = value


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
            right_left, right_right = right.split(left.end - right.start)
            self.right[0] = right_right
            self.left.pop(0)
            self.notify_multiple(self.operator(left, right_left))
            # self.notify(left.apply_binary_operator(self.operator, right_left))
        elif right.end < left.end:
            left_left, left_right = left.split(right.end - left.start)
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
        end = [l[0].end for l in self.locations.values()]
        min_starts = min(starts)
        max_starts = max(starts)
        if min_starts != max_starts:
            self.notify(Interval(min_starts, max_starts, Polynomial.undefined()))
            for l in self.locations:
                l[0] = l[0].split(max_starts - min_starts)[1]
        min_end = min(end)
        cut = []
        for l in self.locations.values():
            l_end = l[0].end
            if l_end > min_end:
                l_left, l_right = l[0].split(min_end - l[0].start)
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
        super().__init__(WindowInterval(length), Min2())

class MaxWindowNode(WindowNode):
    def __init__(self, length: float):
        super().__init__(WindowInterval(length), Max())

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


class MinOptimalWindowNode(IntervalNotifier):

    def __init__(self, length: float):
        super().__init__()
        self.length = length
        self.intervals = []

    def receive(self, add_interval: 'Interval'):
        vout = []
        if not self.intervals:
            window_length = 0 
        else:
            window_length = self.intervals[-1].end - self.intervals[0].start
        to_slide = add_interval.length() - (self.length - window_length)
        if add_interval.is_increasing():
            value = add_interval.function(add_interval.start)
        else:
            value = add_interval.function(add_interval.end)
        while self.intervals and self.intervals[-1].function(self.intervals[-1].start)>value:
            self.intervals.pop()
            if self.intervals:
                zeros = (self.intervals[-1].function - Polynomial.constant(value)).zeros()
                if zeros:
                    zero = zeros[0]
                    left, right = self.intervals[0].split(zero)
                    self.intervals[-1] = left
                    self.intervals.append(Interval(left.end, add_interval.start, Polynomial.constant(value)))
                else:
                    self.intervals.append(Interval(self.intervals[0].end, add_interval.start, Polynomial.constant(value)))
        new_add_interval = Interval(add_interval.start, add_interval.end, Polynomial.constant(value))
        self.intervals.append(new_add_interval)
        if to_slide>0:
            first_state_length = self.intervals[0].length()
            while first_state_length <= to_slide:
                vout.append(self.intervals.pop(0))
                to_slide -= first_state_length
                first_state_length = self.intervals[0].length()
            if to_slide>0:
                left , right = self.intervals[0].split(self.intervals[0].start + to_slide)
                vout.append(left)
                self.intervals[0] = right
        if vout:
            self.notify_multiple(vout)


class MonotonicEdge:

    def __init__(self):
        self.intervals = []

    def add(self, interval:Interval):
        start = None
        if interval.is_increasing():
            value = interval.function(interval.start)
            new_interval = interval
        else:
            value = interval.function(interval.end)
            new_interval = Interval(interval.start, interval.end, Polynomial.constant(value))
        while self.intervals and self.intervals[-1].function(self.intervals[-1].start) > value:
            removed = self.intervals.pop()
            start = removed.start
        if self.intervals:
            zeros = (self.intervals[-1].function - Polynomial.constant(value)).zeros()
            if zeros:
                zero = zeros[0]
                left, right = self.intervals[0].split(zero)
                self.intervals[-1] = left
                start = left.end
        if start is not None and start != new_interval.start:
            self.intervals.append(Interval(start,new_interval.start,Polynomial.constant(value)))
        self.intervals.append(new_interval)

    def remove(self, length:float):
        removed = []
        partial = 0
        while partial<length:
            candidate = self.intervals.pop(0)
            if candidate.length() <= length-partial:
                removed.append(candidate)
                partial += candidate.length()
            else:
                cut = length - partial
                left, right = candidate.split(cut)
                removed.append(left)
                self.intervals.insert(0,right)
                partial = length
        return removed



class MinOptimalWindowNode2(IntervalNotifier):

    def __init__(self, length: float):
        super().__init__()
        self.length = length
        self.intervals = []
        self.start_window = None
        self.end_window = None

    def receive(self, add_interval: 'Interval'):
        if add_interval.is_increasing():
            value = add_interval.function(add_interval.start)
        else:
            value = add_interval.function(add_interval.end)
        new_add_interval = Interval(add_interval.start, add_interval.end, Polynomial.constant(value))
        while self.intervals and self.intervals[-1].function(self.intervals[-1].start) > value:
            self.intervals.pop()
        if self.intervals:
            zeros = (self.intervals[-1].function - Polynomial.constant(value)).zeros()
            if zeros:
                zero = zeros[0]
                left, right = self.intervals[0].split(zero)
                self.intervals[-1] = left
                time = left.end
            else:
                time = self.intervals[0].end
            self.intervals.append(Interval(time, new_add_interval.start, Polynomial.constant(value)))
            self.intervals.append(new_add_interval)
            self.end_window = new_add_interval.end
        else:
            if self.start_window is None:
                self.intervals.append(new_add_interval)
                self.start_window = new_add_interval.start
                self.end_window = new_add_interval.end
            else:
                self.intervals.append(Interval(self.start_window, new_add_interval.start, Polynomial.constant(value)))
                self.intervals.append(new_add_interval)
                self.end_window = new_add_interval.end
        to_slide = self.intervals[-1].end - self.start_window - self.length
        vout=[]
        while to_slide>0:
            first_state_length = self.intervals[0].length()
            while first_state_length <= to_slide:
                remove = self.intervals.pop(0)
                vout.append(remove)
                to_slide -= first_state_length
                self.start_window = remove.end
            if to_slide>0:
                left, right = self.intervals[0].split(self.intervals[0].start + to_slide)
                vout.append(left)
                self.intervals[0] = right
                to_slide = 0
                self.start_window = left.end
        if vout:
            self.notify_multiple(vout)