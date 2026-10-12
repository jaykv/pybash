# PYBASH DEMO #
# run with: pybash demo.py   (or: python -m pybash demo.py)
# see the generated Python with: pybash --show demo.py

# 1. run a command; works anywhere a statement does
$printf 'SORT TEST\nHELLO WORLD\n' > test.txt

def cp_test():
    $cp test.txt test_copy.txt

cp_test()

# 2. capture output as bytes
out = $cat test.txt
print(out.decode().strip().replace("HELLO", "HOWDY"))

# 3. capture inline, with ($ ...) or $(...)
print(($cat test.txt).decode().strip())
print($(wc -l test.txt).decode().split()[0], "lines")

# 4. pipes, redirects and && || ; run without a shell
$cat test.txt | sed 's/HELLO/HOWDY/g' | sed 's/HOW/WHY/g'
$sort < test.txt >> sorted_test.txt
$test -f sorted_test.txt && echo "sorted" || echo "not sorted"
$ls no-such-file 2> errors.txt; echo "kept going"
count = $sort test.txt | uniq | wc -l
print("unique lines:", int(count))

# 5. interpolate Python values; each one is always a single argument
name = "world; echo not-a-second-command"
$echo hello {{name}}
$echo f{len(name):04d} chars

# 6. a real shell when you want globbing or expansion: start the line with >
>ls ./*.txt | head -n 3
>echo "safely quoted: {{name}}"

# 7. long commands can continue onto the next line
$rm -f test.txt test_copy.txt \
    sorted_test.txt errors.txt
