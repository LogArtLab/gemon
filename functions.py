import math
import numbers
from typing import Tuple, List


class Polynomial:

    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

    @staticmethod
    def undefined() -> 'Polynomial':
        return UndefinedFunction()

    @staticmethod
    def constant(c: numbers.Number) -> 'Polynomial':
        return Polynomial(0, 0, c)

    @staticmethod
    def linear(m: numbers.Number, q: numbers.Number) -> 'Polynomial':
        return Polynomial(0, m, q)

    @staticmethod
    def full(a: numbers.Number, b: numbers.Number, c: numbers.Number) -> 'Polynomial':
        return Polynomial(a, b, c)

    @staticmethod
    def true() -> 'Polynomial':
        return Polynomial(0, 0, 1)

    @staticmethod
    def false() -> 'Polynomial':
        return Polynomial(0, 0, 0)

    def __call__(self, x):
        return self.a * x * x + self.b * x + self.c

    def __sub__(self, other):
        if isinstance(other, numbers.Number):
            return self - Polynomial.constant(other)
        return Polynomial(self.a - other.a, self.b - other.b, self.c - other.c)

    def __add__(self, other):
        if isinstance(other, numbers.Number):
            return self + Polynomial.constant(other)
        return Polynomial(self.a + other.a, self.b + other.b, self.c + other.c)

    def __eq__(self, other: 'Polynomial'):
        return (self.a, self.b, self.c) == (other.a, other.b, other.c)

    def __repr__(self):
        return f"[{self.a}, {self.b},{self.c}]"

    def integral(self) -> 'Polynomial':
        if self.a == 0:
            return Polynomial(self.b / 2, self.c, 0)
        else:
            raise Exception("not possible")

    def add_to_x(self, delta) -> 'Polynomial':
        return Polynomial(self.a, 2 * self.a * delta + self.b, self.a * delta * delta + self.b * delta + self.c)

    def zeros(self) -> List:
        if self.a == 0 and self.b == 0:
            return list()
        if self.a == 0 and self.b != 0:
            return [-self.c / self.b, ]
        else:
            delta = self.b * self.b - 4 * self.a * self.c
            if delta > 0:
                if self.a > 0:
                    return [(-self.b - math.sqrt(delta)) / (2 * self.a), (-self.b + math.sqrt(delta)) / (2 * self.a)]
                else:
                    return [(-self.b + math.sqrt(delta)) / (2 * self.a), (-self.b - math.sqrt(delta)) / (2 * self.a)]
            elif delta == 0:
                return [-self.b / (2 * self.a), ]
            else:
                return list()

    def mult_by_const(self, value):
        return Polynomial(value * self.a, value * self.b, value * self.c)


class UndefinedFunction(Polynomial):

    def __init__(self):
        super().__init__(0, 0, 0)

    def __call__(self, x):
        return None

    def __sub__(self, other):
        return UndefinedFunction()

    def __add__(self, other):
        return UndefinedFunction()

    def __eq__(self, other: 'Polynomial'):
        return isinstance(other, UndefinedFunction)

    def __repr__(self):
        return "[ UND ]"

    def integral(self) -> 'Polynomial':
        return Polynomial.constant(0)

    def add_to_x(self, delta) -> 'Polynomial':
        return UndefinedFunction()

    def zeros(self) -> List:
        return list()
