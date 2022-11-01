# PyBash

Streamline bash-command execution from python with an easy-to-use syntax. It combines the simplicity of writing bash scripts with the flexibility of python. Behind the scenes, any line starting with `>` is transformed to python `subprocess` calls and then injected into `sys.meta_path` as an import hook. All possible thanks to the wonderful [ideas](https://github.com/aroberge/ideas) project!


# Example

```
# PYBASH DEMO #
def cp_test():
    >cp test.txt test_copy.txt

cp_test()

# simple command execution with output
>python --version
>echo \nthis is an echo\n

# set output to variable and parse directly
out = >cat test.txt
test_data = out.decode('utf-8').strip()
print(test_data.replace("HELLO", "HOWDY"))
```

Outputs:
```
Python 3.9.14

this is an echo

HOWDY WORLD
```

# Usage
1. `pip install ideas`
2. `python run.py` OR directly, `python -m ideas demo -a pybash`
