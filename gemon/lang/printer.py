"""Surface syntax -> text, with the fewest parentheses that keep the same tree:
parse(unparse(e)) == e for every expression e (positions aside). Extensions of the
language subclass Printer."""

from gemon.lang import syntax as S

# binding strength of each construct (higher binds tighter)
LOWEST, OR, AND, NOT, COMPARE, SUM, PRODUCT, NEG, ATOM = range(0, 9)
BINARY = {"or": OR, "and": AND, "+": SUM, "-": SUM, "*": PRODUCT, "/": PRODUCT}


class Printer:

    def level(self, e):
        if isinstance(e, S.Binary) and e.op in BINARY:
            return BINARY[e.op]
        if isinstance(e, S.Compare):
            return COMPARE
        if isinstance(e, S.Unary) and e.op == "not":
            return NOT
        if isinstance(e, S.Unary) and e.op == "neg":
            return NEG
        return ATOM

    def unparse(self, e, minimum=LOWEST):
        """Text of e, in parentheses when it binds less tightly than minimum."""
        text = self.text(e)
        return f"({text})" if self.level(e) < minimum else text

    def number(self, value):
        text = repr(value)
        if text.startswith("-"):
            raise ValueError(f"negative literal {value!r}: write it as a negation")
        return text

    def text(self, e):
        method = getattr(self, "text_" + type(e).__name__, None)
        if method is None:
            raise TypeError(f"cannot print {e!r}")
        return method(e)

    def text_Number(self, e):
        return self.number(e.value)

    def text_Bool(self, e):
        return "true" if e.value else "false"

    def text_Ref(self, e):
        return e.name

    def text_Unary(self, e):
        if e.op == "abs":
            return f"|{self.unparse(e.operand)}|"
        if e.op == "not":
            return f"not {self.unparse(e.operand, NOT)}"
        return f"-{self.unparse(e.operand, NEG)}"

    def text_Binary(self, e):
        if e.op in ("min", "max"):
            return f"{e.op}({self.unparse(e.left)}, {self.unparse(e.right)})"
        p = BINARY[e.op]
        # left-associative: the right operand of the same level needs parentheses
        return f"{self.unparse(e.left, p)} {e.op} {self.unparse(e.right, p + 1)}"

    def text_Compare(self, e):
        return f"{self.unparse(e.left, SUM)} {e.op} {self.unparse(e.right, SUM)}"

    def text_Window(self, e):
        body = self.unparse(e.operand)
        if e.condition is not None:
            body += f" | {self.unparse(e.condition)}"
        return f"On[{self.unparse(e.lower)}, {self.unparse(e.upper)}] {e.tag}({body})"

    def item(self, item):
        if isinstance(item, S.InputDecl):
            return f"input {item.name} : {item.interpolation}"
        if isinstance(item, S.ParamDecl):
            return f"param {item.name} = {self.unparse(item.value)}"
        if isinstance(item, S.Definition):
            return f"{item.name} := {self.unparse(item.expr)}"
        raise TypeError(f"cannot print {item!r}")

    def program(self, program):
        lines = []
        if program.timeunit != "s":
            lines.append(f"timeunit {program.timeunit}")
        lines += [self.item(item) for item in program.items]
        return "\n".join(lines) + "\n"


_printer = Printer()


def unparse(e, minimum=LOWEST):
    return _printer.unparse(e, minimum)


def unparse_program(program):
    return _printer.program(program)
