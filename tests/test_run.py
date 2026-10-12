"""Run the generated code for real: the transform is only right if the commands behave like a shell's."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

import pybash
from pybash import compile_source, header, transform


@pytest.fixture(autouse=True)
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "in.txt").write_text("pear\napple\npear\nfig\n")
    return tmp_path


def run(source: str, **variables: Any) -> dict[str, Any]:
    namespace: dict[str, Any] = dict(variables)
    exec(compile_source(textwrap.dedent(source)), namespace)
    return namespace


def read(name: str) -> str:
    return Path(name).read_text()


def test_capture_returns_bytes() -> None:
    assert run("out = $echo hello")["out"] == b"hello\n"
    assert run("out = ($printf '%s-%s' a b).decode()")["out"] == "a-b"


def test_arguments_arrive_exactly_as_written(capfd: pytest.CaptureFixture[str]) -> None:
    run("""$printf '%s|' 'say "hi"' it\\'s 'a\\nb' "x  y" ''""")
    assert capfd.readouterr().out == 'say "hi"|it\'s|a\\nb|x  y||'


def test_interpolated_value_is_one_argument() -> None:
    namespace = run("out = $printf '[%s]' {{value}} f{number:03d} pre-{{value}}", value="a b; rm -rf /", number=7)
    assert namespace["out"] == b"[a b; rm -rf /][007][pre-a b; rm -rf /]"


def test_pipeline_and_capture() -> None:
    assert run("out = $sort in.txt | uniq -c | sort -rn | head -n 1")["out"].split() == [b"2", b"pear"]


def test_pipeline_stops_upstream_when_downstream_exits() -> None:
    assert run("out = $yes | head -n 2")["out"] == b"y\ny\n"


def test_redirects() -> None:
    run(
        """
        $sort < in.txt > sorted.txt
        $echo more >> sorted.txt
        $sh -c 'echo out; echo err >&2' > out.txt 2> err.txt
        $sh -c 'echo out; echo err >&2' > both.txt 2>&1
        $sh -c 'echo out; echo err >&2' &> amp.txt
        $sort in.txt | uniq > uniq.txt
        """
    )
    assert read("sorted.txt") == "apple\nfig\npear\npear\nmore\n"
    assert (read("out.txt"), read("err.txt")) == ("out\n", "err\n")
    assert sorted(read("both.txt").split()) == sorted(read("amp.txt").split()) == ["err", "out"]
    assert read("uniq.txt") == "apple\nfig\npear\n"


def test_stderr_redirect_follows_shell_ordering(capfd: pytest.CaptureFixture[str]) -> None:
    run("$sh -c 'echo out; echo err >&2' 2>&1 > only_out.txt")
    assert read("only_out.txt") == "out\n"
    assert capfd.readouterr().out == "err\n"

    run("$echo oops >&2")
    assert capfd.readouterr().err == "oops\n"

    assert run("out = $sh -c 'echo out; echo err >&2' |& sort")["out"] == b"err\nout\n"


def test_several_output_files_all_receive_the_output() -> None:
    Path("b.txt").write_text("old\n")
    run("$echo hi > a.txt >> b.txt > c.txt")
    assert (read("a.txt"), read("b.txt"), read("c.txt")) == ("hi\n", "old\nhi\n", "hi\n")


def test_connectors() -> None:
    namespace = run(
        """
        a = $true && echo yes || echo no
        b = $false && echo yes || echo no
        c = $false; echo after
        """
    )
    assert (namespace["a"], namespace["b"], namespace["c"]) == (b"yes\n", b"no\n", b"after\n")


def test_statement_returns_status_and_capture_raises() -> None:
    status = pybash.runtime.run([["true"], "&&", ["false"]])
    assert status.returncode == 1
    with pytest.raises(subprocess.CalledProcessError) as info:
        run("out = $echo partial && false")
    assert info.value.output == b"partial\n"


def test_missing_command_raises_and_cleans_up() -> None:
    with pytest.raises(FileNotFoundError):
        run("$yes | pybash-no-such-command")


def test_shell_mode() -> None:
    run(">ls *.txt | wc -l > count.txt")
    assert read("count.txt").strip() == "1"


def test_shell_interpolation_cannot_inject() -> None:
    evil = "x'; touch pwned; echo \"$(touch pwned2)`touch pwned3`"
    run(
        """
        >printf '%s' {{value}} > bare.txt
        >printf '%s' "f{value}" > double.txt
        >printf '%s' '{{value}}' > single.txt
        """,
        value=evil,
    )
    assert read("bare.txt") == read("double.txt") == read("single.txt") == evil
    assert not list(Path().glob("pwned*"))
    run(">ls {{! pattern }} > raw.txt", pattern="*.txt")
    assert "in.txt" in read("raw.txt")


def test_line_numbers_match_the_original_source() -> None:
    source = '"""doc"""\nfrom __future__ import annotations\n$true \\\n    \n\nraise RuntimeError("line 6")\n'
    with pytest.raises(RuntimeError) as info:
        exec(compile_source(source, "prog.py"), {})
    assert info.traceback[-1].lineno == 5  # 0-based


@pytest.mark.parametrize("standalone", [False, True])
def test_header_makes_transformed_code_runnable(standalone: bool, workdir: Path) -> None:
    body = transform('out = $sort in.txt | head -n 1\n>echo {{out.decode().strip()}} > "first.txt"', runtime="_pybash")
    script = workdir / "generated.py"
    script.write_text(header(standalone=standalone) + body + "\n")
    if standalone:
        assert "import pybash" not in script.read_text()
    subprocess.run([sys.executable, "-I", str(script)] if standalone else [sys.executable, str(script)], check=True)
    assert read("first.txt") == "apple\n"


def test_import_hook(workdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (workdir / "hooked_mod.py").write_text("def name():\n    return ($echo hooked).decode().strip()\n")
    monkeypatch.syspath_prepend(str(workdir))
    assert pybash.add_hook() is pybash.add_hook()
    try:
        import hooked_mod  # type: ignore[import-not-found]

        assert hooked_mod.name() == "hooked"
        assert not (workdir / "__pycache__").exists()
    finally:
        pybash.remove_hook()
        sys.modules.pop("hooked_mod", None)


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "pybash", *args], capture_output=True, text=True)


def test_cli_runs_scripts_and_modules(workdir: Path) -> None:
    (workdir / "helper.py").write_text("def shout():\n    $echo from helper\n")
    (workdir / "script.py").write_text(
        "import sys\nimport helper\nhelper.shout()\nif __name__ == '__main__':\n    $echo f{sys.argv[1:]}\n"
    )
    result = cli("script.py", "a", "--b")
    assert (result.returncode, result.stdout) == (0, "from helper\n['a', '--b']\n")
    assert cli("script", "c").stdout == "from helper\n['c']\n"
    assert cli("-c", "$echo inline").stdout == "inline\n"


def test_cli_show_and_errors(workdir: Path) -> None:
    (workdir / "script.py").write_text("x = 1\n$echo hi |\n")
    result = cli("script.py")
    assert result.returncode == 2
    assert "script.py:2:10: missing command after '|'" in result.stderr
    (workdir / "ok.py").write_text("$echo hi\n")
    assert cli("--show", "ok.py").stdout == 'subprocess.run(["echo", "hi"])\n\n'
    assert cli("nope").returncode == 2
    assert cli().returncode == 2
