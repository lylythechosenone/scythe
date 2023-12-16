from dataclasses import dataclass
from error import Error
from collections.abc import Generator

from parse.expr import Expr
import lex
from lex import Lexer


@dataclass
class Pattern:
    span: slice

    @staticmethod
    def comma_separated(lexer: Lexer) -> Generator[Error, None, list["Pattern"]]:
        patterns: list[Pattern] = []
        while lexer.peek() != None:
            patterns.append((yield from Pattern.parse(lexer)))
            match lexer.peek():
                case lex.Punct(_, ","):
                    lexer.next()
                case lex.Token(span):
                    raise Error(
                        "Unexpected token",
                        span,
                        "Expected a comma, found this instead",
                    )
                case None:
                    pass
        return patterns

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, "Pattern"]:
        match lexer.peek():
            case lex.Ident(span, "_"):
                lexer.next()
                return Ignore(span)
            case lex.Ident(span, value):
                lexer.next()
                return Ident(span, value)
            case lex.Group(span, "()", inner):
                lexer.next()
                patterns = yield from Pattern.comma_separated(inner)
                if not inner.is_empty():
                    yield Error(
                        "Unexpected tokens",
                        slice(inner.offset, len(inner.file)),
                        "Expected a closing bracket, found these tokens instead",
                    )
                return Tuple(span, patterns)
            case _:
                raise NotImplementedError


@dataclass
class Ident(Pattern):
    value: str

    def __str__(self) -> str:
        return f"{self.value}"


@dataclass
class Ignore(Pattern):
    pass

    def __str__(self) -> str:
        return "_"


@dataclass
class Tuple(Pattern):
    patterns: list[Pattern]

    def __str__(self) -> str:
        return f"({', '.join(map(str, self.patterns))})"


@dataclass
class Struct(Pattern):
    from parse.atom import Path

    ty: Path
    fields: list[tuple[Ident, Pattern]]

    def __str__(self) -> str:
        return f"{self.ty} {{ {', '.join(map(lambda x: f'{x[0]}: {x[1]}', self.fields))} }}"


@dataclass
class Value(Pattern):
    value: Expr

    def __str__(self) -> str:
        return f"{self.value}"
