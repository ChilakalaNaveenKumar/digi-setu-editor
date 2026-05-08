#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

#codly(
  annotations: (
    (
      start: 2, end: 5,
      content: block(
        width: 2em,
        rotate(-90deg, reflow: true,
          align(center)[Function body])
      ),
    ),
  ),
)
```py
def fib(n):
    if n <= 1:
        return n
    else:
        return fib(n - 1) + fib(n - 2)
fib(25)
```
