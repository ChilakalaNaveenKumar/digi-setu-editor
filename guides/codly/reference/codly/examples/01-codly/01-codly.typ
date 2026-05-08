#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/codly:1.3.0": *
#show: codly-init

== Default look

```py
def fib(n):
    return n if n <= 1 else fib(n - 1) + fib(n - 2)
```

== A `codly()` call configures every following block

#codly(
  zebra-fill: aqua.lighten(70%),
  number-format: numbering.with("I"),
)

```py
print("First block uses Roman numerals + aqua zebra")
```

```py
print("So does this one — codly() is sticky.")
```

#codly-reset()

```py
print("Back to the defaults.")
```
