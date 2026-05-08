#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

#codly(ranges: ((2, 2), (4, 4)))
```py
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
fib(25)
```
