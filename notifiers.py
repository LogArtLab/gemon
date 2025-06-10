import numpy as np


class Signal:

    def __init__(self):
        self.intervals = []

    def append(self, interval):
        self.intervals.append(interval)

    def get_points(self):
        t = []
        x = []
        for interval in self.intervals:
            if interval.function.a == 0:
                t.append(interval.start)
                x.append(interval.function(interval.start))
                t.append(interval.end)
                x.append(interval.function(interval.end))
            else:
                times = np.linspace(interval.start, interval.end, 20, endpoint=True)
                for time in times:
                    t.append(time)
                    x.append(interval.function(time))
        return t,x


class IntervalNotifier:

    def __init__(self):
        self.observers = []

    def to(self, observer):
        self.observers.append(observer)

    def notify(self, interval):
        for observer in self.observers:
            observer(interval)

    def notify_multiple(self, intervals):
        for interval in intervals:
            self.notify(interval)

    def observe(self):
        signal = Signal()
        self.to(signal.append)
        return signal

class WindowIntervalNotifier:
    def __init__(self):
        self.observers = []

    def to(self, observer):
        self.observers.append(observer)

    def notify_addition(self, interval):
        for observer in self.observers:
            observer.add(interval)

    def notify_move(self, interval_to_remove, interval_to_add):
        for observer in self.observers:
            observer.move(interval_to_remove, interval_to_add)
