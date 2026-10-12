"""Runtime support for the code pybash generates.

Plain commands compile to bare `subprocess` calls and need nothing from here.
Commands that use shell operators (`|`, `&&`, `>`, ...) or interpolate into a
`>` shell line compile to calls on `_pybash`, which is this module's class.

The class is self-contained (stdlib only, imports inside the methods) so that
its source can be pasted into generated code that must not depend on pybash;
see `pybash.runtime_source()`.
"""

from __future__ import annotations

from typing import Any


class _pybash:
    """Namespace for the helpers referenced by generated code."""

    PIPES = ("|", "|&")
    CONNECTORS = ("&&", "||", ";")
    DUPLICATES = ("2>&1", ">&2")

    @staticmethod
    def quote(value: Any) -> str:
        """Quote a value so a shell reads it as exactly one word."""
        import shlex

        return shlex.quote(str(value))

    @staticmethod
    def dquote(value: Any) -> str:
        """Escape a value for use inside a double-quoted shell string."""
        import re

        return re.sub(r'([\\"$`])', r"\\\1", str(value))

    @staticmethod
    def squote(value: Any) -> str:
        """Escape a value for use inside a single-quoted shell string."""
        return str(value).replace("'", "'\\''")

    @staticmethod
    def run(parts: list[Any], capture: bool = False) -> Any:
        """Run a command list written the way it reads in a shell.

        `parts` alternates argument lists with operator strings, for example
        `[["sort"], "<", "in.txt", "|", ["uniq", "-c"], "&&", ["echo", "ok"]]`.
        A redirect operator is followed by its file name.

        Returns the `subprocess.CompletedProcess` of the last command that ran.
        With `capture=True`, returns everything written to stdout as bytes and
        raises `subprocess.CalledProcessError` if the final status is non-zero.
        """
        import subprocess

        jobs: list[tuple[str, list[dict[str, Any]]]] = [(";", [])]
        position = 0
        while position < len(parts):
            part = parts[position]
            position += 1
            pipeline = jobs[-1][1]
            if not isinstance(part, str):
                pipeline.append({"argv": [str(arg) for arg in part], "redirects": [], "pipe_stderr": False})
            elif part in _pybash.CONNECTORS:
                jobs.append((part, []))
            elif part in _pybash.PIPES:
                pipeline[-1]["pipe_stderr"] = part == "|&"
            elif part in _pybash.DUPLICATES:
                pipeline[-1]["redirects"].append((part, None))
            else:
                pipeline[-1]["redirects"].append((part, parts[position]))
                position += 1

        captured: list[bytes] = []
        result: subprocess.CompletedProcess[bytes] = subprocess.CompletedProcess([], 0)
        for connector, pipeline in jobs:
            if not pipeline:
                continue
            if connector == "&&" and result.returncode != 0:
                continue
            if connector == "||" and result.returncode == 0:
                continue
            result = _pybash._pipeline(pipeline, captured if capture else None)

        if not capture:
            return result
        output = b"".join(captured)
        if result.returncode:
            raise subprocess.CalledProcessError(result.returncode, result.args, output=output)
        return output

    @staticmethod
    def _pipeline(commands: list[dict[str, Any]], sink: list[bytes] | None) -> Any:
        import contextlib
        import subprocess

        procs: list[subprocess.Popen[bytes]] = []
        with contextlib.ExitStack() as files:
            upstream: Any = None
            collect: list[Any] = []
            try:
                for index, command in enumerate(commands):
                    last = index == len(commands) - 1
                    stdin: Any = upstream
                    stderr: Any = None
                    targets: list[Any] = []
                    to_stderr = False
                    stderr_to_original = False
                    for op, name in command["redirects"]:
                        if op == "<":
                            stdin = files.enter_context(open(name, "rb"))
                        elif op in (">", ">>"):
                            targets.append(files.enter_context(open(name, "ab" if op == ">>" else "wb")))
                        elif op in ("2>", "2>>"):
                            stderr = files.enter_context(open(name, "ab" if op == "2>>" else "wb"))
                        elif op in ("&>", "&>>"):
                            targets.append(files.enter_context(open(name, "ab" if op == "&>>" else "wb")))
                            stderr = subprocess.STDOUT
                        elif op == "2>&1":
                            # Like a shell, follow stdout as it is right now: `2>&1 > f` keeps stderr out of f.
                            stderr = subprocess.STDOUT
                            stderr_to_original = not targets
                        elif op == ">&2":
                            to_stderr = True
                        else:
                            raise ValueError(f"pybash: unsupported operator {op!r}")
                    if command["pipe_stderr"]:
                        stderr = subprocess.STDOUT

                    if stderr_to_original and targets and last and sink is None:
                        stderr = 1

                    # Several `>` targets on one command all receive the output.
                    fan_out = len(targets) > 1
                    stdout: Any
                    if fan_out:
                        stdout = subprocess.PIPE
                    elif targets:
                        stdout = targets[0]
                    elif to_stderr:
                        stdout = 2 if stderr is None or stderr == subprocess.STDOUT else stderr
                    elif not last or sink is not None:
                        stdout = subprocess.PIPE
                    else:
                        stdout = None

                    proc = subprocess.Popen(command["argv"], stdin=stdin, stdout=stdout, stderr=stderr)
                    procs.append(proc)
                    if upstream is not None and upstream != subprocess.DEVNULL:
                        # The child holds its own copy; ours would keep the writer from seeing EOF/SIGPIPE.
                        upstream.close()
                    if fan_out:
                        collect.append((proc, targets))
                        upstream = subprocess.DEVNULL
                    elif stdout == subprocess.PIPE:
                        if last:
                            collect.append((proc, None))
                        upstream = proc.stdout
                    else:
                        upstream = subprocess.DEVNULL

                for proc, targets in collect:
                    assert proc.stdout is not None
                    data = proc.stdout.read()
                    if targets is None:
                        assert sink is not None
                        sink.append(data)
                    else:
                        for target in targets:
                            target.write(data)
            finally:
                for proc in procs:
                    if proc.stdout is not None:
                        proc.stdout.close()
                for proc in procs:
                    proc.wait()

        return subprocess.CompletedProcess(procs[-1].args, procs[-1].returncode)


quote = _pybash.quote
dquote = _pybash.dquote
squote = _pybash.squote
run = _pybash.run
