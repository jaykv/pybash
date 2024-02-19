# Setup hook
from pybash.hook import add_hook

add_hook()

##
# Import demo script to run
if __name__ == "__main__":
    import demo

    print(f"~ completed running {demo}")
