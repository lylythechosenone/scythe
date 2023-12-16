from dataclasses import dataclass
from error import Error
from collections.abc import Generator

from expr import Expr
from parse.let import Let
import lex
from lex import Lexer


@dataclass
class Cont(Expr):
    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        match lexer.peek():
            case lex.Ident(start_span, "return"):
                lexer.next()
                match lexer.peek():
                    case lex.Punct(_, ";") | None:
                        return Return(slice(start_span.start, lexer.offset), None)
                    case _:
                        value = yield from Expr.parse(lexer)
                        return Return(slice(start_span.start, lexer.offset), value)
            case lex.Ident(start_span, "break"):
                lexer.next()
                match lexer.peek():
                    case lex.Punct(_, ";") | None:
                        return Break(slice(start_span.start, lexer.offset), None)
                    case _:
                        value = yield from Expr.parse(lexer)
                        return Break(slice(start_span.start, lexer.offset), value)
            case lex.Ident(start_span, "continue"):
                lexer.next()
                return Continue(slice(start_span.start, lexer.offset))
            case _:
                return (yield from Let.parse(lexer))


@dataclass
class Return(Expr):
    value: Expr | None

    def __str__(self) -> str:
        if self.value is None:
            return "return"
        else:
            return f"return {self.value}"


@dataclass
class Break(Expr):
    value: Expr | None

    def __str__(self) -> str:
        if self.value is None:
            return "break"
        else:
            return f"break {self.value}"


@dataclass
class Continue(Expr):
    def __str__(self) -> str:
        return "continue"
