from dataclasses import dataclass
import re
import colors


@dataclass
class Error(Exception):
    msg: str
    span: slice
    long: str
    note: str | None = None

    def start_position(self, file: str) -> tuple[int, int]:
        line = 0
        col = 0
        for i, c in enumerate(file):
            if c == "\n":
                line += 1
                col = 0
            else:
                col += 1
            if self.span.start == i:
                break
        return line, col

    def end_position(
        self, file: str, start_line: int, start_col: int
    ) -> tuple[int, int]:
        line = start_line
        col = start_col
        for i, c in enumerate(file[self.span.start :], self.span.start):
            if self.span.stop == i:
                break
            if c == "\n":
                line += 1
                col = 0
            else:
                col += 1
        return line, col

    def find_line_end(self, file: str, start: int) -> int:
        i = start
        newline = False
        for i, c in enumerate(file[start:], start):
            if c == "\n":
                newline = True
                break
        return i if newline else len(file)

    def display(self, file: str, lex: bool) -> str:
        # import highlight

        start_line, start_col = self.start_position(file)
        end_line, _ = self.end_position(file, start_line, start_col)
        if start_line == end_line:
            line_start = self.span.start - start_col + 1
            while file[line_start].isspace():
                line_start += 1
            line_end = self.find_line_end(file, line_start)
            # if lex:
            #     file = highlight.highlight_simple(file)
            # else:
            #     from lex import Lexer

            #     file = highlight.highlight_lex(file, Lexer(file))
            # line = highlight.slice_ignoring_ansi(file, slice(line_start, line_end))
            line = file[line_start:line_end]
            underline_len = self.span.stop - self.span.start - 1
            leading_spaces = " " * (self.span.start - line_start)
            left_underlines = "─" * (underline_len // 2)
            right_underlines = "─" * (underline_len - len(left_underlines))
            underlines = colors.colorize(
                f"{leading_spaces}{left_underlines}┬{right_underlines}",
                colors.ERROR,
            )
            message_spaces = leading_spaces + " " * len(left_underlines)
            message = colors.colorize(f"{message_spaces}╰─ {self.long}", colors.ERROR)

            line_num = f"{start_line + 1}"
            ln_spaces = " " * (len(line_num) + 1)
            ln_backln = "─" * (len(line_num) + 1)

            note = ""
            if self.note is not None:
                self.note = re.sub(
                    "[^:]+:",
                    lambda m: colors.colorize(m.group(), colors.STRING),
                    self.note,
                )
                note = (
                    f"{colors.STRING}{ln_spaces}│ {colors.RESET}{self.note}\n"
                    f"{colors.STRING}{ln_backln}╯ {colors.RESET}\n"
                )

            return (
                f"{colors.COMMENT}{ln_spaces}╭─{colors.RESET}{colors.ERROR}[{start_line + 1}:{start_col + 1}] Error:{colors.RESET} {self.msg}\n"
                f"{colors.COMMENT}{line_num} │ {colors.RESET}{line}\n"
                f"{colors.COMMENT}{ln_spaces}┆ {colors.RESET}{underlines}\n"
                f"{colors.COMMENT}{ln_spaces}┆ {colors.RESET}{message}\n"
                + (
                    f"{colors.COMMENT}{ln_backln}╯{colors.RESET}\n"
                    if note == ""
                    else f"{colors.COMMENT}{ln_spaces}┆{colors.RESET}\n"
                )
                + f"{note}"
            )
        else:
            print(f"Start line is {start_line} and end line is {end_line}")
            print(self)
            return ""
