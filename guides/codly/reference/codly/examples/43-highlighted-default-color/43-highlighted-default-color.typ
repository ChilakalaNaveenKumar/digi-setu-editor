#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Using a green default highlight color:*
#codly(
  highlighted-default-color: green.lighten(60%),
  highlighted-lines: (1, 3),
)
```py
def fib(n):
    if n <= 1:
        return n
    else:
        return fib(n - 1) + fib(n - 2)
fib(25)
```

*Per-line color selection still works:*
#codly(highlighted-lines: ((1, red.lighten(60%)), 2, 3))
```py
def fib(n):
    if n <= 1:
        return n
    else:
        return fib(n - 1) + fib(n - 2)
fib(25)
```
