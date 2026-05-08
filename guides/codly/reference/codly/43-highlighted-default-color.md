# `highlighted-default-color`

Changes the default colour of [`highlighted-lines`](./42-highlighted-lines.md).

| Field | Value |
| ----- | ----- |
| Type | `color`, `tiling`, or `gradient` |
| Default | `orange.lighten(60%)` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
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
... same code ...
```
```

See [`examples/43-highlighted-default-color/43-highlighted-default-color.typ`](./examples/43-highlighted-default-color/43-highlighted-default-color.typ).

## Related

- [`42-highlighted-lines.md`](./42-highlighted-lines.md).
