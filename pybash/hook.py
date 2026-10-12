"""Import and execute Python files that contain pybash commands."""

from __future__ import annotations

import ast
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import sysconfig
from collections.abc import Sequence
from pathlib import Path
from types import CodeType, ModuleType

from pybash.transformer import transform


def compile_source(source: str, filename: str = "<pybash>") -> CodeType:
    """Transform and compile source, making `subprocess` available to it.

    The import is added to the syntax tree rather than the text, so line
    numbers match the original file.
    """
    tree = ast.parse(transform(source, filename=filename), filename)
    position = 0
    for position, node in enumerate(tree.body):
        is_docstring = position == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        is_future = isinstance(node, ast.ImportFrom) and node.module == "__future__"
        if not (is_docstring or is_future):
            break
    else:
        position = len(tree.body)
    tree.body.insert(position, ast.Import(names=[ast.alias(name="subprocess")]))
    ast.fix_missing_locations(tree)
    code: CodeType = compile(tree, filename, "exec")
    return code


class PybashLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname: str) -> CodeType:
        # Never read or write .pyc files: they would not record that the source was transformed.
        path = self.get_filename(fullname)
        return compile_source(importlib.util.decode_source(self.get_data(path)), path)


class PybashFinder(importlib.abc.MetaPathFinder):
    """Finds project modules (not the stdlib or installed packages) and loads them through pybash."""

    def __init__(self) -> None:
        names = ("stdlib", "platstdlib", "purelib", "platlib")
        self._library_dirs = {Path(path).resolve() for name in names if (path := sysconfig.get_path(name))}

    def _is_library(self, origin: str) -> bool:
        resolved = Path(origin).resolve()
        return any(directory in resolved.parents for directory in self._library_dirs)

    def find_spec(
        self, fullname: str, path: Sequence[str] | None, target: ModuleType | None = None
    ) -> importlib.machinery.ModuleSpec | None:
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or spec.origin is None or type(spec.loader) is not importlib.machinery.SourceFileLoader:
            return None
        if self._is_library(spec.origin):
            return None
        spec.loader = PybashLoader(spec.loader.name, spec.loader.path)
        return spec


def add_hook() -> PybashFinder:
    """Install the import hook (once) so `import module` works for files with pybash commands."""
    for finder in sys.meta_path:
        if isinstance(finder, PybashFinder):
            return finder
    finder = PybashFinder()
    sys.meta_path.insert(0, finder)
    return finder


def remove_hook() -> None:
    sys.meta_path[:] = [finder for finder in sys.meta_path if not isinstance(finder, PybashFinder)]
