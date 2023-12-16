from dataclasses import dataclass
from error import Error
from collections.abc import Generator

from expr import Expr
import lex
from lex import Lexer


include_struct_init = True


@dataclass
class Binary(Expr):
    lhs: Expr
    rhs: Expr

    @staticmethod
    def factor(lexer: Lexer) -> Generator[Error, None, Expr]:
        from parse.prefix import Prefix

        expr = yield from Prefix.parse(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "*"):
                    lexer.next()
                    expr = Mul(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Prefix.parse(lexer)),
                    )
                case lex.Punct(_, "/"):
                    lexer.next()
                    expr = Div(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Prefix.parse(lexer)),
                    )
                case lex.Punct(_, "%"):
                    lexer.next()
                    expr = Mod(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Prefix.parse(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def term(lexer: Lexer) -> Generator[Error, None, Expr]:
        expr = yield from Binary.factor(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "+"):
                    lexer.next()
                    expr = Add(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.factor(lexer)),
                    )
                case lex.Punct(_, "-"):
                    lexer.next()
                    expr = Sub(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.factor(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def shift(lexer: Lexer) -> Generator[Error, None, Expr]:
        expr = yield from Binary.term(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "<<"):
                    lexer.next()
                    expr = Shl(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.term(lexer)),
                    )
                case lex.Punct(_, ">>"):
                    lexer.next()
                    expr = Shr(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.term(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def bit_and(lexer: Lexer) -> Generator[Error, None, Expr]:
        expr = yield from Binary.shift(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "&"):
                    lexer.next()
                    expr = BitAnd(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.shift(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def bit_xor(lexer: Lexer) -> Generator[Error, None, Expr]:
        expr = yield from Binary.bit_and(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "^"):
                    lexer.next()
                    expr = BitXor(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.bit_and(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def bit_or(lexer: Lexer) -> Generator[Error, None, Expr]:
        expr = yield from Binary.bit_xor(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "|"):
                    lexer.next()
                    expr = BitOr(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.bit_xor(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def compare(lexer: Lexer) -> Generator[Error, None, Expr]:
        expr = yield from Binary.bit_or(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "=="):
                    lexer.next()
                    expr = Eq(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.bit_or(lexer)),
                    )
                case lex.Punct(_, "!="):
                    lexer.next()
                    expr = Ne(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.bit_or(lexer)),
                    )
                case lex.Punct(_, "<"):
                    lexer.next()
                    expr = Lt(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.bit_or(lexer)),
                    )
                case lex.Punct(_, "<="):
                    lexer.next()
                    expr = Le(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.bit_or(lexer)),
                    )
                case lex.Punct(_, ">"):
                    lexer.next()
                    expr = Gt(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.bit_or(lexer)),
                    )
                case lex.Punct(_, ">="):
                    lexer.next()
                    expr = Ge(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.bit_or(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def logical_and(lexer: Lexer) -> Generator[Error, None, Expr]:
        expr = yield from Binary.compare(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "&&"):
                    lexer.next()
                    expr = And(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.compare(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def logical_or(lexer: Lexer) -> Generator[Error, None, Expr]:
        expr = yield from Binary.logical_and(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "||"):
                    lexer.next()
                    expr = Or(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.logical_and(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def assign(lexer: Lexer) -> Generator[Error, None, Expr]:
        expr = yield from Binary.logical_or(lexer)

        while lexer.peek() != None:
            match lexer.peek():
                case lex.Punct(_, "="):
                    lexer.next()
                    expr = Assign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, "+="):
                    lexer.next()
                    expr = AddAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, "-="):
                    lexer.next()
                    expr = SubAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, "*="):
                    lexer.next()
                    expr = MulAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, "/="):
                    lexer.next()
                    expr = DivAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, "%="):
                    lexer.next()
                    expr = ModAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, "&="):
                    lexer.next()
                    expr = BitAndAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, "|="):
                    lexer.next()
                    expr = BitOrAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, "^="):
                    lexer.next()
                    expr = BitXorAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, "<<="):
                    lexer.next()
                    expr = ShlAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case lex.Punct(_, ">>="):
                    lexer.next()
                    expr = ShrAssign(
                        slice(expr.span.start, lexer.offset),
                        expr,
                        (yield from Binary.assign(lexer)),
                    )
                case _:
                    return expr
        return expr

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, Expr]:
        return Binary.assign(lexer)


@dataclass
class Add(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} + {self.rhs})"


@dataclass
class Sub(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} - {self.rhs})"


@dataclass
class Mul(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} * {self.rhs})"


@dataclass
class Div(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} / {self.rhs})"


@dataclass
class Mod(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} % {self.rhs})"


@dataclass
class Eq(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} == {self.rhs})"


@dataclass
class Ne(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} != {self.rhs})"


@dataclass
class Lt(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} < {self.rhs})"


@dataclass
class Le(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} <= {self.rhs})"


@dataclass
class Gt(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} > {self.rhs})"


@dataclass
class Ge(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} >= {self.rhs})"


@dataclass
class And(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} && {self.rhs})"


@dataclass
class Or(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} || {self.rhs})"


@dataclass
class BitAnd(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} & {self.rhs})"


@dataclass
class BitOr(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} | {self.rhs})"


@dataclass
class BitXor(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} ^ {self.rhs})"


@dataclass
class Shl(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} << {self.rhs})"


@dataclass
class Shr(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} >> {self.rhs})"


@dataclass
class Assign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} = {self.rhs})"


@dataclass
class AddAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} += {self.rhs})"


@dataclass
class SubAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} -= {self.rhs})"


@dataclass
class MulAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} *= {self.rhs})"


@dataclass
class DivAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} /= {self.rhs})"


@dataclass
class ModAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} %= {self.rhs})"


@dataclass
class BitAndAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} &= {self.rhs})"


@dataclass
class BitOrAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} |= {self.rhs})"


@dataclass
class BitXorAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} ^= {self.rhs})"


@dataclass
class ShlAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} <<= {self.rhs})"


@dataclass
class ShrAssign(Binary):
    def __str__(self) -> str:
        return f"({self.lhs} >>= {self.rhs})"
