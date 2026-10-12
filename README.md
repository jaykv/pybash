# PyBash

![GitHub Workflow Status (with branch)](https://img.shields.io/github/actions/workflow/status/jaykv/pybash/ci.yml?branch=main)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pybash)
![PyPI](https://img.shields.io/pypi/v/pybash)
![GitHub](https://img.shields.io/github/license/jaykv/pybash)

Write shell commands directly in Python. PyBash rewrites lines that start with `$` or `>` into
`subprocess` calls, so you get the brevity of a shell script with the rest of Python around it.

```python
branch = ($git rev-parse --abbrev-ref HEAD).decode().strip()
$git fetch origin && git rebase origin/{{branch}} || echo "rebase failed"
count = $git log --oneline | wc -l
print(f"{branch}: {int(count)} commits")
```

- `$` commands never go through a shell. Arguments are split at transform time, and pipes, redirects
  and `&&` / `||` / `;` are run by PyBash itself, so a value can never turn into shell syntax.
- `>` commands are handed to the shell as written, for globbing and expansion. Interpolated values are
  quoted for you.
- One line in, one line out: tracebacks point at the line you wrote.
- No dependencies. Python 3.11+.

## Install

```bash
pip install pybash
```

## Use

### Run a script

```bash
pybash script.py [args...]      # or: python -m pybash script.py
pybash --show script.py         # print the generated Python instead of running it
pybash -c '$echo hello'
```

Modules the script imports from its own project may use the syntax too.

### Transform source yourself

```python
from pybash import transform

transform("$echo hello world")   # 'subprocess.run(["echo", "hello", "world"])'
```

Plain commands compile to bare `subprocess` calls. Commands with operators call a small helper in
`pybash.runtime`; by default the generated code imports it in place, so the output only needs
`import subprocess`. For tidier output, name the helper yourself and add the header:

```python
import pybash

body = pybash.transform(source, runtime=pybash.RUNTIME_NAME)
code = pybash.header() + body                   # imports pybash.runtime
code = pybash.header(standalone=True) + body    # pastes the helper in: no pybash needed at run time
```

`pybash.compile_source(source, filename)` returns a code object ready for `exec`, and
`pybash.add_hook()` installs an import hook for the current process.

Mistakes raise `PybashSyntaxError`, a `SyntaxError` whose `filename`, `lineno`, `offset` and `text`
point at the original line.

## Syntax

### Run: `$command`

```python
$python --version
$cp test.txt test_copy.txt
```

Returns the `subprocess.CompletedProcess`. A non-zero exit does not raise.

### Capture: `x = $command`, `($command)`, `$(command)`

```python
out = $cat test.txt
print(($cat test.txt).decode().strip())
lines = $(wc -l test.txt).decode().split()[0]
```

Captures are `bytes`, and raise `subprocess.CalledProcessError` on a non-zero exit.
A capture not wrapped in brackets runs to the end of the line.

### Operators

| Operator | Meaning |
|---|---|
| `a \| b` | pipe stdout of `a` into `b` |
| `a \|& b` | pipe stdout and stderr |
| `a && b`, `a \|\| b`, `a ; b` | run `b` if `a` succeeded / failed / either way |
| `< file` | read stdin from a file |
| `> file`, `>> file` | write / append stdout |
| `2> file`, `2>> file` | write / append stderr |
| `&> file`, `&>> file` | write / append both |
| `2>&1`, `>&2` | send stderr to stdout / stdout to stderr |

```python
$sort < in.txt | uniq -c | sort -rn > counts.txt
$make build > build.log 2>&1 && echo ok || echo failed
newest = $ls -t | head -n 1
```

Operators work without surrounding spaces (`a|b`, `2>err.log`). Quote or escape one to pass it as
text: `$echo 'a && b' \| c`. Several output files on one command all receive the output
(`$echo hi > a.txt >> b.txt`).

Background jobs (`&`), here-documents (`<<`) and other file descriptors are not supported in `$`
commands; use a `>` shell command for those.

### Quoting

`$` commands follow POSIX shell quoting: single quotes are literal, double quotes allow `\"` and `\\`,
and a backslash escapes the next character. An unquoted `#` at the start of a word begins a comment.
There is no globbing, `~` or `$VAR` expansion; use `>` when you need the shell.

A trailing backslash continues the command on the next line.

### Interpolation

| Form | Meaning |
|---|---|
| `{{ expr }}` | the value of any Python expression, converted with `str()` |
| `f{ expr }` | the same, with f-string formatting available: `f{n:03d}`, `f{name!r}` |

```python
$git {{command}} {{get_option(command)}}
$kubectl get pods --show-{{display_type}}=true -n f{namespace}
$echo "{{user}} has f{count:,} files"
```

In a `$` command an interpolated value is always exactly one argument, whatever it contains.
Interpolation also applies inside quotes. To write the markers literally, escape them: `\{{` and `\f{`.

### Shell: `>command`

```python
>ls .github/* | wc -l
>echo "hello {{name}}" > out.txt
```

The line is passed to the shell untouched. Interpolated values are quoted for where they appear
(bare, inside `"..."` or inside `'...'`), so they are always data. To splice shell syntax in on
purpose, use `{{! expr }}`:

```python
pattern = "*.txt"
>ls {{! pattern }}
```

## Upgrading from 0.3

- Python 3.11+ is required; the `ideas` and `token-utils` dependencies are gone.
- Arguments reach the command exactly as a shell would pass them. Previously backslashes were
  re-interpreted by Python (`'a\\nb'` became a newline) and a `"` inside an argument produced invalid code.
- `{{ x }}` is converted with `str()`, may contain spaces and quotes, and no longer raises `InvalidInterpolation`
  for them.
- Interpolated values in `>` commands are now quoted. Use `{{! x }}` for the old raw behavior.
- `>` commands keep their quoting; previously quotes were stripped before the shell saw them.
- `a = $x | y` now captures the pipeline's output instead of assigning a process object, and no
  `cmd1` / `fout` variables leak into your code.
- `$a > f1 > f2` writes the output to both files; previously the second file received a copy of the first.
- `&&`, `||`, `;`, `2>`, `&>`, `2>&1`, `|&` and `$( )` are new. `&&` used to raise `NotImplementedError`.
- Generated lists are formatted `["ls", "-la"]` and the result no longer ends with an added newline.
- Text such as `"total = $5"` or `"($x)"` inside a Python string is no longer mistaken for a command.

## Development

```bash
uv sync
make check     # format, lint (ruff + mypy), test
make demo
```
