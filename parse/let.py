from dataclasses import dataclass
from error import Error
from collections.abc import Generator

from expr import Expr
import lex
from lex import Lexer
from ty import Ty


@dataclass
class Let(Expr):
    from pattern import Pattern

    pattern: Pattern
    ty: Ty | None
    value: Expr | None
    else_: Expr | None

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        match lexer.peek():
            case lex.Ident(start_span, "let"):
                from pattern import Pattern

                lexer.next()
                pat = yield from Pattern.parse(lexer)
                match lexer.peek():
                    case lex.Punct(_, ":"):
                        lexer.next()
                        ty = yield from Ty.parse(lexer)
                    case _:
                        ty = None
                match lexer.peek():
                    case lex.Punct(_, "="):
                        lexer.next()
                        expr = yield from Expr.parse(lexer)
                        match lexer.peek():
                            case lex.Ident(_, "else"):
                                lexer.next()
                                else_ = yield from Expr.parse(lexer)
                                return Let(
                                    slice(start_span.start, lexer.offset),
                                    pat,
                                    ty,
                                    expr,
                                    else_,
                                )
                            case _:
                                return Let(
                                    slice(start_span.start, lexer.offset),
                                    pat,
                                    ty,
                                    expr,
                                    None,
                                )
                    case _:
                        return Let(
                            slice(start_span.start, lexer.offset), pat, ty, None, None
                        )
            case _:
                from parse.binary import Binary

                return (yield from Binary.parse(lexer))

    def __str__(self) -> str:
        if self.ty is not None:
            if self.value is not None:
                if self.else_ is not None:
                    return f"let {self.pattern}: {self.ty} = {self.value} else {self.else_}"
                return f"let {self.pattern}: {self.ty} = {self.value}"
            return f"let {self.pattern}: {self.ty}"
        if self.value is not None:
            if self.else_ is not None:
                return f"let {self.pattern} = {self.value} else {self.else_}"
            return f"let {self.pattern} = {self.value}"
        return f"let {self.pattern}"
