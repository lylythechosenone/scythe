from dataclasses import dataclass
from collections.abc import Generator
from parse.atom import StructInit
from parse.binary import Binary
from cont import Cont
from error import Error
from expr import Catcher, Expr
from parse.let import Let
import lex
from lex import Lexer
from parse.prefix import Prefix
from parse.suffix import Suffix


@dataclass
class Flow(Expr):
    @staticmethod
    def fix_improper_struct_init(
        lexer: Lexer, expr: Expr, errors: list[Error]
    ) -> Generator[Error, None, Expr]:
        match expr:
            case Binary(
                _,
                _,
                StructInit() as rhs,
            ) as binary:
                binary.rhs = yield from Flow.fix_improper_struct_init(
                    lexer, rhs, errors
                )
                return binary
            case Prefix(
                _,
                StructInit() as rhs,
            ) as prefix:
                prefix.rhs = yield from Flow.fix_improper_struct_init(
                    lexer, rhs, errors
                )
                return prefix
            case Suffix(
                _,
                StructInit() as base,
            ) as suffix:
                suffix.base = yield from Flow.fix_improper_struct_init(
                    lexer, base, errors
                )
                return suffix
            case Let(_, _, _, StructInit() as value, None) as let:
                let.value = yield from Flow.fix_improper_struct_init(
                    lexer, value, errors
                )
                return let
            case Let(_, _, _, _, StructInit() as else_) as let:
                let.else_ = yield from Flow.fix_improper_struct_init(
                    lexer, else_, errors
                )
                return let
            case StructInit(
                span,
                path,
                block_span,
            ) if len(errors) > 0:
                errors.pop()
                yield from errors
                lexer.rewind_before(block_span)
                return path
            case StructInit(
                span,
                path,
                block_span,
            ) as cond:
                yield Error(
                    "Struct initializer not allowed here",
                    span,
                    "Struct initializers are not allowed as if conditions. "
                    "Use a variable or wrap the intializer in parentheses.",
                )
                return cond
            case _:
                yield from errors
                return expr

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        match lexer.peek():
            case lex.Ident(start_span, "if"):
                lexer.next()
                catcher = Catcher()
                errors = [e for e in catcher.catch(Expr.parse(lexer))]
                if catcher.result is None:
                    assert False, "Unreachable"
                cond = yield from Flow.fix_improper_struct_init(
                    lexer, catcher.result, errors
                )
                then = yield from Expr.parse(lexer)
                match lexer.peek():
                    case lex.Ident(_, "else"):
                        lexer.next()
                        else_ = yield from Expr.parse(lexer)
                        return If(
                            slice(start_span.start, lexer.offset), cond, then, else_
                        )
                    case _:
                        return If(
                            slice(start_span.start, lexer.offset), cond, then, None
                        )
            case lex.Ident(start_span, "while"):
                lexer.next()
                cond = yield from Expr.parse(lexer)
                body = yield from Expr.parse(lexer)
                return While(slice(start_span.start, lexer.offset), cond, body)
            case lex.Ident(start_span, "for"):
                from pattern import Pattern

                lexer.next()
                pat = yield from Pattern.parse(lexer)
                match lexer.next():
                    case lex.Ident(_, "in"):
                        pass
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected 'in', found this instead",
                        )
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected 'in', found end of file instead",
                        )
                itr = yield from Expr.parse(lexer)
                body = yield from Expr.parse(lexer)
                return For(slice(start_span.start, lexer.offset), pat, itr, body)
            case lex.Ident(start_span, "match"):
                from pattern import Pattern

                lexer.next()
                catcher = Catcher()
                errors = [e for e in catcher.catch(Expr.parse(lexer))]
                if catcher.result is None:
                    assert False, "Unreachable"
                cond = yield from Flow.fix_improper_struct_init(
                    lexer, catcher.result, errors
                )
                arms: list[tuple[Pattern, Expr]] = []
                match lexer.next():
                    case lex.Group(_, "{}", inner):
                        while inner.peek() is not None:
                            pat = yield from Pattern.parse(inner)
                            match inner.next():
                                case lex.Punct(_, "=>"):
                                    body = yield from Expr.parse(inner)
                                    arms.append((pat, body))
                                case lex.Token(span):
                                    yield Error(
                                        "Unexpected token",
                                        span,
                                        "Expected '=>', found this instead",
                                    )
                                case None:
                                    yield Error(
                                        "Unexpected end of file",
                                        slice(inner.offset, len(inner.file)),
                                        "Expected '=>', found end of file instead",
                                    )
                            match inner.peek():
                                case lex.Punct(_, ","):
                                    inner.next()
                                case _:
                                    pass
                    case lex.Token(span):
                        yield Error(
                            "Unexpected token",
                            span,
                            "Expected '{', found this instead",
                        )
                    case None:
                        yield Error(
                            "Unexpected end of file",
                            slice(lexer.offset, len(lexer.file)),
                            "Expected '{', found end of file instead",
                        )
                return Match(slice(start_span.start, lexer.offset), cond, arms)
            case _:
                return (yield from Cont.parse(lexer))


@dataclass
class If(Flow):
    cond: Expr
    then: Expr
    else_: Expr | None

    def __str__(self) -> str:
        if self.else_ is None:
            return f"(if {self.cond} {self.then})"
        return f"(if {self.cond} {self.then} else {self.else_})"


@dataclass
class While(Flow):
    cond: Expr
    body: Expr

    def __str__(self) -> str:
        return f"(while {self.cond} {self.body})"


@dataclass
class For(Flow):
    from pattern import Pattern

    pat: Pattern
    itr: Expr
    body: Expr

    def __str__(self) -> str:
        return f"(for {self.pat} in {self.itr} {self.body})"


@dataclass
class Match(Flow):
    from pattern import Pattern

    cond: Expr
    arms: list[tuple[Pattern, Expr]]

    def __str__(self) -> str:
        return f"(match {self.cond} {{ {' '.join(f'{pat} => {body}' for pat, body in self.arms)} }})"
