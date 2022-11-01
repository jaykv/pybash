# PYBASH DEMO

# 1. use inside methods
def cp_test():
    >cp test.txt test_copy.txt

cp_test()

# 2. simple bash command execution with output
>python --version
>echo \\nthis is an echo

# 3. set output to python variable directly
out = >cat test.txt
test_data = out.decode('utf-8').strip()
print(test_data.replace("HELLO", "HOWDY"))

# 4. wrapped, in-line execution
print((>cat test.txt).decode('utf-8').strip())

# TODO:
#>echo "hello" >> test.txt