from __future__ import annotations

import pytest

from pybash import InvalidInterpolation, PybashSyntaxError, transform


def t(source: str) -> str:
    return transform(source, runtime="_pybash")


def test_exec() -> None:
    assert t("$ls -la") == 'subprocess.run(["ls", "-la"])'
    assert t("$ python --version") == 'subprocess.run(["python", "--version"])'


def test_capture_assignment() -> None:
    assert t('a = $echo "test 123"') == 'a = subprocess.check_output(["echo", "test 123"])'
    assert t("a += $ echo hi") == 'a += subprocess.check_output(["echo", "hi"])'
    assert t("    return $whoami") == '    return subprocess.check_output(["whoami"])'


def test_capture_wrapped() -> None:
    assert (
        t('print(($ cat test.txt).decode("utf-8").strip())')
        == 'print((subprocess.check_output(["cat", "test.txt"])).decode("utf-8").strip())'
    )
    assert t("print(str($echo test 123))") == 'print(str(subprocess.check_output(["echo", "test", "123"])))'
    assert t("x = [$echo a]") == 'x = [subprocess.check_output(["echo", "a"])]'
    assert t("f(1, $echo (a) b)") == 'f(1, subprocess.check_output(["echo", "(a)", "b"]))'


def test_capture_dollar_paren() -> None:
    assert (
        t("out = $(echo hi).decode() + $(date)")
        == 'out = subprocess.check_output(["echo", "hi"]).decode() + subprocess.check_output(["date"])'
    )
    assert t('a =$(echo "test 123")') == 'a =subprocess.check_output(["echo", "test 123"])'


def test_indentation_and_line_count_are_preserved() -> None:
    source = "def cp_test():\n        $cp test.txt test_copy.txt\n    "
    assert t(source) == 'def cp_test():\n        subprocess.run(["cp", "test.txt", "test_copy.txt"])\n    '
    source = "$docker run \\\n    --rm \\\n    alpine\nprint(1)\n"
    assert t(source) == 'subprocess.run(["docker", "run", "--rm", "alpine"])\n\n\nprint(1)\n'


def test_quoting_and_escapes_survive() -> None:
    assert t("""$echo 'say "hi"' it\\'s a\\\\b""") == r"""subprocess.run(["echo", "say \"hi\"", "it's", "a\\b"])"""
    assert t("$sed 's/HELLO/HOWDY\\n/g'") == 'subprocess.run(["sed", "s/HELLO/HOWDY\\\\n/g"])'
    assert t("""$echo "" ''""") == 'subprocess.run(["echo", "", ""])'
    assert t("""$echo "a  b"'c'd""") == 'subprocess.run(["echo", "a  bcd"])'
    assert t("""$curl -d '{"a": 1}' url""") == r"""subprocess.run(["curl", "-d", "{\"a\": 1}", "url"])"""


def test_trailing_comment() -> None:
    assert t("$echo hi # greet") == 'subprocess.run(["echo", "hi"])'
    assert t("$echo a#b '# c'") == 'subprocess.run(["echo", "a#b", "# c"])'


def test_python_is_left_alone() -> None:
    for source in (
        "if 5 > 4:",
        "if (pred1 and pred2) > 0:",
        'print("$(echo hi)")',
        'x = "a = $5 and ($b)"',
        "x = 'cost: ($5)'  # ($ comment)",
        "x = [\n    1\n    > 2]",
        "y = (1\n> 2)",
        "y = 1 + \\\n    2\nz = 3 \\\n> 2",
        's = """\n$ not a command\n> nor this\n"""',
        "s = '''a\n  $ls\n'''; t = 1",
        'x = f"{a}" > b',
    ):
        assert t(source) == source


def test_commands_after_multiline_constructs() -> None:
    source = 's = """\n$ no\n"""\n$ls\nx = (\n    1,\n)\n>ls *'
    assert (
        t(source) == 's = """\n$ no\n"""\nsubprocess.run(["ls"])\nx = (\n    1,\n)\nsubprocess.run("ls *", shell=True)'
    )


def test_pipes() -> None:
    assert t("$cat a.txt | sed 's/A/B/g'") == '_pybash.run([["cat", "a.txt"], "|", ["sed", "s/A/B/g"]])'
    assert t("$a|b|&c") == '_pybash.run([["a"], "|", ["b"], "|&", ["c"]])'
    assert t("x = $cat a | grep b") == 'x = _pybash.run([["cat", "a"], "|", ["grep", "b"]], capture=True)'
    assert t("print($cat a | wc -l)") == 'print(_pybash.run([["cat", "a"], "|", ["wc", "-l"]], capture=True))'


def test_redirects() -> None:
    assert t("$cat a > b") == '_pybash.run([["cat", "a"], ">", "b"])'
    assert t("$cat a>>b") == '_pybash.run([["cat", "a"], ">>", "b"])'
    assert t("$sort < a.txt >> b.txt") == '_pybash.run([["sort"], "<", "a.txt", ">>", "b.txt"])'
    assert t("$ > out.txt echo hi") == '_pybash.run([["echo", "hi"], ">", "out.txt"])'
    assert t("$make 2> err.log") == '_pybash.run([["make"], "2>", "err.log"])'
    assert t("$make 2>>err.log 1>out.log") == '_pybash.run([["make"], "2>>", "err.log", ">", "out.log"])'
    assert t("$make > all.log 2>&1") == '_pybash.run([["make"], ">", "all.log", "2>&1"])'
    assert t("$make &> all.log") == '_pybash.run([["make"], "&>", "all.log"])'
    assert t("$echo oops >&2") == '_pybash.run([["echo", "oops"], ">&2"])'
    assert t("$echo 2 > f") == '_pybash.run([["echo", "2"], ">", "f"])'
    assert t("$echo a2>f") == '_pybash.run([["echo", "a2"], ">", "f"])'


def test_connectors() -> None:
    assert (
        t("$test -f a && echo yes || echo no; echo done")
        == '_pybash.run([["test", "-f", "a"], "&&", ["echo", "yes"], "||", ["echo", "no"], ";", ["echo", "done"]])'
    )
    assert t("$echo a;") == '_pybash.run([["echo", "a"]])'
    assert t("$echo 'a && b' \\| c") == 'subprocess.run(["echo", "a && b", "|", "c"])'


def test_default_runtime_needs_only_subprocess() -> None:
    assert transform("$a | b") == '__import__("pybash.runtime").runtime.run([["a"], "|", ["b"]])'


def test_shell() -> None:
    assert t(">ls .github/*") == 'subprocess.run("ls .github/*", shell=True)'
    assert t('>  echo "a   b" | wc -c') == r"""subprocess.run("echo \"a   b\" | wc -c", shell=True)"""


def test_shell_interpolation_is_quoted_for_its_context() -> None:
    assert t(">echo {{name}}") == 'subprocess.run("echo " + _pybash.quote(name), shell=True)'
    assert (
        t('>echo "hi f{name}"')
        == r'''subprocess.run("echo \"hi " + _pybash.dquote(f"""{name}""") + "\"", shell=True)'''
    )
    assert t(">echo '{{name}}'") == """subprocess.run("echo '" + _pybash.squote(name) + "'", shell=True)"""
    assert t(">ls {{! pattern }}") == 'subprocess.run("ls " + str(pattern), shell=True)'


def test_direct_interpolation() -> None:
    assert t("$git {{command}} {{option}}") == 'subprocess.run(["git", str(command), str(option)])'
    assert t("$git {{ process(option) }}") == 'subprocess.run(["git", str(process(option))])'
    assert (
        t("$git {{a['key']}} {{ {'x': 1}['x'] }}") == """subprocess.run(["git", str(a['key']), str({'x': 1}['x'])])"""
    )
    assert (
        t("$k get pods --show-{{display_type}}=true")
        == 'subprocess.run(["k", "get", "pods", "--show-" + str(display_type) + "=true"])'
    )


def test_fstring_interpolation() -> None:
    assert (
        t("$k get f{\"--\" + \"-\".join(['show', 'labels'])} -n f{ namespace  }")
        == 'subprocess.run(["k", "get", f"""{"--" + "-".join([\'show\', \'labels\'])}""", "-n", f"""{ namespace  }"""])'
    )
    assert t("$f{HOME_DIR}/bin/python -sE") == 'subprocess.run([f"""{HOME_DIR}""" + "/bin/python", "-sE"])'
    assert t("$echo f{n:>5} --f{flag}") == 'subprocess.run(["echo", f"""{n:>5}""", "--" + f"""{flag}"""])'


def test_interpolation_inside_quotes_and_combined() -> None:
    assert t("$echo 'f{PODS} 123' {{ARGS}}") == 'subprocess.run(["echo", f"""{PODS}""" + " 123", str(ARGS)])'
    assert t('$echo "{{a}} f{b}"') == 'subprocess.run(["echo", str(a) + " " + f"""{b}"""])'


def test_interpolation_can_be_escaped_or_left_literal() -> None:
    assert t(r"$docker inspect -f '\{{.State}}' c") == 'subprocess.run(["docker", "inspect", "-f", "{{.State}}", "c"])'
    assert t(r"$echo \f{x} conf{a}") == 'subprocess.run(["echo", "f{x}", "conf{a}"])'
    assert t("$echo {{ f{") == 'subprocess.run(["echo", "{{", "f{"])'


@pytest.mark.parametrize(
    ("source", "message", "offset"),
    [
        ("$a |", "missing command after '|'", 4),
        ("$| b", "missing command before '|'", 2),
        ("$a && ; b", "missing command before ';'", 7),
        ("$a > ", "missing file name after '>'", 4),
        ("$a > | b", "missing file name before '|'", 6),
        ("$a &", "background", 4),
        ("$cat <<EOF", "here-document", 6),
        ("$a 3> f", "file descriptor 3", 4),
        ("$a 2>&3", "2>&3", 4),
        ("$echo 'x", "unterminated ' quote", 8),
        ("$", "empty command", 2),
        (">", "empty command", 2),
        ("print($ls", "Missing end parentheses", 7),
        ("x = $(ls", "Missing end parentheses", 5),
    ],
)
def test_syntax_errors_point_at_the_source(source: str, message: str, offset: int) -> None:
    with pytest.raises(PybashSyntaxError) as info:
        transform("x = 1\n    " + source, filename="cmd.py")
    error = info.value
    assert message in error.msg
    assert (error.filename, error.lineno, error.text) == ("cmd.py", 2, "    " + source)
    assert error.offset == offset + 4


@pytest.mark.parametrize("source", ["$git {{ }}", "$git f{ }", ">echo {{}}"])
def test_invalid_interpolation(source: str) -> None:
    with pytest.raises(InvalidInterpolation):
        transform(source)
