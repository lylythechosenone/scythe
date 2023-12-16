from dataclasses import dataclass
from collections.abc import Generator
from error import Error
from parse.expr import Expr, Unrecoverable
import lex
from lex import Lexer


@dataclass
class Atom(Expr):
    @staticmethod
    def continue_path(lexer: Lexer) -> Generator[Error, None, list["Ident"]]:
        segments: list[Ident] = []
        while True:
            match lexer.peek():
                case lex.Punct(_, "::"):
                    lexer.next()
                    match lexer.peek():
                        case lex.Ident(span, value):
                            lexer.next()
                            segments.append(Ident(span, value))
                        case lex.Token(span):
                            yield Error(
                                "Unexpected token",
                                span,
                                "Expected an identifier, found this instead",
                            )
                            return segments
                        case None:
                            yield Error(
                                "Unexpected end of file",
                                slice(lexer.offset, len(lexer.file)),
                                "Expected an identifier, found end of file instead",
                            )
                            return segments
                case _:
                    return segments

    @staticmethod
    def path(lexer: Lexer) -> Generator[Error, None, "Expr"]:
        match lexer.next():
            case lex.Ident(span, value):
                segments = [Ident(span, value)] + (yield from Atom.continue_path(lexer))
                path = Path(slice(span.start, lexer.offset), segments)
                return path
            case lex.Token(span):
                yield Error(
                    "Unexpected token",
                    span,
                    "Expected an identifier, found this instead",
                )
                return Unrecoverable(span)
            case None:
                yield Error(
                    "Unexpected end of file",
                    slice(lexer.offset, len(lexer.file)),
                    "Expected an identifier, found end of file instead",
                )
                return Unrecoverable(slice(lexer.offset, lexer.offset + 1))

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        match lexer.next():
            case lex.Ident(span, value):
                segments = [Ident(span, value)] + (yield from Atom.continue_path(lexer))
                path = Path(slice(span.start, lexer.offset), segments)
                match lexer.peek():
                    case lex.Group(block_span, "{}", inner):
                        lexer.next()
                        start = span.start
                        fields = []
                        while inner.peek() != None:
                            match inner.next():
                                case lex.Ident(span, name):
                                    match inner.next():
                                        case lex.Punct(_, ":"):
                                            fields.append(
                                                (
                                                    Ident(span, name),
                                                    (yield from Expr.parse(inner)),
                                                )
                                            )
                                            match inner.peek():
                                                case lex.Punct(_, ",") | None:
                                                    inner.next()
                                                case lex.Token(span):
                                                    yield Error(
                                                        "Unexpected token",
                                                        span,
                                                        "Expected a comma or closing brace, found this instead",
                                                    )
                                                    break
                                        case lex.Token(span):
                                            yield Error(
                                                "Unexpected token",
                                                span,
                                                "Expected a colon, found this instead",
                                            )
                                            fields.append(
                                                (
                                                    Ident(span, name),
                                                    Unrecoverable(slice(0, 0)),
                                                )
                                            )
                                            break
                                        case None:
                                            yield Error(
                                                "Unexpected end of file",
                                                slice(inner.offset, len(inner.file)),
                                                "Expected a colon, found end of file instead",
                                            )
                                            fields.append(
                                                (
                                                    Ident(span, name),
                                                    Unrecoverable(slice(0, 0)),
                                                )
                                            )
                                            break
                                case lex.Token(span):
                                    yield Error(
                                        "Unexpected token",
                                        span,
                                        "Expected an identifier, found this instead",
                                    )
                                    break
                                case None:
                                    yield Error(
                                        "Unexpected end of file",
                                        slice(inner.offset, len(inner.file)),
                                        "Expected an identifier, found end of file instead",
                                    )
                                    break
                        return StructInit(
                            slice(start, lexer.offset), path, block_span, fields
                        )
                    case _:
                        if len(segments) > 1:
                            return path
                        else:
                            return Ident(span, value)
            case lex.String(span, value):
                return String(span, value)
            case lex.Char(span, value):
                return Char(span, value)
            case lex.Int(span, value, type_hint):
                return Int(span, value, type_hint)
            case lex.Float(span, value, type_hint):
                return Float(span, value, type_hint)
            case lex.Group(span, "()", inner):
                if inner.is_empty():
                    return Tuple(span, [])
                expr = yield from Expr.parse(inner)
                if not inner.is_empty():
                    match inner.peek():
                        case lex.Punct(_, ","):
                            inner.next()
                            exprs = [expr] + (yield from Expr.comma_separated(inner))
                            return Tuple(span, exprs)
                        case _:
                            yield Error(
                                "Unexpected tokens",
                                slice(inner.offset, len(inner.file)),
                                "Expected a closing parenthesis, found these tokens instead",
                            )
                return expr
            case lex.Group(span, "{}", inner):
                from semi import Semi

                exprs = []
                while inner.peek() != None:
                    exprs.append((yield from Semi.parse(inner)))
                return Block(span, exprs)
            case lex.Token(span):
                yield Error(
                    "Expected an expression",
                    span,
                    "Expected an expression, found this instead",
                )
                return Unrecoverable(span)
            case None:
                yield Error(
                    "Expected an expression",
                    slice(lexer.offset, lexer.offset + 1),
                    "Expected an expression, found end of file instead",
                )
                return Unrecoverable(slice(lexer.offset, lexer.offset + 1))


@dataclass
class Path(Atom):
    segments: list["Ident"]

    def __str__(self) -> str:
        return "::".join(map(str, self.segments))


@dataclass
class Ident(Atom):
    value: str

    def __str__(self) -> str:
        return f"{self.value}"


@dataclass
class String(Atom):
    value: str

    def __str__(self) -> str:
        return f'"{self.value}"'


@dataclass
class Char(Atom):
    value: str

    def __str__(self) -> str:
        return f"'{self.value}'"


@dataclass
class Int(Atom):
    value: int
    type_hint: str | None

    def __str__(self) -> str:
        return f"{self.value}"


@dataclass
class Float(Atom):
    value: float
    type_hint: str | None

    def __str__(self) -> str:
        return f"{self.value}"


@dataclass
class Block(Atom):
    exprs: list[Expr]

    def __str__(self) -> str:
        if len(self.exprs) > 2:
            return "{\n    " + "\n    ".join(map(str, self.exprs)) + "\n}"
        else:
            return "{ " + " ".join(map(str, self.exprs)) + " }"


@dataclass
class Tuple(Atom):
    exprs: list[Expr]

    def __str__(self) -> str:
        return "(" + ", ".join(map(str, self.exprs)) + ")"


@dataclass
class StructInit(Atom):
    ty: Path
    block_span: slice
    fields: list[tuple[Ident, Expr]]

    def __str__(self) -> str:
        return (
            f"{self.ty} "
            + "{"
            + ", ".join(f"{name}: {expr}" for name, expr in self.fields)
            + "}"
        )
