#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

#codly(number-align: right + top)
```py
# Iterative Fibonacci
# As opposed to the recursive version
def fib(n):
    if n <= 1:
        return n
    last, current = 0, 1
    for _ in range(2, n + 1):
        last, current = current, last + current
    return current
fib(25)
```
