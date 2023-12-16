from dataclasses import dataclass
from parse.atom import Atom, Path
from error import Error
from collections.abc import Generator

from parse.expr import Expr, Unrecoverable
import lex
from lex import Lexer
from parse.pattern import Pattern
from parse.semi import Semi
from parse import ty
from parse.ty import Ty


@dataclass
class Items(Expr):
    items: list["Item"]

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        items: list[Item] = []
        items = []
        while lexer.peek() is not None:
            item = yield from Item.parse(lexer)
            match item:
                case Item():
                    items.append(item)
                case _:
                    yield Error(
                        "Unexpected token",
                        item.span,
                        "Expected a declaration, found this instead",
                    )
            match lexer.peek():
                case lex.Token(span):
                    yield Error(
                        "Unexpected token",
                        span,
                        "Expected a declaration, found this instead",
                    )
                case None:
                    pass
        if len(items) == 0:
            span = slice(lexer.offset, lexer.offset)
        else:
            span = slice(items[0].span.start, items[-1].span.stop)
        return Items(span, items)


@dataclass
class Item(Expr):
    public: bool

    @staticmethod
    def file(lexer: Lexer) -> Generator[Error, None, list["Item"]]:
        items: list[Item] = []
        items = []
        while lexer.peek() is not None:
            item = yield from Semi.parse(lexer)
            match item:
                case Item():
                    items.append(item)
                case Semi(span, Item() as inner):
                    inner.span = span
                    items.append(inner)
                case _:
                    print(item)
                    yield Error(
                        "Unexpected token",
                        item.span,
                        "Expected a declaration, found this instead",
                    )
                    lexer.offset = item.span.stop
        return items

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        match lexer.peek():
            case lex.Ident(_, "pub"):
                lexer.next()
                val = yield from Item.parse(lexer)
                match val:
                    case Item():
                        val.public = True
                    case _:
                        pass
                return val
            case lex.Ident(start_span, "fn"):
                lexer.next()
                match lexer.next():
                    case lex.Ident(_, name):
                        pass
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected an identifier, found this instead",
                        )
                        return Unrecoverable(start_span)
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected an identifier, found end of file instead",
                        )
                        return Unrecoverable(start_span)
                params = []
                match lexer.next():
                    case lex.Group(_, "()", inner):
                        while inner.peek() is not None:
                            pat = Pattern.parse(inner)
                            match inner.peek():
                                case lex.Ident(_, ":"):
                                    inner.next()
                                    type = Ty.parse(inner)
                                    params.append((pat, type))
                                case lex.Token(span):
                                    yield Error(
                                        "Unexpected token",
                                        span,
                                        "Expected ':', found this instead",
                                    )
                                case None:
                                    yield Error(
                                        "Unexpected end of file",
                                        slice(inner.offset, len(inner.file)),
                                        "Expected ':', found end of file instead",
                                    )
                            match inner.peek():
                                case lex.Punct(_, ","):
                                    inner.next()
                                case lex.Token(span):
                                    yield Error(
                                        "Unexpected token",
                                        span,
                                        "Expected ',', found this instead",
                                    )
                                case None:
                                    assert False, "Unreachable"
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected '(', found this instead",
                        )
                        return Unrecoverable(slice(start_span.start, lexer.offset))
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected '(', found end of file instead",
                        )
                        return Unrecoverable(slice(start_span.start, lexer.offset))
                match lexer.peek():
                    case lex.Punct(_, "->"):
                        lexer.next()
                        ret_ty = yield from Ty.parse(lexer)
                    case _:
                        ret_ty = None
                body = yield from Expr.parse(lexer)
                return Function(start_span, False, name, params, ret_ty, body)
            case lex.Ident(start_span, "use"):
                lexer.next()
                match (yield from Atom.path(lexer)):
                    case Path(_, segments):
                        match lexer.peek():
                            case lex.Ident(_, "as"):
                                lexer.next()
                                match lexer.next():
                                    case lex.Ident(_, alias):
                                        pass
                                    case lex.Token(span):
                                        yield Error(
                                            "Unexpected token",
                                            span,
                                            "Expected an identifier, found this instead",
                                        )
                                        return Unrecoverable(start_span)
                                    case None:
                                        yield Error(
                                            "Unexpected end of file",
                                            slice(lexer.offset, len(lexer.file)),
                                            "Expected an identifier, found end of file instead",
                                        )
                                        return Unrecoverable(start_span)
                            case _:
                                alias = None
                        return Use(
                            slice(start_span.start, lexer.offset),
                            False,
                            [str(s) for s in segments],
                            alias,
                        )
                    case Unrecoverable(span):
                        return Unrecoverable(span)
                    case _:
                        assert False, "Unreachable"
            case lex.Ident(start_span, "mod"):
                lexer.next()
                match lexer.next():
                    case lex.Ident(_, name):
                        pass
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected an identifier, found this instead",
                        )
                        return Unrecoverable(start_span)
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected an identifier, found end of file instead",
                        )
                        return Unrecoverable(start_span)
                match lexer.peek():
                    case lex.Group(_, "{}", inner):
                        items = yield from Item.file(inner)
                        return ModDef(
                            slice(start_span.start, lexer.offset), False, name, items
                        )
                    case _:
                        return ModDecl(
                            slice(start_span.start, lexer.offset), False, name
                        )
            case (
                lex.Ident(start_span, "static") | lex.Ident(start_span, "const")
            ) as start:
                lexer.next()
                match lexer.next():
                    case lex.Ident(_, name):
                        pass
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected an identifier, found this instead",
                        )
                        return Unrecoverable(start_span)
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected an identifier, found end of file instead",
                        )
                        return Unrecoverable(start_span)
                match lexer.peek():
                    case lex.Punct(_, ":"):
                        lexer.next()
                        type = yield from Ty.parse(lexer)
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected ':', found this instead",
                            "hint: static and const declarations must have a known type",
                        )
                        type = ty.Unrecoverable(span)
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected ':', found end of file instead",
                            "hint: static and const declarations must have a known type",
                        )
                        type = ty.Unrecoverable(slice(start_span.start, lexer.offset))
                match lexer.peek():
                    case lex.Punct(_, "="):
                        lexer.next()
                        value = yield from Expr.parse(lexer)
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected '=', found this instead",
                            "hint: static and const declarations must have a value",
                        )
                        return Unrecoverable(slice(start_span.start, lexer.offset))
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected '=', found end of file instead",
                            "hint: static and const declarations must have a value",
                        )
                        return Unrecoverable(slice(start_span.start, lexer.offset))
                match start.value:
                    case "static":
                        return Static(start_span, False, name, type, value)
                    case "const":
                        return Const(start_span, False, name, type, value)
                    case _:
                        assert False, "Unreachable"
            case lex.Ident(start_span, "struct"):
                lexer.next()
                match lexer.next():
                    case lex.Ident(_, name):
                        pass
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected an identifier, found this instead",
                        )
                        return Unrecoverable(start_span)
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected an identifier, found end of file instead",
                        )
                        return Unrecoverable(start_span)
                fields = yield from Fields.parse(lexer)
                return Struct(start_span, False, name, fields)
            case lex.Ident(start_span, "enum"):
                lexer.next()
                match lexer.next():
                    case lex.Ident(_, name):
                        pass
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected an identifier, found this instead",
                        )
                        return Unrecoverable(start_span)
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected an identifier, found end of file instead",
                        )
                        return Unrecoverable(start_span)
                match lexer.next():
                    case lex.Group(_, "{}", inner):
                        variants = []
                        while inner.peek() is not None:
                            match inner.next():
                                case lex.Ident(_, name):
                                    pass
                                case lex.Token(span):
                                    yield Error(
                                        "Unexpected token",
                                        span,
                                        "Expected an identifier, found this instead",
                                    )
                                    return Unrecoverable(start_span)
                                case None:
                                    yield Error(
                                        "Unexpected end of file",
                                        slice(lexer.offset, len(lexer.file)),
                                        "Expected an identifier, found end of file instead",
                                    )
                                    return Unrecoverable(start_span)
                            fields = yield from Fields.parse(inner)
                            variants.append((name, fields))
                            match inner.peek():
                                case lex.Punct(_, ","):
                                    inner.next()
                                case lex.Token(span):
                                    yield Error(
                                        "Unexpected token",
                                        span,
                                        "Expected ',', found this instead",
                                    )
                                    return Unrecoverable(start_span)
                                case None:
                                    pass
                        return Enum(start_span, False, name, variants)
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected '{', found this instead",
                        )
                        return Unrecoverable(start_span)
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected '{', found end of file instead",
                        )
                        return Unrecoverable(start_span)
            case lex.Ident(start_span, "union"):
                lexer.next()
                match lexer.next():
                    case lex.Ident(_, name):
                        pass
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected an identifier, found this instead",
                        )
                        return Unrecoverable(start_span)
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected an identifier, found end of file instead",
                        )
                        return Unrecoverable(start_span)
                fields = []
                match lexer.peek():
                    case lex.Group(_, "{}", inner):
                        lexer.next()
                        fields = yield from Fields.named(inner)
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected '{', found this instead",
                            "help: unions must have at least one field",
                        )
                        return Unrecoverable(start_span)
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected '{', found end of file instead",
                            "help: unions must have at least one field",
                        )
                        return Unrecoverable(start_span)
                return Union(start_span, False, name, fields)
            case _:
                from parse.flow import Flow

                return (yield from Flow.parse(lexer))


@dataclass
class Use(Item):
    segments: list[str]
    alias: str | None

    def __str__(self) -> str:
        return f"use {'::'.join(self.segments)}"


@dataclass
class ModDecl(Item):
    name: str

    def __str__(self) -> str:
        return f"mod {self.name}"


@dataclass
class ModDef(Item):
    name: str
    items: list[Item]

    def __str__(self) -> str:
        items = "\n".join(str(item) for item in self.items)
        return f"mod {self.name} {{\n{items}\n}}"


@dataclass
class Function(Item):
    from parse.pattern import Pattern

    name: str
    params: list[tuple[Pattern, Ty]]
    ret_ty: Ty | None
    body: Expr

    def __str__(self) -> str:
        params = ", ".join(f"{pat}: {ty}" for pat, ty in self.params)
        ret_ty = f" -> {self.ret_ty}" if self.ret_ty else ""
        return f"fn {self.name}({params}){ret_ty} {self.body}"


@dataclass
class Static(Item):
    name: str
    ty: Ty
    value: Expr

    def __str__(self) -> str:
        return f"static {self.name}: {self.ty} = {self.value}"


@dataclass
class Const(Item):
    name: str
    ty: Ty
    value: Expr

    def __str__(self) -> str:
        return f"const {self.name}: {self.ty} = {self.value}"


@dataclass
class Fields:
    span: slice

    @staticmethod
    def named(lexer: Lexer) -> Generator[Error, None, list[tuple[str, Ty]]]:
        fields: list[tuple[str, Ty]] = []
        while lexer.peek() is not None:
            match lexer.next():
                case lex.Ident(span, name):
                    match lexer.peek():
                        case lex.Punct(_, ":"):
                            lexer.next()
                            type = yield from Ty.parse(lexer)
                            fields.append((name, type))
                        case lex.Token(span):
                            yield Error(
                                "Unexpected token",
                                span,
                                "Expected ':', found this instead",
                            )
                        case None:
                            yield Error(
                                "Unexpected end of file",
                                slice(lexer.offset, len(lexer.file)),
                                "Expected ':', found end of file instead",
                            )
                case lex.Token(span):
                    yield Error(
                        "Unexpected token",
                        span,
                        "Expected an identifier, found this instead",
                    )
                case None:
                    pass
            match lexer.peek():
                case lex.Punct(_, ","):
                    lexer.next()
                case lex.Token(span):
                    yield Error(
                        "Unexpected token",
                        span,
                        "Expected ',', found this instead",
                    )
                case None:
                    pass
        return fields

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, "Fields"]:
        match lexer.peek():
            case lex.Group(span, "()", inner):
                lexer.next()
                return Tuple(span, (yield from Ty.comma_separated(inner)))
            case lex.Group(span, "{}", inner):
                lexer.next()
                return Named(span, (yield from Fields.named(inner)))
            case _:
                return Unit(slice(lexer.offset, lexer.offset))


@dataclass
class Unit(Fields):
    def __str__(self) -> str:
        return ""


@dataclass
class Tuple(Fields):
    tys: list[Ty]

    def __str__(self) -> str:
        tys = ", ".join(str(ty) for ty in self.tys)
        return f"({tys})"


@dataclass
class Named(Fields):
    tys: list[tuple[str, Ty]]

    def __str__(self) -> str:
        tys = ", ".join(f"{name}: {ty}" for name, ty in self.tys)
        return f"{{ {tys} }}"


@dataclass
class Struct(Item):
    name: str
    fields: Fields

    def __str__(self) -> str:
        return f"struct {self.name}{' ' if isinstance(self.fields, Named) else ''}{self.fields}"


@dataclass
class Enum(Item):
    name: str
    variants: list[tuple[str, Fields]]

    def __str__(self) -> str:
        variants = "\n".join(
            f"{name}{' ' if isinstance(fields, Named) else ''}{fields}"
            for name, fields in self.variants
        )
        return f"enum {self.name} {{\n{variants}\n}}"


@dataclass
class Union(Item):
    name: str
    fields: list[tuple[str, Ty]]

    def __str__(self) -> str:
        fields = ", ".join(f"{name}: {ty}" for name, ty in self.fields)
        return f"union {self.name} {{ {fields} }}"
