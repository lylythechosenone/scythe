from dataclasses import dataclass
from collections.abc import Generator
from error import Error

import lex
from lex import Lexer


@dataclass
class Expr:
    span: slice

    @staticmethod
    def parse(lexer: Lexer) -> Generator[Error, None, "Expr"]:
        from parse.item import Item

        expr = yield from Item.parse(lexer)

        return expr

    @staticmethod
    def comma_separated(lexer: Lexer) -> Generator[Error, None, list["Expr"]]:
        exprs: list[Expr] = []
        while lexer.peek() is not None:
            expr = yield from Expr.parse(lexer)
            exprs.append(expr)
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
        return exprs


@dataclass
class Unrecoverable(Expr):
    def __str__(self) -> str:
        return "{error}"


class Catcher:
    result: Expr | None = None

    def catch(
        self, generator: Generator[Error, None, Expr]
    ) -> Generator[Error, None, None]:
        self.result = yield from generator


if __name__ == "__main__":
    file = """
    struct Foo;
    struct Bar(i32);
    struct Baz {
        x: i32,
        y: i32,
    }

    enum Qux {
        A,
        B(i32),
        C { x: i32, y: i32 },
    }

    union Quux {
        a: i32,
        b: u32,
    }
    """
    lexer = Lexer(file)
    while not lexer.is_empty():
        catcher = Catcher()
        try:
            from parse.semi import Semi

            errors = catcher.catch(Semi.parse(lexer))
        except Error as e:
            print(e.display(file, True))
            break
        for error in errors:
            print(error.display(file, False))
        print(catcher.result)
