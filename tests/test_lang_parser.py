"""Tests of the parser of the gemon specification language (text -> surface syntax)."""

import re

import pytest

from gemon.lang import LangError, parse
from gemon.lang.printer import unparse, unparse_program
from gemon.lang.syntax import (Binary, Bool, Compare, Definition, InputDecl, Number, ParamDecl, Ref, Unary,
                               Window)


def expr(text, prelude="input x : linear\ninput y : linear\ninput z : const\n"):
    program = parse(prelude + "e := " + text + "\n")
    return program.items[-1].expr


x, y, z = Ref("x"), Ref("y"), Ref("z")


def test_declarations_and_definitions_in_source_order():
    program = parse("""
        input G : linear   # glucose
        input B : const
        param T = 180
        TAR := G
    """)
    assert program.timeunit == "s"
    assert program.items == (InputDecl("G", "linear"), InputDecl("B", "const"),
                             ParamDecl("T", Number(180)), Definition("TAR", Ref("G")))


@pytest.mark.parametrize("text, tree", [
    ("x + y * 2", Binary("+", x, Binary("*", y, Number(2)))),
    ("(x + y) * 2", Binary("*", Binary("+", x, y), Number(2))),
    ("x - y - z", Binary("-", Binary("-", x, y), z)),
    ("x - (y - z)", Binary("-", x, Binary("-", y, z))),
    ("x / 2 / 4", Binary("/", Binary("/", x, Number(2)), Number(4))),
    ("-x * 2", Binary("*", Unary("neg", x), Number(2))),
    ("- -x", Unary("neg", Unary("neg", x))),
    ("x + 1 > y", Compare(">", Binary("+", x, Number(1)), y)),
    ("x > 1 and y < 2 or z >= 3", Binary("or", Binary("and", Compare(">", x, Number(1)), Compare("<", y, Number(2))),
                                         Compare(">=", z, Number(3)))),
    ("x > 1 or y > 1 and z > 1", Binary("or", Compare(">", x, Number(1)),
                                        Binary("and", Compare(">", y, Number(1)), Compare(">", z, Number(1))))),
    ("not x > 1 and y > 1", Binary("and", Unary("not", Compare(">", x, Number(1))), Compare(">", y, Number(1)))),
    ("not not x > 1", Unary("not", Unary("not", Compare(">", x, Number(1))))),
    ("|x - y|", Unary("abs", Binary("-", x, y))),
    ("abs(x - y)", Unary("abs", Binary("-", x, y))),
    ("||x| - |y||", Unary("abs", Binary("-", Unary("abs", x), Unary("abs", y)))),
    ("min(x, max(y, 1.5e2))", Binary("min", x, Binary("max", y, Number(150.0)))),
    ("true and x > 0", Binary("and", Bool(True), Compare(">", x, Number(0)))),
    ("On[0, 10] Int(x)", Window("Int", Number(0), Number(10), x)),
    ("On[2, 10] Max(x | y > 0)", Window("Max", Number(2), Number(10), x, Compare(">", y, Number(0)))),
    ("On[0, 5] Min(|x| | |y| > 1)", Window("Min", Number(0), Number(5), Unary("abs", x),
                                          Compare(">", Unary("abs", y), Number(1)))),
    ("On[0, 10] Int(x) / 10", Binary("/", Window("Int", Number(0), Number(10), x), Number(10))),
])
def test_precedence_and_associativity(text, tree):
    assert expr(text) == tree


def test_number_literals_keep_their_type():
    assert expr("x + 180").right == Number(180) and type(expr("x + 180").right.value) is int
    assert type(expr("x + 180.0").right.value) is float
    assert expr("x + .5").right == Number(0.5)
    assert expr("x + 1e3").right == Number(1000.0)


@pytest.mark.parametrize("text, value", [
    ("300s", 300), ("5min", 300), ("2h", 7200), ("1d", 86400), ("1.5h", 5400.0), ("250ms", 0.25),
])
def test_time_units_in_seconds(text, value):
    number = expr(f"On[0, {text}] Int(x)").upper
    assert number.value == value and type(number.value) is type(value)


def test_timeunit_changes_the_base_unit():
    program = parse("timeunit ms\ninput x : linear\ne := On[0, 2s] Int(x) + 7\n")
    assert program.timeunit == "ms"
    window = program.items[-1].expr.left
    assert window.upper == Number(2000)
    assert program.items[-1].expr.right == Number(7)  # plain numbers are in the base unit


def test_timeunit_may_appear_anywhere_once():
    assert parse("input x : linear\ne := On[0, 1min] Int(x)\ntimeunit s\n").items[-1].expr.upper == Number(60)
    with pytest.raises(LangError, match="more than once"):
        parse("timeunit s\ntimeunit ms\n")


def test_unit_must_be_attached_to_the_number():
    with pytest.raises(LangError):
        parse("input x : linear\ne := On[0, 5 min] Int(x)\n")


def test_short_names_that_look_like_units():
    program = parse("input s : linear\ninput h : const\nd := s + h\n")
    assert program.items[-1] == Definition("d", Binary("+", Ref("s"), Ref("h")))


def test_params_are_expressions():
    program = parse("param T = 3min\nparam H = T / 2\n")
    assert program.items == (ParamDecl("T", Number(180)), ParamDecl("H", Binary("/", Ref("T"), Number(2))))


@pytest.mark.parametrize("text, message, line, column", [
    ("input x : linear\ne := x +\n", "unexpected end of input", None, None),
    ("input x : linear\ne := x < 1 < 2\n", "unexpected '<'", 2, 12),
    ("input x : cubic\n", "unexpected", 1, 11),
    ("input x : linear\ne := x $ 2\n", "unexpected character '$'", 2, 8),
    ("input x : linear\ne = x\n", "unexpected '='", 2, 3),
    ("input x : linear\ne := On[0, 1] Avg(x)\n", "unexpected", 2, 15),
])
def test_syntax_errors_have_a_position(text, message, line, column):
    with pytest.raises(LangError, match=re.escape(message)) as info:
        parse(text)
    if line is not None:
        assert (info.value.position.line, info.value.position.column) == (line, column)


def test_positions_do_not_matter_for_equality():
    assert expr("x + 1") == expr("x   +   1")
    assert expr("x + 1").position != expr("  x + 1").position


@pytest.mark.parametrize("text", [
    "x + y * 2", "(x + y) * 2", "x - (y - z)", "-(x + y)", "not (x > 1 and y > 1)", "(x > 1) - (y < 2)",
    "|x - |y||", "On[1, 10] Max(x | y > 0 or z < 1) - 3", "min(-x, max(y, 2))", "x / (2 * 3)",
])
def test_unparse_round_trip(text):
    tree = expr(text)
    assert expr(unparse(tree)) == tree


def test_unparse_program_round_trip():
    text = "timeunit ms\ninput x : linear\nparam T = 3\ne := On[0, T] Int(x > 1) / T\n"
    program = parse(text)
    assert parse(unparse_program(program)) == program
