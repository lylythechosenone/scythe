STRING = "\x1b[0;32m"
KEYWORD = "\x1b[0;35m"
PRIMITIVE = "\x1b[0;34m"
COMMENT = "\x1b[0;30m"
RESET = "\x1b[0m"
INT = "\x1b[0;36m"
ERROR = "\x1b[1;31m"


def colorize(val: object, color: str) -> str:
    return f"{color}{val}{RESET}"
