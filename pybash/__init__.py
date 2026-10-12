"""Run shell commands from Python source with `$` and `>` lines."""

from __future__ import annotations

import inspect

from pybash import runtime as _runtime
from pybash.errors import InvalidInterpolation, PybashSyntaxError
from pybash.hook import add_hook, compile_source, remove_hook
from pybash.transformer import transform

__all__ = [
    "RUNTIME_NAME",
    "InvalidInterpolation",
    "PybashSyntaxError",
    "add_hook",
    "compile_source",
    "header",
    "remove_hook",
    "runtime_source",
    "transform",
]

#: Pass as `transform(..., runtime=RUNTIME_NAME)` when the output is prefixed with `header()`.
RUNTIME_NAME = "_pybash"


def runtime_source() -> str:
    """Source of the stdlib-only helper class that generated code calls for operators."""
    return inspect.getsource(_runtime._pybash)


def header(*, standalone: bool = False) -> str:
    """Lines to put above code produced by `transform(..., runtime=RUNTIME_NAME)`.

    With `standalone=True` the helper is pasted in, so the result runs without
    pybash installed.
    """
    if standalone:
        return f"import subprocess\nfrom typing import Any\n\n\n{runtime_source()}\n"
    return f"import subprocess\n\nimport pybash.runtime as {RUNTIME_NAME}\n"
