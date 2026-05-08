# `skips`

Insert a "skip" at specified line numbers, setting its offset to the
length of the skip. The skip is formatted using
[`skip-line`](./38-skip-line.md) and [`skip-number`](./39-skip-number.md).

Each skip is an array `(line, length)`:

| Position | Meaning |
| -------- | ------- |
| `line` | the line where the skip is inserted (**zero-indexed**) |
| `length` | the number of lines to "skip" (added to subsequent line numbers) |

The same effect can be achieved using
[`codly-skip`](../functions/02-codly-skip.md).

| Field | Value |
| ----- | ----- |
| Type | `array` or `none` |
| Default | `none` |
| Contextual function | yes |
| Automatically reset | yes |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(skips: ((4, 32),))
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)
fib(25)
```
```

After line 3 (zero-index 3 = "after line 4 in the manual's count?" — see
pitfalls below), the next visible line jumps to 36.

See [`examples/37-skips/37-skips.typ`](./examples/37-skips/37-skips.typ).

## Pitfalls

- `line` is **zero-indexed** (unlike most other line-number arguments in
  Codly, which are one-indexed). The manual's example uses `(4, 32)` and
  the resulting figure shows the skip after the *fourth visible line*.
- The skip increments the subsequent line numbers by `length`, so use
  this to mirror omitted source rather than to "shift" line numbers.
- Resets after each block.

## Related

- [`38-skip-line.md`](./38-skip-line.md),
  [`39-skip-number.md`](./39-skip-number.md),
  [`15-smart-skip.md`](./15-smart-skip.md),
  [`../functions/02-codly-skip.md`](../functions/02-codly-skip.md).
