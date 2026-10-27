"""Surface syntax -> text, with the fewest parentheses that keep the same tree:
parse(unparse(e)) == e for every expression e (positions aside)."""

from gemon.lang import syntax as S

# binding strength of each construct (higher binds tighter)
OR, AND, NOT, COMPARE, SUM, PRODUCT, NEG, ATOM = range(1, 9)
BINARY = {"or": OR, "and": AND, "+": SUM, "-": SUM, "*": PRODUCT, "/": PRODUCT}


def _number(value):
    text = repr(value)
    if text.startswith("-"):
        raise ValueError(f"negative literal {value!r}: write it as a negation")
    return text


def level(e):
    if isinstance(e, S.Binary) and e.op in BINARY:
        return BINARY[e.op]
    if isinstance(e, S.Compare):
        return COMPARE
    if isinstance(e, S.Unary) and e.op == "not":
        return NOT
    if isinstance(e, S.Unary) and e.op == "neg":
        return NEG
    return ATOM


def unparse(e, minimum=0):
    """Text of e, in parentheses when it binds less tightly than minimum."""
    text = _unparse(e)
    return f"({text})" if level(e) < minimum else text


def _unparse(e):
    if isinstance(e, S.Number):
        return _number(e.value)
    if isinstance(e, S.Bool):
        return "true" if e.value else "false"
    if isinstance(e, S.Ref):
        return e.name
    if isinstance(e, S.Unary):
        if e.op == "abs":
            return f"|{unparse(e.operand)}|"
        if e.op == "not":
            return f"not {unparse(e.operand, NOT)}"
        return f"-{unparse(e.operand, NEG)}"
    if isinstance(e, S.Binary):
        if e.op in ("min", "max"):
            return f"{e.op}({unparse(e.left)}, {unparse(e.right)})"
        p = BINARY[e.op]
        # left-associative: the right operand of the same level needs parentheses
        return f"{unparse(e.left, p)} {e.op} {unparse(e.right, p + 1)}"
    if isinstance(e, S.Compare):
        return f"{unparse(e.left, SUM)} {e.op} {unparse(e.right, SUM)}"
    if isinstance(e, S.Window):
        body = unparse(e.operand)
        if e.condition is not None:
            body += f" | {unparse(e.condition)}"
        return f"On[{unparse(e.lower)}, {unparse(e.upper)}] {e.tag}({body})"
    raise TypeError(f"cannot print {e!r}")


def unparse_program(program):
    lines = []
    if program.timeunit != "s":
        lines.append(f"timeunit {program.timeunit}")
    for item in program.items:
        if isinstance(item, S.InputDecl):
            lines.append(f"input {item.name} : {item.interpolation}")
        elif isinstance(item, S.ParamDecl):
            lines.append(f"param {item.name} = {unparse(item.value)}")
        else:
            lines.append(f"{item.name} := {unparse(item.expr)}")
    return "\n".join(lines) + "\n"
