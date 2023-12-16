from dataclasses import dataclass
from collections.abc import Generator
from error import Error
from parse.expr import Expr
import lex
from lex import Lexer


@dataclass
class Semi(Expr):
    base: Expr

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        from parse.item import Item

        base = yield from Item.parse(lexer)
        match lexer.peek():
            case lex.Punct(_, ";"):
                lexer.next()
                return Semi(slice(base.span.start, lexer.offset), base)
            case _:
                return base

    def __str__(self) -> str:
        return f"{self.base};"
