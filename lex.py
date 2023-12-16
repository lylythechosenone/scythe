from dataclasses import dataclass

from error import Error
import regex


@dataclass
class Token:
    span: slice


@dataclass
class Ident(Token):
    value: str


@dataclass
class String(Token):
    value: str


@dataclass
class Char(Token):
    value: str


@dataclass
class Int(Token):
    value: int
    type_hint: str | None


@dataclass
class Float(Token):
    value: float
    type_hint: str | None


@dataclass
class Group(Token):
    delim: str
    lexer: "Lexer"


@dataclass
class Punct(Token):
    value: str


def is_digit(c: str, radix: int) -> bool:
    try:
        int(c, radix)
        return True
    except ValueError:
        return False


@dataclass
class Lexer:
    file: str
    offset: int = 0

    def has(self, expected: str) -> bool:
        return len(self.file) > self.offset and self.file[self.offset] == expected

    def expect(self, expected: str):
        if len(self.file) <= self.offset:
            raise Error(
                "Unexpected end of file",
                slice(self.offset, self.offset),
                f"Expected {expected}",
            )
        if self.file[self.offset] != expected:
            raise Error(
                "Unexpected token",
                slice(self.offset, self.offset + 1),
                f"Expected {expected}, found this instead",
            )
        self.offset += 1

    def digits(self, radix: int) -> str:
        start = self.offset
        while True:
            try:
                if len(self.file) <= self.offset:
                    break
                int(self.file[self.offset], radix)
                self.offset += 1
            except ValueError:
                break
        return self.file[start : self.offset]

    def escape(self) -> str:
        match self.file[self.offset]:
            case "n":
                self.offset += 1
                return "\n"
            case "t":
                self.offset += 1
                return "\t"
            case "\\":
                self.offset += 1
                return "\\"
            case '"':
                self.offset += 1
                return '"'
            case "0":
                self.offset += 1
                return "\0"
            case "r":
                self.offset += 1
                return "\r"
            case "b":
                self.offset += 1
                return "\b"
            case "f":
                self.offset += 1
                return "\f"
            case "v":
                self.offset += 1
                return "\v"
            case "a":
                self.offset += 1
                return "\a"
            case "u":
                self.offset += 1
                self.expect("{")
                digits = self.digits(16)
                self.expect("}")
                return chr(int(digits, 16))
            case c:
                raise Error(
                    "Invalid escape sequence",
                    slice(self.offset, self.offset + 1),
                    f"\\{c} is not a valid escape sequence",
                )

    def string(self) -> String:
        start = self.offset
        self.offset += 1
        escape = False
        accum = ""
        while escape or self.file[self.offset] != '"':
            if self.file[self.offset] == "\\":
                escape = True
                self.offset += 1
            elif escape:
                accum += self.escape()
                escape = False
            else:
                accum += self.file[self.offset]
                self.offset += 1
        self.offset += 1
        return String(slice(start, self.offset), accum)

    def char(self) -> Char:
        start = self.offset
        self.offset += 1
        val = ""
        if self.file[self.offset] == "\\":
            self.offset += 1
            val = self.escape()
        else:
            self.offset += 1
            val = self.file[self.offset - 1]
        self.expect("'")
        return Char(slice(start, self.offset), val)

    def strip(self):
        while True:
            if self.file[self.offset : self.offset + 2] == "//":
                while len(self.file) > self.offset and self.file[self.offset] != "\n":
                    self.offset += 1
            if self.file[self.offset : self.offset + 2] == "/*":
                while (
                    len(self.file) > self.offset
                    and self.file[self.offset : self.offset + 2] != "*/"
                ):
                    self.offset += 1
                self.offset += 2
            if len(self.file) <= self.offset:
                return
            if self.file[self.offset] in (" ", "\t", "\n"):
                self.offset += 1
            else:
                return

    def int_suffix(self) -> str | None:
        if len(self.file) <= self.offset:
            return None
        if self.file[self.offset] in ("i", "u"):
            start = self.offset
            self.offset += 1
            size = self.digits(10)
            if size not in ("8", "16", "32", "64"):
                raise Error(
                    "Invalid integer suffix",
                    slice(start, self.offset + len(size)),
                    "This is not a valid integer size",
                )
            return self.file[start] + size

    def float_suffix(self) -> str | None:
        if len(self.file) <= self.offset:
            return None
        if self.file[self.offset] == "f":
            start = self.offset
            self.offset += 1
            size = self.digits(10)
            if size not in ("32", "64"):
                raise Error(
                    "Invalid float suffix",
                    slice(start, self.offset + len(size)),
                    "This is not a valid float size",
                )
            return self.file[start] + size

    def rewind_before(self, span: slice):
        self.offset = span.start

    def next(self) -> Token | None:
        self.strip()

        if len(self.file) <= self.offset:
            return None

        first = self.file[self.offset]
        match first:
            case ",":
                self.offset += 1
                return Punct(slice(self.offset - 1, self.offset), ",")
            case ":":
                self.offset += 1
                if self.has(":"):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "::")
                return Punct(slice(self.offset - 1, self.offset), ":")
            case ".":
                self.offset += 1
                return Punct(slice(self.offset - 1, self.offset), ".")
            case "-":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "-=")
                elif self.has(">"):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "->")
                return Punct(slice(self.offset - 1, self.offset), "-")
            case "+":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "+=")
                return Punct(slice(self.offset - 1, self.offset), "+")
            case "*":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "*=")
                return Punct(slice(self.offset - 1, self.offset), "*")
            case "/":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "/=")
                return Punct(slice(self.offset - 1, self.offset), "/")
            case "&":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "&=")
                elif self.has("&"):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "&&")
                return Punct(slice(self.offset - 1, self.offset), "&")
            case "!":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "!=")
                return Punct(slice(self.offset - 1, self.offset), "!")
            case "<":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "<=")
                elif self.has("<"):
                    self.offset += 1
                    if self.has("="):
                        self.offset += 1
                        return Punct(slice(self.offset - 3, self.offset), "<<=")
                    return Punct(slice(self.offset - 2, self.offset), "<<")
                return Punct(slice(self.offset - 1, self.offset), "<")
            case ">":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), ">=")
                elif self.has(">"):
                    self.offset += 1
                    if self.has("="):
                        self.offset += 1
                        return Punct(slice(self.offset - 3, self.offset), ">>=")
                    return Punct(slice(self.offset - 2, self.offset), ">>")
                return Punct(slice(self.offset - 1, self.offset), ">")
            case "^":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "^=")
                return Punct(slice(self.offset - 1, self.offset), "^")
            case "|":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "|=")
                elif self.has("|"):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "||")
                return Punct(slice(self.offset - 1, self.offset), "|")
            case "=":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "==")
                elif self.has(">"):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "=>")
                return Punct(slice(self.offset - 1, self.offset), "=")
            case ";":
                self.offset += 1
                return Punct(slice(self.offset - 1, self.offset), ";")
            case "%":
                self.offset += 1
                if self.has("="):
                    self.offset += 1
                    return Punct(slice(self.offset - 2, self.offset), "%=")
                return Punct(slice(self.offset - 1, self.offset), "%")

            case "(":
                start = self.offset
                nesting = 1
                while nesting > 0:
                    self.offset += 1
                    if len(self.file) <= self.offset:
                        raise Error(
                            "Unclosed delimiters",
                            slice(start, self.offset),
                            "Expected ')' to close this group",
                        )
                    if self.file[self.offset] == "(":
                        nesting += 1
                    elif self.file[self.offset] == ")":
                        nesting -= 1
                self.offset += 1
                return Group(
                    slice(start, self.offset),
                    "()",
                    Lexer(self.file[: self.offset - 1], start + 1),
                )
            case "[":
                start = self.offset
                nesting = 1
                while nesting > 0:
                    self.offset += 1
                    if len(self.file) <= self.offset:
                        raise Error(
                            "Unclosed delimiters",
                            slice(start, self.offset),
                            "Expected ']' to close this group",
                        )
                    if self.file[self.offset] == "[":
                        nesting += 1
                    elif self.file[self.offset] == "]":
                        nesting -= 1
                self.offset += 1
                return Group(
                    slice(start, self.offset),
                    "[]",
                    Lexer(self.file[: self.offset - 1], start + 1),
                )
            case "{":
                start = self.offset
                nesting = 1
                while nesting > 0:
                    self.offset += 1
                    if len(self.file) <= self.offset:
                        raise Error(
                            "Unclosed delimiters",
                            slice(start, self.offset),
                            "Expected '}' to close this group",
                        )
                    if self.file[self.offset] == "{":
                        nesting += 1
                    elif self.file[self.offset] == "}":
                        nesting -= 1
                self.offset += 1
                return Group(
                    slice(start, self.offset),
                    "{}",
                    Lexer(self.file[: self.offset - 1], start + 1),
                )
            case '"':
                return self.string()
            case "'":
                return self.char()
            case "0" if len(self.file) > self.offset + 1 and self.file[
                self.offset + 1
            ].lower() in ("x", "b", "o"):
                start = self.offset
                self.offset += 1
                match self.file[self.offset]:
                    case "x":
                        radix = 16
                    case "b":
                        radix = 2
                    case "o":
                        radix = 8
                    case _:
                        raise Error(
                            "Invalid radix",
                            slice(self.offset, self.offset + 1),
                            "This is not a valid radix for an integer literal",
                        )
                self.offset += 1

                digits = self.digits(radix)
                if len(digits) == 0:
                    raise Error(
                        "Invalid integer literal",
                        slice(start, self.offset),
                        "Expected digits after this prefix",
                    )

                while len(self.file) > self.offset and self.file[self.offset] == "_":
                    self.offset += 1
                    digits += self.digits(radix)

                val = int(digits, radix)

                return Int(slice(start, self.offset), val, self.int_suffix())
            case c if is_digit(c, 10):
                start = self.offset
                digits = self.digits(10)

                while len(self.file) > self.offset and self.file[self.offset] == "_":
                    self.offset += 1
                    digits += self.digits(10)

                val = int(digits, 10)

                if len(self.file) > self.offset and self.file[self.offset] == ".":
                    self.offset += 1
                    digits = self.digits(10)
                    while (
                        len(self.file) > self.offset and self.file[self.offset] == "_"
                    ):
                        self.offset += 1
                        digits += self.digits(10)
                    val += float("." + digits)
                    return Float(slice(start, self.offset), val, self.float_suffix())

                suffix = self.int_suffix()
                if suffix is None:
                    suffix = self.float_suffix()
                    if suffix is not None:
                        return Float(slice(start, self.offset), float(val), suffix)
                return Int(slice(start, self.offset), val, suffix)
            case _ if (
                match := regex.match(
                    r"^[\p{XID_Start}_]\p{XID_Continue}*", self.file[self.offset :]
                )
            ) is not None:
                self.offset += match.end()
                return Ident(slice(self.offset - match.end(), self.offset), match[0])
            case _:
                raise Error(
                    "Unexpected token",
                    slice(self.offset, self.offset + 1),
                    "This character was not understood",
                )

    def peek(self) -> Token | None:
        offset = self.offset
        token = self.next()
        self.offset = offset
        return token

    def is_empty(self) -> bool:
        self.strip()
        return len(self.file) <= self.offset


def print_tokens(file: str, indents: str = ""):
    lexer = Lexer(file)
    while (token := lexer.next()) is not None:
        match token:
            case Group(_, delim, inner):
                print(f"{indents}{delim[0]}")
                print_tokens(inner.file, indents + "    ")
                print(f"{indents}{delim[1]}")
            case _:
                print(f"{indents}{token}")
