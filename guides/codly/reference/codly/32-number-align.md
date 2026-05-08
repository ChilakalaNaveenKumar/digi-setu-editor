# `number-align`

The alignment of the line numbers in their gutter cell.

| Field | Value |
| ----- | ----- |
| Type | `alignment` |
| Default | `left + horizon` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
#codly(number-align: right + top)
```py
# Iterative Fibonacci
def fib(n):
  if n <= 1:
    return n
  last, current = 0, 1
  for _ in range(2, n + 1):
    last, current = current, last + current
  return current
fib(25)
```
```

See [`examples/32-number-align/32-number-align.typ`](./examples/32-number-align/32-number-align.typ).

## Pitfalls

- Combine `right + top` with multi-line wrapping for the most natural
  look on long lines.

## Related

- [`31-number-format.md`](./31-number-format.md),
  [`33-number-placement.md`](./33-number-placement.md).
