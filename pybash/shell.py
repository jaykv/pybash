"""Turn the text of one command into a Python expression.

`$` commands are lexed into words and operators here (quotes, escapes,
redirects, pipes, `&&`/`||`/`;`) and never reach a shell. `>` commands are
handed to the shell verbatim, with interpolated values quoted for the context
they appear in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from pybash.errors import InvalidInterpolation, PybashSyntaxError

DEFAULT_RUNTIME = '__import__("pybash.runtime").runtime'

PIPES = ("|", "|&")
CONNECTORS = ("&&", "||", ";")
DUPLICATES = ("2>&1", ">&2")
FILE_REDIRECTS = ("<", ">", ">>", "2>", "2>>", "&>", "&>>")


@dataclass
class Lit:
    text: str


@dataclass
class Expr:
    code: str
    kind: str  # "f" (f-string), "direct" ({{ }}) or "raw" ({{! }})
    quote: str = ""  # shell quote context the interpolation appeared in


@dataclass
class Word:
    pos: int
    parts: list[Lit | Expr] = field(default_factory=list)
    plain: bool = True  # only unquoted literal characters so far


@dataclass
class Op:
    pos: int
    text: str


def _skip_python_string(text: str, start: int) -> int:
    """Index just past the Python string literal starting at `start`."""
    quote = text[start]
    delim = quote * 3 if text.startswith(quote * 3, start) else quote
    i = start + len(delim)
    while i < len(text):
        if text[i] == "\\":
            i += 2
        elif text.startswith(delim, i):
            return i + len(delim)
        else:
            i += 1
    return len(text)


def _balanced_end(text: str, start: int, closer: str) -> int:
    """Index of the `closer` that ends the Python expression starting at `start`, or -1."""
    depth = 0
    i = start
    while i < len(text):
        char = text[i]
        if char in "'\"":
            i = _skip_python_string(text, i)
            continue
        if depth == 0 and text.startswith(closer, i):
            return i
        if char in "{[(":
            depth += 1
        elif char in "}])" and depth:
            depth -= 1
        i += 1
    return -1


def scan_interpolation(text: str, i: int, quote: str = "") -> tuple[Expr, int] | None:
    """Parse a `{{ expr }}` or `f{ expr }` interpolation starting at `i`, if there is one."""
    if text.startswith("{{", i):
        end = _balanced_end(text, i + 2, "}}")
        if end < 0:
            return None
        code = text[i + 2 : end].strip()
        kind = "direct"
        if code.startswith("!") and not code.startswith("!="):
            code, kind = code[1:].strip(), "raw"
        if not code:
            raise InvalidInterpolation("empty {{ }} interpolation", text=text, offset=i)
        return Expr(code, kind, quote), end + 2
    if text.startswith("f{", i) and not (i and (text[i - 1].isalnum() or text[i - 1] == "_")):
        end = _balanced_end(text, i + 2, "}")
        if end < 0:
            return None
        code = text[i + 2 : end]
        if not code.strip():
            raise InvalidInterpolation("empty f{ } interpolation", text=text, offset=i)
        return Expr(code, "f", quote), end + 1
    return None


def _escaped_marker(text: str, i: int) -> str | None:
    r"""`\{{` and `\f{` are the literal texts `{{` and `f{`."""
    if text[i] == "\\":
        for marker in ("{{", "f{"):
            if text.startswith(marker, i + 1):
                return marker
    return None


def lex(text: str) -> list[Word | Op]:
    """Split a `$` command into words and operators using POSIX shell quoting rules."""
    tokens: list[Word | Op] = []
    word: Word | None = None
    quote = ""
    i = 0

    def literal(chars: str, *, plain: bool) -> None:
        nonlocal word
        if word is None:
            word = Word(i)
        word.plain = word.plain and plain
        if word.parts and isinstance(word.parts[-1], Lit):
            word.parts[-1].text += chars
        else:
            word.parts.append(Lit(chars))

    def flush() -> None:
        nonlocal word
        if word is not None:
            tokens.append(word)
            word = None

    while i < len(text):
        char = text[i]
        marker = _escaped_marker(text, i)
        if marker:
            literal(marker, plain=False)
            i += 3
            continue
        found = scan_interpolation(text, i, quote)
        if found:
            if word is None:
                word = Word(i)
            word.plain = False
            word.parts.append(found[0])
            i = found[1]
            continue

        if quote == "'":
            if char == "'":
                quote = ""
            else:
                literal(char, plain=False)
            i += 1
        elif quote == '"':
            if char == '"':
                quote = ""
            elif char == "\\" and text[i + 1 : i + 2] in ('"', "\\", "$", "`"):
                literal(text[i + 1], plain=False)
                i += 1
            else:
                literal(char, plain=False)
            i += 1
        elif char.isspace():
            flush()
            i += 1
        elif char == "#" and word is None:
            break
        elif char in "'\"":
            quote = char
            if word is None:
                word = Word(i)
            word.plain = False
            i += 1
        elif char == "\\":
            if i + 1 < len(text):
                literal(text[i + 1], plain=False)
            i += 2
        elif char in "|&;<>":
            fd, start = "", i
            if char == ">" and word is not None and word.plain and len(word.parts) == 1:
                digits = word.parts[0]
                if isinstance(digits, Lit) and digits.text.isdigit():
                    fd, start = digits.text, word.pos
                    word = None
            flush()
            op, i = _lex_operator(text, i, fd, start)
            tokens.append(Op(start, op))
        else:
            literal(char, plain=True)
            i += 1

    if quote:
        raise PybashSyntaxError(f"unterminated {quote} quote in command", text=text, offset=len(text) - 1)
    flush()
    return tokens


def _lex_operator(text: str, i: int, fd: str, start: int) -> tuple[str, int]:
    def unsupported(what: str) -> PybashSyntaxError:
        return PybashSyntaxError(
            f"{what} is not supported in a $ command; use a > shell command", text=text, offset=start
        )

    for op in ("||", "|&", "|", "&&", "&>>", "&>", ";"):
        if text.startswith(op, i):
            return op, i + len(op)
    if text[i] == "&":
        raise unsupported("running in the background with &")
    if text[i] == "<":
        if text.startswith("<<", i):
            raise unsupported("a here-document (<<)")
        return "<", i + 1

    if fd not in ("", "1", "2"):
        raise unsupported(f"redirecting file descriptor {fd}")
    if text.startswith(">&", i):
        j = i + 2
        while j < len(text) and text[j].isdigit():
            j += 1
        op = (fd or "1") + ">&" + text[i + 2 : j]
        if op == "2>&1":
            return op, j
        if op == "1>&2":
            return ">&2", j
        raise unsupported(f"the redirect {fd}>&{text[i + 2 : j]}")
    prefix = "2" if fd == "2" else ""
    if text.startswith(">>", i):
        return prefix + ">>", i + 2
    return prefix + ">", i + 1


def _string(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _fstring(code: str) -> str:
    return 'f"""{' + code + '}"""'


def _word_expr(word: Word) -> str:
    """The Python expression that evaluates to this word's text."""
    if not word.parts:
        return '""'
    if len(word.parts) == 1 and isinstance(word.parts[0], Expr) and word.parts[0].kind != "f":
        return f"str({word.parts[0].code})"
    pieces = []
    for part in word.parts:
        if isinstance(part, Lit):
            pieces.append(_string(part.text))
        elif part.kind == "f":
            pieces.append(_fstring(part.code))
        else:
            pieces.append(f"str({part.code})")
    return " + ".join(pieces)


def compile_exec(text: str, *, capture: bool, runtime: str = DEFAULT_RUNTIME) -> str:
    """Compile a `$` command to an expression that runs it without a shell."""
    tokens = lex(text)
    if not tokens:
        raise PybashSyntaxError("empty command", text=text, offset=0)

    simple = all(isinstance(token, Word) for token in tokens)
    if simple:
        args = ", ".join(_word_expr(token) for token in tokens if isinstance(token, Word))
        return f"subprocess.{'check_output' if capture else 'run'}([{args}])"

    parts: list[str] = []
    argv: list[str] = []
    redirects: list[str] = []
    expects = ""  # what the previous operator still needs: "command" or "file"
    last_op: Op | None = None

    def end_command(op: Op | None) -> None:
        if not argv:
            where = op.pos if op else last_op.pos if last_op else len(text)
            what = f"before {op.text!r}" if op else f"after {last_op.text!r}" if last_op else ""
            raise PybashSyntaxError(f"missing command {what}".strip(), text=text, offset=where)
        parts.append("[" + ", ".join(argv) + "]")
        parts.extend(redirects)
        argv.clear()
        redirects.clear()

    for token in tokens:
        if isinstance(token, Word):
            if expects == "file":
                redirects.append(_word_expr(token))
            else:
                argv.append(_word_expr(token))
            expects = ""
            continue
        if expects == "file":
            raise PybashSyntaxError(f"missing file name before {token.text!r}", text=text, offset=token.pos)
        if token.text in FILE_REDIRECTS:
            redirects.append(_string(token.text))
            expects = "file"
        elif token.text in DUPLICATES:
            redirects.append(_string(token.text))
        else:
            end_command(token)
            parts.append(_string(token.text))
            expects = "command"
        last_op = token

    if expects == "file":
        assert last_op is not None
        raise PybashSyntaxError(f"missing file name after {last_op.text!r}", text=text, offset=last_op.pos)
    if argv or redirects or not (last_op and last_op.text == ";"):
        end_command(None)
    else:
        parts.pop()  # a trailing `;` is harmless

    call = f"{runtime}.run([{', '.join(parts)}]"
    return call + (", capture=True)" if capture else ")")


def compile_shell(text: str, *, runtime: str = DEFAULT_RUNTIME) -> str:
    """Compile a `>` command to an expression that runs it through the shell.

    The command text is passed through untouched. Interpolated values are
    quoted for where they sit (bare, inside "..." or inside '...') so a value
    is always data and never shell syntax; `{{! expr }}` opts out.
    """
    text = text.strip()
    if not text:
        raise PybashSyntaxError("empty command", text=text, offset=0)

    pieces: list[str] = []
    buffer = ""
    quote = ""
    i = 0
    while i < len(text):
        char = text[i]
        marker = _escaped_marker(text, i)
        if marker:
            buffer += marker
            i += 3
            continue
        found = scan_interpolation(text, i, quote)
        if found:
            expr, i = found
            if buffer:
                pieces.append(_string(buffer))
                buffer = ""
            value = _fstring(expr.code) if expr.kind == "f" else expr.code
            if expr.kind == "raw":
                pieces.append(f"str({value})")
            else:
                helper = {"": "quote", '"': "dquote", "'": "squote"}[quote]
                pieces.append(f"{runtime}.{helper}({value})")
            continue
        if quote == "'":
            quote = "" if char == "'" else quote
        elif quote == '"':
            if char == "\\" and i + 1 < len(text):
                buffer += char
                i += 1
                char = text[i]
            elif char == '"':
                quote = ""
        elif char == "\\" and i + 1 < len(text):
            buffer += char
            i += 1
            char = text[i]
        elif char in "'\"":
            quote = char
        buffer += char
        i += 1

    if buffer:
        pieces.append(_string(buffer))
    return f"subprocess.run({' + '.join(pieces)}, shell=True)"
