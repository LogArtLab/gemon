class LangError(Exception):
    """A syntax or semantic error in a program, with its source position when known."""

    def __init__(self, message, position=None, context=None):
        self.message = message
        self.position = position
        self.context = context
        where = f"{position}: " if position is not None else ""
        text = where + message
        if context:
            text += "\n" + context.rstrip("\n")
        super().__init__(text)
