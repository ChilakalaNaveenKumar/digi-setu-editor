# `range`

The range of line numbers to display, **one-indexed**. If set to `none`,
all lines are displayed.

The same effect can be achieved using
[`codly-range`](../functions/03-codly-range.md).

| Field | Value |
| ----- | ----- |
| Type | `none` or `array` |
| Default | `none` |
| Contextual function | yes |
| Automatically reset | yes |
| Released in 1.3.1 | yes |

> **Info** — Line numbers are one-indexed, meaning that to reference the
> fourth line, you use the number `4`.

## Example

```typst
#codly(range: (2, 4))
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

See [`examples/13-range/13-range.typ`](./examples/13-range/13-range.typ).

## Pitfalls

- One-indexed: `(2, 4)` shows lines 2, 3, **and** 4 (inclusive).
- For multiple disjoint windows, use [`14-ranges.md`](./14-ranges.md)
  instead — it overrides `range`.
- Resets after each block.

## Related

- [`14-ranges.md`](./14-ranges.md), [`15-smart-skip.md`](./15-smart-skip.md),
  [`../functions/03-codly-range.md`](../functions/03-codly-range.md).
