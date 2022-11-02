# PyBash

Streamline bash-command execution from python with an easy-to-use syntax. It combines the simplicity of writing bash scripts with the flexibility of python. Behind the scenes, any line starting with `>` is transformed to python `subprocess` calls and then injected into `sys.meta_path` as an import hook. All possible thanks to the wonderful [ideas](https://github.com/aroberge/ideas) project!


# Examples

### Simple execution with output
```python
>python --version
>echo \\nthis is an echo
```
outputs:
```
Python 3.9.15

this is an echo
```

### Set output to variable and parse
```python
out = >cat test.txt
test_data = out.decode('utf-8').strip()
print(test_data.replace("HELLO", "HOWDY"))
```
outputs:
```
HOWDY WORLD
```

### Wrapped, in-line execution and parsing
```python
print((>cat test.txt).decode('utf-8').strip())
```
outputs:
```
HELLO WORLD
```

### Redirection
```python
>echo "hello" >> test4.txt
```

### Pipe chaining
```python
>cat test.txt | sed 's/HELLO/HOWDY/g' | sed 's/HOW/WHY/g' | sed 's/WHY/WHEN/g'
```
outputs:
```
WHENDY WORLD
```

### Redirection chaining
```python
>cat test.txt | sed 's/HELLO/HOWDY\\n/g' > test1.txt >> test2.txt > test3.txt
```

### Chaining pipes and redirection- works in tandem!
```python
>cat test.txt | sed 's/HELLO/HOWDY\\n/g' > test5.txt
```

#### Also works inside methods!
```python
# PYBASH DEMO #
def cp_test():
    >cp test.txt test_copy.txt

cp_test()
```

# Usage
1. `pip install ideas`
2. `python run.py` OR directly, `python -m ideas demo -a pybash`


# TODO
- Redirection: `>echo "hello" >> test.txt`
- Pipes: `>cat test.txt | sed 's/HELLO/HOWDY/g'`