"""Compiler of the gemon specification language: surface syntax -> gemon nodes.

Two passes:

1. Lower (class Lowering): resolve names, fold constants, check types and degrees,
   and rewrite every construct into core syntax (syntax.Core), one core node per
   gemon node. Equal sub-formulas give equal core nodes.
2. Build (class Builder): create one gemon node per distinct core node and wire it
   to the nodes of its operands. Shared sub-formulas are built once.

Typing. Every expression is a constant (int/float/bool, folded at compile time) or a
signal. A signal is boolean (0/1: comparisons, and/or/not and their windows) or
numeric, and has a polynomial degree: 0 for piecewise-constant inputs and booleans,
1 for linear inputs. Int raises the degree by one; gemon represents degree <= 2
exactly, so a formula of higher degree is rejected.
"""

from dataclasses import dataclass

from gemon.lang import syntax as S
from gemon.lang.errors import LangError
from gemon.lang.parser import parse
from gemon.nodes import (AbsNode, AddConstNode, AndNode, FilterNode, HigherThanNode, IntegralWindowNode,
                         LowerThanNode, MaxNode, MaxWindowNode, MinNode, MinWindowNode, MultiplyByConst, NotNode,
                         OrNode, ShiftNode, SubNode, SumNode, VariablePWCNode, VariablePWLNode)

MAX_DEGREE = 2


@dataclass(frozen=True)
class Signal:
    """A lowered signal expression: its core node, whether it is boolean, its degree."""
    core: S.Core
    boolean: bool
    degree: int


def _is_const(value):
    return not isinstance(value, Signal)


def _describe(value):
    if isinstance(value, bool):
        return "the boolean constant " + ("true" if value else "false")
    return f"the constant {value!r}"


class Lowering:
    """Surface syntax -> core syntax, with name resolution, constant folding and checks."""

    def __init__(self, program: S.Program):
        self.program = program
        self.inputs = {}        # name -> Signal
        self.params = {}        # name -> constant
        self.definitions = {}   # name -> Signal (in source order)

    # entry point
    def run(self):
        for item in self.program.items:
            self.declare(item)
        return self

    def declare(self, item):
        if isinstance(item, S.InputDecl):
            self._new_name(item.name, item.position)
            degree = 1 if item.interpolation == "linear" else 0
            self.inputs[item.name] = Signal(S.Input(item.name, item.interpolation), False, degree)
        elif isinstance(item, S.ParamDecl):
            self._new_name(item.name, item.position)
            value = self.lower(item.value)
            if not _is_const(value):
                raise LangError(f"parameter {item.name!r} must be a constant", item.position)
            self.params[item.name] = value
        elif isinstance(item, S.Definition):
            self._new_name(item.name, item.position)
            value = self.lower(item.expr)
            if _is_const(value):
                raise LangError(f"{item.name!r} is {_describe(value)}: a definition must be a signal",
                                item.position)
            self.definitions[item.name] = value
        else:
            raise LangError(f"unexpected item {item!r}")

    def _new_name(self, name, position):
        if name in self.inputs or name in self.params or name in self.definitions:
            raise LangError(f"{name!r} is already defined", position)

    # expressions: constant (int/float/bool) or Signal
    def lower(self, e):
        method = getattr(self, "lower_" + type(e).__name__, None)
        if method is None:
            raise LangError(f"unsupported expression {type(e).__name__}", e.position)
        return method(e)

    def lower_Number(self, e):
        return e.value

    def lower_Bool(self, e):
        return e.value

    def lower_Ref(self, e):
        for table in (self.params, self.inputs, self.definitions):
            if e.name in table:
                return table[e.name]
        raise LangError(f"undefined name {e.name!r}", e.position)

    def lower_Unary(self, e):
        x = self.lower(e.operand)
        if e.op == "neg":
            if _is_const(x):
                return -self.number(x, e)
            return self.scale(x, -1, e)
        if e.op == "abs":
            if _is_const(x):
                return abs(self.number(x, e))
            return Signal(S.Abs(x.core), False, x.degree)
        if e.op == "not":
            if _is_const(x):
                return not self.boolean(x, e)
            return Signal(S.Not(self.boolean(x, e).core), True, 0)
        raise LangError(f"unknown operator {e.op!r}", e.position)

    def lower_Binary(self, e):
        a, b = self.lower(e.left), self.lower(e.right)
        op = e.op
        if op in ("and", "or"):
            return self.logic(op, a, b, e)
        if op in ("min", "max"):
            if _is_const(a) and _is_const(b):
                return (min if op == "min" else max)(self.number(a, e), self.number(b, e))
            if _is_const(a) or _is_const(b):
                raise LangError(f"{op}(signal, constant) is not supported: both arguments must be signals",
                                e.position)
            core = (S.PointMin if op == "min" else S.PointMax)(a.core, b.core)
            return Signal(core, a.boolean and b.boolean, max(a.degree, b.degree))
        if _is_const(a) and _is_const(b):
            return self.fold(op, self.number(a, e), self.number(b, e), e)
        if op == "+":
            if _is_const(a):
                return self.add_const(b, self.number(a, e), e)
            if _is_const(b):
                return self.add_const(a, self.number(b, e), e)
            return Signal(S.Sum(a.core, b.core), False, max(a.degree, b.degree))
        if op == "-":
            if _is_const(b):
                return self.add_const(a, -self.number(b, e), e)
            if _is_const(a):  # c - x = (-1 * x) + c
                return self.add_const(self.scale(b, -1, e), self.number(a, e), e)
            return Signal(S.Sub(a.core, b.core), False, max(a.degree, b.degree))
        if op == "*":
            if _is_const(a):
                return self.scale(b, self.number(a, e), e)
            if _is_const(b):
                return self.scale(a, self.number(b, e), e)
            raise LangError("product of two signals is not supported (only signal * constant)", e.position)
        if op == "/":
            if _is_const(b):
                c = self.number(b, e)
                if c == 0:
                    raise LangError("division by zero", e.position)
                return self.scale(a, 1 / c, e)
            raise LangError("division by a signal is not supported (only signal / constant)", e.position)
        raise LangError(f"unknown operator {op!r}", e.position)

    def lower_Compare(self, e):
        a, b = self.lower(e.left), self.lower(e.right)
        op = e.op
        if _is_const(a) and _is_const(b):
            raise LangError("comparison between constants", e.position)
        if _is_const(a):  # c < x  is  x > c
            a, b, op = b, a, {"<": ">", ">": "<", "<=": ">=", ">=": "<="}[op]
        if not _is_const(b):  # x < y  is  x - y < 0
            a = Signal(S.Sub(a.core, b.core), False, max(a.degree, b.degree))
            b = 0
        c = self.number(b, e)
        x = a.core  # booleans are 0/1 signals and may be compared as numbers
        if op == ">":
            core = S.Threshold(">", x, c)
        elif op == "<":
            core = S.Threshold("<", x, c)
        elif op == ">=":  # not (x < c)
            core = S.Not(S.Threshold("<", x, c))
        else:  # <=: not (x > c)
            core = S.Not(S.Threshold(">", x, c))
        return Signal(core, True, 0)

    def lower_Window(self, e):
        lower = self.lower(e.lower)
        upper = self.lower(e.upper)
        if not (_is_const(lower) and _is_const(upper)):
            raise LangError("the bounds of a time window must be constants", e.position)
        lower, upper = self.number(lower, e), self.number(upper, e)
        if lower < 0 or upper <= lower:
            raise LangError(f"invalid time window [{lower}, {upper}]: need 0 <= a < b", e.position)
        x = self.lower(e.operand)
        if _is_const(x):
            raise LangError(f"time window over {_describe(x)}", e.position)
        core = x.core
        if e.condition is not None:
            chi = self.lower(e.condition)
            if _is_const(chi):
                raise LangError(f"filter condition is {_describe(chi)}", e.condition.position or e.position)
            core = S.Filter(core, self.boolean(chi, e).core)
        if e.tag == "Int":
            degree, boolean = x.degree + 1, False
        else:
            degree, boolean = x.degree, x.boolean
        if degree > MAX_DEGREE:
            raise LangError(f"Int of a signal of degree {x.degree} gives degree {degree}: gemon is exact only up "
                            f"to degree {MAX_DEGREE} (avoid nesting Int over linear signals)", e.position)
        length = upper - lower
        core = S.SlidingWindow(e.tag, length, core)
        if lower != 0:  # On[a, b] at t is On[0, b - a] at t + a
            core = S.Shift(core, -lower)
        return Signal(core, boolean, degree)

    # helpers
    def number(self, value, e):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise LangError(f"expected a number, found {_describe(value)}", e.position)
        return value

    def boolean(self, value, e):
        if _is_const(value):
            if not isinstance(value, bool):
                raise LangError(f"expected a boolean, found {_describe(value)}", e.position)
            return value
        if not value.boolean:
            raise LangError("expected a boolean signal (a comparison, and/or/not), found a numeric signal",
                            e.position)
        return value

    def fold(self, op, a, b, e):
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if b == 0:
            raise LangError("division by zero", e.position)
        return a / b

    def add_const(self, x, c, e):
        if c == 0:
            return x
        return Signal(S.AddConst(x.core, c), False, x.degree)

    def scale(self, x, c, e):
        if c == 1:
            return x
        return Signal(S.Scale(x.core, c), False, x.degree)

    def logic(self, op, a, b, e):
        if _is_const(a) and _is_const(b):
            a, b = self.boolean(a, e), self.boolean(b, e)
            return (a and b) if op == "and" else (a or b)
        if _is_const(a) or _is_const(b):
            c, x = (a, b) if _is_const(a) else (b, a)
            c = self.boolean(c, e)
            x = self.boolean(x, e)
            if op == "and":
                return x if c else False
            return True if c else x
        a, b = self.boolean(a, e), self.boolean(b, e)
        return Signal((S.And if op == "and" else S.Or)(a.core, b.core), True, 0)


class Builder:
    """Core syntax -> gemon nodes, one node per distinct core node."""

    def __init__(self):
        self.nodes = {}   # core -> gemon node

    def build(self, core):
        node = self.nodes.get(core)
        if node is None:
            node = getattr(self, "build_" + type(core).__name__)(core)
            self.nodes[core] = node
        return node

    def unary(self, node, operand):
        self.build(operand).to(node.receive)
        return node

    def binary(self, node, left, right):
        self.build(left).to(node.receive_left)
        self.build(right).to(node.receive_right)
        return node

    def build_Input(self, c):
        return VariablePWLNode() if c.interpolation == "linear" else VariablePWCNode()

    def build_Sum(self, c):
        return self.binary(SumNode(), c.left, c.right)

    def build_Sub(self, c):
        return self.binary(SubNode(), c.left, c.right)

    def build_AddConst(self, c):
        return self.unary(AddConstNode(c.value), c.operand)

    def build_Scale(self, c):
        return self.unary(MultiplyByConst(c.value), c.operand)

    def build_Threshold(self, c):
        node = HigherThanNode(c.value) if c.op == ">" else LowerThanNode(c.value)
        return self.unary(node, c.operand)

    def build_Not(self, c):
        return self.unary(NotNode(), c.operand)

    def build_And(self, c):
        return self.binary(AndNode(), c.left, c.right)

    def build_Or(self, c):
        return self.binary(OrNode(), c.left, c.right)

    def build_Abs(self, c):
        return self.unary(AbsNode(), c.operand)

    def build_PointMin(self, c):
        return self.binary(MinNode(), c.left, c.right)

    def build_PointMax(self, c):
        return self.binary(MaxNode(), c.left, c.right)

    def build_Filter(self, c):
        return self.binary(FilterNode(), c.operand, c.condition)

    def build_SlidingWindow(self, c):
        cls = {"Int": IntegralWindowNode, "Min": MinWindowNode, "Max": MaxWindowNode}[c.tag]
        return self.unary(cls(c.length), c.operand)

    def build_Shift(self, c):
        return self.unary(ShiftNode(c.delta), c.operand)


class Monitor:
    """A compiled program: feed its inputs with receive, read its definitions with
    observe (a gemon Signal recording every interval) or to (a callback)."""

    def __init__(self, inputs, outputs, nodes):
        self.inputs = inputs      # input name -> gemon input node
        self.outputs = outputs    # definition name -> gemon node
        self.nodes = nodes        # every gemon node of the graph

    def receive(self, name, time, value):
        try:
            node = self.inputs[name]
        except KeyError:
            raise KeyError(f"{name!r} is not an input of the program") from None
        node.receive(time, value)

    def node(self, name):
        if name in self.outputs:
            return self.outputs[name]
        if name in self.inputs:
            return self.inputs[name]
        raise KeyError(f"{name!r} is neither a definition nor an input of the program")

    def observe(self, name):
        return self.node(name).observe()

    def to(self, name, callback):
        self.node(name).to(callback)


def lower_program(program: S.Program) -> Lowering:
    return Lowering(program).run()


def compile_program(text: str) -> Monitor:
    """Compile a program (text) into a Monitor. Raises LangError on errors."""
    return build(lower_program(parse(text)))


def compile_file(path: str) -> Monitor:
    with open(path) as f:
        return compile_program(f.read())


def build(lowered: Lowering) -> Monitor:
    builder = Builder()
    inputs = {name: builder.build(signal.core) for name, signal in lowered.inputs.items()}
    outputs = {name: builder.build(signal.core) for name, signal in lowered.definitions.items()}
    return Monitor(inputs, outputs, list(builder.nodes.values()))
