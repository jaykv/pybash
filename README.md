# PyBash

Streamline bash-command execution from python with an easy-to-use syntax. It combines the simplicity of writing bash scripts with the flexibility of python. Under the hood, any line or variable assignment starting with `>` or surrounded by parentheses is transformed to python `subprocess` calls and then injected into `sys.meta_path` as an import hook. All possible thanks to the wonderful [ideas](https://github.com/aroberge/ideas) project!

For security and performance reasons, PyBash will NOT execute as shell, unless explicitly specified with a `$` instead of a single `>` before the command. While running commands as shell can be convenient, it can also spawn security risks and  if you're not too careful. If you're curious about the transformations, look at the [unit tests](test_pybash.py) for some quick examples.

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
