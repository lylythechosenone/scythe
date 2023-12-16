from dataclasses import dataclass
from collections.abc import Generator
from error import Error

import lex
from lex import Lexer


@dataclass
class Ty:
    span: slice

    @staticmethod
    def continue_path(lexer: Lexer) -> Generator[Error, None, list[str]]:
        segments: list[str] = []
        while True:
            match lexer.peek():
                case lex.Punct(_, "::"):
                    lexer.next()
                    match lexer.peek():
                        case lex.Ident(_, value):
                            lexer.next()
                            segments.append(value)
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
    def comma_separated(lexer: Lexer) -> Generator[Error, None, list["Ty"]]:
        tys: list[Ty] = []
        while lexer.peek() != None:
            tys.append((yield from Ty.parse(lexer)))
            match lexer.peek():
                case lex.Punct(_, ","):
                    lexer.next()
                case lex.Token(span):
                    yield Error(
                        "Unexpected token",
                        span,
                        "Expected a comma, found this instead",
                    )
                case None:
                    pass
        return tys

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, "Ty"]:
        match lexer.next():
            case lex.Ident(span, val):
                segments = [val] + (yield from Ty.continue_path(lexer))
                return Path(slice(span.start, lexer.offset), segments)
            case lex.Ident(span, "i8"):
                return Int(slice(span.start, lexer.offset), 8, True)
            case lex.Ident(span, "i16"):
                return Int(slice(span.start, lexer.offset), 16, True)
            case lex.Ident(span, "i32"):
                return Int(slice(span.start, lexer.offset), 32, True)
            case lex.Ident(span, "i64"):
                return Int(slice(span.start, lexer.offset), 64, True)
            case lex.Ident(span, "i128"):
                return Int(slice(span.start, lexer.offset), 128, True)
            case lex.Ident(span, "u8"):
                return Int(slice(span.start, lexer.offset), 8, False)
            case lex.Ident(span, "u16"):
                return Int(slice(span.start, lexer.offset), 16, False)
            case lex.Ident(span, "u32"):
                return Int(slice(span.start, lexer.offset), 32, False)
            case lex.Ident(span, "u64"):
                return Int(slice(span.start, lexer.offset), 64, False)
            case lex.Ident(span, "u128"):
                return Int(slice(span.start, lexer.offset), 128, False)
            case lex.Ident(span, "f32"):
                return Float(slice(span.start, lexer.offset), 32)
            case lex.Ident(span, "f64"):
                return Float(slice(span.start, lexer.offset), 64)
            case lex.Ident(span, "str"):
                return Str(slice(span.start, lexer.offset))
            case lex.Ident(span, "bool"):
                return Bool(slice(span.start, lexer.offset))
            case lex.Ident(span, "char"):
                return Char(slice(span.start, lexer.offset))
            case lex.Ident(span, "usize"):
                return Size(slice(span.start, lexer.offset), False)
            case lex.Ident(span, "isize"):
                return Size(slice(span.start, lexer.offset), True)
            case lex.Ident(span, "Self"):
                return Self(slice(span.start, lexer.offset))
            case lex.Punct(span, "*"):
                ty = yield from Ty.parse(lexer)
                return Ptr(slice(span.start, lexer.offset), ty)
            case lex.Group(span, "()", inner):
                lexer.next()
                tys = yield from Ty.comma_separated(inner)
                if not inner.is_empty():
                    yield Error(
                        "Unexpected tokens",
                        slice(inner.offset, len(inner.file)),
                        "Expected a closing bracket, found these tokens instead",
                    )
                return Tuple(slice(span.start, lexer.offset), tys)
            case lex.Group(span, "[]", inner):
                lexer.next()
                ty = yield from Ty.parse(inner)
                match inner.next():
                    case lex.Punct(_, ";"):
                        match inner.next():
                            case lex.Int(span, value, None):
                                return Array(
                                    slice(span.start, lexer.offset), ty, int(value)
                                )
                            case lex.Token(span):
                                yield Error(
                                    "Unexpected token",
                                    span,
                                    "Expected an integer, found this instead",
                                )
                                return Array(slice(span.start, lexer.offset), ty, 0)
                            case None:
                                yield Error(
                                    "Unexpected end of file",
                                    slice(inner.offset, len(inner.file)),
                                    "Expected an integer, found end of file instead",
                                )
                                return Array(slice(span.start, lexer.offset), ty, 0)
                    case None:
                        pass
                    case _:
                        yield Error(
                            "Unexpected tokens",
                            slice(inner.offset, len(inner.file)),
                            "Expected a closing bracket, found these tokens instead",
                        )
                return Slice(slice(span.start, lexer.offset), ty)
            case _:
                raise NotImplementedError


@dataclass
class Int(Ty):
    size: int
    signed: bool

    def __str__(self) -> str:
        return f"{'i' if self.signed else 'u'}{self.size}"


@dataclass
class Size(Ty):
    signed: bool

    def __str__(self) -> str:
        if self.signed:
            return "isize"
        else:
            return "usize"


@dataclass
class Float(Ty):
    size: int

    def __str__(self) -> str:
        return f"f{self.size}"


@dataclass
class Str(Ty):
    def __str__(self) -> str:
        return "str"


@dataclass
class Bool(Ty):
    def __str__(self) -> str:
        return "bool"


@dataclass
class Char(Ty):
    def __str__(self) -> str:
        return "char"


@dataclass
class Self(Ty):
    def __str__(self) -> str:
        return "Self"


@dataclass
class Unit(Ty):
    def __str__(self) -> str:
        return "()"


@dataclass
class Ptr(Ty):
    ty: Ty

    def __str__(self) -> str:
        return f"*{self.ty}"


@dataclass
class Tuple(Ty):
    tys: list[Ty]

    def __str__(self) -> str:
        return f"({', '.join(map(str, self.tys))})"


@dataclass
class Array(Ty):
    ty: Ty
    size: int

    def __str__(self) -> str:
        return f"[{self.ty}; {self.size}]"


@dataclass
class Slice(Ty):
    ty: Ty

    def __str__(self) -> str:
        return f"[{self.ty}]"


@dataclass
class Path(Ty):
    segments: list[str]

    def __str__(self) -> str:
        return "::".join(self.segments)


@dataclass
class Unrecoverable(Ty):
    def __str__(self) -> str:
        return "{error}"
