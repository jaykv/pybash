"""Rewrite Python source that contains `$` and `>` commands into plain Python.

Every input line maps to exactly one output line, so line numbers in
tracebacks still point at the original source.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pybash.errors import InvalidInterpolation, PybashSyntaxError
from pybash.shell import DEFAULT_RUNTIME, _escaped_marker, compile_exec, compile_shell, scan_interpolation

__all__ = ["InvalidInterpolation", "PybashSyntaxError", "transform"]

_OPENERS = {"(": ")", "[": "]", "{": "}"}
_CLOSERS = {closer: opener for opener, closer in _OPENERS.items()}


@dataclass
class _State:
    """What carries over from one physical line to the next."""

    string: str = ""  # delimiter of an open triple-quoted string
    brackets: list[str] = field(default_factory=list)
    continued: bool = False  # previous line ended with a backslash

    @property
    def at_statement_start(self) -> bool:
        return not (self.string or self.brackets or self.continued)


def _command_end(line: str, start: int, closer: str) -> int:
    """Index of the unbalanced `closer` that ends the command starting at `start`, or -1."""
    opener = _CLOSERS[closer]
    depth = 0
    quote = ""
    i = start
    while i < len(line):
        char = line[i]
        if _escaped_marker(line, i):
            i += 3
            continue
        found = scan_interpolation(line, i)
        if found:
            i = found[1]
            continue
        if quote:
            if char == "\\" and quote == '"':
                i += 1
            elif char == quote:
                quote = ""
        elif char == "\\":
            i += 1
        elif char in "'\"":
            quote = char
        elif char == opener:
            depth += 1
        elif char == closer:
            if depth == 0:
                return i
            depth -= 1
        i += 1
    return -1


def _rewrite_code(line: str, state: _State, runtime: str) -> str:
    """Rewrite the `$` captures in a line of Python, tracking strings and brackets."""
    out: list[str] = []
    i = 0
    last_code = ""
    while i < len(line):
        if state.string:
            end = line.find(state.string, i)
            while end > 0 and line[end - 1] == "\\":
                end = line.find(state.string, end + 1)
            if end < 0:
                out.append(line[i:])
                state.continued = False
                return "".join(out)
            out.append(line[i : end + 3])
            i = end + 3
            state.string = ""
            last_code = '"'
            continue

        char = line[i]
        if char == "#":
            out.append(line[i:])
            break
        if char in "'\"":
            delim = char * 3 if line.startswith(char * 3, i) else char
            j = i + len(delim)
            while j < len(line) and not line.startswith(delim, j):
                j += 2 if line[j] == "\\" else 1
            if j >= len(line) and len(delim) == 3:
                state.string = delim
            j = min(j + len(delim), len(line))
            out.append(line[i:j])
            i = j
            last_code = '"'
            continue
        if char == "$":
            missing = PybashSyntaxError("Missing end parentheses", text=line, offset=i)
            if line.startswith("(", i + 1):
                # $(command)
                column = i + 2
                end = _command_end(line, column, ")")
                if end < 0:
                    raise missing
                i = end + 1
            elif state.brackets:
                # ($command): the command runs up to the bracket that encloses it
                column = i + 1
                end = _command_end(line, column, _OPENERS[state.brackets[-1]])
                if end < 0:
                    if state.brackets[-1] == "(":
                        raise missing
                    end = len(line)
                i = end
            else:
                # x = $command
                column, end = i + 1, len(line)
                i = end
            try:
                out.append(compile_exec(line[column:end], capture=True, runtime=runtime))
            except PybashSyntaxError as error:
                error.column += column
                raise
            last_code = ")"
            continue
        if char in _OPENERS:
            state.brackets.append(char)
        elif char in _CLOSERS and state.brackets:
            state.brackets.pop()
        if not char.isspace():
            last_code = char
        out.append(char)
        i += 1

    state.continued = last_code == "\\" and not state.string
    return "".join(out)


def _may_change_state(line: str) -> bool:
    return any(char in line for char in "([{\\") or '"""' in line or "'''" in line


def transform(source: str, *, runtime: str | None = None, filename: str = "<pybash>", **_ignored: object) -> str:
    """Convert `$` and `>` commands in Python source to `subprocess` calls.

    Args:
        source: Python source that may contain pybash commands.
        runtime: Expression the generated code uses to reach `pybash.runtime`
            for commands with operators. The default imports it in place, so the
            output only needs `import subprocess`. Pass a name such as
            `"_pybash"` when the host provides it (see `pybash.header`).
        filename: Reported in syntax errors.

    Raises:
        PybashSyntaxError: A command could not be translated. `lineno`, `offset`
            and `text` point at the original source.
    """
    runtime = runtime or DEFAULT_RUNTIME
    lines = source.split("\n")
    out: list[str] = []
    state = _State()
    index = 0
    while index < len(lines):
        line = lines[index]
        lineno = index + 1
        index += 1
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        is_exec = stripped.startswith("$") and not stripped.startswith("$(")
        try:
            if state.at_statement_start and (is_exec or stripped.startswith(">")):
                command = stripped[1:]
                joined = 0
                while command.endswith("\\") and not command.endswith("\\\\") and index < len(lines):
                    command = command[:-1] + " " + lines[index].strip()
                    index += 1
                    joined += 1
                try:
                    if is_exec:
                        code = compile_exec(command, capture=False, runtime=runtime)
                    else:
                        code = compile_shell(command, runtime=runtime)
                except PybashSyntaxError as error:
                    error.column += len(indent) + 1
                    raise
                out.append(indent + code)
                out.extend([""] * joined)
            elif "$" in line or not state.at_statement_start or _may_change_state(line):
                out.append(_rewrite_code(line, state, runtime))
            else:
                out.append(line)
        except PybashSyntaxError as error:
            error.filename = filename
            error.lineno = lineno
            error.text = line
            error.offset = error.column + 1
            raise
    return "\n".join(out)
