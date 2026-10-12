from __future__ import annotations


class PybashSyntaxError(SyntaxError):
    """A `$` or `>` command that pybash cannot translate.

    `transform` fills in `filename`, `lineno`, `offset` and `text` like any
    SyntaxError, so hosts can point at the offending line of the original source.
    """

    def __init__(self, message: str, *, text: str = "", offset: int = 0) -> None:
        super().__init__(message)
        self.msg = message
        self.text = text
        self.column = offset  # 0-based, relative to `text`


class InvalidInterpolation(PybashSyntaxError):
    """An empty or malformed `{{ }}` / `f{ }` interpolation."""
