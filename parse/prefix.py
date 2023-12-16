from dataclasses import dataclass
from error import Error
from collections.abc import Generator

from expr import Expr
import lex
from lex import Lexer


@dataclass
class Prefix(Expr):
    rhs: Expr

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        from parse.suffix import Suffix

        match lexer.peek():
            case lex.Punct(span, "-"):
                lexer.next()
                return Neg(span, (yield from Prefix.parse(lexer)))
            case lex.Punct(span, "!"):
                lexer.next()
                return Not(span, (yield from Prefix.parse(lexer)))
            case lex.Punct(span, "+"):
                lexer.next()
                return Pos(span, (yield from Prefix.parse(lexer)))
            case lex.Punct(span, "*"):
                lexer.next()
                return Deref(span, (yield from Prefix.parse(lexer)))
            case lex.Punct(span, "&"):
                lexer.next()
                return Ref(span, (yield from Prefix.parse(lexer)))
            case _:
                return (yield from Suffix.parse(lexer))


@dataclass
class Neg(Prefix):
    def __str__(self) -> str:
        return f"-({self.rhs})"


@dataclass
class Not(Prefix):
    def __str__(self) -> str:
        return f"!({self.rhs})"


@dataclass
class Pos(Prefix):
    def __str__(self) -> str:
        return f"+({self.rhs})"


@dataclass
class Deref(Prefix):
    def __str__(self) -> str:
        return f"*({self.rhs})"


@dataclass
class Ref(Prefix):
    def __str__(self) -> str:
        return f"&({self.rhs})"
