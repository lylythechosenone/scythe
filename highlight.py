import re
import colors
import lex
from lex import Lexer

keywords = [
    "as",
    "break",
    "const",
    "continue",
    "crate",
    "else",
    "enum",
    "extern",
    "false",
    "fn",
    "for",
    "if",
    "impl",
    "in",
    "let",
    "loop",
    "match",
    "mod",
    "mut",
    "pub",
    "return",
    "self",
    "static",
    "struct",
    "super",
    "true",
    "type",
    "use",
    "where",
    "while",
]
primitives = [
    "u8",
    "u16",
    "u32",
    "u64",
    "u128",
    "i8",
    "i16",
    "i32",
    "i64",
    "i128",
    "f32",
    "f64",
    "bool",
    "str",
    "char",
    "usize",
    "isize",
    "Self",
]


def highlight_simple(text: str) -> str:
    text = re.sub(
        r"[\d_]+((\.[\d_]*)|(e[+-]?\d+))?(([ui](8|16|32|64)|f(32|64)))?",
        lambda int: colors.colorize(int.group(), colors.INT),
        text,
    )
    for keyword in keywords:
        text = re.sub(rf"\b{keyword}\b", colors.colorize(keyword, colors.KEYWORD), text)
    for primitive in primitives:
        text = re.sub(
            rf"\b{primitive}\b", colors.colorize(primitive, colors.PRIMITIVE), text
        )
    text = re.sub(
        r"//.*$",
        lambda comment: colors.colorize(comment.group(), colors.COMMENT),
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"/\*.*?\*/",
        lambda comment: colors.colorize(comment.group(), colors.COMMENT),
        text,
    )
    text = re.sub(
        r"\"(\\.|[^\"\\]|)*\"?",
        lambda string: colors.colorize(string.group(), colors.STRING),
        text,
    )
    return text


def highlight_lex(text: str, lexer: Lexer, start: int = 0) -> str:
    accum: str = ""
    last_end = start
    while (token := lexer.next()) is not None:
        match token:
            case lex.String(span):
                accum += text[last_end : span.start]
                accum += colors.colorize(text[span], colors.STRING)
                last_end = span.stop
            case lex.Int(span):
                accum += text[last_end : span.start]
                accum += colors.colorize(text[span], colors.INT)
                last_end = span.stop
            case lex.Ident(span, val) if val in keywords:
                accum += text[last_end : span.start]
                accum += colors.colorize(text[span], colors.KEYWORD)
                last_end = span.stop
            case lex.Ident(span, val) if val in primitives:
                accum += text[last_end : span.start]
                accum += colors.colorize(text[span], colors.PRIMITIVE)
                last_end = span.stop
            case lex.Group(span, _, inner):
                accum += text[last_end : inner.offset]
                accum += highlight_lex(inner.file, inner, inner.offset)
                accum += text[inner.offset : span.stop]
                last_end = span.stop
            case lex.Token(span):
                accum += text[last_end : span.stop]
                last_end = span.stop
    accum += text[last_end:]
    accum = re.sub(
        r"//.*$",
        lambda comment: colors.colorize(comment.group(), colors.COMMENT),
        accum,
        flags=re.MULTILINE,
    )
    accum = re.sub(
        r"/\*.*?\*/",
        lambda comment: colors.colorize(comment.group(), colors.COMMENT),
        accum,
    )
    return accum


def slice_ignoring_ansi(text: str, range: slice) -> str:
    logical_pos = 0
    start = 0
    for start, c in enumerate(text):
        if c == "\x1b":
            while text[start] != "m":
                start += 1
            start += 1
        if range.start == logical_pos:
            break
        logical_pos += 1
    end = start
    for end, c in enumerate(text[logical_pos:], start):
        if c == "\x1b":
            while text[start] != "m":
                end += 1
            end += 1
        if range.stop == logical_pos:
            break
        logical_pos += 1
    return text[start:end]
