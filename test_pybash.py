import pybash

run_bash = pybash.transform_source


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


def test_no_parse():
    assert run_bash('if 5 > 4:') == 'if 5 > 4:'
    assert run_bash('if (pred1 and pred2) > 0:') == 'if (pred1 and pred2) > 0:'
