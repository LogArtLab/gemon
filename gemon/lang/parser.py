"""Parser of the gemon specification language: text -> surface syntax (syntax.py).

The grammar is gemon.lark (Lark, LALR(1)). Extensions of the language (e.g. LIM)
load their own grammar, which imports this one, and subclass ToSyntax.
"""

import os
from functools import lru_cache

from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, UnexpectedToken, VisitError

from gemon.lang.errors import LangError
from gemon.lang.syntax import (Binary, Bool, Compare, Definition, InputDecl, Number, ParamDecl, Position, Program,
                               Ref, Unary, Window)

GRAMMAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemon.lark")

# seconds per unit
UNITS = {"ms": 0.001, "s": 1, "min": 60, "h": 3600, "d": 86400}


def _position(item):
    line = getattr(item, "line", None)
    column = getattr(item, "column", None)
    if line is None and hasattr(item, "meta") and not getattr(item.meta, "empty", True):
        line, column = item.meta.line, item.meta.column
    return Position(line, column) if line is not None else None


def _number(text):
    if any(c in text for c in ".eE"):
        return float(text)
    return int(text)


@v_args(meta=True)
class ToSyntax(Transformer):
    """Lark tree -> surface syntax. Time units are converted to the base unit of the
    program (timeunit, seconds by default) here, so later stages see plain numbers."""

    def __init__(self, timeunit="s"):
        super().__init__()
        self.base_unit = timeunit

    def to_base(self, value, unit, position):
        if unit is None:
            return value
        factor = UNITS[unit] / UNITS[self.base_unit]
        scaled = value * factor
        if isinstance(value, int) and float(scaled).is_integer() and factor >= 1:
            return int(round(scaled))
        return scaled

    # program
    def start(self, meta, items):
        return items

    def timeunit(self, meta, children):
        return ("timeunit", str(children[0]))

    def input(self, meta, children):
        name, interpolation = children
        return InputDecl(str(name), str(interpolation), _position(name))

    def param(self, meta, children):
        name, value = children
        return ParamDecl(str(name), value, _position(name))

    def definition(self, meta, children):
        name, expr = children
        return Definition(str(name), expr, _position(name))

    # expressions
    def number(self, meta, children):
        token = children[0]
        return Number(_number(str(token)), _position(token))

    def quantity(self, meta, children):
        token = children[0]
        text = str(token)
        digits = text.rstrip("abcdefghijklmnopqrstuvwxyz")
        position = _position(token)
        return Number(self.to_base(_number(digits), text[len(digits):], position), position)

    def true(self, meta, children):
        return Bool(True, Position(meta.line, meta.column))

    def false(self, meta, children):
        return Bool(False, Position(meta.line, meta.column))

    def ref(self, meta, children):
        return Ref(str(children[0]), _position(children[0]))

    def _binary(op):
        def method(self, meta, children):
            return Binary(op, children[0], children[1], Position(meta.line, meta.column))
        return method

    or_ = _binary("or")
    and_ = _binary("and")
    add = _binary("+")
    sub = _binary("-")
    mul = _binary("*")
    div = _binary("/")
    pmin = _binary("min")
    pmax = _binary("max")

    def _unary(op):
        def method(self, meta, children):
            return Unary(op, children[0], Position(meta.line, meta.column))
        return method

    not_ = _unary("not")
    neg = _unary("neg")
    abs = _unary("abs")

    def compare(self, meta, children):
        left, op, right = children
        return Compare(str(op), left, right, Position(meta.line, meta.column))

    def window(self, meta, children):
        lower, upper, tag, operand, condition = children
        return Window(str(tag), lower, upper, operand, condition, Position(meta.line, meta.column))


@lru_cache(maxsize=None)
def _lark(path, start="start"):
    with open(path) as f:
        return Lark(f.read(), parser="lalr", start=start, propagate_positions=True, maybe_placeholders=True,
                    import_paths=[os.path.dirname(GRAMMAR), os.path.dirname(path)])


def _syntax_error(error, text):
    position = Position(error.line, error.column) if getattr(error, "line", None) else None
    if isinstance(error, UnexpectedEOF):
        message = "unexpected end of input"
    elif isinstance(error, UnexpectedToken):
        found = "end of input" if error.token.type == "$END" else repr(str(error.token))
        expected = ", ".join(sorted(error.accepts or error.expected))
        message = f"unexpected {found}; expected one of: {expected}"
    elif isinstance(error, UnexpectedCharacters):
        message = f"unexpected character {text[error.pos_in_stream]!r}"
    else:
        message = str(error)
    return LangError(message, position, error.get_context(text) if position else None)


def _timeunit(tree):
    """The timeunit declaration must be known before numbers are converted: it is read
    from the tree first (it may appear anywhere, at most once)."""
    units = [t.children[0] for t in tree.children if getattr(t, "data", None) == "timeunit"]
    if len(units) > 1:
        raise LangError("timeunit declared more than once", Position(units[1].line, units[1].column))
    return str(units[0]) if units else "s"


def parse(text, grammar=GRAMMAR, transformer=ToSyntax):
    """Parse a program: text -> syntax.Program. Raises LangError on syntax errors."""
    lark = _lark(grammar)
    try:
        tree = lark.parse(text)
    except UnexpectedInput as error:
        raise _syntax_error(error, text) from None
    timeunit = _timeunit(tree)
    try:
        items = transformer(timeunit).transform(tree)
    except VisitError as error:
        if isinstance(error.orig_exc, LangError):
            raise error.orig_exc from None
        raise
    return Program(timeunit, tuple(item for item in items if not isinstance(item, tuple)))
