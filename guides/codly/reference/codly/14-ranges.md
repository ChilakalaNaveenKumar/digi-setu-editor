# `ranges`

The **multiple** ranges of line numbers to display, one-indexed. If set
to `none`, all lines are displayed.

Note that it overrides the [`range`](./13-range.md) argument when both
are set. The same effect can be achieved using
[`codly-range`](../functions/03-codly-range.md) when given more than one
range.

| Field | Value |
| ----- | ----- |
| Type | `none` or `array` |
| Default | `none` |
| Contextual function | yes |
| Automatically reset | yes |
| Released in 1.3.1 | yes |

> **Info** — Line numbers are one-indexed.

## Example

```typst
#codly(ranges: ((2, 2), (4, 4)))
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

Renders just lines 2 and 4. Pair with
[`smart-skip: true`](./15-smart-skip.md) to insert a "..." between them.

See [`examples/14-ranges/14-ranges.typ`](./examples/14-ranges/14-ranges.typ).

## Related

- [`13-range.md`](./13-range.md), [`15-smart-skip.md`](./15-smart-skip.md),
  [`../functions/03-codly-range.md`](../functions/03-codly-range.md).
