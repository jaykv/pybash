"""`pybash script.py [args...]`: run a Python file that contains pybash commands."""

from __future__ import annotations

import argparse
import importlib.util
import runpy
import sys
from pathlib import Path

from pybash.errors import PybashSyntaxError
from pybash.hook import add_hook, compile_source
from pybash.transformer import transform


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pybash", description="Run Python with $ and > shell commands.")
    parser.add_argument("-s", "--show", action="store_true", help="print the transformed Python instead of running it")
    parser.add_argument("-c", dest="code", metavar="CODE", help="run code passed as a string")
    parser.add_argument("target", nargs="?", help="script path or module name")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="arguments passed to the script")
    options = parser.parse_args(argv)

    if (options.code is None) == (options.target is None):
        parser.error("give either a script/module or -c CODE")

    try:
        if options.code is not None:
            return _run_source(options.code, "<string>", options, script_dir="")
        path = Path(options.target)
        if path.is_file():
            return _run_source(path.read_text(encoding="utf-8"), str(path), options, script_dir=str(path.parent))
        if options.show:
            parser.error(f"no such file: {options.target}")
        sys.path.insert(0, "")
        add_hook()
        if not _module_exists(options.target):
            print(f"pybash: no such file or module: {options.target}", file=sys.stderr)
            return 2
        sys.argv = [options.target, *options.args]
        runpy.run_module(options.target, run_name="__main__", alter_sys=True)
    except PybashSyntaxError as error:
        print(f"{error.filename}:{error.lineno}:{error.offset}: {error.msg}", file=sys.stderr)
        if error.text:
            print(f"    {error.text.strip()}", file=sys.stderr)
        return 2
    return 0


def _module_exists(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _run_source(source: str, filename: str, options: argparse.Namespace, *, script_dir: str) -> int:
    if options.show:
        print(transform(source, filename=filename))
        return 0
    code = compile_source(source, filename)
    sys.path.insert(0, script_dir)
    add_hook()
    sys.argv = [filename if options.code is None else "-c", *options.args]
    exec(code, {"__name__": "__main__", "__file__": filename, "__builtins__": __builtins__})
    return 0


if __name__ == "__main__":
    sys.exit(main())
