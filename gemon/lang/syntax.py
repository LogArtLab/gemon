"""Abstract syntax of the gemon specification language.

Two layers:

- the *surface* tree (Number, Ref, Binary, ...) produced by the parser, one class per
  construct of the grammar, with the source position of each node;
- the *core* tree (Input, Sum, AddConst, ...) produced by the lowering in
  compiler.py, one class per gemon node. Core nodes are frozen and compared by
  structure, so equal sub-formulas are the same dictionary key: the compiler builds
  one gemon node per distinct core node (common sub-expressions are shared).

Positions are excluded from equality and hashing.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class Position:
    line: int
    column: int

    def __str__(self):
        return f"line {self.line}, column {self.column}"


def _position():
    return field(default=None, compare=False, repr=False)


# ── Surface syntax ────────────────────────────────────────────────────────────

class Expr:
    position: Optional[Position]


@dataclass(frozen=True)
class Number(Expr):
    value: object                  # int or float, as written (after the time unit)
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class Bool(Expr):
    value: bool
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class Ref(Expr):
    name: str
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class Unary(Expr):
    op: str                        # "neg", "not", "abs"
    operand: Expr
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class Binary(Expr):
    op: str                        # "+", "-", "*", "/", "and", "or", "min", "max"
    left: Expr
    right: Expr
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class Compare(Expr):
    op: str                        # "<", ">", "<=", ">="
    left: Expr
    right: Expr
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class Window(Expr):
    tag: str                       # "Int", "Min", "Max"
    lower: Expr
    upper: Expr
    operand: Expr
    condition: Optional[Expr] = None
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class InputDecl:
    name: str
    interpolation: str             # "const" or "linear"
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class ParamDecl:
    name: str
    value: Expr
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class Definition:
    name: str
    expr: Expr
    position: Optional[Position] = _position()


@dataclass(frozen=True)
class Program:
    timeunit: str                  # base unit of the timestamps
    items: Tuple[object, ...]      # InputDecl, ParamDecl, Definition, in source order


# ── Core syntax: one class per gemon node ────────────────────────────────────

class Core:
    pass


def _number_key(value):
    # 180 and 180.0 are equal in Python but give different gemon nodes (the bounds
    # of the intervals are printed differently): the type is part of the key.
    return type(value).__name__, value


@dataclass(frozen=True)
class Input(Core):
    name: str
    interpolation: str


@dataclass(frozen=True)
class Sum(Core):
    left: Core
    right: Core


@dataclass(frozen=True)
class Sub(Core):
    left: Core
    right: Core


@dataclass(frozen=True)
class AddConst(Core):
    operand: Core
    value: object

    def __eq__(self, other):
        return (type(other) is AddConst and self.operand == other.operand
                and _number_key(self.value) == _number_key(other.value))

    def __hash__(self):
        return hash(("AddConst", self.operand, _number_key(self.value)))


@dataclass(frozen=True)
class Scale(Core):
    operand: Core
    value: object

    def __eq__(self, other):
        return (type(other) is Scale and self.operand == other.operand
                and _number_key(self.value) == _number_key(other.value))

    def __hash__(self):
        return hash(("Scale", self.operand, _number_key(self.value)))


@dataclass(frozen=True)
class Threshold(Core):
    op: str                        # ">" (HigherThanNode) or "<" (LowerThanNode)
    operand: Core
    value: object

    def __eq__(self, other):
        return (type(other) is Threshold and self.op == other.op and self.operand == other.operand
                and _number_key(self.value) == _number_key(other.value))

    def __hash__(self):
        return hash(("Threshold", self.op, self.operand, _number_key(self.value)))


@dataclass(frozen=True)
class Not(Core):
    operand: Core


@dataclass(frozen=True)
class And(Core):
    left: Core
    right: Core


@dataclass(frozen=True)
class Or(Core):
    left: Core
    right: Core


@dataclass(frozen=True)
class Abs(Core):
    operand: Core


@dataclass(frozen=True)
class PointMin(Core):
    left: Core
    right: Core


@dataclass(frozen=True)
class PointMax(Core):
    left: Core
    right: Core


@dataclass(frozen=True)
class Filter(Core):
    operand: Core
    condition: Core


@dataclass(frozen=True)
class SlidingWindow(Core):
    tag: str                       # "Int", "Min", "Max"
    length: object
    operand: Core

    def __eq__(self, other):
        return (type(other) is SlidingWindow and self.tag == other.tag and self.operand == other.operand
                and _number_key(self.length) == _number_key(other.length))

    def __hash__(self):
        return hash(("SlidingWindow", self.tag, self.operand, _number_key(self.length)))


@dataclass(frozen=True)
class Shift(Core):
    operand: Core
    delta: object

    def __eq__(self, other):
        return (type(other) is Shift and self.operand == other.operand
                and _number_key(self.delta) == _number_key(other.delta))

    def __hash__(self):
        return hash(("Shift", self.operand, _number_key(self.delta)))
