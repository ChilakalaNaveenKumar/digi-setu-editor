# `highlighted-lines`

Changes the background fill of certain lines to give them the appearance
of being highlighted. Specified as an array of either:

- **Line numbers:** the line number (one-indexed) as it is shown in the
  document (including offsets, skips, etc.)
- **Array `(line, fill)`:** an array of strictly two elements containing
  the line number (same as before) and a `color`, `gradient`, or `tiling`
  fill.

The default highlight colour is controlled by
[`highlighted-default-color`](./43-highlighted-default-color.md).

| Field | Value |
| ----- | ----- |
| Type | `array` or `none` |
| Default | `()` |
| Contextual function | yes |
| Automatically reset | yes |
| Released in 1.3.1 | yes |

> **Info** — Line numbers are one-indexed.

## Example

```typst
*Using default highlight color:*
#codly(highlighted-lines: (1, 3))
```py
def fib(n):
  if n <= 1:
    return n
  else:
    return fib(n - 1) + fib(n - 2)
fib(25)
```

*Per-line color selection:*
#codly(highlighted-lines: ((1, red.lighten(60%)), 2, 3))
```py
def fib(n):
  if n <= 1:
    return n
  else:
    return fib(n - 1) + fib(n - 2)
fib(25)
```
```

See [`examples/42-highlighted-lines/42-highlighted-lines.typ`](./examples/42-highlighted-lines/42-highlighted-lines.typ).

## Related

- [`43-highlighted-default-color.md`](./43-highlighted-default-color.md),
  [`44-highlights.md`](./44-highlights.md).
