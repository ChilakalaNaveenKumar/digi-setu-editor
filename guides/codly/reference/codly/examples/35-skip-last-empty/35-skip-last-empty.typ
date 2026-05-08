#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

*Enabled (default):*
```py
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

```

*Disabled:*
#codly(skip-last-empty: false)
```py
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

```
