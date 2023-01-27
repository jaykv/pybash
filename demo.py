# PYBASH DEMO #
def run():
    # dynamic interpolation
    options = {'version': '-v', 'help': '-h'}
    >git {{{options['h']}}}
    
    namespace = "coffee"
    >kubectl get pods {{{"--" + "-".join(['show', 'labels'])}}} --namespace {{{namespace}}}
    
    # static interpolation
    git_command = "status"
    option = "-v"
    
    >git {{git_command}} {{option}}
    
    #TODO:
    #a = >echo "hello" >> test.txt
    #a = >sort < test.txt | grep "HELLO"
    #print(f"test: {a}")
    
    # 1. use inside methods
    def cp_test():
        print("1. >cp test.txt test_copy.txt")
        >cp test.txt test_copy.txt

    cp_test()

    # 2. simple bash command execution with output
    print("2. >python --version\n   >echo \\nthis is an echo")
    >python --version
    >echo \\nthis is an echo

    # 3. set output to python variable directly
    out = >cat test.txt
    test_data = out.decode('utf-8').strip()
    print(test_data.replace("HELLO", "HOWDY"))

    # 4. wrapped, in-line execution
    print((>cat test.txt).decode('utf-8').strip())

    # 5. redirection
    >echo "hello" >> test4.txt

    # 6. pipe chaining
    >cat test.txt | sed 's/HELLO/HOWDY/g' | sed 's/HOW/WHY/g' | sed 's/WHY/WHEN/g'
    
    # 7. chaining pipes and redirection- works with all!
    >cat test.txt | sed 's/HELLO/HOWDY\\n/g' > test5.txt
    
    # 8. chained redirection
    >cat test.txt | sed 's/HELLO/HOWDY\\n/g' > test1.txt >> test2.txt > test3.txt

    # 9. input redirection
    >sort < test.txt >> sorted_test.txt
    >sort < test.txt | sed 's/SORT/TEST\\n/g'
    
    # 10. Glob patterns
    $ls .github/*
