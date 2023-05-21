##
# Setup hook
import importlib.util
import sys
from pathlib import Path

from pybash.hook import add_hook

hook = add_hook()

# Run script dynamically
if __name__ == "__main__":
    spec = None

    if path_or_module := sys.argv[1]:
        file_path = Path(path_or_module)
        if file_path.exists() and file_path.is_file():
            spec = hook.find_spec(path_or_module.split('.py')[0], None)
        else:
            spec = importlib.util.find_spec(path_or_module)

        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            print(f"Could not import {path_or_module}")
