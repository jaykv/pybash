# PyBash

![GitHub Workflow Status (with branch)](https://img.shields.io/github/actions/workflow/status/jaykv/pybash/python-app.yml?branch=main)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pybash)
![PyPI](https://img.shields.io/pypi/v/pybash)
![GitHub](https://img.shields.io/github/license/jaykv/pybash)

Streamline bash-command execution from python with a new syntax. It combines the simplicity of writing bash scripts with the flexibility of python. Under the hood, any line or variable assignment starting with `>` or surrounded by parentheses is transformed to python `subprocess` calls and then injected into `sys.meta_path` as an import hook. All possible thanks to the wonderful [ideas](https://github.com/aroberge/ideas) project!

For security and performance reasons, PyBash will NOT execute as shell, unless explicitly specified with a `$` instead of a single `>` before the command. While running commands as shell can be convenient, it can also spawn security risks if you're not too careful. If you're curious about the transformations, look at the [unit tests](test_pybash.py) for some quick examples.

Note: this is a mainly experimental library. Consider the risks and test before using in prod.

# Installation
`pip install pybash`

# Setup hook
```python
import pybash
pybash.add_hook()
```

# Usage

### 1. Simple execution with output
```python
>python --version
>echo \\nthis is an echo
```
outputs:
```
Python 3.9.15

this is an echo
```

### 2. Set output to variable and parse
```python
out = >cat test.txt
test_data = out.decode('utf-8').strip()
print(test_data.replace("HELLO", "HOWDY"))
```
outputs:
```
HOWDY WORLD
```

### 3. Wrapped, in-line execution and parsing
```python
print((>cat test.txt).decode('utf-8').strip())
```
outputs:
```
HELLO WORLD
```

### 4. Redirection
```python
>echo "hello" >> test4.txt
```

### 5. Pipe chaining
```python
>cat test.txt | sed 's/HELLO/HOWDY/g' | sed 's/HOW/WHY/g' | sed 's/WHY/WHEN/g'
```
outputs:
```
WHENDY WORLD
```

### 6. Redirection chaining
```python
>cat test.txt | sed 's/HELLO/HOWDY\\n/g' > test1.txt >> test2.txt > test3.txt
```

### 7. Chaining pipes and redirection- works in tandem!
```python
>cat test.txt | sed 's/HELLO/HOWDY\\n/g' > test5.txt
```

### 8. Input redirection
```python
>sort < test.txt >> sorted_test.txt
```

```python
>sort < test.txt | sed 's/SORT/TEST\\n/g'
```
### 9. Glob patterns with shell
```python
$ls .github/*
```

### 10. Static interpolation
Denoted by {{variable_or_function_call_here}}. For static interpolation, no quotes, spaces or expressions within the {{}} or in the string being injected.

```python
## GOOD
command = "status"
def get_option(command):
    return "-s" if command == "status" else "-v"
>git {{command}} {{get_option(command)}}

display_type = "labels"
>kubectl get pods --show-{{display_type}}=true

## BAD
option = "-s -v"
>git status {{option}}

options = ['-s', '-v']
>git status {{" ".join(options)}}

# use dynamic interpolation
options = {'version': '-v'}
>git status {{options['version']}}
```

### 11. Dynamic interpolation
Denoted by {{{ any python variable, function call, or expression here }}}. The output of the variable, function call, or the expression must still not include spaces.

```python
## GOOD

# git -h
options = {'version': '-v', 'help': '-h'}
>git {{{options['h']}}}

# kubectl get pods --show-labels -n coffee
namespace = "coffee"
>kubectl get pods {{{"--" + "-".join(['show', 'labels'])}}} -n {{{namespace}}}

## BAD
option = "-s -v"
>git status {{{ option }}}
```

#### Also works inside methods!
```python
# PYBASH DEMO #
def cp_test():
    >cp test.txt test_copy.txt

cp_test()
```

# Dev

#### Demo
`python run.py`

#### Debugging
`python -m ideas demo -a pybash -s` to view the transformed source code
