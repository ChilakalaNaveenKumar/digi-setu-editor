#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

```py
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
``` <fib-fn>

*Will continue at line 5*
#codly(offset-from: <fib-fn>)
```py
fib(25)
```
