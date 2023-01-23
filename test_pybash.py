import pybash

run_bash = pybash.Transformer.transform_source


def test_single_exec():
    assert run_bash('>ls -la') == 'subprocess.run(["ls","-la"])\n'
    assert run_bash('>python --version') == 'subprocess.run(["python","--version"])\n'


def test_var_exec():
    assert run_bash('a = >echo "test 123"') == 'a =subprocess.check_output(["echo","test 123"])\n'


def test_inline_exec():
    assert run_bash('print(str(>echo test 123))') == 'print(str(subprocess.check_output(["echo","test","123"])))\n'


def test_inline_dot_exec():
    assert (
        run_bash("print((>cat test.txt).decode('utf-8').strip())")
        == 'print((subprocess.check_output(["cat","test.txt"])).decode(\'utf-8\').strip())\n'
    )


def test_method_exec():
    src = '''def cp_test():
        >cp test.txt test_copy.txt
    '''
    assert (
        run_bash(src)
        == '''def cp_test():
        subprocess.run(["cp","test.txt","test_copy.txt"])
    '''
    )


def test_pipe_basic():
    assert (
        run_bash(">cat test.txt | sed 's/HELLO/HOWDY/g'")
        == 'cmd1 = subprocess.Popen(["cat","test.txt"], stdout=subprocess.PIPE); cmd2 = subprocess.run(["sed","s/HELLO/HOWDY/g"], stdin=cmd1.stdout)\n'
    )
    assert (
        run_bash(">cat test.txt > test2.txt")
        == 'fout = open("test2.txt", "wb"); cmd1 = subprocess.run(["cat","test.txt"], stdout=fout)\n'
    )


def test_pipe_redirect():
    assert (
        run_bash(">cat test.txt | sed 's/HELLO/HOWDY/g' > test2.txt")
        == 'cmd1 = subprocess.Popen(["cat","test.txt"], stdout=subprocess.PIPE);fout = open("test2.txt", "wb"); cmd1 = subprocess.run(["sed","s/HELLO/HOWDY/g"], stdout=fout, stdin=cmd1.stdout)\n'
    )


def test_pipe_pipe_pipe():
    assert (
        run_bash(">cat test.txt | sed 's/HELLO/HOWDY/g' | sed 's/HOW/WHY/g' | sed 's/WHY/WHEN/g'")
        == 'cmd1 = subprocess.Popen(["cat","test.txt"], stdout=subprocess.PIPE);cmd1 = subprocess.Popen(["sed","s/HELLO/HOWDY/g"], stdout=subprocess.PIPE, stdin=cmd1.stdout);cmd1 = subprocess.Popen(["sed","s/HOW/WHY/g"], stdout=subprocess.PIPE, stdin=cmd1.stdout); cmd2 = subprocess.run(["sed","s/WHY/WHEN/g"], stdin=cmd1.stdout)\n'
    )


def test_pipe_chained_redirect():
    assert (
        run_bash(">cat test.txt | sed 's/HELLO/HOWDY\\n/g' > test1.txt >> test2.txt > test3.txt")
        == 'cmd1 = subprocess.Popen(["cat","test.txt"], stdout=subprocess.PIPE);fout = open("test1.txt", "wb"); cmd1 = subprocess.run(["sed","s/HELLO/HOWDY\\n/g"], stdout=fout, stdin=cmd1.stdout);fout7 = open("test2.txt", "ab"); cmd1 = subprocess.run(["cat","test1.txt"], stdout=fout7);fout9 = open("test3.txt", "wb"); cmd1 = subprocess.run(["cat","test2.txt"], stdout=fout9)\n'
    )


def test_input_redirect():
    assert run_bash(">sort < test.txt") == 'fout = open("test.txt", "r"); cmd1 = subprocess.run(["sort"], stdin=fout)\n'
    assert (
        run_bash(">sort < test.txt | sed 's/SORT/WHAT/g'")
        == 'fout = open("test.txt", "r"); cmd1 = subprocess.Popen(["sort"], stdin=fout, stdout=subprocess.PIPE);cmd2 = subprocess.run(["sed","s/SORT/WHAT/g"], stdin=cmd1.stdout)\n'
    )
    assert (
        run_bash(">sort < test.txt | sed 's/SORT/WHAT/g' | sed 's/WHAT/WHY/g'")
        == 'fout = open("test.txt", "r"); cmd1 = subprocess.Popen(["sort"], stdin=fout, stdout=subprocess.PIPE);cmd1 = subprocess.Popen(["sed","s/SORT/WHAT/g"], stdout=subprocess.PIPE, stdin=cmd1.stdout); cmd2 = subprocess.run(["sed","s/WHAT/WHY/g"], stdin=cmd1.stdout)\n'
    )
    assert (
        run_bash(">sort < test.txt | sed 's/SORT/WHAT/g' | sed 's/WHAT/WHY/g' > iredirect_end.txt")
        == 'fout = open("test.txt", "r"); cmd1 = subprocess.Popen(["sort"], stdin=fout, stdout=subprocess.PIPE);cmd1 = subprocess.Popen(["sed","s/SORT/WHAT/g"], stdout=subprocess.PIPE, stdin=cmd1.stdout);fout = open("iredirect_end.txt", "wb"); cmd1 = subprocess.run(["sed","s/WHAT/WHY/g"], stdout=fout, stdin=cmd1.stdout)\n'
    )
    assert (
        run_bash(">sort < test.txt > test_wb_redirect.txt")
        == 'fout = open("test.txt", "r"); cmd1 = subprocess.Popen(["sort"], stdin=fout, stdout=subprocess.PIPE);fout = open("test_wb_redirect.txt", "wb"); fout.write(cmd1.stdout.read());\n'
    )
    assert (
        run_bash(">sort < test.txt >> test_ab_redirect.txt")
        == 'fout = open("test.txt", "r"); cmd1 = subprocess.Popen(["sort"], stdin=fout, stdout=subprocess.PIPE);fout = open("test_ab_redirect.txt", "ab"); fout.write(cmd1.stdout.read());\n'
    )


def test_shell_commands():
    assert run_bash("$ls .github/*") == 'subprocess.run("ls .github/*", shell=True)\n'


def test_no_parse():
    assert run_bash('if 5 > 4:') == 'if 5 > 4:'
    assert run_bash('if (pred1 and pred2) > 0:') == 'if (pred1 and pred2) > 0:'
