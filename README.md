# PyBash

Streamline bash-command execution from python with an easy-to-use syntax. It combines the simplicity of writing bash scripts with the flexibility of python. Behind the scenes, any line starting with `>` is transformed to python `subprocess` calls and then injected into `sys.meta_path` as an import hook. All possible thanks to the wonderful [ideas](https://github.com/aroberge/ideas) project!


# Example

```
# PYBASH DEMO #

def cp_test():
    >cp test.txt test_copy.txt

cp_test()

>echo \nthis is an echo \n
>cat test.txt
```

Outputs:
```
this is an echo

HELLO WORLD
```

# Usage
1. `pip install ideas`
2. `python run.py` OR directly, `python -m ideas demo -a pybash`
