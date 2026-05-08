#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

== Multiple highlights with tags

#codly(highlights: (
  (line: 4, start: 2, end: none, fill: red),
  (line: 5, start: 13, end: 19, fill: green, tag: "(a)"),
  (line: 5, start: 26, fill: blue, tag: "(b)"),
))
```py
def fib(n):
    if n <= 1:
        return n
    else:
        return fib(n - 1) + fib(n - 2)
print(fib(25))
```

== Per-highlight overrides

#codly(highlights: (
  (line: 4, start: 2, end: none, fill: red),
  (line: 5, start: 13, end: 19, fill: green, tag: "(a)",
    inset: 0.1em, radius: 0.5em),
  (line: 5, start: 26, fill: blue, tag: "(b)", clip: false),
))
```py
def fib(n):
    if n <= 1:
        return n
    else:
        return fib(n - 1) + fib(n - 2)
print(fib(25))
```
