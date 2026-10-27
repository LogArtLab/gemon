"""The gemon specification language: write a monitor as text, compile it into a graph
of gemon nodes.

    from gemon.lang import compile_program

    monitor = compile_program('''
        input G : linear
        param T = 180
        TAR := On[0, T] Int(G > 180) / T
    ''')
    tar = monitor.observe("TAR")
    for t, g in samples:
        monitor.receive("G", t, g)

Grammar: gemon/lang/gemon.lark. Language reference: README.md.
"""

from gemon.lang.compiler import Monitor, compile_file, compile_program
from gemon.lang.errors import LangError
from gemon.lang.parser import parse

__all__ = ["compile_program", "compile_file", "parse", "Monitor", "LangError"]
