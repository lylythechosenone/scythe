from dataclasses import dataclass
from error import Error
from collections.abc import Generator

from expr import Expr
import lex
from lex import Lexer
from ty import Ty


@dataclass
class Suffix(Expr):
    base: Expr

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        from parse.atom import Atom

        expr = yield from Atom.parse(lexer)
        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "."):
                    lexer.next()
                    match lexer.next():
                        case lex.Ident() as name:
                            pass
                        case lex.Int(_, _, None) as name:
                            pass
                        case _:
                            yield Error(
                                "Unexpected token",
                                slice(lexer.offset, lexer.offset + 1),
                                "Expected an identifier or integer, found this instead",
                            )
                            continue
                    expr = Member(
                        slice(expr.span.start, name.span.stop),
                        expr,
                        lexer.file[name.span],
                    )
                case lex.Punct(_, "->"):
                    lexer.next()
                    match lexer.next():
                        case lex.Ident() as name:
                            pass
                        case lex.Int(_, _, None) as name:
                            pass
                        case _:
                            yield Error(
                                "Unexpected token",
                                slice(lexer.offset, lexer.offset + 1),
                                "Expected an identifier or integer, found this instead",
                            )
                            continue
                    expr = Offset(
                        slice(expr.span.start, name.span.stop),
                        expr,
                        lexer.file[name.span],
                    )
                case lex.Group(_, "()", inner):
                    lexer.next()
                    args = yield from Expr.comma_separated(inner)
                    if not inner.is_empty():
                        yield Error(
                            "Unexpected tokens",
                            slice(inner.offset, len(inner.file)),
                            "Expected a closing bracket, found these tokens instead",
                        )
                    expr = Call(slice(expr.span.start, lexer.offset), expr, args)
                case lex.Group(_, "[]", inner):
                    lexer.next()
                    index = yield from Expr.parse(inner)
                    if not inner.is_empty():
                        yield Error(
                            "Unexpected tokens",
                            slice(inner.offset, len(inner.file)),
                            "Expected a closing bracket, found these tokens instead",
                        )
                    expr = Index(slice(expr.span.start, lexer.offset), expr, index)
                case lex.Punct(_, "as"):
                    lexer.next()
                    to = yield from Ty.parse(lexer)
                    expr = Cast(slice(expr.span.start, lexer.offset), expr, to)
                case _:
                    return expr
        return expr


@dataclass
class Member(Suffix):
    name: str

    def __str__(self) -> str:
        return f"({self.base}).{self.name}"


@dataclass
class Offset(Suffix):
    name: str

    def __str__(self) -> str:
        return f"({self.base})->{self.name}"


@dataclass
class Call(Suffix):
    args: list[Expr]

    def __str__(self) -> str:
        return f"({self.base})({', '.join(map(str, self.args))})"


@dataclass
class Index(Suffix):
    index: Expr

    def __str__(self) -> str:
        return f"({self.base})[{self.index}]"


@dataclass
class Cast(Suffix):
    to: Ty

    def __str__(self) -> str:
        return f"({self.base} as {self.to})"
